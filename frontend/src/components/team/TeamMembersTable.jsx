import React, { useState } from 'react';

function getInitials(name) {
  if (!name) return 'U';
  const parts = String(name).trim().split(/\s+/);
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() || '').join('') || 'U';
}

function getStatusBadge(status) {
  const s = String(status || 'active').toLowerCase();
  if (s === 'active') return { label: 'Active', bg: '#DCFCE7', color: '#166534', border: '#BBF7D0' };
  if (s === 'invited') return { label: 'Invited', bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE' };
  if (s === 'suspended') return { label: 'Suspended', bg: '#FEF3C7', color: '#92400E', border: '#FDE68A' };
  if (s === 'deactivated' || s === 'inactive') return { label: 'Deactivated', bg: '#F1F5F9', color: '#475569', border: '#CBD5E1' };
  return { label: s, bg: '#F1F5F9', color: '#475569', border: '#CBD5E1' };
}

export default function TeamMembersTable({
  users,
  authUserId,
  capabilities,
  roleCatalog,
  onRefresh,
  onConfirmRoleChange,
  onConfirmDeactivate,
  showToast,
}) {
  const [pendingRoleModal, setPendingRoleModal] = useState(null); // { user, newRole, reason }
  const [pendingDeactivateModal, setPendingDeactivateModal] = useState(null); // { user, reason }
  const [submitting, setSubmitting] = useState(false);

  const availableRoles = Object.keys(roleCatalog || {}).length > 0
    ? Object.entries(roleCatalog).map(([key, meta]) => ({ value: key, label: `${key.toUpperCase()} (${meta.title})` }))
    : [
        { value: 'admin', label: 'ADMIN (Chief Compliance Officer)' },
        { value: 'data_owner', label: 'DATA_OWNER (Data Steward)' },
        { value: 'reviewer', label: 'REVIEWER (Risk Auditor)' },
        { value: 'compliance_officer', label: 'COMPLIANCE_OFFICER (Compliance Officer)' },
        { value: 'developer', label: 'DEVELOPER (Operator / Agent)' },
        { value: 'auditor', label: 'AUDITOR (External Auditor)' },
        { value: 'viewer', label: 'VIEWER (Compliance Observer)' },
      ];

  const handleRoleSubmit = async (e) => {
    e.preventDefault();
    if (!pendingRoleModal) return;
    try {
      setSubmitting(true);
      await onConfirmRoleChange(pendingRoleModal.user.id, pendingRoleModal.newRole, pendingRoleModal.reason);
      setPendingRoleModal(null);
    } catch (err) {
      showToast?.(err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeactivateSubmit = async (e) => {
    e.preventDefault();
    if (!pendingDeactivateModal) return;
    try {
      setSubmitting(true);
      await onConfirmDeactivate(pendingDeactivateModal.user.id, pendingDeactivateModal.reason);
      setPendingDeactivateModal(null);
    } catch (err) {
      showToast?.(err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card" style={{ padding: 0, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
            Organization Members & Roles
          </h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
            Server-enforced RBAC roles and member lifecycle status.
          </p>
        </div>
        <button type="button" onClick={onRefresh} className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
          Refresh
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-card-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <th style={{ padding: '12px 20px' }}>Member</th>
              <th style={{ padding: '12px 16px' }}>Department</th>
              <th style={{ padding: '12px 16px' }}>Role</th>
              <th style={{ padding: '12px 16px' }}>Status</th>
              <th style={{ padding: '12px 20px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '28px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No organization members found.
                </td>
              </tr>
            ) : (
              users.map((u) => {
                const st = getStatusBadge(u.status);
                const isSelf = authUserId && u.id === authUserId;
                const isDeactivated = String(u.status).toLowerCase() === 'deactivated';
                return (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          aria-hidden="true"
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            background: '#EEF2FF',
                            color: '#3730A3',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 800,
                            fontSize: '0.74rem',
                            flexShrink: 0,
                          }}
                        >
                          {getInitials(u.name)}
                        </div>
                        <div>
                          <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                            {u.name}
                            {isSelf && (
                              <span style={{ marginLeft: '6px', fontSize: '0.65rem', padding: '1px 6px', borderRadius: '999px', background: '#DBEAFE', color: '#1E40AF', fontWeight: 700 }}>
                                You
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{u.title || 'Team Member'}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-main)' }}>{u.department || 'General'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      {capabilities.can_change_roles && !isDeactivated ? (
                        <label style={{ display: 'inline-flex', alignItems: 'center' }}>
                          <span className="sr-only" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
                            Role for {u.name}
                          </span>
                          <select
                            aria-label={`Role for ${u.name}`}
                            value={u.role}
                            onChange={(e) => setPendingRoleModal({ user: u, newRole: e.target.value, reason: '' })}
                            style={{
                              padding: '4px 8px',
                              fontSize: '0.75rem',
                              borderRadius: '5px',
                              border: '1px solid var(--border-subtle)',
                              background: 'var(--bg-card-subtle)',
                              color: 'var(--text-main)',
                              fontWeight: 700,
                              cursor: 'pointer',
                            }}
                          >
                            {availableRoles.map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </label>
                      ) : (
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          {String(u.role).toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: '999px',
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          background: st.bg,
                          color: st.color,
                          border: `1px solid ${st.border}`,
                        }}
                      >
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '12px 20px', textAlign: 'right' }}>
                      {capabilities.can_remove_members && !isDeactivated && !isSelf ? (
                        <button
                          type="button"
                          onClick={() => setPendingDeactivateModal({ user: u, reason: '' })}
                          className="btn btn-secondary"
                          aria-label={`Deactivate ${u.name}`}
                          style={{
                            fontSize: '0.72rem',
                            padding: '4px 10px',
                            color: '#B91C1C',
                            borderColor: '#FCA5A5',
                            background: '#FEF2F2',
                            fontWeight: 600,
                          }}
                        >
                          Deactivate
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Role Change Confirmation Dialog */}
      {pendingRoleModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="role-confirm-title" style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <form onSubmit={handleRoleSubmit} style={{ width: '420px', maxWidth: '92vw', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px' }}>
            <h4 id="role-confirm-title" style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
              Confirm Role Change
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 12px 0' }}>
              Change <strong>{pendingRoleModal.user.name}</strong> from <strong>{String(pendingRoleModal.user.role).toUpperCase()}</strong> to{' '}
              <strong>{String(pendingRoleModal.newRole).toUpperCase()}</strong>? This change is audited immediately.
            </p>
            <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
              Audit Reason (optional)
            </label>
            <input
              type="text"
              value={pendingRoleModal.reason}
              onChange={(e) => setPendingRoleModal({ ...pendingRoleModal, reason: e.target.value })}
              placeholder="e.g. Quarterly access review"
              style={{ width: '100%', padding: '8px 10px', fontSize: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" onClick={() => setPendingRoleModal(null)} className="btn btn-secondary" disabled={submitting}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Saving...' : 'Confirm Change'}</button>
            </div>
          </form>
        </div>
      )}

      {/* Deactivate Confirmation Dialog */}
      {pendingDeactivateModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="deactivate-confirm-title" style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <form onSubmit={handleDeactivateSubmit} style={{ width: '420px', maxWidth: '92vw', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px' }}>
            <h4 id="deactivate-confirm-title" style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: 800, color: '#991B1B' }}>
              Deactivate Member
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 12px 0' }}>
              Deactivating <strong>{pendingDeactivateModal.user.name}</strong> revokes all active sessions while preserving governance audit history.
            </p>
            <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
              Reason
            </label>
            <input
              type="text"
              required
              value={pendingDeactivateModal.reason}
              onChange={(e) => setPendingDeactivateModal({ ...pendingDeactivateModal, reason: e.target.value })}
              placeholder="e.g. Offboarding or role transfer"
              style={{ width: '100%', padding: '8px 10px', fontSize: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" onClick={() => setPendingDeactivateModal(null)} className="btn btn-secondary" disabled={submitting}>Cancel</button>
              <button type="submit" className="btn btn-primary" style={{ background: '#DC2626', borderColor: '#DC2626' }} disabled={submitting}>
                {submitting ? 'Deactivating...' : 'Deactivate Member'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
