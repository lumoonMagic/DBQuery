# modules/vector_engine.py
"""
Stable vector engine for DBQuery POC.

- store_documents_and_embeddings(uploaded_files, vec_config)
- similarity_search(query, vec_config, k=5)

Behavior:
- If chromadb + an embedding backend exists, store embeddings in Chroma.
- If not, save files locally and return demo metadata.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
GROUNDING_DIR = BASE_DIR / "grounding_files"
GROUNDING_DIR.mkdir(exist_ok=True)

# Optional imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTEVAL_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    SENTEVAL_AVAILABLE = False

# Simple local embedding function (fallback)
def _local_embed_texts(texts: List[str]) -> List[List[float]]:
    # deterministic simple hashed vector fallback (not real embeddings)
    import hashlib
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        vec = [b / 255.0 for b in h[:128]]  # 128-d pseudo-vector
        out.append(vec)
    return out

def _use_sentence_transformer(texts: List[str], model_name="all-MiniLM-L6-v2"):
    if not SENTEVAL_AVAILABLE:
        return _local_embed_texts(texts)
    model = SentenceTransformer(model_name)
    embs = model.encode(texts, show_progress_bar=False)
    return embs.tolist()

def init_chroma_client(vec_dir: str = "./vector_store"):
    if not CHROMADB_AVAILABLE:
        raise RuntimeError("chromadb not installed")
    settings = Settings(persist_directory=str(vec_dir))
    client = chromadb.PersistentClient(path=str(vec_dir))
    # older chromadb versions use chromadb.Client(Settings(...)). We try to be defensive.
    return client

def store_documents_and_embeddings(uploaded_files: List[Any], vec_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    uploaded_files: list of Streamlit UploadedFile objects
    vec_config: dict: {'provider': 'DEMO'|'Chroma', 'vector_dir': './vector_store', 'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2'}
    """
    provider = (vec_config or {}).get("provider", "DEMO")
    vector_dir = (vec_config or {}).get("vector_dir", "./vector_store")
    embedding_model = (vec_config or {}).get("embedding_model", "all-MiniLM-L6-v2")
    stored = []

    texts = []
    metas = []
    ids = []

    for f in uploaded_files:
        filename = f.name
        dest = GROUNDING_DIR / filename
        with open(dest, "wb") as out:
            out.write(f.getbuffer())
        # try to get text content for simple files
        try:
            content = f.getvalue().decode("utf-8", errors="ignore")
        except Exception:
            content = f"name:" + filename
        texts.append(content[:4000])  # truncate to reasonable size
        metas.append({"filename": filename})
        ids.append(filename + "_" + str(len(stored)))

        stored.append({"name": filename, "path": str(dest), "provider": provider})

    # embeddings + persist (Chroma)
    if provider == "Chroma" and CHROMADB_AVAILABLE:
        try:
            client = init_chroma_client(vector_dir)
            # create/get collection
            coll_name = vec_config.get("collection_name", "dbquery_grounding") if vec_config else "dbquery_grounding"
            try:
                collection = client.get_collection(coll_name)
            except Exception:
                collection = client.create_collection(name=coll_name)
            # compute embeddings
            if SENTEVAL_AVAILABLE:
                embs = _use_sentence_transformer(texts, model_name=embedding_model)
            else:
                embs = _local_embed_texts(texts)
            collection.upsert(ids=ids, metadatas=metas, documents=texts, embeddings=embs)
            client.persist()
            return stored
        except Exception as e:
            # fallback: save files only
            stored.append({"error": str(e)})
            return stored

    # DEMO fallback: only saved to disk
    return stored

def similarity_search(query: str, vec_config: Dict[str, Any] = None, k: int = 5) -> List[Dict[str, Any]]:
    provider = (vec_config or {}).get("provider", "DEMO")
    vector_dir = (vec_config or {}).get("vector_dir", "./vector_store")
    results = []
    if provider == "Chroma" and CHROMADB_AVAILABLE:
        try:
            client = init_chroma_client(vector_dir)
            coll_name = (vec_config or {}).get("collection_name", "dbquery_grounding")
            # try get collection
            try:
                collection = client.get_collection(coll_name)
            except Exception:
                return []
            # compute query embedding
            if SENTEVAL_AVAILABLE:
                q_emb = _use_sentence_transformer([query])[0]
            else:
                q_emb = _local_embed_texts([query])[0]
            out = collection.query(query_embeddings=[q_emb], n_results=k)
            # chroma returns dict structure; adapt to friendly format
            docs = out.get("documents", [[]])[0]
            metadatas = out.get("metadatas", [[]])[0]
            for d, m in zip(docs, metadatas):
                results.append({"text": d, "metadata": m})
            return results
        except Exception:
            return []
    # DEMO: naive file search
    for p in GROUNDING_DIR.iterdir():
        if query.lower() in p.name.lower():
            results.append({"text": p.name, "metadata": {"path": str(p)}})
    return results

if __name__ == "__main__":
    print("vector_engine module loaded (stable demo).")
