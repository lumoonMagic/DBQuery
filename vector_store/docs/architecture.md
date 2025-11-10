```mermaid
flowchart LR
    User -->|Web UI| StreamlitApp[Streamlit App]

    StreamlitApp -->|Demo Mode Data| DemoCSV[(CSV Demo Data)]
    StreamlitApp -->|Demo Mode Data| DemoJSON[(JSON Demo Data)]
    StreamlitApp -->|Embeddings| ChromaDB[(Chroma Vector Store)]

    StreamlitApp -->|Real SQL| Databricks[(Databricks SQL Warehouse)]
    StreamlitApp -->|Real Graph| Neo4j[(Neo4j Aura / VM Instance)]
    
    UploadedDocs[PDF / SOP / Quality Files] --> Vectorizer[Embedding Pipeline]
    Vectorizer --> ChromaDB

    StreamlitApp --> Exporter[PPT/Insights Export Engine]
