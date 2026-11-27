import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';

export function useTeamAccess({ orgId, activityFilter = 'all', showToast }) {
  const { token, user: authUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [activities, setActivities] = useState([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [domainsData, setDomainsData] = useState({ domains: [], summary: {}, is_preview: false });
  const [capabilities, setCapabilities] = useState({
    can_view_members: true,
    can_invite_members: false,
    can_change_roles: false,
    can_remove_members: false,
    can_view_activity: false,
    can_export_activity: false,
    can_view_domains: true,
  });
  const [roleCatalog, setRoleCatalog] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const authHeaders = useCallback(() => {
    const activeToken = token || localStorage.getItem('ctl_token');
    return activeToken
      ? { 'Content-Type': 'application/json', Authorization: `Bearer ${activeToken}` }
      : { 'Content-Type': 'application/json' };
  }, [token]);

  const fetchCapabilities = useCallback(async () => {
    try {
      const res = await fetch('/v1/auth/capabilities', { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.capabilities) setCapabilities(data.capabilities);
        if (data.roles) setRoleCatalog(data.roles);
      }
    } catch {
      // Keep least-privilege defaults on failure
    }
  }, [authHeaders]);

  const fetchUsers = useCallback(async () => {
    if (!orgId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/v1/users?organization_id=${encodeURIComponent(orgId)}`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        setUsers(await res.json());
      } else if (res.status === 401 || res.status === 403) {
        setUsers([]);
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Not authorized to view organization members.');
      }
    } catch {
      setError('Failed to load organization members.');
    } finally {
      setLoading(false);
    }
  }, [orgId, authHeaders]);

  const fetchInvites = useCallback(async () => {
    if (!orgId) return;
    try {
      const res = await fetch(`/v1/organizations/${encodeURIComponent(orgId)}/invites`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        setInvites(await res.json());
      } else {
        setInvites([]);
      }
    } catch {
      setInvites([]);
    }
  }, [orgId, authHeaders]);

  const fetchActivities = useCallback(async () => {
    if (!orgId) return;
    try {
      const base = `/v1/users/activity?organization_id=${encodeURIComponent(orgId)}&limit=50`;
      const url = activityFilter === 'all' ? base : `${base}&action_type=${encodeURIComponent(activityFilter)}`;
      const res = await fetch(url, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setActivities(data.activities || []);
        setActivityTotal(data.total || 0);
      } else {
        setActivities([]);
        setActivityTotal(0);
      }
    } catch {
      setActivities([]);
    }
  }, [orgId, activityFilter, authHeaders]);

  const fetchDomains = useCallback(async () => {
    if (!orgId) return;
    try {
      const res = await fetch(`/v1/users/domains?organization_id=${encodeURIComponent(orgId)}`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setDomainsData({
          domains: data.domains || [],
          summary: data.summary || {},
          is_preview: Boolean(data.is_preview),
        });
      }
    } catch {
      // Leave empty on error
    }
  }, [orgId, authHeaders]);

  useEffect(() => {
    fetchCapabilities();
    fetchUsers();
    fetchInvites();
    fetchDomains();
  }, [fetchCapabilities, fetchUsers, fetchInvites, fetchDomains]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const inviteMember = async ({ email, role }) => {
    const res = await fetch(`/v1/organizations/${encodeURIComponent(orgId)}/invites`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ email, role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to send invitation.');
    }
    const created = await res.json();
    await fetchInvites();
    showToast?.(`Invitation sent to ${created.email} (${created.role.toUpperCase()})`);
    return created;
  };

  const revokeInvite = async (inviteId) => {
    const res = await fetch(
      `/v1/organizations/${encodeURIComponent(orgId)}/invites/${encodeURIComponent(inviteId)}`,
      { method: 'DELETE', headers: authHeaders() }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to revoke invitation.');
    }
    await fetchInvites();
    showToast?.('Invitation revoked.');
  };

  const updateUserRole = async (userId, newRole, reason = '') => {
    const res = await fetch(`/v1/users/${encodeURIComponent(userId)}`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({ role: newRole, reason: reason || undefined }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update user role.');
    }
    const updated = await res.json();
    setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    await fetchActivities();
    showToast?.(`Updated role for ${updated.name} to ${String(updated.role).toUpperCase()}`);
    return updated;
  };

  const deactivateUser = async (userId, reason = '') => {
    const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    const res = await fetch(`/v1/users/${encodeURIComponent(userId)}${query}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (!res.ok && res.status !== 204) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to deactivate member.');
    }
    await fetchUsers();
    await fetchActivities();
    showToast?.('Member deactivated and active sessions revoked.');
  };

  return {
    authUser,
    users,
    invites,
    activities,
    activityTotal,
    domainsData,
    capabilities,
    roleCatalog,
    loading,
    error,
    refreshUsers: fetchUsers,
    refreshActivities: fetchActivities,
    inviteMember,
    revokeInvite,
    updateUserRole,
    deactivateUser,
  };
}
