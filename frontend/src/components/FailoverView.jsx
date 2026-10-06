import React, { useState, useEffect } from 'react';
import { API_BASE } from '../apiConfig';

export default function FailoverView() {
  const [telemetry, setTelemetry] = useState(null);
  const [pingResult, setPingResult] = useState(null);
  const [isPinging, setIsPinging] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/llm-status`);
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.error('Failed to fetch LLM status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handlePing = async () => {
    setIsPinging(true);
    setPingResult('Pinging active cascade...');
    try {
      const res = await fetch(`${API_BASE}/api/test-llm`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setPingResult(`✓ Responded in ${data.ping_latency_ms}ms via ${data.active_model_used} (${data.provider})`);
        fetchStatus();
      } else {
        setPingResult('Ping failed: HTTP ' + res.status);
      }
    } catch (err) {
      setPingResult('Ping failed: ' + err.message);
    } finally {
      setIsPinging(false);
    }
  };

  const cascade = telemetry?.configured_cascade || [
    { tier: 1, model: 'openai/gpt-oss-20b', provider: 'Groq', role: 'Primary MoE Fast Reasoner', rate_budget: '8k TPM Free Tier' },
    { tier: 2, model: 'qwen/qwen3.8-27b', provider: 'Groq', role: 'Secondary Dense Reasoner (Quota Balancer)', rate_budget: '8k TPM Free Tier' },
    { tier: 3, model: 'openai/gpt-oss-120b', provider: 'Groq', role: 'Tertiary Flagship Reasoner (Fallback)', rate_budget: '8k TPM Free Tier' },
    { tier: 4, model: 'gemini-1.5-flash', provider: 'Google Gemini', role: 'External Failover Provider', rate_budget: '15 RPM Free Tier' }
  ];

  const usage = telemetry?.model_usage || {};
  const failoverHistory = telemetry?.failover_history || [];

  return (
    <div className="view-panel">
      <div className="dashboard-wrap">
        <div className="dashboard-head">
          <h2>LLM Failover Cascade & Rate-Limit Resilience</h2>
          <p>
            Real-time multi-model telemetry tracking quota load-balancing, zero-wait failover, and automatic backoff across Groq and Google Gemini inference endpoints.
          </p>
        </div>

        {/* Live Test Ping Action */}
        <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
          <button className="btn-submit" onClick={handlePing} disabled={isPinging}>
            <span>⚡ Send Live Test Ping to LLM Cascade</span>
          </button>
          {pingResult && (
            <span style={{ fontSize: '13px', fontFamily: 'JetBrains Mono', color: 'var(--accent-emerald)', fontWeight: 600 }}>
              {pingResult}
            </span>
          )}
        </div>

        {/* 4-Tier Cascade Cards */}
        <div className="cascade-grid">
          {cascade.map((item, idx) => {
            const tierClass = `tier-${item.tier || idx + 1}`;
            return (
              <div key={idx} className="cascade-box">
                <span className={`cascade-badge ${tierClass}`}>
                  Tier {item.tier}: {item.provider}
                </span>
                <h4>{item.model}</h4>
                <p>{item.role}</p>
                <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontFamily: 'JetBrains Mono' }}>
                  Budget: {item.rate_budget}
                </div>
              </div>
            );
          })}
        </div>

        {/* Telemetry Numbers */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          <div className="hero-card">
            <h3>Total LLM Calls</h3>
            <span style={{ fontSize: '26px', fontWeight: 700, color: 'var(--text-main)', fontFamily: 'JetBrains Mono' }}>
              {telemetry?.total_calls || 0}
            </span>
          </div>

          <div className="hero-card">
            <h3>Failover Incidents</h3>
            <span style={{ fontSize: '26px', fontWeight: 700, color: 'var(--accent-amber)', fontFamily: 'JetBrains Mono' }}>
              {telemetry?.failover_count || 0}
            </span>
          </div>

          <div className="hero-card">
            <h3>Retry Cooldown Strategy</h3>
            <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--accent-emerald)', marginTop: '4px' }}>
              8.0s Auto-Backoff Window
            </span>
          </div>
        </div>

        {/* Model Inferences Breakdown Table */}
        <div className="table-card">
          <div className="table-header">Model Inferences Log</div>
          <table className="data-tbl">
            <thead>
              <tr>
                <th>Model Identifier</th>
                <th>Provider</th>
                <th>Architecture Role</th>
                <th>Inferences Served</th>
              </tr>
            </thead>
            <tbody>
              {cascade.map((c, idx) => (
                <tr key={idx}>
                  <td><code>{c.model}</code></td>
                  <td>{c.provider}</td>
                  <td>{c.role}</td>
                  <td style={{ fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'JetBrains Mono' }}>
                    {usage[c.model] || 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Failover History */}
        <div className="table-card">
          <div className="table-header">Recent Failover Events Trail</div>
          <table className="data-tbl">
            <thead>
              <tr>
                <th>Time</th>
                <th>Query Context</th>
                <th>Failed Model & Error</th>
                <th>Responded Model</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {failoverHistory.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '24px' }}>
                    No failover incidents recorded. All primary requests completed cleanly.
                  </td>
                </tr>
              ) : (
                failoverHistory.map((ev, eIdx) => (
                  <tr key={eIdx}>
                    <td>{ev.timestamp}</td>
                    <td>{ev.question}</td>
                    <td style={{ color: 'var(--accent-rose)', fontSize: '12px' }}>
                      {JSON.stringify(ev.trail || [])}
                    </td>
                    <td style={{ color: 'var(--accent-emerald)' }}>
                      <code>{ev.succeeded_with}</code>
                    </td>
                    <td>{ev.latency_ms} ms</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
