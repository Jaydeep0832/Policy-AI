from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class PolicyManifestItem(BaseModel):
    file_name: str
    policy_id: str
    title: str
    version: str
    status: Literal["approved", "superseded", "draft", "expired"]
    effective_date: str
    is_latest: bool = False
    superseded_by: Optional[str] = None
    precedence_rank: int = 3
    department: str = "General"
    description: Optional[str] = None

class PolicyChunk(BaseModel):
    chunk_id: str
    document_title: str
    file_name: str
    policy_id: str
    version: str
    status: Literal["approved", "superseded", "draft", "expired"]
    effective_date: str
    is_latest: bool
    page_number: int
    breadcrumb: str
    precedence_rank: int
    text: str
    token_count: Optional[int] = None

class CitedChunk(BaseModel):
    chunk_id: str = Field(description="Exact chunk_id (e.g., chunk_1, chunk_5) providing direct evidence")
    quoted_snippet: str = Field(description="Verbatim excerpt from the chunk text supporting the claim")

class VerifiedCitation(BaseModel):
    chunk_id: str
    document: str
    version: str
    page_number: int
    section: str
    quoted_snippet: str
    verified_in_source: bool = True

class PolicyQAResponse(BaseModel):
    status: Literal["answered", "policy_conflict", "insufficient_information", "needs_clarification", "draft_or_expired_rejected"]
    answer: str = Field(description="Comprehensive answer, conflict synthesis, or abstention refusal")
    has_conflict: bool = Field(default=False, description="True if multiple active policies contradict each other")
    conflict_analysis: Optional[str] = Field(default=None, description="Detailed explanation of the contradiction and legal precedence")
    citations: List[VerifiedCitation] = Field(default_factory=list, description="Authoritative citations with verified quotes")
    retrieval_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Diagnostic metrics for observability")

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Employee question regarding policies")
    department: Optional[str] = Field(default=None, description="Optional user department for contextual scoping")
