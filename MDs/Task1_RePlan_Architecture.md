# Revised Architectural Plan: Lean, Zero-Cost Policy Q&A Assistant (Task-1)

## 1. Executive Summary & Philosophy Shift

The objective of Task-1 is to demonstrate a robust, verifiable, and grounded AI assistant capable of answering questions from policy documents while handling version precedence, draft/expired exclusion, unanswerable queries, and conflicting policies.

To transition from an over-engineered cloud enterprise blueprint to a **100% free, reproducible, and trial-appropriate solution**, this plan implements:
1. **Zero-Cost Local Primitives**: Local CPU embeddings, local reranking, and embedded vector storage. No subscriptions, credit cards, or Docker containers required.
2. **Deterministic Metadata & Grounding**: Explicit JSON manifest and ingestion-time `is_latest` calculation instead of brittle LLM extraction. Deterministic substring citation verification and score-based abstention.
3. **Single-Call LLM Architecture**: Collapsing 4–5 LLM steps into a single structured Pydantic call with multi-provider free-tier fallback (Groq $\rightarrow$ Cerebras $\rightarrow$ Gemini Flash-Lite).
4. **Exact Trial Deliverables**: Comprehensive setup guide, a 30–35 question balanced evaluation set, and an empirical limitations/failure log.

---

## 2. Corpus, Metadata & Policy Knowledge Base Strategy

### 2.1 Official IIMA Policy Knowledge Base Catalog (Discovered from Portal)
Extracted and cataloged directly from the institutional portal (`https://www.iima.ac.in/the-institute/privacy-policy` and footer navigation):

| Policy Name | Source Link / Document | Status & Version | Concise Summary | Key Rules & Provisions | Retrieval / Coverage Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HR Policy Manual (Staff)** | `HR Policy Manual 2026_20.03.26.pdf` (Latest) & `HR_Policy_Manual_2024.pdf` (Superceded) | Approved (v2026 active; v2024 outdated) | Comprehensive human resources manual governing institute staff employment terms, benefits, conduct, and leave. | Recruitment, probation, performance appraisals, promotion norms; leave rules (casual, earned, medical, maternity/paternity, study leave); travel/per diem allowances; medical benefits & group insurance; retirement, PF, gratuity; code of conduct & grievance redressal. | Fully downloaded & indexed locally. Serves as primary benchmark for version precedence testing. |
| **IIM Act and Rules / Gazetted Regulations** | `https://www.iima.ac.in/sites/default/files/2024-06/IIMA%20Regulation%20Gazetted.pdf` | Approved / Statutory (2024-06) | Official statutory gazetted regulations under the Indian Institutes of Management Act, 2017 governing administrative & academic governance. | Powers and duties of the Director, Board of Governors, Academic Council; terms of appointment for faculty and staff; institute bylaws; disciplinary regulations and governance procedures. | Fully downloaded & verified (`IIMA_Regulation_Gazetted.pdf`). |
| **Whistleblower Policy** | `IIMA-Whistleblower-Policy.pdf` | Approved (v1.0) | Formal governance framework providing a secure mechanism to report unethical behavior, fraud, financial irregularities, or violations of law without retaliation. | Reportable infractions; roles of the Ombudsperson / Audit Committee; reporting procedure and strict identity confidentiality; non-retaliation protections; inquiry timelines; penalties for malicious/frivolous complaints. | Downloaded & indexed locally (`IIMA-Whistleblower-Policy.pdf`). |
| **Privacy Policy - Terms & Conditions (Privacy Policy-T&C)** | `https://www.iima.ac.in/the-institute/privacy-policy` | Active Web Policy | Institutional public data protection disclosure and website terms of use. | Personal information collection and processing; cookie management and session tracking; non-disclosure to unauthorized third parties; IP rights and copyright of digital assets; terms of liability. | Web text accessible; requires static scraping / conversion to markdown for offline RAG ingestion. |

#### Secondary & Linked Institutional Resources Cataloged:
- **RTI (Right to Information)**: Statutory compliance disclosure section under RTI Act, 2005. Provides Public Information Officer (PIO) details and fee structures.
- **NIRF (National Institutional Ranking Framework)**: Institutional metrics and accreditation filings.
- **Work with Us / For Recruiters / Tenders**: Public portals for staff/faculty recruitment guidelines, placement terms, and procurement conditions.
- **ESS Portal (Employee Self Service) & IIMA Mail**: Authenticated staff intranets (login required; excluded from public unauthenticated ingestion).

#### Inaccessible Resources & Coverage Gaps:
1. **Intranet / ESS Portal Gaps**: Internal operational HR circulars, department-level standard operating procedures (SOPs), and salary slips hosted behind the authenticated ESS portal (`https://ess.iima.ac.in`) cannot be accessed publicly without credentials.
2. **Dynamic Web Policy**: The `Privacy Policy-T&C` page is rendered via HTML rather than PDF; must be mirrored as a local markdown snapshot to ensure 100% offline reproducibility.

#### Ambiguities Needing Clarification:
- **Gazetted Regulations vs. HR Manual Hierarchy**: Where the Gazetted Regulations of 2024 specify general disciplinary authorities while the Staff HR Manual details specific penalty schedules, the RAG assistant must clearly distinguish statutory regulations from operational HR policies.

---

### 2.2 Deterministic Document Manifest (`manifest.json`)
The IIMA PDFs lack machine-readable frontmatter metadata. Instead of error-prone LLM extraction, all documents (official + synthetic edge cases) are registered deterministically via a `manifest.json` sidecar:

```json
[
  {
    "file_name": "HR Policy Manual 2026_20.03.26.pdf",
    "policy_id": "IIMA-HR-STAFF",
    "title": "IIMA HR Policy Manual (Staff)",
    "version": "2026.1",
    "status": "approved",
    "effective_date": "2026-03-20",
    "department": "Human Resources"
  },
  {
    "file_name": "HR_Policy_Manual_2024.pdf",
    "policy_id": "IIMA-HR-STAFF",
    "title": "IIMA HR Policy Manual (Staff)",
    "version": "2024.1",
    "status": "approved",
    "effective_date": "2024-01-01",
    "department": "Human Resources"
  },
  {
    "file_name": "IIMA_Regulation_Gazetted.pdf",
    "policy_id": "IIMA-REG-GAZETTED",
    "title": "IIMA Gazetted Regulations",
    "version": "2024.1",
    "status": "approved",
    "effective_date": "2024-06-01",
    "department": "Board of Governors"
  },
  {
    "file_name": "IIMA-Whistleblower-Policy.pdf",
    "policy_id": "IIMA-GOV-WHISTLEBLOWER",
    "title": "IIMA Whistleblower Policy",
    "version": "1.0",
    "status": "approved",
    "effective_date": "2023-09-01",
    "department": "Audit Committee / Board of Governors"
  },
  {
    "file_name": "IIMA_Privacy_Policy_TandC.md",
    "policy_id": "IIMA-LEGAL-PRIVACY",
    "title": "IIMA Privacy Policy & Terms of Use",
    "version": "1.0",
    "status": "approved",
    "effective_date": "2024-01-01",
    "department": "Legal & IT"
  },
  {
    "file_name": "remote_work_policy_v1_expired.md",
    "policy_id": "POL-REMOTE-WORK",
    "title": "Remote Work and Telecommuting Policy",
    "version": "1.0",
    "status": "expired",
    "effective_date": "2021-06-01",
    "department": "Operations"
  },
  {
    "file_name": "remote_work_policy_v2_approved.md",
    "policy_id": "POL-REMOTE-WORK",
    "title": "Remote Work and Telecommuting Policy",
    "version": "2.0",
    "status": "approved",
    "effective_date": "2024-03-01",
    "department": "Operations"
  },
  {
    "file_name": "travel_reimbursement_draft_v3.md",
    "policy_id": "POL-TRAVEL",
    "title": "Travel and Daily Allowance Policy",
    "version": "3.0-DRAFT",
    "status": "draft",
    "effective_date": "2025-01-01",
    "department": "Finance"
  },
  {
    "file_name": "annual_leave_override_memo_2024.md",
    "policy_id": "POL-LEAVE-SPECIAL",
    "title": "Executive Special Leave and Encashment Addendum",
    "version": "1.0",
    "status": "approved",
    "effective_date": "2024-06-15",
    "department": "HR Advisory Committee"
  }
]
```

### 2.3 Verified Institutional & Synthetic Test Corpus
Following direct inspection of the workspace and downloaded resources, the corpus contains verified institutional documents and targeted test fixtures:

1. **Master Approved (Latest)**: `HR Policy Manual 2026_20.03.26.pdf` (Effective 2026-03-20, 211 pages).
   - *Verified Entitlements*: Casual Leave = 8 days/year (max 5 days at a time, no carry forward / lapses Dec 31); Earned Leave = 30 days/year (credit of 15 days on Jan 1 & July 1, **accumulation ceiling = 300 days**, max 180 days at once); Encashment = max 10 days during LTC with min 30 days balance remaining.
2. **Superseded Historical**: `HR_Policy_Manual_2024.pdf` (Explicitly superseded by the 2026 declaration on page 3).
3. **Statutory Benchmark**: `IIMA Regulation Gazetted.pdf` (Statutory authority under IIM Act 2017).
4. **Governance Benchmark**: `IIMA-Whistleblower-Policy.pdf` (v1.0 approved).
5. **Operational Workplace Policy**: `Employee_Workplace_Policy_2026.pdf` (EWP-2026-01, approved 2026-04-01: 24 annual leave days, 10-day carry-forward, 8 remote days/mo).
6. **Synthetic Outdated Test Fixture**: `Leave_Policy_2021_OUTDATED_TEST.pdf` (Outdated 2021 policy: 20 days leave, 30 days carry-forward limit).
7. **Synthetic Draft/Future Test Fixture**: `Travel_Allowance_Policy_v3.0_2035_1789994375.pdf` (Draft 2035 policy: $500 per diem).
8. **Synthetic Conflict Memo**: `executive_leave_override_memo_2026.md` (Addendum purporting to reduce EL accumulation ceiling to 180 days for executive staff).

---

## 3. Robust, Zero-Cost Technology Stack & Component Specifications

| Lifecycle Phase | Component | Selected Technology | Mode / Specification | Rationale & Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion & Parsing** | Header & Page Parser | `pymupdf` (`fitz`) / `pymupdf4llm` | Local Python | Extracts text with structural headers while **strictly binding page numbers**. Injects breadcrumbs: `[DOC: ... \| BREADCRUMB: ... \| PAGE: ... \| CHUNK_ID: chunk_N]`. Fallback to paragraph boundaries and page-level chunks if heading markers are missing. |
| **Chunking Strategy** | Hierarchical Splitter | 600-token target, 100-token overlap | Local Python | Preserves clause integrity and numeric tables. Keeps full paragraphs intact. |
| **Dual Indexing** | Primary & Shadow Vector Stores | **Qdrant (Embedded)** or **ChromaDB** | Local directory (`./storage`) | **Primary Index**: Filtered strictly to `status == 'approved' AND is_latest == True`.<br>**Shadow Index**: Contains `draft`, `expired`, and `superseded` chunks for query interception. |
| **Dense Embeddings** | Bi-Encoder | `BAAI/bge-small-en-v1.5` (or `all-MiniLM-L6-v2`) | ONNX / `fastembed` | 384-dimensional dense vectors. 100% local CPU execution. Zero API cost, zero rate limits. |
| **Lexical Engine** | Sparse BM25 | `rank-bm25` | Local Python | Built **strictly over the latest approved chunks**. Matches exact acronyms, clause codes, and monetary figures. |
| **Hybrid Fusion** | Reciprocal Rank Fusion | **RRF ($k=60$)** | Custom Python | $RRF(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{60 + rank_m(d)}$. Fetches top-15 from each retriever before fusion. |
| **Conflict Coverage** | Grouped Retrieval | Top-$k$ per `policy_id` | Python logic | Retrieves top-2 candidates per matching `policy_id` (up to 15 candidates total) to prevent a single document from crowding out contradictory policies. |
| **Reranker** | Cross-Encoder | **FlashRank** or `bge-reranker-base` | Local CPU | Cross-attention scoring over full (query, chunk) pairs. Reranks fused candidates down to top-4. |
| **Sufficiency Gate** | Calibrated Abstention | Empirical score threshold | Local Python | Replaces arbitrary constants with an **empirically calibrated threshold** $\tau_{cal}$ tuned on the eval set. If `max(score) < \tau_{cal}`, abstain immediately with zero LLM spend. |
| **Primary LLM** | Generation & Synthesis | **Llama 3.3 70B** via **Groq** | `llama-3.3-70b-versatile` | Ultra-fast inference, high context adherence, robust JSON-schema structured output support. |
| **Fallback & Router** | Multi-Provider Failover | `litellm` / resilient router | Fallback with backoff | **Fallback 1**: Cerebras (`llama3.1-8b` / `llama-3.3-70b`).<br>**Fallback 2**: Google Gemini (`gemini-1.5-flash` or `gemini-2.0-flash`).<br>Includes in-memory cache for duplicate queries and exponential retry backoff. |
| **API Layer** | Web Service | **FastAPI** | Uvicorn ASGI | Lightweight endpoints for `/query` and `/health` with automated Swagger UI docs at `/docs`. |

---

## 4. Ingestion-Time Precedence & Governance Lineage

Vector stores cannot compute `MAX(effective_date)` dynamically. Governance is handled deterministically:

1. **State Machine Definitions**:
   - `DRAFT`: Pending approval; excluded from active search.
   - `ACTIVE`: Approved and currently in effect (`Effective Date <= Today <= Expiry Date`).
   - `SUPERSEDED`: Replaced by a newer approved version of the same `policy_id` (points to `superseded_by`).
   - `EXPIRED`: Reached natural expiration date without explicit replacement.
2. **Ingest-Time Lineage Computation**:
   - Group records by `policy_id`.
   - Filter `status == "approved"`.
   - Sort by `effective_date DESC`.
   - Stamp `is_latest = True` on the newest approved version; stamp `is_latest = False` and `status = "superseded"` on all older versions.
   - Index active chunks into the **Primary Index**; index draft, expired, and superseded chunks into the **Shadow Index**.

---

## 5. End-to-End LangGraph Workflow & Guardrails

```
                                [User Query]
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
  [1A. Primary Active Retrieval]               [1B. Shadow Draft/Expired Probe]
  (Dense + BM25 over approved & latest)        (Checks if query targets draft/expired)
               │                                             │
               ▼                                             │
      [2. RRF Fusion (k=60)]                                 │
   (Diverse top-k per policy_id)                             │
               │                                             │
               ▼                                             ▼
  [3. Local Cross-Encoder Rerank]               [Shadow Match Detected?]
   (FlashRank: Top 15 -> Top 4)                              │
               │                                             ├─► (Yes) ──► [Explicit Draft/Expired Rejection]
               ▼                                             │             "Document X is marked as DRAFT/EXPIRED
  [4. Calibrated Sufficiency Gate]                           │              and cannot be cited as binding policy."
  If max(score) < calibrated_tau:                            │
    ├─► (True)  ──► [Fast Abstention Exit]                   │
    │               (0 LLM calls consumed)                   │
    │                                                        │
    └─► (False)                                              │
          │                                                  │
          ▼                                                  │
  [5. Single Structured LLM Call] ◄──────────────────────────┘
  - Enforces Legal Precedence:
    Statute (Gazetted) > Master Manual (HR 2026) > Addenda/Memos
  - Categorizes: answered | policy_conflict | needs_clarification | insufficient
  - Returns answer + cited chunk_ids
          │
          ▼
  [6. Deterministic Citation & Substring Verification]
  - Attaches ground-truth metadata (Doc, Version, Page, Section) from chunk store
  - Verifies cited snippets exist using regex whitespace and soft-hyphen normalization (\s+)
          │
          ▼
     [Final Verified Output]
```

### 5.1 Single-Call Structured Pydantic Schema
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CitedChunk(BaseModel):
    chunk_id: str = Field(description="The exact chunk_id (e.g., chunk_1, chunk_3) providing direct evidence")
    quoted_snippet: str = Field(description="Verbatim excerpt from the chunk text proving the claim")

class PolicyQAResponse(BaseModel):
    status: Literal["answered", "policy_conflict", "insufficient_information", "needs_clarification"]
    answer: str = Field(description="Clear, grounded response, conflict synthesis, or clarifying question")
    has_conflict: bool = Field(default=False, description="True if multiple binding documents contradict each other")
    conflict_analysis: Optional[str] = Field(default=None, description="Detailed breakdown of conflicting clauses and governing precedence")
    citations: List[CitedChunk] = Field(default_factory=list, description="List of cited chunk references")
```

---

## 6. Curated Evaluation Suite (30–35 Questions Aligned to 2026 Manual)

All ground-truth answers are aligned to the **2026 Staff Manual** (latest active policy):

| Category | Count | Example Query | Target Ground-Truth Behavior |
| :--- | :---: | :--- | :--- |
| **Answerable (Standard)** | 12 | "What is the maximum accumulation limit for Earned Leave?" | Answers **300 days** citing IIMA HR Policy Manual 2026, Section 5.2.2. |
| **Answerable (Standard)** | 3 | "Can casual leave be carried forward to the next calendar year?" | Answers **No, casual leave cannot be accumulated and lapses at year-end** (citing 2026 Manual, Sec 5.1.7). |
| **Latest Precedence (2026 vs 2024)** | 5 | "What are the rules regarding staff leave encashment?" | Cites 2026 Manual (Section 6.1: max 10 days during LTC with min 30 days balance); ignores outdated 2024 manual. |
| **Draft / Expired Detection** | 4 | "What is the daily allowance under the 2035 Travel Policy draft?" | Triggers shadow detection: explicitly states the 2035 policy is a **DRAFT** and cannot be cited. |
| **Superseded Policy Detection** | 3 | "What were the annual leave days under the 2021 leave policy?" | Triggers shadow detection: states the 2021 policy is **EXPIRED/SUPERSEDED** and refers user to 2026 rules. |
| **Policy Conflict & Scope** | 4 | "How many days of leave can be accumulated: 300 days or 180 days?" | Identifies conflict between General HR Manual (300 days) and Executive Addendum (180 days); explains precedence and scope. |
| **Unanswerable / Out of Scope** | 4 | "What is the institute's pet insurance policy for staff?" | Reranker score falls below calibrated threshold $\tau_{cal}$; triggers immediate abstention without hallucination. |

---

## 7. Concrete Deliverables Mapping

| Required Deliverable | Workspace Artifact | Verification Method |
| :--- | :--- | :--- |
| **1. Working Application / API** | `app/main.py` + Uvicorn server | Interactive Swagger UI (`/docs`), `/query` POST endpoint with token streaming / structured JSON. |
| **2. Source Code & Setup Guide** | `README.md` + `requirements.txt` | Single-command reproduction: `pip install -r requirements.txt && python ingest.py && uvicorn app.main:app`. |
| **3. Curated Evaluation Suite** | `eval/evaluation_set.json` + `eval/run_eval.py` | Automated run scoring: Precision, Recall, Citation Groundedness, and Abstention Accuracy (with cached outputs). |
| **4. Architecture Report** | `docs/ARCHITECTURE.md` | Full documentation of RRF fusion, dual-indexing, precedence hierarchy, and threshold calibration. |
| **5. Observed Limitations & Failure Log** | `docs/LIMITATIONS.md` | Documents PDF whitespace artifacts, cross-encoder score variances, table parsing edge-cases, and free-tier rate limits. |

---

## 8. What is Excluded (Marked as Future Work)

- ❌ **Paid External APIs** (OpenAI embeddings, Cohere Rerank, Anthropic Claude).
- ❌ **Heavy Infrastructure** (Celery workers, Redis clusters, Kubernetes/EKS, Terraform).
- ❌ **Enterprise Identity Management** (Okta, Azure AD SSO).
- ❌ **Distributed Monitoring** (Prometheus, Grafana daemons).
