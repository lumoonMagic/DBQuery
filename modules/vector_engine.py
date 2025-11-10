"""
vector_engine.py
Hybrid LangChain + Gemini embeddings + Chroma vector DB layer
with DEMO + REAL mode support.

Functions exposed:

- init_vector_store(config) → chroma client
- embed_and_store(docs, metadata, config)
- similarity_search(query, config, k=5)
- load_demo_embeddings() (for demo mode)

Gemini model names configured by UI/config cockpit.
Stored keys:
  config['gemini_model']
  config['gemini_api_key']
  config['vector_dir']
  config['demo_mode']

Chroma runs local for POC. In REAL mode can be swapped for Qdrant/Pinecone.
"""
import os
import json
from typing import List, Dict, Any

# LangChain & Chroma
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma
    from langchain.docstore.document import Document
    LC_AVAILABLE = True
except Exception:
    LC_AVAILABLE = False

# Fallback local embedding model (MiniLM)
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    HF_AVAILABLE = True
except Exception:
    HF_AVAILABLE = False

DEFAULT_VECTOR_DIR = "vector_store"


def init_vector_store(config: Dict[str, Any]):
    """Initialize Chroma vector store directory."""
    if not LC_AVAILABLE:
        raise RuntimeError("LangChain or Chroma not installed. Check requirements.txt")

    vector_dir = config.get("vector_dir", DEFAULT_VECTOR_DIR)
    os.makedirs(vector_dir, exist_ok=True)

    return Chroma(persist_directory=vector_dir, embedding_function=_get_embedding_fn(config))


def _get_embedding_fn(config: Dict[str, Any]):
    """Choose embedding model based on config and availability."""
    if config.get("demo_mode", True):
        # In demo mode try HF MiniLM first if available
        if HF_AVAILABLE:
            return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        # Else fallback to Gemini if key exists
        if LC_AVAILABLE and config.get("gemini_api_key"):
            return GoogleGenerativeAIEmbeddings(
                model=config.get("gemini_model", "models/embedding-001"),
                google_api_key=config.get("gemini_api_key"),
            )
        raise RuntimeError("No embedding backend available in DEMO mode.")

    # REAL mode flow
    if config.get("gemini_api_key"):
        return GoogleGenerativeAIEmbeddings(
            model=config.get("gemini_model", "models/embedding-001"),
            google_api_key=config.get("gemini_api_key"),
        )

    if HF_AVAILABLE:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    raise RuntimeError("No embedding backend configured for REAL mode.")


def embed_and_store(docs: List[str], metadata: List[dict], config: Dict[str, Any]):
    """Embed a list of text docs & store into vector db with metadata."""
    vectordb = init_vector_store(config)
    lang_docs = [Document(page_content=t, metadata=m or {}) for t, m in zip(docs, metadata)]
    vectordb.add_documents(lang_docs)
    vectordb.persist()
    return True


def similarity_search(query: str, config: Dict[str, Any], k: int = 5):
    """Return top-k similar docs for a query string."""
    vectordb = init_vector_store(config)
    try:
        results = vectordb.similarity_search(query, k=k)
        return [{"text": r.page_content, "metadata": r.metadata} for r in results]
    except Exception as e:
        return []


# DEMO / sample embeddings for supply chain use case
_demo_data_path = os.path.join("demo_data", "demo_supply_chain_vectors.json")


def load_demo_embeddings() -> List[Dict[str, Any]]:
    """Load demo embedding results if vector DB disabled."""
    if not os.path.exists(_demo_data_path):
        return [
            {"text": "Vendor ABC has 98% on-time delivery performance", "metadata": {"source": "demo"}},
            {"text": "Vendor XYZ has high defect rate and delays", "metadata": {"source": "demo"}},
        ]
    with open(_demo_data_path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    print("Vector Engine module ready. Use embed_and_store() & similarity_search().")
