import React, { useState, useEffect, useMemo } from 'react';
import { ShieldCheck, Activity, Search, UserPlus } from 'lucide-react';
import { useTeamAccess } from './team/useTeamAccess';
import TeamMembersTable from './team/TeamMembersTable';
import PendingInvitationsList from './team/PendingInvitationsList';
import GovernanceActivityFeed from './team/GovernanceActivityFeed';
import GovernanceDomainsGrid from './team/GovernanceDomainsGrid';

export default function TeamAndActivityHub({
  activeOrg,
  showToast,
  initialSubTab = 'directory',
  onSubTabChange,
  onOpenRbacModal,
}) {
  const [activeSubTab, setActiveSubTab] = useState(initialSubTab || 'directory');
  const [activityFilter, setActivityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'reviewer' });

  useEffect(() => {
    if (initialSubTab) setActiveSubTab(initialSubTab);
  }, [initialSubTab]);

  const handleSubTabClick = (tab) => {
    setActiveSubTab(tab);
    onSubTabChange?.(tab);
  };

  const orgId = activeOrg?.id || '';
  const {
    authUser,
    users,
    invites,
    activities,
    activityTotal,
    domainsData,
    capabilities,
    roleCatalog,
    error,
    refreshUsers,
    refreshActivities,
    inviteMember,
    revokeInvite,
    updateUserRole,
    deactivateUser,
  } = useTeamAccess({ orgId, activityFilter, showToast });

  const activeMembersCount = useMemo(
    () => users.filter((u) => String(u.status).toLowerCase() === 'active').length,
    [users]
  );

  const filteredUsers = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.name?.toLowerCase().includes(q) ||
        u.email?.toLowerCase().includes(q) ||
        u.department?.toLowerCase().includes(q) ||
        String(u.role || '').toLowerCase().includes(q)
    );
  }, [users, searchQuery]);

  const filteredActivities = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return activities;
    return activities.filter(
      (a) =>
        a.user_name?.toLowerCase().includes(q) ||
        a.action_type?.toLowerCase().includes(q) ||
        a.target_title?.toLowerCase().includes(q) ||
        a.domain?.toLowerCase().includes(q)
    );
  }, [activities, searchQuery]);

  const handleInviteSubmit = async (e) => {
    e.preventDefault();
    try {
      setInviteSubmitting(true);
      await inviteMember({ email: inviteForm.email, role: inviteForm.role });
      setShowInviteModal(false);
      setInviteForm({ email: '', role: 'reviewer' });
    } catch (err) {
      showToast?.(err.message, 'error');
    } finally {
      setInviteSubmitting(false);
    }
  };

  const roleOptions = Object.keys(roleCatalog || {}).length > 0
    ? Object.entries(roleCatalog).map(([key, meta]) => ({ value: key, label: `${key.toUpperCase()} — ${meta.title}` }))
    : [
        { value: 'data_owner', label: 'DATA_OWNER — Data Steward' },
        { value: 'reviewer', label: 'REVIEWER — Risk Auditor' },
        { value: 'compliance_officer', label: 'COMPLIANCE_OFFICER — Compliance Officer' },
        { value: 'admin', label: 'ADMIN — Chief Compliance Officer' },
        { value: 'developer', label: 'DEVELOPER — Operator / Agent' },
        { value: 'auditor', label: 'AUDITOR — External Auditor' },
        { value: 'viewer', label: 'VIEWER — Compliance Observer' },
      ];

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* 1. Action Controls */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {onOpenRbacModal && (
            <button
              type="button"
              onClick={onOpenRbacModal}
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 13px', fontSize: '0.8rem', fontWeight: 600 }}
            >
              <ShieldCheck size={15} />
              <span>RBAC Matrix</span>
            </button>
          )}
          {capabilities.can_invite_members && (
            <button
              type="button"
              onClick={() => setShowInviteModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', fontSize: '0.8rem', fontWeight: 700 }}
            >
              <UserPlus size={14} />
              <span>Invite Member</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" style={{ padding: '10px 14px', borderRadius: '8px', background: '#FEF2F2', border: '1px solid #FECACA', color: '#991B1B', fontSize: '0.8rem', fontWeight: 600 }}>
          {error}
        </div>
      )}

      {/* 2. Sub-Navigation Tabs */}
      <div role="tablist" aria-label="Team and access sections" style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
        {[
          { id: 'directory', label: 'Members & Invites', count: users.length },
          { id: 'activity', label: 'Audit Activity', count: activities.length },
          { id: 'domains', label: 'Governance Domains', count: domainsData?.domains?.length || 0 },
        ].map((tab) => {
          const active = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => handleSubTabClick(tab.id)}
              className="btn"
              style={{
                padding: '10px 16px',
                fontSize: '0.84rem',
                fontWeight: active ? 800 : 500,
                background: 'transparent',
                border: 'none',
                borderBottom: active ? '2px solid var(--primary)' : '2px solid transparent',
                color: active ? 'var(--primary)' : 'var(--text-muted)',
                cursor: 'pointer',
                borderRadius: 0,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span>{tab.label}</span>
              <span className="badge badge-muted" style={{ fontSize: '0.65rem' }}>{tab.count}</span>
            </button>
          );
        })}
      </div>

      {/* 4. Sub-Views */}
      <div aria-live="polite">
        {activeSubTab === 'directory' && (
          <>
            <TeamMembersTable
              users={filteredUsers}
              authUserId={authUser?.id}
              capabilities={capabilities}
              roleCatalog={roleCatalog}
              onRefresh={refreshUsers}
              onConfirmRoleChange={updateUserRole}
              onConfirmDeactivate={deactivateUser}
              showToast={showToast}
            />
            <PendingInvitationsList
              invites={invites}
              canRevoke={capabilities.can_remove_members}
              onRevoke={revokeInvite}
              showToast={showToast}
            />
          </>
        )}

        {activeSubTab === 'activity' && (
          <GovernanceActivityFeed
            activities={filteredActivities}
            activityFilter={activityFilter}
            onFilterChange={setActivityFilter}
            onRefresh={refreshActivities}
            canViewActivity={capabilities.can_view_activity}
            canExportActivity={capabilities.can_export_activity}
          />
        )}

        {activeSubTab === 'domains' && (
          <GovernanceDomainsGrid domainsData={domainsData} />
        )}
      </div>

      {/* 5. Invite Member Modal (creates pending invite only) */}
      {showInviteModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="invite-modal-title" style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', width: '430px', maxWidth: '92vw', padding: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 id="invite-modal-title" style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)' }}>
                Invite Team Member
              </h3>
              <button type="button" aria-label="Close invite modal" onClick={() => setShowInviteModal(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.1rem', cursor: 'pointer' }}>
                ✕
              </button>
            </div>
            <form onSubmit={handleInviteSubmit}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                Work Email Address
              </label>
              <input
                type="email"
                required
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                placeholder="colleague@company.com"
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginBottom: '12px' }}
              />
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                Intended Role
              </label>
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginBottom: '18px' }}
              >
                {roleOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={() => setShowInviteModal(false)} className="btn btn-secondary" disabled={inviteSubmitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={inviteSubmitting}>
                  {inviteSubmitting ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
