# app.py
"""
Streamlit entrypoint - stable demo-first version.
- Removes deprecated experimental_rerun calls.
- Applies theme CSS immediately (no rerun).
- Defensive imports for optional modules.
- Keeps demo mode fully functional without external dependencies.
"""

import streamlit as st
import pandas as pd
import time
from pathlib import Path
import json

# Defensive module imports (modules may be added later)
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

# helper modules (optional)
try:
    from modules import ui_components, utils
except Exception:
    ui_components = None
    utils = None

# -----------------------
# App configuration
# -----------------------
st.set_page_config(layout="wide", page_title="DBQuery - Pharma Supply Chain", initial_sidebar_state="expanded")
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
    }
}


def apply_theme(theme_name: str):
    p = THEMES.get(theme_name, THEMES["Aurora Purple"])
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


# -----------------------
# Session initialization
# -----------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.ui_theme = "Aurora Purple"
    st.session_state.demo_mode = True
    st.session_state.history = []
    st.session_state.last_df = None
    st.session_state.pinned = []
    st.session_state.config = {}

# Apply theme once (no rerun required)
apply_theme(st.session_state.ui_theme)

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
    admin_email = st.text_input("Admin email (demo)")
    if st.button("Send OTP (demo)"):
        st.session_state._demo_otp = "123456"
        st.success("Demo OTP generated and shown (for demo).")
        st.write("Demo OTP: 123456")

    otp_val = st.text_input("Enter OTP to unlock admin")
    if st.button("Verify OTP"):
        if otp_val and otp_val == st.session_state.get("_demo_otp"):
            st.session_state.admin_unlocked = True
            st.success("Admin unlocked")
        else:
            st.error("Invalid OTP")

    st.markdown("---")
    st.subheader("UI Theme")
    theme = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.ui_theme))
    if theme != st.session_state.ui_theme:
        # apply theme immediately; do NOT call rerun
        st.session_state.ui_theme = theme
        apply_theme(theme)
        st.info(f"Theme switched to {theme} (applied live)")

    st.markdown("---")
    st.subheader("Model & Vector DB")
    model_endpoint = st.text_input("Model endpoint", value=st.session_state.config.get("model_endpoint", ""))
    model_key = st.text_input("Model API Key", type="password", value=st.session_state.config.get("model_key", ""))
    vec_provider = st.selectbox("Vector DB Provider", ["DEMO", "Chroma", "Pinecone"], index=0)
    vec_api_key = st.text_input("Vector DB API Key", type="password", value=st.session_state.config.get("vec_api_key", ""))

    if st.button("Save Config (session only)"):
        st.session_state.config.update({
            "model_endpoint": model_endpoint,
            "model_key": model_key,
            "vec_provider": vec_provider,
            "vec_api_key": vec_api_key
        })
        st.success("Config saved to session (POC)")

# -----------------------
# Main layout: top header & columns
# -----------------------
st.markdown(f"# <span class='accent'>DBQuery — Pharma Supply Chain POC</span>", unsafe_allow_html=True)
left_col, right_col = st.columns([2, 3])

# ---- Left: Chat / Input ----
with left_col:
    st.markdown("### 💬 Chat & Query")
    prompt = st.text_area("Natural language question (e.g. 'Top 5 low performing vendors in US')", height=120)
    expert_mode = st.checkbox("Expert mode (show SQL before execution)")

    if st.button("Generate SQL (demo)"):
        # demo generator
        if st.session_state.demo_mode:
            if "vendor" in prompt.lower() and "top" in prompt.lower():
                sql = "SELECT vendor_id, vendor_name, on_time_delivery_rate FROM demo_vendors ORDER BY on_time_delivery_rate DESC LIMIT 5"
            elif "batch" in prompt.lower() and "trace" in prompt.lower():
                sql = "SELECT batch_id, material_id, vendor_id, status FROM demo_batches WHERE batch_id LIKE 'B2025%'"
            else:
                sql = "-- DEMO: refine prompt (try 'top vendors' or 'trace batch')"
            st.session_state.generated_sql = sql
            st.success("Demo SQL generated")
        else:
            st.error("Real query generator not configured in this POC")

    gen_sql = st.text_area("Generated SQL (editable)", value=st.session_state.get("generated_sql", ""), height=160)
    if expert_mode and gen_sql:
        with st.expander("Generated SQL (expert view)"):
            st.code(gen_sql, language="sql")

    st.markdown("#### Execution")
    if st.button("Execute SQL (sync)"):
        if st.session_state.demo_mode:
            # load demo data from repo/demo_data if present
            demo_folder = APP_DIR / "demo_data"
            vendors_path = demo_folder / "vendor_performance.json"
            batches_path = demo_folder / "supply_chain_sample.csv"
            df = pd.DataFrame({"message": ["No demo result. Make sure demo_data exists."]})
            try:
                if "vendor" in gen_sql.lower():
                    vendors = pd.read_json(vendors_path)
                    df = vendors.sort_values("on_time_delivery_rate", ascending=False)
                elif "batch" in gen_sql.lower():
                    batches = pd.read_csv(batches_path)
                    df = batches
                st.session_state.last_df = df
                st.success("Demo execution complete")
            except Exception as e:
                st.error(f"Demo dataset missing or error: {e}")
        else:
            if databricks_connector is None:
                st.error("Databricks connector missing. Add modules/databricks_connector.py")
            else:
                try:
                    df = databricks_connector.run_sql(gen_sql, config=st.session_state.config)
                    st.session_state.last_df = df
                    st.success("Query executed on Databricks")
                except Exception as e:
                    st.error(f"Databricks execution error: {e}")

# ---- Right: Results & Insights ----
with right_col:
    st.markdown("### 📊 Results & Insights")
    if st.session_state.last_df is None:
        st.info("No results yet. Run a query on the left.")
    else:
        df = st.session_state.last_df
        st.dataframe(df)
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            st.markdown("**Suggested chart**")
            chart_col = numeric_cols[0]
            try:
                st.bar_chart(df.set_index(df.columns[1])[chart_col])
            except Exception:
                pass
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
        try:
            st.table(card.get("df").head(5))
        except Exception:
            st.write(card.get("df"))
        if export_ppt:
            if st.button(f"Export slide #{i}"):
                try:
                    path = export_ppt.create_pptx_from_insights([card], out_path=f"insight_{i}.pptx")
                    with open(path, "rb") as f:
                        st.download_button("Download PPTX", f.read(), file_name=path)
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
            saved = []
            for f in uploads:
                dest = GROUNDING_DIR / f.name
                with open(dest, "wb") as out:
                    out.write(f.getbuffer())
                saved.append({"name": f.name, "path": str(dest), "provider": "DEMO"})
            st.json(saved)
            st.success("Files saved (demo)")
        else:
            cfg = st.session_state.config.get("vec_config", {"demo_mode": st.session_state.demo_mode})
            stored_meta = vector_engine.store_documents_and_embeddings(uploads, vec_config=cfg)
            st.json(stored_meta)
            st.success("Stored & embedded to vector DB")
    except Exception as e:
        st.error(f"Embedding/storage failed: {e}")

# -----------------------
# Neo4j sync (admin)
# -----------------------
st.markdown("---")
st.header("🔗 Neo4j Schema / Ontology (admin)")
if st.session_state.get("admin_unlocked", False):
    if st.button("Extract Databricks metadata (dry-run)"):
        st.info("Dry-run: simulate metadata extraction")
        schema = {"demo_table": ["col1", "col2", "col3"]}
        st.json(schema)
    if st.button("Push schema to Neo4j (real)"):
        if neo4j_sync is None:
            st.error("Neo4j sync module missing (modules/neo4j_sync.py)")
        else:
            schema_obj = {"demo_table": ["col1", "col2", "col3"]}
            ok = neo4j_sync.sync_schema_to_neo4j(schema_obj, config=st.session_state.config)
            if ok:
                st.success("Schema pushed to Neo4j")
            else:
                st.error("Neo4j push failed")
else:
    st.info("Unlock Admin to enable Neo4j actions")

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

st.markdown("---")
st.caption("POC: Demo mode enabled by default. Replace module placeholders under /modules for full REAL integration.")
