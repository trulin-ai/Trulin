import React, { useRef, useState } from 'react';
import { ZoomIn, ZoomOut } from 'lucide-react';
import LineageNodeCard from './LineageNodeCard';
import LineageEdge from './LineageEdge';

export default function LineageCanvas({
  nodes,
  edges,
  layout,
  positions,
  selectedNodeId,
  highlightedNodeIds,
  highlightedEdgeIds,
  onSelectNode,
  onExpandGroup,
  onNodePositionChange,
  zoom,
  pan,
  onZoomChange,
  onPanChange,
  totalUniverseNodes,
  rankingBasis,
  truncated,
  onLoadMore,
  loading,
}) {
  const containerRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [draggingNodeId, setDraggingNodeId] = useState(null);
  const dragStartRef = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const nodeDragRef = useRef(null);
  const didDragNodeRef = useRef(false);

  const effectivePositions = positions || layout.positions;
  const hasHighlight = highlightedNodeIds && highlightedNodeIds.size > 0;

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    setDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  };

  const handleNodeMouseDown = (node, pos, e) => {
    didDragNodeRef.current = false;
    setDraggingNodeId(node.id);
    nodeDragRef.current = {
      id: node.id,
      startX: e.clientX,
      startY: e.clientY,
      origX: pos.x,
      origY: pos.y,
    };
  };

  const handleMouseMove = (e) => {
    if (nodeDragRef.current) {
      const dx = (e.clientX - nodeDragRef.current.startX) / zoom;
      const dy = (e.clientY - nodeDragRef.current.startY) / zoom;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        didDragNodeRef.current = true;
      }
      onNodePositionChange?.(nodeDragRef.current.id, {
        x: Math.round(nodeDragRef.current.origX + dx),
        y: Math.round(nodeDragRef.current.origY + dy),
      });
      return;
    }
    if (!dragging) return;
    onPanChange({
      x: dragStartRef.current.panX + (e.clientX - dragStartRef.current.x),
      y: dragStartRef.current.panY + (e.clientY - dragStartRef.current.y),
    });
  };

  const handleMouseUp = () => {
    setDragging(false);
    setDraggingNodeId(null);
    nodeDragRef.current = null;
  };

  const handleWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.08 : 0.08;
      onZoomChange(Math.min(1.6, Math.max(0.4, Number((zoom + delta).toFixed(2)))));
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '12px',
        overflow: 'hidden',
        minHeight: '560px',
      }}
    >
      {/* Interactive Canvas Viewport */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onClick={() => {
          if (didDragNodeRef.current) {
            didDragNodeRef.current = false;
            return;
          }
          onSelectNode(null);
        }}
        style={{
          position: 'relative',
          flex: 1,
          minHeight: '510px',
          overflow: 'hidden',
          cursor: draggingNodeId || dragging ? 'grabbing' : 'grab',
          background: 'radial-gradient(#E2E8F0 1px, transparent 1px)',
          backgroundSize: '20px 20px',
          backgroundColor: '#FCFBF9',
        }}
      >
        {nodes.length === 0 && !loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748B', gap: '6px' }}>
            <strong style={{ fontSize: '0.92rem', color: '#0F172A' }}>No lineage entities match the current scope or filter</strong>
            <span style={{ fontSize: '0.78rem' }}>Upload documents or adjust your lens and search criteria.</span>
          </div>
        )}

        {/* Transformed Graph Layer */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: `${layout.canvasWidth}px`,
            height: `${layout.canvasHeight}px`,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
        >
          {/* Tier Column Headers */}
          {layout.columns.map((col) => (
            <div
              key={col.tier}
              style={{
                position: 'absolute',
                left: `${col.x}px`,
                top: '14px',
                fontSize: '0.68rem',
                fontWeight: 800,
                color: '#64748B',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              {col.label} ({col.count})
            </div>
          ))}

          {/* Semantic SVG Edges */}
          <svg
            width={layout.canvasWidth}
            height={layout.canvasHeight}
            style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
          >
            {edges.map((edge) => {
              const sPos = effectivePositions[edge.source];
              const tPos = effectivePositions[edge.target];
              const isHighlighted = highlightedEdgeIds?.has(edge.id);
              const isDimmed = hasHighlight && !isHighlighted;
              return (
                <LineageEdge
                  key={edge.id}
                  edge={edge}
                  sourcePos={sPos}
                  targetPos={tPos}
                  isHighlighted={isHighlighted}
                  isDimmed={isDimmed}
                />
              );
            })}
          </svg>

          {/* Node Cards */}
          {nodes.map((node) => {
            const pos = effectivePositions[node.id];
            if (!pos) return null;
            const isSelected = selectedNodeId === node.id;
            const isHighlighted = highlightedNodeIds?.has(node.id);
            const isDimmed = hasHighlight && !isHighlighted;
            return (
              <LineageNodeCard
                key={node.id}
                node={node}
                pos={pos}
                isSelected={isSelected}
                isHighlighted={isHighlighted}
                isDimmed={isDimmed}
                onNodeMouseDown={handleNodeMouseDown}
                onSelect={(n) => {
                  if (didDragNodeRef.current) {
                    didDragNodeRef.current = false;
                    return;
                  }
                  onSelectNode(n);
                }}
                onExpandGroup={(gid) => {
                  if (didDragNodeRef.current) {
                    didDragNodeRef.current = false;
                    return;
                  }
                  onExpandGroup(gid);
                }}
              />
            );
          })}
        </div>

        {/* Zoom Controls */}
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'absolute',
            bottom: '12px',
            right: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '4px',
            boxShadow: '0 2px 6px rgba(15,23,42,0.08)',
          }}
        >
          <button
            type="button"
            aria-label="Zoom out"
            onClick={() => onZoomChange(Math.max(0.4, Number((zoom - 0.1).toFixed(2))))}
            style={{ background: 'transparent', border: 'none', padding: '4px', cursor: 'pointer', display: 'flex' }}
          >
            <ZoomOut size={14} color="#334155" />
          </button>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#334155', minWidth: '38px', textAlign: 'center' }}>
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            aria-label="Zoom in"
            onClick={() => onZoomChange(Math.min(1.6, Number((zoom + 0.1).toFixed(2))))}
            style={{ background: 'transparent', border: 'none', padding: '4px', cursor: 'pointer', display: 'flex' }}
          >
            <ZoomIn size={14} color="#334155" />
          </button>
        </div>
      </div>

      {/* Persistent Truncation & Ranking Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          borderTop: '1px solid #E2E8F0',
          background: '#F8FAFC',
          fontSize: '0.73rem',
          color: '#475569',
        }}
      >
        <span>
          Showing <strong>{nodes.length}</strong> of <strong>{totalUniverseNodes}</strong> nodes
          {rankingBasis ? ` · Ranked by ${rankingBasis.replace(/_/g, ' ')}` : ''}
        </span>
        {truncated && onLoadMore && (
          <button
            type="button"
            onClick={onLoadMore}
            disabled={loading}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid #FED7AA',
              background: '#FFF7ED',
              color: '#C2410C',
              fontSize: '0.72rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {loading ? 'Loading...' : 'Expand more'}
          </button>
        )}
      </div>
    </div>
  );
}
