import chromadb
from chromadb.utils import embedding_functions
import os

# Built-in best practices — no external file dependency for POC
BEST_PRACTICES = [
    {
        "id": "bp_001",
        "text": """Apex Trigger Best Practices:
- One trigger per object. Never write logic directly in the trigger body.
- Always use a TriggerHandler class to separate logic from the trigger.
- Bulkify all trigger logic — assume 200 records in every context.
- Use trigger context variables: Trigger.new, Trigger.old, Trigger.newMap, Trigger.oldMap.
- Never write SOQL or DML inside a for loop — always collect IDs, query outside, then process.
- Use Trigger.isBefore / Trigger.isAfter / Trigger.isInsert / Trigger.isUpdate guards.
- Example trigger structure:
  trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
      AccountTriggerHandler handler = new AccountTriggerHandler();
      if (Trigger.isBefore) {
          if (Trigger.isInsert) handler.onBeforeInsert(Trigger.new);
          if (Trigger.isUpdate) handler.onBeforeUpdate(Trigger.new, Trigger.oldMap);
      }
      if (Trigger.isAfter) {
          if (Trigger.isInsert) handler.onAfterInsert(Trigger.new);
          if (Trigger.isUpdate) handler.onAfterUpdate(Trigger.new, Trigger.oldMap);
      }
  }"""
    },
    {
        "id": "bp_002",
        "text": """Apex TriggerHandler Class Pattern:
- The handler class contains all business logic called from the trigger.
- Methods map 1:1 to trigger contexts: onBeforeInsert, onBeforeUpdate, onAfterInsert, onAfterUpdate.
- Delegate to service classes for complex logic — the handler is an orchestrator, not a processor.
- Example handler structure:
  public class AccountTriggerHandler {
      public void onBeforeInsert(List<Account> newAccounts) {
          AccountService.populateDefaults(newAccounts);
      }
      public void onAfterInsert(List<Account> newAccounts) {
          AccountService.createRelatedRecords(newAccounts);
      }
  }"""
    },
    {
        "id": "bp_003",
        "text": """Apex Service Class Pattern:
- Service classes contain reusable business logic.
- All methods should be static unless state management is required.
- Accept lists of SObjects, not single records — always bulk-safe.
- Service classes call selector/repository classes for SOQL, never inline queries.
- Example: AccountService.cls with static methods like updateAccountRatings(List<Account> accounts)"""
    },
    {
        "id": "bp_004",
        "text": """Apex Governor Limits — Critical Rules:
- SOQL limit: 100 queries per transaction. Never query inside a loop.
- DML limit: 150 statements per transaction. Collect records in a list, DML once.
- Heap size: 6MB (sync) / 12MB (async). Avoid storing large collections unnecessarily.
- CPU time: 10,000ms (sync). Move heavy processing to Queueable or Batch Apex.
- Pattern for bulk-safe SOQL:
  Set<Id> accountIds = new Set<Id>();
  for (Opportunity opp : triggerNew) { accountIds.add(opp.AccountId); }
  Map<Id, Account> accountMap = new Map<Id, Account>(
      [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
  );"""
    },
    {
        "id": "bp_005",
        "text": """Apex Test Class Best Practices:
- Minimum 75% code coverage required for deployment; target 90%+.
- Use @isTest annotation on the class and each test method.
- Use Test.startTest() and Test.stopTest() to reset governor limits.
- Create test data inside the test — never rely on org data.
- Use System.assert(), System.assertEquals(), System.assertNotEquals() for assertions.
- Test both positive (happy path) and negative (error/exception) scenarios.
- Use @TestSetup for shared test data across multiple test methods.
- Example structure:
  @isTest
  private class AccountTriggerHandlerTest {
      @TestSetup
      static void setupData() {
          Account acc = new Account(Name = 'Test Account');
          insert acc;
      }
      @isTest
      static void testOnBeforeInsert_populatesDefaults() {
          Test.startTest();
          Account acc = new Account(Name = 'New Account');
          insert acc;
          Test.stopTest();
          Account result = [SELECT Id, Rating FROM Account WHERE Id = :acc.Id];
          System.assertNotEquals(null, result.Rating, 'Rating should be populated');
      }
  }"""
    },
    {
        "id": "bp_006",
        "text": """Apex Security Best Practices:
- Always enforce CRUD and FLS using with sharing or inherited sharing on classes.
- Use WITH SECURITY_ENFORCED in SOQL or Security.stripInaccessible() for FLS.
- Never expose sensitive fields directly; use wrapper classes for API responses.
- Declare classes as: public with sharing class MyClass for user-context operations.
- For system-level operations (integrations, batch), use: public without sharing class MyClass with explicit justification in comments."""
    },
    {
        "id": "bp_007",
        "text": """Apex Naming Conventions:
- Trigger: ObjectNameTrigger.trigger (e.g. AccountTrigger)
- Handler: ObjectNameTriggerHandler.cls (e.g. AccountTriggerHandler)
- Service: ObjectNameService.cls (e.g. AccountService)
- Test class: ClassNameTest.cls (e.g. AccountTriggerHandlerTest)
- Constants: Use ALL_CAPS_WITH_UNDERSCORES
- Methods: camelCase, verb-first (e.g. populateDefaults, createRelatedRecords)
- Variables: camelCase (e.g. newAccountList, accountMap)"""
    },
]

_chroma_client = None
_collection = None

def _init_chroma():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    _chroma_client = chromadb.Client()
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    _collection = _chroma_client.get_or_create_collection(
        name="sf_best_practices",
        embedding_function=ef,
    )

    # Populate if empty
    if _collection.count() == 0:
        _collection.add(
            documents=[bp["text"] for bp in BEST_PRACTICES],
            ids=[bp["id"] for bp in BEST_PRACTICES],
        )

    return _collection

def retrieve_best_practices(query: str, n_results: int = 3) -> str:
    """Retrieve top-N relevant best practice chunks for a given query."""
    collection = _init_chroma()
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, len(BEST_PRACTICES)),
    )
    docs = results.get("documents", [[]])[0]
    return "\n\n---\n\n".join(docs) if docs else ""
