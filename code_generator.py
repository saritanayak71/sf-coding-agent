"""
Code Generator — calls Groq API (Llama 3.1 70B) via standard urllib (no SDK needed).
Generates Apex Trigger + Handler + Test Class.
"""

import json
import re
import urllib.request
from typing import Dict, Any


SYSTEM_PROMPT = """You are a senior Salesforce developer with deep Apex expertise.
Follow these rules strictly:
- One trigger per object, thin trigger, handler class pattern
- Bulkified code — never SOQL or DML inside loops
- with sharing on handler classes
- Separation of concerns: trigger -> handler -> service layer
- Meaningful variable names, clear inline comments
- Test classes: @TestSetup, bulk test with 200 records, no SeeAllData=true, assertions included

Respond ONLY with a valid JSON object. No markdown fences, no preamble, no extra text outside JSON.
"""

PROMPT_TEMPLATE = """Generate Apex code for the following requirement.

## Requirement
{requirement}

## SObject: {sobject_name} ({sobject_label})

## Key Fields
{fields_summary}

## Best Practices to Apply
{best_practices_context}

## Deliverables
1. A thin Apex trigger on {sobject_name} routing to a handler class
2. The handler class with appropriate context methods and full business logic
3. A test class with @TestSetup, bulk test (200 records), and meaningful assertions

Choose trigger contexts (before/after insert/update/delete) based on the requirement.
Use actual field API names from the schema above.

Respond ONLY with this exact JSON (no markdown, no extra text):
{{"trigger": "<full trigger code>", "handler": "<full handler class code>", "test_class": "<full test class code>", "notes": "<brief notes on trigger contexts chosen, governor limit considerations, assumptions>"}}
"""


def _summarise_fields(schema: Dict[str, Any], max_fields: int = 40) -> str:
    fields = schema.get("fields", [])
    priority_names = {
        "Id","Name","OwnerId","RecordTypeId","AccountId","ContactId",
        "OpportunityId","CaseId","LeadId","StageName","Amount","CloseDate",
        "Status","Priority","Type","Description",
    }
    priority = [f for f in fields if f.get("required") or f["name"] in priority_names]
    others   = [f for f in fields if f not in priority]
    lines    = []
    for f in (priority + others)[:max_fields]:
        ref  = f" -> {', '.join(f['referenceTo'])}" if "referenceTo" in f else ""
        req  = " [required]" if f.get("required") else ""
        lines.append(f"  {f['name']} ({f['type']}){ref}{req} — {f.get('label','')}")
    return "\n".join(lines)


def _extract_json(raw: str) -> Dict[str, str]:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {
        "trigger":    raw,
        "handler":    "// Could not parse structured response — see Trigger tab",
        "test_class": "// Could not parse structured response",
        "notes":      "Response parsing failed. Raw output is in the Trigger tab.",
    }


class CodeGenerator:
    def __init__(self, groq_api_key: str):
        self.api_key = groq_api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model   = "llama-3.1-70b-versatile"

    def generate(self, requirement: str, sobject: str,
                 schema: Dict[str, Any], best_practices_context: str) -> Dict[str, str]:

        user_prompt = PROMPT_TEMPLATE.format(
            requirement            = requirement,
            sobject_name           = sobject,
            sobject_label          = schema.get("label", sobject),
            fields_summary         = _summarise_fields(schema),
            best_practices_context = best_practices_context or "Apply standard Salesforce Apex best practices.",
        )

        payload = json.dumps({
            "model":       self.model,
            "temperature": 0.2,
            "max_tokens":  4096,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data    = payload,
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method = "POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return _extract_json(data["choices"][0]["message"]["content"])
