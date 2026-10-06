import React, { useState, useEffect } from 'react';
import { API_BASE } from '../apiConfig';

export default function ExplainerView() {
  const [exampleData, setExampleData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/rag-example`)
      .then((res) => res.json())
      .then((data) => setExampleData(data))
      .catch((err) => console.error('Failed to load RAG example:', err));
  }, []);

  const stages = exampleData?.stages || [];

  return (
    <div className="view-panel">
      <div className="dashboard-wrap">
        <div className="dashboard-head">
          <h2>How the Grounded RAG Pipeline Works</h2>
          <p>
            An end-to-end interactive breakdown of the 9-stage architecture using the live reference query:{' '}
            <code style={{ color: 'var(--accent-cyan)', fontFamily: 'JetBrains Mono' }}>
              "{exampleData?.reference_question || 'What is the maximum earned leave an employee can accumulate?'}"
            </code>
          </p>
        </div>

        {/* Reference Answer Card */}
        <div className="inspector-card" style={{ borderColor: 'rgba(0, 242, 254, 0.3)', background: 'rgba(0, 242, 254, 0.04)' }}>
          <div className="inspector-top">
            <span className="inspector-title">Institutional Ground Truth Target</span>
            <span className="cascade-badge tier-1">Master Rule</span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
            {exampleData?.ground_truth || '300 days (IIMA HR Policy Manual 2026, Section 4.2, Page 70)'}
          </div>
        </div>

        {/* Stepper Cards */}
        <div className="explainer-list">
          {stages.map((s, idx) => (
            <div key={idx} className="explainer-step">
              <div className="step-num-col">{s.stage}</div>
              <div className="step-main-col">
                <h4>
                  <span>{s.title}</span>
                  <span className="cascade-badge tier-1">{s.tag}</span>
                </h4>
                <p>
                  <strong>Mechanism:</strong> {s.summary}
                </p>
                <p style={{ color: '#cbd5e1', fontSize: '13px' }}>
                  {s.details}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
