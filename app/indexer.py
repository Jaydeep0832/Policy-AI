import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from app.config import STORAGE_DIR, POLICIES_DIR, MANIFEST_PATH, EMBEDDING_MODEL_NAME
from app.models import PolicyManifestItem, PolicyChunk
from app.chunker import HierarchicalPolicyChunker

def tokenize_corpus(texts: List[str]) -> List[List[str]]:
    """Simple alphanumeric tokenizer for BM25."""
    return [[token.lower() for token in text.split() if token.isalnum() or '-' in token] for text in texts]

class PolicyIndexBuilder:
    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
        self.chunker = HierarchicalPolicyChunker()

    def load_manifest(self) -> List[PolicyManifestItem]:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [PolicyManifestItem(**d) for d in data]

        # Enforce deterministic lineage and is_latest resolution
        grouped: Dict[str, List[PolicyManifestItem]] = {}
        for item in items:
            grouped.setdefault(item.policy_id, []).append(item)

        resolved_items = []
        for policy_id, group in grouped.items():
            approved = [it for it in group if it.status == "approved"]
            if approved:
                approved.sort(key=lambda x: x.effective_date, reverse=True)
                latest_approved = approved[0]
                latest_approved.is_latest = True
                resolved_items.append(latest_approved)

                for older in approved[1:]:
                    older.is_latest = False
                    older.status = "superseded"
                    older.superseded_by = latest_approved.file_name
                    resolved_items.append(older)

            # Include draft, expired, and superseded documents unchanged for shadow indexing
            for other in group:
                if other.status in ["draft", "expired", "superseded"] and other not in resolved_items:
                    other.is_latest = False
                    resolved_items.append(other)

        return resolved_items

    def build_indexes(self) -> Dict[str, Any]:
        items = self.load_manifest()
        print(f"Loaded {len(items)} policy records from manifest.")

        active_chunks: List[PolicyChunk] = []
        shadow_chunks: List[PolicyChunk] = []

        for item in items:
            file_path = POLICIES_DIR / item.file_name
            if not file_path.exists():
                print(f"Warning: File {item.file_name} not found in {POLICIES_DIR}")
                continue

            doc_chunks = self.chunker.chunk_document(item, file_path)
            print(f"-> Parsed {item.file_name}: {len(doc_chunks)} chunks (Status: {item.status}, Latest: {item.is_latest})")

            for c in doc_chunks:
                if c.status == "approved" and c.is_latest:
                    active_chunks.append(c)
                else:
                    shadow_chunks.append(c)

        print(f"\nTotal Active Chunks: {len(active_chunks)}")
        print(f"Total Shadow Chunks (Draft/Expired/Superseded): {len(shadow_chunks)}")

        # 1. Compute and save Dense Embeddings for Active Chunks
        active_texts = [c.text for c in active_chunks]
        active_embeds = list(self.embedder.embed(active_texts))
        active_matrix = np.array(active_embeds, dtype=np.float32)
        # Normalize for cosine similarity via dot product
        norms = np.linalg.norm(active_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        active_matrix = active_matrix / norms

        np.save(self.storage_dir / "active_embeddings.npy", active_matrix)

        # 2. Build BM25 Index over Active Chunks
        active_tokens = tokenize_corpus(active_texts)
        active_bm25 = BM25Okapi(active_tokens)
        with open(self.storage_dir / "active_bm25.pkl", "wb") as f:
            pickle.dump(active_bm25, f)

        # 3. Compute and save Dense Embeddings for Shadow Chunks
        shadow_texts = [c.text for c in shadow_chunks]
        if shadow_texts:
            shadow_embeds = list(self.embedder.embed(shadow_texts))
            shadow_matrix = np.array(shadow_embeds, dtype=np.float32)
            s_norms = np.linalg.norm(shadow_matrix, axis=1, keepdims=True)
            s_norms[s_norms == 0] = 1e-12
            shadow_matrix = shadow_matrix / s_norms
            np.save(self.storage_dir / "shadow_embeddings.npy", shadow_matrix)
        else:
            np.save(self.storage_dir / "shadow_embeddings.npy", np.empty((0, 384), dtype=np.float32))

        # 4. Save metadata JSONs
        with open(self.storage_dir / "active_chunks.json", "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in active_chunks], f, indent=2)

        with open(self.storage_dir / "shadow_chunks.json", "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in shadow_chunks], f, indent=2)

        # 5. Build lookup map: chunk_id -> chunk dict
        lookup = {c.chunk_id: c.model_dump() for c in active_chunks + shadow_chunks}
        with open(self.storage_dir / "chunk_lookup.json", "w", encoding="utf-8") as f:
            json.dump(lookup, f, indent=2)

        # 6. Save manifest snapshot
        with open(self.storage_dir / "manifest_snapshot.json", "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in items], f, indent=2)

        print("\nAll indexes successfully generated and saved to storage directory.")
        return {
            "active_chunk_count": len(active_chunks),
            "shadow_chunk_count": len(shadow_chunks),
            "storage_path": str(self.storage_dir)
        }

if __name__ == "__main__":
    builder = PolicyIndexBuilder()
    builder.build_indexes()
