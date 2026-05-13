from simple_salesforce import Salesforce
import streamlit as st

def get_sf_connection():
    """Establish Salesforce connection using Streamlit secrets."""
    try:
        sf = Salesforce(
            username=st.secrets["SF_USERNAME"],
            password=st.secrets["SF_PASSWORD"],
            security_token=st.secrets["SF_SECURITY_TOKEN"],
            domain=st.secrets.get("SF_DOMAIN", "login")
        )
        return sf
    except Exception as e:
        st.error(f"Salesforce connection failed: {str(e)}")
        return None

def get_sobject_list(sf):
    """Fetch all queryable, createable SObjects from the org."""
    try:
        describe = sf.describe()
        objects = [
            obj["name"]
            for obj in describe["sobjects"]
            if obj["queryable"] and obj["createable"]
        ]
        return sorted(objects)
    except Exception as e:
        st.error(f"Failed to fetch SObject list: {str(e)}")
        return []

def get_object_schema(sf, object_name):
    """Fetch full schema for a given SObject — fields, types, relationships."""
    try:
        obj_describe = getattr(sf, object_name).describe()

        fields = []
        for f in obj_describe["fields"]:
            field_info = {
                "name": f["name"],
                "label": f["label"],
                "type": f["type"],
                "required": not f["nillable"] and not f["defaultedOnCreate"],
                "updateable": f["updateable"],
                "createable": f["createable"],
            }
            # Capture relationship name for lookups
            if f["type"] in ("reference", "lookup") and f.get("relationshipName"):
                field_info["relationshipName"] = f["relationshipName"]
                field_info["referenceTo"] = f.get("referenceTo", [])
            fields.append(field_info)

        relationships = [
            {
                "name": r["relationshipName"],
                "childSObject": r["childSObject"],
                "field": r["field"],
            }
            for r in obj_describe.get("childRelationships", [])
            if r["relationshipName"]
        ]

        return {
            "name": object_name,
            "label": obj_describe["label"],
            "fields": fields,
            "childRelationships": relationships[:10],  # cap for context window
        }
    except Exception as e:
        st.error(f"Failed to fetch schema for {object_name}: {str(e)}")
        return None

def format_schema_for_prompt(schema):
    """Convert schema dict into a concise string for the LLM prompt."""
    if not schema:
        return ""

    lines = [
        f"Object: {schema['name']} ({schema['label']})",
        "",
        "Fields:",
    ]
    for f in schema["fields"]:
        req = "REQUIRED" if f["required"] else "optional"
        ref = ""
        if "referenceTo" in f:
            ref = f" → {', '.join(f['referenceTo'])}"
        lines.append(f"  - {f['name']} ({f['type']}, {req}){ref}")

    if schema["childRelationships"]:
        lines.append("")
        lines.append("Child Relationships:")
        for r in schema["childRelationships"]:
            lines.append(f"  - {r['childSObject']} via {r['field']} [{r['name']}]")

    return "\n".join(lines)
