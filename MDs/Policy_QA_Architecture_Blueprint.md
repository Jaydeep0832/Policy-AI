# Enterprise Architecture Blueprint: Internal Policy Q&A Assistant

## 1. Executive Summary & Overview
This document establishes the architectural foundation and technology stack specification for an enterprise-grade Internal Policy Question-Answering Assistant. The system is designed to provide strictly grounded answers derived solely from approved internal policy documents, with native support for document lifecycle management (draft, approved, expired), version precedence, multi-policy conflict detection, and granular citation tracking down to page and section levels.

---

## 2. Requirements Analysis

### 2.1 Functional Requirements (FR)

| ID | Capability | Detailed Description |
| :--- | :--- | :--- |
| **FR-01** | **Multi-Format Ingestion & Metadata Tagging** | Ingest policy documents (`PDF`, `DOCX`, `Markdown`, `HTML`). Extract structural hierarchies (sections, subsections, tables) along with essential metadata: `policy_id`, `version`, `status` (`draft`, `approved`, `expired`), `effective_date`, `expiration_date`, and `department`. |
| **FR-02** | **Document Lifecycle & Invalidation Filtering** | Filter out all documents flagged as `draft`, `expired`, or superseded prior to query matching. When multiple approved versions exist for the same policy, resolve dynamically to the latest approved version based on `effective_date`. |
| **FR-03** | **Hybrid Semantic & Lexical Retrieval** | Execute hybrid search (dense semantic embeddings + sparse BM25/keyword search) combined with cross-encoder re-ranking to capture both conceptual queries ("maternity benefits") and exact administrative jargon/clause codes ("Section 4.2(a)"). |
| **FR-04** | **Policy Conflict Detection & Resolution** | Detect when two or more active policies contain conflicting or contradictory clauses on the same subject. The system must synthesize both stances, highlight the discrepancy, reference both sources, and advise consultation with the respective policy owner. |
| **FR-05** | **Strict Grounding & Unanswerable Handling** | Enforce a strict "closed-book" generation policy. If the retrieved context contains insufficient evidence or low retrieval confidence, the assistant must explicitly declare that the information is unavailable rather than hallucinating. |
| **FR-06** | **Granular Citations & Source Attribution** | Every response must provide inline citations linked directly to the source document name, approved version number, page number, and section/clause heading. |
| **FR-07** | **Stateful Multi-Turn Dialogue & Disambiguation** | Maintain conversation state across turns. If an employee query is ambiguous (e.g., "What is the notice period?" without specifying role or tenure), prompt clarifying questions before answering. |
| **FR-08** | **Role-Based Access Control (RBAC)** | Filter document retrieval at the database level according to user identity, clearance level, and department (e.g., HR executive vs. general staff). |
| **FR-09** | **Audit Trail & User Feedback Loop** | Persist complete conversation trajectories (query, retrieved chunks, LLM prompt, answer, citations, latency, token usage) with user feedback (`thumbs up/down`, comments) for continuous evaluation. |

---

### 2.2 Non-Functional Requirements (NFR)

| ID | Category | Requirement & Target Metric |
| :--- | :--- | :--- |
| **NFR-01** | **Accuracy & Groundedness** | **Faithfulness > 95%** and **Answer Relevance > 90%** measured via automated RAG evaluation (Ragas/TruLens). Near-zero tolerance for ungrounded hallucination on compliance and HR legal topics. |
| **NFR-02** | **Latency & Performance** | End-to-end P95 response latency **< 2.5 seconds** (incorporating streaming token responses via Server-Sent Events / SSE starting in **< 800ms**). |
| **NFR-03** | **Scalability & Concurrency** | Horizontal auto-scaling capable of supporting **100+ concurrent user queries** without performance degradation, utilizing asynchronous I/O and vector DB connection pooling. |
| **NFR-04** | **Security & Data Privacy** | Zero data retention (ZDR) policy with external LLM providers; data at rest encrypted using **AES-256**, data in transit encrypted via **TLS 1.3**. Strict sanitization of PII before processing. |
| **NFR-05** | **Availability & Resilience** | System uptime SLA of **99.9%**. Graceful degradation (fallback to pure semantic search if reranker or graph router encounters an issue). |
| **NFR-06** | **Maintainability & Modularity** | Decoupled architecture allowing independent swapping of embedding models, vector databases, or LLMs without refactoring core business logic. |
| **NFR-07** | **Traceability & Observability** | Distributed tracing for every pipeline step (ingestion, chunking, query rewrite, retrieval, reranking, synthesis) via OpenTelemetry/Langfuse. |

---

## 3. End-to-End Technology Stack Recommendation

The stack below is organized chronologically across the system lifecycle, explicitly featuring **LangChain**, **LangGraph**, and **FastAPI**.

### Phase 1: Ingestion, Parsing & Chunking Pipeline
*Objective: Transform raw policy documents into structurally coherent, metadata-rich, searchable chunks.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **Document Parser** | **Docling / PyMuPDF (fitz)** | High-fidelity extraction of complex enterprise PDFs, tables, headers, and section hierarchies. Preserves page coordinates and structural layout. |
| **Chunking Strategy** | **LangChain `MarkdownHeaderTextSplitter` + Recursive Character Splitter** | Chunking policies along natural section boundaries (H1, H2, H3) ensures semantic coherence. Prevents splitting a single policy clause across arbitrary token boundaries. |
| **Metadata Enrichment** | **Pydantic + Instructor / OpenAI Function Calling** | Automatically extracts and standardizes document frontmatter: `policy_title`, `version`, `status` (`approved`, `draft`, `expired`), `effective_date`, and `department`. |
| **Sparse Ingestion** | **BM25 / FastEmbed Sparse** | Generates lexical keyword representations alongside dense vectors for hybrid retrieval. |

---

### Phase 2: Vector Database & Retrieval-Augmented Generation (RAG) Storage
*Objective: High-speed, filtered semantic and lexical indexing with strict version isolation.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **Vector Database** | **Qdrant (or Milvus)** | Top-tier performance for hybrid search (dense + sparse vectors). Provides **native metadata payload filtering** (essential for pre-filtering `status == "approved"` and selecting the latest `effective_date`). |
| **Embedding Model** | **`text-embedding-3-large` (OpenAI)** *(Alt: `bge-large-en-v1.5` for on-premise)* | 3072-dimension embeddings offering state-of-the-art semantic representation of domain-specific legal and organizational policies with configurable dimensionality. |
| **Cross-Encoder Re-ranker** | **Cohere Rerank v3** *(Alt: `bge-reranker-large`)* | Re-ranks top-30 hybrid search results down to top-5 most relevant passages. Dramatically cuts down noise and resolves nuanced policy differences. |
| **Cache Layer** | **Redis** | In-memory semantic caching for frequent queries, session state storage for multi-turn conversations, and API rate limiting. |

---

### Phase 3: Agentic Orchestration & RAG Pipeline
*Objective: Dynamic workflow management, conflict evaluation, and hallucination-free answer generation.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **Workflow Orchestration** | **LangGraph** | Enables a cyclic state machine architecture. Handles complex conditional branching: query classification $\rightarrow$ retrieval $\rightarrow$ relevance validation $\rightarrow$ policy conflict resolution $\rightarrow$ response synthesis $\rightarrow$ citation grounding check. |
| **RAG Component Abstraction** | **LangChain Core & Community** | Provides standardized interfaces for document loaders, text splitters, prompt templates, output parsers, and vector store connectors. |
| **Inference LLM** | **Anthropic Claude 3.5 Sonnet / OpenAI GPT-4o** | Unmatched performance in complex instruction-following, strict adherence to negative constraints ("answer only from context"), and nuanced logical reasoning across conflicting texts. |
| **Validation & Guardrails** | **NeMo Guardrails / Guardrails AI** | Ensures input sanitization (prompt injection defense) and enforces strict output grounding to prevent hallucinations. |

---

### Phase 4: API & Backend Service Layer
*Objective: High-throughput, asynchronous service exposure with enterprise-grade security.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **API Framework** | **FastAPI** | High-performance asynchronous Python framework (`ASGI`). Supports native Pydantic v2 validation, automated OpenAPI/Swagger documentation, and real-time token streaming via `StreamingResponse` (SSE). |
| **Authentication & RBAC** | **OAuth2 / OIDC with Azure AD / Okta (via `python-jose`)** | Standard enterprise single sign-on (SSO). Extracts JWT claims to enforce role-based document access control at query time. |
| **Background Task Processing** | **Celery + Redis** | Asynchronous processing of document uploads, parsing, embedding generation, and bulk indexing without blocking the primary API. |

---

### Phase 5: Evaluation, Quality Assurance & Benchmarking
*Objective: Systematic validation against answerable, unanswerable, and conflicting test cases.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **RAG Evaluation Framework** | **Ragas (Retrieval Augmented Generation Assessment)** | Automated scoring of: Faithfulness, Answer Relevance, Context Precision, and Context Recall. |
| **Ground Truth Test Suite** | **Pytest + Custom Golden Dataset** | Curated evaluation set of 50–100 policy questions categorized into: (1) Answerable, (2) Unanswerable/Out-of-scope, and (3) Conflicting/Superseded policies. |

---

### Phase 6: Observability, Tracing & Monitoring
*Objective: Complete visibility into agent execution paths, token economics, and retrieval quality.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **LLM Tracing & Observability** | **Langfuse (Self-hosted or Cloud) / LangSmith** | Native integration with LangChain and LangGraph. Captures complete execution DAGs, intermediate node states, latency breakdown, prompt iterations, and token costs. |
| **System Metrics & Logging** | **Prometheus + Grafana + Structlog** | System-level metrics (CPU, memory, request latency, throughput, error rates) and structured JSON application logs. |

---

### Phase 7: Deployment, Infrastructure & CI/CD
*Objective: Reproducible, scalable, and automated cloud delivery.*

| Component | Recommended Technology | Role & Justification |
| :--- | :--- | :--- |
| **Containerization** | **Docker & Docker Compose** | Multi-stage Docker builds optimizing image sizes for the FastAPI service, vector DB, and worker processes. |
| **Container Orchestration** | **AWS ECS (Fargate) / Kubernetes (EKS / AKS)** | Production-grade auto-scaling container management with zero server maintenance overhead. |
| **CI/CD Pipeline** | **GitHub Actions / GitLab CI** | Automated testing (unit tests, linting with `ruff`, security scans with `trivy`), RAG regression evaluation, and container build/push. |
| **Infrastructure as Code (IaC)** | **Terraform** | Declarative provisioning of cloud resources (VPC, databases, container registries, IAM roles). |

---

## 4. LangGraph Execution Flow & State Machine Architecture

```
                       [User Query]
                             │
                             ▼
              [1. Query Analyzer & Rewriter]
          (Resolves context, generates search terms)
                             │
                             ▼
               [2. Filtered Hybrid Retrieval]
    (Qdrant: pre-filter status=="approved", latest version)
                             │
                             ▼
               [3. Context Relevance Grader]
               /                           \
(Context Relevant)                       (Low / No Relevant Context)
             │                                     │
             ▼                                     ▼
 [4. Conflict Detection Node]            [Unanswerable Fallback Node]
       /             \                             │
(No Conflict)    (Conflict Found)                  │
     │                 │                           │
     ▼                 ▼                           │
[Grounded       [Synthesize                        │
Synthesis]       Discrepancies]                    │
     │                 │                           │
     └─────────┬───────┘                           │
               │                                   │
               ▼                                   │
  [5. Citation & Hallucination Guardrail]          │
               │                                   │
               └─────────────────┬─────────────────┘
                                 │
                                 ▼
                      [Final Streamed Response]
```

---

## 5. Review & Approval

This specification is complete and ready for your sign-off before proceeding with any scaffolding, implementation, or code generation.
