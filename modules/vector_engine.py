import os
import pandas as pd

# Chroma for local vector DB
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None

# Gemini 2.5 Flash embeddings placeholder
class GeminiEmbedder:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def embed_text(self, text: str):
        # DEMO placeholder: returns list of float numbers
        # In REAL mode, connect to Gemini 2.5 API
        return [float(ord(c)) / 1000 for c in text[:512]]


class VectorEngine:
    def __init__(self, config=None, demo_mode=True):
        self.config = config
        self.demo_mode = demo_mode
        self.chroma_client = None
        self.embedder = GeminiEmbedder(api_key=config.get("gemini_api_key") if config else None)

        if not demo_mode:
            if chromadb is None:
                raise ImportError("chromadb is required for REAL vector DB.")
            self.chroma_client = chromadb.Client()

        self.collection = None
        if self.chroma_client:
            # create/get collection
            self.collection = self.chroma_client.get_or_create_collection(name="grounding_docs")

    # --------------------------
    # Demo mode embeddings
    # --------------------------
    def demo_embed_docs(self):
        docs = [
            {"id": "doc1", "text": "Vendor OTIF means On-Time In-Full delivery performance."},
            {"id": "doc2", "text": "Sales vs Procurement KPIs for vendor evaluation."},
        ]
        for doc in docs:
            doc["embedding"] = self.embedder.embed_text(doc["text"])
        return docs

    # --------------------------
    # Ingest document (PDF, JSON, CSV)
    # --------------------------
    def ingest_document(self, doc_path):
        ext = os.path.splitext(doc_path)[1].lower()
        text = ""
        if ext == ".pdf":
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(doc_path)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
            except Exception as e:
                print(f"PDF parse error: {e}")
        elif ext == ".json":
            df = pd.read_json(doc_path)
            text = df.to_string()
        elif ext == ".csv":
            df = pd.read_csv(doc_path)
            text = df.to_string()
        else:
            raise ValueError("Unsupported document type")

        embedding = self.embedder.embed_text(text)

        if self.demo_mode:
            print("[DEMO MODE] Document ingested and embedded (simulation).")
            return {"text": text, "embedding": embedding}

        # REAL mode: store in Chroma collection
        if self.collection:
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[os.path.basename(doc_path)]
            )
        return {"text": text, "embedding": embedding}

    # --------------------------
    # Query vector DB for grounding
    # --------------------------
    def query_grounding(self, query_text):
        query_embedding = self.embedder.embed_text(query_text)
        if self.demo_mode:
            print("[DEMO MODE] Querying grounding docs...")
            return self.demo_embed_docs()

        if self.collection:
            results = self.collection.query(query_embeddings=[query_embedding], n_results=3)
            return results
        return []

# --------------------------
# Example usage
# --------------------------
if __name__ == "__main__":
    ve_demo = VectorEngine(demo_mode=True)
    docs = ve_demo.demo_embed_docs()
    print(docs)

    # Example document ingestion
    # ve_demo.ingest_document("demo_data/vendor_performance.json")
    results = ve_demo.query_grounding("What is OTIF in vendor SLAs?")
    print(results)
