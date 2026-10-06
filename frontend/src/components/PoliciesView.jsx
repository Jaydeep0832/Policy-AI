import React, { useState, useEffect } from 'react';
import { API_BASE } from '../apiConfig';

export default function PoliciesView() {
  const [policies, setPolicies] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetch(`${API_BASE}/policies`)
      .then((res) => res.json())
      .then((data) => setPolicies(data))
      .catch((err) => console.error('Failed to load policies:', err));
  }, []);

  const filtered = policies.filter((p) => {
    if (filter === 'all') return true;
    return p.status === filter;
  });

  return (
    <div className="view-panel">
      <div className="dashboard-wrap">
        <div className="dashboard-head">
          <h2>Institutional Policy Corpus & Lifecycle Manifest</h2>
          <p>
            Authoritative catalog of official policies, statutory regulations, draft fixtures, and superseded documents indexed across the primary and shadow vector spaces.
          </p>
        </div>

        {/* Filter Chips */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {['all', 'approved', 'superseded', 'draft', 'expired'].map((st) => (
            <button
              key={st}
              className={`btn-secondary ${filter === st ? 'active' : ''}`}
              style={{
                textTransform: 'capitalize',
                borderColor: filter === st ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                color: filter === st ? 'var(--accent-cyan)' : 'var(--text-muted)'
              }}
              onClick={() => setFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Policies Table */}
        <div className="table-card">
          <table className="data-tbl">
            <thead>
              <tr>
                <th>Document Title</th>
                <th>Status</th>
                <th>Version</th>
                <th>Effective Date</th>
                <th>Precedence</th>
                <th>Role in Assistant</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, idx) => {
                let statusColor = 'var(--accent-emerald)';
                if (p.status === 'superseded') statusColor = 'var(--text-dim)';
                if (p.status === 'draft') statusColor = 'var(--accent-amber)';
                if (p.status === 'expired') statusColor = 'var(--accent-rose)';

                return (
                  <tr key={idx}>
                    <td>
                      <strong>{p.title}</strong>
                      <br />
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'JetBrains Mono' }}>
                        {p.file_name}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: statusColor, fontWeight: 700, textTransform: 'uppercase', fontSize: '11px' }}>
                        {p.status}
                      </span>
                    </td>
                    <td><code>{p.version}</code></td>
                    <td>{p.effective_date}</td>
                    <td>Tier {p.precedence_rank}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {p.description}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
