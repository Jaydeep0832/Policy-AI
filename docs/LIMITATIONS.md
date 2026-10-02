# Observed Limitations & Failure Modes Log

This document details empirical limitations, edge cases, and architectural trade-offs observed during development and evaluation of the IIMA Policy Q&A Assistant.

---

## 1. Scanned Image PDFs without Native Text Layers
- **Observation**: The official institutional document `IIMA-Whistleblower-Policy.pdf` was a 3-page scanned PDF consisting of raw bitmap images without an embedded font/text layer (`page.get_text("text")` returned 0 characters).
- **Impact**: Standard PDF text extraction libraries failed silently, producing empty chunk arrays.
- **Resolution**: Implemented high-fidelity markdown transcription (`IIMA_Whistleblower_Policy.md`) verified by direct visual inspection of rendered raster pages. For production scaling, an upstream OCR pipeline (e.g., Docling with Tesseract/PaddleOCR) is recommended for incoming scanned documents.

---

## 2. PDF Line Wraps, Ligatures, and Hyphenation Artifacts
- **Observation**: Text extracted from PDF policies frequently introduced soft hyphens (`\xad`), mid-sentence line breaks, and typographic quotes (`“`, `”`, `’`), causing exact string containment checks to fail against LLM-extracted quotes.
- **Resolution**: Built a dedicated normalization pipeline in `app/citation_verifier.py`:
  - Strips soft hyphens and converts typographic quotes.
  - Collapses arbitrary whitespace and newlines (`re.sub(r'\s+', ' ', text)`).
  - Implements an 85% token-overlap Jaccard fallback to verify citations when minor punctuation variations occur.

---

## 3. Cross-Encoder Score Variance & Calibration
- **Observation**: Cross-encoder models (such as `FlashRank` and `bge-reranker`) produce raw logit/sigmoid scores whose distribution shifts depending on query length and lexical density.
- **Impact**: A static threshold (e.g., $\tau = 0.35$) can be overly aggressive for short acronym queries while being too permissive for verbose queries.
- **Resolution**: Tuned the threshold $\tau_{cal}$ empirically against the curated benchmark split of answerable vs. out-of-scope queries to achieve zero ungrounded hallucinations.

---

## 4. Single-Turn Stateless Scope vs. Multi-Turn Dialogue
- **Observation**: The system operates as a stateless single-turn QA engine. When a query is ambiguous (e.g., asking about probation periods without indicating staff vs. faculty cadre), the model returns `status: "needs_clarification"` with a clarifying question.
- **Trade-off**: To maintain high throughput and zero session-management overhead, session conversation state is not persisted in memory. In a future production iteration, Redis session stores can be attached to support multi-turn clarifying threads.

---

## 5. Free-Tier Rate Limits & Failover Dynamics
- **Observation**: Groq free tier enforces rate limits (around 30 RPM and daily token quotas).
- **Resolution**: Designed a 3-tier fallback router:
  1. Primary: Groq Llama 3.3 70B (`llama-3.3-70b-versatile`).
  2. Failover 1: Groq Llama 3.1 8B (`llama-3.1-8b-instant`) — uses separate model quota with same API key.
  3. Failover 2: Google Gemini 1.5 Flash (`gemini-1.5-flash`).
