# SF Coding Agent — Infoglen AI CoE POC

A Salesforce-aware Apex code generator. Connects live to your Salesforce org, fetches object schema, and generates a Trigger + TriggerHandler + Test Class from a plain English requirement.

## Stack
- **LLM:** Groq API (Llama 3.1 70B) — free tier
- **RAG:** Chroma in-memory + sentence-transformers (all-MiniLM-L6-v2)
- **Salesforce:** simple-salesforce via REST API
- **UI:** Streamlit

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-org/sf-coding-agent.git
cd sf-coding-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure secrets
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your credentials
```

You need:
- **Groq API key** — free at groq.com
- **Salesforce credentials** — username, password, security token from your SDO/sandbox

To get your Salesforce security token:
1. Login to Salesforce
2. My Settings → Personal → Reset My Security Token
3. Check your email

### 4. Run locally
```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Push code to a **public** GitHub repo (no secrets in code)
2. Go to share.streamlit.io
3. Connect your GitHub repo, set main file as `app.py`
4. Under **Advanced settings → Secrets**, paste your secrets in TOML format:
```toml
SF_USERNAME = "your-username"
SF_PASSWORD = "your-password"
SF_SECURITY_TOKEN = "your-token"
SF_DOMAIN = "login"
GROQ_API_KEY = "your-groq-key"
```
5. Deploy

## Usage

1. Click **Connect to Salesforce Org**
2. Select an SObject from the dropdown
3. Click **Fetch Schema**
4. Type your requirement in plain English
5. Click **Generate Apex Code**
6. Download the generated Trigger, Handler, and Test Class files

## Security Notes
- Credentials stored in Streamlit Secrets only — never in code
- Agent is read-only — it fetches metadata, never writes to your org
- Only schema metadata (field names, types) is sent to Groq — no record data
- Do not enter client-specific information into the requirement field

## Project Structure
```
sf-coding-agent/
├── app.py                  # Streamlit UI
├── salesforce_client.py    # Salesforce REST API connectivity
├── rag_engine.py           # Chroma RAG + best practices
├── code_generator.py       # Groq LLM + prompt engineering
├── requirements.txt
├── .streamlit/
│   ├── config.toml         # Theme config
│   └── secrets.toml        # Your credentials (gitignored)
└── .gitignore
```
