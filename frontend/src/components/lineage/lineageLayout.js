/**
 * Pure deterministic left-to-right tiered layout and sibling grouping
 * for the Governed-Context Lineage Explorer.
 */

export const TIER_ORDER = ['source', 'document', 'claim', 'conflict', 'decision'];

export const TIER_LABELS = {
  source: 'Sources',
  document: 'Documents',
  claim: 'Claims & Evidence',
  conflict: 'Conflicts',
  decision: 'AI Decisions',
};

export const CARD_WIDTH = 256;
export const CARD_HEIGHT = 86;
export const COL_GAP = 96;
export const ROW_GAP = 22;

/**
 * Groups excess sibling claims under the same parent document when
 * granularity === 'claim' and the group is not expanded.
 */
export function applySiblingGrouping(nodes, edges, expandedGroupIds = new Set(), maxPerDoc = 4) {
  const claimParentMap = new Map();
  for (const e of edges) {
    if (e.type === 'extraction' && String(e.target).startsWith('cl_')) {
      claimParentMap.set(e.target, e.source);
    }
  }

  const claimsByDoc = new Map();
  const nonClaimNodes = [];
  for (const n of nodes) {
    if (n.type === 'claim') {
      const parentId = claimParentMap.get(n.id) || 'unparented';
      if (!claimsByDoc.has(parentId)) claimsByDoc.set(parentId, []);
      claimsByDoc.get(parentId).push(n);
    } else {
      nonClaimNodes.push(n);
    }
  }

  const visibleClaims = [];
  const collapsedClaimToGroup = new Map();

  for (const [docId, docClaims] of claimsByDoc.entries()) {
    const groupId = `grp_${docId}`;
    if (docClaims.length <= maxPerDoc || expandedGroupIds.has(groupId)) {
      visibleClaims.push(...docClaims);
    } else {
      const head = docClaims.slice(0, maxPerDoc - 1);
      const hidden = docClaims.slice(maxPerDoc - 1);
      visibleClaims.push(...head);
      visibleClaims.push({
        id: groupId,
        type: 'claim',
        isGroupNode: true,
        groupParentDocId: docId,
        hiddenCount: hidden.length,
        label: `+${hidden.length} related claims`,
        status: 'grouped',
        data: { hiddenClaimIds: hidden.map((c) => c.id) },
      });
      for (const h of hidden) collapsedClaimToGroup.set(h.id, groupId);
    }
  }

  const finalNodes = [...nonClaimNodes, ...visibleClaims];
  const finalNodeIds = new Set(finalNodes.map((n) => n.id));

  const remappedEdges = [];
  const seenEdgePairs = new Set();
  for (const e of edges) {
    const src = collapsedClaimToGroup.get(e.source) || e.source;
    const tgt = collapsedClaimToGroup.get(e.target) || e.target;
    if (!finalNodeIds.has(src) || !finalNodeIds.has(tgt) || src === tgt) continue;
    const pairKey = `${src}->${tgt}:${e.type}`;
    if (seenEdgePairs.has(pairKey)) continue;
    seenEdgePairs.add(pairKey);
    remappedEdges.push({ ...e, source: src, target: tgt });
  }

  return { nodes: finalNodes, edges: remappedEdges };
}

/**
 * Computes deterministic left-to-right column positions for all visible nodes.
 */
export function computeTieredLayout(nodes, granularity = 'claim') {
  const activeTiers = TIER_ORDER.filter((tier) => {
    if (granularity === 'document' && tier === 'claim') return false;
    return nodes.some((n) => n.type === tier);
  });

  const positions = {};
  const columns = [];
  let maxBottom = 260;

  activeTiers.forEach((tier, colIdx) => {
    const tierNodes = nodes.filter((n) => n.type === tier);
    const x = 36 + colIdx * (CARD_WIDTH + COL_GAP);
    columns.push({ tier, label: TIER_LABELS[tier], x, count: tierNodes.length });

    tierNodes.forEach((n, rowIdx) => {
      const y = 52 + rowIdx * (CARD_HEIGHT + ROW_GAP);
      positions[n.id] = { x, y };
      maxBottom = Math.max(maxBottom, y + CARD_HEIGHT + 40);
    });
  });

  const canvasWidth = Math.max(820, 36 + activeTiers.length * (CARD_WIDTH + COL_GAP));
  const canvasHeight = maxBottom;
  return { positions, columns, canvasWidth, canvasHeight };
}
