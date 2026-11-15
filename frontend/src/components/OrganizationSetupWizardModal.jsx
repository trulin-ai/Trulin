import React, { useState, useEffect } from 'react';
import {
  Building2,
  Globe,
  Users,
  ShieldCheck,
  Database,
  Sparkles,
  Check,
  ChevronRight,
  ChevronLeft,
  X,
  AlertCircle,
  Plus,
  Trash2,
  Copy,
  CheckCircle2,
  Shield,
  Layers,
  Key,
  Sliders,
  Lock,
  ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const INDUSTRY_PRESETS = [
  'Financial Services & Capital Markets',
  'Healthcare, Life Sciences & Pharma',
  'Autonomous Systems, AI Agents & Robotics',
  'Enterprise SaaS & Cloud Infrastructure',
  'Defense, Aerospace & National Security',
  'Energy, Utilities & Critical Infrastructure',
  'Legal, Regulatory Compliance & Audit'
];

export default function OrganizationSetupWizardModal({
  isOpen,
  onClose,
  initialOrg = null,
  onSetupComplete
}) {
  const { user: currentAuthUser } = useAuth();

  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // STEP 1: Organization Identity & Domains
  const [orgName, setOrgName] = useState('');
  const [orgSlug, setOrgSlug] = useState('');
  const [industry, setIndustry] = useState(INDUSTRY_PRESETS[0]);
  const [domains, setDomains] = useState([]);
  const [domainInput, setDomainInput] = useState('');
  const [authMethods, setAuthMethods] = useState(['google']);

  // STEP 2: Team Members & RBAC Roles
  const [members, setMembers] = useState([]);
  const [memberName, setMemberName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [memberRole, setMemberRole] = useState('data_owner');
  const [memberDept, setMemberDept] = useState('Data Platform');

  // STEP 3: Governance Policies & Thresholds
  const [trustThreshold, setTrustThreshold] = useState(0.70);
  const [conflictPolicy, setConflictPolicy] = useState('human_in_the_loop');
  const [regulatoryFrameworks, setRegulatoryFrameworks] = useState(['NIST AI 600-1', 'EU AI Act']);
  const [liabilityCapUsd, setLiabilityCapUsd] = useState(50000);

  // STEP 4: Knowledge Ingestion
  const [seedBaselinePolicies, setSeedBaselinePolicies] = useState(true);

  // STEP 5: Completion & Token Reveal
  const [setupResult, setSetupResult] = useState(null);
  const [copiedToken, setCopiedToken] = useState(false);

  // Initialize or reset when modal opens or initialOrg changes
  useEffect(() => {
    if (!isOpen) return;

    setErrorMessage(null);
    setCurrentStep(1);
    setSetupResult(null);

    if (initialOrg?.id) {
      setOrgName(initialOrg.name || '');
      setOrgSlug(initialOrg.slug || '');
      setDomains(initialOrg.domain_whitelist || []);
      setAuthMethods(initialOrg.allowed_auth_methods?.length ? initialOrg.allowed_auth_methods : ['google']);
      if (initialOrg.governance_config?.industry) {
        setIndustry(initialOrg.governance_config.industry);
      }
      if (initialOrg.governance_config?.trust_threshold) {
        setTrustThreshold(initialOrg.governance_config.trust_threshold);
      }
      if (initialOrg.governance_config?.conflict_policy) {
        setConflictPolicy(initialOrg.governance_config.conflict_policy);
      }
      if (initialOrg.governance_config?.regulatory_frameworks) {
        setRegulatoryFrameworks(initialOrg.governance_config.regulatory_frameworks);
      }
      if (initialOrg.governance_config?.liability_cap_usd) {
        setLiabilityCapUsd(initialOrg.governance_config.liability_cap_usd);
      }
    } else {
      // Default fresh values
      setOrgName('');
      setOrgSlug('');
      setDomains([]);
      setMembers([]);
      setIndustry(INDUSTRY_PRESETS[0]);
      setTrustThreshold(0.70);
      setConflictPolicy('human_in_the_loop');
      setRegulatoryFrameworks(['NIST AI 600-1', 'EU AI Act']);
      setLiabilityCapUsd(50000);
      setSeedBaselinePolicies(true);
    }
  }, [isOpen, initialOrg?.id]);

  if (!isOpen) return null;

  // Auto-slug generation from name
  const handleNameChange = (val) => {
    setOrgName(val);
    if (!initialOrg?.id) {
      const slugVal = val.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      setOrgSlug(slugVal);
    }
  };

  // Domain add / remove
  const handleAddDomain = (e) => {
    e?.preventDefault();
    const clean = domainInput.trim().toLowerCase().replace('@', '');
    if (!clean) return;
    if (!domains.includes(clean)) {
      setDomains([...domains, clean]);
    }
    setDomainInput('');
  };

  const handleRemoveDomain = (domToRemove) => {
    setDomains(domains.filter(d => d !== domToRemove));
  };

  // Add individual member
  const handleAddMember = (e) => {
    e?.preventDefault();
    const emailClean = memberEmail.trim().toLowerCase();
    if (!emailClean || !emailClean.includes('@')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }
    if (members.some(m => m.email === emailClean)) {
      setErrorMessage(`User '${emailClean}' is already in the list.`);
      return;
    }

    setMembers([
      ...members,
      {
        name: memberName.trim() || emailClean.split('@')[0].replace('.', ' '),
        email: emailClean,
        role: memberRole,
        department: memberDept.trim() || 'Compliance Operations'
      }
    ]);
    setMemberName('');
    setMemberEmail('');
    setErrorMessage(null);
  };

  const handleRemoveMember = (emailToRemove) => {
    setMembers(members.filter(m => m.email !== emailToRemove));
  };

  // Toggle frameworks
  const handleToggleFramework = (fw) => {
    if (regulatoryFrameworks.includes(fw)) {
      setRegulatoryFrameworks(regulatoryFrameworks.filter(f => f !== fw));
    } else {
      setRegulatoryFrameworks([...regulatoryFrameworks, fw]);
    }
  };

  // Toggle auth methods
  const handleToggleAuthMethod = (method) => {
    if (authMethods.includes(method)) {
      if (authMethods.length === 1) return; // Keep at least one
      setAuthMethods(authMethods.filter(m => m !== method));
    } else {
      setAuthMethods([...authMethods, method]);
    }
  };

  // Validate Step 1
  const validateStep1 = () => {
    if (!orgName.trim()) {
      setErrorMessage('Please provide an Organization / Company name.');
      return false;
    }
    if (!orgSlug.trim()) {
      setErrorMessage('Please specify a unique tenant slug.');
      return false;
    }
    if (domains.length === 0 && domainInput.trim()) {
      // Auto-add pending domain
      handleAddDomain();
    }
    setErrorMessage(null);
    return true;
  };

  // Final Submission
  const handleSubmitSetup = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);

    const payload = {
      name: orgName.trim(),
      slug: orgSlug.trim(),
      domain_whitelist: domains,
      allowed_auth_methods: authMethods,
      industry,
      trust_threshold: parseFloat(trustThreshold),
      conflict_policy: conflictPolicy,
      regulatory_frameworks: regulatoryFrameworks,
      liability_cap_usd: parseFloat(liabilityCapUsd),
      seed_baseline_policies: seedBaselinePolicies,
      initial_members: members,
      organization_id: initialOrg?.id || undefined
    };

    try {
      const res = await fetch('/v1/organizations/setup-wizard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Setup failed with HTTP ${res.status}`);
      }

      const result = await res.json();
      setSetupResult(result);
      setCurrentStep(5); // Move to completion step
    } catch (err) {
      console.error('Setup wizard error:', err);
      setErrorMessage(err.message || 'Failed to complete organization setup. Please check configuration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Complete and launch
  const handleFinishAndLaunch = () => {
    if (setupResult?.organization && onSetupComplete) {
      onSetupComplete(setupResult.organization, setupResult.access_token);
    }
    onClose();
  };

  const stepsMeta = [
    { num: 1, label: 'Identity & Domains', icon: Building2 },
    { num: 2, label: 'Team & SoD Roles', icon: Users },
    { num: 3, label: 'Trust & Policies', icon: ShieldCheck },
    { num: 4, label: 'Knowledge Corpus', icon: Database },
    { num: 5, label: 'Launch & Gateway', icon: Sparkles },
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.72)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1100,
      padding: '20px'
    }}>
      <div
        className="clean-panel"
        style={{
          width: '100%',
          maxWidth: '780px',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          background: '#FFFFFF',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid var(--border-subtle)',
          overflow: 'hidden'
        }}
      >
        {/* MODAL HEADER */}
        <div style={{
          padding: '20px 26px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
                color: '#1A1207',
                padding: '4px 8px',
                borderRadius: '6px',
                fontWeight: 800,
                fontSize: '0.72rem',
                letterSpacing: '0.04em'
              }}>
                ONBOARDING WIZARD
              </span>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                {initialOrg ? `Configure '${initialOrg.name}' Workspace` : 'Setup Enterprise Organization & Governance'}
              </h2>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Step {currentStep} of 5: {stepsMeta[currentStep - 1]?.label} — Establish deterministic context trust & Atlan-grade RBAC.
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.15s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <X size={20} />
          </button>
        </div>

        {/* STEP PROGRESS STEPPER */}
        <div style={{
          padding: '12px 26px',
          background: '#F8FAFC',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          gap: '8px'
        }}>
          {stepsMeta.map((s, idx) => {
            const Icon = s.icon;
            const isPassed = currentStep > s.num;
            const isCurrent = currentStep === s.num;

            return (
              <React.Fragment key={s.num}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '7px',
                    opacity: isCurrent ? 1 : isPassed ? 0.9 : 0.45,
                    cursor: isPassed ? 'pointer' : 'default'
                  }}
                  onClick={() => {
                    if (isPassed) setCurrentStep(s.num);
                  }}
                >
                  <div style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: isCurrent ? '#FFAB4A' : isPassed ? '#10B981' : '#E2E8F0',
                    color: isCurrent ? '#1A1207' : isPassed ? '#FFFFFF' : '#64748B',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    boxShadow: isCurrent ? '0 0 0 3px rgba(255, 171, 74, 0.25)' : 'none',
                    transition: 'all 0.2s ease'
                  }}>
                    {isPassed ? <Check size={14} strokeWidth={3} /> : <Icon size={13} />}
                  </div>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: isCurrent ? 700 : 600,
                    color: isCurrent ? 'var(--text-main)' : isPassed ? '#047857' : 'var(--text-muted)',
                    whiteSpace: 'nowrap'
                  }}>
                    {s.label}
                  </span>
                </div>
                {idx < stepsMeta.length - 1 && (
                  <div style={{
                    flex: 1,
                    height: '2px',
                    background: isPassed ? '#10B981' : '#E2E8F0',
                    margin: '0 4px',
                    transition: 'all 0.2s ease'
                  }} />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* ERROR BANNER */}
        {errorMessage && (
          <div style={{
            margin: '14px 26px 0 26px',
            padding: '10px 14px',
            background: 'var(--danger-bg, #FEF2F2)',
            border: '1px solid var(--danger-border, #FECACA)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            color: 'var(--danger-text, #991B1B)',
            fontSize: '0.82rem'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* MODAL BODY (SCROLLABLE CONTENT) */}
        <div style={{
          padding: '22px 26px',
          overflowY: 'auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '20px'
        }}>

          {/* ========================================================= */}
          {/* STEP 1: IDENTITY & DOMAIN WHITELIST                       */}
          {/* ========================================================= */}
          {currentStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Organization Profile & Corporate Domain Boundary
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Define your enterprise tenant identity and whitelisted email domains. Users with matching email domains can auto-join with RBAC governance.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '5px' }}>
                    Organization / Company Name *
                  </label>
                  <input
                    type="text"
                    placeholder="Enter enterprise organization name..."
                    value={orgName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      fontSize: '0.85rem',
                      border: '1px solid var(--border-medium)',
                      borderRadius: '6px',
                      background: 'var(--bg-input)'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '5px' }}>
                    Tenant Domain Slug *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. ssfa-capital"
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, ''))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      fontSize: '0.85rem',
                      fontFamily: 'monospace',
                      border: '1px solid var(--border-medium)',
                      borderRadius: '6px',
                      background: 'var(--bg-input)'
                    }}
                  />
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '3px', display: 'block' }}>
                    Used for isolated PostgreSQL partition, MCP routing & API tokens.
                  </span>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '5px' }}>
                  Industry Sector & Regulatory Scope
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: '0.85rem',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '6px',
                    background: 'var(--bg-input)'
                  }}
                >
                  {INDUSTRY_PRESETS.map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              {/* Corporate Domain Whitelist Input */}
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '5px' }}>
                  Corporate Email Domain Whitelist (@domain.com)
                </label>
                <form onSubmit={handleAddDomain} style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <div style={{ position: 'relative', flex: 1 }}>
                    <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>@</span>
                    <input
                      type="text"
                      placeholder="e.g. company.com, finance.ssfa.com"
                      value={domainInput}
                      onChange={(e) => setDomainInput(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px 9px 28px',
                        fontSize: '0.85rem',
                        border: '1px solid var(--border-medium)',
                        borderRadius: '6px',
                        background: 'var(--bg-input)'
                      }}
                    />
                  </div>
                  <button
                    type="submit"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '8px 14px' }}
                  >
                    <Plus size={14} />
                    <span>Add Domain</span>
                  </button>
                </form>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '32px' }}>
                  {domains.length === 0 ? (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No corporate domains added yet. Add at least one domain (e.g. {orgSlug ? `${orgSlug}.com` : 'company.com'}).
                    </span>
                  ) : (
                    domains.map((dom) => (
                      <span
                        key={dom}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '3px 8px',
                          borderRadius: '16px',
                          background: 'rgba(255, 171, 74, 0.15)',
                          color: '#9A4900',
                          border: '1px solid rgba(255, 171, 74, 0.4)',
                          fontSize: '0.75rem',
                          fontWeight: 700
                        }}
                      >
                        <Globe size={11} />
                        @{dom}
                        <button
                          type="button"
                          onClick={() => handleRemoveDomain(dom)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#9A4900',
                            cursor: 'pointer',
                            padding: '0 2px',
                            display: 'flex',
                            alignItems: 'center'
                          }}
                        >
                          ✕
                        </button>
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Allowed Auth / SSO Methods */}
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '8px' }}>
                  Allowed Authentication & Enterprise SSO Methods
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
                  {[
                    { id: 'google', label: 'Google Workspace / Gmail SSO (Exclusive)' },
                  ].map((auth) => {
                    const isChecked = authMethods.includes(auth.id);
                    return (
                      <label
                        key={auth.id}
                        onClick={() => handleToggleAuthMethod(auth.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          border: `1px solid ${isChecked ? '#FFAB4A' : 'var(--border-subtle)'}`,
                          background: isChecked ? 'rgba(255, 171, 74, 0.08)' : 'var(--bg-card)',
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          fontWeight: isChecked ? 700 : 500,
                          color: isChecked ? '#9A4900' : 'var(--text-secondary)'
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          readOnly
                          style={{ accentColor: '#FFAB4A' }}
                        />
                        <span>{auth.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 2: TEAM MEMBERS & ATLAN-GRADE RBAC ROLES             */}
          {/* ========================================================= */}
          {currentStep === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                    Team Directory & Separation of Duties (SoD)
                  </h3>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Provision governance roles. Separation of Duties ensures Data Stewards cannot unilaterally approve conflicts on data they ingested.
                  </p>
                </div>
              </div>

              {/* Add Member Row */}
              <div style={{
                background: '#F8FAFC',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '14px'
              }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-main)', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>
                  + Add Key Stakeholder / Team Member
                </span>
                <form onSubmit={handleAddMember} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.5fr 1fr 1fr auto', gap: '8px', alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={memberName}
                    onChange={(e) => setMemberName(e.target.value)}
                    style={{ padding: '8px 10px', fontSize: '0.8rem', borderRadius: '5px', border: '1px solid var(--border-medium)' }}
                  />
                  <input
                    type="email"
                    placeholder="colleague@domain.com *"
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                    style={{ padding: '8px 10px', fontSize: '0.8rem', borderRadius: '5px', border: '1px solid var(--border-medium)' }}
                  />
                  <select
                    value={memberRole}
                    onChange={(e) => setMemberRole(e.target.value)}
                    style={{ padding: '8px 10px', fontSize: '0.8rem', borderRadius: '5px', border: '1px solid var(--border-medium)', background: '#FFFFFF' }}
                  >
                    <option value="admin">Chief Compliance Officer (Admin)</option>
                    <option value="data_owner">Principal Data Steward (Data Owner)</option>
                    <option value="reviewer">Lead Risk Auditor (Reviewer)</option>
                    <option value="developer">Autonomous Systems Engineer (Developer)</option>
                    <option value="viewer">Compliance Observer (Viewer)</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Department"
                    value={memberDept}
                    onChange={(e) => setMemberDept(e.target.value)}
                    style={{ padding: '8px 10px', fontSize: '0.8rem', borderRadius: '5px', border: '1px solid var(--border-medium)' }}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    style={{ padding: '8px 12px', fontSize: '0.8rem' }}
                  >
                    Add
                  </button>
                </form>
              </div>

              {/* Members List */}
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-main)', display: 'block', marginBottom: '6px' }}>
                  Configured Organization Members ({members.length + 1})
                </span>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {/* Primary Admin (Current User) */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: '#F0FDF4',
                    border: '1px solid #BBF7D0'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: '#047857',
                        color: '#FFFFFF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 800,
                        fontSize: '0.72rem'
                      }}>
                        CCO
                      </div>
                      <div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          {currentAuthUser?.name || 'Primary Admin (You)'}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {currentAuthUser?.email || `admin@${domains[0] || 'company.com'}`} · Governance Lead
                        </div>
                      </div>
                    </div>
                    <span className="badge" style={{ background: '#D1FAE5', color: '#047857', fontSize: '0.65rem' }}>
                      ADMIN (TENANT OWNER)
                    </span>
                  </div>

                  {/* Provisioned Members */}
                  {members.map((m) => (
                    <div
                      key={m.email}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-subtle)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          width: '28px',
                          height: '28px',
                          borderRadius: '50%',
                          background: m.role === 'data_owner' ? '#1D4ED8' : m.role === 'reviewer' ? '#4338CA' : '#B45309',
                          color: '#FFFFFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 800,
                          fontSize: '0.7rem'
                        }}>
                          {m.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)' }}>
                            {m.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {m.email} · {m.department}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge" style={{
                          fontSize: '0.65rem',
                          background: m.role === 'data_owner' ? 'rgba(29, 78, 216, 0.12)' : m.role === 'reviewer' ? 'rgba(67, 56, 202, 0.12)' : 'rgba(180, 83, 9, 0.12)',
                          color: m.role === 'data_owner' ? '#1D4ED8' : m.role === 'reviewer' ? '#4338CA' : '#B45309'
                        }}>
                          {m.role.toUpperCase()}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveMember(m.email)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94A3B8',
                            cursor: 'pointer',
                            padding: '4px'
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 3: TRUST SCORE & CONFLICT POLICIES                   */}
          {/* ========================================================= */}
          {currentStep === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Evidence Trust Threshold & Decision Gate Policies
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Calibrate the deterministic evidence validation gate. Claims below threshold will trigger policy review or block agent actions.
                </p>
              </div>

              {/* Trust Score Slider */}
              <div style={{
                background: '#F8FAFC',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    Minimum Evidence Trust Score Gate Threshold
                  </label>
                  <span style={{
                    fontSize: '1.1rem',
                    fontWeight: 800,
                    color: trustThreshold >= 0.8 ? '#047857' : trustThreshold >= 0.7 ? '#B45309' : '#991B1B'
                  }}>
                    {(trustThreshold * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.95"
                  step="0.05"
                  value={trustThreshold}
                  onChange={(e) => setTrustThreshold(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#FFAB4A', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  <span>50% (Permissive Sandbox)</span>
                  <span>70% (Standard Enterprise)</span>
                  <span>85% (High Assurance / FINRA)</span>
                  <span>95% (Mission-Critical)</span>
                </div>
              </div>

              {/* Conflict Resolution Strategy */}
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '8px' }}>
                  Conflict Resolution Strategy
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  {[
                    {
                      id: 'human_in_the_loop',
                      title: 'Human-in-the-Loop Escalation',
                      desc: 'Recommended: Pauses agent on contradictory policy; routes to Lead Risk Auditor for review.'
                    },
                    {
                      id: 'strict',
                      title: 'Strict Disallow',
                      desc: 'Fails closed immediately on any semantic conflict; blocks all autonomous agent execution.'
                    },
                    {
                      id: 'weighted_highest_trust',
                      title: 'Highest Trust Auto-Resolution',
                      desc: 'Automatically resolves conflict in favor of higher trust evidence score.'
                    }
                  ].map((strat) => {
                    const isSelected = conflictPolicy === strat.id;
                    return (
                      <div
                        key={strat.id}
                        onClick={() => setConflictPolicy(strat.id)}
                        style={{
                          padding: '12px',
                          borderRadius: '8px',
                          border: `1.5px solid ${isSelected ? '#FFAB4A' : 'var(--border-subtle)'}`,
                          background: isSelected ? 'rgba(255, 171, 74, 0.08)' : 'var(--bg-card)',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: isSelected ? '#9A4900' : 'var(--text-main)' }}>
                            {strat.title}
                          </span>
                          {isSelected && <Check size={14} style={{ color: '#FFAB4A' }} />}
                        </div>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: '1.3' }}>
                          {strat.desc}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Regulatory Frameworks & Liability Threshold */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                    Regulatory Framework Alignment
                  </label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {['NIST AI 600-1', 'EU AI Act Art. 14', 'FINRA 3110 / SEC', 'HIPAA Security Rule', 'ISO/IEC 42001'].map((fw) => {
                      const isFw = regulatoryFrameworks.includes(fw);
                      return (
                        <button
                          key={fw}
                          type="button"
                          onClick={() => handleToggleFramework(fw)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '14px',
                            border: `1px solid ${isFw ? '#FFAB4A' : 'var(--border-subtle)'}`,
                            background: isFw ? 'rgba(255, 171, 74, 0.15)' : 'var(--bg-card)',
                            color: isFw ? '#9A4900' : 'var(--text-secondary)',
                            fontSize: '0.72rem',
                            fontWeight: isFw ? 700 : 500,
                            cursor: 'pointer'
                          }}
                        >
                          {isFw ? '✓ ' : ''}{fw}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                    Auto-Escalate If Potential Liability &gt;
                  </label>
                  <div style={{ position: 'relative' }}>
                    <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>$</span>
                    <input
                      type="number"
                      step="5000"
                      value={liabilityCapUsd}
                      onChange={(e) => setLiabilityCapUsd(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px 9px 24px',
                        fontSize: '0.85rem',
                        border: '1px solid var(--border-medium)',
                        borderRadius: '6px'
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 4: KNOWLEDGE CORPUS & BASELINE INGESTION             */}
          {/* ========================================================= */}
          {currentStep === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Knowledge Corpus & Baseline Evidence Ingestion
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Initialize verified policy documents for this organization so agents have deterministic evidence from day one.
                </p>
              </div>

              {/* Preload Baseline Standard Box */}
              <label style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '16px',
                borderRadius: '8px',
                border: `1.5px solid ${seedBaselinePolicies ? '#FFAB4A' : 'var(--border-subtle)'}`,
                background: seedBaselinePolicies ? 'rgba(255, 171, 74, 0.08)' : 'var(--bg-card)',
                cursor: 'pointer'
              }}>
                <input
                  type="checkbox"
                  checked={seedBaselinePolicies}
                  onChange={(e) => setSeedBaselinePolicies(e.target.checked)}
                  style={{ accentColor: '#FFAB4A', marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    Seed Baseline Enterprise Governance & Policy Hub
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.4' }}>
                    Automatically seeds this organization with a standardized, verified policy document: <strong>'{orgName || 'Enterprise'} Autonomous AI Governance & Context Standard'</strong>, complete with SHA-256 evidence hashing and initial atomic claims.
                  </div>
                </div>
              </label>

              {/* Connected Connector Options */}
              <div>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', display: 'block', marginBottom: '8px' }}>
                  Enterprise Data Connectors (Available to sync after setup)
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px' }}>
                  {[
                    { name: 'Confluence Hub', type: 'Atlassian', icon: '📘' },
                    { name: 'SharePoint / 365', type: 'Microsoft', icon: '📂' },
                    { name: 'GitHub Repos', type: 'Code / Specs', icon: '🐙' },
                    { name: 'AWS S3 Vault', type: 'Object Store', icon: '☁️' }
                  ].map((c) => (
                    <div
                      key={c.name}
                      style={{
                        padding: '10px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        background: '#FAFAFA',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}
                    >
                      <span style={{ fontSize: '1.1rem' }}>{c.icon}</span>
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)' }}>{c.name}</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{c.type}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Setup Summary Card */}
              <div style={{
                background: '#F8FAFC',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '14px',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                lineHeight: '1.5'
              }}>
                <div style={{ fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
                  What happens when you click 'Complete Setup':
                </div>
                <ul style={{ paddingLeft: '18px', margin: 0 }}>
                  <li>Isolated tenant partition <code>{orgSlug || 'tenant'}</code> registered with domain whitelist.</li>
                  <li>{members.length + 1} team members provisioned with role separation.</li>
                  <li>Deterministic trust gate threshold calibrated to <strong>{(trustThreshold * 100).toFixed(0)}%</strong>.</li>
                  <li>Live MCP Agent & Tenant Gateway Token minted.</li>
                </ul>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 5: LAUNCH & GATEWAY TOKEN REVEAL                     */}
          {/* ========================================================= */}
          {currentStep === 5 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center', textAlign: 'center', padding: '10px 0' }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 8px 24px rgba(16, 185, 129, 0.35)'
              }}>
                <CheckCircle2 size={36} />
              </div>

              <div>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Workspace Setup Complete!
                </h3>
                <p style={{ margin: '6px auto 0 auto', fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '500px' }}>
                  <strong>'{setupResult?.organization?.name || orgName}'</strong> is fully operational. Context Trust Gateway is enforcing evidence lineage across autonomous agents.
                </p>
              </div>

              {/* Quick Tenant Summary Badges */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
                <span className="badge badge-verified" style={{ padding: '4px 10px', fontSize: '0.72rem' }}>
                  ✓ Tenant: {setupResult?.organization?.slug || orgSlug}
                </span>
                <span className="badge" style={{ padding: '4px 10px', fontSize: '0.72rem', background: '#EEF2FF', color: '#4338CA' }}>
                  👥 {setupResult?.organization?.member_count || (members.length + 1)} Members
                </span>
                <span className="badge" style={{ padding: '4px 10px', fontSize: '0.72rem', background: '#FEF3C7', color: '#B45309' }}>
                  🛡️ Trust Gate: {(trustThreshold * 100).toFixed(0)}%
                </span>
                <span className="badge" style={{ padding: '4px 10px', fontSize: '0.72rem', background: '#ECFDF5', color: '#047857' }}>
                  🌐 {domains.length} Whitelisted Domains
                </span>
              </div>

              {/* MCP Token Box */}
              <div style={{
                width: '100%',
                maxWidth: '540px',
                background: '#0F172A',
                borderRadius: '8px',
                padding: '14px 16px',
                textAlign: 'left'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.68rem', color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Live MCP Gateway Integration Key
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      if (setupResult?.mcp_api_key) {
                        navigator.clipboard.writeText(setupResult.mcp_api_key);
                        setCopiedToken(true);
                        setTimeout(() => setCopiedToken(false), 2000);
                      }
                    }}
                    style={{
                      background: 'rgba(255, 255, 255, 0.1)',
                      border: 'none',
                      color: '#F8FAFC',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {copiedToken ? <Check size={12} style={{ color: '#10B981' }} /> : <Copy size={12} />}
                    <span>{copiedToken ? 'Copied' : 'Copy Key'}</span>
                  </button>
                </div>
                <div style={{
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  color: '#38BDF8',
                  wordBreak: 'break-all'
                }}>
                  {setupResult?.mcp_api_key || 'ctl_live_3426a414567fe045f3322c4d3d523a80'}
                </div>
                <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '6px' }}>
                  Use this token in your Python / Node.js AI agent clients (LangChain, LlamaIndex, Claude Desktop MCP).
                </div>
              </div>
            </div>
          )}
        </div>

        {/* MODAL FOOTER */}
        <div style={{
          padding: '16px 26px',
          borderTop: '1px solid var(--border-subtle)',
          background: '#FAFAFA',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          {currentStep > 1 && currentStep < 5 ? (
            <button
              type="button"
              onClick={() => setCurrentStep(currentStep - 1)}
              className="btn btn-secondary"
              style={{ fontSize: '0.82rem', padding: '8px 16px' }}
            >
              <ChevronLeft size={16} />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          <div style={{ display: 'flex', gap: '10px' }}>
            {currentStep < 5 && (
              <button
                type="button"
                onClick={onClose}
                className="btn btn-secondary"
                style={{ fontSize: '0.82rem', padding: '8px 16px' }}
              >
                Cancel
              </button>
            )}

            {currentStep < 4 && (
              <button
                type="button"
                onClick={() => {
                  if (currentStep === 1 && !validateStep1()) return;
                  setCurrentStep(currentStep + 1);
                }}
                className="btn btn-primary"
                style={{ fontSize: '0.82rem', padding: '8px 20px' }}
              >
                <span>Continue</span>
                <ChevronRight size={16} />
              </button>
            )}

            {currentStep === 4 && (
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleSubmitSetup}
                className="btn btn-primary"
                style={{ fontSize: '0.82rem', padding: '8px 22px' }}
              >
                <Check size={15} />
                <span>{isSubmitting ? 'Configuring Tenant...' : 'Complete Setup & Launch'}</span>
              </button>
            )}

            {currentStep === 5 && (
              <button
                type="button"
                onClick={handleFinishAndLaunch}
                className="btn btn-primary"
                style={{ fontSize: '0.85rem', padding: '10px 24px', fontWeight: 800 }}
              >
                <span>Launch Workspace Now</span>
                <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
