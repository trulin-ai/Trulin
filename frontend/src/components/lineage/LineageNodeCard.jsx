import React from 'react';
import { Database, FileText, ShieldCheck, AlertTriangle, Bot, Layers } from 'lucide-react';
import { CARD_WIDTH, CARD_HEIGHT } from './lineageLayout';
import { getNodeStatusMeta } from './lineageTransforms';

const TYPE_ICONS = {
  source: Database,
  document: FileText,
  claim: ShieldCheck,
  conflict: AlertTriangle,
  decision: Bot,
};

export default function LineageNodeCard({
  node,
  pos,
  isSelected,
  isHighlighted,
  isDimmed,
  onSelect,
  onExpandGroup,
  onNodeMouseDown,
}) {
  const Icon = node.isGroupNode ? Layers : (TYPE_ICONS[node.type] || ShieldCheck);
  const statusMeta = getNodeStatusMeta(node);

  const secondaryLine = (() => {
    if (node.isGroupNode) return 'Click to expand sibling claims';
    if (node.type === 'source') return `${node.subType || 'Connector'} · ${node.status || 'active'}`;
    if (node.type === 'document') return `${node.subType || 'policy'} · v${node.data?.version_count || 1}`;
    if (node.type === 'claim') return `${statusMeta.label} · ${Math.round((node.trustScore || 0.9) * 100)}% trust`;
    if (node.type === 'conflict') return `${String(node.severity || 'high').toUpperCase()} · ${node.status || 'detected'}`;
    if (node.type === 'decision') return `${node.verdict || 'ALLOW'} · ${node.actor || 'agent'}`;
    return '';
  })();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (node.isGroupNode) onExpandGroup?.(node.id);
      else onSelect?.(node);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${node.type}: ${node.label}. Status: ${statusMeta.label}`}
      aria-pressed={isSelected}
      onMouseDown={(e) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        onNodeMouseDown?.(node, pos, e);
      }}
      onClick={(e) => {
        e.stopPropagation();
        if (node.isGroupNode) onExpandGroup?.(node.id);
        else onSelect?.(node);
      }}
      onKeyDown={handleKeyDown}
      style={{
        position: 'absolute',
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        width: `${CARD_WIDTH}px`,
        height: `${CARD_HEIGHT}px`,
        boxSizing: 'border-box',
        background: node.isGroupNode ? '#FFF7ED' : '#FFFFFF',
        border: isSelected
          ? '2px solid #EA580C'
          : isHighlighted
            ? '1.5px solid #2563EB'
            : node.isGroupNode
              ? '1px dashed #F97316'
              : '1px solid #E2E8F0',
        borderRadius: '10px',
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        cursor: 'grab',
        userSelect: 'none',
        opacity: isDimmed ? 0.35 : 1,
        boxShadow: isSelected ? '0 4px 12px rgba(234, 88, 12, 0.16)' : '0 1px 3px rgba(15, 23, 42, 0.04)',
        outline: 'none',
        transition: 'border-color 0.15s ease, opacity 0.15s ease',
      }}
    >
      {/* Top row: Icon + Type + Status Pill */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.65rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          <Icon size={12} color={isSelected ? '#EA580C' : '#475569'} />
          <span>{node.isGroupNode ? 'Group' : node.type}</span>
        </div>

        {!node.isGroupNode && (
          <span
            style={{
              fontSize: '0.62rem',
              fontWeight: 700,
              color: statusMeta.color,
              background: statusMeta.bg,
              border: `1px solid ${statusMeta.border}`,
              padding: '1px 6px',
              borderRadius: '999px',
              whiteSpace: 'nowrap',
            }}
          >
            {statusMeta.label}
          </span>
        )}
      </div>

      {/* Primary label */}
      <div
        title={node.fullText || node.label}
        style={{
          fontSize: '0.78rem',
          fontWeight: 700,
          color: '#0F172A',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {node.label}
      </div>

      {/* Secondary contextual line */}
      <div
        style={{
          fontSize: '0.68rem',
          color: '#64748B',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {secondaryLine}
      </div>
    </div>
  );
}
