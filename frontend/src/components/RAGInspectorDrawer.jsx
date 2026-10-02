import React from 'react';

export default function RAGInspectorDrawer({ isOpen, onClose, inspectData }) {
  if (!isOpen || !inspectData) return null;

  const { question, response } = inspectData;
  const metrics = response?.retrieval_metrics || {};
  const isGrounded = metrics.is_grounded !== false;
  const score = metrics.max_rerank_score || 0;
  const scorePercent = Math.min(Math.max(Math.round(score * 100), 4), 100);
  const candidates = metrics.retrieved_candidates || [];

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-pane" onClick={(e) => e.stopPropagation()}>
        {/* Top Header */}
        <div className="drawer-top">
          <div>
            <h3>RAG Groundedness & Pipeline Inspector</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Deterministic transparency for this query
            </span>
          </div>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>

        {/* Scrollable Body */}
        <div className="drawer-scrollable">
          {/* Query Summary */}
          <div className="inspector-card" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="inspector-top">
              <span className="inspector-title" style={{ color: 'var(--text-dim)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                Question Being Evaluated
              </span>
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
              "{question}"
            </div>
          </div>

          {/* Groundedness Gauge */}
          <div
            className="inspector-card"
            style={{
              borderColor: isGrounded ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)',
              background: isGrounded ? 'rgba(16, 185, 129, 0.04)' : 'rgba(245, 158, 11, 0.04)'
            }}
          >
            <div className="inspector-top">
              <span className="inspector-title">Groundedness Verdict & Confidence</span>
              <span
                className="inspector-tag"
                style={{
                  color: isGrounded ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                  background: isGrounded ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)'
                }}
              >
                {isGrounded ? 'GROUNDED EVIDENCE' : 'REFUSED / ABSTAINED'}
              </span>
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
              {metrics.groundedness_verdict || 'Evaluated against policy corpus'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '10px' }}>
              <div style={{ flex: 1, height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${scorePercent}%`,
                    height: '100%',
                    background: isGrounded
                      ? 'linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald))'
                      : 'linear-gradient(90deg, var(--accent-amber), var(--accent-rose))',
                    borderRadius: '4px'
                  }}
                ></div>
              </div>
              <span style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', color: 'var(--accent-cyan)' }}>
                {Number(score).toFixed(4)} score
              </span>
            </div>
          </div>

          {/* Pipeline Stage Breakdown */}
          <div className="section-label">
            <span>Execution Pipeline Trace</span>
          </div>

          <div className="inspector-card">
            <div className="inspector-top">
              <span className="inspector-title">Stage 1: Shadow Index Probe (Firewall)</span>
              <span className="inspector-tag">STEP 1</span>
            </div>
            <div className="inspector-desc">
              Probed 218 non-binding vector chunks (drafts, expired 2021, superseded 2024).
              {metrics.shadow_status ? (
                <div style={{ color: 'var(--accent-amber)', marginTop: '4px' }}>
                  ⚠️ <strong>Triggered Rejection:</strong> Target document matched status <code>{metrics.shadow_status}</code> with similarity {metrics.shadow_match_score}. Bypassed LLM.
                </div>
              ) : (
                <div style={{ color: 'var(--accent-emerald)', marginTop: '4px' }}>
                  ✓ <strong>Clear:</strong> No non-binding policy intercepted. Proceeded to active hybrid search.
                </div>
              )}
            </div>
          </div>

          <div className="inspector-card">
            <div className="inspector-top">
              <span className="inspector-title">Stage 2: Hybrid RRF Retrieval & Reranking</span>
              <span className="inspector-tag">STEP 2</span>
            </div>
            <div className="inspector-desc">
              Simultaneous Dense BGE-Small (384d ONNX) + Lexical Rank-BM25 fused via Reciprocal Rank Fusion ($k=60$).
              <br />Retrieved <strong>{metrics.candidate_count || 0} candidate chunks</strong> across active policy categories.
              <br />Reranked via local FlashRank TinyBERT Cross-Encoder in <strong>{metrics.rerank_latency_ms || 0} ms</strong>.
            </div>
          </div>

          <div className="inspector-card">
            <div className="inspector-top">
              <span className="inspector-title">Stage 3: Calibrated Sufficiency Gate</span>
              <span className="inspector-tag">STEP 3</span>
            </div>
            <div className="inspector-desc">
              Top Cross-Encoder Score: <code>{Number(metrics.max_rerank_score || 0).toFixed(4)}</code> vs Calibrated Threshold: <code>&tau; = {metrics.sufficiency_threshold || 0.03}</code>.
              <br /><strong>Result:</strong> {metrics.is_sufficient ? (
                <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>PASSED &rarr; Proceeded to structured LLM synthesis</span>
              ) : (
                <span style={{ color: 'var(--text-dim)', fontWeight: 600 }}>BLOCKED &rarr; Strict closed-book abstention enforced (Zero Hallucination)</span>
              )}
            </div>
          </div>

          <div className="inspector-card">
            <div className="inspector-top">
              <span className="inspector-title">Stage 4: Multi-Model Structured Synthesis</span>
              <span className="inspector-tag">STEP 4</span>
            </div>
            <div className="inspector-desc">
              Active Model: <code>{metrics.model_used || 'openai/gpt-oss-20b'}</code> ({metrics.provider || 'Groq'})
              <br />LLM Synthesis Latency: <strong>{metrics.llm_latency_ms || 0} ms</strong>
              <br />Failover Status: <strong>{metrics.failover_occurred ? '⚠️ Failover Occurred' : '✓ Direct Primary Hit'}</strong>
            </div>
          </div>

          {/* Retrieved Chunks */}
          <div className="section-label">
            <span>Retrieved Evidence Chunks ({candidates.length})</span>
          </div>

          {candidates.map((c, idx) => (
            <div key={idx} className="citation-box">
              <div className="citation-top">
                <span className="citation-doc">{c.document_title} (Page {c.page_number})</span>
                <span className="citation-page-badge">Score: {c.rerank_score}</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                {c.breadcrumb} • Version {c.version}
              </div>
              <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.45', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px', marginTop: '4px' }}>
                {c.text}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
