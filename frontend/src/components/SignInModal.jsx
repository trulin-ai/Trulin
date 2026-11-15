import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  X,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Building2,
  Lock,
  Mail,
  Key,
  Eye,
  EyeOff,
  UserPlus,
  Users,
  ArrowRight,
  Laptop,
  Shield,
  Sparkles,
  RefreshCw,
  Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SignInModal() {
  const {
    isAuthModalOpen,
    setIsAuthModalOpen,
    authModalTab,
    setAuthModalTab,
    login,
    register,
    loginAsPersona,
    loginWithSSO,
    loginWithGoogleCredential,
    loginWithCorporateDomain,
    personas,
    deviceId
  } = useAuth();

  // Active tab state: 'login' | 'sso' | 'register' | 'personas'
  const [activeTab, setActiveTab] = useState(authModalTab || 'login');

  useEffect(() => {
    if (authModalTab) {
      setActiveTab(authModalTab);
    }
  }, [authModalTab]);

  // Form states
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(true);

  // Register form
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regOrgName, setRegOrgName] = useState('');
  const [regRole, setRegRole] = useState('admin');
  const [regPassword, setRegPassword] = useState('');
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Corporate SSO Domain input
  const [ssoDomainEmail, setSsoDomainEmail] = useState('');

  // Status & loading states
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const isPreviewBranch = typeof window !== 'undefined' && (
    (window.location.hostname.includes('.vercel.app') && !window.location.hostname.startsWith('context-trust-layer.vercel.app')) ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  );

  const googleBtnRef = useRef(null);

  // Reset errors when switching tabs
  const handleTabChange = (newTab) => {
    setActiveTab(newTab);
    if (setAuthModalTab) setAuthModalTab(newTab);
    setErrorMsg(null);
    setSuccessMsg(null);
  };

  // Google Identity Services (GIS) button initialization
  useEffect(() => {
    if (activeTab !== 'sso' && activeTab !== 'login') return;
    if (isPreviewBranch) return; // Skip GIS iframe on preview domains to avoid origin_mismatch
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '727103176838-d6flfi3ef09448699or2n90opjjfn0us.apps.googleusercontent.com';
    if (window.google?.accounts?.id && googleBtnRef.current && isAuthModalOpen) {
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            if (response.credential) {
              try {
                setLoading(true);
                setLoadingAction('Authenticating Google Account...');
                await loginWithGoogleCredential(response.credential);
                setSuccessMsg('Google authentication verified! Session established.');
                setTimeout(() => setIsAuthModalOpen(false), 700);
              } catch (err) {
                setErrorMsg(err.message || 'Google Sign-In failed.');
              } finally {
                setLoading(false);
                setLoadingAction('');
              }
            }
          },
          auto_select: false,
        });
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          type: 'standard',
          shape: 'rectangular',
          text: 'signin_with',
          logo_alignment: 'left',
          width: 320,
        });
      } catch (err) {
        console.warn('GIS button render error:', err);
      }
    }
  }, [googleBtnRef.current, isAuthModalOpen, isPreviewBranch, activeTab]);

  if (!isAuthModalOpen) return null;

  // Handle Corporate Email/Password Sign-In
  const handleCorporateLogin = async (e) => {
    if (e) e.preventDefault();
    if (!loginEmail.trim() || !loginPassword) {
      setErrorMsg('Please enter your work email and password.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Authenticating corporate credentials...');
    try {
      await login(loginEmail.trim(), loginPassword);
      setSuccessMsg('Authentication successful! Welcome to Context Trust Layer.');
      setTimeout(() => setIsAuthModalOpen(false), 700);
    } catch (err) {
      setErrorMsg(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle New Enterprise Account Registration
  const handleRegister = async (e) => {
    if (e) e.preventDefault();
    if (!regName.trim() || !regEmail.trim() || !regPassword) {
      setErrorMsg('Please complete all required fields.');
      return;
    }
    if (regPassword.length < 6) {
      setErrorMsg('Password must be at least 6 characters long.');
      return;
    }
    if (regPassword !== regPasswordConfirm) {
      setErrorMsg('Passwords do not match. Please verify your password confirmation.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Provisioning enterprise organization & account...');
    try {
      await register({
        name: regName.trim(),
        email: regEmail.trim(),
        password: regPassword,
        organization_name: regOrgName.trim() || undefined,
        role: regRole,
        title: regRole === 'admin' ? 'Organization Admin' : regRole === 'data_owner' ? 'Principal Data Steward' : regRole === 'reviewer' ? 'Lead Risk Auditor' : 'Autonomous Systems Engineer'
      });
      setSuccessMsg('Account and enterprise tenant created! Entering workspace...');
      setTimeout(() => setIsAuthModalOpen(false), 800);
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed. An account with this email may already exist.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle Direct Google SSO Login
  const handleGoogleSSO = async (forceSandbox = false) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(isPreviewBranch ? 'Connecting with Google Workspace...' : 'Authenticating with Google Workspace...');
    try {
      if (isPreviewBranch || forceSandbox) {
        await loginWithSSO('google', {
          sandboxEmail: 'sarah.chen@google.com',
          sandboxName: 'Sarah Chen (Google Workspace)'
        });
      } else {
        await loginWithSSO('google');
      }
      setSuccessMsg('Authenticated successfully via Google Workspace!');
      setTimeout(() => setIsAuthModalOpen(false), 700);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to sign in via Google Workspace.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle Microsoft Entra ID
  const handleMicrosoftSSO = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Connecting to Microsoft Entra ID...');
    try {
      await loginWithSSO('microsoft', {
        sandboxEmail: 'marcus.vance@microsoft.com',
        sandboxName: 'Marcus Vance (Entra ID)'
      });
      setSuccessMsg('Authenticated successfully via Microsoft Entra ID!');
      setTimeout(() => setIsAuthModalOpen(false), 700);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to sign in via Microsoft Entra ID.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle Okta OIDC
  const handleOktaSSO = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Routing through Okta Identity Cloud...');
    try {
      await loginWithSSO('okta', {
        sandboxEmail: 'compliance@okta.com',
        sandboxName: 'Enterprise Okta User'
      });
      setSuccessMsg('Authenticated successfully via Okta SSO!');
      setTimeout(() => setIsAuthModalOpen(false), 700);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to sign in via Okta.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle Corporate Domain Router
  const handleCorporateDomainSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!ssoDomainEmail.trim() || !ssoDomainEmail.includes('@')) {
      setErrorMsg('Please enter a valid corporate email address (e.g., alex@enterprise.com).');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Resolving corporate IdP federation...');
    try {
      await loginWithCorporateDomain(ssoDomainEmail.trim());
      setSuccessMsg(`Federation verified for ${ssoDomainEmail}! Redirecting...`);
      setTimeout(() => setIsAuthModalOpen(false), 700);
    } catch (err) {
      setErrorMsg(err.message || 'Corporate domain routing failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  // Handle Persona 1-Click Login
  const handlePersonaSelect = async (p) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(`Signing in as ${p.name} (${p.title})...`);
    try {
      await loginAsPersona(p);
      setSuccessMsg(`Welcome, ${p.name}! Multi-tab session active.`);
      setTimeout(() => setIsAuthModalOpen(false), 600);
    } catch (err) {
      setErrorMsg(err.message || 'Persona login failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const roleColors = {
    admin: { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' },
    data_owner: { bg: '#EFF6FF', text: '#1E40AF', border: '#BFDBFE' },
    reviewer: { bg: '#FAF5FF', text: '#6B21A8', border: '#E9D5FF' },
    developer: { bg: '#FFFBEB', text: '#92400E', border: '#FDE68A' },
    viewer: { bg: '#F8FAFC', text: '#334155', border: '#E2E8F0' },
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.72)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        padding: '16px',
        animation: 'fadeIn 0.2s ease-out'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) setIsAuthModalOpen(false);
      }}
    >
      {/* Modal Dialog Box */}
      <div
        style={{
          width: '100%',
          maxWidth: activeTab === 'personas' ? '680px' : '520px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(0, 0, 0, 0.04)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          transition: 'max-width 0.25s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        {/* Top Accent Gradient Bar */}
        <div style={{ height: '4px', background: 'linear-gradient(90deg, #FFAB4A 0%, #F5982C 50%, #EA580C 100%)' }} />

        {/* Modal Header */}
        <div
          style={{
            padding: '16px 22px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FFFFFF'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src="/Trulin-Main-NoBg.png" 
              alt="Trulin Logo" 
              style={{ height: '28px', maxWidth: '120px', objectFit: 'contain' }} 
            />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                style={{
                  fontSize: '0.62rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  backgroundColor: 'rgba(255,171,74,0.12)',
                  color: '#C2410C',
                  border: '1px solid rgba(255,171,74,0.3)',
                  borderRadius: '4px',
                  padding: '1px 6px',
                  alignSelf: 'flex-start'
                }}
              >
                Enterprise Trust Gateway
              </span>
              <span style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                Secure AI Context Layer Access
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              disabled={loading}
              onClick={() => setIsAuthModalOpen(false)}
              aria-label="Close modal"
              style={{
                width: '30px',
                height: '30px',
                borderRadius: '8px',
                border: '1px solid #E2E8F0',
                background: '#F8FAFC',
                color: '#64748B',
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = '#F1F5F9';
                  e.currentTarget.style.color = '#0F172A';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = '#F8FAFC';
                  e.currentTarget.style.color = '#64748B';
                }
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Device Policy Bar (Highlights Single Device + Multi Tab Guarantee) */}
        <div
          style={{
            padding: '8px 22px',
            backgroundColor: '#F8FAFC',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.73rem',
            color: '#475569'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={14} style={{ color: '#16A34A', flexShrink: 0 }} />
            <span style={{ fontWeight: 600, color: '#1E293B' }}>Hardware Policy:</span>
            <span>Single Active Device Session</span>
            <span style={{ color: '#CBD5E1' }}>•</span>
            <span style={{ color: '#059669', fontWeight: 500 }}>Multi-Tab Synced</span>
          </div>
          <div
            title={`Device Hardware Identifier: ${deviceId}`}
            style={{
              fontFamily: 'monospace',
              fontSize: '0.67rem',
              backgroundColor: '#EDF2F7',
              padding: '2px 7px',
              borderRadius: '4px',
              color: '#64748B',
              border: '1px solid #E2E8F0'
            }}
          >
            {deviceId ? `${deviceId.substring(0, 10)}...` : 'dev_active'}
          </div>
        </div>

        {/* Tab Navigation Header */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #E2E8F0',
            backgroundColor: '#FAFAFC',
            padding: '0 12px'
          }}
        >
          {[
            { id: 'login', label: 'Corporate Login', icon: Lock },
            { id: 'sso', label: 'Enterprise SSO', icon: Building2 },
            { id: 'register', label: 'Create Account', icon: UserPlus },
            { id: 'personas', label: 'Enterprise Personas', icon: Users }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '7px',
                  padding: '12px 10px',
                  fontSize: '0.78rem',
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? '#C2410C' : '#64748B',
                  backgroundColor: 'transparent',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #EA580C' : '2px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap'
                }}
              >
                <Icon size={14} style={{ color: isActive ? '#EA580C' : '#94A3B8' }} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Notifications / Alerts */}
        {errorMsg && (
          <div
            style={{
              margin: '14px 22px 0 22px',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: '#FEF2F2',
              border: '1px solid #FECACA',
              color: '#991B1B',
              fontSize: '0.76rem',
              display: 'flex',
              alignItems: 'center',
              gap: '9px',
              animation: 'fadeIn 0.2s ease'
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0, color: '#DC2626' }} />
            <span style={{ lineHeight: 1.4 }}>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div
            style={{
              margin: '14px 22px 0 22px',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: '#F0FDF4',
              border: '1px solid #BBF7D0',
              color: '#166534',
              fontSize: '0.76rem',
              display: 'flex',
              alignItems: 'center',
              gap: '9px',
              animation: 'fadeIn 0.2s ease'
            }}
          >
            <CheckCircle2 size={16} style={{ flexShrink: 0, color: '#16A34A' }} />
            <span style={{ lineHeight: 1.4 }}>{successMsg}</span>
          </div>
        )}

        {/* Body Content by Tab */}
        <div style={{ padding: '20px 24px 24px 24px', overflowY: 'auto', maxHeight: '72vh' }}>
          
          {/* TAB 1: CORPORATE LOGIN */}
          {activeTab === 'login' && (
            <div>
              <div style={{ marginBottom: '18px', textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', margin: '0 0 6px 0' }}>
                  Sign in with Corporate Account
                </h3>
                <p style={{ fontSize: '0.78rem', color: '#64748B', margin: 0 }}>
                  Enter your registered work credentials to access your enterprise trust workspace.
                </p>
              </div>

              <form onSubmit={handleCorporateLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Corporate Work Email
                  </label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <Mail size={15} style={{ position: 'absolute', left: '12px', color: '#94A3B8' }} />
                    <input
                      type="email"
                      required
                      placeholder="name@company.com"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px 10px 36px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.84rem',
                        color: '#0F172A',
                        outline: 'none',
                        transition: 'border-color 0.15s ease'
                      }}
                      onFocus={(e) => e.target.style.borderColor = '#EA580C'}
                      onBlur={(e) => e.target.style.borderColor = '#CBD5E1'}
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label style={{ fontSize: '0.74rem', fontWeight: 600, color: '#334155' }}>
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => setErrorMsg('For password reset assistance, contact your workspace Administrator or SSFA IT Security.')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#EA580C',
                        fontSize: '0.71rem',
                        cursor: 'pointer',
                        padding: 0
                      }}
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <Lock size={15} style={{ position: 'absolute', left: '12px', color: '#94A3B8' }} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 38px 10px 36px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.84rem',
                        color: '#0F172A',
                        outline: 'none',
                        transition: 'border-color 0.15s ease'
                      }}
                      onFocus={(e) => e.target.style.borderColor = '#EA580C'}
                      onBlur={(e) => e.target.style.borderColor = '#CBD5E1'}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: 'absolute',
                        right: '10px',
                        background: 'none',
                        border: 'none',
                        color: '#94A3B8',
                        cursor: 'pointer',
                        padding: '4px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '0.74rem', color: '#64748B', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={rememberDevice}
                      onChange={(e) => setRememberDevice(e.target.checked)}
                      style={{ accentColor: '#EA580C', cursor: 'pointer' }}
                    />
                    <span>Remember this active device</span>
                  </label>
                  <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>
                    Multi-Tab Active
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '11px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 12px rgba(234, 88, 12, 0.25)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (!loading) e.currentTarget.style.filter = 'brightness(1.05)';
                  }}
                  onMouseLeave={(e) => {
                    if (!loading) e.currentTarget.style.filter = 'none';
                  }}
                >
                  {loading ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" />
                      <span>{loadingAction || 'Signing in...'}</span>
                    </>
                  ) : (
                    <>
                      <Lock size={15} />
                      <span>Sign In to Workspace</span>
                    </>
                  )}
                </button>
              </form>

              {/* Or Quick Enterprise SSO Switch */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '20px 0 16px 0' }}>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#E2E8F0' }} />
                <span style={{ fontSize: '0.7rem', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Or Connect With
                </span>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#E2E8F0' }} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleGoogleSSO(false)}
                  style={{
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    backgroundColor: '#FFFFFF',
                    color: '#1E293B',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#F8FAFC'; }}
                  onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                  </svg>
                  <span>Google SSO</span>
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleTabChange('personas')}
                  style={{
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    backgroundColor: '#FFFFFF',
                    color: '#1E293B',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#F8FAFC'; }}
                  onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
                >
                  <Users size={15} style={{ color: '#EA580C' }} />
                  <span>Demo Personas</span>
                </button>
              </div>

              <div style={{ marginTop: '16px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
                  Don't have an enterprise account?{' '}
                  <button
                    type="button"
                    onClick={() => handleTabChange('register')}
                    style={{ background: 'none', border: 'none', color: '#EA580C', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                  >
                    Create Organization Account
                  </button>
                </span>
              </div>
            </div>
          )}

          {/* TAB 2: ENTERPRISE SSO */}
          {activeTab === 'sso' && (
            <div>
              <div style={{ marginBottom: '18px', textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', margin: '0 0 6px 0' }}>
                  Enterprise Single Sign-On (SSO)
                </h3>
                <p style={{ fontSize: '0.78rem', color: '#64748B', margin: 0 }}>
                  Federate authentication through your corporate Identity Provider (IdP) with automated RBAC mapping.
                </p>
              </div>

              {isPreviewBranch && (
                <div
                  style={{
                    marginBottom: '16px',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    backgroundColor: '#EFF6FF',
                    border: '1px solid #BFDBFE',
                    color: '#1E40AF',
                    fontSize: '0.74rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Info size={15} style={{ flexShrink: 0, color: '#2563EB' }} />
                  <span>
                    <strong>Preview Deployment Active:</strong> 1-Click enterprise sandbox SSO is enabled without requiring domain redirect whitelisting.
                  </span>
                </div>
              )}

              {/* SSO Provider Buttons Stack */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Google Workspace */}
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleGoogleSSO(false)}
                  style={{
                    width: '100%',
                    padding: '11px 16px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    backgroundColor: '#FFFFFF',
                    color: '#1E293B',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#F8FAFC'; e.currentTarget.style.borderColor = '#94A3B8'; }}}
                  onMouseLeave={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#FFFFFF'; e.currentTarget.style.borderColor = '#CBD5E1'; }}}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                    </svg>
                    <span>Sign in with Google Workspace</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', backgroundColor: '#F1F5F9', padding: '2px 8px', borderRadius: '4px' }}>
                    OAuth 2.0 / OIDC
                  </span>
                </button>

                {/* Microsoft Entra ID */}
                <button
                  type="button"
                  disabled={loading}
                  onClick={handleMicrosoftSSO}
                  style={{
                    width: '100%',
                    padding: '11px 16px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    backgroundColor: '#FFFFFF',
                    color: '#1E293B',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#F8FAFC'; e.currentTarget.style.borderColor = '#94A3B8'; }}}
                  onMouseLeave={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#FFFFFF'; e.currentTarget.style.borderColor = '#CBD5E1'; }}}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <svg width="20" height="20" viewBox="0 0 21 21">
                      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                    </svg>
                    <span>Sign in with Microsoft Entra ID</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', backgroundColor: '#F1F5F9', padding: '2px 8px', borderRadius: '4px' }}>
                    Azure AD SAML
                  </span>
                </button>

                {/* Okta Enterprise */}
                <button
                  type="button"
                  disabled={loading}
                  onClick={handleOktaSSO}
                  style={{
                    width: '100%',
                    padding: '11px 16px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    backgroundColor: '#FFFFFF',
                    color: '#1E293B',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#F8FAFC'; e.currentTarget.style.borderColor = '#94A3B8'; }}}
                  onMouseLeave={(e) => { if (!loading) { e.currentTarget.style.backgroundColor = '#FFFFFF'; e.currentTarget.style.borderColor = '#CBD5E1'; }}}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#007DC1', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#FFFFFF' }} />
                    </div>
                    <span>Sign in with Okta</span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', backgroundColor: '#F1F5F9', padding: '2px 8px', borderRadius: '4px' }}>
                    Okta Identity Cloud
                  </span>
                </button>
              </div>

              {/* Corporate Domain Direct Routing Form */}
              <div style={{ marginTop: '20px', paddingTop: '18px', borderTop: '1px solid #E2E8F0' }}>
                <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#1E293B', marginBottom: '4px' }}>
                  Custom Corporate Domain Routing
                </span>
                <p style={{ fontSize: '0.72rem', color: '#64748B', margin: '0 0 10px 0' }}>
                  If your organization uses a custom IdP or private SSO portal, enter your work email to auto-discover your corporate gateway:
                </p>
                <form onSubmit={handleCorporateDomainSubmit} style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="email"
                    required
                    placeholder="you@corporate-domain.com"
                    value={ssoDomainEmail}
                    onChange={(e) => setSsoDomainEmail(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '9px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.8rem',
                      outline: 'none'
                    }}
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    style={{
                      padding: '9px 16px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#0F172A',
                      color: '#FFFFFF',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: loading ? 'not-allowed' : 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    Route SSO
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 3: CREATE ACCOUNT / REGISTER */}
          {activeTab === 'register' && (
            <div>
              <div style={{ marginBottom: '16px', textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0' }}>
                  Create Enterprise Workspace & Account
                </h3>
                <p style={{ fontSize: '0.76rem', color: '#64748B', margin: 0 }}>
                  Initialize your dedicated enterprise tenant with complete compliance isolation and audit trails.
                </p>
              </div>

              <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.73rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Full Name *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. John Doe"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.82rem',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.73rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Corporate Email *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="john@company.com"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.82rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.73rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Organization / Tenant Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Apex Global Corp"
                      value={regOrgName}
                      onChange={(e) => setRegOrgName(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.82rem',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.73rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Initial Enterprise Role
                    </label>
                    <select
                      value={regRole}
                      onChange={(e) => setRegRole(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 8px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.8rem',
                        backgroundColor: '#FFFFFF',
                        outline: 'none'
                      }}
                    >
                      <option value="admin">Administrator (Full Access)</option>
                      <option value="data_owner">Principal Data Steward</option>
                      <option value="reviewer">Lead Risk Auditor</option>
                      <option value="developer">Systems / AI Engineer</option>
                      <option value="viewer">Compliance Observer</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.73rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Password * (Min 6 chars)
                    </label>
                    <input
                      type={showRegPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.82rem',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label style={{ fontSize: '0.73rem', fontWeight: 600, color: '#334155' }}>
                        Confirm Password *
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowRegPassword(!showRegPassword)}
                        style={{ background: 'none', border: 'none', color: '#64748B', fontSize: '0.7rem', cursor: 'pointer', padding: 0 }}
                      >
                        {showRegPassword ? 'Hide' : 'Show'}
                      </button>
                    </div>
                    <input
                      type={showRegPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={regPasswordConfirm}
                      onChange={(e) => setRegPasswordConfirm(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.82rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>

                <div style={{ padding: '8px 12px', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '0.71rem', color: '#64748B', display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                  <Info size={14} style={{ flexShrink: 0, marginTop: '2px', color: '#0284C7' }} />
                  <span>
                    New tenant creation automatically bootstraps starter knowledge graphs, RBAC separation of duties, and registers your current hardware as the primary active session device.
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    marginTop: '4px',
                    width: '100%',
                    padding: '11px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 12px rgba(234, 88, 12, 0.25)',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {loading ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" />
                      <span>{loadingAction || 'Creating tenant...'}</span>
                    </>
                  ) : (
                    <>
                      <UserPlus size={15} />
                      <span>Create Account & Launch Workspace</span>
                    </>
                  )}
                </button>
              </form>

              <div style={{ marginTop: '14px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => handleTabChange('login')}
                    style={{ background: 'none', border: 'none', color: '#EA580C', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                  >
                    Sign In
                  </button>
                </span>
              </div>
            </div>
          )}

          {/* TAB 4: ENTERPRISE PERSONAS (DEMO / INSTANT ACCESS) */}
          {activeTab === 'personas' && (
            <div>
              <div style={{ marginBottom: '16px', textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0' }}>
                  Enterprise Persona Quick Access
                </h3>
                <p style={{ fontSize: '0.78rem', color: '#64748B', margin: 0 }}>
                  Test multi-stakeholder workflows and Separation of Duties (SoD) policies with pre-configured personas:
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {(personas || []).map((p) => {
                  const roleStyle = roleColors[p.role] || roleColors.developer;
                  return (
                    <div
                      key={p.id}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '10px',
                        border: '1px solid #E2E8F0',
                        backgroundColor: '#FFFFFF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '12px',
                        transition: 'all 0.15s ease',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#EA580C';
                        e.currentTarget.style.backgroundColor = '#FFFBF7';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#E2E8F0';
                        e.currentTarget.style.backgroundColor = '#FFFFFF';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <img
                          src={p.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}`}
                          alt={p.name}
                          style={{
                            width: '38px',
                            height: '38px',
                            borderRadius: '10px',
                            border: '1px solid #E2E8F0',
                            backgroundColor: '#F8FAFC'
                          }}
                        />
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                              {p.name}
                            </span>
                            <span
                              style={{
                                fontSize: '0.64rem',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                backgroundColor: roleStyle.bg,
                                color: roleStyle.text,
                                border: `1px solid ${roleStyle.border}`
                              }}
                            >
                              {p.role.replace('_', ' ')}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                            {p.title} • {p.department}
                          </div>
                          <div style={{ fontSize: '0.67rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                            {p.email}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => handlePersonaSelect(p)}
                        style={{
                          padding: '7px 14px',
                          borderRadius: '6px',
                          border: '1px solid #CBD5E1',
                          backgroundColor: '#FFFFFF',
                          color: '#0F172A',
                          fontSize: '0.76rem',
                          fontWeight: 600,
                          cursor: loading ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          whiteSpace: 'nowrap',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={(e) => {
                          if (!loading) {
                            e.currentTarget.style.backgroundColor = '#EA580C';
                            e.currentTarget.style.color = '#FFFFFF';
                            e.currentTarget.style.borderColor = '#EA580C';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!loading) {
                            e.currentTarget.style.backgroundColor = '#FFFFFF';
                            e.currentTarget.style.color = '#0F172A';
                            e.currentTarget.style.borderColor = '#CBD5E1';
                          }
                        }}
                      >
                        <span>Access</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </div>

        {/* Enterprise Security Footer */}
        <div
          style={{
            padding: '12px 22px',
            backgroundColor: '#FAFAFC',
            borderTop: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.71rem',
            color: '#64748B'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Shield size={13} style={{ color: '#EA580C', flexShrink: 0 }} />
            <span>NIST AI 600-1 & SOC2 Compliant Identity Federation</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#94A3B8' }}>Single Device Active</span>
            <span style={{ color: '#CBD5E1' }}>•</span>
            <span style={{ color: '#16A34A', fontWeight: 600 }}>Multi-Tab Synced</span>
          </div>
        </div>

      </div>
    </div>
  );
}
