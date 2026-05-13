import streamlit as st
from salesforce_client import get_sf_connection, get_sobject_list, get_object_schema, format_schema_for_prompt
from rag_engine import retrieve_best_practices
from code_generator import generate_apex_code, parse_code_sections

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SF Coding Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

:root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --text: #e2e8f0;
    --muted: #64748b;
    --success: #10b981;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'IBM Plex Sans', sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--sans);
    background-color: var(--bg);
    color: var(--text);
}

.main .block-container { padding: 2rem 3rem; max-width: 1400px; }

/* Header */
.agent-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem 0 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.agent-title {
    font-family: var(--mono);
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.02em;
}
.agent-subtitle {
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 0.2rem;
}
.status-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 8px var(--success);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Step labels */
.step-label {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
}

/* Panels */
.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

/* Code tabs */
.code-header {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 0.5rem 1rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    display: inline-block;
}

/* Schema display */
.schema-chip {
    display: inline-block;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.2rem 0.6rem;
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--accent);
    margin: 0.15rem;
}

/* Streamlit overrides */
.stTextArea textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}
.stButton > button {
    background: var(--accent) !important;
    color: #0a0e1a !important;
    border: none !important;
    font-family: var(--mono) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 2rem !important;
    border-radius: 4px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #00b8e0 !important;
    transform: translateY(-1px) !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface2) !important;
    border-radius: 6px 6px 0 0 !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
.stCodeBlock { border-radius: 0 0 6px 6px !important; }
div[data-testid="stExpander"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}
.stInfo { background: rgba(0, 212, 255, 0.08) !important; border-left: 3px solid var(--accent) !important; }
.stSuccess { background: rgba(16, 185, 129, 0.08) !important; border-left: 3px solid var(--success) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="agent-header">
    <div class="status-dot"></div>
    <div>
        <div class="agent-title">⚡ SF Coding Agent</div>
        <div class="agent-subtitle">Salesforce-aware Apex generator · Trigger + Handler + Test Class</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "sf" not in st.session_state:
    st.session_state.sf = None
if "sobjects" not in st.session_state:
    st.session_state.sobjects = []
if "schema" not in st.session_state:
    st.session_state.schema = None
if "generated" not in st.session_state:
    st.session_state.generated = None

# ── Layout ────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 1.6], gap="large")

with left_col:
    # ── Step 1: Connect ───────────────────────────────────────────────────────
    st.markdown('<div class="step-label">Step 1 · Connect</div>', unsafe_allow_html=True)

    if st.session_state.sf is None:
        if st.button("🔌 Connect to Salesforce Org"):
            with st.spinner("Connecting..."):
                sf = get_sf_connection()
                if sf:
                    st.session_state.sf = sf
                    st.session_state.sobjects = get_sobject_list(sf)
                    st.success(f"Connected · {len(st.session_state.sobjects)} objects loaded")
                    st.rerun()
    else:
        st.success(f"✓ Connected · {len(st.session_state.sobjects)} objects available")
        if st.button("Disconnect", type="secondary"):
            st.session_state.sf = None
            st.session_state.sobjects = []
            st.session_state.schema = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Step 2: Pick Object ───────────────────────────────────────────────────
    st.markdown('<div class="step-label">Step 2 · Select Object</div>', unsafe_allow_html=True)

    if st.session_state.sobjects:
        selected_object = st.selectbox(
            "SObject",
            options=["— select —"] + st.session_state.sobjects,
            label_visibility="collapsed",
        )

        if selected_object and selected_object != "— select —":
            if st.button("Fetch Schema"):
                with st.spinner(f"Fetching {selected_object} schema..."):
                    schema = get_object_schema(st.session_state.sf, selected_object)
                    if schema:
                        st.session_state.schema = schema
                        st.success(f"✓ {len(schema['fields'])} fields loaded")
    else:
        st.info("Connect to your org first")

    # Schema preview
    if st.session_state.schema:
        with st.expander(f"📋 {st.session_state.schema['name']} schema preview"):
            fields = st.session_state.schema["fields"][:20]
            chips = "".join([
                f'<span class="schema-chip">{f["name"]} <span style="color:#64748b">({f["type"]})</span></span>'
                for f in fields
            ])
            if len(st.session_state.schema["fields"]) > 20:
                chips += f'<span class="schema-chip" style="color:#64748b">+{len(st.session_state.schema["fields"])-20} more</span>'
            st.markdown(chips, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Step 3: Requirement ───────────────────────────────────────────────────
    st.markdown('<div class="step-label">Step 3 · Describe Requirement</div>', unsafe_allow_html=True)

    requirement = st.text_area(
        "Requirement",
        placeholder="e.g. When an Opportunity is closed-won, automatically create a follow-up Task assigned to the owner with a due date 7 days from today.",
        height=140,
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Generate ──────────────────────────────────────────────────────────────
    can_generate = (
        st.session_state.sf is not None
        and st.session_state.schema is not None
        and requirement.strip() != ""
    )

    if st.button("⚡ Generate Apex Code", disabled=not can_generate):
        with st.spinner("Fetching best practices..."):
            best_practices = retrieve_best_practices(requirement)

        with st.spinner("Generating Trigger · Handler · Test Class..."):
            schema_text = format_schema_for_prompt(st.session_state.schema)
            raw_output = generate_apex_code(requirement, schema_text, best_practices)
            st.session_state.generated = parse_code_sections(raw_output)

        st.success("✓ Code generated")
        st.rerun()

    if not can_generate and requirement.strip():
        if st.session_state.sf is None:
            st.caption("⚠ Connect to org first")
        elif st.session_state.schema is None:
            st.caption("⚠ Fetch object schema first")

# ── Right column: Output ──────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="step-label">Output · Generated Apex</div>', unsafe_allow_html=True)

    if st.session_state.generated:
        sections = st.session_state.generated
        tab1, tab2, tab3 = st.tabs([
            "⚡ Trigger",
            "🔧 Handler Class",
            "🧪 Test Class",
        ])

        with tab1:
            if sections["trigger"]:
                st.code(sections["trigger"], language="apex")
                st.download_button(
                    "↓ Download .trigger",
                    data=sections["trigger"],
                    file_name=f"{st.session_state.schema['name']}Trigger.trigger",
                    mime="text/plain",
                )
            else:
                st.info("Trigger section not found in output")

        with tab2:
            if sections["handler"]:
                st.code(sections["handler"], language="apex")
                st.download_button(
                    "↓ Download Handler.cls",
                    data=sections["handler"],
                    file_name=f"{st.session_state.schema['name']}TriggerHandler.cls",
                    mime="text/plain",
                )
            else:
                st.info("Handler section not found in output")

        with tab3:
            if sections["test"]:
                st.code(sections["test"], language="apex")
                st.download_button(
                    "↓ Download Test.cls",
                    data=sections["test"],
                    file_name=f"{st.session_state.schema['name']}TriggerHandlerTest.cls",
                    mime="text/plain",
                )
            else:
                st.info("Test class section not found in output")

    else:
        # Empty state
        st.markdown("""
        <div style="
            border: 1px dashed #1e2d45;
            border-radius: 8px;
            padding: 4rem 2rem;
            text-align: center;
            margin-top: 1rem;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">⚡</div>
            <div style="font-family: 'IBM Plex Mono', monospace; color: #64748b; font-size: 0.85rem;">
                Connect → Select Object → Describe Requirement → Generate
            </div>
            <div style="color: #374151; font-size: 0.8rem; margin-top: 0.5rem;">
                Your Trigger, Handler, and Test Class will appear here
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="border-top: 1px solid #1e2d45; padding-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
    <span style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #374151;">
        SF Coding Agent · Infoglen AI CoE · POC v1.0
    </span>
    <span style="font-size: 0.7rem; color: #374151;">
        Groq · Llama 3.1 70B · Chroma · Streamlit
    </span>
</div>
""", unsafe_allow_html=True)
