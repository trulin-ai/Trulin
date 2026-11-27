import React, { useState, useMemo, useEffect } from 'react';
import { useLineageData } from './useLineageData';
import { applySiblingGrouping, computeTieredLayout } from './lineageLayout';
import {
  matchesSearch,
  traceUpstream,
  traceDownstream,
  readLineageUrlParams,
  writeLineageUrlParams,
} from './lineageTransforms';
import LineageToolbar from './LineageToolbar';
import LineageOverviewBar from './LineageOverviewBar';
import LineageCanvas from './LineageCanvas';
import LineageInspector from './LineageInspector';
import LineageTableView from './LineageTableView';

export default function LineageExplorer({
  organizationId,
  workspaceId,
  workspaceName,
  onOpenDocument,
}) {
  const initialUrl = useMemo(() => readLineageUrlParams(), []);
  const [lens, setLens] = useState(initialUrl.lens || 'risk');
  const [granularity, setGranularity] = useState(initialUrl.granularity || 'claim');
  const [viewMode, setViewMode] = useState(initialUrl.view || 'canvas');
  const [searchQuery, setSearchQuery] = useState(initialUrl.q || '');
  const [selectedNodeId, setSelectedNodeId] = useState(initialUrl.nodeId || null);
  const [expandedGroups, setExpandedGroups] = useState(() => new Set());
  const [traceState, setTraceState] = useState(null); // { mode: 'upstream'|'downstream', nodeIds, edgeIds }
  const [zoom, setZoom] = useState(0.9);
  const [pan, setPan] = useState({ x: 16, y: 12 });
  const [nodeOverrides, setNodeOverrides] = useState({});

  const {
    data,
    loading,
    error,
    blastRadius,
    blastLoading,
    refresh,
    loadMore,
    fetchBlastRadius,
  } = useLineageData({ organizationId, workspaceId, lens });

  useEffect(() => {
    writeLineageUrlParams({
      lens,
      granularity,
      nodeId: selectedNodeId,
      view: viewMode,
      q: searchQuery,
    });
  }, [lens, granularity, selectedNodeId, viewMode, searchQuery]);

  const rawNodes = data?.nodes || [];
  const rawEdges = data?.edges || [];

  const filteredBySearch = useMemo(() => {
    const matched = rawNodes.filter((n) => matchesSearch(n, searchQuery));
    if (granularity === 'document') {
      return matched.filter((n) => n.type !== 'claim');
    }
    return matched;
  }, [rawNodes, searchQuery, granularity]);

  const grouped = useMemo(() => {
    if (granularity === 'document') {
      const idSet = new Set(filteredBySearch.map((n) => n.id));
      return {
        nodes: filteredBySearch,
        edges: rawEdges.filter((e) => idSet.has(e.source) && idSet.has(e.target)),
      };
    }
    return applySiblingGrouping(filteredBySearch, rawEdges, expandedGroups);
  }, [filteredBySearch, rawEdges, granularity, expandedGroups]);

  const layout = useMemo(
    () => computeTieredLayout(grouped.nodes, granularity),
    [grouped.nodes, granularity]
  );

  const effectivePositions = useMemo(
    () => ({ ...layout.positions, ...nodeOverrides }),
    [layout.positions, nodeOverrides]
  );

  const selectedNode = useMemo(
    () => grouped.nodes.find((n) => n.id === selectedNodeId) || null,
    [grouped.nodes, selectedNodeId]
  );

  const handleSelectNode = (node) => {
    if (!node) {
      setSelectedNodeId(null);
      setTraceState(null);
      fetchBlastRadius(null);
      return;
    }
    setSelectedNodeId(node.id);
    if (node.type === 'claim' && !node.isGroupNode) {
      fetchBlastRadius(node.data?.claim_id || node.id);
    } else {
      fetchBlastRadius(null);
    }
  };

  const handleTraceUpstream = (nid) => {
    const res = traceUpstream(nid, grouped.edges);
    setTraceState({ mode: 'upstream', ...res });
  };

  const handleTraceDownstream = (nid) => {
    const res = traceDownstream(nid, grouped.edges);
    setTraceState({ mode: 'downstream', ...res });
  };

  const handleFitView = () => {
    setZoom(0.9);
    setPan({ x: 16, y: 12 });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      <LineageToolbar
        lens={lens}
        onLensChange={(next) => {
          setLens(next);
          setTraceState(null);
        }}
        granularity={granularity}
        onGranularityChange={setGranularity}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onFitView={handleFitView}
        onRefresh={refresh}
        loading={loading}
        scopeLabel={workspaceName || 'All Workspaces'}
      />

      {error && (
        <div style={{ padding: '10px 14px', borderRadius: '8px', background: '#FEF2F2', border: '1px solid #FECACA', color: '#991B1B', fontSize: '0.8rem', fontWeight: 600 }}>
          {error}
        </div>
      )}

      <LineageOverviewBar
        summary={data?.summary}
        rankingBasis={data?.ranking_basis}
        activeLens={lens}
        onSelectSavedView={(id) => {
          setLens(id);
          setTraceState(null);
        }}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 280px',
          gap: '14px',
          alignItems: 'start',
        }}
      >

        {viewMode === 'table' ? (
          <LineageTableView
            nodes={grouped.nodes}
            edges={grouped.edges}
            selectedNodeId={selectedNodeId}
            onSelectNode={handleSelectNode}
          />
        ) : (
          <LineageCanvas
            nodes={grouped.nodes}
            edges={grouped.edges}
            layout={layout}
            positions={effectivePositions}
            selectedNodeId={selectedNodeId}
            highlightedNodeIds={traceState?.nodeIds}
            highlightedEdgeIds={traceState?.edgeIds}
            onSelectNode={handleSelectNode}
            onNodePositionChange={(nodeId, pos) => {
              setNodeOverrides((prev) => ({ ...prev, [nodeId]: pos }));
            }}
            onExpandGroup={(gid) => {
              setExpandedGroups((prev) => {
                const next = new Set(prev);
                next.add(gid);
                return next;
              });
            }}
            zoom={zoom}
            pan={pan}
            onZoomChange={setZoom}
            onPanChange={setPan}
            totalUniverseNodes={data?.summary?.total_universe_nodes ?? grouped.nodes.length}
            rankingBasis={data?.ranking_basis}
            truncated={Boolean(data?.truncated)}
            onLoadMore={loadMore}
            loading={loading}
          />
        )}

        <LineageInspector
          node={selectedNode}
          edges={grouped.edges}
          blastRadius={blastRadius}
          blastLoading={blastLoading}
          onTraceUpstream={handleTraceUpstream}
          onTraceDownstream={handleTraceDownstream}
          onClearTrace={() => setTraceState(null)}
          activeTraceMode={traceState?.mode || null}
          onOpenDocument={onOpenDocument}
        />
      </div>
    </div>
  );
}
