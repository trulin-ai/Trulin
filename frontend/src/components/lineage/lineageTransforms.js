/**
 * Pure functions for Governed-Context Lineage filtering, path tracing,
 * search matching, and shareable URL state encoding.
 */

export function traceUpstream(nodeId, edges = []) {
  const visited = new Set([nodeId]);
  const edgeIds = new Set();
  const queue = [nodeId];
  while (queue.length > 0) {
    const curr = queue.shift();
    for (const e of edges) {
      if (e.target === curr) {
        edgeIds.add(e.id);
        if (!visited.has(e.source)) {
          visited.add(e.source);
          queue.push(e.source);
        }
      }
    }
  }
  return { nodeIds: visited, edgeIds };
}

export function traceDownstream(nodeId, edges = []) {
  const visited = new Set([nodeId]);
  const edgeIds = new Set();
  const queue = [nodeId];
  while (queue.length > 0) {
    const curr = queue.shift();
    for (const e of edges) {
      if (e.source === curr) {
        edgeIds.add(e.id);
        if (!visited.has(e.target)) {
          visited.add(e.target);
          queue.push(e.target);
        }
      }
    }
  }
  return { nodeIds: visited, edgeIds };
}

export function matchesSearch(node, rawQuery) {
  const q = (rawQuery || '').trim().toLowerCase();
  if (!q) return true;
  const haystacks = [
    node.id,
    node.label,
    node.fullText,
    node.subject,
    node.data?.claim_id,
    node.data?.audit_id,
    node.data?.doc_id,
    node.data?.evidence_snippet,
    node.subType,
    node.verdict,
    node.severity,
  ];
  return haystacks.some((val) => val && String(val).toLowerCase().includes(q));
}

export function getNodeStatusMeta(node) {
  if (node.type === 'conflict') {
    const resolved = String(node.status || '').toLowerCase() === 'resolved';
    return resolved
      ? { label: 'Resolved', tone: 'verified', color: '#166534', bg: '#DCFCE7', border: '#86EFAC' }
      : { label: 'Conflicted', tone: 'conflicted', color: '#9A3412', bg: '#FFEDD5', border: '#FDBA74' };
  }
  if (node.type === 'decision') {
    const v = String(node.verdict || 'ALLOW').toUpperCase();
    if (v === 'BLOCK') return { label: 'BLOCK', tone: 'rejected', color: '#991B1B', bg: '#FEE2E2', border: '#FCA5A5' };
    if (v === 'REQUIRE_REVIEW' || v === 'REVIEW') return { label: 'Review', tone: 'candidate', color: '#92400E', bg: '#FEF3C7', border: '#FCD34D' };
    return { label: v, tone: 'verified', color: '#166534', bg: '#DCFCE7', border: '#86EFAC' };
  }
  if (node.type === 'claim') {
    const st = String(node.status || '').toLowerCase();
    if (st === 'rejected' || st === 'quarantined') return { label: 'Rejected', tone: 'rejected', color: '#991B1B', bg: '#FEE2E2', border: '#FCA5A5' };
    if (node.is_canonical || st === 'verified' || st === 'active') return { label: 'Verified', tone: 'verified', color: '#166534', bg: '#DCFCE7', border: '#86EFAC' };
    if (st === 'stale' || st === 'outdated') return { label: 'Stale', tone: 'stale', color: '#78350F', bg: '#FEF3C7', border: '#FDE68A' };
    return { label: 'Candidate', tone: 'candidate', color: '#1E40AF', bg: '#DBEAFE', border: '#93C5FD' };
  }
  if (node.type === 'document') {
    return { label: node.subType || 'Policy', tone: 'neutral', color: '#334155', bg: '#F1F5F9', border: '#CBD5E1' };
  }
  return { label: node.subType || 'Source', tone: 'neutral', color: '#334155', bg: '#F1F5F9', border: '#CBD5E1' };
}

export function readLineageUrlParams() {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  return {
    lens: params.get('lens') || undefined,
    granularity: params.get('granularity') || undefined,
    nodeId: params.get('node') || undefined,
    view: params.get('view') || undefined,
    q: params.get('q') || undefined,
  };
}

export function writeLineageUrlParams({ lens, granularity, nodeId, view, q }) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  const setOrDel = (k, v) => {
    if (v) url.searchParams.set(k, v);
    else url.searchParams.delete(k);
  };
  setOrDel('lens', lens);
  setOrDel('granularity', granularity);
  setOrDel('node', nodeId);
  setOrDel('view', view);
  setOrDel('q', q);
  window.history.replaceState(window.history.state, '', url.toString());
}
