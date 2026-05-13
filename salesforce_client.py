"""
Salesforce connectivity layer.
Uses OAuth 2.0 Username-Password flow — works with SDO orgs where SOAP login is disabled.
"""

import urllib.request
import urllib.parse
import json
from typing import List, Dict, Any


EXCLUDED_PREFIXES = (
    "Ai","Auth","Async","Apex","Background","Batch","Connected","Custom",
    "Dashboard","Data","Duplicate","Email","Entity","Event","External","Feed",
    "Flow","Flex","Group","History","Individual","Knowledge","Lightning","List",
    "Login","Macro","Metric","My","Named","Network","Note","Org","Package",
    "Permission","Platform","Process","Profile","Queue","Quick","Recent",
    "Record","Report","Role","Search","Set","Site","Skill","Stamp","Static",
    "Stream","Tag","Territory","Trigger","User","View","Visualforce","Wave",
    "Web","Workflow",
)

USEFUL_OBJECTS = {
    "Account","Contact","Opportunity","Lead","Case","Campaign","Contract",
    "Order","Product2","Pricebook2","PricebookEntry","OpportunityLineItem",
    "Quote","Asset","ServiceAppointment","WorkOrder","Solution",
}


class SalesforceClient:
    def __init__(self, username: str, password: str, security_token: str,
                 instance_url: str, consumer_key: str, consumer_secret: str):

        instance_url = instance_url.rstrip("/")

        # OAuth 2.0 Username-Password flow
        token_url = f"{instance_url}/services/oauth2/token"
        params = urllib.parse.urlencode({
            "grant_type":    "password",
            "client_id":     consumer_key,
            "client_secret": consumer_secret,
            "username":      username,
            "password":      password + security_token,
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=params, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))

        self.access_token  = token_data["access_token"]
        self.instance_url  = token_data["instance_url"]
        self.api_version   = "62.0"
        self.base_url      = f"{self.instance_url}/services/data/v{self.api_version}"

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_sobject_list(self) -> List[Dict[str, str]]:
        result   = self._get("/sobjects/")
        filtered = []
        for obj in result.get("sobjects", []):
            name = obj.get("name", "")
            if not obj.get("triggerable") or not obj.get("queryable"):
                continue
            if "__" in name and not name.endswith("__c"):
                continue
            is_custom   = name.endswith("__c")
            is_useful   = name in USEFUL_OBJECTS
            is_excluded = any(name.startswith(p) for p in EXCLUDED_PREFIXES)
            if is_custom or is_useful or not is_excluded:
                filtered.append({"name": name, "label": obj.get("label",""), "is_custom": is_custom})
        filtered.sort(key=lambda x: (not x["is_custom"], x["name"].lower()))
        return filtered

    def get_object_schema(self, object_name: str) -> Dict[str, Any]:
        describe = self._get(f"/sobjects/{object_name}/describe/")
        fields   = []
        for f in describe.get("fields", []):
            fi = {
                "name":       f["name"],
                "label":      f["label"],
                "type":       f["type"],
                "required":   not f["nillable"] and not f["defaultedOnCreate"],
                "updateable": f["updateable"],
                "createable": f["createable"],
            }
            if f["type"] in ("reference", "masterrecord"):
                refs = f.get("referenceTo", [])
                if refs:
                    fi["referenceTo"] = refs
            fields.append(fi)
        return {
            "name":        describe["name"],
            "label":       describe["label"],
            "fields":      fields,
            "keyPrefix":   describe.get("keyPrefix", ""),
            "custom":      describe.get("custom", False),
            "triggerable": describe.get("triggerable", False),
        }
