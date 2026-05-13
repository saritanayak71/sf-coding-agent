"""
RAG Engine — embeds best practices docs and retrieves relevant chunks.
Uses sentence-transformers (all-MiniLM-L6-v2) — no API key needed.
"""

from typing import List
import numpy as np

DEFAULT_BEST_PRACTICES = """
# Apex Trigger Best Practices

## One Trigger Per Object
Always write one trigger per SObject. Never put business logic directly in the trigger.
Use a handler class to keep triggers thin and testable.

trigger OpportunityTrigger on Opportunity (before insert, before update, after insert, after update) {
    OpportunityTriggerHandler handler = new OpportunityTriggerHandler();
    if (Trigger.isBefore) {
        if (Trigger.isInsert) handler.onBeforeInsert(Trigger.new);
        if (Trigger.isUpdate) handler.onBeforeUpdate(Trigger.new, Trigger.oldMap);
    }
    if (Trigger.isAfter) {
        if (Trigger.isInsert) handler.onAfterInsert(Trigger.new);
        if (Trigger.isUpdate) handler.onAfterUpdate(Trigger.new, Trigger.oldMap);
    }
}

## Governor Limits
Never put SOQL or DML inside a for loop. Always collect IDs first, query outside, then process.

## Handler Class Pattern
public with sharing class OpportunityTriggerHandler {
    public void onBeforeInsert(List<Opportunity> newList) {}
    public void onBeforeUpdate(List<Opportunity> newList, Map<Id,Opportunity> oldMap) {}
    public void onAfterInsert(List<Opportunity> newList) {}
    public void onAfterUpdate(List<Opportunity> newList, Map<Id,Opportunity> oldMap) {}
}

## Security
Use with sharing on handler classes. Enforce CRUD/FLS. Use WITH SECURITY_ENFORCED in SOQL.

## Test Classes
@isTest
private class OpportunityTriggerHandlerTest {
    @TestSetup
    static void makeData() {
        Account acc = new Account(Name = 'Test Account');
        insert acc;
    }
    @isTest
    static void testBulkInsert() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        List<Opportunity> opps = new List<Opportunity>();
        for (Integer i = 0; i < 200; i++) {
            opps.add(new Opportunity(Name='Test '+i, AccountId=acc.Id,
                StageName='Prospecting', CloseDate=Date.today().addDays(30)));
        }
        Test.startTest();
        insert opps;
        Test.stopTest();
    }
}

## Separation of Concerns
Layer: Trigger (routing only) -> Handler (orchestration) -> Service (business logic) -> Selector (SOQL)

## Custom Metadata Types
Use CMTs for configuration values instead of hardcoded strings.

## DML Best Practices
Collect all records into lists, perform single DML at end.

## Async Patterns
Use Queueable for callouts from triggers, long-running operations, or chained jobs.
"""


class RAGEngine:
    def __init__(self):
        self.chunks: List[str] = []
        self.embeddings: List[np.ndarray] = []
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def _chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 40) -> List[str]:
        words  = text.split()
        chunks = []
        start  = 0
        while start < len(words):
            chunks.append(" ".join(words[start:start + chunk_size]))
            start += chunk_size - overlap
        return chunks

    def add_document(self, name: str, content: str):
        model = self._get_model()
        for chunk in self._chunk_text(content):
            if len(chunk.strip()) > 20:
                self.chunks.append(chunk)
                self.embeddings.append(model.encode(chunk, convert_to_numpy=True))

    def load_defaults(self):
        self.add_document("defaults", DEFAULT_BEST_PRACTICES)

    def query(self, query_text: str, top_k: int = 4) -> str:
        if not self.chunks:
            return ""
        model  = self._get_model()
        q_emb  = model.encode(query_text, convert_to_numpy=True)
        scores = []
        for emb in self.embeddings:
            nq, ne = np.linalg.norm(q_emb), np.linalg.norm(emb)
            scores.append(float(np.dot(q_emb, emb) / (nq * ne)) if nq and ne else 0.0)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return "\n\n---\n\n".join(self.chunks[i] for i in top_idx)
