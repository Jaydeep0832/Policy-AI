import React from 'react';

export default function Sidebar({ activeView, setActiveView, onSelectPreset }) {
  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="brand-header">
        <div className="brand-logo">II</div>
        <div>
          <h1 className="brand-title">IIMA Policy AI</h1>
          <div className="brand-status">
            <span className="status-dot"></span>
            <span>Engine Active • 476 Chunks</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeView === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveView('chat')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>Policy Chat</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === 'failover' ? 'active' : ''}`}
          onClick={() => setActiveView('failover')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <span>LLM Failover Details</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === 'explainer' ? 'active' : ''}`}
          onClick={() => setActiveView('explainer')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <span>How RAG Works</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === 'policies' ? 'active' : ''}`}
          onClick={() => setActiveView('policies')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <span>Institutional Policies</span>
        </button>
      </nav>

      {/* Preset Queries & Live Telemetry */}
      <div className="sidebar-scroll">
        <div className="section-label">
          <span>Trial Benchmark Queries</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('What is the maximum earned leave an employee can accumulate?')}
        >
          <span className="chip-badge tag-ground">Master Ground Truth (2026)</span>
          <span>Max earned leave accumulation ceiling?</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('How many days of casual leave are granted per calendar year?')}
        >
          <span className="chip-badge tag-ground">Staff HR Manual (Page 69)</span>
          <span>Annual casual leave entitlement?</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('What does the 2024 Staff HR manual say about probation?')}
        >
          <span className="chip-badge tag-ground">Version Precedence Test</span>
          <span>2024 manual probation rule vs 2026?</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('Can I claim travel allowance under the 2035 draft travel policy?')}
        >
          <span className="chip-badge tag-draft">Draft Shadow Interception</span>
          <span>Claim travel allowance under 2035 draft?</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('What is the earned leave ceiling for executive cadre staff?')}
        >
          <span className="chip-badge tag-conflict">Policy Conflict Resolution</span>
          <span>Earned leave limit for executives?</span>
        </div>

        <div
          className="preset-chip"
          onClick={() => onSelectPreset('Does IIMA offer pet health insurance for staff?')}
        >
          <span className="chip-badge tag-out">Sufficiency Abstention</span>
          <span>Does IIMA offer pet insurance?</span>
        </div>

        <div style={{ marginTop: 'auto' }}>
          <div className="section-label">
            <span>Engine Telemetry</span>
          </div>
          <div className="telemetry-card">
            <div className="telemetry-row">
              <span>Primary LLM</span>
              <span className="telemetry-val">openai/gpt-oss-20b</span>
            </div>
            <div className="telemetry-row">
              <span>Dense Embeddings</span>
              <span className="telemetry-val">BGE-Small (384d)</span>
            </div>
            <div className="telemetry-row">
              <span>Sufficiency Gate</span>
              <span className="telemetry-val">&tau; &ge; 0.03</span>
            </div>
            <div className="telemetry-row">
              <span>Active Index</span>
              <span className="telemetry-val">258 Chunks (Approved)</span>
            </div>
            <div className="telemetry-row">
              <span>Shadow Index</span>
              <span className="telemetry-val">218 Chunks (Draft/Old)</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
