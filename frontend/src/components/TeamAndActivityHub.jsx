import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function TeamAndActivityHub({
  activeOrg,
  activePersona,
  onSelectPersona,
  showToast,
  initialSubTab = 'directory',
  onSubTabChange,
  onLaunchSetupWizard,
  onOpenRbacModal
}) {
  const { user: currentAuthUser, refreshPersonas } = useAuth();
  const [activeSubTab, setActiveSubTab] = useState(initialSubTab || 'directory'); // 'directory', 'activity', 'domains'

  useEffect(() => {
    if (initialSubTab) {
      setActiveSubTab(initialSubTab);
    }
  }, [initialSubTab]);

  const handleSubTabClick = (tab) => {
    setActiveSubTab(tab);
    onSubTabChange?.(tab);
  };
  const [users, setUsers] = useState([]);
  const [activities, setActivities] = useState([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityFilter, setActivityFilter] = useState('all');
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    name: '',
    email: '',
    role: 'data_owner',
    title: '',
    department: 'Data Platform',
  });

  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';

  // Fetch Users
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/v1/users?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch Activities
  const fetchActivities = async () => {
    try {
      const url = activityFilter === 'all'
        ? `/v1/users/activity?organization_id=${orgId}&limit=50`
        : `/v1/users/activity?organization_id=${orgId}&limit=50&action_type=${activityFilter}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setActivities(data.activities || []);
        setActivityTotal(data.total || 0);
      }
    } catch (err) {
      console.error('Failed to load activities:', err);
    }
  };

  // Fetch Domains
  const fetchDomains = async () => {
    try {
      const res = await fetch(`/v1/users/domains?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setDomains(data);
      }
    } catch (err) {
      console.error('Failed to load domains:', err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchActivities();
    fetchDomains();
  }, [orgId, activityFilter]);

  // Handle Role Change
  const handleRoleChange = async (userId, newRole) => {
    try {
      const res = await fetch(`/v1/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUsers(prev => prev.map(u => (u.id === userId ? updated : u)));
        showToast(`Updated role for ${updated.name} to ${newRole.toUpperCase()}`);
        if (refreshPersonas) refreshPersonas();
        fetchActivities();
      }
    } catch (err) {
      showToast('Failed to update user role', 'error');
    }
  };

  // Handle Invite Member
  const handleInviteMember = async (e) => {
    e.preventDefault();
    try {
      // 1. Create or bind user membership
      const res = await fetch('/v1/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          name: inviteForm.name,
          email: inviteForm.email,
          role: inviteForm.role,
          title: inviteForm.title || `${inviteForm.role.replace('_', ' ').toUpperCase()}`,
          department: inviteForm.department,
        }),
      });

      // 2. Also register official pending invitation token
      await fetch(`/v1/organizations/${orgId}/invites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: inviteForm.email,
          role: inviteForm.role,
        }),
      }).catch(err => console.warn('Invite token registration:', err));

      if (res.ok) {
        const newUser = await res.json();
        setUsers(prev => [...prev, newUser]);
        setShowInviteModal(false);
        setInviteForm({ name: '', email: '', role: 'reviewer', title: '', department: 'Governance & Risk' });
        showToast(`Invited ${newUser.name} as ${newUser.role.toUpperCase()} to ${activeOrg?.name || 'organization'}`);
        if (refreshPersonas) refreshPersonas();
        fetchActivities();
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to invite user', 'error');
      }
    } catch (err) {
      showToast('Network error while inviting user', 'error');
    }
  };

  // Handle Delete Member
  const handleDeleteMember = async (userId, userName) => {
    if (!window.confirm(`Are you sure you want to remove ${userName} from the organization?`)) {
      return;
    }
    try {
      const res = await fetch(`/v1/users/${userId}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        setUsers(prev => prev.filter(u => u.id !== userId));
        showToast(`Removed ${userName} from organization.`);
        if (refreshPersonas) refreshPersonas();
        fetchActivities();
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast(errData.detail || 'Failed to remove member', 'error');
      }
    } catch (err) {
      showToast('Network error removing member', 'error');
    }
  };

  const getRoleBadgeClass = (role) => {
    switch (role) {
      case 'admin':
        return 'badge-verified';
      case 'data_owner':
        return 'badge-warning';
      case 'reviewer':
        return 'badge-review';
      case 'developer':
        return 'badge-primary';
      default:
        return 'badge-muted';
    }
  };

  const getActionBadgeClass = (actionType) => {
    if (actionType.includes('SYNC')) return 'badge-verified';
    if (actionType.includes('CONFLICT') || actionType.includes('RESOLV')) return 'badge-review';
    if (actionType.includes('ROLE') || actionType.includes('MEMBER')) return 'badge-warning';
    if (actionType.includes('EXPORT') || actionType.includes('AUDIT')) return 'badge-primary';
    return 'badge-muted';
  };

  const formatTimeAgo = (dateStr) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffSecs = Math.floor((now - date) / 1000);
      if (diffSecs < 60) return 'Just now';
      if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
      if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
      return `${Math.floor(diffSecs / 86400)}d ago`;
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 1. Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.6rem' }}>👥</span>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
              Team, Personas & Governance Ecosystem
            </h1>
            <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
              Atlan Active Governance
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '6px', maxWidth: '750px' }}>
            Multi-user collaboration, granular persona-based access control (RBAC), data mesh domain ownership, and immutable collaborative activity audit trails.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {onLaunchSetupWizard && (
            <button
              onClick={() => onLaunchSetupWizard(activeOrg)}
              className="btn btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', fontSize: '0.82rem', fontWeight: 600 }}
              title="Launch Guided Organization Onboarding & Setup Wizard"
            >
              <span>🚀 Setup Wizard</span>
            </button>
          )}
          {onOpenRbacModal && (
            <button
              onClick={onOpenRbacModal}
              className="btn btn-secondary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                fontSize: '0.82rem',
                fontWeight: 600,
                background: '#FFFFFF',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                color: '#0F172A',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
              onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
              title="Inspect Atlan-Grade RBAC Permissions & Separation of Duties Matrix"
            >
              <ShieldCheck size={15} style={{ color: '#0F172A' }} />
              <span>RBAC Matrix</span>
            </button>
          )}
          <button
            onClick={() => setShowInviteModal(true)}
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', fontSize: '0.82rem', fontWeight: 700 }}
          >
            <span>+ Invite Member</span>
          </button>
        </div>
      </div>

      {/* 2. Top Summary KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        
        {/* Card 1: Active Team Members */}
        <div className="card" style={{ padding: '18px 20px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Active Team Members
            </span>
            <span style={{ fontSize: '1.2rem' }}>👥</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--text-main)' }}>
            {users.length}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--success-text)', marginTop: '4px' }}>
            ● 100% Active Directory Linked
          </div>
        </div>

        {/* Card 2: Governance Domains */}
        <div className="card" style={{ padding: '18px 20px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Data Mesh Domains
            </span>
            <span style={{ fontSize: '1.2rem' }}>🌐</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--text-main)' }}>
            {domains.length || 4}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--primary)', marginTop: '4px' }}>
            Finance, Eng, Risk, AI Mesh
          </div>
        </div>

        {/* Card 3: Collaborative Events */}
        <div className="card" style={{ padding: '18px 20px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Recorded Actions
            </span>
            <Activity size={18} color="var(--primary)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--text-main)' }}>
            {activityTotal || activities.length}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Collaborative sync & review log
          </div>
        </div>

        {/* Card 4: Active Simulated Persona */}
        <div className="card" style={{ padding: '18px 20px', background: 'var(--bg-card-subtle)', border: '1px solid var(--primary)', borderRadius: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--primary)', textTransform: 'uppercase' }}>
              Current Active Persona
            </span>
            <span className={`badge ${getRoleBadgeClass(activePersona?.role)}`} style={{ fontSize: '0.65rem' }}>
              {activePersona?.role?.toUpperCase()}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <img
              src={activePersona?.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${activePersona?.name || 'Admin'}`}
              alt="avatar"
              style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--bg-card)' }}
            />
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.2 }}>
                {activePersona?.name || 'Sarah Chen'}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {activePersona?.title || 'Chief Compliance Officer'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Sub Navigation Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '24px' }}>
        <button
          onClick={() => handleSubTabClick('directory')}
          className="btn"
          style={{
            padding: '10px 18px',
            fontSize: '0.85rem',
            fontWeight: activeSubTab === 'directory' ? 800 : 500,
            background: 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'directory' ? '2px solid var(--primary)' : '2px solid transparent',
            color: activeSubTab === 'directory' ? 'var(--primary)' : 'var(--text-muted)',
            cursor: 'pointer',
            borderRadius: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>👥 Team Directory & Personas</span>
          <span className="badge badge-muted" style={{ fontSize: '0.65rem' }}>{users.length}</span>
        </button>

        <button
          onClick={() => handleSubTabClick('activity')}
          className="btn"
          style={{
            padding: '10px 18px',
            fontSize: '0.85rem',
            fontWeight: activeSubTab === 'activity' ? 800 : 500,
            background: 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'activity' ? '2px solid var(--primary)' : '2px solid transparent',
            color: activeSubTab === 'activity' ? 'var(--primary)' : 'var(--text-muted)',
            cursor: 'pointer',
            borderRadius: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>Collaborative Activity Feed</span>
          <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>Live</span>
        </button>

        <button
          onClick={() => handleSubTabClick('domains')}
          className="btn"
          style={{
            padding: '10px 18px',
            fontSize: '0.85rem',
            fontWeight: activeSubTab === 'domains' ? 800 : 500,
            background: 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'domains' ? '2px solid var(--primary)' : '2px solid transparent',
            color: activeSubTab === 'domains' ? 'var(--primary)' : 'var(--text-muted)',
            cursor: 'pointer',
            borderRadius: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>🌐 Data Mesh Domains & Stewardship</span>
          <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>4 Domains</span>
        </button>
      </div>

      {/* 4. Sub-view 1: Team Directory & Roles */}
      {activeSubTab === 'directory' && (
        <div className="card" style={{ padding: '0', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                Organization Members & Roles
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                Manage team permissions, Atlan persona assignments, and active user roles.
              </p>
            </div>
            <button
              onClick={fetchUsers}
              className="btn btn-secondary"
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              ↻ Refresh
            </button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'var(--bg-card-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  <th style={{ padding: '12px 20px' }}>User & Title</th>
                  <th style={{ padding: '12px 16px' }}>Email</th>
                  <th style={{ padding: '12px 16px' }}>Department</th>
                  <th style={{ padding: '12px 16px' }}>Persona Role</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 20px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '14px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <img
                          src={u.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.name}`}
                          alt="avatar"
                          style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--bg-card-subtle)' }}
                        />
                        <div>
                          <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                            {u.name}
                            {activePersona?.id === u.id && (
                              <span className="badge badge-verified" style={{ marginLeft: '6px', fontSize: '0.62rem', padding: '1px 4px' }}>
                                Active Switcher
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {u.title || 'Team Member'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: '0.78rem' }}>
                      {u.email}
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-main)', fontWeight: 500 }}>
                      {u.department || 'General'}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        style={{
                          padding: '4px 8px',
                          fontSize: '0.75rem',
                          borderRadius: '4px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-card-subtle)',
                          color: 'var(--text-main)',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        <option value="admin">ADMIN (Compliance & Org)</option>
                        <option value="data_owner">DATA_OWNER (Eng & Sources)</option>
                        <option value="reviewer">REVIEWER (Data Steward)</option>
                        <option value="developer">DEVELOPER (AI & MCP)</option>
                        <option value="viewer">VIEWER (Read Only)</option>
                      </select>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>
                        ACTIVE
                      </span>
                    </td>
                    <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
                        <button
                          onClick={() => {
                            onSelectPersona(u);
                            showToast(`Switched active persona to ${u.name} (${u.role.toUpperCase()})`);
                          }}
                          className="btn btn-secondary"
                          style={{ fontSize: '0.72rem', padding: '4px 10px', fontWeight: 600 }}
                        >
                          Switch Persona
                        </button>
                        {u.role !== 'admin' && (
                          <button
                            onClick={() => handleDeleteMember(u.id, u.name)}
                            className="btn btn-secondary"
                            title="Remove member from organization"
                            style={{
                              fontSize: '0.72rem',
                              padding: '4px 8px',
                              color: '#EF4444',
                              borderColor: '#FCA5A5',
                              background: '#FEF2F2',
                              fontWeight: 600,
                              cursor: 'pointer'
                            }}
                          >
                            🗑️ Remove
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 5. Sub-view 2: Collaborative Activity Feed */}
      {activeSubTab === 'activity' && (
        <div>
          {/* Activity Filters */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
              Filter By Action:
            </span>
            {['all', 'SOURCE_SYNCED', 'CONFLICT_RESOLVED', 'MEMBER_INVITED', 'ROLE_UPDATED', 'SOURCE_CREATED'].map((filter) => (
              <button
                key={filter}
                onClick={() => setActivityFilter(filter)}
                className={`btn ${activityFilter === filter ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.72rem', padding: '4px 10px', borderRadius: '20px', textTransform: 'uppercase' }}
              >
                {filter.replace('_', ' ')}
              </button>
            ))}
          </div>

          <div className="card" style={{ padding: '0', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                  Collaborative Governance Stream ({activities.length} Events)
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                  Real-time timeline of crawler runs, policy approvals, and team governance.
                </p>
              </div>
              <button
                onClick={fetchActivities}
                className="btn btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 10px' }}
              >
                ↻ Refresh Stream
              </button>
            </div>

            {activities.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📜</div>
                <div style={{ fontWeight: 700 }}>No activities recorded yet</div>
                <div style={{ fontSize: '0.78rem', marginTop: '4px' }}>
                  Sync a data connector or resolve a conflict to start generating collaborative audit entries.
                </div>
              </div>
            ) : (
              <div style={{ padding: '8px 0' }}>
                {activities.map((act) => (
                  <div
                    key={act.id}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '14px',
                      padding: '14px 20px',
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.2s',
                    }}
                  >
                    <div style={{ fontSize: '1.3rem', marginTop: '2px' }}>
                      {act.action_type.includes('SYNC') ? '🔄' :
                       act.action_type.includes('CONFLICT') ? '⚔️' :
                       act.action_type.includes('ROLE') ? '🛡️' :
                       act.action_type.includes('MEMBER') ? '👤' : '📜'}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 800, color: 'var(--text-main)', fontSize: '0.84rem' }}>
                          {act.user_name}
                        </span>
                        <span className={`badge ${getRoleBadgeClass(act.user_role)}`} style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                          {act.user_role?.toUpperCase()}
                        </span>
                        <span className={`badge ${getActionBadgeClass(act.action_type)}`} style={{ fontSize: '0.62rem', padding: '1px 6px' }}>
                          {act.action_type}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          {formatTimeAgo(act.created_at)}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.82rem', color: 'var(--text-main)', marginTop: '4px' }}>
                        Target: <strong style={{ color: 'var(--primary)' }}>{act.target_title || act.target_id || 'Resource'}</strong> ({act.target_type}) in domain <span className="badge badge-muted" style={{ fontSize: '0.62rem' }}>{act.domain}</span>
                      </div>

                      {act.details && Object.keys(act.details).length > 0 && (
                        <div style={{
                          marginTop: '6px',
                          padding: '6px 10px',
                          background: 'var(--bg-card-subtle)',
                          borderRadius: '6px',
                          fontSize: '0.74rem',
                          fontFamily: 'monospace',
                          color: 'var(--text-muted)'
                        }}>
                          {JSON.stringify(act.details)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. Sub-view 3: Data Mesh Domains & Stewardship */}
      {activeSubTab === 'domains' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {domains.map((dom) => (
            <div
              key={dom.id}
              className="card"
              style={{
                padding: '20px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.4rem' }}>
                      {dom.id.includes('finance') ? '💳' :
                       dom.id.includes('eng') ? '⚙️' :
                       dom.id.includes('compliance') ? '⚖️' : '📁'}
                    </span>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {dom.name}
                      </h4>
                      <span className="badge badge-warning" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                        {dom.sensitivity}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.2rem', fontWeight: 900, color: 'var(--success-text)' }}>
                      {dom.trust_score_avg}%
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Trust Score</div>
                  </div>
                </div>

                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '10px 0 16px 0', lineHeight: 1.4 }}>
                  {dom.description}
                </p>

                {/* Domain Lead */}
                <div style={{ padding: '10px 12px', background: 'var(--bg-card-subtle)', borderRadius: '8px', marginBottom: '14px' }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                    Domain Lead / Steward
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <img src={dom.lead_avatar} alt="lead" style={{ width: 24, height: 24, borderRadius: '50%' }} />
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)' }}>{dom.lead_name}</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{dom.lead_role}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)' }}>{dom.data_sources_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Data Sources</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)' }}>{dom.claims_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Verified Claims</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 7. Invite Member Modal */}
      {showInviteModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.6)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            width: '460px',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                👤 Invite Team Member
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.1rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInviteMember}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={inviteForm.name}
                  onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
                  placeholder="e.g. Jordan Mitchell"
                  style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  placeholder="jordan.mitchell@demo.local"
                  style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Persona Role
                </label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)', color: 'var(--text-main)' }}
                >
                  <option value="data_owner">DATA_OWNER (Data Engineer - Crawlers & Sync)</option>
                  <option value="reviewer">REVIEWER (Data Steward - Policy & Conflicts)</option>
                  <option value="admin">ADMIN (Compliance Officer - SOC2 & RBAC)</option>
                  <option value="developer">DEVELOPER (AI Platform - MCP & Keys)</option>
                  <option value="viewer">VIEWER (Business User - Read Only)</option>
                </select>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Job Title
                </label>
                <input
                  type="text"
                  value={inviteForm.title}
                  onChange={(e) => setInviteForm({ ...inviteForm, title: e.target.value })}
                  placeholder="e.g. Senior Data Steward"
                  style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Department / Domain
                </label>
                <input
                  type="text"
                  value={inviteForm.department}
                  onChange={(e) => setInviteForm({ ...inviteForm, department: e.target.value })}
                  placeholder="e.g. Finance & Billing"
                  style={{ width: '100%', padding: '8px 10px', fontSize: '0.82rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.82rem', padding: '8px 16px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ fontSize: '0.82rem', padding: '8px 16px', fontWeight: 700 }}
                >
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
