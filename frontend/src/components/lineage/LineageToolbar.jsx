import React from 'react';
import {
  GitBranch,
  ShieldCheck,
  AlertTriangle,
  Search,
  Table2,
  Network,
  RefreshCw,
  Maximize2,
  X
} from 'lucide-react';

export default function LineageToolbar({
  lens,
  onLensChange,
  granularity,
  onGranularityChange,
  viewMode,
  onViewModeChange,
  searchQuery,
  onSearchChange,
  onFitView,
  onRefresh,
  loading,
  scopeLabel,
}) {
  const lenses = [
    { id: 'risk', label: 'Risk & conflicts', icon: <AlertTriangle size={13} />, title: 'What needs review? Conflicts and unverified dependencies' },
    { id: 'impact', label: 'Impact', icon: <GitBranch size={13} />, title: 'What depends on this source or document?' },
    { id: 'evidence', label: 'Evidence trace', icon: <ShieldCheck size={13} />, title: 'Why does this answer or claim exist?' },
  ];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        padding: '10px 14px',
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
      }}
    >
      {/* Investigation Lenses */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <div
          role="tablist"
          aria-label="Investigation lenses"
          style={{
            display: 'flex',
            background: '#F1F5F9',
            padding: '3px',
            borderRadius: '8px',
            gap: '2px',
          }}
        >
          {lenses.map((item) => {
            const active = lens === item.id;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={active}
                title={item.title}
                onClick={() => onLensChange(item.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 11px',
                  borderRadius: '6px',
                  border: 'none',
                  background: active ? '#FFFFFF' : 'transparent',
                  color: active ? '#0F172A' : '#475569',
                  fontWeight: active ? 700 : 600,
                  fontSize: '0.76rem',
                  cursor: 'pointer',
                  boxShadow: active ? '0 1px 2px rgba(15,23,42,0.08)' : 'none',
                }}
              >
                <span style={{ color: active ? '#EA580C' : '#64748B', display: 'inline-flex' }}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Secondary Granularity Control */}
        <div
          style={{
            display: 'inline-flex',
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '7px',
            padding: '2px',
          }}
        >
          {['document', 'claim'].map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => onGranularityChange(g)}
              style={{
                padding: '4px 9px',
                borderRadius: '5px',
                border: 'none',
                background: granularity === g ? '#0F172A' : 'transparent',
                color: granularity === g ? '#FFFFFF' : '#475569',
                fontSize: '0.72rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Right Controls: Search, Canvas/Table Toggle, Fit, Refresh */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative' }}>
          <Search size={13} color="#94A3B8" style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            aria-label="Search lineage entities"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search doc, claim, ID, audit..."
            style={{
              padding: '5px 26px 5px 28px',
              borderRadius: '7px',
              border: '1px solid #E2E8F0',
              background: '#F8FAFC',
              color: '#0F172A',
              fontSize: '0.76rem',
              width: '215px',
              outline: 'none',
            }}
          />
          {searchQuery && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => onSearchChange('')}
              style={{ position: 'absolute', right: '7px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
            >
              <X size={12} color="#64748B" />
            </button>
          )}
        </div>

        <div style={{ display: 'inline-flex', background: '#F1F5F9', padding: '2px', borderRadius: '7px' }}>
          <button
            type="button"
            onClick={() => onViewModeChange('canvas')}
            aria-pressed={viewMode === 'canvas'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 9px',
              borderRadius: '5px',
              border: 'none',
              background: viewMode === 'canvas' ? '#FFFFFF' : 'transparent',
              color: viewMode === 'canvas' ? '#0F172A' : '#64748B',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Network size={12} />
            <span>Canvas</span>
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange('table')}
            aria-pressed={viewMode === 'table'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 9px',
              borderRadius: '5px',
              border: 'none',
              background: viewMode === 'table' ? '#FFFFFF' : 'transparent',
              color: viewMode === 'table' ? '#0F172A' : '#64748B',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Table2 size={12} />
            <span>Table</span>
          </button>
        </div>

        {viewMode === 'canvas' && (
          <button
            type="button"
            onClick={onFitView}
            title="Fit graph to view"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '5px 9px',
              borderRadius: '7px',
              border: '1px solid #E2E8F0',
              background: '#FFFFFF',
              color: '#334155',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Maximize2 size={12} />
            <span>Fit</span>
          </button>
        )}

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          title="Refresh lineage"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '5px 9px',
            borderRadius: '7px',
            border: '1px solid #E2E8F0',
            background: '#FFFFFF',
            color: '#334155',
            fontSize: '0.72rem',
            fontWeight: 600,
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          <RefreshCw size={12} />
        </button>
      </div>
    </div>
  );
}
