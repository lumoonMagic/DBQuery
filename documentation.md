Here’s a fully elaborated and structured documentation update reflecting **Configuration Cockpit** integration, Executive overview, hybrid product + technical + demo guide, Python module responsibilities, and Streamlit flow for your demo scripts:

---

# Supply Chain AI Assistant — Comprehensive Technical & Executive Guide

---

## 1. Executive Product Overview

**Vision:**
Enable business users and analysts to interact with enterprise supply chain data naturally using prompts, without worrying about database schemas, SQL knowledge, or underlying infrastructure.

**Value:**

* Simplifies access to actionable insights.
* Reduces dependency on BI developers for ad-hoc queries.
* Automates SQL query generation, execution, visualization, and reporting.
* Supports hybrid modes: **DEMO** for rapid POC and training, **REAL** for live enterprise data.

**Problem Solved:**
Traditional BI dashboards are static and require technical knowledge to create. Users cannot interactively explore vendor or supply chain data with natural language. This tool bridges that gap, connecting graph databases, SQL engines, and LLMs in a single workflow.

**Demo Storyline:**

1. Show top-performing vendors in the US.
2. Explore trends in vendor performance across products.
3. Obtain actionable insights from LLM.
4. Export summarized insights to PPT/JSON/CSV for boardroom presentation.
5. Expert Mode demonstrates SQL query review for transparency and trust.

**Screenshots Planned:**

* Prompt input panel.
* Query review panel in Expert Mode.
* Results canvas with tables and charts.
* Configuration Cockpit capturing Databricks, Neo4j, vector DB, and model parameters.
* Export panel for PPT/PDF.

**Business Impact:**

* Faster decision-making with actionable insights.
* Democratization of data for business users.
* Reduced turnaround time for ad-hoc queries.
* Increased trust via Expert Mode and clear query provenance.

---

## 2. Hybrid Product + Technical + Demo Guide

**Mode Overview:**

| Mode | Data Source                    | Behavior                                            |
| ---- | ------------------------------ | --------------------------------------------------- |
| DEMO | Local CSV/JSON                 | Mock queries and outputs, simulates full workflow   |
| REAL | Neo4j + Databricks + Vector DB | Live query generation, execution, and visualization |

### Demo Flow Example

1. **Prompt:** “Show top 5 vendors in US by on-time delivery rate.”
2. **LLM builds SQL** → Display in Query Review (if Expert Mode).
3. **Databricks executes query** → Results to Output Canvas.
4. **Display Canvas:** Table + Bar chart + Suggested Actions.
5. **Follow-up:** “Compare sales vs procurement for these vendors.”
6. **UI updates:** Output canvas updates, chat continues.
7. **Export:** “Export pinned insights” → Generates PPT/CSV.

---

## 3. Configuration Cockpit

**Purpose:** Central UI-based configuration management for all sensitive and technical parameters.

**Features:**

* Admin-only access via OTP + Email authentication.
* Capture and persist **Databricks connection details**:

  * Cluster ID / name
  * Host URL
  * Catalog and schema
  * Token/API key
  * Optional start/stop cluster controls
* Capture **Neo4j connection details**:

  * Host, port
  * Username/password
  * SSL options
  * Graph ontology sync options
* **Vector DB / Embeddings**:

  * Local Chroma path or Pinecone/Qdrant API key
  * Model type selection (Gemini 2.5 Flash)
* **Grounding Documents**:

  * Upload PDF, JSON, CSV, or image files
  * Vector embedding for LLM context
* **Role-Based Controls**:

  * Admin: full access
  * Analyst: prompt + results + export
  * Business User: results + visualization
* **Persistence**:

  * All values stored encrypted in local JSON / secrets manager
  * Eliminates hardcoding in `.toml` files

**Impact:**

* Users do not need to edit code or secrets manually.
* Centralizes configuration for demo and real execution.
* Reduces operational errors.

---

## 4. Python Module Responsibilities

| File                              | Responsibility                                                                                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.py`                          | Main Streamlit app orchestrating UI, Demo/Real mode toggle, prompt input, query review, execution, and output canvas. Handles session state and theme management. |
| `modules/databricks_connector.py` | Handles Databricks connection, SQL query execution, async job support (if needed), cluster start/stop hooks. Uses configuration from cockpit.                     |
| `modules/neo4j_sync.py`           | Interfaces with Neo4j, queries schema/ontology, optional graph sync, feeds table/column info to LLM. Configuration-driven.                                        |
| `modules/vector_engine.py`        | Handles embedding of uploaded grounding documents (Gemini 2.5 Flash), storage in vector DB (Chroma/Pinecone/Qdrant placeholders), and similarity-based recall.    |
| `modules/export_ppt.py`           | Generates board-ready PPT/PDF exports from pinned insights. Supports slide templates, charts, and tables.                                                         |
| `config/settings.json`            | Local fallback for cockpit values (encrypted).                                                                                                                    |
| `demo_data/`                      | Contains sample CSV/JSON files to simulate data for demo mode.                                                                                                    |
| `.streamlit/secrets.toml`         | Only required if local dev; on Streamlit Cloud, values are set through the cockpit UI.                                                                            |

---

## 5. Streamlit Flow & Call Sequence

### User Flow

```
User Prompt Input --> app.py
       │
       ├─> Configuration Cockpit (Admin-only, load settings)
       │
       ├─> Neo4j Sync Module --> returns relevant tables/columns
       │
       ├─> LLM SQL Generation (LangChain + Gemini 2.5 Flash)
       │
       ├─> Query Review Panel (Expert Mode)
       │
       ├─> Databricks Connector executes query (REAL) / DEMO Data Module (DEMO)
       │
       ├─> Output Canvas:
       │       - Table
       │       - Graphs / Charts
       │       - Suggested Actions
       │
       └─> Export Panel (PPTX / PDF / CSV)
```

**Note:** Demo mode simulates Databricks execution locally, maintaining identical UI flow.

---

## 6. Demo Script Example

**Step-by-Step Prompts:**

1. "Show top 5 vendors in US by on-time delivery rate" → Table output
2. "Break this down by product category" → Line chart
3. "Trace batch B2025001 from vendor to hospital" → Table output
4. Upload SLA CSV under Grounding Documents
5. "What does OTIF mean in vendor SLAs?" → LLM insight
6. Export pinned insights → PPTX/CSV

**Expected Behavior:**

* Each prompt updates the output canvas.
* Follow-up prompts maintain context.
* Expert Mode shows generated SQL for trust.
* Visualizations appear in dedicated canvas section.
* Export generates board-ready slides/files.

---

## 7. UI Requirements

* **Prompt Input Panel** – Single text input box.
* **Query Review (Expert Mode)** – Optional review before execution.
* **Output Canvas** – Dedicated section for table/chart/PPT previews.
* **Export Panel** – Export insights and pinned outputs.
* **Configuration Cockpit** – Admin-only, collects all credentials and parameters.
* **Role-Based Sections** – Hide sensitive sections based on user role.
* **Theme Management** – High-contrast UI for dark/light themes.

---

## 8. Data Flow Diagram (Logical)

```
[User Prompt] 
      │
      ▼
[Configuration Cockpit] ──────> [Neo4j] ──────> [LLM: SQL Gen] 
                                      │
                                      ▼
                  ┌───────────── DEMO Data Module ─────────────┐
                  │                 or                        │
                  │         [Databricks Connector]            │
                  └───────────────────────────────────────────┘
                                      │
                                      ▼
                               [Output Canvas]
                              /      |       \
                         Table     Charts     Suggested Actions
                                      │
                                      ▼
                                [Export Panel]
```

---

This document can be used for **developer onboarding**, **POC/demo guide**, and **executive presentation**, providing clarity on module responsibilities, workflow, and business value.

---

If you want, I can **also create a visually annotated Flow Diagram with UI sections and backend calls** to complement this documentation for presentations and boardroom demos.

Do you want me to do that next?
