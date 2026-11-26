import { useState, useEffect, useCallback } from 'react';

function getAuthHeaders() {
  const jwt = typeof localStorage !== 'undefined' ? localStorage.getItem('ctl_token') : null;
  return jwt ? { Authorization: `Bearer ${jwt}` } : {};
}

export function useLineageData({ organizationId, workspaceId, lens = 'risk', rootId = null, limit = 45 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [blastRadius, setBlastRadius] = useState(null);
  const [blastLoading, setBlastLoading] = useState(false);

  const fetchInvestigate = useCallback(async (cursor = null, append = false) => {
    if (!organizationId) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('mode', lens);
      params.set('limit', String(limit));
      if (workspaceId && workspaceId !== 'all') params.set('workspace_id', workspaceId);
      if (rootId) params.set('root_id', rootId);
      if (cursor) params.set('cursor', cursor);

      const res = await fetch(`/v1/lineage/investigate?${params.toString()}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const detailMsg = typeof errBody.detail === 'string'
          ? errBody.detail
          : errBody.detail
            ? JSON.stringify(errBody.detail)
            : `Lineage request failed (${res.status})`;
        throw new Error(detailMsg);
      }
      const payload = await res.json();
      if (append && data) {
        const existingIds = new Set((data.nodes || []).map((n) => n.id));
        const mergedNodes = [...(data.nodes || []), ...(payload.nodes || []).filter((n) => !existingIds.has(n.id))];
        const existingEdgeIds = new Set((data.edges || []).map((e) => e.id));
        const mergedEdges = [...(data.edges || []), ...(payload.edges || []).filter((e) => !existingEdgeIds.has(e.id))];
        setData({ ...payload, nodes: mergedNodes, edges: mergedEdges });
      } else {
        setData(payload);
      }
    } catch (e) {
      setError(e.message || 'Failed to load lineage');
    } finally {
      setLoading(false);
    }
  }, [organizationId, workspaceId, lens, rootId, limit]);

  useEffect(() => {
    fetchInvestigate(null, false);
  }, [fetchInvestigate]);

  const fetchBlastRadius = useCallback(async (claimId) => {
    if (!claimId) {
      setBlastRadius(null);
      return;
    }
    setBlastLoading(true);
    try {
      const cleanId = String(claimId).replace(/^cl_/, '');
      const wsParam = workspaceId && workspaceId !== 'all' ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
      const res = await fetch(`/v1/lineage/blast-radius/${cleanId}${wsParam}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setBlastRadius(await res.json());
      } else {
        setBlastRadius(null);
      }
    } catch {
      setBlastRadius(null);
    } finally {
      setBlastLoading(false);
    }
  }, [workspaceId]);

  return {
    data,
    loading,
    error,
    blastRadius,
    blastLoading,
    refresh: () => fetchInvestigate(null, false),
    loadMore: () => data?.next_cursor && fetchInvestigate(data.next_cursor, true),
    fetchBlastRadius,
  };
}
