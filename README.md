# DBQuery

# Streamlit Graph + SQL Agent (DBQuery)

This project demonstrates an enterprise-style Streamlit application that connects to Databricks, Neo4j, and a vector database, with demo/real mode switching, configuration cockpit, and export utilities.

## ✅ Features

* Smart configuration cockpit with OTP email login (admin)
* Databricks SQL connector (demo + real modes)
* Neo4j sync hooks (demo + real modes)
* Vector DB integration (Chroma local) + Gemini embedding pipeline
* Upload grounding docs (PDF/JSON) and embed
* Role-based UI (Admin / Analyst / Viewer)
* Query execution with Databricks
* Board-ready export utility
* Streamlit Cloud compatible

## 📂 Project Structure

```
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
└── README.md
```

## 🚀 Deployment Steps

1. Create a GitHub repo and push the files.
2. Deploy to Streamlit Cloud (select app.py).
3. Configure secrets (see .streamlit/secrets.toml or Streamlit Cloud secrets).
4. Install requirements: pip install -r requirements.txt
5. Run locally: streamlit run app.py

## 📦 Requirements / Dependencies

Add the following to your requirements.txt (or use as guidance):

# ---- Streamlit UI ----
streamlit==1.33.0
streamlit-option-menu==0.3.6
streamlit-extras==0.2.8

# ---- Core Helpers ----
pandas
numpy
python-dotenv
pydantic
requests
cryptography

# ---- Vector DB + Embeddings ----
langchain==0.1.17
langchain-community==0.0.30
langchain-openai==0.1.8

# Gemini langchain binding
langchain-google-genai==0.1.2

# Google Gemini SDK
google-generativeai==0.3.2

chromadb==0.4.24

# ---- Databricks ----
databricks-sql-connector==2.9.0

# ---- Neo4j ----
neo4j==5.11.0

# ---- PPT Export ----
python-pptx==0.6.21

# ---- Background Job Placeholder ----
celery==5.3.1
redis==5.0.3

# ---- File parsing for uploads ----
PyPDF2
tiktoken

# ---- Security ----
bcrypt

# ---- Optional Local Embeddings (fallback) ----
sentence-transformers==2.2.2

---
