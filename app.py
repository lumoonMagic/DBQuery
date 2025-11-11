# app.py
"""
DBQuery - Enterprise-style Streamlit UI (polished)
- Central prompt with Ask -> Review -> Execute flow
- Canvas area: Table | Chart | PPT | PDF | Logs
- Demo mode follows demo_script prompts
- Admin Configuration Cockpit captures Databricks, Neo4j, Vector, Gemini, SMTP
- Theme switching with correct contrast
- Defensive imports: app runs in demo mode without external libs
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from io import BytesIO

# App paths
ROOT = Path(__file__).parent
DEMO_DIR = ROOT / "demo_data"
GROUNDING_DIR = ROOT / "grounding_files"
GROUNDING_DIR.mkdir(exist_ok=True)
CONFIG_FILE = ROOT / "config" / "settings.json"
CONFIG_FILE.parent.mkdir(exist_ok=True)

# Defensive imports (modules may be optional)
try:
    from modules import databricks_connector, neo4j_sync, export_ppt
except Exception:
    databricks_connector = None
    neo4j_sync = None
    export_ppt = None

try:
    from modules import vector_engine
except Exception:
    vector_engine = None

# -----------------------------
# UI constants & themes
# -----------------------------
THEMES = {
    "Aurora Purple": {"bg": "#0f1724", "card": "#1f2340", "text": "#E6E7FF", "muted": "#cbd5ff", "accent": "#9B5CF6"},
    "Light Enterprise": {"bg": "#FFFFFF", "card": "#F7FAFC", "text": "#0F1724", "muted": "#475569", "accent": "#0B74DE"},
    "Carbon Black": {"bg": "#0b0b0d", "card": "#151515", "text": "#F7F7F7", "muted": "#CCCCCC", "accent": "#D4AF37"},
}

DEFAULT_THEME = "Aurora Purple"

# Apply safe theme CSS (ensures contrast)
def apply_theme(theme_name: str):
    p = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    text = p["text"]
    muted = p["muted"]
    accent = p["accent"]
    card = p["card"]
    bg = p["bg"]
    css = f"""
    <style>
      body {{ background-color: {bg}; color: {text}; }}
      .stApp {{ background-color: {bg}; color: {text}; }}
      .card {{ background: {card}; border-radius:8px; padding:12px; }}
      .accent {{ color: {accent}; font-weight:600; }}
      .muted {{ color: {muted}; }}
      .canvas-tab {{ background: {card}; padding:10px; border-radius:8px; }}
      /* ensure buttons readable */
      button[role="button"] {{ background: linear-gradient(90deg, {accent}, #6b21a8); color: white; }}
      /* readable code / pre blocks */
      .stCodeBlock pre {{ color: {text}; background: rgba(0,0,0,0.08); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# -----------------------------
# Session State init
# -----------------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.ui_theme = DEFAULT_THEME
    st.session_state.demo_mode = True
    st.session_state.admin_unlocked = False
    st.session_state.generated_sql = ""
    st.session_state.sql_rationale = ""
    st.session_state.last_df = None
    st.session_state.pinned = []
    st.session_state.history = []
    st.session_state.config = {}
    # load config file fallback if exists
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        st.session_state.config = cfg
    except Exception:
        pass

apply_theme(st.session_state.ui_theme)

# -----------------------------
# Helper functions
# -----------------------------
def save_session_config():
    """Persist session config to local config file for local use (not secure)."""
    try:
        CONFIG_FILE.write_text(json.dumps(st.session_state.config, indent=2))
        st.success("Config saved to local file (config/settings.json). Use secrets for production.")
    except Exception as e:
        st.error(f"Unable to save config file: {e}")

def load_demo_df_for_sql(sql_text: str):
    """Simple mapping for demo SQL -> demo DataFrames"""
    s = (sql_text or "").lower()
    vendors_path = DEMO_DIR / "vendor_performance.json"
    batches_path = DEMO_DIR / "supply_chain_sample.csv"
    # Robust checks
    if "vendor" in s and "top" in s:
        try:
            df = pd.read_json(vendors_path)
            return df.sort_values("on_time_delivery_rate", ascending=False).reset_index(drop=True)
        except Exception:
            return pd.DataFrame({"message":["demo vendors missing"]})
    if "batch" in s or "supply" in s or "batch_id" in s:
        try:
            df = pd.read_csv(batches_path)
            return df
        except Exception:
            return pd.DataFrame({"message":["demo batches missing"]})
    # default demo response
    return pd.DataFrame({"message":["Demo: no mapped SQL - try 'top vendors' or 'trace batch'"]})

def generate_demo_sql_and_rationale(prompt: str):
    p = prompt.lower()
    if "top" in p and "vendor" in p:
        sql = "SELECT vendor_id, vendor_name, on_time_delivery_rate FROM demo_vendors ORDER BY on_time_delivery_rate DESC LIMIT 5"
        rationale = "Selecting vendor_id and on_time_delivery_rate to rank vendors by delivery performance."
    elif "trace" in p and "batch" in p:
        sql = "SELECT batch_id, material_id, vendor_id, status FROM demo_batches WHERE batch_id LIKE 'B2025%'"
        rationale = "Retrieve batch lineage details for matching batch_id pattern."
    elif "insulin" in p and "delay" in p:
        sql = "SELECT batch_id, vendor_id, status, received_qty, produced_qty FROM demo_batches WHERE material_name ILIKE '%insulin%'"
        rationale = "Filter batches by material_name and show production/receipt quantities to spot delays."
    else:
        sql = "-- DEMO: refine prompt (try 'top vendors', 'trace batch', or 'insulin delays')"
        rationale = "Could not confidently map to a demo SQL. Please refine."
    return sql, rationale

def clear_generated():
    st.session_state.generated_sql = ""
    st.session_state.sql_rationale = ""

# -----------------------------
# Layout: Header
# -----------------------------
st.markdown(
    f"""
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <h2 class='accent'>DBQuery — Pharma Data Copilot</h2>
        <div class='muted'>Material flow & vendor intelligence — Demo & Real modes</div>
      </div>
      <div>
        <small class='muted'>Mode: <b>{'DEMO' if st.session_state.demo_mode else 'REAL'}</b></small>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Main columns: Left Nav | Center Chat | Right Canvas
# -----------------------------
left_col, center_col, right_col = st.columns([1, 2, 2], gap="large")

# ---- Left Nav (history, pinned, admin)
with left_col:
    st.markdown("### Navigation")
    st.markdown("**Quick Actions**")
    if st.button("Clear Pinned"):
        st.session_state.pinned = []
    st.markdown("---")
    st.markdown("**Pinned Insights**")
    for idx, pcard in enumerate(st.session_state.pinned[::-1]):
        st.write(f"**{pcard['title']}**")
        st.caption(pcard.get("summary",""))
    st.markdown("---")
    st.markdown("**History**")
    for h in st.session_state.history[-8:][::-1]:
        st.write(h if isinstance(h, str) else str(h))
    st.markdown("---")
    # Admin quick link
    with st.expander("Admin / Config"):
        st.write("Open full Configuration Cockpit in sidebar to edit details.")

# ---- Center: Chat & SQL flow
with center_col:
    st.markdown("### Ask your data")
    prompt = st.text_area("Enter natural language question (short & actionable)", height=120, key="prompt_box")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("Generate SQL"):
            if st.session_state.demo_mode:
                sql, rationale = generate_demo_sql_and_rationale(prompt)
                st.session_state.generated_sql = sql
                st.session_state.sql_rationale = rationale
                st.session_state.history.append(f"GenSQL: {prompt[:80]}")
                st.success("SQL generated (demo). Review and execute.")
            else:
                # placeholder for real generator
                st.error("Real generator not configured in POC.")
    with col2:
        if st.button("Refine SQL"):
            # Quick refine simulation: append WHERE clause in demo
            if st.session_state.generated_sql:
                st.session_state.generated_sql += " -- refined"
                st.info("SQL refined (demo).")
    with col3:
        if st.button("Clear"):
            clear_generated()

    st.markdown("#### SQL Preview & Rationale")
    if st.session_state.generated_sql:
        st.code(st.session_state.generated_sql, language="sql")
        st.markdown(f"**Rationale:** {st.session_state.sql_rationale}")
    else:
        st.info("No SQL generated yet. Click Generate SQL.")

    # Execution controls
    exec_col1, exec_col2 = st.columns([1,1])
    with exec_col1:
        if st.button("Review Query"):
            # show a modal-like expander with explanation (demo)
            with st.expander("Query Review (explainability)"):
                st.write("Query explanation / safety checks:")
                st.write(st.session_state.sql_rationale or "No rationale available.")
    with exec_col2:
        if st.button("Execute Query"):
            if not st.session_state.generated_sql:
                st.error("No SQL to execute. Generate SQL first.")
            else:
                if st.session_state.demo_mode:
                    df = load_demo_df_for_sql(st.session_state.generated_sql)
                    st.session_state.last_df = df
                    st.success("Query executed in DEMO mode.")
                    st.session_state.history.append(f"ExecSQL: {st.session_state.generated_sql[:120]}")
                else:
                    # Real execution path
                    if databricks_connector is None:
                        st.error("Databricks connector not available in this POC.")
                    else:
                        try:
                            df = databricks_connector.run_sql(st.session_state.generated_sql, config=st.session_state.config)
                            st.session_state.last_df = df
                            st.success("Query executed on Databricks.")
                            st.session_state.history.append(f"ExecSQL: REAL - {st.session_state.generated_sql[:120]}")
                        except Exception as e:
                            st.error(f"Execution error: {e}")
    st.markdown("---")
    st.markdown("### Actions")
    act1, act2, act3 = st.columns([1,1,1])
    with act1:
        if st.button("Pin Insight"):
            if st.session_state.last_df is not None:
                st.session_state.pinned.append({
                    "title": f"Insight {time.strftime('%Y-%m-%d %H:%M')}",
                    "summary": st.session_state.generated_sql,
                    "df": st.session_state.last_df
                })
                st.success("Pinned.")
            else:
                st.error("No result to pin.")
    with act2:
        if st.button("Export Pinned to PPTX (demo)"):
            if export_ppt is None:
                st.error("Export module missing.")
            else:
                try:
                    path = export_ppt.create_pptx_from_insights(st.session_state.pinned or [], out_path="report_demo.pptx")
                    with open(path, "rb") as f:
                        st.download_button("Download PPTX", f.read(), file_name="report_demo.pptx")
                except Exception as e:
                    st.error(f"PPT export failed: {e}")
    with act3:
        if st.button("Download Last Result CSV"):
            if st.session_state.last_df is not None:
                csv = st.session_state.last_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv, file_name="last_result.csv", mime="text/csv")
            else:
                st.error("Nothing to download.")

# ---- Right: Canvas (Tabs) ----
with right_col:
    st.markdown("### Canvas")
    tab = st.radio("", ["Table", "Chart", "PPT", "PDF", "Logs"], index=0, horizontal=True)
    if tab == "Table":
        st.markdown("#### Table View")
        if st.session_state.last_df is None:
            st.info("No table to show. Execute a query.")
        else:
            st.dataframe(st.session_state.last_df)
    elif tab == "Chart":
        st.markdown("#### Chart View")
        if st.session_state.last_df is None:
            st.info("No chart to show.")
        else:
            df = st.session_state.last_df
            numeric = df.select_dtypes(include="number").columns.tolist()
            if numeric and df.shape[0] > 0:
                col_y = numeric[0]
                try:
                    st.line_chart(df.set_index(df.columns[0])[col_y])
                except Exception:
                    st.bar_chart(df[col_y])
            else:
                st.info("No numeric columns available for charting.")
    elif tab == "PPT":
        st.markdown("#### PPT Export (preview)")
        st.info("Use 'Export Pinned to PPTX' in Actions to create PPTX.")
    elif tab == "PDF":
        st.markdown("#### PDF Viewer")
        st.info("Upload a PDF in Grounding Documents to preview here (not implemented in POC).")
    else:
        st.markdown("#### Logs")
        for h in st.session_state.history[::-1]:
            st.markdown(f"- {h}")

# -----------------------------
# Sidebar: Detailed Configuration Cockpit (expanded)
# -----------------------------
with st.sidebar:
    st.markdown("### Configuration Cockpit (Admin)")
    st.markdown("**Mode & Theme**")
    demo_mode_checkbox = st.checkbox("DEMO MODE (safe)", value=st.session_state.demo_mode)
    st.session_state.demo_mode = demo_mode_checkbox
    theme_choice = st.selectbox("UI Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.ui_theme))
    if theme_choice != st.session_state.ui_theme:
        st.session_state.ui_theme = theme_choice
        apply_theme(theme_choice)
        st.success("Theme applied.")

    st.markdown("---")
    st.markdown("#### Databricks Configuration")
    st.session_state.config.setdefault("databricks", {})
    db = st.session_state.config["databricks"]
    db["host"] = st.text_input("Databricks Host (https://...)", value=db.get("host",""))
    db["http_path"] = st.text_input("Databricks HTTP Path", value=db.get("http_path",""))
    db["token"] = st.text_input("Databricks PAT (store secrets in cloud!)", value=db.get("token",""), type="password")
    db["warehouse_id"] = st.text_input("SQL Warehouse ID / Name", value=db.get("warehouse_id",""))
    db["cluster_id"] = st.text_input("Cluster ID (for Jobs API)", value=db.get("cluster_id",""))

    st.markdown("---")
    st.markdown("#### Neo4j Configuration")
    st.session_state.config.setdefault("neo4j", {})
    n = st.session_state.config["neo4j"]
    n["uri"] = st.text_input("Neo4j URI (bolt://host:7687)", value=n.get("uri",""))
    n["user"] = st.text_input("Neo4j User", value=n.get("user",""))
    n["password"] = st.text_input("Neo4j Password", value=n.get("password",""), type="password")
    n["encrypt"] = st.selectbox("Encrypt (neo4j tls)", ["true","false"], index=0 if n.get("encrypt","true")=="true" else 1)

    st.markdown("---")
    st.markdown("#### Vector DB / Embedding")
    st.session_state.config.setdefault("vector", {})
    v = st.session_state.config["vector"]
    v["provider"] = st.selectbox("Provider", ["DEMO","Chroma","Pinecone"], index=0 if v.get("provider","DEMO")=="DEMO" else 1)
    v["vector_dir"] = st.text_input("Vector directory (local)", value=v.get("vector_dir","./vector_store"))
    v["embedding_model"] = st.text_input("Embedding model (e.g., all-MiniLM-L6-v2)", value=v.get("embedding_model","all-MiniLM-L6-v2"))
    v["api_key"] = st.text_input("Vector API Key (if applicable)", value=v.get("api_key",""), type="password")

    st.markdown("---")
    st.markdown("#### Gemini / LLM")
    st.session_state.config.setdefault("llm", {})
    l = st.session_state.config["llm"]
    l["provider"] = st.selectbox("LLM Provider", ["Gemini","Other"], index=0 if l.get("provider","Gemini")=="Gemini" else 1)
    l["endpoint"] = st.text_input("LLM Endpoint (if any)", value=l.get("endpoint",""))
    l["api_key"] = st.text_input("LLM API Key (store secrets in cloud!)", value=l.get("api_key",""), type="password")

    st.markdown("---")
    st.markdown("#### Email / OTP (demo only)")
    st.session_state.config.setdefault("email", {})
    e = st.session_state.config["email"]
    e["smtp_server"] = st.text_input("SMTP Server", value=e.get("smtp_server",""))
    e["smtp_port"] = st.text_input("SMTP Port", value=e.get("smtp_port","587"))
    e["smtp_user"] = st.text_input("SMTP User", value=e.get("smtp_user",""))
    e["smtp_pass"] = st.text_input("SMTP Password", value=e.get("smtp_pass",""), type="password")

    if st.button("Save Config (session + local)"):
        st.session_state.config["saved_at"] = time.time()
        save_session_config()

# -----------------------------
# Grounding upload area (bottom)
# -----------------------------
st.markdown("---")
st.header("Grounding Documents")
files = st.file_uploader("Upload PDF / JSON / CSV (these will be used for grounding)", accept_multiple_files=True)
if files:
    saved = []
    for f in files:
        dest = GROUNDING_DIR / f.name
        with open(dest, "wb") as out:
            out.write(f.getbuffer())
        saved.append(str(dest))
    st.success(f"Saved {len(saved)} files to grounding_files/")
    st.write(saved)

# -----------------------------
# Demo Script download / display
# -----------------------------
demo_script_md = r'''
# Demo Script — DBQuery Pharma Supply Chain

1) Mode: DEMO (sidebar) — ensure demo mode ON.
2) Prompt: "Show top 5 vendors in US by on-time delivery rate"
   - Click Generate SQL -> Review Query -> Execute Query -> Canvas -> Table/Chart
3) Prompt: "Break this down by product category"
   - Generate -> Execute -> observe chart
4) Prompt: "Trace batch B2025001 from vendor to distribution center to hospital"
   - Generate -> Execute -> Canvas -> Table
5) Upload vendor SLA CSV under Grounding Documents.
6) Prompt: "What does OTIF mean in vendor SLAs?"
   - Generate -> (demo grounding) -> Answer
7) Export pinned insights -> Export Pinned to PPTX -> Download
'''

if st.button("Show / Download Demo Script"):
    st.markdown("### Demo Script")
    st.code(demo_script_md)
    b = demo_script_md.encode("utf-8")
    st.download_button("Download Demo Script", b, file_name="demo_script.md", mime="text/markdown")

# end of app.py
