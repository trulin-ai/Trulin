import React, { useState } from 'react';
import {
  Activity,
  Download,
  RefreshCw,
  ShieldCheck,
  UserPlus,
  UserMinus,
  Trash2,
  GitCommitHorizontal,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

function formatTimeAgo(dateStr) {
  try {
    const diffSecs = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
    if (diffSecs < 60) return 'Just now';
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
    if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
    return `${Math.floor(diffSecs / 86400)}d ago`;
  } catch {
    return dateStr;
  }
}

function humanizeAction(actionType) {
  return String(actionType || 'EVENT')
    .toLowerCase()
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ''))
    .join(' ');
}

function getInitials(name) {
  if (!name) return 'S';
  return String(name)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || '')
    .join('') || 'S';
}

function getActionTheme(actionType) {
  const t = String(actionType || '').toUpperCase();
  if (t.includes('PURGE') || t.includes('DEACTIVAT') || t.includes('REMOVE') || t.includes('DELETE')) {
    return { bg: '#FEF2F2', color: '#B91C1C', border: '#FECACA', iconBg: '#FEE2E2', Icon: Trash2 };
  }
  if (t.includes('INVITE') || t.includes('MEMBER')) {
    return { bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE', iconBg: '#DBEAFE', Icon: UserPlus };
  }
  if (t.includes('ROLE') || t.includes('STATUS')) {
    return { bg: '#FFFBEB', color: '#B45309', border: '#FDE68A', iconBg: '#FEF3C7', Icon: UserMinus };
  }
  if (t.includes('CONFLICT') || t.includes('RESOLV')) {
    return { bg: '#F5F3FF', color: '#6D28D9', border: '#DDD6FE', iconBg: '#EDE9FE', Icon: GitCommitHorizontal };
  }
  if (t.includes('SYNC') || t.includes('SETUP') || t.includes('CREATE')) {
    return { bg: '#ECFDF5', color: '#047857', border: '#A7F3D0', iconBg: '#D1FAE5', Icon: ShieldCheck };
  }
  return { bg: '#F8FAFC', color: '#334155', border: '#E2E8F0', iconBg: '#F1F5F9', Icon: Activity };
}

function formatDetailValue(val) {
  if (val === null || val === undefined) return '—';
  if (Array.isArray(val)) return val.length ? val.join(', ') : 'none';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}

const FILTERS = [
  { id: 'all', label: 'All Events' },
  { id: 'SOURCE_SYNCED', label: 'Synced' },
  { id: 'CONFLICT_RESOLVED', label: 'Conflicts' },
  { id: 'MEMBER_INVITED', label: 'Invites' },
  { id: 'ROLE_UPDATED', label: 'Roles' },
  { id: 'MEMBER_DEACTIVATED', label: 'Deactivations' },
];

export default function GovernanceActivityFeed({
  activities,
  activityFilter,
  onFilterChange,
  onRefresh,
  canViewActivity,
  canExportActivity,
}) {
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  if (!canViewActivity) {
    return (
      <div
        className="card"
        style={{
          padding: '32px',
          textAlign: 'center',
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          color: '#64748B',
          fontSize: '0.85rem',
        }}
      >
        You do not have audit permission (`decisions:audit`) to view organization governance activity.
      </div>
    );
  }

  const toggleDetails = (id) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(activities, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trulin-governance-activity-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Top Filter & Actions Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          padding: '10px 14px',
        }}
      >
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
          {FILTERS.map((f) => {
            const active = activityFilter === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => onFilterChange(f.id)}
                style={{
                  padding: '5px 11px',
                  borderRadius: '999px',
                  border: active ? '1px solid #EA580C' : '1px solid #E2E8F0',
                  background: active ? '#FFF7ED' : '#F8FAFC',
                  color: active ? '#C2410C' : '#475569',
                  fontSize: '0.73rem',
                  fontWeight: active ? 700 : 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {f.label}
              </button>
            );
          })}
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {canExportActivity && activities.length > 0 && (
            <button
              type="button"
              onClick={handleExport}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '5px 10px',
                borderRadius: '7px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#334155',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <Download size={13} />
              <span>Export JSON</span>
            </button>
          )}
          <button
            type="button"
            onClick={onRefresh}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 10px',
              borderRadius: '7px',
              border: '1px solid #E2E8F0',
              background: '#FFFFFF',
              color: '#334155',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Timeline Ledger */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '0.84rem', fontWeight: 800, color: '#0F172A' }}>
            Activity Timeline
          </span>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              color: '#475569',
              background: '#F1F5F9',
              padding: '2px 9px',
              borderRadius: '999px',
            }}
          >
            {activities.length} {activities.length === 1 ? 'event' : 'events'}
          </span>
        </div>

        {activities.length === 0 ? (
          <div style={{ padding: '44px 20px', textAlign: 'center', color: '#64748B' }}>
            <Activity size={24} color="#94A3B8" style={{ marginBottom: '8px' }} />
            <div style={{ fontWeight: 700, color: '#0F172A', fontSize: '0.9rem' }}>No audit events recorded</div>
            <div style={{ fontSize: '0.78rem', marginTop: '4px' }}>
              Authorized team and governance actions will appear here automatically.
            </div>
          </div>
        ) : (
          <div style={{ padding: '8px 18px' }}>
            {activities.map((act, idx) => {
              const theme = getActionTheme(act.action_type);
              const IconComp = theme.Icon;
              const isLast = idx === activities.length - 1;
              const detailEntries = act.details ? Object.entries(act.details) : [];
              const isRawOpen = expandedIds.has(act.id);

              return (
                <div
                  key={act.id}
                  style={{
                    display: 'flex',
                    gap: '14px',
                    padding: '14px 4px',
                    borderBottom: isLast ? 'none' : '1px solid #F1F5F9',
                    transition: 'background 0.15s ease',
                  }}
                >
                  {/* Timeline Icon & Connector */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '2px' }}>
                    <div
                      style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '50%',
                        background: theme.iconBg,
                        color: theme.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <IconComp size={14} />
                    </div>
                    {!isLast && (
                      <div style={{ width: '1.5px', flex: 1, background: '#E2E8F0', marginTop: '6px' }} />
                    )}
                  </div>

                  {/* Event Body */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span
                        aria-hidden="true"
                        style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: '#EEF2FF',
                          color: '#3730A3',
                          fontSize: '0.62rem',
                          fontWeight: 800,
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {getInitials(act.user_name)}
                      </span>
                      <span style={{ fontWeight: 700, color: '#0F172A', fontSize: '0.84rem' }}>
                        {act.user_name}
                      </span>
                      <span
                        style={{
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          padding: '1px 7px',
                          borderRadius: '999px',
                          background: '#F1F5F9',
                          color: '#475569',
                          textTransform: 'uppercase',
                        }}
                      >
                        {act.user_role || 'system'}
                      </span>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          background: theme.bg,
                          color: theme.color,
                          border: `1px solid ${theme.border}`,
                        }}
                      >
                        {humanizeAction(act.action_type)}
                      </span>
                      <span
                        title={act.created_at ? new Date(act.created_at).toLocaleString() : ''}
                        style={{ fontSize: '0.73rem', color: '#64748B', marginLeft: 'auto', fontWeight: 500 }}
                      >
                        {formatTimeAgo(act.created_at)}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.8rem', color: '#334155', marginTop: '6px', lineHeight: 1.45 }}>
                      <strong style={{ color: '#0F172A' }}>{act.target_title || act.target_id || 'Resource'}</strong>
                      <span style={{ color: '#64748B' }}> · {act.target_type}</span>
                      {act.domain && (
                        <span
                          style={{
                            marginLeft: '8px',
                            fontSize: '0.66rem',
                            fontWeight: 700,
                            padding: '1px 7px',
                            borderRadius: '6px',
                            background: '#F8FAFC',
                            border: '1px solid #E2E8F0',
                            color: '#475569',
                          }}
                        >
                          {act.domain}
                        </span>
                      )}
                    </div>

                    {/* Structured Metadata Chips + Raw Toggle */}
                    {detailEntries.length > 0 && (
                      <div style={{ marginTop: '8px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                          {detailEntries.map(([k, v]) => (
                            <span
                              key={k}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '2px 8px',
                                borderRadius: '6px',
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                fontSize: '0.71rem',
                                color: '#475569',
                              }}
                            >
                              <span style={{ color: '#64748B', fontWeight: 600 }}>{k.replace(/_/g, ' ')}:</span>
                              <strong style={{ color: '#0F172A', fontWeight: 600 }}>{formatDetailValue(v)}</strong>
                            </span>
                          ))}
                          <button
                            type="button"
                            onClick={() => toggleDetails(act.id)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '2px',
                              background: 'none',
                              border: 'none',
                              color: '#64748B',
                              fontSize: '0.7rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              padding: '2px 4px',
                            }}
                          >
                            {isRawOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                            <span>JSON</span>
                          </button>
                        </div>

                        {isRawOpen && (
                          <pre
                            style={{
                              margin: '6px 0 0 0',
                              padding: '8px 10px',
                              background: '#0F172A',
                              color: '#E2E8F0',
                              borderRadius: '8px',
                              fontSize: '0.72rem',
                              overflowX: 'auto',
                            }}
                          >
                            {JSON.stringify(act.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
