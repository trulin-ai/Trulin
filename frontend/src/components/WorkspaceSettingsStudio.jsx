import React, { useState, useEffect } from 'react';
import {
  Building2,
  Globe,
  Users,
  Mail,
  Plus,
  Trash2,
  Copy,
  Check,
  Shield,
  Clock,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  ArrowLeft,
  Lock,
  Sliders,
  Key,
  ShieldCheck,
  Settings,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function WorkspaceSettingsStudio({
  activeOrg,
  onOrgUpdated,
  onBack,
  onOpenRbacModal,
  showToast
}) {
  const { token, user: currentUser } = useAuth();

  const [activeTab, setActiveTab] = useState('domains'); // 'domains' | 'members' | 'invites' | 'security' | 'general'
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // General & Domain Whitelist states
  const [orgName, setOrgName] = useState('');
  const [orgSlug, setOrgSlug] = useState('');
  const [domains, setDomains] = useState([]);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [authMethods, setAuthMethods] = useState(['google']);

  // Members states
  const [members, setMembers] = useState([]);
  const [membersLoading, setMembersLoading] = useState(false);

  // Invites states
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('reviewer');
  const [invites, setInvites] = useState([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [lastCreatedInvite, setLastCreatedInvite] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    setOrgName(activeOrg.name || 'Trulin Trust Workspace');
    setOrgSlug(activeOrg.slug || 'demo');
    setDomains(activeOrg.domain_whitelist || ['trulin.ai', 'demo.com', 'gmail.com']);
    setAuthMethods(activeOrg.allowed_auth_methods?.length ? activeOrg.allowed_auth_methods : ['google']);

    fetchOrgDetails();
    fetchMembers();
    fetchInvites();
  }, [activeOrg?.id]);

  const fetchOrgDetails = async () => {
    if (!activeOrg?.id) return;
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/settings`);
      if (res.ok) {
        const data = await res.json();
        setOrgName(data.name);
        setOrgSlug(data.slug);
        setDomains(data.domain_whitelist || []);
        if (data.allowed_auth_methods) setAuthMethods(data.allowed_auth_methods);
      }
    } catch (err) {
      console.warn('Failed to fetch org details:', err);
    }
  };

  const fetchMembers = async () => {
    if (!activeOrg?.id) return;
    setMembersLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      }
    } catch (err) {
      console.warn('Failed to fetch org members:', err);
    } finally {
      setMembersLoading(false);
    }
  };

  const fetchInvites = async () => {
    if (!activeOrg?.id) return;
    setInvitesLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites`);
      if (res.ok) {
        const data = await res.json();
        setInvites(data);
      }
    } catch (err) {
      console.warn('Failed to fetch invites:', err);
    } finally {
      setInvitesLoading(false);
    }
  };

  const handleAddDomain = () => {
    if (!newDomainInput.trim()) return;
    const cleanDomain = newDomainInput.trim().toLowerCase().replace(/^@/, '');
    if (domains.includes(cleanDomain)) {
      setErrorMsg(`Domain '@${cleanDomain}' is already in the authorized whitelist.`);
      return;
    }
    setDomains([...domains, cleanDomain]);
    setNewDomainInput('');
    setErrorMsg(null);
  };

  const handleRemoveDomain = (domainToRemove) => {
    setDomains(domains.filter((d) => d !== domainToRemove));
  };

  const handleToggleAuthMethod = (methodKey) => {
    if (authMethods.includes(methodKey)) {
      if (authMethods.length === 1) {
        setErrorMsg('At least one authentication method must remain active.');
        return;
      }
      setAuthMethods(authMethods.filter((m) => m !== methodKey));
    } else {
      setAuthMethods([...authMethods, methodKey]);
    }
    setErrorMsg(null);
  };

  const handleSaveSettings = async (e) => {
    if (e) e.preventDefault();
    if (!activeOrg?.id) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/settings`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: orgName.trim(),
          domain_whitelist: domains,
          allowed_auth_methods: authMethods
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save workspace configuration.');
      }

      const updated = await res.json();
      setSuccessMsg('Workspace settings saved and applied across all gateways!');
      if (onOrgUpdated) onOrgUpdated(updated);
      if (showToast) showToast('Workspace settings successfully updated', 'success');
    } catch (err) {
      setErrorMsg(err.message || 'Error saving workspace configuration.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail || !inviteEmail.includes('@')) {
      setErrorMsg('Please enter a valid recipient email address.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setInvitesLoading(true);

    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: inviteEmail.trim().toLowerCase(),
          role: inviteRole,
          expires_days: 7
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate invitation.');
      }

      const data = await res.json();
      setLastCreatedInvite(data);
      setInviteEmail('');
      setSuccessMsg(`Invitation generated for ${data.email}!`);
      fetchInvites();
      if (showToast) showToast(`Invite link created for ${data.email}`, 'success');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to dispatch workspace invitation.');
    } finally {
      setInvitesLoading(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites/${inviteId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setInvites(invites.filter((i) => i.id !== inviteId));
        if (showToast) showToast('Invitation link revoked', 'info');
      }
    } catch (err) {
      console.warn('Failed to revoke invite:', err);
    }
  };

  const handleCopyLink = (tokenValue) => {
    const link = `${window.location.origin}/invite/${tokenValue}`;
    navigator.clipboard.writeText(link);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const handleMemberRoleChange = async (memberId, newRole) => {
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/members/${memberId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) {
        const updatedUser = await res.json();
        setMembers(members.map((m) => (m.id === memberId ? updatedUser : m)));
        if (showToast) showToast(`Member role updated to ${newRole.toUpperCase()}`, 'success');
      }
    } catch (err) {
      console.warn('Failed to update member role:', err);
    }
  };

  const getRoleBadge = (role) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return { label: 'ADMIN / CCO', bg: '#ECFDF5', color: '#047857', border: '#A7F3D0' };
      case 'data_owner':
        return { label: 'DATA STEWARD', bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE' };
      case 'reviewer':
        return { label: 'RISK AUDITOR', bg: '#FFF7ED', color: '#C2410C', border: '#FED7AA' };
      case 'developer':
        return { label: 'ENGINEER', bg: '#FDF4FF', color: '#86198F', border: '#F5D0FE' };
      default:
        return { label: 'OPERATOR', bg: '#F1F5F9', color: '#475569', border: '#E2E8F0' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1280px', margin: '0 auto', paddingBottom: '40px' }}>
      {/* 1. Top Header Bar with Breadcrumb & Back Action */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="btn btn-secondary"
              style={{ padding: '7px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={14} />
              <span>Back</span>
            </button>
          )}

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.66rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#EA580C' }}>
                Governance & Identity Control
              </span>
              <span
                style={{
                  fontSize: '0.62rem',
                  fontWeight: 700,
                  padding: '1px 6px',
                  borderRadius: '10px',
                  backgroundColor: '#ECFDF5',
                  color: '#047857',
                  border: '1px solid #A7F3D0'
                }}
              >
                ● Active Tenant
              </span>
            </div>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-main)', margin: '2px 0 0 0', letterSpacing: '-0.02em' }}>
              Workspace Settings & Identity Governance
            </h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {onOpenRbacModal && (
            <button
              type="button"
              onClick={onOpenRbacModal}
              className="btn btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.82rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}
              title="Inspect Enterprise RBAC Permissions & Separation of Duties Matrix"
            >
              <ShieldCheck size={14} />
              <span>RBAC Matrix</span>
            </button>
          )}
          <button
            type="button"
            onClick={handleSaveSettings}
            disabled={loading}
            className="btn btn-primary"
            style={{
              padding: '8px 18px',
              fontSize: '0.82rem',
              fontWeight: 700,
              backgroundColor: '#EA580C',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {loading ? <RefreshCw size={14} className="spinning" /> : <Check size={14} strokeWidth={2.5} />}
            <span>Save Workspace Settings</span>
          </button>
        </div>
      </div>

      {/* Error & Success Feedback Alerts */}
      {errorMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            borderRadius: '8px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FECACA',
            color: '#B91C1C',
            fontSize: '0.82rem'
          }}
        >
          <AlertCircle size={16} color="#DC2626" style={{ flexShrink: 0 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            borderRadius: '8px',
            backgroundColor: '#ECFDF5',
            border: '1px solid #A7F3D0',
            color: '#047857',
            fontSize: '0.82rem'
          }}
        >
          <CheckCircle2 size={16} color="#10B981" style={{ flexShrink: 0 }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 2. Navigation Tab Switcher */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', gap: '4px' }}>
        <button
          type="button"
          onClick={() => { setActiveTab('domains'); setErrorMsg(null); }}
          style={{
            padding: '10px 18px',
            borderBottom: activeTab === 'domains' ? '2.5px solid #EA580C' : '2.5px solid transparent',
            color: activeTab === 'domains' ? '#EA580C' : 'var(--text-secondary)',
            fontWeight: activeTab === 'domains' ? 700 : 500,
            fontSize: '0.84rem',
            background: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Globe size={16} />
          <span>Domain Whitelist & Routing</span>
          <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '10px', backgroundColor: 'var(--bg-card)', color: 'var(--text-muted)' }}>
            {domains.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('members'); setErrorMsg(null); }}
          style={{
            padding: '10px 18px',
            borderBottom: activeTab === 'members' ? '2.5px solid #EA580C' : '2.5px solid transparent',
            color: activeTab === 'members' ? '#EA580C' : 'var(--text-secondary)',
            fontWeight: activeTab === 'members' ? 700 : 500,
            fontSize: '0.84rem',
            background: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Users size={16} />
          <span>Members & Clearances</span>
          <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '10px', backgroundColor: 'var(--bg-card)', color: 'var(--text-muted)' }}>
            {members.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('invites'); setErrorMsg(null); }}
          style={{
            padding: '10px 18px',
            borderBottom: activeTab === 'invites' ? '2.5px solid #EA580C' : '2.5px solid transparent',
            color: activeTab === 'invites' ? '#EA580C' : 'var(--text-secondary)',
            fontWeight: activeTab === 'invites' ? 700 : 500,
            fontSize: '0.84rem',
            background: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Mail size={16} />
          <span>Invitations & Magic Links</span>
          <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '10px', backgroundColor: 'var(--bg-card)', color: 'var(--text-muted)' }}>
            {invites.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('security'); setErrorMsg(null); }}
          style={{
            padding: '10px 18px',
            borderBottom: activeTab === 'security' ? '2.5px solid #EA580C' : '2.5px solid transparent',
            color: activeTab === 'security' ? '#EA580C' : 'var(--text-secondary)',
            fontWeight: activeTab === 'security' ? 700 : 500,
            fontSize: '0.84rem',
            background: 'transparent',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <ShieldCheck size={16} />
          <span>SSO & Auth Providers</span>
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: DOMAIN WHITELIST & ROUTING                         */}
      {/* ========================================================= */}
      {activeTab === 'domains' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
          <div className="clean-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Authorized Corporate & Webmail Domains
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                Users signing in with these email domains will automatically resolve into this workspace.
              </p>
            </div>

            {/* Domain Input Form */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Globe size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="e.g. acme.com or gmail.com"
                  value={newDomainInput}
                  onChange={(e) => setNewDomainInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddDomain(); } }}
                  style={{
                    width: '100%',
                    padding: '9px 12px 9px 36px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    fontSize: '0.84rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              <button
                type="button"
                onClick={handleAddDomain}
                className="btn btn-secondary"
                style={{ padding: '9px 16px', fontSize: '0.82rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Plus size={14} />
                <span>Add Domain</span>
              </button>
            </div>

            {/* Domains Badges Grid */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', minHeight: '60px', padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-card-subtle)', border: '1px solid var(--border-subtle)' }}>
              {domains.length === 0 ? (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={14} />
                  <span>No domain restrictions. Anyone with invitation or demo credentials can join.</span>
                </div>
              ) : (
                domains.map((dom) => (
                  <div
                    key={dom}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '5px 10px',
                      borderRadius: '6px',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      color: '#1E293B',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                    }}
                  >
                    <span style={{ color: '#EA580C' }}>@</span>
                    <span>{dom}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveDomain(dom)}
                      style={{ border: 'none', background: 'transparent', color: '#94A3B8', cursor: 'pointer', padding: 0, display: 'flex' }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = '#EF4444'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = '#94A3B8'; }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Organization Metadata Form */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Workspace Display Name
                </label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    fontSize: '0.82rem',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Tenant Slug (Immutable Identifier)
                </label>
                <input
                  type="text"
                  value={orgSlug}
                  disabled
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-card-subtle)',
                    color: 'var(--text-muted)',
                    fontSize: '0.82rem',
                    fontFamily: 'monospace',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Quick Help / Info Sidebar */}
          <div className="clean-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', height: 'fit-content' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={16} color="#EA580C" />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, margin: 0 }}>Domain Auto-Provisioning</h3>
            </div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              When users register or authenticate through SSO using an email ending in an authorized domain (e.g. <code>@company.com</code> or <code>@gmail.com</code>), Trulin will automatically route them directly to this workspace without manual administrator approval.
            </p>
            <div style={{ padding: '10px', borderRadius: '6px', backgroundColor: 'var(--bg-card-subtle)', border: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              🔒 <strong>Cryptographic Isolation:</strong> Documents and claims in this workspace remain isolated from other tenant accounts.
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: MEMBERS & RBAC ASSIGNMENTS                         */}
      {/* ========================================================= */}
      {activeTab === 'members' && (
        <div className="clean-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Workspace Members & Role Clearances
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                Manage team memberships, role hierarchy, and governance permissions.
              </p>
            </div>
            <button
              type="button"
              onClick={fetchMembers}
              disabled={membersLoading}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.76rem' }}
            >
              <RefreshCw size={12} className={membersLoading ? 'spinning' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {members.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                No members found in this workspace.
              </div>
            ) : (
              members.map((member) => {
                const badge = getRoleBadge(member.role);
                const initials = member.name ? member.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'US';
                return (
                  <div
                    key={member.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          backgroundColor: '#FFF7ED',
                          color: '#EA580C',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        {initials}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-main)' }}>{member.name}</span>
                          <span
                            style={{
                              fontSize: '0.62rem',
                              fontWeight: 700,
                              padding: '1px 6px',
                              borderRadius: '4px',
                              backgroundColor: badge.bg,
                              color: badge.color,
                              border: `1px solid ${badge.border}`
                            }}
                          >
                            {badge.label}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {member.email} • {member.title || member.department || 'Governance Team'}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <select
                        value={member.role}
                        onChange={(e) => handleMemberRoleChange(member.id, e.target.value)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: '6px',
                          border: '1px solid var(--border-subtle)',
                          backgroundColor: 'var(--bg-card-subtle)',
                          color: 'var(--text-main)',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          outline: 'none'
                        }}
                      >
                        <option value="admin">Administrator / CCO</option>
                        <option value="data_owner">Principal Data Steward</option>
                        <option value="reviewer">Lead Risk Auditor</option>
                        <option value="developer">Systems Engineer</option>
                        <option value="viewer">Compliance Observer</option>
                      </select>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 3: INVITATIONS & MAGIC TOKENS                         */}
      {/* ========================================================= */}
      {activeTab === 'invites' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Invite Creator Panel */}
          <div className="clean-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Invite New Teammate
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                Generate a cryptographically signed magic link for instant onboarding.
              </p>
            </div>

            <form onSubmit={handleCreateInvite} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Recipient Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="email"
                    required
                    placeholder="colleague@company.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 12px 9px 36px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      backgroundColor: 'var(--bg-card)',
                      color: 'var(--text-main)',
                      fontSize: '0.82rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Initial Assigned Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    fontSize: '0.82rem',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="reviewer">Lead Risk Auditor</option>
                  <option value="data_owner">Principal Data Steward</option>
                  <option value="admin">Administrator / CCO</option>
                  <option value="developer">Autonomous Systems Engineer</option>
                  <option value="viewer">Compliance Observer</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={invitesLoading}
                className="btn btn-primary"
                style={{
                  padding: '10px',
                  backgroundColor: '#EA580C',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  fontSize: '0.82rem',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: invitesLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  marginTop: '6px'
                }}
              >
                {invitesLoading ? <RefreshCw size={14} className="spinning" /> : <Plus size={14} />}
                <span>Generate Workspace Invite Link</span>
              </button>
            </form>

            {lastCreatedInvite && (
              <div style={{ marginTop: '12px', padding: '14px', borderRadius: '8px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0' }}>
                <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#047857', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle2 size={14} color="#10B981" />
                  <span>Invitation Link Ready!</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}/invite/${lastCreatedInvite.token}`}
                    style={{
                      flex: 1,
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid #A7F3D0',
                      backgroundColor: '#FFFFFF',
                      fontSize: '0.74rem',
                      fontFamily: 'monospace',
                      color: '#065F46'
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleCopyLink(lastCreatedInvite.token)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', fontSize: '0.74rem' }}
                  >
                    {copiedLink ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                    <span>{copiedLink ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Pending Invites Queue */}
          <div className="clean-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Active Pending Invitations ({invites.length})
              </h3>
              <button
                type="button"
                onClick={fetchInvites}
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
              >
                <RefreshCw size={11} className={invitesLoading ? 'spinning' : ''} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '380px', overflowY: 'auto' }}>
              {invites.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
                  No pending invitations.
                </div>
              ) : (
                invites.map((inv) => (
                  <div
                    key={inv.id}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-card-subtle)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)' }}>{inv.email}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '1px' }}>
                        Role: <span style={{ fontWeight: 600, color: '#EA580C' }}>{inv.role.toUpperCase()}</span> • Expires: {new Date(inv.expires_at).toLocaleDateString()}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={() => handleCopyLink(inv.token)}
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                        title="Copy Invitation Link"
                      >
                        <Copy size={11} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRevokeInvite(inv.id)}
                        style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #FECACA', backgroundColor: '#FEF2F2', color: '#DC2626', cursor: 'pointer', fontSize: '0.7rem' }}
                        title="Revoke Invitation"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 4: SSO & AUTH PROVIDERS                               */}
      {/* ========================================================= */}
      {activeTab === 'security' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
          <div className="clean-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Enterprise Identity Providers & Auth Policy
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                Configure which authentication methods employees and external auditors may use to access this tenant.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { key: 'google', title: 'Google Workspace & Google Identity OIDC (Exclusive)', desc: 'Enterprise Single Sign-On via Google OAuth 2.0 federation (Client ID: 727103176838-d6flfi3ef09448699or2n90opjjfn0us.apps.googleusercontent.com)', icon: Globe }
              ].map((method) => {
                const isChecked = authMethods.includes(method.key);
                const IconComponent = method.icon;
                return (
                  <label
                    key={method.key}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '14px 16px',
                      borderRadius: '8px',
                      backgroundColor: isChecked ? '#FFFBF5' : 'var(--bg-card)',
                      border: `1.5px solid ${isChecked ? '#FED7AA' : 'var(--border-subtle)'}`,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '6px',
                          backgroundColor: isChecked ? '#FFEDD5' : 'var(--bg-card-subtle)',
                          color: isChecked ? '#EA580C' : 'var(--text-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        <IconComponent size={17} />
                      </div>
                      <div>
                        <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-main)' }}>{method.title}</div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>{method.desc}</div>
                      </div>
                    </div>

                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleAuthMethod(method.key)}
                      style={{ accentColor: '#EA580C', width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                  </label>
                );
              })}
            </div>
          </div>

          <div className="clean-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', height: 'fit-content' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={16} color="#10B981" />
              <span>Security Posture</span>
            </h3>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              All API tokens, session cookies, and database connections utilize TLS 1.3 encryption with ECDSA signature verification.
            </div>
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Audit logs record every SSO assertion and credential exchange.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
