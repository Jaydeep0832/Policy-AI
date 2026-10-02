# System Architecture: Enterprise Policy Question-Answering Assistant

## 1. Overview
The **IIMA Policy Question-Answering Assistant** is a production-oriented, grounded Retrieval-Augmented Generation (RAG) system built to answer questions on internal institutional policies. It enforces strict closed-book generation, dynamic version precedence, draft/expired policy interception, multi-policy conflict handling, and verifiable citation binding.

---

## 2. Ingestion & Dual Indexing Pipeline

```
                                [Raw Documents]
                      (PDFs, Markdown Sidecars, Portal Web Text)
                                     │
                                     ▼
                      [Deterministic manifest.json]
             (policy_id, version, status, effective_date, precedence_rank)
                                     │
                                     ▼
                     [Lineage & Precedence Resolution]
          (Sort by effective_date DESC; Latest approved -> is_latest=True)
                                     │
                                     ▼
                   [Hierarchical Page-Aware Chunker]
          (Extracts paragraphs, binds breadcrumbs & page coordinates)
                                     │
             ┌───────────────────────┴───────────────────────┐
             ▼                                               ▼
[Active Approved Chunks]                         [Shadow Chunks]
(status == 'approved' & is_latest == True)       (status in ['draft', 'expired', 'superseded'])
             │                                               │
     ┌───────┴───────┐                                       │
     ▼               ▼                                       ▼
[BGE-Small Dense] [BM25 Sparse]                  [BGE-Small Dense Index]
```

### 2.1 Chunk Header Injection
To guarantee that the LLM is physically anchored to authoritative sources without hallucinating citations, each chunk embeds an explicit header:
```text
[DOC: IIMA HR Policy Manual (Staff) | BREADCRUMB: IIMA HR Policy Manual (Staff) > (5) KINDS OF LEAVE > 5.2 LEAVE TYPE 2: EARNED LEAVE | PAGE: 69 | CHUNK_ID: IIMA-HR-STAFF_p69_c8]

5.2.2 The existing ceiling on the accumulation of EL is 300 days...
```

---

## 3. Retrieval & Orchestration Flow (LangGraph)

```
                            [User Question]
                                   │
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
 [Primary Hybrid Retrieval]                     [Shadow Probe]
 - Dense BGE-Small Cosine Similarity            - Dot product over shadow vectors
 - BM25 Term Frequency                          - Regex match for draft/expired terms
            │                                             │
            ▼                                             ├─► (Match Detected)
    [RRF Fusion (k=60)]                                   │         │
 - Merges Dense + BM25 rankings                           │         ▼
 - Grouped top-2 per policy_id                            │   [Explicit Rejection Exit]
            │                                             │   "Document X is DRAFT/EXPIRED"
            ▼                                             │
 [Local FlashRank Cross-Encoder]                          │
 - Joint query-chunk cross-attention                      │
 - Selects top-4 most relevant chunks                     │
            │                                             │
            ▼                                             │
 [Calibrated Sufficiency Gate]                            │
 - Evaluates max(rerank_score) >= tau_cal                 │
   ├─► (False) ──► [Abstention Exit]                      │
   │               "Information not found"                │
   │                                                      │
   └─► (True)                                             │
         │                                                │
         ▼                                                │
 [Structured LLM Synthesis (Groq Llama 3.3 70B)] ◄────────┘
 - Legal Precedence: Statute > Manual > Memo
 - JSON Output: answered | policy_conflict | clarification
         │
         ▼
 [Deterministic Citation Verifier]
 - Attaches metadata from chunk registry
 - Validates quotes with regex whitespace/soft-hyphen normalization
         │
         ▼
  [Final Verified Response]
```

---

## 4. Key Architectural Mechanisms

### 4.1 Ingestion-Time Precedence
Because vector databases cannot dynamically execute `MAX(effective_date)` across query filters, the system groups records by `policy_id` at ingestion, sorts approved entries by date, and stamps `is_latest = True` on the newest approved document. All superseded versions receive `is_latest = False` and are placed in the shadow index.

### 4.2 Shadow Probe for Draft & Expired Refusal
When non-approved documents are simply deleted from the index, a question targeting a draft policy (e.g. *"What is the daily allowance under the 2035 draft travel guidelines?"*) may inadvertently match an approved general manual and answer from it. The **Shadow Probe** actively checks the non-binding space to trigger an explicit refusal.

### 4.3 Evidence Sufficiency Gate
To eliminate hallucinations on out-of-scope or unanswerable queries, the system tests the top cross-encoder relevance score against an empirically calibrated threshold $\tau_{cal}$. Queries with weak retrieval are rejected **before invoking the LLM**, saving API calls and guaranteeing zero hallucination.

### 4.4 Legal Precedence in Multi-Policy Conflicts
When contradictory provisions exist (e.g., General Staff HR Manual vs. Departmental Executive Addendum), the LLM prompt enforces the legal hierarchy:
1. **Statutory Regulations** (`precedence_rank: 1`)
2. **Master Staff HR Manual** (`precedence_rank: 2`)
3. **Departmental Memos / Addenda** (`precedence_rank: 3`)
4. **Website Guidelines** (`precedence_rank: 4`)
