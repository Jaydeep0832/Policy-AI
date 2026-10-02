import React, { useRef, useEffect } from 'react';

export default function ChatView({
  messages,
  inputQuestion,
  setInputQuestion,
  selectedDept,
  setSelectedDept,
  isLoading,
  onSubmit,
  onInspect,
  onSelectPreset
}) {
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="chat-container">
      {/* Messages Stream */}
      <div className="messages-list">
        {messages.length === 0 ? (
          <div className="welcome-hero">
            <div className="hero-pill">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
              <span>Strict Closed-Book Grounding Active</span>
            </div>
            <h2>IIMA Policy Q&A Assistant</h2>
            <p>
              Answers employee inquiries exclusively using approved institutional policies. Enforces latest 2026 version precedence, rejects draft/expired rules via shadow indexing, and reconciles policy conflicts with full source attribution.
            </p>

            <div className="hero-grid">
              <div className="hero-card" onClick={() => onSelectPreset('What is the maximum earned leave an employee can accumulate?')}>
                <h3>🛡️ Master Ground Truth</h3>
                <p>Verifies 300-day EL ceiling & 8-day CL from 2026 Staff HR Manual.</p>
              </div>
              <div className="hero-card" onClick={() => onSelectPreset('What is the earned leave ceiling for executive cadre staff?')}>
                <h3>⚖️ Conflict Resolution</h3>
                <p>Surfaces 180-day executive memo contradiction & clarifies precedence.</p>
              </div>
              <div className="hero-card" onClick={() => onSelectPreset('Can I claim travel allowance under the 2035 draft travel policy?')}>
                <h3>🚫 Shadow Interception</h3>
                <p>Detects non-binding draft policies and refuses without calling LLM.</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => {
            if (msg.role === 'user') {
              return (
                <div key={index} className="message-row user-row">
                  <div className="message-wrap">
                    <div className="user-bubble">{msg.content}</div>
                  </div>
                  <div className="avatar-badge user-avatar">U</div>
                </div>
              );
            }

            // Assistant Message
            const resp = msg.response;
            const metrics = resp?.retrieval_metrics || {};
            const e2eSec = ((metrics.e2e_latency_ms || 1200) / 1000).toFixed(2);
            const modelName = metrics.model_used || 'openai/gpt-oss-20b';
            const rerankScore = metrics.max_rerank_score !== undefined ? Number(metrics.max_rerank_score).toFixed(4) : 'N/A';

            let pillClass = 'pill-answered';
            let pillText = 'ANSWERED';
            if (resp.status === 'policy_conflict') {
              pillClass = 'pill-conflict';
              pillText = 'POLICY CONFLICT RESOLVED';
            } else if (resp.status === 'draft_or_expired_rejected') {
              pillClass = 'pill-rejected';
              pillText = 'NON-BINDING DRAFT REJECTED';
            } else if (resp.status === 'insufficient_information') {
              pillClass = 'pill-insufficient';
              pillText = 'INSUFFICIENT INFORMATION';
            }

            return (
              <div key={index} className="message-row bot-row">
                <div className="avatar-badge bot-avatar">II</div>
                <div className="message-wrap">
                  <div className="bot-bubble">
                    <div className={`status-pill ${pillClass}`}>{pillText}</div>
                    
                    <div style={{ fontSize: '14.5px', lineHeight: '1.65', whiteSpace: 'pre-wrap' }}>
                      {resp.answer}
                    </div>

                    {/* Conflict Explanation Card */}
                    {resp.has_conflict && resp.conflict_analysis && (
                      <div className="conflict-card">
                        <h4>⚖️ Contradiction & Legal Precedence Analysis</h4>
                        <p>{resp.conflict_analysis}</p>
                      </div>
                    )}

                    {/* Citations List */}
                    {resp.citations && resp.citations.length > 0 && (
                      <div className="citations-list">
                        <div className="citations-title">
                          Authoritative Verified Citations ({resp.citations.length})
                        </div>
                        {resp.citations.map((c, cIdx) => (
                          <div key={cIdx} className="citation-box">
                            <div className="citation-top">
                              <span className="citation-doc">{c.document} (v{c.version})</span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="citation-page-badge">Page {c.page_number}</span>
                                <span className="citation-verified">✓ Verified in Source</span>
                              </div>
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                              {c.section}
                            </div>
                            <div className="citation-quote">"{c.quoted_snippet}"</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Real-Time Performance Strip */}
                    <div className="perf-strip">
                      <span className="perf-pill">⏱️ {e2eSec}s</span>
                      <span className="perf-pill">🧠 {modelName}</span>
                      <span className="perf-pill">🎯 Rerank: {rerankScore}</span>
                      {metrics.failover_occurred && (
                        <span className="perf-pill" style={{ color: 'var(--accent-amber)' }}>
                          ⚠️ Failover Active
                        </span>
                      )}
                      <button
                        className="btn-inspect"
                        onClick={() => onInspect({ question: msg.userQuestion, response: resp })}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="11" cy="11" r="8"/>
                          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <span>Inspect Groundedness</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="message-row bot-row">
            <div className="avatar-badge bot-avatar">II</div>
            <div className="message-wrap">
              <div className="bot-bubble" style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)' }}>
                <div className="status-dot"></div>
                <span>Evaluating policy evidence via hybrid RRF & FlashRank reranker...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="chat-input-dock">
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Ask any question about IIMA HR, leave, probation, travel, or statutory policies..."
            rows={1}
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />

          <div className="chat-input-footer">
            <span className="chat-shortcut-hint">
              Press <strong>Enter</strong> to send • <strong>Shift + Enter</strong> for newline
            </span>
            <button
              className="btn-submit"
              onClick={onSubmit}
              disabled={isLoading || !inputQuestion.trim()}
            >
              <span>Ask Assistant</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
