# app.py
"""
DataWeave AI - Chat-first Streamlit UI
- Chat flow with dynamic Canvas surfaces
- Expert SQL preview + Approve & Execute
- Configuration Cockpit (drawer) capturing DBX / Neo4j / Vector / LLM creds
- Demo & Real modes
- Defensive imports so demo runs without all libs installed
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
CONFIG_FILE = ROOT / "config" / "settings.json"
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
DEMO_DIR = ROOT / "demo_data"
GROUNDING_DIR = ROOT / "grounding_files"
GROUNDING_DIR.mkdir(exist_ok=True)

# Defensive module imports (may be placeholders)
try:
    from modules.databricks_connector import DatabricksConnector
except Exception:
    DatabricksConnector = None

try:
    from modules.neo4j_sync import Neo4jSync
except Exception:
    Neo4jSync = None

try:
    from modules.vector_engine import VectorEngine
except Exception:
    VectorEngine = None

try:
    from modules.export_ppt import BoardExporter
except Exception:
    BoardExporter = None

# -------------------------
# Session state bootstrap
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of dicts: {role:'user'|'assistant'|'system', text, meta}
if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = ""
if "sql_rationale" not in st.session_state:
    st.session_state.sql_rationale = ""
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "pinned" not in st.session_state:
    st.session_state.pinned = []
if "demo_mode" not in st.session_state:
    # load default from config fallback if present
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        st.session_state.demo_mode = cfg.get("app_mode", "DEMO").upper() == "DEMO"
    except Exception:
        st.session_state.demo_mode = True
if "expert_mode" not in st.session_state:
    st.session_state.expert_mode = False
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "light"
if "config" not in st.session_state:
    try:
        st.session_state.config = json.loads(CONFIG_FILE.read_text())
    except Exception:
        st.session_state.config = {}

# -------------------------
# Theming (ensures contrast)
# -------------------------
def apply_theme(theme_name: str):
    # minimal theme tokens with safe contrast
    if theme_name == "dark":
        css = """
        <style>
          .stApp { background: #0b1220; color: #e6eef8; }
          .chat-bubble-user { background:#1f2a44; color:#e6eef8; padding:10px; border-radius:10px; }
          .chat-bubble-assistant { background:#11203a; color:#e6eef8; padding:10px; border-radius:10px; }
          .card { background:#0f1724; color:#e6eef8; padding:12px; border-radius:8px; }
        </style>
        """
    else:
        css = """
        <style>
          .stApp { background: #ffffff; color: #0f1724; }
          .chat-bubble-user { background:#e6f0ff; color:#0f1724; padding:10px; border-radius:10px; }
          .chat-bubble-assistant { background:#f3f4f6; color:#0f1724; padding:10px; border-radius:10px; }
          .card { background:#ffffff; color:#0f1724; padding:12px; border-radius:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

apply_theme(st.session_state.ui_theme)

# -------------------------
# Helpers
# -------------------------
def append_message(role: str, text: str, meta: Optional[dict] = None):
    st.session_state.messages.append({"role": role, "text": text, "meta": meta or {}})

def save_config_to_file():
    try:
        CONFIG_FILE.write_text(json.dumps(st.session_state.config or {}, indent=2))
        st.success("Configuration saved to config/settings.json (local). For production use secrets manager.")
    except Exception as e:
        st.error(f"Unable to persist config: {e}")

def load_demo_vendors_df():
    path = DEMO_DIR / "vendor_performance.json"
    if path.exists():
        return pd.read_json(path)
    # fallback constructed df
    return pd.DataFrame([
        {"vendor_id":"V001","vendor_name":"Alpha","on_time_delivery_rate":92.5,"quality_score":4.5},
        {"vendor_id":"V002","vendor_name":"Beta","on_time_delivery_rate":88.3,"quality_score":4.2},
        {"vendor_id":"V003","vendor_name":"Gamma","on_time_delivery_rate":95.0,"quality_score":4.7},
    ])

def load_demo_batches_df():
    path = DEMO_DIR / "supply_chain_sample.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame([{"batch_id":"B2025001","material_name":"Atorvastatin","vendor_id":"V001","status":"Completed"}])

# Simple demo LLM -> generate SQL
def demo_generate_sql(prompt: str):
    p = prompt.lower()
    if "top" in p and "vendor" in p:
        sql = "SELECT vendor_id, vendor_name, on_time_delivery_rate FROM demo_vendors ORDER BY on_time_delivery_rate DESC LIMIT 5;"
        rationale = "Rank vendors by on-time delivery rate to identify top performers."
        return sql, rationale
    if "lowest" in p or "low" in p and "vendor" in p:
        sql = "SELECT vendor_id, vendor_name, on_time_delivery_rate FROM demo_vendors ORDER BY on_time_delivery_rate ASC LIMIT 5;"
        rationale = "Find vendors with the lowest on-time delivery rate to investigate causes."
        return sql, rationale
    if "trace" in p and "batch" in p:
        sql = "SELECT batch_id, material_name, vendor_id, status FROM demo_batches WHERE batch_id='B2025001';"
        rationale = "Trace lineage of batch B2025001."
        return sql, rationale
    # default
    return "-- DEMO: refine prompt: try 'top vendors' or 'trace batch B2025001'", "No strong mapping."

# Execute SQL in demo or real mode
def execute_sql(sql_text: str) -> pd.DataFrame:
    if st.session_state.demo_mode:
        # simplistic routing for demo SQL
        if "demo_vendors" in sql_text or "vendor" in sql_text:
            return load_demo_vendors_df()
        if "demo_batches" in sql_text or "batch" in sql_text:
            return load_demo_batches_df()
        # fallback
        return pd.DataFrame({"message":["Demo: no matching data for SQL"]})
    # real mode
    connector = None
    try:
        if DatabricksConnector is None:
            raise ImportError("Databricks connector not available.")
        connector = DatabricksConnector(config=st.session_state.config.get("databricks", {}), demo_mode=False)
        df = connector.execute_query(sql_text)
        return df
    except Exception as e:
        st.error(f"Real execution failed: {e}")
        # fallback empty df
        return pd.DataFrame({"error":[str(e)]})

# Render chat message
def render_messages():
    for m in st.session_state.messages:
        role = m["role"]
        text = m["text"]
        meta = m.get("meta", {})
        if role == "user":
            st.markdown(f"<div class='chat-bubble-user'>{text}</div>", unsafe_allow_html=True)
        elif role == "assistant":
            st.markdown(f"<div class='chat-bubble-assistant'>{text}</div>", unsafe_allow_html=True)
            # If assistant provided SQL preview in meta, show controls
            if meta.get("sql_preview"):
                st.markdown("**SQL Preview:**")
                st.code(meta["sql_preview"], language="sql")
                st.markdown(f"*Rationale:* {meta.get('rationale','-')}")
                if st.session_state.expert_mode:
                    col1, col2 = st.columns([1,1])
                    with col1:
                        if st.button("Approve & Execute", key=f"approve_{hash(meta['sql_preview'])}"):
                            df = execute_sql(meta["sql_preview"])
                            st.session_state.last_result = df
                            append_message("assistant", f"Executed SQL and produced {len(df)} rows.", {"executed": True})
                    with col2:
                        if st.button("Refine SQL", key=f"refine_{hash(meta['sql_preview'])}"):
                            # quick refine simulation
                            new_sql = meta["sql_preview"] + " -- refined"
                            st.session_state.generated_sql = new_sql
                            st.session_state.sql_rationale = "Refined by user."
                            append_message("assistant", "SQL refined. Review and approve to run.", {"sql_preview": new_sql, "rationale": st.session_state.sql_rationale})
                else:
                    if st.button("Execute (non-expert)", key=f"exec_{hash(meta['sql_preview'])}"):
                        df = execute_sql(meta["sql_preview"])
                        st.session_state.last_result = df
                        append_message("assistant", f"Executed SQL and produced {len(df)} rows.", {"executed": True})

# Render dynamic canvas based on last_result or pinned items
def render_canvas():
    if st.session_state.last_result is None and not st.session_state.pinned:
        return  # nothing to show
    st.markdown("---")
    st.subheader("Canvas")
    tabs = []
    if st.session_state.last_result is not None:
        tabs.append("Table")
        # check numeric columns for chart
        df = st.session_state.last_result
        numeric = df.select_dtypes(include="number").columns.tolist()
        if numeric:
            tabs.append("Chart")
        tabs.append("Insights")
    if st.session_state.pinned:
        tabs.append("Pinned")
    selected = st.radio("View", tabs, index=0, horizontal=True) if tabs else None

    if selected == "Table":
        st.write("### Table")
        st.dataframe(st.session_state.last_result)
        if st.button("Pin this result"):
            st.session_state.pinned.append({"title":f"Pinned at {time.strftime('%Y-%m-%d %H:%M')}", "df": st.session_state.last_result})
            st.success("Pinned.")
    elif selected == "Chart":
        st.write("### Chart")
        df = st.session_state.last_result
        numeric = df.select_dtypes(include="number").columns.tolist()
        if numeric:
            y = numeric[0]
            try:
                st.line_chart(df.set_index(df.columns[0])[y])
            except Exception:
                st.bar_chart(df[y])
    elif selected == "Insights":
        st.write("### Suggested Actions / Insights")
        # simple LLM-like insight in demo
        if st.session_state.demo_mode:
            st.markdown("- Investigate vendors with on-time < 90%")
            st.markdown("- Add backup suppliers for critical products")
        else:
            st.markdown("- (Real) Inspect QC hold reasons via QC results table")
    elif selected == "Pinned":
        st.write("### Pinned Insights")
        for p in st.session_state.pinned:
            st.markdown(f"**{p['title']}**")
            st.dataframe(p["df"])

    # Export panel
    if st.session_state.pinned:
        if st.button("Export pinned to PPT (demo)"):
            if BoardExporter is None:
                st.error("Export module not available.")
            else:
                exporter = BoardExporter(demo_mode=st.session_state.demo_mode)
                exporter.add_title_slide("DataWeave AI - Pinned Insights")
                for p in st.session_state.pinned:
                    exporter.add_table_slide(p.get("title", "Insight"), p["df"].head(10))
                out = exporter.save_ppt("dataweave_pinned.pptx")
                with open(out, "rb") as f:
                    st.download_button("Download PPTX", f.read(), file_name=out)

# -------------------------
# Layout: header + controls
# -------------------------
cols = st.columns([0.02, 1, 0.18])
with cols[1]:
    st.markdown(f"## <span style='color:#0b74de'>DataWeave AI</span> — Agent-driven Data Engineering", unsafe_allow_html=True)

# top right quick controls
with cols[2]:
    demo_toggle = st.checkbox("DEMO", value=st.session_state.demo_mode)
    st.session_state.demo_mode = demo_toggle
    expert_toggle = st.checkbox("Expert Mode", value=st.session_state.expert_mode)
    st.session_state.expert_mode = expert_toggle
    if st.button("Settings ⚙️"):
        st.session_state.open_settings = True

st.markdown("---")

# -------------------------
# Chat area
# -------------------------
chat_col, input_col = st.columns([4,1])
with chat_col:
    render_messages()
    render_canvas()

# -------------------------
# Input area
# -------------------------
with input_col:
    user_prompt = st.text_area("Ask DataWeave AI", key="prompt_input", height=150)
    if st.button("Send"):
        if not user_prompt.strip():
            st.warning("Please type a prompt.")
        else:
            append_message("user", user_prompt)
            # Generate SQL & response (demo or real)
            if st.session_state.demo_mode:
                sql, rationale = demo_generate_sql(user_prompt)
                st.session_state.generated_sql = sql
                st.session_state.sql_rationale = rationale
                append_message("assistant", f"Generated SQL preview (demo).", {"sql_preview": sql, "rationale": rationale})
            else:
                # REAL: call Neo4j to identify tables, LLM module to generate SQL (placeholder)
                try:
                    # 1) query neo4j for schema
                    neo = None
                    if Neo4jSync is not None:
                        neo = Neo4jSync(config=st.session_state.config.get("neo4j", {}), demo_mode=False if not st.session_state.demo_mode else True)
                        meta = neo.get_tables_and_columns()
                    else:
                        meta = None
                    # 2) call LLM (placeholder) to build SQL using meta & prompt
                    # for now we show a placeholder SQL
                    generated_sql = f"-- REAL MODE: SQL generated for prompt: {user_prompt[:120]}"
                    st.session_state.generated_sql = generated_sql
                    st.session_state.sql_rationale = "Real generator placeholder; integrate LLM/LLM-client here."
                    append_message("assistant", "Generated SQL preview (real-mode placeholder).", {"sql_preview": generated_sql, "rationale": st.session_state.sql_rationale})
                except Exception as e:
                    append_message("assistant", f"Error generating SQL: {e}")

    # Quick demo script runner (step-by-step)
    if st.button("Run Demo Script Step"):
        # pop next step from an internal script queue; for brevity, we implement a few steps
        steps = [
            "Show top 5 vendors in US by on-time delivery rate",
            "Break this down by product category",
            "Trace batch B2025001 from vendor to distribution center to hospital",
            "Upload SLA and ask: What does OTIF mean?"
        ]
        idx = st.session_state.get("demo_step_index", 0)
        if idx >= len(steps):
            st.info("Demo finished.")
            st.session_state.demo_step_index = 0
        else:
            step_prompt = steps[idx]
            st.session_state.demo_step_index = idx + 1
            append_message("user", step_prompt)
            sql, rationale = demo_generate_sql(step_prompt)
            append_message("assistant", "Generated SQL preview (demo).", {"sql_preview": sql, "rationale": rationale})
            st.experimental_rerun()

# -------------------------
# Settings / Configuration Cockpit (slide-out)
# -------------------------
if st.session_state.get("open_settings", False):
    with st.expander("Configuration Cockpit (Admin)", expanded=True):
        st.markdown("**Databricks**")
        db = st.session_state.config.get("databricks", {})
        db["host"] = st.text_input("Host", value=db.get("host",""))
        db["http_path"] = st.text_input("HTTP Path", value=db.get("http_path",""))
        db["token"] = st.text_input("Token (store in secrets!)", value=db.get("token",""), type="password")
        db["warehouse_id"] = st.text_input("Warehouse/Cluster ID", value=db.get("warehouse_id",""))
        st.session_state.config["databricks"] = db

        st.markdown("**Neo4j**")
        n = st.session_state.config.get("neo4j", {})
        n["uri"] = st.text_input("URI", value=n.get("uri",""))
        n["user"] = st.text_input("User", value=n.get("user",""))
        n["password"] = st.text_input("Password", value=n.get("password",""), type="password")
        st.session_state.config["neo4j"] = n

        st.markdown("**Vector / Embeddings**")
        v = st.session_state.config.get("vector", {})
        v["provider"] = st.selectbox("Provider", ["DEMO","Chroma","Pinecone"], index=0 if v.get("provider","DEMO")=="DEMO" else 1)
        v["vector_dir"] = st.text_input("Vector directory", value=v.get("vector_dir","./vector_store"))
        v["gemini_key"] = st.text_input("Gemini API Key", value=v.get("gemini_key",""), type="password")
        st.session_state.config["vector"] = v

        st.markdown("**LLM**")
        l = st.session_state.config.get("llm", {})
        l["provider"] = st.selectbox("LLM Provider", ["Gemini","Other"], index=0 if l.get("provider","Gemini")=="Gemini" else 1)
        l["api_key"] = st.text_input("LLM API Key (store in secrets!)", value=l.get("api_key",""), type="password")
        st.session_state.config["llm"] = l

        st.markdown("**Email OTP (demo)**")
        e = st.session_state.config.get("email", {})
        e["smtp_server"] = st.text_input("SMTP Server", value=e.get("smtp_server",""))
        e["smtp_port"] = st.text_input("SMTP Port", value=e.get("smtp_port","587"))
        e["smtp_user"] = st.text_input("SMTP User", value=e.get("smtp_user",""))
        e["smtp_pass"] = st.text_input("SMTP Password", value=e.get("smtp_pass",""), type="password")
        st.session_state.config["email"] = e

        col_a, col_b = st.columns([1,1])
        with col_a:
            if st.button("Save Config"):
                save_config_to_file()
        with col_b:
            if st.button("Close Settings"):
                st.session_state.open_settings = False

# -------------------------
# Footer / Demo Script Download
# -------------------------
st.markdown("---")
if st.button("Download Demo Script"):
    demo_md = """# Demo Script - DataWeave AI
1) Ensure DEMO mode is ON (top-right).
2) Prompt: 'Show top 5 vendors in US by on-time delivery rate' -> Generate -> Execute -> Canvas->Table
3) Prompt: 'Break this down by product category' -> Generate -> Execute -> Chart
4) Prompt: 'Trace batch B2025001 from vendor to distribution center to hospital' -> Generate -> Execute -> Table
5) Upload vendor SLA -> Ask 'What does OTIF mean in vendor SLAs?' -> See grounded response.
6) Pin insights and Export pinned to PPT.
"""
    st.download_button("Download .md", demo_md.encode("utf-8"), file_name="demo_script_dataweave.md", mime="text/markdown")

