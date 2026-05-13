import streamlit as st
from salesforce_client import SalesforceClient
from rag_engine import RAGEngine
from code_generator import CodeGenerator

st.set_page_config(
    page_title="SF Coding Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap');
:root {
    --bg: #0a0e1a; --surface: #111827; --border: #1e2d40;
    --accent: #00d4ff; --accent2: #7c3aed; --text: #e2e8f0;
    --muted: #64748b; --success: #10b981;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important; color: var(--text) !important;
    font-family: 'Syne', sans-serif !important;
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,212,255,0.07) 0%, transparent 60%),
                radial-gradient(ellipse 60% 40% at 80% 110%, rgba(124,58,237,0.07) 0%, transparent 60%),
                var(--bg) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; }
.hero-title {
    font-family: 'Syne', sans-serif; font-size: 2.4rem; font-weight: 800;
    background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.2rem; line-height: 1.1;
}
.hero-sub { color: var(--muted); font-size: 0.9rem; font-family: 'JetBrains Mono', monospace; margin-bottom: 1.5rem; }
.step-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--accent);
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.4rem;
}
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 1rem; border-left: 3px solid var(--accent); }
.warning-box {
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25);
    border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.82rem; color: #fcd34d;
    font-family: 'JetBrains Mono', monospace; margin-bottom: 1rem;
}
.stTextArea textarea {
    background: #0d1525 !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.88rem !important;
}
.stTextArea textarea:focus { border-color: var(--accent) !important; }
.stSelectbox > div > div { background: #0d1525 !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; }
.stButton > button {
    background: linear-gradient(135deg, #00d4ff, #7c3aed) !important; color: white !important;
    border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important; font-size: 0.9rem !important; padding: 0.6rem 1.8rem !important;
}
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--muted) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; }
.stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# Session state
for key, default in {
    "sf_connected": False, "sf_client": None, "rag_ready": False,
    "rag_engine": None, "sobjects": [], "selected_object": None,
    "schema": None, "generated": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Header
st.markdown('<div class="hero-title">⚡ SF Coding Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">requirement → apex trigger · handler · test class</div>', unsafe_allow_html=True)
st.markdown('<div class="warning-box">⚠️ Internal use only — do not enter client org credentials or client-specific data.</div>', unsafe_allow_html=True)
st.markdown('<hr>', unsafe_allow_html=True)

# ── STEP 1: CONNECT ───────────────────────────────────────────────────────────
st.markdown('<div class="step-label">Step 01 — Connect to Salesforce</div>', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)

if st.session_state.sf_connected:
    st.success(f"✅ Connected — {len(st.session_state.sobjects)} objects loaded")
else:
    col1, col2 = st.columns(2)
    with col1:
        sf_username        = st.text_input("Username", placeholder="user@sdo.org")
        sf_password        = st.text_input("Password", type="password")
        sf_token           = st.text_input("Security Token", type="password")
    with col2:
        sf_instance        = st.text_input("Instance URL", placeholder="https://yourorg.my.salesforce.com")
        sf_consumer_key    = st.text_input("Consumer Key", type="password")
        sf_consumer_secret = st.text_input("Consumer Secret", type="password")

    if st.button("Connect to Salesforce"):
        if not all([sf_username, sf_password, sf_token, sf_instance]):
            st.error("All four fields are required.")
        else:
            with st.spinner("Connecting..."):
                try:
                     client = SalesforceClient(
                        sf_username, sf_password, sf_token,
                        sf_instance, sf_consumer_key, sf_consumer_secret
                    )
                    objects = client.get_sobject_list()
                    st.session_state.sf_client    = client
                    st.session_state.sobjects     = objects
                    st.session_state.sf_connected = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# ── STEP 2: RAG ───────────────────────────────────────────────────────────────
if st.session_state.sf_connected:
    st.markdown('<div class="step-label">Step 02 — Load Best Practices</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state.rag_ready:
        st.success("✅ Knowledge base ready")
    else:
        uploaded_files = st.file_uploader("Upload best practices docs (optional)", type=["txt","md"], accept_multiple_files=True)
        if st.button("Load Knowledge Base"):
            with st.spinner("Embedding documents..."):
                try:
                    rag = RAGEngine()
                    if uploaded_files:
                        for f in uploaded_files:
                            rag.add_document(f.name, f.read().decode("utf-8"))
                    else:
                        rag.load_defaults()
                    st.session_state.rag_engine = rag
                    st.session_state.rag_ready  = True
                    st.rerun()
                except Exception as e:
                    st.error(f"RAG setup failed: {e}")
        st.caption("No docs? Click Load to use built-in Salesforce best practices.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── STEP 3: GENERATE ──────────────────────────────────────────────────────────
if st.session_state.sf_connected and st.session_state.rag_ready:
    st.markdown('<div class="step-label">Step 03 — Generate Code</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        requirement = st.text_area("Requirement", placeholder="e.g. When an Opportunity is closed won, create a follow-up Task assigned to the owner due 3 days later.", height=120)

    with col_right:
        object_names = [o["name"] for o in st.session_state.sobjects]
        selected_obj = st.selectbox("SObject", options=["— select —"] + object_names)

        if selected_obj and selected_obj != "— select —":
            if st.session_state.selected_object != selected_obj:
                with st.spinner(f"Fetching {selected_obj} schema..."):
                    try:
                        schema = st.session_state.sf_client.get_object_schema(selected_obj)
                        st.session_state.schema          = schema
                        st.session_state.selected_object = selected_obj
                    except Exception as e:
                        st.error(f"Schema fetch failed: {e}")

        if st.session_state.schema:
            st.caption(f"↳ {len(st.session_state.schema.get('fields', []))} fields loaded")

    if st.session_state.schema:
        with st.expander(f"📋 {selected_obj} schema preview"):
            fields = st.session_state.schema.get("fields", [])[:20]
            for f in fields:
                st.caption(f"`{f['name']}` ({f['type']}) — {f.get('label','')}")

    groq_key = st.text_input("Groq API Key", type="password", help="Get free key at console.groq.com")

    if st.button("⚡ Generate Code"):
        if not requirement.strip():
            st.error("Enter a requirement.")
        elif not st.session_state.schema:
            st.error("Select an SObject.")
        elif not groq_key.strip():
            st.error("Enter your Groq API key.")
        else:
            with st.spinner("Retrieving best practices..."):
                context = st.session_state.rag_engine.query(requirement)
            with st.spinner("Generating Apex via Groq (Llama 3.1 70B)..."):
                try:
                    gen    = CodeGenerator(groq_key.strip())
                    result = gen.generate(
                        requirement=requirement,
                        sobject=selected_obj,
                        schema=st.session_state.schema,
                        best_practices_context=context,
                    )
                    st.session_state.generated = result
                except Exception as e:
                    st.error(f"Generation failed: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── OUTPUT ────────────────────────────────────────────────────────────────────
if st.session_state.generated:
    g = st.session_state.generated
    st.markdown('<div class="step-label">Output — Generated Code</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Trigger", "🔧 Handler Class", "🧪 Test Class", "📝 Notes"])
    selected_obj = st.session_state.selected_object or "Object"

    with tab1:
        st.code(g.get("trigger",""), language="java")
        st.download_button("Download Trigger", g.get("trigger",""), file_name=f"{selected_obj}Trigger.trigger", mime="text/plain")
    with tab2:
        st.code(g.get("handler",""), language="java")
        st.download_button("Download Handler", g.get("handler",""), file_name=f"{selected_obj}TriggerHandler.cls", mime="text/plain")
    with tab3:
        st.code(g.get("test_class",""), language="java")
        st.download_button("Download Test Class", g.get("test_class",""), file_name=f"{selected_obj}TriggerHandlerTest.cls", mime="text/plain")
    with tab4:
        notes = g.get("notes","")
        if notes:
            st.info(notes)

    if st.button("🔄 New Generation"):
        st.session_state.generated = None
        st.session_state.selected_object = None
        st.session_state.schema = None
        st.rerun()
