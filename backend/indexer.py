import chromadb
from rank_bm25 import BM25Okapi

class Indexer:
    def __init__(self):
        self.chroma_client = chromadb.EphemeralClient()
        self.collection = self.chroma_client.get_or_create_collection(name="clauses")
        self.bm25 = None
        self.clauses = []
        
    def index(self, clauses: list[dict]):
        self.clauses = clauses
        if not clauses:
            return
            
        try:
            self.chroma_client.delete_collection(name="clauses")
        except Exception:
            pass
        self.collection = self.chroma_client.create_collection(name="clauses")
        
        texts = [c["text"] for c in clauses]
        ids = [f"doc_{i}" for i in range(len(clauses))]
        
        # ChromaDB index (uses default ONNX embedding function, avoiding PyTorch hanging on Windows)
        self.collection.add(
            documents=texts,
            ids=ids,
            metadatas=[c["bbox"] for c in clauses]
        )
        
        # BM25 index
        tokenized_corpus = [doc.lower().split() for doc in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
    def hybrid_search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.clauses:
            return []
            
        # Dense search
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 2, len(self.clauses))
        )
        dense_ids = results["ids"][0] if results["ids"] else []
        dense_scores = results["distances"][0] if results["distances"] else []
        
        # Sparse search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k*2]
        
        # RRF (Reciprocal Rank Fusion)
        rrf_scores = {}
        for rank, doc_id in enumerate(dense_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (60.0 + rank + 1)
            
        for rank, idx in enumerate(bm25_ranked):
            doc_id = f"doc_{idx}"
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (60.0 + rank + 1)
            
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        top_chunks = []
        for doc_id, _ in sorted_docs:
            idx = int(doc_id.split("_")[1])
            top_chunks.append(self.clauses[idx])
            
        return top_chunks
