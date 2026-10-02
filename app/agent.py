import time
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langsmith import traceable

from app.config import CALIBRATED_SUFFICIENCY_THRESHOLD
from app.models import PolicyQAResponse, VerifiedCitation, CitedChunk
from app.retriever import HybridPolicyRetriever
from app.llm_router import LLMRouter
from app.citation_verifier import CitationVerifier

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    question: str
    department: Optional[str]
    start_time: float
    retrieval_latency_ms: float
    rerank_latency_ms: float
    shadow_match: Optional[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    reranked_chunks: List[Dict[str, Any]]
    max_rerank_score: float
    is_sufficient: bool
    raw_llm_response: Optional[Dict[str, Any]]
    final_response: Optional[PolicyQAResponse]

class PolicyQAAgent:
    def __init__(self, retriever: Optional[HybridPolicyRetriever] = None):
        self.retriever = retriever or HybridPolicyRetriever()
        self.llm_router = LLMRouter()
        self.citation_verifier = CitationVerifier(self.retriever.chunk_lookup)
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        # Add Nodes
        graph.add_node("probe_shadow", self._node_probe_shadow)
        graph.add_node("reject_shadow", self._node_reject_shadow)
        graph.add_node("retrieve_active", self._node_retrieve_active)
        graph.add_node("abstain_insufficient", self._node_abstain_insufficient)
        graph.add_node("synthesize_answer", self._node_synthesize_answer)
        graph.add_node("verify_citations", self._node_verify_citations)

        # Entry Point
        graph.set_entry_point("probe_shadow")

        # Routing from probe_shadow
        graph.add_conditional_edges(
            "probe_shadow",
            self._route_after_shadow_probe,
            {
                "reject": "reject_shadow",
                "continue": "retrieve_active"
            }
        )

        # Routing from retrieve_active
        graph.add_conditional_edges(
            "retrieve_active",
            self._route_after_retrieval,
            {
                "abstain": "abstain_insufficient",
                "synthesize": "synthesize_answer"
            }
        )

        # Edges to Verification and End
        graph.add_edge("reject_shadow", END)
        graph.add_edge("abstain_insufficient", END)
        graph.add_edge("synthesize_answer", "verify_citations")
        graph.add_edge("verify_citations", END)

        return graph.compile()

    def _node_probe_shadow(self, state: AgentState) -> Dict[str, Any]:
        """Probes the shadow index to detect queries targeting draft or outdated documents."""
        match = self.retriever.probe_shadow_index(state["question"])
        return {"shadow_match": match}

    def _route_after_shadow_probe(self, state: AgentState) -> str:
        if state.get("shadow_match"):
            return "reject"
        return "continue"

    def _node_reject_shadow(self, state: AgentState) -> Dict[str, Any]:
        """Generates an explicit rejection when user asks about non-binding documents."""
        e2e_ms = round((time.time() - state.get("start_time", time.time())) * 1000, 1)
        shadow = state["shadow_match"]
        doc = shadow["document_title"]
        status = shadow["status"].upper()
        ver = shadow["version"]
        
        answer = (
            f"The document '{doc}' (version {ver}) is marked as {status} and cannot be cited as binding policy. "
            f"According to institutional governance rules, only approved, active policies (such as the 2026 Staff HR Policy Manual) "
            f"may be used to answer official policy queries."
        )

        resp = PolicyQAResponse(
            status="draft_or_expired_rejected",
            answer=answer,
            has_conflict=False,
            conflict_analysis=None,
            citations=[],
            retrieval_metrics={
                "e2e_latency_ms": e2e_ms,
                "retrieval_latency_ms": 0.0,
                "rerank_latency_ms": 0.0,
                "llm_latency_ms": 0.0,
                "model_used": "Bypassed (Deterministic Shadow Probe)",
                "provider": "Local ONNX Cosine Search",
                "failover_occurred": False,
                "failover_trail": [],
                "is_grounded": False,
                "groundedness_verdict": f"Intercepted Non-Binding Document: '{doc}' (v{ver}) is marked as {status} in the institutional shadow index.",
                "shadow_match_score": shadow["score"],
                "shadow_status": shadow["status"],
                "max_rerank_score": 0.0,
                "sufficiency_threshold": CALIBRATED_SUFFICIENCY_THRESHOLD,
                "candidate_count": 0,
                "retrieved_candidates": []
            }
        )
        return {"final_response": resp}

    def _node_retrieve_active(self, state: AgentState) -> Dict[str, Any]:
        """Executes filtered hybrid retrieval (dense + BM25 via RRF) and local cross-encoder reranking."""
        query = state["question"]
        t0 = time.time()
        fused_candidates = self.retriever.hybrid_retrieve_rrf(query)
        retrieval_ms = round((time.time() - t0) * 1000, 1)

        t1 = time.time()
        reranked = self.retriever.rerank(query, fused_candidates)
        rerank_ms = round((time.time() - t1) * 1000, 1)

        max_score = reranked[0]["rerank_score"] if reranked else -99.0
        is_sufficient = max_score >= CALIBRATED_SUFFICIENCY_THRESHOLD

        return {
            "retrieved_chunks": fused_candidates,
            "reranked_chunks": reranked,
            "max_rerank_score": max_score,
            "is_sufficient": is_sufficient,
            "retrieval_latency_ms": retrieval_ms,
            "rerank_latency_ms": rerank_ms
        }

    def _route_after_retrieval(self, state: AgentState) -> str:
        if not state["is_sufficient"]:
            return "abstain"
        return "synthesize"

    def _node_abstain_insufficient(self, state: AgentState) -> Dict[str, Any]:
        """Deterministic abstention when evidence sufficiency gate fails."""
        e2e_ms = round((time.time() - state.get("start_time", time.time())) * 1000, 1)
        resp = PolicyQAResponse(
            status="insufficient_information",
            answer="The available approved policy documents do not contain sufficient information to answer this question.",
            has_conflict=False,
            conflict_analysis=None,
            citations=[],
            retrieval_metrics={
                "e2e_latency_ms": e2e_ms,
                "retrieval_latency_ms": state.get("retrieval_latency_ms", 0.0),
                "rerank_latency_ms": state.get("rerank_latency_ms", 0.0),
                "llm_latency_ms": 0.0,
                "model_used": "Bypassed (Sufficiency Gate Below Threshold)",
                "provider": "Local FlashRank TinyBERT Cross-Encoder",
                "failover_occurred": False,
                "failover_trail": [],
                "is_grounded": False,
                "groundedness_verdict": f"Out of Scope / Low Evidence: Top cross-encoder score ({state['max_rerank_score']:.4f}) is below sufficiency gate threshold ({CALIBRATED_SUFFICIENCY_THRESHOLD}). LLM invocation prevented to protect against hallucination.",
                "max_rerank_score": state["max_rerank_score"],
                "sufficiency_threshold": CALIBRATED_SUFFICIENCY_THRESHOLD,
                "candidate_count": len(state.get("retrieved_chunks", [])),
                "retrieved_candidates": [
                    {
                        "chunk_id": c["chunk_id"],
                        "document_title": c["document_title"],
                        "version": c["version"],
                        "page_number": c["page_number"],
                        "breadcrumb": c["breadcrumb"],
                        "rerank_score": round(c.get("rerank_score", 0.0), 4),
                        "text": c["text"][:240] + "..." if len(c["text"]) > 240 else c["text"]
                    }
                    for c in state.get("reranked_chunks", [])[:3]
                ]
            }
        )
        return {"final_response": resp}

    def _node_synthesize_answer(self, state: AgentState) -> Dict[str, Any]:
        """Calls LLM Router with legal precedence hierarchy to generate structured answer."""
        raw_output = self.llm_router.synthesize_answer(state["question"], state["reranked_chunks"])
        return {"raw_llm_response": raw_output}

    def _node_verify_citations(self, state: AgentState) -> Dict[str, Any]:
        """Validates quotes against retrieved chunks and binds authoritative metadata."""
        raw = state["raw_llm_response"] or {}
        llm_meta = raw.get("_llm_meta", {})
        raw_citations = [CitedChunk(**c) for c in raw.get("citations", [])]

        verified_citations = self.citation_verifier.verify_citations(
            raw_citations=raw_citations,
            retrieved_chunks=state["reranked_chunks"]
        )

        e2e_ms = round((time.time() - state.get("start_time", time.time())) * 1000, 1)

        has_conflict = raw.get("has_conflict", False)
        status_str = raw.get("status", "answered")

        if has_conflict:
            verdict = "Contradiction Grounded: Multiple contradictory policy provisions detected and reconciled via legal hierarchy."
        elif verified_citations:
            all_verified = all(c.verified_in_source for c in verified_citations)
            verdict = "Fully Grounded: Every cited snippet was verified verbatim against authoritative source passages." if all_verified else "Partially Grounded: Citations corrected to match source text."
        else:
            verdict = "Grounded: Response synthesized directly from retrieved policy context."

        resp = PolicyQAResponse(
            status=status_str,
            answer=raw.get("answer", "Answer unavailable."),
            has_conflict=has_conflict,
            conflict_analysis=raw.get("conflict_analysis"),
            citations=verified_citations,
            retrieval_metrics={
                "e2e_latency_ms": e2e_ms,
                "retrieval_latency_ms": state.get("retrieval_latency_ms", 0.0),
                "rerank_latency_ms": state.get("rerank_latency_ms", 0.0),
                "llm_latency_ms": llm_meta.get("llm_latency_ms", 0.0),
                "model_used": llm_meta.get("model_used", "openai/gpt-oss-20b"),
                "provider": llm_meta.get("provider", "Groq"),
                "failover_occurred": llm_meta.get("failover_occurred", False),
                "failover_trail": llm_meta.get("failover_trail", []),
                "max_rerank_score": state["max_rerank_score"],
                "sufficiency_threshold": CALIBRATED_SUFFICIENCY_THRESHOLD,
                "is_sufficient": state["is_sufficient"],
                "is_grounded": True,
                "groundedness_verdict": verdict,
                "candidate_count": len(state["retrieved_chunks"]),
                "context_chunk_ids": [c["chunk_id"] for c in state["reranked_chunks"]],
                "retrieved_candidates": [
                    {
                        "chunk_id": c["chunk_id"],
                        "document_title": c["document_title"],
                        "version": c["version"],
                        "page_number": c["page_number"],
                        "breadcrumb": c["breadcrumb"],
                        "rerank_score": round(c.get("rerank_score", 0.0), 4),
                        "text": c["text"][:300] + "..." if len(c["text"]) > 300 else c["text"]
                    }
                    for c in state["reranked_chunks"]
                ]
            }
        )
        return {"final_response": resp}

    @traceable(name="policy_qa_agent_pipeline", run_type="chain")
    def ask(self, question: str, department: Optional[str] = None) -> PolicyQAResponse:
        """Executes the complete LangGraph policy question-answering workflow."""
        initial_state: AgentState = {
            "question": question,
            "department": department,
            "start_time": time.time(),
            "retrieval_latency_ms": 0.0,
            "rerank_latency_ms": 0.0,
            "shadow_match": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "max_rerank_score": 0.0,
            "is_sufficient": False,
            "raw_llm_response": None,
            "final_response": None
        }

        result = self.workflow.invoke(initial_state)
        return result["final_response"]
