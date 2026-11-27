import React from 'react';

export default function GovernanceDomainsGrid({ domainsData }) {
  const domains = domainsData?.domains || [];
  const isPreview = Boolean(domainsData?.is_preview);

  if (domains.length === 0) {
    return (
      <div className="card" style={{ padding: '32px', textAlign: 'center', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px', color: 'var(--text-muted)' }}>
        No governance domains or workspaces found in the authorized scope.
      </div>
    );
  }

  return (
    <div>
      {isPreview && (
        <div style={{ marginBottom: '12px', padding: '8px 12px', borderRadius: '8px', background: '#FFFBEB', border: '1px solid #FDE68A', color: '#92400E', fontSize: '0.78rem', fontWeight: 600 }}>
          Governance domains: preview data
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        {domains.map((dom) => (
          <div
            key={dom.id}
            className="card"
            style={{
              padding: '18px 20px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>{dom.name}</h4>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                  {dom.folder_type || 'workspace'}
                </span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--text-main)' }}>
                  {dom.average_trust_score != null ? `${dom.average_trust_score}%` : '—'}
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>Avg Trust Score</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 800 }}>{dom.source_count ?? '—'}</div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>Sources</div>
              </div>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 800 }}>{dom.claim_count ?? '—'}</div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>Claims</div>
              </div>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 800 }}>{dom.verified_claim_count ?? '—'}</div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>Verified</div>
              </div>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: (dom.open_conflict_count || 0) > 0 ? '#C2410C' : 'var(--text-main)' }}>
                  {dom.open_conflict_count ?? '—'}
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>Conflicts</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
