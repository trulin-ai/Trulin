import React, { useState, useEffect, useRef } from 'react';
import {
  Building2,
  Shield,
  ShieldCheck,
  Check,
  Plus,
  Settings,
  Mail,
  Lock,
  Sparkles,
  Save,
  CheckCircle2,
  Camera,
  Upload,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// Curated Instant Avatars across professional styles
const INSTANT_AVATARS = [
  // 1. Executive & Modern (Clean Notionist style)
  {
    id: 'exec-1',
    name: 'Sarah - Governance Lead',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Sarah&backgroundColor=e2e8f0'
  },
  {
    id: 'exec-2',
    name: 'Marcus - Data Steward',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Marcus&backgroundColor=cbd5e1'
  },
  {
    id: 'exec-3',
    name: 'Aria - Compliance Officer',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Aria&backgroundColor=f1f5f9'
  },
  {
    id: 'exec-4',
    name: 'Felix - Risk Architect',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Felix&backgroundColor=e0e7ff'
  },
  {
    id: 'exec-5',
    name: 'Zara - Platform Director',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Zara&backgroundColor=fef3c7'
  },
  {
    id: 'exec-6',
    name: 'Elena - Auditor General',
    category: 'executive',
    url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Elena&backgroundColor=dcfce7'
  },

  // 2. AI & Robotics Stewards (Bottts 3D & Cyber)
  {
    id: 'bot-1',
    name: 'Titan - Decision Arbiter',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Titan&backgroundColor=0f172a'
  },
  {
    id: 'bot-2',
    name: 'Nexus - Context Engine',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Nexus&backgroundColor=1e293b'
  },
  {
    id: 'bot-3',
    name: 'Aegis - Gate Sentinel',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Aegis&backgroundColor=047857'
  },
  {
    id: 'bot-4',
    name: 'Vertex - Lineage Tracer',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Vertex&backgroundColor=1d4ed8'
  },
  {
    id: 'bot-5',
    name: 'Cyber - Claim Extractor',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Cyber&backgroundColor=4338ca'
  },
  {
    id: 'bot-6',
    name: 'Steward - Trust Observer',
    category: 'robotics',
    url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Steward&backgroundColor=334155'
  },

  // 3. Professional Personas (Avataaars)
  {
    id: 'pro-1',
    name: 'David - Enterprise Ops',
    category: 'professional',
    url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=David'
  },
  {
    id: 'pro-2',
    name: 'Aisha - Senior AI Engineer',
    category: 'professional',
    url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Aisha'
  },
  {
    id: 'pro-3',
    name: 'Devin - Policy Analyst',
    category: 'professional',
    url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Devin'
  },
  {
    id: 'pro-4',
    name: 'Chloe - Legal Counsel',
    category: 'professional',
    url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Chloe'
  },

  // 4. Geometric Trust Badges (Shapes & Monograms)
  {
    id: 'geo-1',
    name: 'Trulin Alpha Matrix',
    category: 'geometric',
    url: 'https://api.dicebear.com/7.x/shapes/svg?seed=TrulinAlpha&backgroundColor=0f172a'
  },
  {
    id: 'geo-2',
    name: 'Trust Shield Node',
    category: 'geometric',
    url: 'https://api.dicebear.com/7.x/shapes/svg?seed=TrustShield&backgroundColor=047857'
  },
  {
    id: 'geo-3',
    name: 'Quantum Governance Core',
    category: 'geometric',
    url: 'https://api.dicebear.com/7.x/shapes/svg?seed=QuantumGate&backgroundColor=1e1b4b'
  },
  {
    id: 'geo-4',
    name: 'Data Horizon Vault',
    category: 'geometric',
    url: 'https://api.dicebear.com/7.x/shapes/svg?seed=DataHorizon&backgroundColor=0369a1'
  }
];

export default function UserProfileStudio({
  activeOrg,
  organizations = [],
  onSwitchOrg,
  activeWorkspace,
  workspaces = [],
  onSwitchWorkspace,
  activePersona,
  personas = [],
  onSelectPersona,
  effectiveRole,
  roleMetadata,
  onOpenRegisterOrg,
  onOpenOrgSettings,
  onOpenRbacModal,
  onLaunchSetupWizard,
  onLogout,
  showToast,
  initialSubSection = 'user_profile',
  onSubSectionChange
}) {
  const { user: authUser, token, updateUser } = useAuth();
  const [switchingOrgId, setSwitchingOrgId] = useState(null);
  const [activeSubSection, setActiveSubSection] = useState(
    initialSubSection && initialSubSection !== 'identity' && initialSubSection !== 'security' ? initialSubSection : 'user_profile'
  ); // 'user_profile' | 'companies' | 'register'

  // Editable Non-Confidential Profile state
  const [editName, setEditName] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [editDepartment, setEditDepartment] = useState('');
  const [editTimezone, setEditTimezone] = useState('UTC');
  const [editPhone, setEditPhone] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editAvatarUrl, setEditAvatarUrl] = useState('');
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  const [selectedAvatarCategory, setSelectedAvatarCategory] = useState('all');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSavedMsg, setProfileSavedMsg] = useState(false);

  const fileInputRef = useRef(null);

  // Sync initial user details into edit form
  useEffect(() => {
    const currentName = authUser?.name || activePersona?.name || 'PRASANNA KUMAR SIMHADRI';
    const currentTitle = authUser?.title || activePersona?.title || 'Administrator';
    const currentDept = authUser?.department || activePersona?.department || 'Trust & Governance';
    const currentTz = authUser?.timezone || 'UTC';
    const currentPhone = authUser?.phone || '';
    const currentBio = authUser?.bio || 'Enterprise security and compliance administrator for autonomous AI decision gates.';
    const currentAvatar = authUser?.avatar_url || authUser?.picture || activePersona?.avatar_url || '';

    setEditName(currentName);
    setEditTitle(currentTitle);
    setEditDepartment(currentDept);
    setEditTimezone(currentTz);
    setEditPhone(currentPhone);
    setEditBio(currentBio);
    setEditAvatarUrl(prev => prev || currentAvatar);
  }, [authUser?.id, authUser?.email, activePersona?.id]);

  // Register Company Form state
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyDomain, setNewCompanyDomain] = useState('');
  const [newCompanyIndustry, setNewCompanyIndustry] = useState('Enterprise AI & Decision Governance');
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerError, setRegisterError] = useState(null);

  useEffect(() => {
    if (initialSubSection && initialSubSection !== 'identity' && initialSubSection !== 'security') {
      setActiveSubSection(initialSubSection);
    }
  }, [initialSubSection]);

  const handleSubSectionClick = (sub) => {
    setActiveSubSection(sub);
    onSubSectionChange?.(sub);
  };

  const handleSelectCompany = async (org) => {
    if (org.id === activeOrg?.id) return;
    setSwitchingOrgId(org.id);
    try {
      if (onSwitchOrg) {
        await onSwitchOrg(org);
      }
    } finally {
      setTimeout(() => setSwitchingOrgId(null), 300);
    }
  };

  const isCurrentAvatarGoogle = Boolean(
    editAvatarUrl && (
      editAvatarUrl.includes('googleusercontent.com') ||
      editAvatarUrl.includes('background=4285F4')
    )
  );

  // Apply & immediately persist avatar update across UI and backend
  const applyAndPersistAvatar = async (newAvatarUrl, message = 'Profile photo updated!') => {
    setEditAvatarUrl(newAvatarUrl);
    setIsAvatarModalOpen(false);

    if (updateUser) {
      updateUser({ avatar_url: newAvatarUrl });
    }

    const targetUserId = authUser?.id || activePersona?.id;
    if (targetUserId) {
      try {
        const patchRes = await fetch(`/v1/users/${targetUserId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            avatar_url: newAvatarUrl
          })
        });
        if (!patchRes.ok) {
          const errData = await patchRes.json().catch(() => ({}));
          console.warn('Failed to persist avatar to backend:', errData);
        }
      } catch (err) {
        console.warn('Network error saving avatar to backend:', err);
      }
    }

    if (showToast) {
      showToast(message, 'success');
    }
  };

  // File Upload Handler (with instant client-side canvas downscale & immediate persist)
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      if (showToast) showToast('File too large (max 10MB). Please choose a smaller image.', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (uploadEvent) => {
      const dataUrlRaw = uploadEvent.target?.result;
      if (!dataUrlRaw) return;
      const img = new Image();
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          const MAX_SIZE = 256;
          let width = img.width;
          let height = img.height;
          if (width > height) {
            if (width > MAX_SIZE) {
              height = Math.round(height * (MAX_SIZE / width));
              width = MAX_SIZE;
            }
          } else {
            if (height > MAX_SIZE) {
              width = Math.round(width * (MAX_SIZE / height));
              height = MAX_SIZE;
            }
          }
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
          applyAndPersistAvatar(dataUrl, 'Custom photo uploaded & applied!');
        } catch (err) {
          console.warn('Canvas optimization fallback:', err);
          applyAndPersistAvatar(dataUrlRaw, 'Custom photo uploaded & applied!');
        }
      };
      img.onerror = () => {
        applyAndPersistAvatar(dataUrlRaw, 'Custom photo uploaded & applied!');
      };
      img.src = dataUrlRaw;
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleSaveProfileSubmit = async (e) => {
    e.preventDefault();
    if (!editName.trim()) {
      if (showToast) showToast('Name cannot be empty', 'error');
      return;
    }

    setIsSavingProfile(true);
    const updatedUser = {
      name: editName.trim(),
      title: editTitle.trim(),
      department: editDepartment.trim(),
      timezone: editTimezone,
      phone: editPhone.trim(),
      bio: editBio.trim(),
      avatar_url: editAvatarUrl || null,
    };

    const targetUserId = authUser?.id || activePersona?.id;
    if (targetUserId) {
      try {
        await fetch(`/v1/users/${targetUserId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            name: editName.trim(),
            title: editTitle.trim(),
            department: editDepartment.trim(),
            avatar_url: editAvatarUrl || null,
            phone: editPhone.trim(),
            bio: editBio.trim(),
            timezone: editTimezone,
          })
        });
      } catch (err) {
        console.warn('Backend patch user error:', err);
      }
    }

    if (updateUser) {
      updateUser(updatedUser);
    }

    setProfileSavedMsg(true);
    if (showToast) {
      showToast('Profile information successfully updated!', 'success');
    }

    setTimeout(() => {
      setIsSavingProfile(false);
      setTimeout(() => setProfileSavedMsg(false), 3000);
    }, 400);
  };

  const displayName = authUser?.name || activePersona?.name || editName || 'Authorized User';
  const displayEmail = authUser?.email || activePersona?.email || 'user@enterprise.com';
  const activeAvatarUrl = editAvatarUrl || authUser?.avatar_url || authUser?.picture || activePersona?.avatar_url;
  const userInitials = displayName
    ? displayName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U';

  const cleanOrgs = (organizations && organizations.length > 0)
    ? organizations.filter(o => 
        !o.name.includes('Auto Resolve') && 
        !o.name.includes('Default Org')
      )
    : (activeOrg ? [activeOrg] : []);

  const filteredAvatars = selectedAvatarCategory === 'all'
    ? INSTANT_AVATARS
    : INSTANT_AVATARS.filter(a => a.category === selectedAvatarCategory);

  const handleRegisterCompanySubmit = async (e) => {
    e.preventDefault();
    if (!newCompanyName.trim()) {
      setRegisterError('Organization name is required.');
      return;
    }
    setRegisterError(null);
    setIsRegistering(true);

    const slug = newCompanyName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    const domains = newCompanyDomain.trim()
      ? newCompanyDomain.split(',').map(d => d.trim().toLowerCase().replace(/^@/, '')).filter(Boolean)
      : ['gmail.com'];

    try {
      const res = await fetch('/v1/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: newCompanyName.trim(),
          slug,
          domain_whitelist: domains,
          setup_completed: true
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }

      const created = await res.json();
      created.setup_completed = true;
      if (onSwitchOrg) {
        await onSwitchOrg(created);
      }
      if (showToast) {
        showToast(`Enterprise organization '${created.name}' registered successfully!`, 'success');
      }
      setNewCompanyName('');
      setNewCompanyDomain('');
      handleSubSectionClick('companies');
    } catch (err) {
      setRegisterError(err.message || 'Failed to register organization.');
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', maxWidth: '1280px', margin: '0 auto' }}>
      
      {/* Hidden File Input for Avatar Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept="image/png, image/jpeg, image/jpg, image/webp, image/svg+xml"
        style={{ display: 'none' }}
      />

      {/* 1. Profile Header Hero (Dedicated to User Profile view) */}
      {activeSubSection === 'user_profile' && (
        <div style={{
          padding: '16px 20px',
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '14px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
              {/* Profile Avatar with click-to-change */}
              <div
                onClick={() => setIsAvatarModalOpen(true)}
                title="Click to change photo"
                style={{
                  position: 'relative',
                  width: '74px',
                  height: '74px',
                  borderRadius: '50%',
                  backgroundColor: '#0F172A',
                  color: '#FFFFFF',
                  fontSize: '1.4rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
                  border: isCurrentAvatarGoogle ? '2.5px solid #4285F4' : '2px solid #E2E8F0',
                  overflow: 'hidden',
                  flexShrink: 0,
                  cursor: 'pointer'
                }}
              >
                {activeAvatarUrl ? (
                  <img
                    src={activeAvatarUrl}
                    alt={displayName}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                ) : (
                  <span>{userInitials}</span>
                )}
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0F172A', margin: 0, letterSpacing: '-0.02em' }}>
                    {displayName}
                  </h1>

                  <button
                    type="button"
                    onClick={() => setIsAvatarModalOpen(true)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      background: '#F1F5F9',
                      border: '1px solid #CBD5E1',
                      color: '#0F172A',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#E2E8F0'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#F1F5F9'}
                  >
                    <Camera size={13} />
                    <span>Change Photo</span>
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '6px', fontSize: '0.82rem', color: '#64748B', flexWrap: 'wrap' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                    <Building2 size={13} style={{ color: '#94A3B8' }} />
                    {activeOrg?.name || 'Enterprise Workspace'}
                  </span>
                  <span>•</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                    <Mail size={13} style={{ color: '#94A3B8' }} />
                    {displayEmail}
                  </span>
                  <span>•</span>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontWeight: 700,
                    color: '#047857',
                    background: 'rgba(4, 120, 87, 0.08)',
                    padding: '1px 8px',
                    borderRadius: '4px'
                  }}>
                    <Shield size={11} />
                    {(effectiveRole || 'ADMIN').toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. SUB-SECTION: EDITABLE USER PROFILE FORM (CLEAN & NEAT) */}
      {activeSubSection === 'user_profile' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '820px' }}>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A', margin: 0 }}>
              User Profile & Account Information
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#64748B' }}>
              Manage and customize your non-confidential operational profile and identity attributes.
            </p>
          </div>

          <form
            onSubmit={handleSaveProfileSubmit}
            className="clean-panel"
            style={{
              padding: '28px',
              display: 'flex',
              flexDirection: 'column',
              gap: '22px',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
            }}
          >
            {profileSavedMsg && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: '8px',
                backgroundColor: '#F0FDF4',
                border: '1px solid #DCFCE7',
                color: '#15803D',
                fontSize: '0.82rem',
                fontWeight: 600
              }}>
                <CheckCircle2 size={16} />
                <span>Profile details successfully updated and saved!</span>
              </div>
            )}

            {/* Editable Fields Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Full Display Name *
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="e.g. John Doe"
                  required
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Job Title / Operational Role
                </label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="e.g. Security & Compliance Architect"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Department / Business Unit
                </label>
                <input
                  type="text"
                  value={editDepartment}
                  onChange={(e) => setEditDepartment(e.target.value)}
                  placeholder="e.g. Trust & Governance Platform"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Preferred Timezone
                </label>
                <select
                  value={editTimezone}
                  onChange={(e) => setEditTimezone(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    backgroundColor: '#FFFFFF',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="UTC">UTC (Coordinated Universal Time)</option>
                  <option value="America/New_York">America/New_York (EST / EDT)</option>
                  <option value="America/Los_Angeles">America/Los_Angeles (PST / PDT)</option>
                  <option value="Europe/London">Europe/London (GMT / BST)</option>
                  <option value="Europe/Berlin">Europe/Berlin (CET / CEST)</option>
                  <option value="Asia/Kolkata">Asia/Kolkata (IST +05:30)</option>
                  <option value="Asia/Singapore">Asia/Singapore (SGT +08:00)</option>
                  <option value="Asia/Tokyo">Asia/Tokyo (JST +09:00)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Contact Phone (Optional)
                </label>
                <input
                  type="tel"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  placeholder="+1 (555) 000-0000"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Professional Bio & Responsibilities
              </label>
              <textarea
                rows={3}
                value={editBio}
                onChange={(e) => setEditBio(e.target.value)}
                placeholder="Brief summary of your governance scope and decision responsibilities..."
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.86rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                  fontFamily: 'inherit',
                  resize: 'vertical'
                }}
              />
            </div>

            {/* Read-Only Confidential & Security Identity Details */}
            <div style={{
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '16px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Authentication & Governance Role (Managed by Identity Provider)
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
                <div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', display: 'block' }}>Primary Authentication Email</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }}>
                    <Lock size={12} style={{ color: '#64748B' }} />
                    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0F172A' }}>{displayEmail}</span>
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', display: 'block' }}>System Governance Role</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px', flexWrap: 'wrap' }}>
                    <Shield size={12} style={{ color: '#047857' }} />
                    <span style={{ fontSize: '0.84rem', fontWeight: 700, color: '#047857' }}>
                      {effectiveRole?.toUpperCase() || 'ADMIN'}
                    </span>
                    <span style={{ fontSize: '0.64rem', color: '#64748B' }}>(System enforced)</span>
                    {onOpenRbacModal && (
                      <button
                        type="button"
                        onClick={onOpenRbacModal}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#0F172A',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          padding: '0 4px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px',
                          marginLeft: '4px'
                        }}
                      >
                        <ShieldCheck size={12} />
                        <span>Inspect RBAC Matrix →</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', paddingTop: '8px' }}>
              <button
                type="submit"
                disabled={isSavingProfile}
                className="btn btn-primary"
                style={{
                  padding: '10px 26px',
                  fontSize: '0.86rem',
                  fontWeight: 700,
                  borderRadius: '8px',
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: isSavingProfile ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}
              >
                {isSavingProfile ? <Sparkles size={14} className="spinning" /> : <Save size={14} />}
                <span>{isSavingProfile ? 'Saving Changes...' : 'Save Profile Changes'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 3. CHANGE PHOTO MODAL (ONLY AVATARS AND UPLOAD OPTION) */}
      {isAvatarModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '16px'
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '560px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            border: '1px solid #E2E8F0',
            overflow: 'hidden'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '18px 22px',
              borderBottom: '1px solid #E2E8F0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.08rem', fontWeight: 800, color: '#0F172A' }}>
                  Change Profile Photo
                </h3>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.78rem', color: '#64748B' }}>
                  Choose an avatar for instant setup or upload your own photo.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsAvatarModalOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748B',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '20px 22px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Upload Button */}
              <div style={{
                padding: '14px 16px',
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px'
              }}>
                <div>
                  <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A' }}>
                    Upload Custom Photo
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#64748B', marginTop: '2px' }}>
                    Select a JPG, PNG, WEBP, or SVG file from your computer.
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    background: '#0F172A',
                    color: '#FFFFFF',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    border: 'none',
                    cursor: 'pointer',
                    flexShrink: 0
                  }}
                >
                  <Upload size={14} />
                  <span>Upload Photo</span>
                </button>
              </div>

              {/* Avatars Section */}
              <div>
                <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>
                  Choose an Avatar
                </div>

                {/* Category Tabs */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                  {[
                    { id: 'all', label: 'All' },
                    { id: 'executive', label: 'Executive' },
                    { id: 'robotics', label: 'AI & Robotics' },
                    { id: 'professional', label: 'Professional' },
                    { id: 'geometric', label: 'Geometric' },
                  ].map((cat) => {
                    const isActive = selectedAvatarCategory === cat.id;
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setSelectedAvatarCategory(cat.id)}
                        style={{
                          padding: '4px 12px',
                          borderRadius: '20px',
                          fontSize: '0.74rem',
                          fontWeight: isActive ? 700 : 500,
                          background: isActive ? '#0F172A' : '#F1F5F9',
                          color: isActive ? '#FFFFFF' : '#475569',
                          border: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {cat.label}
                      </button>
                    );
                  })}
                </div>

                {/* Avatars Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(84px, 1fr))',
                  gap: '10px',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  padding: '2px'
                }}>
                  {filteredAvatars.map((item) => {
                    const isSelected = editAvatarUrl === item.url;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          applyAndPersistAvatar(item.url, `Avatar "${item.name.split(' - ')[0]}" applied!`);
                        }}
                        title={item.name}
                        style={{
                          position: 'relative',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '8px 4px',
                          borderRadius: '10px',
                          background: isSelected ? 'rgba(4, 120, 87, 0.08)' : '#F8FAFC',
                          border: isSelected ? '2px solid #047857' : '1px solid #E2E8F0',
                          cursor: 'pointer',
                          outline: 'none',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <div style={{
                          width: '48px',
                          height: '48px',
                          borderRadius: '50%',
                          overflow: 'hidden',
                          backgroundColor: '#E2E8F0'
                        }}>
                          <img
                            src={item.url}
                            alt={item.name}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        </div>
                        <span style={{
                          fontSize: '0.64rem',
                          fontWeight: 600,
                          color: isSelected ? '#047857' : '#475569',
                          textAlign: 'center',
                          maxWidth: '74px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {item.name.split(' - ')[0]}
                        </span>
                        {isSelected && (
                          <span style={{
                            position: 'absolute',
                            top: '3px',
                            right: '3px',
                            width: '16px',
                            height: '16px',
                            borderRadius: '50%',
                            background: '#047857',
                            color: '#FFFFFF',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            <Check size={10} strokeWidth={3} />
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{
              padding: '14px 22px',
              borderTop: '1px solid #E2E8F0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '8px'
            }}>
              <button
                type="button"
                onClick={() => setIsAvatarModalOpen(false)}
                className="btn btn-secondary"
                style={{
                  padding: '7px 16px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  borderRadius: '6px',
                  background: '#FFFFFF',
                  border: '1px solid #CBD5E1',
                  color: '#475569',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (editAvatarUrl) {
                    applyAndPersistAvatar(editAvatarUrl, 'Profile photo updated!');
                  } else {
                    setIsAvatarModalOpen(false);
                  }
                }}
                className="btn btn-primary"
                style={{
                  padding: '7px 18px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  borderRadius: '6px',
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. SUB-SECTION: ENTERPRISE ORGANIZATIONS CARDS */}
      {activeSubSection === 'companies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Associated Companies & Organizations
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Manage, switch operational environments, or configure workspace settings for your enterprise.
              </p>
            </div>

            <button
              onClick={() => handleSubSectionClick('register')}
              className="btn btn-primary"
              style={{
                fontSize: '0.8rem',
                padding: '7px 14px',
                borderRadius: '6px',
                background: '#0F172A',
                color: '#FFFFFF',
                fontWeight: 600,
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              <Plus size={14} />
              <span>Register Company</span>
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {cleanOrgs.map((org) => {
              const isActive = activeOrg?.id === org.id;
              const isSwitching = switchingOrgId === org.id;

              return (
                <div
                  key={org.id}
                  onClick={() => handleSelectCompany(org)}
                  style={{
                    background: '#FFFFFF',
                    border: `1.5px solid ${isActive ? '#0F172A' : '#E2E8F0'}`,
                    borderRadius: '12px',
                    padding: '20px 22px',
                    cursor: isActive ? 'default' : 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    boxShadow: isActive ? '0 4px 20px -2px rgba(15, 23, 42, 0.08)' : '0 1px 3px rgba(0, 0, 0, 0.04)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = '#94A3B8';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = '#E2E8F0';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                      <div style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '10px',
                        background: isActive ? '#0F172A' : '#F1F5F9',
                        color: isActive ? '#FFFFFF' : '#475569',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: isActive ? '0 2px 8px rgba(15, 23, 42, 0.25)' : 'none'
                      }}>
                        <Building2 size={20} />
                      </div>

                      {isActive ? (
                        <span style={{
                          padding: '3px 10px',
                          borderRadius: '20px',
                          background: '#0F172A',
                          color: '#FFFFFF',
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}>
                          <Check size={11} strokeWidth={3} />
                          Active Organization
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 500 }}>
                          Available
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: '0 0 6px 0' }}>
                      {org.name}
                    </h3>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {org.domain_whitelist && org.domain_whitelist.length > 0 && (
                        <span style={{ fontSize: '0.7rem', color: '#475569', background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '2px 8px', borderRadius: '4px' }}>
                          🌐 {org.domain_whitelist.join(', ')}
                        </span>
                      )}
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: org.setup_completed ? '#F0FDF4' : '#FFFBEB',
                        color: org.setup_completed ? '#15803D' : '#B45309',
                        border: `1px solid ${org.setup_completed ? '#DCFCE7' : '#FEF3C7'}`,
                        fontWeight: 600
                      }}>
                        {org.setup_completed ? '✓ Verified Enterprise Tenant' : '● Setup In Progress'}
                      </span>
                    </div>
                  </div>

                  <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                    <div style={{ fontSize: '0.72rem', color: isActive ? '#0F172A' : '#64748B', fontWeight: isActive ? 600 : 400 }}>
                      {isActive ? '● Current operational session' : 'Click card to activate'}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onOpenOrgSettings) onOpenOrgSettings(org);
                        }}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.76rem',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: '6px',
                          color: '#0F172A',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                        onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        title="Configure workspace settings for this organization"
                      >
                        <Settings size={13} style={{ color: '#475569' }} />
                        <span>Workspace Settings</span>
                      </button>

                      {!isActive && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectCompany(org);
                          }}
                          disabled={isSwitching}
                          className="btn btn-primary"
                          style={{
                            padding: '5px 14px',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            borderRadius: '6px',
                            background: '#0F172A',
                            color: '#FFFFFF',
                            border: 'none',
                            cursor: 'pointer'
                          }}
                        >
                          {isSwitching ? 'Switching...' : 'Switch Organization'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. SUB-SECTION: DEDICATED REGISTER COMPANY PAGE (NO POPUPS) */}
      {activeSubSection === 'register' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '780px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              onClick={() => handleSubSectionClick('companies')}
              className="btn btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#0F172A',
                cursor: 'pointer'
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to Organizations</span>
            </button>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.01em' }}>
                Register Enterprise Organization
              </h2>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Provision a dedicated multi-tenant operational environment for compliance, governance, and document processing.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleRegisterCompanySubmit}
            className="clean-panel"
            style={{
              padding: '28px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
            }}
          >
            {registerError && (
              <div style={{
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA',
                color: '#B91C1C',
                fontSize: '0.82rem'
              }}>
                {registerError}
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Organization / Company Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Acme Corporation or Horizon Financial"
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Authorized Corporate Email Domains
              </label>
              <input
                type="text"
                placeholder="e.g. acme.com, acmecorp.io (comma-separated)"
                value={newCompanyDomain}
                onChange={(e) => setNewCompanyDomain(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <span style={{ fontSize: '0.74rem', color: '#64748B', marginTop: '4px', display: 'block' }}>
                Users signing in with these domains will automatically resolve to this organization.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Primary Industry & Compliance Standard
              </label>
              <select
                value={newCompanyIndustry}
                onChange={(e) => setNewCompanyIndustry(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  backgroundColor: '#FFFFFF',
                  boxSizing: 'border-box'
                }}
              >
                <option value="Enterprise AI & Decision Governance">Enterprise AI & Decision Governance (EU AI Act & NIST)</option>
                <option value="Financial Services & Wealth Management">Financial Services & Wealth Management (SEC & FINRA)</option>
                <option value="Healthcare & Life Sciences">Healthcare & Life Sciences (HIPAA & FDA)</option>
                <option value="Defense & Public Sector">Defense & Public Sector (FedRAMP & SOC2)</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '10px', paddingTop: '16px', borderTop: '1px solid #F1F5F9' }}>
              <button
                type="button"
                onClick={() => handleSubSectionClick('companies')}
                disabled={isRegistering}
                className="btn btn-secondary"
                style={{
                  padding: '9px 18px',
                  fontSize: '0.84rem',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  background: '#FFFFFF',
                  color: '#475569',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isRegistering || !newCompanyName.trim()}
                className="btn btn-primary"
                style={{
                  padding: '9px 22px',
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  borderRadius: '8px',
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: isRegistering ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {isRegistering ? <Sparkles size={14} className="spinning" /> : <Plus size={14} />}
                <span>{isRegistering ? 'Provisioning...' : 'Register Enterprise Organization'}</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
