import json
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STORAGE_DIR, MANIFEST_PATH
from app.models import QueryRequest, PolicyQAResponse, PolicyManifestItem
from app.agent import PolicyQAAgent
from app.retriever import HybridPolicyRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

# ---------------------------------------------------------------------------
# RAG Pipeline Educational Trace (static reference data)
# ---------------------------------------------------------------------------
RAG_EXAMPLE_DATA: Dict[str, Any] = {
    "reference_question": "What is the maximum earned leave an employee can accumulate?",
    "ground_truth": "300 days (IIMA HR Policy Manual 2026, Section 4.2, Page 70)",
    "stages": [
        {
            "stage": 1,
            "title": "Query Ingestion & Intent Scoping",
            "tag": "Pre-Processing",
            "summary": "Employee query enters the LangGraph pipeline with optional departmental context.",
            "details": "The query is sanitized and tokenized. An initial state is initialized with timers for retrieval and reranking latency profiling.",
        },
        {
            "stage": 2,
            "title": "Shadow Index Probe (Firewall)",
            "tag": "Governance Guardrail",
            "summary": "Probes the 218 shadow vectors (drafts, expired 2021, superseded 2024).",
            "details": "FastEmbed ONNX cosine similarity checks if the user is targeting non-binding policies. If targeting a draft (e.g. 2035) or expired (2021) document, an explicit refusal is returned immediately without invoking the LLM.",
        },
        {
            "stage": 3,
            "title": "Dual Hybrid Retrieval (Dense + Sparse)",
            "tag": "Hybrid Search",
            "summary": "Simultaneous dense semantic embedding and lexical keyword matching.",
            "details": "Dense BGE-Small (384d) captures semantic concepts ('accumulate' ≈ 'carry forward'), while Rank-BM25 captures exact lexical tokens ('earned leave', '300 days').",
        },
        {
            "stage": 4,
            "title": "Reciprocal Rank Fusion (RRF k=60)",
            "tag": "Ranking Fusion",
            "summary": "Fuses dense and sparse rankings mathematically into a unified candidate list.",
            "details": "Formula: RRF(d) = 1/(60 + rank_dense) + 1/(60 + rank_sparse). Normalizes disparate score distributions without sensitive weight hyperparameters.",
        },
        {
            "stage": 5,
            "title": "Policy-Grouped Diversity Allocation",
            "tag": "Conflict Prevention",
            "summary": "Limits candidate chunks to at most 2 per policy_id.",
            "details": "Guarantees that a 211-page master manual cannot drown out a 2-page executive addendum or gazetted statutory regulation, enabling reliable contradiction detection.",
        },
        {
            "stage": 6,
            "title": "FlashRank Cross-Encoder Reranking",
            "tag": "Precision Reranker",
            "summary": "Computes deep cross-attention over [Query + Context] via ms-marco-TinyBERT.",
            "details": "Unlike bi-encoders, the cross-encoder compares query and passage tokens jointly, yielding calibrated relevance probabilities in [0.0, 1.0].",
        },
        {
            "stage": 7,
            "title": "Calibrated Sufficiency Gate",
            "tag": "Anti-Hallucination Gate",
            "summary": "Enforces deterministic abstention if max(score) < 0.03.",
            "details": "Empirically calibrated threshold separates valid policy questions (score >= 0.04) from out-of-scope/irrelevant topics (score <= 0.0016). Out-of-scope queries exit immediately with zero hallucination.",
        },
        {
            "stage": 8,
            "title": "Multi-Model Structured LLM Synthesis",
            "tag": "Constrained LLM",
            "summary": "Synthesizes answer under legal hierarchy with round-robin failover.",
            "details": "Executes on Groq LPU (20B MoE / 27B Dense) with fallback to Gemini 1.5 Flash. Enforces strict JSON schema: status, answer, conflict_analysis, and citations.",
        },
        {
            "stage": 9,
            "title": "Deterministic Citation Guardrail",
            "tag": "Attribution Verifier",
            "summary": "Regex whitespace-normalized string verification of all quoted snippets.",
            "details": "Validates that every claim and quoted snippet exists verbatim on the cited PDF page before returning the response to the employee.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Application Lifecycle & Agent Singleton
# ---------------------------------------------------------------------------
_agent_instance: PolicyQAAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boots the retrieval engine and QA agent at startup."""
    global _agent_instance
    logger.info("Initializing Policy QA Assistant and loading vector indexes...")
    try:
        retriever = HybridPolicyRetriever(storage_dir=STORAGE_DIR)
        _agent_instance = PolicyQAAgent(retriever=retriever)
        logger.info("Policy QA Agent successfully initialized and ready.")
    except Exception as e:
        logger.error(f"Failed to initialize Policy QA Agent: {e}")
        _agent_instance = None
    yield
    logger.info("Shutting down Policy QA Assistant service.")


def get_agent() -> PolicyQAAgent:
    """FastAPI dependency that returns the live agent or raises 503."""
    if _agent_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not initialized. Please ensure indexes are built with `python ingest.py`.",
        )
    return _agent_instance


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IIMA Policy Question-Answering Assistant",
    description=(
        "Enterprise-grade grounded RAG assistant for IIMA internal policies "
        "with version precedence, conflict detection, and strict source attribution."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend production build if available
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    if FRONTEND_INDEX.exists():
        return FileResponse(str(FRONTEND_INDEX))
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check(agent: PolicyQAAgent = Depends(get_agent)) -> Dict[str, Any]:
    """Returns operational status and index statistics."""
    return {
        "status": "healthy",
        "service": "IIMA Policy Q&A Assistant",
        "version": "1.0.0",
        "active_chunks": len(agent.retriever.active_chunks),
        "shadow_chunks": len(agent.retriever.shadow_chunks),
        "embedding_model": agent.retriever.embedder.model_name,
    }


@app.get("/policies", response_model=List[PolicyManifestItem], tags=["Governance"])
async def list_policies() -> List[PolicyManifestItem]:
    """Returns all policies registered in the institutional manifest."""
    if not MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="Policy manifest not found")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PolicyManifestItem(**d) for d in data]


@app.post("/query", response_model=PolicyQAResponse, tags=["Policy Q&A"])
async def query_policy(
    request: QueryRequest,
    agent: PolicyQAAgent = Depends(get_agent),
) -> PolicyQAResponse:
    """Submits an employee query to the LangGraph policy workflow."""
    try:
        return agent.ask(question=request.question, department=request.department)
    except Exception as e:
        logger.error(f"Error processing query '{request.question}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while evaluating the query: {str(e)}",
        )


@app.get("/api/llm-status", tags=["Observability"])
async def get_llm_status(agent: PolicyQAAgent = Depends(get_agent)) -> Dict[str, Any]:
    """Returns telemetry on model usage, failover cascade health, and retry stats."""
    return agent.llm_router.get_failover_status()


@app.post("/api/test-llm", tags=["Observability"])
async def test_llm_ping(agent: PolicyQAAgent = Depends(get_agent)) -> Dict[str, Any]:
    """Sends a live health-check ping through the multi-model router."""
    t0 = time.time()
    sample_context = [
        {
            "chunk_id": "test_ping_chunk",
            "text": (
                "[DOC: IIMA HR Policy Manual 2026 | PAGE: 1 | CHUNK_ID: test_ping_chunk] "
                "System operational health check ping."
            ),
        }
    ]
    result = agent.llm_router.synthesize_answer(
        "Verify operational status in one short sentence.", sample_context
    )
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    meta = result.get("_llm_meta", {})

    return {
        "status": "healthy",
        "ping_latency_ms": elapsed_ms,
        "active_model_used": meta.get("model_used", "N/A"),
        "provider": meta.get("provider", "Groq"),
        "failover_occurred": meta.get("failover_occurred", False),
        "telemetry": agent.llm_router.get_failover_status(),
    }


@app.get("/api/rag-example", tags=["Observability"])
async def get_rag_example() -> Dict[str, Any]:
    """Returns a step-by-step educational trace of the RAG pipeline."""
    return RAG_EXAMPLE_DATA
