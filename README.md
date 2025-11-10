DBQuery — Streamlit Graph + SQL Agent (E2E Pharma Supply Chain)

This project demonstrates an enterprise-grade Streamlit application for real-time supply chain intelligence powered by:

✅ Databricks SQL (real + demo)
✅ Neo4j Material Flow Graph (real + demo)
✅ Vector search (Chroma) + Hybrid RAG
✅ Pharma-specific E2E flow (raw → WIP → batch → FG → DC → Market)
✅ “Demo Mode” with pre-loaded pharma supply chain data
✅ Board-ready PPT export

It operates in two modes:

Mode	Description
Demo Mode	Uses included CSV/JSON pharma datasets and scripted GenAI responses
Enterprise Mode	Connects to live Databricks / Neo4j / Vectors & executes real SQL + graph queries

This allows seamless PoC → Enterprise rollout.

✅ Features
🔧 Configuration Cockpit

Admin OTP login

Set Databricks SQL/Neo4j creds

Toggle Demo vs Real mode

🧠 AI Intelligence

Hybrid Agent: SQL + Graph + RAG

Embeddings: Gemini / fallback: Sentence-Transformer

Domain: Pharma Supply Chain / Material Flow

Smart grounding on uploaded SOPs, policies, BOM sheets

📊 Enterprise Data Flow Support

E2E material traceability

Vendor → RM → Batch → Plant → DC → Market

Touchpoints: procurement, QA, batch release, logistics

📎 Upload / Embed Documents

PDF / JSON / XLS vendor & RM spec sheets

Create searchable knowledge bank

📤 Board-Ready Exports

Generate PPT decks with charts & flows

📂 Project Structure
DBQuery/
│── app.py
│── config/
│   └── settings.json
│── modules/
│   ├── databricks_connector.py
│   ├── neo4j_sync.py
│   ├── vector_engine.py
│   └── export_ppt.py
│── demo_data/
│   ├── supply_chain_sample.csv
│   └── vendor_performance.json
│── vector_store/
│   └── .gitkeep
│── .streamlit/
│   └── secrets.toml
│── requirements.txt
└── README.md  ← (this file)

🧪 Demo Mode Instructions
✅ Enable Demo Mode

In UI → Admin → Settings → Toggle "Demo Mode"

📁 Demo Datasets Used

supply_chain_sample.csv → Material flow (PO → GRN → Batch → FG movement)

vendor_performance.json → Vendor OTIF/quality scores

🎯 Example Prompts & Expected Outputs
Prompt

Show traceability for Batch B2317 from vendor RM to finished goods shipment

Expected Output

SQL View: RM PO → GRN → Batch → FG → Shipment

Graph view: Vendor → RM Lot → Batch → DC → Market

KPI: lead time, cycle time, QA holds

Prompt

Highlight vendors with repeat RM quality deviations in last 3 months

Expected Output

Table of vendors

OTIF, quality score, CAPA notes

Suggested root causes + improvement actions

Prompt

What is the average plant-to-market cycle time for Product X

Expected

Mean / p95 cycle times

Bottleneck stage inference

Chart + narrative

🏗️ Enterprise Mode (Real)
Requires:

✅ Databricks SQL Warehouse
✅ Neo4j Aura / VM instance
✅ Object storage (optional for ingestion)

Configure in admin settings page.

🚀 Deployment Steps
Streamlit Cloud

Push repo to GitHub

Create Streamlit Cloud app → select app.py

Add secrets via Streamlit Cloud UI

Launch

Local Run
pip install -r requirements.txt
streamlit run app.py

VM Deployment (Ubuntu)
sudo apt update && sudo apt install python3-pip -y
pip install -r requirements.txt
nohup streamlit run app.py --server.port 8501 &

🔐 Secrets Template (.streamlit/secrets.toml)
[databricks]
host = ""
token = ""
warehouse = ""

[neo4j]
uri = ""
user = ""
password = ""

[email]
smtp_server = ""
smtp_port = ""
username = ""
password = ""

⚙️ Fallback Config (config/settings.json)
{
  "mode": "demo",
  "embedding": "gemini",
  "enable_ppt_export": true
}

📦 Requirements

(Already provided earlier — unchanged)

🎬 Demo Script for Stakeholders
Persona

Supply Chain Ops Lead / COO Dashboard

Flow
Step	Action	Result
1	Login as admin	Toggle demo mode
2	Query material traceability	Batch lineage table + graph
3	View RM vendor risk	OTIF / quality score
4	Upload SOP / CAPA	Instant vector index
5	“Explain supply risk”	GenAI narrative
6	Export PPT	Board-deck generated

🎤 Suggested line:

"Now imagine this switching from sample to live Databricks tables in one click."

📎 Support Docs Automatically Loaded (Optional)

RM Specs

Vendor SLA Sheets

SAP BOM

GMP SOP PDFs
