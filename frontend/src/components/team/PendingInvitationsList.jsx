import React, { useState } from 'react';

export default function PendingInvitationsList({ invites, canRevoke, onRevoke, showToast }) {
  const [revokingId, setRevokingId] = useState(null);

  if (!invites || invites.length === 0) {
    return null;
  }

  const handleRevoke = async (inv) => {
    try {
      setRevokingId(inv.id);
      await onRevoke(inv.id);
    } catch (err) {
      showToast?.(err.message, 'error');
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className="card" style={{ padding: 0, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden', marginTop: '16px' }}>
      <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
          Pending Invitations ({invites.length})
        </h3>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Pending invites are not active members until accepted.
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-card-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '10px 20px' }}>Email</th>
              <th style={{ padding: '10px 16px' }}>Intended Role</th>
              <th style={{ padding: '10px 16px' }}>Status</th>
              <th style={{ padding: '10px 16px' }}>Expires</th>
              <th style={{ padding: '10px 20px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invites.map((inv) => (
              <tr key={inv.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '10px 20px', fontFamily: 'monospace' }}>{inv.email}</td>
                <td style={{ padding: '10px 16px', fontWeight: 700 }}>{String(inv.role).toUpperCase()}</td>
                <td style={{ padding: '10px 16px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '0.68rem', fontWeight: 700, background: '#EFF6FF', color: '#1D4ED8', border: '1px solid #BFDBFE' }}>
                    {inv.status}
                  </span>
                </td>
                <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>
                  {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : '—'}
                </td>
                <td style={{ padding: '10px 20px', textAlign: 'right' }}>
                  {canRevoke ? (
                    <button
                      type="button"
                      onClick={() => handleRevoke(inv)}
                      disabled={revokingId === inv.id}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.72rem', padding: '4px 10px', color: '#B91C1C', borderColor: '#FCA5A5', background: '#FEF2F2' }}
                    >
                      {revokingId === inv.id ? 'Revoking...' : 'Revoke'}
                    </button>
                  ) : (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
