import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const DEFAULT_ENTERPRISE_PERSONAS = [
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Sarah Chen',
    email: 'sarah.chen@ssfa.com',
    role: 'admin',
    title: 'Administrator',
    department: 'Risk, Trust & Security',
    organization_name: 'SSFA Capital Holdings',
    organization_id: '11111111-1111-1111-1111-111111111111',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Sarah'
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    name: 'Marcus Vance',
    email: 'marcus.vance@ssfa.com',
    role: 'data_owner',
    title: 'Principal Data Steward',
    department: 'Enterprise Data Platform',
    organization_name: 'SSFA Capital Holdings',
    organization_id: '11111111-1111-1111-1111-111111111111',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Marcus'
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    name: 'Elena Rostova',
    email: 'elena.rostova@ssfa.com',
    role: 'reviewer',
    title: 'Lead Risk Auditor',
    department: 'Independent Governance & Oversight',
    organization_name: 'SSFA Capital Holdings',
    organization_id: '11111111-1111-1111-1111-111111111111',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Elena'
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    name: 'Alex Vance',
    email: 'alex.vance@ssfa.com',
    role: 'developer',
    title: 'Autonomous Systems Engineer',
    department: 'AI Operations & Platform Engineering',
    organization_name: 'SSFA Capital Holdings',
    organization_id: '11111111-1111-1111-1111-111111111111',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Alex'
  },
  {
    id: '66666666-6666-6666-6666-666666666666',
    name: 'Devin Zhao',
    email: 'devin.zhao@regulatory-watch.org',
    role: 'viewer',
    title: 'Compliance Observer',
    department: 'Regulatory Assurance & Oversight',
    organization_name: 'SSFA Capital Holdings',
    organization_id: '11111111-1111-1111-1111-111111111111',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Devin'
  }
];

export const getOrCreateDeviceId = () => {
  if (typeof window === 'undefined') return 'device_client';
  try {
    let id = localStorage.getItem('ctl_device_id');
    if (!id) {
      id = 'dev_' + (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
      localStorage.setItem('ctl_device_id', id);
    }
    return id;
  } catch {
    return 'dev_default';
  }
};

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('ctl_token') || null);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [organization, setOrganization] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_org');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [myOrganizations, setMyOrganizations] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_my_orgs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [myInvitations, setMyInvitations] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_my_invitations');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [isNewUser, setIsNewUser] = useState(false);

  const [personas, setPersonas] = useState(DEFAULT_ENTERPRISE_PERSONAS);
  const [ssoProviders, setSsoProviders] = useState([]);
  const [rbacMatrix, setRbacMatrix] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState('login'); // 'login' | 'sso' | 'register' | 'personas'
  const [deviceId] = useState(() => getOrCreateDeviceId());
  const [sessionSupersededNotice, setSessionSupersededNotice] = useState(null);

  // Broadcast sync events to all other tabs on this device
  const broadcastSyncEvent = (type, payload) => {
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        const bc = new BroadcastChannel('ctl_sync_channel');
        bc.postMessage({ type, payload });
        bc.close();
      }
    } catch (err) {
      console.warn('Broadcast sync error:', err);
    }
  };

  // Multi-tab synchronization on the same device
  useEffect(() => {
    let channel = null;
    if (typeof BroadcastChannel !== 'undefined') {
      try {
        channel = new BroadcastChannel('ctl_sync_channel');
        channel.onmessage = (event) => {
          const { type, payload } = event.data || {};
          if (type === 'AUTH_LOGIN') {
            if (payload?.token) {
              setToken(payload.token);
              setUser(payload.user);
              if (payload.organization) setOrganization(payload.organization);
              if (payload.myOrganizations) setMyOrganizations(payload.myOrganizations);
              setIsAuthModalOpen(false);
              setSessionSupersededNotice(null);
            }
          } else if (type === 'AUTH_LOGOUT') {
            setToken(null);
            setUser(null);
            setOrganization(null);
            setMyOrganizations([]);
          } else if (type === 'USER_UPDATED') {
            if (payload) setUser(payload);
          } else if (type === 'SESSION_SUPERSEDED') {
            setSessionSupersededNotice(
              'Your account was signed into on another device. In compliance with enterprise security policy, this session has been closed.'
            );
            logout(false);
          }
        };
      } catch (err) {
        console.warn('BroadcastChannel sync init error:', err);
      }
    }

    // Fallback: storage event listener for cross-tab sync
    const handleStorage = (e) => {
      if (e.key === 'ctl_token') {
        if (!e.newValue) {
          setToken(null);
          setUser(null);
          setOrganization(null);
          setMyOrganizations([]);
        } else {
          setToken(e.newValue);
          try {
            const u = JSON.parse(localStorage.getItem('ctl_user') || 'null');
            if (u) setUser(u);
            const o = JSON.parse(localStorage.getItem('ctl_org') || 'null');
            if (o) setOrganization(o);
          } catch {}
        }
      } else if (e.key === 'ctl_user') {
        try {
          if (e.newValue) setUser(JSON.parse(e.newValue));
        } catch {}
      }
    };
    window.addEventListener('storage', handleStorage);

    return () => {
      if (channel) channel.close();
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  // 1. Fetch available personas, SSO providers, and RBAC matrix
  const refreshPersonas = async () => {
    try {
      const res = await fetch('/v1/auth/personas');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setPersonas(data);
          return data;
        }
      }
    } catch (err) {
      console.warn('Failed to fetch personas, using defaults:', err);
    }
    return DEFAULT_ENTERPRISE_PERSONAS;
  };

  useEffect(() => {
    async function initAuth() {
      try {
        await refreshPersonas();
        // 2. Fetch SSO providers
        const ssoRes = await fetch('/v1/auth/sso/providers');
        if (ssoRes.ok) {
          const ssoData = await ssoRes.json();
          setSsoProviders(ssoData);
        }
        // 3. Fetch RBAC matrix
        const rbacRes = await fetch('/v1/auth/permissions/matrix');
        if (rbacRes.ok) {
          const rbacData = await rbacRes.json();
          setRbacMatrix(rbacData);
        }
      } catch (err) {
        console.warn('Failed to init auth metadata:', err);
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, []);

  const [simulatedRole, setSimulatedRole] = useState(null);

  // Compute effectiveRole (only admin users can simulate other roles)
  const userActualRole = (user?.role || 'admin').toLowerCase();
  const effectiveRole = (userActualRole === 'admin' && simulatedRole) ? simulatedRole.toLowerCase() : userActualRole;

  // Update granted permissions whenever effectiveRole or rbacMatrix changes
  useEffect(() => {
    if (!user && !simulatedRole) {
      setPermissions([]);
      return;
    }
    const roleKey = effectiveRole;
    if (rbacMatrix?.roles?.[roleKey]?.permissions) {
      setPermissions(rbacMatrix.roles[roleKey].permissions);
    } else {
      // Local fallback until matrix finishes loading
      if (roleKey === 'admin') {
        setPermissions(['sources:read', 'sources:sync', 'sources:manage', 'claims:read', 'claims:extract', 'claims:edit', 'claims:delete', 'conflicts:read', 'conflicts:resolve', 'conflicts:override', 'decisions:evaluate', 'decisions:audit', 'org:settings', 'org:members', 'org:invite']);
      } else if (roleKey === 'data_owner') {
        setPermissions(['sources:read', 'sources:sync', 'sources:manage', 'claims:read', 'claims:extract', 'claims:edit', 'conflicts:read', 'decisions:evaluate', 'decisions:audit']);
      } else if (roleKey === 'reviewer') {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read', 'conflicts:resolve', 'decisions:evaluate', 'decisions:audit']);
      } else if (roleKey === 'developer') {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read', 'decisions:evaluate']);
      } else {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read']);
      }
    }
  }, [user, simulatedRole, rbacMatrix, effectiveRole]);

  // 2. Validate token and load user profile if token exists
  useEffect(() => {
    if (!token) return;
    async function verifySession() {
      try {
        const res = await fetch('/v1/auth/me', {
          headers: {
            Authorization: `Bearer ${token}`,
            'X-Device-Id': deviceId,
          }
        });
        if (res.ok) {
          const profile = await res.json();
          setUser(profile);
          localStorage.setItem('ctl_user', JSON.stringify(profile));
          if (profile.organization_id) {
            const orgData = {
              id: profile.organization_id,
              name: profile.organization_name || 'Enterprise Tenant'
            };
            setOrganization(orgData);
            localStorage.setItem('ctl_org', JSON.stringify(orgData));
          }
        } else if (res.status === 401 || res.status === 403 || res.status === 404) {
          try {
            const errJson = await res.json();
            if (errJson?.detail && typeof errJson.detail === 'string' && errJson.detail.includes('SESSION_SUPERSEDED')) {
              setSessionSupersededNotice(
                'Your account was signed into on another device. In compliance with enterprise security policy, only one active device session is permitted.'
              );
              broadcastSyncEvent('SESSION_SUPERSEDED');
            }
          } catch {}
          logout(false);
        }
      } catch (err) {
        console.warn('Error verifying session:', err);
      }
    }
    verifySession();
  }, [token, deviceId]);

  // 3. Handle live OAuth redirect callback (e.g. ?code=... from Google)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      async function exchangeCode() {
        try {
          setIsLoading(true);
          const redirectUri = window.location.origin + window.location.pathname;
          const res = await fetch('/v1/auth/sso/callback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              provider: 'google',
              code: code,
              redirect_uri: redirectUri,
              device_id: deviceId,
            })
          });
          if (res.ok) {
            const data = await res.json();
            handleAuthSuccess(data);
            window.history.replaceState({}, document.title, '/');
          } else {
            const err = await res.json().catch(() => ({}));
            console.error('OAuth callback failed:', err);
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        } catch (err) {
          console.error('OAuth callback network error:', err);
        } finally {
          setIsLoading(false);
        }
      }
      exchangeCode();
    }
  }, [deviceId]);

  const handleAuthSuccess = (data) => {
    const { access_token, user: userData, organizations: orgs, pending_invitations: invites, is_new_user } = data;
    setToken(access_token);
    setUser(userData);
    localStorage.setItem('ctl_token', access_token);
    localStorage.setItem('ctl_user', JSON.stringify(userData));
    let orgData = null;
    if (userData && userData.organization_id) {
      orgData = {
        id: userData.organization_id,
        name: userData.organization_name || 'Enterprise Tenant'
      };
      setOrganization(orgData);
      localStorage.setItem('ctl_org', JSON.stringify(orgData));
      localStorage.setItem('context_layer_active_org_id', userData.organization_id);
    }
    if (orgs && Array.isArray(orgs)) {
      setMyOrganizations(orgs);
      localStorage.setItem('ctl_my_orgs', JSON.stringify(orgs));
      if (!orgData && orgs.length > 0) {
        setOrganization(orgs[0]);
        localStorage.setItem('ctl_org', JSON.stringify(orgs[0]));
      }
    }
    if (invites && Array.isArray(invites)) {
      setMyInvitations(invites);
      localStorage.setItem('ctl_my_invitations', JSON.stringify(invites));
    }
    if (is_new_user !== undefined) {
      setIsNewUser(Boolean(is_new_user));
    }
    setIsAuthModalOpen(false);
    setSessionSupersededNotice(null);

    // Multi-tab broadcast
    broadcastSyncEvent('AUTH_LOGIN', {
      token: access_token,
      user: userData,
      organization: orgData || (orgs && orgs[0]) || null,
      myOrganizations: orgs || [],
    });
  };

  const login = async (email, password) => {
    const res = await fetch('/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, device_id: deviceId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Sign in failed. Check your credentials.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const register = async (formData) => {
    const res = await fetch('/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...formData, device_id: deviceId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const loginAsPersona = async (persona) => {
    try {
      const res = await fetch('/v1/auth/persona-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: persona.id, device_id: deviceId })
      });
      if (res.ok) {
        const data = await res.json();
        handleAuthSuccess(data);
        setSimulatedRole(null);
        return data;
      }
    } catch (err) {
      console.warn('Persona quick-login error:', err);
    }
    // Fallback: set local persona
    setUser(persona);
    setSimulatedRole(null);
    localStorage.setItem('ctl_user', JSON.stringify(persona));
    setIsAuthModalOpen(false);
  };

  const loginWithSSO = async (provider, customOptions = {}) => {
    try {
      // 1. Inquire provider authorization endpoint
      const currentRedirectUri = `${window.location.origin}/auth/callback`;
      const authRes = await fetch(`/v1/auth/sso/authorize/${provider}?redirect_uri=${encodeURIComponent(currentRedirectUri)}`);
      if (!authRes.ok) {
        const err = await authRes.json();
        throw new Error(err.detail || `Failed to initiate ${provider} SSO authorization`);
      }
      const authData = await authRes.json();

      if (!authData.is_sandbox && authData.authorization_url && !customOptions.sandboxEmail) {
        // Production live OAuth redirect
        window.location.href = authData.authorization_url;
        return;
      }

      // 2. Sandbox / Developer mock flow for instant local testing
      const callbackPayload = {
        provider,
        code: `sandbox_code_${Date.now()}`,
        mock_email: customOptions.sandboxEmail || (
          provider === 'google'
            ? 'sarah.chen@google.com'
            : provider === 'microsoft'
            ? 'marcus.vance@microsoft.com'
            : 'compliance@okta.com'
        ),
        mock_name: customOptions.sandboxName || (
          provider === 'google'
            ? 'Sarah Chen (Google Workspace)'
            : provider === 'microsoft'
            ? 'Marcus Vance (Entra ID)'
            : 'Enterprise Okta User'
        ),
        device_id: deviceId
      };

      const cbRes = await fetch('/v1/auth/sso/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(callbackPayload)
      });

      if (!cbRes.ok) {
        const err = await cbRes.json();
        throw new Error(err.detail || 'SSO authentication failed');
      }

      const data = await cbRes.json();
      handleAuthSuccess(data);
      return data;
    } catch (err) {
      console.error('SSO login error:', err);
      throw err;
    }
  };

  const loginWithCorporateDomain = async (corporateEmail, fullName, organizationName) => {
    const res = await fetch('/v1/auth/sso/sandbox-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'sso',
        corporate_email: corporateEmail,
        full_name: fullName || undefined,
        organization_name: organizationName || undefined,
        device_id: deviceId,
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Corporate domain SSO failed.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const switchOrganization = async (orgId) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`/v1/organizations/${orgId}/switch`, {
      method: 'POST',
      headers,
      body: JSON.stringify({})
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to switch organization');
    }
    const data = await res.json();
    handleAuthSuccess({
      access_token: data.access_token,
      user: data.user
    });
    if (data.active_organization) {
      const orgObj = {
        id: data.active_organization.id,
        name: data.active_organization.name,
        slug: data.active_organization.slug,
        domain_whitelist: data.active_organization.domain_whitelist || [],
        member_count: data.active_organization.member_count || 0
      };
      setOrganization(orgObj);
      localStorage.setItem('ctl_org', JSON.stringify(orgObj));
      localStorage.setItem('context_layer_active_org_id', data.active_organization.id);
    }
    await refreshMyOrganizations();
    return data;
  };

  const loginWithGoogleCredential = async (credential) => {
    try {
      setIsLoading(true);
      const res = await fetch('/v1/auth/sso/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'google',
          credential,
          device_id: deviceId,
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Google sign-in token verification failed.');
      }
      const data = await res.json();
      handleAuthSuccess(data);
      return data;
    } catch (err) {
      console.error('Google sign-in error:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const acceptInvitation = async (inviteId) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`/v1/organizations/invites/${inviteId}/accept-direct`, {
      method: 'POST',
      headers,
      body: JSON.stringify({})
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to accept invitation.');
    }
    const data = await res.json();
    handleAuthSuccess({
      access_token: data.access_token,
      user: data.user
    });
    if (data.active_organization) {
      const orgObj = {
        id: data.active_organization.id,
        name: data.active_organization.name,
        slug: data.active_organization.slug,
        domain_whitelist: data.active_organization.domain_whitelist || [],
        member_count: data.active_organization.member_count || 0
      };
      setOrganization(orgObj);
      localStorage.setItem('ctl_org', JSON.stringify(orgObj));
      localStorage.setItem('context_layer_active_org_id', data.active_organization.id);
    }
    setMyInvitations((prev) => {
      const updated = prev.filter((inv) => inv.id !== inviteId);
      localStorage.setItem('ctl_my_invitations', JSON.stringify(updated));
      return updated;
    });
    await refreshMyOrganizations();
    return data;
  };

  const refreshMyOrganizations = async () => {
    if (!token) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [orgsRes, invitesRes] = await Promise.all([
        fetch('/v1/organizations/my-organizations', { headers }),
        fetch('/v1/organizations/my-invitations', { headers })
      ]);
      if (orgsRes.ok) {
        const orgs = await orgsRes.json();
        if (Array.isArray(orgs)) {
          setMyOrganizations(orgs);
          localStorage.setItem('ctl_my_orgs', JSON.stringify(orgs));
        }
      }
      if (invitesRes.ok) {
        const invites = await invitesRes.json();
        if (Array.isArray(invites)) {
          setMyInvitations(invites);
          localStorage.setItem('ctl_my_invitations', JSON.stringify(invites));
        }
      }
    } catch (err) {
      console.warn('Failed to refresh user organizations/invites:', err);
    }
  };

  const isTabVisible = (tabKey) => {
    if (tabKey === 'home' || tabKey === 'profile' || tabKey === 'settings' || tabKey === 'register_company') return true;
    const meta = ROLE_METADATA[effectiveRole] || ROLE_METADATA.admin;
    return meta.allowed_tabs ? meta.allowed_tabs.includes(tabKey) : true;
  };

  const getSodGuard = (actionKey) => {
    const rule = SOD_RULES[actionKey];
    if (!rule) return { allowed: true };
    const reason = rule[effectiveRole];
    if (reason) {
      return { allowed: false, reason };
    }
    return { allowed: true };
  };

  const hasPermission = (permissionKey) => {
    if (!permissions || permissions.length === 0) return false;
    return permissions.includes(permissionKey);
  };

  const logout = (broadcast = true) => {
    setToken(null);
    setUser(null);
    setOrganization(null);
    setSimulatedRole(null);
    setMyOrganizations([]);
    setMyInvitations([]);
    setIsNewUser(false);
    localStorage.removeItem('ctl_token');
    localStorage.removeItem('ctl_user');
    localStorage.removeItem('ctl_org');
    localStorage.removeItem('ctl_my_orgs');
    localStorage.removeItem('ctl_my_invitations');
    if (broadcast) {
      broadcastSyncEvent('AUTH_LOGOUT');
    }
  };

  const updateUser = (updatedFields) => {
    setUser(prev => {
      const merged = { ...(prev || {}), ...updatedFields };
      try {
        localStorage.setItem('ctl_user', JSON.stringify(merged));
      } catch (e) {
        console.warn('Failed to persist user profile:', e);
      }
      broadcastSyncEvent('USER_UPDATED', merged);
      return merged;
    });
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        updateUser,
        organization,
        personas,
        ssoProviders,
        rbacMatrix,
        permissions,
        hasPermission,
        effectiveRole,
        simulatedRole,
        setSimulatedRole,
        isTabVisible,
        getSodGuard,
        roleMetadata: ROLE_METADATA[effectiveRole] || ROLE_METADATA.admin,
        isLoading,
        isAuthenticated: !!token && !!user,
        isAuthModalOpen,
        setIsAuthModalOpen,
        authModalTab,
        setAuthModalTab,
        myOrganizations,
        myInvitations,
        isNewUser,
        setIsNewUser,
        deviceId,
        sessionSupersededNotice,
        setSessionSupersededNotice,
        broadcastSyncEvent,
        login,
        register,
        handleAuthSuccess,
        loginAsPersona,
        loginWithSSO,
        loginWithGoogleCredential,
        loginWithCorporateDomain,
        switchOrganization,
        acceptInvitation,
        refreshMyOrganizations,
        logout,
        refreshPersonas,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const ROLE_METADATA = {
  admin: {
    title: 'Administrator',
    role: 'admin',
    description: 'Executive authority: full tenant governance, policy overrides, user promotions, and audit sign-offs.',
    separation_of_duties: 'Executive override authority across all workflows.',
    badge_color: '#047857',
    badge_bg: 'rgba(4, 120, 87, 0.12)',
    allowed_tabs: ['home', 'profile', 'settings', 'register_company', 'demo', 'live_ingestion', 'visual_lineage', 'context_curator', 'ingestion', 'integrations', 'audit', 'team', 'playground', 'conflicts'],
  },
  data_owner: {
    title: 'Data Steward',
    role: 'data_owner',
    description: 'Authority over data source ingestion, pipeline syncs, document ingestion, and claim definition curation.',
    separation_of_duties: 'Restricted from resolving policy conflicts to prevent unilateral compliance tampering (SoD enforced).',
    badge_color: '#1D4ED8',
    badge_bg: 'rgba(29, 78, 216, 0.12)',
    allowed_tabs: ['home', 'profile', 'live_ingestion', 'visual_lineage', 'ingestion', 'playground', 'audit'],
  },
  reviewer: {
    title: 'Risk Auditor / Reviewer',
    role: 'reviewer',
    description: 'Authority to review, approve, and resolve semantic policy contradictions and evidence exceptions.',
    separation_of_duties: 'Restricted from altering source ingestion connectors or uploading raw data (SoD enforced).',
    badge_color: '#4338CA',
    badge_bg: 'rgba(67, 56, 202, 0.12)',
    allowed_tabs: ['home', 'profile', 'demo', 'visual_lineage', 'context_curator', 'conflicts', 'audit', 'playground'],
  },
  developer: {
    title: 'Operator / Developer / Agent',
    role: 'developer',
    description: 'Operational access to query verified context layer, run decision simulations, and configure MCP connectors.',
    separation_of_duties: 'Read-only policy access; no authority to resolve conflicts or alter source pipelines (SoD enforced).',
    badge_color: '#B45309',
    badge_bg: 'rgba(180, 83, 9, 0.12)',
    allowed_tabs: ['home', 'profile', 'demo', 'visual_lineage', 'ingestion', 'integrations', 'playground'],
  },
  viewer: {
    title: 'Compliance Observer',
    role: 'viewer',
    description: 'Read-only access to trust score dashboards and lineage graphs. Zero mutation privileges.',
    separation_of_duties: 'Zero mutation privileges across all systems (Observer Mode).',
    badge_color: '#64748B',
    badge_bg: 'rgba(100, 116, 139, 0.12)',
    allowed_tabs: ['home', 'profile', 'visual_lineage', 'audit', 'playground'],
  },
};

export const SOD_RULES = {
  'conflicts:resolve': {
    data_owner: 'Restricted by Separation of Duties: Data Stewards cannot resolve conflicts on data they ingested. Requires Risk Auditor approval.',
    developer: 'Restricted: Operators/Developers cannot resolve governance contradictions.',
    viewer: 'Observer Mode: Read-only viewers cannot resolve governance conflicts.',
  },
  'sources:manage': {
    reviewer: 'Restricted by Separation of Duties: Risk Auditors cannot alter raw data sources or trigger pipeline syncs.',
    developer: 'Restricted: Developers cannot register or configure source ingestion connectors.',
    viewer: 'Observer Mode: Viewers cannot upload documents or alter data sources.',
  },
  'decisions:simulate': {
    viewer: 'Observer Mode: Decision simulations are restricted for read-only observers.',
  },
  'org:members': {
    data_owner: 'Restricted: Member invitations and role assignments require Admin authority.',
    reviewer: 'Restricted: Member invitations and role assignments require Admin authority.',
    developer: 'Restricted: Member invitations and role assignments require Admin authority.',
    viewer: 'Restricted: Member invitations and role assignments require Admin authority.',
  },
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
