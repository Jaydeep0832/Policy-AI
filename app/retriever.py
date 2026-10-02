import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from fastembed import TextEmbedding
from flashrank import Ranker, RerankRequest

from app.config import (
    STORAGE_DIR,
    EMBEDDING_MODEL_NAME,
    RERANKER_MODEL_NAME,
    CALIBRATED_SUFFICIENCY_THRESHOLD,
    TOP_K_RETRIEVAL,
    TOP_K_RERANKED,
    RRF_K_CONSTANT,
    MAX_PER_POLICY
)
from app.models import PolicyChunk
from app.indexer import tokenize_corpus

DRAFT_EXPIRED_KEYWORDS = re.compile(
    r'\b(draft|expired|outdated|superseded|old\s+policy|previous\s+policy|2021|2024\s+manual|2035)\b',
    re.IGNORECASE
)

class HybridPolicyRetriever:
    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = Path(storage_dir)
        self.embedder = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
        self.ranker = Ranker(model_name=RERANKER_MODEL_NAME)

        self._load_storage()

    def _load_storage(self):
        # Load active embeddings & chunks
        self.active_embeddings = np.load(self.storage_dir / "active_embeddings.npy")
        with open(self.storage_dir / "active_chunks.json", "r", encoding="utf-8") as f:
            self.active_chunks = json.load(f)

        # Load shadow embeddings & chunks
        self.shadow_embeddings = np.load(self.storage_dir / "shadow_embeddings.npy")
        with open(self.storage_dir / "shadow_chunks.json", "r", encoding="utf-8") as f:
            self.shadow_chunks = json.load(f)

        # Load BM25 index
        with open(self.storage_dir / "active_bm25.pkl", "rb") as f:
            self.active_bm25 = pickle.load(f)

        # Load master chunk lookup
        with open(self.storage_dir / "chunk_lookup.json", "r", encoding="utf-8") as f:
            self.chunk_lookup = json.load(f)

    def retrieve_dense(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Tuple[int, float]]:
        """Dense cosine similarity search over active chunks."""
        q_vec = list(self.embedder.embed([query]))[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores = np.dot(self.active_embeddings, q_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices]

    def retrieve_bm25(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Tuple[int, float]]:
        """Sparse BM25 search over active chunks."""
        tokens = [token.lower() for token in query.split() if token.isalnum() or '-' in token]
        if not tokens:
            return []
        scores = self.active_bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    def hybrid_retrieve_rrf(
        self,
        query: str,
        top_k_candidates: int = TOP_K_RETRIEVAL,
        max_per_policy: int = MAX_PER_POLICY
    ) -> List[Dict[str, Any]]:
        """Fuses dense and sparse rankings using Reciprocal Rank Fusion (RRF) with policy diversity."""
        dense_results = self.retrieve_dense(query, top_k=top_k_candidates)
        bm25_results = self.retrieve_bm25(query, top_k=top_k_candidates)

        rrf_scores: Dict[int, float] = {}

        for rank, (idx, _) in enumerate(dense_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (RRF_K_CONSTANT + rank + 1))

        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (RRF_K_CONSTANT + rank + 1))

        # Sort candidates by combined RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        # Apply Grouped Retrieval: Prevent one document from starving others
        selected_chunks = []
        policy_counts: Dict[str, int] = {}

        for idx in sorted_indices:
            chunk = self.active_chunks[idx]
            p_id = chunk["policy_id"]
            if policy_counts.get(p_id, 0) < max_per_policy or len(selected_chunks) < 4:
                policy_counts[p_id] = policy_counts.get(p_id, 0) + 1
                chunk_copy = dict(chunk)
                chunk_copy["rrf_score"] = rrf_scores[idx]
                selected_chunks.append(chunk_copy)

            if len(selected_chunks) >= top_k_candidates:
                break

        return selected_chunks

    def rerank(self, query: str, candidate_chunks: List[Dict[str, Any]], top_k: int = TOP_K_RERANKED) -> List[Dict[str, Any]]:
        """Reranks candidate passages using local cross-encoder."""
        if not candidate_chunks:
            return []

        passages = [
            {"id": c["chunk_id"], "text": c["text"], "meta": c}
            for c in candidate_chunks
        ]
        request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(request)

        reranked = []
        for r in results[:top_k]:
            item = dict(r["meta"])
            item["rerank_score"] = float(r["score"])
            reranked.append(item)

        return reranked

    def probe_shadow_index(self, query: str, active_max_score: float = 0.0) -> Optional[Dict[str, Any]]:
        """Probes shadow index (draft, expired, superseded) to detect queries targeting non-binding documents."""
        if len(self.shadow_chunks) == 0:
            return None

        has_keyword = bool(DRAFT_EXPIRED_KEYWORDS.search(query)) and ("2026" not in query)

        q_vec = list(self.embedder.embed([query]))[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores = np.dot(self.shadow_embeddings, q_vec)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        matched_chunk = self.shadow_chunks[best_idx]

        # Scenario 1: User explicitly queries draft, expired, superseded, or historical years
        if has_keyword and best_score > 0.35:
            return {
                "matched_chunk": matched_chunk,
                "score": best_score,
                "document_title": matched_chunk["document_title"],
                "status": matched_chunk["status"],
                "version": matched_chunk["version"],
                "trigger": "explicit_keyword"
            }

        # Scenario 2: Active retrieval ran and found nothing (active_max_score < 0.05), but shadow index has high confidence match
        if 0.0 < active_max_score < 0.05 and best_score >= 0.82:
            return {
                "matched_chunk": matched_chunk,
                "score": best_score,
                "document_title": matched_chunk["document_title"],
                "status": matched_chunk["status"],
                "version": matched_chunk["version"],
                "trigger": "exclusive_shadow_topic"
            }

        return None
