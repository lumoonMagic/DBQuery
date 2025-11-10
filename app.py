# app.py
"""
Streamlit entrypoint for Streamlit Graph + SQL Agent (POC)

- Default theme: Aurora Purple (configurable)
- Demo vs Real toggle (Demo safe to run without external services)
- Configuration Cockpit (OTP demo gating)
- Query generation slot + expert SQL preview
- Upload grounding docs -> vector pipeline (pluggable)
- Neo4j sync hook (pluggable)
- Databricks execution (pluggable)
- PPT export (pluggable)
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

# --- Defensive imports (modules are created separately) ---
try:
    from modules import databricks_connector, neo4j_sync, vector_engine, export_ppt
except Exception:
    # If modules are not present yet, we define minimal fallbacks to keep demo mode working.
    databricks_connector = None
    neo4j_sync = None
    vector_engine = None
    export_ppt = None

# -----------------------
# App configuration
# -----------------------
st.set_page_config(layout="wide", page_title="AI Supply Chain Insight Assistant", initial_sidebar_state="expanded")

APP_DIR = Path(__file__).parent
GROUNDING_DIR = APP_DIR / "grounding_files"
GROUNDING_DIR.mkdir(exist_ok=True)

# -----------------------
# Theme palettes
# -----------------------
THEMES = {
    "Aurora Purple": {
        "bg": "#0f1724",
        "card": "#1f2340",
        "text": "#E6E7FF",
        "accent": "#9B5CF6"
    },
    "Carbon Black": {
        "bg": "#0b0b0d",
        "card": "#151515",
        "text": "#F7F7F7",
        "accent": "#D4AF37"
    },
    "Azure Cloud": {
        "bg": "#f6fbff",
        "card": "#ffffff",
        "text": "#0f1724",
        "accent": "#0b74de"
    },
    "Google Material": {
        "bg": "#ffffff",
        "card": "#f3f4f6",
        "text": "#111827",
        "accent": "#3b82f6"
    },
    "Databricks Red": {
        "bg": "#0b0b0f",
        "card": "#1b1b1f",
        "text": "#f7f7f7",
        "accent": "#ea4335"
    }
}

# default theme
DEFAULT_THEME = "Aurora Purple"

# helper to inject theme CSS
def apply_theme(theme_name: str):
    p = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    css = f"""
    <style>
    .reportview-container {{ background: {p['bg']}; color: {p['text']}; }}
    .stApp {{ background: {p['bg']}; color: {p['text']}; }}
    .card {{ background: {p['card']}; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
    .accent {{ color: {p['accent']}; }}
    .stButton>button {{ background: linear-gradient(90deg, {p['accent']}, #6b21a8); color: white; }}
    .kpi {{ padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.02); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# apply default theme (initial)
theme_choice_default = DEFAULT_THEME
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = theme_choice_default
apply_theme(st.session_state.ui_theme)

# -----------------------
# Session initialization
# -----------------------
if "history" not in st.session_state:
    st.session_state.history = []           # chat history and actions
if "last_df" not in st.session_state:
    st.session_state.last_df = None
if "pinned" not in st.session_state:
    st.session_state.pinned = []
if "config" not in st.session_state:
    st.session_state.config = {}            # live config loaded from secrets or saved config
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = True      # default to demo

# -----------------------
# Sidebar: Configuration Cockpit
# -----------------------
with st.sidebar:
    st.title("Configuration Cockpit")
    st.markdown("**Mode**")
    demo_toggle = st.checkbox("DEMO MODE (safe)", value=st.session_state.demo_mode)
    st.session_state.demo_mode = demo_toggle

    st.markdown("---")
    st.subheader("Admin Access (OTP)")
    admin_email = st.text_input("Admin email to send OTP (demo)")
    if st.button("Send OTP (demo)"):
        # demo OTP printed to log (replace with SMTP in prod)
        demo_otp = "123456"
        st.session_state._demo_otp = demo_otp
        st.success("OTP generated and displayed in console (demo).")
        st.write(f"Demo OTP: {demo_otp}")  # in demo show OTP
    otp_val = st.text_input("Enter OTP to unlock admin")
    if st.button("Verify OTP"):
        if otp_val and otp_val == st.session_state.get("_demo_otp"):
            st.session_state.admin_unlocked = True
            st.success("Admin unlocked")
        else:
            st.error("Invalid OTP")

    # theme selector
    st.markdown("---")
    st.subheader("UI Theme")
    theme = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.ui_theme))
    if theme != st.session_state.ui_theme:
        st.session_state.ui_theme = theme
        apply_theme(theme)
        st.experimental_rerun()

    # model & vector DB config (store in-state; persistence module will save encrypted)
    st.markdown("---")
    st.subheader("Model & Vector DB")
    model_provider = st.selectbox("Model Provider", ["Gemini-2.5-Flash (GenAI)", "Other"])
    model_endpoint = st.text_input("Model endpoint (for embeddings & LLM calls)", value=st.session_state.config.get("model_endpoint",""))
    model_key = st.text_input("Model API Key (store encrypted)", type="password", value=st.session_state.config.get("model_key",""))
    vec_provider = st.selectbox("Vector DB Provider", ["DEMO","Chroma","Pinecone","Qdrant","FAISS"], index=0)
    vec_api_key = st.text_input("Vector DB API Key", type="password", value=st.session_state.config.get("vec_api_key",""))
    if st.button("Save Config (local POC)"):
        # persist into session config; modules should provide secure saving hooks
        st.session_state.config.update({
            "model_endpoint": model_endpoint,
            "model_key": model_key,
            "vec_provider": vec_provider,
            "vec_api_key": vec_api_key
        })
        st.success("Config saved to session (POC). Persist to secure store for production.")

    st.markdown("---")
    st.markdown("**Quick Links**")
    st.markdown("- Upload Grounding Docs in main UI")
    st.markdown("- Use Demo Mode for safe demo")
    st.markdown("---")
    st.markdown("Streamlit Cloud: set secrets under App Settings → Secrets")

# -----------------------
# Main layout: top header & 2-column layout
# -----------------------
st.markdown(f"# <span class='accent'>AI Supply Chain Insight Assistant</span>", unsafe_allow_html=True)
left_col, right_col = st.columns([2, 3])

# ---- Left: Chat / Input ----
with left_col:
    st.markdown("### 💬 Chat & Query")
    prompt = st.text_area("Natural language question (e.g. 'Top 5 low performing vendors in US')", height=120)
    expert_mode = st.checkbox("Expert mode (show SQL before execution)")
    if st.button("Generate SQL (call Query Generator)"):
        # Placeholder: call your SQL-generator or adapter
        if st.session_state.demo_mode:
            # demo generator: simple mapping (keeps POC independent)
            if "vendor" in prompt.lower() and "top" in prompt.lower():
                sql = "SELECT vendor_id, vendor_name, on_time_rate FROM demo.vendors ORDER BY on_time_rate DESC LIMIT 5"
            elif "procurement" in prompt.lower() and "sales" in prompt.lower():
                sql = "-- DEMO: procurement vs sales join"
            else:
                sql = "-- DEMO: please refine prompt (try 'top vendors' or 'procurement vs sales')"
            st.session_state.generated_sql = sql
            st.success("SQL generated (demo)")
        else:
            # REAL: call your query-generator adapter module here (TO BE IMPLEMENTED)
            try:
                # modules.databricks_connector or an agent module should implement this
                from modules.agent_adapter import generate_sql_for_user
                out = generate_sql_for_user(prompt, context={})
                st.session_state.generated_sql = out.get("sql")
                st.success("SQL generated (real agent)")
            except Exception as e:
                st.error(f"Query generator not configured: {e}")

    gen_sql = st.text_area("Generated SQL (editable)", value=st.session_state.get("generated_sql",""), height=160)
    if expert_mode and gen_sql:
        with st.expander("Generated SQL (expert view)"):
            st.code(gen_sql, language="sql")

    # Execution controls
    st.markdown("#### Execution")
    exec_sync = st.button("Execute SQL (sync)")
    exec_async = st.button("Execute SQL (async placeholder)")  # async placeholder (we're not running Celery here)
    if exec_sync:
        if st.session_state.demo_mode:
            # Demo execution: we will use small local demo dataset
            demo_vendors = pd.DataFrame({
                "vendor_id": ["V001","V002","V003","V004"],
                "vendor_name": ["Alpha Logistics","Beta Supplies","Gamma Traders","Delta Corp"],
                "on_time_rate": [0.92,0.78,0.88,0.65],
                "defect_rate": [0.01,0.03,0.02,0.04],
                "avg_cost":[120,110,105,150]
            })
            # simple SQL parser to detect vendor query
            s = gen_sql.strip().lower()
            if "on_time_rate" in s or "vendor" in s:
                df = demo_vendors.sort_values("on_time_rate", ascending=False).head(10)
            else:
                df = pd.DataFrame({"message":["DEMO execution completed. Replace with real connector."]})
            st.session_state.last_df = df
            st.success("Demo SQL executed")
        else:
            # REAL execution: call the databricks connector module
            try:
                if databricks_connector is None:
                    st.error("Databricks connector module missing. Add modules/databricks_connector.py")
                else:
                    cfg = st.session_state.config
                    # databricks_connector.run_sql should implement the real run and return a pandas.DataFrame
                    df = databricks_connector.run_sql(gen_sql, config=cfg)
                    st.session_state.last_df = df
                    st.success("SQL executed on Databricks")
            except Exception as e:
                st.error(f"Databricks execution failed: {e}")

    if exec_async:
        st.info("Async execution placeholder. For long-running tasks use Celery/Redis (not enabled in this POC).")

# ---- Right: Results & Insights ----
with right_col:
    st.markdown("### 📊 Results & Insights")
    if st.session_state.get("last_df") is None:
        st.info("No results yet. Run a query on the left.")
    else:
        df = st.session_state.last_df
        st.dataframe(df)
        # quick plot suggestions
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            st.markdown("**Suggested chart**")
            chart_col = numeric_cols[0]
            st.bar_chart(df.set_index(df.columns[1])[chart_col]) if df.shape[0] > 0 else None
        # pin insight
        if st.button("Pin this insight"):
            st.session_state.pinned.append({
                "title": f"Pin: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "summary": f"Query: {gen_sql}",
                "df": df
            })
            st.success("Insight pinned")

    st.markdown("### 📁 Pinned Insights")
    for i, card in enumerate(st.session_state.pinned[::-1]):
        st.markdown(f"**{card.get('title')}**")
        st.write(card.get("summary"))
        st.table(card.get("df").head(5))
        if st.button(f"Export slide #{i}"):
            # export single slide via export_ppt module if available
            try:
                if export_ppt:
                    path = export_ppt.create_pptx_from_insights([card], out_path=f"insight_{i}.pptx")
                    with open(path, "rb") as f:
                        st.download_button("Download PPTX", f.read(), file_name=path)
                else:
                    st.error("Export module missing (modules/export_ppt.py).")
            except Exception as e:
                st.error(f"PPT export error: {e}")

# -----------------------
# Upload grounding docs & vector embed
# -----------------------
st.markdown("---")
st.header("🔎 Grounding Documents & Vector Memory")
uploads = st.file_uploader("Upload JSON/PDF/CSV/PNG for grounding", accept_multiple_files=True)
if uploads:
    st.info(f"{len(uploads)} files uploaded. Storing and embedding...")
    try:
        if vector_engine is None:
            # fallback: save files locally for demo
            saved = []
            for f in uploads:
                dest = GROUNDING_DIR / f.name
                with open(dest, "wb") as out:
                    out.write(f.getbuffer())
                saved.append({"name": f.name, "path": str(dest), "provider": "DEMO"})
            st.json(saved)
            st.success("Files saved (demo)")
        else:
            cfg = st.session_state.config.get("vec_config", {})
            stored_meta = vector_engine.store_documents_and_embeddings(uploads, vec_config=cfg)
            st.json(stored_meta)
            st.success("Stored & embedded to vector DB")
    except Exception as e:
        st.error(f"Embedding/storage failed: {e}")

# -----------------------
# Neo4j sync panel (admin)
# -----------------------
st.markdown("---")
st.header("🔗 Neo4j Schema / Ontology (admin)")
if st.session_state.get("admin_unlocked", False):
    if st.button("Extract Databricks metadata and push to Neo4j (dry-run)"):
        st.info("Dry-run: will simulate metadata extraction (replace with real implementation)")
        # TODO: call databricks metadata -> build schema object
        schema = {"demo_table": ["col1","col2","col3"]}
        st.json(schema)
    if st.button("Push schema to Neo4j (real)"):
        if neo4j_sync is None:
            st.error("Neo4j sync module missing (modules/neo4j_sync.py)")
        else:
            schema_obj = {"demo_table": ["col1","col2","col3"]}  # replace with real metadata
            ok = neo4j_sync.sync_schema_to_neo4j(schema_obj, config=st.session_state.config)
            if ok:
                st.success("Schema pushed to Neo4j")
            else:
                st.error("Neo4j push failed")
else:
    st.info("Unlock the admin cockpit to enable Neo4j sync and advanced actions")

# -----------------------
# Export full report (ppt/pdf)
# -----------------------
st.markdown("---")
st.header("📤 Export: Board-ready Report")
if st.button("Export pinned insights to PPTX (demo)"):
    if export_ppt is None:
        st.error("Export module missing (modules/export_ppt.py)")
    else:
        try:
            path = export_ppt.create_pptx_from_insights(st.session_state.pinned or [], out_path="report.pptx")
            with open(path, "rb") as f:
                st.download_button("Download PPTX", f.read(), file_name="report.pptx")
        except Exception as e:
            st.error(f"Export failed: {e}")

# -----------------------
# Footer / help
# -----------------------
st.markdown("---")
st.caption("POC: Demo mode enabled by default. Replace module placeholders under /modules for full REAL integration.")
