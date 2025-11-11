# app.py
import streamlit as st
import pandas as pd
import json
from modules import databricks_connector, neo4j_sync, vector_engine, export_ppt

# ----------------------------
# --- Global Config / State ---
# ----------------------------
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = True

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "light"

if "expert_mode" not in st.session_state:
    st.session_state.expert_mode = False

if "pinned_outputs" not in st.session_state:
    st.session_state.pinned_outputs = []

# ----------------------------
# --- Theme Handling ----------
# ----------------------------
def apply_theme(theme):
    if theme == "dark":
        st.markdown(
            """
            <style>
            .stApp {background-color:#111; color:white;}
            .css-1d391kg p {color:white;}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp {background-color:white; color:black;}
            </style>
            """,
            unsafe_allow_html=True,
        )

# ----------------------------
# --- Sidebar ----------------
# ----------------------------
st.sidebar.title("DBQuery Agent")
st.sidebar.markdown("**Mode & Theme**")

st.session_state.demo_mode = st.sidebar.checkbox("Demo Mode", value=st.session_state.demo_mode)
st.session_state.expert_mode = st.sidebar.checkbox("Expert Mode", value=st.session_state.expert_mode)

theme = st.sidebar.selectbox("Theme", ["light", "dark"], index=0 if st.session_state.ui_theme=="light" else 1)
if theme != st.session_state.ui_theme:
    st.session_state.ui_theme = theme
    apply_theme(theme)

st.sidebar.markdown("---")
st.sidebar.markdown("**Configuration Cockpit**")
if st.sidebar.button("Open Admin Cockpit"):
    st.session_state.show_cockpit = True

if "show_cockpit" in st.session_state and st.session_state.show_cockpit:
    st.sidebar.markdown("Admin Cockpit Placeholder: Capture all credentials here")
    st.sidebar.text_input("Databricks Host", key="db_host")
    st.sidebar.text_input("Databricks Token", key="db_token")
    st.sidebar.text_input("Neo4J Host", key="neo4j_host")
    st.sidebar.text_input("Neo4J User", key="neo4j_user")
    st.sidebar.text_input("Neo4J Password", key="neo4j_pass")
    st.sidebar.text_input("Vector DB Key", key="vector_key")
    st.sidebar.text_input("LLM Model Type", key="llm_model")
    st.sidebar.button("Save Configurations")

# ----------------------------
# --- Main Layout ------------
# ----------------------------
st.title("DBQuery: Graph → SQL Agent")

prompt = st.text_area("Enter your requirement or question:", height=100)

if st.button("Generate SQL / Run Query"):
    st.markdown("**Query Flow:**")
    if st.session_state.demo_mode:
        st.info("Demo Mode: Using sample data.")
        # Sample demo response based on prompt
        if "top vendors" in prompt.lower():
            df = pd.read_csv("demo_data/supply_chain_sample.csv")
            st.dataframe(df.head(5))
            st.bar_chart(df["performance_score"].head(5))
            st.session_state.pinned_outputs.append(df.head(5))
        elif "low vendors" in prompt.lower():
            df = pd.read_csv("demo_data/supply_chain_sample.csv")
            st.dataframe(df.tail(5))
            st.bar_chart(df["performance_score"].tail(5))
            st.session_state.pinned_outputs.append(df.tail(5))
        else:
            st.info("Demo: Sample answer for prompt")
    else:
        st.info("Real Mode: Generating SQL via LLM and executing on Databricks")
        # Placeholder: Call modules for real-mode
        sql_query = "SELECT * FROM vendor_table WHERE country='US' ORDER BY performance DESC LIMIT 5;"
        st.markdown(f"**Generated SQL:** `{sql_query}`")
        if st.session_state.expert_mode:
            st.text_area("Review SQL (Expert Mode)", value=sql_query, height=100)
        # Execute on Databricks (placeholder)
        df_real = pd.DataFrame({"vendor":["A","B"],"score":[95,92]})
        st.dataframe(df_real)
        st.bar_chart(df_real["score"])
        st.session_state.pinned_outputs.append(df_real)

# ----------------------------
# --- Output Canvas ----------
# ----------------------------
st.markdown("---")
st.subheader("Output Canvas")
for i, output in enumerate(st.session_state.pinned_outputs):
    st.write(f"**Pinned Output {i+1}**")
    st.dataframe(output)

if st.button("Export Pinned Outputs to PPT"):
    export_ppt.generate_ppt(st.session_state.pinned_outputs)
    st.success("PPT generated (Demo Mode)")

