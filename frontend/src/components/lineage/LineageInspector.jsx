import React, { useState } from 'react';
import { ArrowUpLeft, ArrowDownRight, ChevronDown, ChevronRight, ExternalLink, AlertTriangle } from 'lucide-react';
import { getNodeStatusMeta } from './lineageTransforms';

export default function LineageInspector({
  node,
  edges,
  blastRadius,
  blastLoading,
  onTraceUpstream,
  onTraceDownstream,
  onClearTrace,
  activeTraceMode,
  onOpenDocument,
}) {
  const [showTechnical, setShowTechnical] = useState(false);

  if (!node) {
    return (
      <aside
        aria-label="Node inspector"
        style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          padding: '18px 16px',
          color: '#64748B',
          fontSize: '0.78rem',
          lineHeight: 1.55,
        }}
      >
        <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
          Inspector
        </div>
        Select any node on the canvas or table to inspect its evidence span, certification gates, upstream sources, and downstream agent impact.
      </aside>
    );
  }

  const statusMeta = getNodeStatusMeta(node);
  const upstreamCount = edges.filter((e) => e.target === node.id).length;
  const downstreamCount = edges.filter((e) => e.source === node.id).length;
  const evidenceSnippet = node.data?.evidence_snippet;
  const docId = node.data?.doc_id || node.document_id;

  return (
    <aside
      aria-label="Node inspector"
      style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
      }}
    >
      {/* Identity & Status */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.66rem', fontWeight: 800, color: '#EA580C', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {node.type}
          </span>
          <span
            style={{
              fontSize: '0.66rem',
              fontWeight: 700,
              color: statusMeta.color,
              background: statusMeta.bg,
              border: `1px solid ${statusMeta.border}`,
              padding: '2px 8px',
              borderRadius: '999px',
            }}
          >
            {statusMeta.label}
          </span>
        </div>
        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0F172A', lineHeight: 1.4 }}>
          {node.fullText || node.label}
        </div>
        {node.data?.scope && (
          <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '4px' }}>
            Scope: <strong>{node.data.scope}</strong>
          </div>
        )}
      </div>

      {/* Path Tracing Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid #F1F5F9', paddingTop: '12px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
          <button
            type="button"
            onClick={() => onTraceUpstream(node.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              padding: '6px 8px',
              borderRadius: '7px',
              border: activeTraceMode === 'upstream' ? '1px solid #EA580C' : '1px solid #E2E8F0',
              background: activeTraceMode === 'upstream' ? '#FFF7ED' : '#F8FAFC',
              color: activeTraceMode === 'upstream' ? '#C2410C' : '#334155',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <ArrowUpLeft size={13} />
            <span>Trace upstream ({upstreamCount})</span>
          </button>
          <button
            type="button"
            onClick={() => onTraceDownstream(node.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              padding: '6px 8px',
              borderRadius: '7px',
              border: activeTraceMode === 'downstream' ? '1px solid #2563EB' : '1px solid #E2E8F0',
              background: activeTraceMode === 'downstream' ? '#EFF6FF' : '#F8FAFC',
              color: activeTraceMode === 'downstream' ? '#1D4ED8' : '#334155',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <ArrowDownRight size={13} />
            <span>Downstream ({downstreamCount})</span>
          </button>
        </div>
        {activeTraceMode && (
          <button
            type="button"
            onClick={onClearTrace}
            style={{ background: 'transparent', border: 'none', color: '#64748B', fontSize: '0.71rem', cursor: 'pointer', textAlign: 'left', padding: 0 }}
          >
            Clear path highlight
          </button>
        )}
      </div>

      {/* Evidence Excerpt */}
      {evidenceSnippet && (
        <div style={{ borderTop: '1px solid #F1F5F9', paddingTop: '12px' }}>
          <div style={{ fontSize: '0.66rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
            Evidence Excerpt {node.data?.evidence_section ? `· ${node.data.evidence_section}` : ''}
          </div>
          <blockquote style={{ margin: 0, padding: '8px 10px', background: '#F8FAFC', borderLeft: '3px solid #2563EB', borderRadius: '0 6px 6px 0', fontSize: '0.75rem', color: '#334155', lineHeight: 1.5 }}>
            “{evidenceSnippet}”
          </blockquote>
        </div>
      )}

      {/* Blast Radius / Conflicts / Agent Usage for Claims */}
      {node.type === 'claim' && (
        <div style={{ borderTop: '1px solid #F1F5F9', paddingTop: '12px' }}>
          <div style={{ fontSize: '0.66rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
            Impact & Conflicts
          </div>
          {blastLoading ? (
            <div style={{ fontSize: '0.74rem', color: '#64748B' }}>Computing blast radius...</div>
          ) : blastRadius ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.74rem', color: '#334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Connected conflicts</span>
                <strong>{blastRadius.connected_conflicts_count ?? 0}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Impacted AI decisions</span>
                <strong>{blastRadius.impacted_decisions_count ?? 0}</strong>
              </div>
              {blastRadius.conflicting_claims?.map((c) => (
                <div key={c.claim_id} style={{ background: '#FFF7ED', border: '1px solid #FED7AA', borderRadius: '6px', padding: '6px 8px', fontSize: '0.71rem', color: '#9A3412', display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                  <AlertTriangle size={12} style={{ marginTop: '2px', flexShrink: 0 }} />
                  <span>{c.text}</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.74rem', color: '#64748B' }}>No downstream impact data.</div>
          )}
        </div>
      )}

      {/* Open Source Document */}
      {docId && onOpenDocument && (
        <button
          type="button"
          onClick={() => onOpenDocument(docId)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '7px 10px',
            borderRadius: '8px',
            border: '1px solid #CBD5E1',
            background: '#FFFFFF',
            color: '#0F172A',
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <span>Open Source Document</span>
          <ExternalLink size={13} />
        </button>
      )}

      {/* Expandable Technical Details */}
      <div style={{ borderTop: '1px solid #F1F5F9', paddingTop: '10px' }}>
        <button
          type="button"
          onClick={() => setShowTechnical((v) => !v)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'transparent',
            border: 'none',
            padding: 0,
            fontSize: '0.72rem',
            fontWeight: 700,
            color: '#475569',
            cursor: 'pointer',
          }}
        >
          <span>Technical IDs & Metadata</span>
          {showTechnical ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        {showTechnical && (
          <pre style={{ marginTop: '8px', background: '#0F172A', color: '#E2E8F0', padding: '10px', borderRadius: '8px', fontSize: '0.68rem', overflowX: 'auto', maxHeight: '200px' }}>
            {JSON.stringify({ id: node.id, type: node.type, status: node.status, data: node.data }, null, 2)}
          </pre>
        )}
      </div>
    </aside>
  );
}
