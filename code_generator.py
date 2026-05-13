from groq import Groq
import streamlit as st

SYSTEM_PROMPT = """You are a senior Salesforce developer and Apex code expert.
You generate production-quality Apex code following Salesforce best practices.

Rules you ALWAYS follow:
- One trigger per object, all logic in a TriggerHandler class
- Bulkify everything — assume 200 records
- No SOQL or DML inside loops
- Use with sharing on all classes
- Follow the handler → service pattern
- Meaningful variable and method names
- Include inline comments explaining non-obvious logic

When asked to generate code, you ALWAYS produce three sections:
1. The Trigger (.trigger file)
2. The TriggerHandler class (.cls file)
3. The Test Class (.cls file) with at least one positive and one negative test

Format your response EXACTLY as:
## TRIGGER: <ClassName>
```apex
<trigger code here>
```

## HANDLER: <ClassName>
```apex
<handler class code here>
```

## TEST CLASS: <ClassName>
```apex
<test class code here>
```

Do not add any explanation outside these three sections."""

def generate_apex_code(requirement: str, schema_text: str, best_practices: str) -> str:
    """Call Groq API to generate Apex trigger + handler + test class."""
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    user_prompt = f"""Generate Apex code for the following requirement:

REQUIREMENT:
{requirement}

SALESFORCE OBJECT SCHEMA:
{schema_text}

BEST PRACTICES TO FOLLOW:
{best_practices}

Generate the Trigger, TriggerHandler, and Test Class now."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,  # Low temperature for consistent code output
            max_tokens=3000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Code generation failed: {str(e)}"

def parse_code_sections(raw_output: str) -> dict:
    """Parse the LLM output into separate trigger, handler, test sections."""
    sections = {"trigger": "", "handler": "", "test": ""}
    current_section = None
    current_lines = []

    for line in raw_output.split("\n"):
        if line.startswith("## TRIGGER:"):
            if current_section and current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = "trigger"
            current_lines = []
        elif line.startswith("## HANDLER:"):
            if current_section and current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = "handler"
            current_lines = []
        elif line.startswith("## TEST CLASS:"):
            if current_section and current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = "test"
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section and current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    # Strip markdown code fences if present
    for key in sections:
        code = sections[key]
        if code.startswith("```"):
            lines = code.split("\n")
            # Remove first line (```apex or ```) and last line (```)
            code = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        sections[key] = code.strip()

    return sections
