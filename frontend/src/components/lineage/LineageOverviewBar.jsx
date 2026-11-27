import React, { useState, useRef, useEffect } from 'react';
import { Bookmark, AlertTriangle, ShieldCheck, Layers, ChevronDown } from 'lucide-react';

export default function LineageOverviewBar({
  summary,
  rankingBasis,
  activeLens,
  onSelectSavedView,
}) {
  const [openMenu, setOpenMenu] = useState(null); // 'saved' | 'legend' | null
  const containerRef = useRef(null);

  const counts = summary?.node_counts || {};
  const risks = summary?.risk_counts || {};

  const savedViews = [
    { id: 'risk', label: 'Highest-risk conflicts', desc: 'Unresolved contradictions & dependencies' },
    { id: 'impact', label: 'Source-to-decision impact', desc: 'Downstream consumer blast radius' },
    { id: 'evidence', label: 'Evidence provenance', desc: 'Claims grounded in document spans' },
  ];

  useEffect(() => {
    if (!openMenu) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openMenu]);

  const unresolvedCount = risks.unresolved_conflicts ?? 0;

  return (
    <div
      ref={containerRef}
      aria-label="Lineage overview and legend"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        padding: '7px 12px',
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
        position: 'relative',
      }}
    >
      {/* Left: Inline Entity Counts + Risk Summary */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.67rem',
              fontWeight: 800,
              color: '#64748B',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              marginRight: '2px',
            }}
          >
            <Layers size={12} />
            <span>Counts</span>
          </span>
          {[
            ['Sources', counts.sources ?? 0],
            ['Docs', counts.documents ?? 0],
            ['Claims', counts.claims ?? 0],
            ['Conflicts', counts.conflicts ?? 0],
            ['Decisions', counts.decisions ?? 0],
          ].map(([label, val]) => (
            <span
              key={label}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '2px 8px',
                borderRadius: '999px',
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                fontSize: '0.72rem',
                color: '#475569',
                fontWeight: 600,
              }}
            >
              <span>{label}</span>
              <strong style={{ color: '#0F172A', fontWeight: 800 }}>{val}</strong>
            </span>
          ))}
        </div>

        <div style={{ width: '1px', height: '16px', background: '#E2E8F0' }} />

        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px', fontSize: '0.72rem', color: '#475569' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <AlertTriangle size={12} color={unresolvedCount > 0 ? '#EA580C' : '#64748B'} />
            <span>Unresolved:</span>
            <strong style={{ color: unresolvedCount > 0 ? '#C2410C' : '#166534' }}>
              {unresolvedCount}
            </strong>
          </span>
          <span>
            Non-canonical: <strong style={{ color: '#0F172A' }}>{risks.review_required_claims ?? 0}</strong>
          </span>
          <span>
            Inferred edges: <strong style={{ color: '#0F172A' }}>{risks.inferred_edges ?? 0}</strong>
          </span>
        </div>
      </div>

      {/* Right: Saved Views & Edge Legend Popovers */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            onClick={() => setOpenMenu((m) => (m === 'saved' ? null : 'saved'))}
            aria-expanded={openMenu === 'saved'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 9px',
              borderRadius: '7px',
              border: openMenu === 'saved' ? '1px solid #FDBA74' : '1px solid #E2E8F0',
              background: openMenu === 'saved' ? '#FFF7ED' : '#F8FAFC',
              color: openMenu === 'saved' ? '#C2410C' : '#334155',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Bookmark size={12} />
            <span>Saved Views</span>
            <ChevronDown size={12} />
          </button>

          {openMenu === 'saved' && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                width: '250px',
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                boxShadow: '0 10px 25px rgba(15, 23, 42, 0.12)',
                padding: '8px',
                zIndex: 40,
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              {savedViews.map((sv) => {
                const active = activeLens === sv.id;
                return (
                  <button
                    key={sv.id}
                    type="button"
                    onClick={() => {
                      onSelectSavedView(sv.id);
                      setOpenMenu(null);
                    }}
                    style={{
                      textAlign: 'left',
                      padding: '7px 9px',
                      borderRadius: '7px',
                      border: active ? '1px solid #FED7AA' : '1px solid transparent',
                      background: active ? '#FFF7ED' : '#F8FAFC',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: active ? '#C2410C' : '#0F172A' }}>{sv.label}</div>
                    <div style={{ fontSize: '0.67rem', color: '#64748B' }}>{sv.desc}</div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ position: 'relative' }}>
          <button
            type="button"
            onClick={() => setOpenMenu((m) => (m === 'legend' ? null : 'legend'))}
            aria-expanded={openMenu === 'legend'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 9px',
              borderRadius: '7px',
              border: openMenu === 'legend' ? '1px solid #93C5FD' : '1px solid #E2E8F0',
              background: openMenu === 'legend' ? '#EFF6FF' : '#F8FAFC',
              color: openMenu === 'legend' ? '#1D4ED8' : '#334155',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <ShieldCheck size={12} />
            <span>Legend</span>
            <ChevronDown size={12} />
          </button>

          {openMenu === 'legend' && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                width: '215px',
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                boxShadow: '0 10px 25px rgba(15, 23, 42, 0.12)',
                padding: '10px 12px',
                zIndex: 40,
                display: 'flex',
                flexDirection: 'column',
                gap: '7px',
                fontSize: '0.72rem',
                color: '#475569',
              }}
            >
              <div style={{ fontSize: '0.66rem', fontWeight: 800, color: '#64748B', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Edge Semantics
              </div>
              {[
                ['Provenance', '#94A3B8', 'solid'],
                ['Extraction (evidence)', '#2563EB', 'solid'],
                ['Decision dependency', '#0D9488', 'solid'],
                ['Conflict', '#EA580C', 'dashed'],
                ['Inferred (legacy)', '#64748B', 'dotted'],
              ].map(([label, color, style]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '22px', borderTop: `2px ${style} ${color}`, display: 'inline-block', flexShrink: 0 }} />
                  <span>{label}</span>
                </div>
              ))}
              {rankingBasis && (
                <div style={{ marginTop: '4px', paddingTop: '6px', borderTop: '1px solid #F1F5F9', fontSize: '0.66rem', color: '#94A3B8' }}>
                  Ranking: {rankingBasis.replace(/_/g, ' ')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
