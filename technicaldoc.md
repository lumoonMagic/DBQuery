# Supply Chain AI Assistant — Technical Documentation

## 1. Overview

This document provides a detailed technical guide for the Supply Chain AI Assistant, a Streamlit-based application that leverages Neo4j, Databricks, and vector-based embeddings to automate SQL query generation, execution, and business analytics visualization.

The application supports both **DEMO mode** for POC scenarios and **REAL mode** for production with live data sources.

---

## 2. Features

* **Neo4j Integration:** Graph database to store ontology of tables, columns, and relationships.
* **SQL Generation:** LLM generates SQL queries dynamically based on natural language prompts.
* **Databricks Connector:** Executes queries on Databricks clusters and returns results.
* **Vector Database Embeddings:** Supports Gemini 2.5 Flash embeddings for grounding documents.
* **Role-Based Access Control (RBAC):** Admin, Analyst, Business User roles.
* **Admin Configuration Cockpit:** Capture connection details for Databricks, Neo4j, vector DB, and manage grounding documents.
* **Demo Mode:** Uses local CSV/JSON files to simulate end-to-end data flow.
* **Board-Ready Export:** Export results and pinned insights to PPT or PDF.
* **Expert Mode:** Allows reviewing SQL before execution.
* **UI Sections:** Prompt input, query review, execution results, graphs, and export canvas.

---

## 3. Application Flow (Technical)

### 3.1 Real Mode

1. User enters a natural language prompt.
2. App queries Neo4j to identify relevant tables/columns.
3. LLM builds SQL query.
4. Databricks connector executes query on target cluster.
5. Results returned and displayed in UI:

   * Tables
   * Performance bar charts
   * Suggested actions
6. Follow-up queries maintain context in the session.
7. Insights can be exported to PPT/PDF for board presentations.

### 3.2 Demo Mode

* Uses local CSV (`supply_chain_sample.csv`) and JSON (`vendor_performance.json`).
* Same UI flow as Real Mode.
* SQL queries are generated but executed on mocked data.
* Allows showcasing all visualization and export features without live connections.

---

## 4. Data Flow

### 4.1 Demo Mode

```
User Prompt --> LLM (SQL Gen) --> Demo Data CSV/JSON --> Output Canvas (Table/Chart) --> Export
```

### 4.2 Real Mode

```
User Prompt --> Neo4j (Graph lookup) --> LLM (SQL Gen) --> Databricks (Query Exec) --> Output Canvas (Table/Chart) --> Export
```

---

## 5. UI Technical Requirements

* **Prompt Input Section:** Single text box for natural language prompts.
* **Query Review Panel:** Button to review SQL before execution (Expert Mode).
* **Execution Canvas:** Displays results, tables, graphs, charts.
* **Export Panel:** For PPT/PDF and CSV/JSON export.
* **Configuration Cockpit:** Admin-only section to store Databricks, Neo4j, Vector DB, and model credentials.
* **Role-based visibility:** Only Admin sees configuration; Analysts see queries and outputs; Business Users see results and visualizations.

---

## 6. Configuration Requirements

* **Databricks:** Cluster URL, Token/API Key, catalog, schema.
* **Neo4j:** Host, port, username, password, SSL settings.
* **Vector DB (Chroma/Pinecone/Qdrant):** Storage path or API key, model type (Gemini 2.5 Flash).
* **Grounding Documents:** Upload PDFs, JSONs, CSVs for LLM context.
* **Email OTP:** For secure admin authentication.
* **Persistence:** Configurations stored encrypted in local JSON or secret manager.

---

## 7. Project Structure

```
streamlit-graph-sql-agent/
│── app.py                       # Main Streamlit app
│── config/
│   └── settings.json            # Local fallback config
│── modules/
│   ├── databricks_connector.py  # Handles Databricks SQL execution
│   ├── neo4j_sync.py            # Neo4j integration and schema crawling
│   ├── vector_engine.py         # Embedding and vector DB operations
│   └── export_ppt.py            # PPT/PDF export utilities
│── demo_data/
│   ├── supply_chain_sample.csv  # Demo supply chain data
│   └── vendor_performance.json  # Demo vendor data
│── vector_store/                # Local Chroma vector DB storage
│── .streamlit/
│   └── secrets.toml             # Streamlit Cloud secrets
│── requirements.txt             # Python dependencies
└── README.md                     # Project documentation
```

### Module Responsibilities

* **app.py:** Orchestrates UI, mode toggle, LLM query, and execution flow.
* **databricks_connector.py:** Manages connections and query execution on Databricks.
* **neo4j_sync.py:** Reads ontology, optionally syncs schema updates, and queries Neo4j.
* **vector_engine.py:** Handles embedding of grounding documents and vector DB queries.
* **export_ppt.py:** Generates board-ready PPTX or PDF summaries from pinned insights.

---

## 8. Demo Scenarios & Prompts

1️⃣ Show top performing vendors in US

* Prompt: "Show top 5 vendors in US by on-time delivery rate"
* UI displays table with performance scores.

2️⃣ Plot vendor performance trends

* Prompt: "Break this down by product category"
* UI displays line chart.

3️⃣ LLM Insight

* Prompt: "What improvements are needed?"
* UI shows suggested actions panel with textual insights.

4️⃣ Export findings

* Prompt: "Export pinned insights"
* Generates PPTX/CSV for board review.

5️⃣ Expert Mode

* Review SQL before execution.
* Ensures transparency and trust for analysts.

---

## 9. Notes

* Demo Mode is enabled via sidebar toggle; ensures safety for demonstration without live data.
* All sensitive credentials are configured via `secrets.toml` or encrypted local storage.
* UI is modular to separate prompt input, query review, output canvas, and export functionalities.
* Themes should maintain high contrast to avoid visibility issues.

---

*End of Technical Documentation*
