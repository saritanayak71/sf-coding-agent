"""
Salesforce connectivity layer.
Uses simple-salesforce to connect via Username + Password + Security Token.
"""

from simple_salesforce import Salesforce
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
    def __init__(self, username: str, password: str, security_token: str, instance_url: str):
        self.sf = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            instance_url=instance_url.rstrip("/"),
            version="62.0",
        )

    def get_sobject_list(self) -> List[Dict[str, str]]:
        result   = self.sf.describe()
        filtered = []
        for obj in result["sobjects"]:
            name = obj.get("name","")
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
        describe = getattr(self.sf, object_name).describe()
        fields   = []
        for f in describe["fields"]:
            fi = {
                "name":       f["name"],
                "label":      f["label"],
                "type":       f["type"],
                "required":   not f["nillable"] and not f["defaultedOnCreate"],
                "updateable": f["updateable"],
                "createable": f["createable"],
            }
            if f["type"] in ("reference","masterrecord"):
                refs = f.get("referenceTo",[])
                if refs:
                    fi["referenceTo"] = refs
            fields.append(fi)
        return {
            "name":        describe["name"],
            "label":       describe["label"],
            "fields":      fields,
            "keyPrefix":   describe.get("keyPrefix",""),
            "custom":      describe.get("custom", False),
            "triggerable": describe.get("triggerable", False),
        }
