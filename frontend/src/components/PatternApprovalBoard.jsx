import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Search,
  Filter,
  FileText,
  RefreshCw,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Check,
  X,
  Layers,
  Inbox,
  UserCheck,
  Clock,
  Undo2,
  CheckSquare,
  Square,
  Eye,
  ShieldAlert,
  ArrowRight,
  ShieldCheck,
  HelpCircle
} from 'lucide-react';

export default function PatternApprovalBoard({
  activeOrg,
  token,
  user,
  showToast,
  selectedDocFilter = 'all',
  documents = [],
  onReviewSuccess
}) {
  const [data, setData] = useState({ patterns: [], summary: null });
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [revertLoading, setRevertLoading] = useState(false);
  const [lastBatchReversible, setLastBatchReversible] = useState(null);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'safe' | 'held'
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Outlier Drawer State
  const [inspectingPattern, setInspectingPattern] = useState(null);
  const [drawerClaims, setDrawerClaims] = useState([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerSelectedIds, setDrawerSelectedIds] = useState(new Set());
  const [drawerActionLoading, setDrawerActionLoading] = useState(false);

  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';

  // 1. Fetch Patterns and Clustering Data
  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let url = `/v1/review/patterns?organization_id=${orgId}`;
      if (selectedDocFilter && selectedDocFilter !== 'all') {
        url += `&document_id=${selectedDocFilter}`;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast?.(err.detail || 'Failed to load pattern clusters', 'error');
      }
    } catch (err) {
      console.error('Error fetching claim patterns:', err);
      showToast?.('Network error loading pattern board', 'error');
    } finally {
      setLoading(false);
    }
  }, [orgId, token, selectedDocFilter, showToast]);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  // Unique categories list
  const categories = useMemo(() => {
    const set = new Set();
    (data.patterns || []).forEach(p => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set).sort();
  }, [data.patterns]);

  // Filtered patterns
  const filteredPatterns = useMemo(() => {
    return (data.patterns || []).filter(p => {
      // Status filter
      if (statusFilter === 'safe' && !p.is_safe) return false;
      if (statusFilter === 'held' && p.is_safe) return false;

      // Category filter
      if (categoryFilter !== 'all' && p.category !== categoryFilter) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const nameMatch = (p.pattern_name || '').toLowerCase().includes(q);
        const catMatch = (p.category || '').toLowerCase().includes(q);
        const predMatch = (p.canonical_predicate || '').toLowerCase().includes(q);
        const quoteMatch = (p.representative_claim?.claim_text || '').toLowerCase().includes(q);
        if (!nameMatch && !catMatch && !predMatch && !quoteMatch) return false;
      }

      return true;
    });
  }, [data.patterns, statusFilter, categoryFilter, searchQuery]);

  // 2. Execute Batch Action on a Pattern
  const handleBatchPatternAction = async (pattern, action, explicitClaimIds = null) => {
    if (!pattern) return;
    setActionLoadingId(pattern.pattern_id);

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const payload = {
        action,
        reviewer_id: user?.id || null,
        reviewer_notes: `Batch ${action.toUpperCase()} on pattern: ${pattern.pattern_name}`,
        selected_claim_ids: explicitClaimIds
      };

      const res = await fetch(`/v1/review/patterns/${pattern.pattern_id}/action?organization_id=${orgId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const result = await res.json();
        showToast?.(
          action === 'approve'
            ? `✓ Batch certified ${result.modified_count} claims for "${pattern.pattern_name}"!`
            : action === 'reject'
            ? `✓ Rejected ${result.modified_count} claims from baseline.`
            : `Pattern action "${action}" completed.`,
          action === 'reject' ? 'warning' : 'success'
        );

        if (action === 'approve' || action === 'reject') {
          setLastBatchReversible({
            batch_id: result.batch_id,
            pattern_name: pattern.pattern_name,
            count: result.modified_count,
            action
          });
        }

        // Close drawer if open
        setInspectingPattern(null);

        // Refresh pattern list and tell parent to update metrics
        await fetchPatterns();
        onReviewSuccess?.();
      } else {
        const err = await res.json().catch(() => ({}));
        showToast?.(err.detail || 'Failed to execute pattern action', 'error');
      }
    } catch (err) {
      console.error('Error applying batch pattern action:', err);
      showToast?.('Network error applying batch action', 'error');
    } finally {
      setActionLoadingId(null);
    }
  };

  // 3. Revert Last Batch Transaction
  const handleRevertLastBatch = async () => {
    if (!lastBatchReversible) return;
    setRevertLoading(true);

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/v1/review/patterns/batch_revert', {
        method: 'POST',
        headers,
        body: JSON.stringify({ batch_id: lastBatchReversible.batch_id })
      });

      if (res.ok) {
        showToast?.(`✓ Reverted batch: restored ${lastBatchReversible.count} claims to candidate status.`, 'info');
        setLastBatchReversible(null);
        await fetchPatterns();
        onReviewSuccess?.();
      } else {
        const err = await res.json().catch(() => ({}));
        showToast?.(err.detail || 'Failed to revert batch', 'error');
      }
    } catch (err) {
      console.error('Error reverting batch:', err);
      showToast?.('Network error reverting batch', 'error');
    } finally {
      setRevertLoading(false);
    }
  };

  // 4. Open Outlier Inspection Drawer
  const handleInspectOutliers = async (pattern) => {
    setInspectingPattern(pattern);
    setDrawerLoading(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let url = `/v1/review/patterns/${pattern.pattern_id}/claims?organization_id=${orgId}`;
      if (selectedDocFilter && selectedDocFilter !== 'all') {
        url += `&document_id=${selectedDocFilter}`;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const claims = await res.json();
        setDrawerClaims(claims);
        // Pre-select all by default for high-confidence items
        const initialSelected = new Set(claims.map(c => c.id));
        setDrawerSelectedIds(initialSelected);
      } else {
        showToast?.('Failed to load member claims for inspection', 'error');
      }
    } catch (err) {
      console.error('Failed to load pattern claims:', err);
      showToast?.('Error loading claims', 'error');
    } finally {
      setDrawerLoading(false);
    }
  };

  // Toggle individual claim in drawer
  const toggleDrawerClaim = (claimId) => {
    setDrawerSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(claimId)) next.delete(claimId);
      else next.add(claimId);
      return next;
    });
  };

  // Select / Deselect All in drawer
  const toggleSelectAllDrawer = () => {
    if (drawerSelectedIds.size === drawerClaims.length) {
      setDrawerSelectedIds(new Set());
    } else {
      setDrawerSelectedIds(new Set(drawerClaims.map(c => c.id)));
    }
  };

  // Submit Selected Claims from Drawer
  const handleApproveDrawerSelected = async () => {
    if (drawerSelectedIds.size === 0) {
      showToast?.('Please select at least one claim to approve.', 'info');
      return;
    }
    setDrawerActionLoading(true);
    await handleBatchPatternAction(inspectingPattern, 'approve', Array.from(drawerSelectedIds));
    setDrawerActionLoading(false);
  };

  const summary = data.summary;
  const safeCount = summary?.safe_batch_claims_count ?? 0;
  const heldCount = summary?.held_claims_count ?? 0;
  const totalCount = summary?.total_candidates ?? 0;
  const percentClearedOrReady = totalCount > 0 ? Math.round((safeCount / totalCount) * 100) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      
      {/* ── TRIAGE BURN-DOWN HERO BANNER ── */}
      <div style={{
        background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)',
        borderRadius: '10px',
        padding: '16px 20px',
        color: '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: '0 4px 12px rgba(15, 23, 42, 0.12)'
      }}>
        {/* Top Line: Title & Fast-Track Target */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(217, 119, 6, 0.35)'
            }}>
              <Zap size={18} style={{ color: '#FFFFFF' }} />
            </div>
            <div>
              <div style={{ fontSize: '1.02rem', fontWeight: 800, letterSpacing: '-0.01em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>10-Minute Extreme Batch Adjudication</span>
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  padding: '2px 7px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  color: '#FCD34D',
                  borderRadius: '12px',
                  border: '1px solid rgba(245, 158, 11, 0.4)'
                }}>
                  Fail-Closed HITL
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '1px' }}>
                Approve high-confidence policy patterns across repeated clauses • Generic verbs held for review
              </div>
            </div>
          </div>

          {/* Quick Metrics & Revert Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {lastBatchReversible && (
              <button
                type="button"
                disabled={revertLoading}
                onClick={handleRevertLastBatch}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 11px',
                  borderRadius: '6px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  color: '#FCA5A5',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  cursor: revertLoading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s ease'
                }}
                title="Undo the last batch approval/rejection"
              >
                <Undo2 size={13} className={revertLoading ? 'spin' : ''} />
                <span>Undo Last Batch ({lastBatchReversible.count} claims)</span>
              </button>
            )}

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.08)',
              padding: '5px 10px',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.12)'
            }}>
              <Clock size={14} style={{ color: '#FBBF24' }} />
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#E2E8F0' }}>
                Est. Time: <strong style={{ color: '#FCD34D' }}>~{summary?.estimated_review_time_mins ?? 8.8} mins</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Multi-Segment Burn-down Bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <div style={{
            height: '8px',
            width: '100%',
            background: 'rgba(255, 255, 255, 0.12)',
            borderRadius: '4px',
            overflow: 'hidden',
            display: 'flex'
          }}>
            {/* Ready for Batch (Green) */}
            <div
              style={{
                width: `${percentClearedOrReady}%`,
                background: 'linear-gradient(90deg, #10B981, #059669)',
                transition: 'width 0.4s ease'
              }}
              title={`${safeCount} claims ready for 1-click batch certification`}
            />
            {/* Intentionally Held (Slate/Orange) */}
            <div
              style={{
                width: `${100 - percentClearedOrReady}%`,
                background: 'rgba(245, 158, 11, 0.5)',
                transition: 'width 0.4s ease'
              }}
              title={`${heldCount} claims held for focused individual review`}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem', color: '#CBD5E1' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }}></span>
                <strong style={{ color: '#FFFFFF' }}>{safeCount.toLocaleString()} claims</strong> ready for batch approval ({summary?.safe_patterns_count ?? 0} patterns)
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#F59E0B' }}></span>
                <strong style={{ color: '#FDE68A' }}>{heldCount.toLocaleString()} claims</strong> held for safety ({summary?.held_patterns_count ?? 0} generic/edge patterns)
              </span>
            </div>
            <div>
              Total Queue: <strong style={{ color: '#FFFFFF' }}>{totalCount.toLocaleString()} candidates</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ── TOOLBAR: FILTER & SEARCH PATTERNS ── */}
      <div style={{
        background: '#FAF8F5',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        {/* Left: Status Filter Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginRight: '4px' }}>
            Filter:
          </span>
          <div style={{ display: 'inline-flex', background: '#E2E8F0', padding: '2px', borderRadius: '6px', gap: '2px' }}>
            {[
              { id: 'all', label: `All Patterns (${data.patterns?.length ?? 0})` },
              { id: 'safe', label: `⚡ Ready to Batch (${summary?.safe_patterns_count ?? 0})` },
              { id: 'held', label: `⏸ Intentionally Held (${summary?.held_patterns_count ?? 0})` }
            ].map(p => {
              const active = statusFilter === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setStatusFilter(p.id)}
                  style={{
                    padding: '3px 9px',
                    fontSize: '0.72rem',
                    fontWeight: active ? 700 : 500,
                    borderRadius: '4px',
                    border: 'none',
                    background: active ? '#FFFFFF' : 'transparent',
                    color: active ? '#0F172A' : '#64748B',
                    cursor: 'pointer',
                    boxShadow: active ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* Category Dropdown */}
          <select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            style={{
              height: '28px',
              padding: '0 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              color: '#334155',
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '5px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="all">All Categories ({categories.length})</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        {/* Right: Search Box & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '220px', maxWidth: '380px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={13} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search pattern, rule, or quote..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                height: '28px',
                padding: '2px 8px 2px 28px',
                fontSize: '0.74rem',
                border: '1px solid #CBD5E1',
                borderRadius: '5px',
                background: '#FFFFFF',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: 0 }}
              >
                <X size={12} />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={fetchPatterns}
            disabled={loading}
            style={{
              height: '28px',
              padding: '0 8px',
              fontSize: '0.72rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '5px',
              cursor: loading ? 'not-allowed' : 'pointer',
              color: '#475569',
              fontWeight: 600
            }}
            title="Refresh patterns"
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* ── PATTERN CARDS / ROWS LIST ── */}
      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: '#64748B', background: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 12px auto', color: '#D97706' }} />
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#1E293B' }}>Clustering candidate claims into policy patterns...</div>
          <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '4px' }}>Evaluating domain deontic modalities and canonical predicates</div>
        </div>
      ) : filteredPatterns.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748B', background: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
          <CheckCircle2 size={32} style={{ margin: '0 auto 10px auto', color: '#16A34A' }} />
          <div style={{ fontSize: '0.90rem', fontWeight: 700, color: '#1E293B' }}>All matching patterns resolved!</div>
          <div style={{ fontSize: '0.76rem', color: '#64748B', marginTop: '4px' }}>No candidate claims remain in this filter view.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredPatterns.map((pat, idx) => {
            const isActing = actionLoadingId === pat.pattern_id;
            const isSafe = pat.is_safe;

            return (
              <div
                key={pat.pattern_id}
                style={{
                  background: '#FFFFFF',
                  borderRadius: '8px',
                  border: isSafe ? '1px solid #E2E8F0' : '1px solid #FED7AA',
                  padding: '14px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
                  transition: 'border-color 0.15s ease',
                  borderLeft: isSafe ? '4px solid #10B981' : '4px solid #F59E0B'
                }}
              >
                {/* Header Strip */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '1px 6px',
                        background: '#F1F5F9',
                        color: '#475569',
                        borderRadius: '4px'
                      }}>
                        {pat.category}
                      </span>

                      <span style={{ fontSize: '0.94rem', fontWeight: 700, color: '#0F172A' }}>
                        {pat.pattern_name}
                      </span>

                      <span style={{
                        fontSize: '0.70rem',
                        fontWeight: 800,
                        padding: '2px 8px',
                        background: isSafe ? '#DCFCE7' : '#FEF3C7',
                        color: isSafe ? '#166534' : '#92400E',
                        borderRadius: '12px',
                        border: isSafe ? '1px solid #BBF7D0' : '1px solid #FDE68A'
                      }}>
                        {pat.claim_count} claims
                      </span>
                    </div>

                    <div style={{ fontSize: '0.72rem', color: '#64748B', display: 'flex', alignItems: 'center', gap: '10px', marginTop: '1px' }}>
                      <span>{pat.document_distribution}</span>
                      <span>•</span>
                      <span>Confidence: <strong style={{ color: isSafe ? '#15803D' : '#B45309' }}>{pat.confidence}</strong></span>
                      {pat.canonical_predicate && (
                        <>
                          <span>•</span>
                          <span>Canonical: <code style={{ background: '#F8FAFC', padding: '1px 4px', borderRadius: '3px', border: '1px solid #E2E8F0', color: '#0284C7' }}>{pat.canonical_predicate}</code></span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Pre-selection status */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: isSafe ? '#059669' : '#D97706',
                      background: isSafe ? '#ECFDF5' : '#FFFBEB',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <CheckCircle2 size={12} />
                      <span>{pat.claim_count} / {pat.claim_count} pre-selected</span>
                    </span>
                  </div>
                </div>

                {/* Representative Verbatim Quote */}
                {pat.representative_claim?.claim_text && (
                  <div style={{
                    background: '#FAF8F5',
                    border: '1px solid #EBE5DF',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '0.77rem',
                    color: '#334155',
                    fontStyle: 'italic',
                    lineHeight: 1.45,
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '6px'
                  }}>
                    <span style={{ color: '#94A3B8', fontWeight: 800, fontSize: '0.85rem' }}>“</span>
                    <span style={{ flex: 1 }}>{pat.representative_claim.claim_text}</span>
                    <span style={{ color: '#94A3B8', fontWeight: 800, fontSize: '0.85rem' }}>”</span>
                  </div>
                )}

                {/* Bottom Actions Row */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingTop: '6px',
                  borderTop: '1px solid #F1F5F9',
                  flexWrap: 'wrap',
                  gap: '8px'
                }}>
                  {/* Left: Reason / Safety Note */}
                  <div style={{ fontSize: '0.72rem', color: isSafe ? '#475569' : '#B45309', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    {isSafe ? (
                      <>
                        <ShieldCheck size={13} style={{ color: '#10B981' }} />
                        <span>{pat.reason}</span>
                      </>
                    ) : (
                      <>
                        <ShieldAlert size={13} style={{ color: '#F59E0B' }} />
                        <span><strong>Fail-closed:</strong> {pat.reason}</span>
                      </>
                    )}
                  </div>

                  {/* Right: Action Buttons */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {/* Outliers Drawer Trigger */}
                    <button
                      type="button"
                      disabled={isActing}
                      onClick={() => handleInspectOutliers(pat)}
                      style={{
                        padding: '4px 9px',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        background: '#FFFFFF',
                        border: '1px solid #CBD5E1',
                        borderRadius: '5px',
                        color: '#475569',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title="Inspect all individual claims in this cluster and uncheck outliers"
                    >
                      <Eye size={12} />
                      <span>Inspect Outliers ({pat.claim_count})</span>
                    </button>

                    {isSafe ? (
                      <>
                        {/* Reject Pattern */}
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() => handleBatchPatternAction(pat, 'reject')}
                          style={{
                            padding: '4px 9px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            background: '#FFF5F5',
                            border: '1px solid #FECACA',
                            borderRadius: '5px',
                            color: '#DC2626',
                            cursor: isActing ? 'not-allowed' : 'pointer'
                          }}
                          title="Reject all claims in this cluster from policy baseline"
                        >
                          ✕ Reject Pattern
                        </button>

                        {/* Approve Pattern (Primary) */}
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() => handleBatchPatternAction(pat, 'approve')}
                          style={{
                            padding: '5px 12px',
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            background: '#16A34A',
                            border: '1px solid #15803D',
                            borderRadius: '5px',
                            color: '#FFFFFF',
                            cursor: isActing ? 'not-allowed' : 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            boxShadow: '0 1px 2px rgba(22, 163, 74, 0.25)'
                          }}
                        >
                          <Check size={13} className={isActing ? 'spin' : ''} />
                          <span>{isActing ? 'Certifying...' : `✓ Approve Pattern (${pat.claim_count})`}</span>
                        </button>
                      </>
                    ) : (
                      <>
                        {/* Escalate button for held patterns */}
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() => handleBatchPatternAction(pat, 'escalate')}
                          style={{
                            padding: '4px 9px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            background: '#FEF3C7',
                            border: '1px solid #FDE68A',
                            borderRadius: '5px',
                            color: '#92400E',
                            cursor: isActing ? 'not-allowed' : 'pointer'
                          }}
                          title="Escalate this ambiguous pattern to senior compliance review"
                        >
                          ⚡ Escalate to Legal
                        </button>

                        {/* Inspect & Review Button */}
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() => handleInspectOutliers(pat)}
                          style={{
                            padding: '5px 12px',
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            background: '#0F172A',
                            border: '1px solid #0F172A',
                            borderRadius: '5px',
                            color: '#FFFFFF',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <span>Review Items ({pat.claim_count})</span>
                          <ChevronRight size={13} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── OUTLIER INSPECTION SLIDE-OVER FLYOUT DRAWER ── */}
      {inspectingPattern && (
        <div style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          left: 0,
          background: 'rgba(15, 23, 42, 0.45)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'flex-end',
          animation: 'fadeIn 0.15s ease'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '560px',
            height: '100%',
            background: '#FFFFFF',
            boxShadow: '-4px 0 20px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            animation: 'slideInRight 0.2s ease'
          }}>
            {/* Drawer Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid #E2E8F0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#F8FAFC'
            }}>
              <div>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                  {inspectingPattern.category} • Cluster Inspection
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                  {inspectingPattern.pattern_name}
                </div>
                {inspectingPattern.canonical_predicate && (
                  <div style={{ fontSize: '0.72rem', color: '#0284C7', marginTop: '2px' }}>
                    Target Predicate: <code>{inspectingPattern.canonical_predicate}</code>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => setInspectingPattern(null)}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  background: '#FFFFFF',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#64748B'
                }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Instruction Banner */}
            <div style={{
              padding: '10px 18px',
              background: inspectingPattern.is_safe ? '#F0FDF4' : '#FFFBEB',
              borderBottom: '1px solid #E2E8F0',
              fontSize: '0.74rem',
              color: inspectingPattern.is_safe ? '#166534' : '#92400E',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <HelpCircle size={14} />
                <span>Uncheck any non-conforming outliers before batch certifying.</span>
              </div>
              <button
                type="button"
                onClick={toggleSelectAllDrawer}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: inspectingPattern.is_safe ? '#15803D' : '#B45309',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                {drawerSelectedIds.size === drawerClaims.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>

            {/* Selection Counter Bar */}
            <div style={{
              padding: '8px 20px',
              borderBottom: '1px solid #F1F5F9',
              fontSize: '0.74rem',
              fontWeight: 600,
              color: '#475569',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span>Selected: <strong style={{ color: '#0F172A' }}>{drawerSelectedIds.size} of {drawerClaims.length} claims</strong></span>
              <span style={{ fontSize: '0.70rem', color: '#94A3B8' }}>{inspectingPattern.document_distribution}</span>
            </div>

            {/* Claims Checklist Scroll View */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {drawerLoading ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>
                  <RefreshCw size={20} className="spin" style={{ margin: '0 auto 8px auto' }} />
                  <div>Loading cluster members...</div>
                </div>
              ) : drawerClaims.length === 0 ? (
                <div style={{ padding: '30px', textAlign: 'center', color: '#94A3B8' }}>
                  No candidate claims found in this cluster.
                </div>
              ) : (
                drawerClaims.map((claim, cIdx) => {
                  const isChecked = drawerSelectedIds.has(claim.id);
                  return (
                    <div
                      key={claim.id}
                      onClick={() => toggleDrawerClaim(claim.id)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        border: isChecked ? '1px solid #93C5FD' : '1px solid #E2E8F0',
                        background: isChecked ? '#EFF6FF' : '#FFFFFF',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '10px',
                        transition: 'all 0.12s ease'
                      }}
                    >
                      <div style={{ marginTop: '2px', color: isChecked ? '#2563EB' : '#94A3B8' }}>
                        {isChecked ? <CheckSquare size={16} /> : <Square size={16} />}
                      </div>

                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ fontSize: '0.76rem', color: '#1E293B', lineHeight: 1.45 }}>
                          "{claim.claim_text}"
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.68rem', color: '#64748B' }}>
                          <span style={{ fontWeight: 600, color: '#0284C7' }}>{claim.document_title || 'Document'}</span>
                          <span>•</span>
                          <span>Subj: <strong>{claim.subject || 'unspecified'}</strong></span>
                          <span>•</span>
                          <span>Pred: <code>{claim.predicate}</code></span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom Drawer Action Footer */}
            <div style={{
              padding: '14px 20px',
              borderTop: '1px solid #E2E8F0',
              background: '#F8FAFC',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <button
                type="button"
                onClick={() => setInspectingPattern(null)}
                style={{
                  padding: '7px 14px',
                  fontSize: '0.76rem',
                  fontWeight: 600,
                  background: '#FFFFFF',
                  border: '1px solid #CBD5E1',
                  borderRadius: '6px',
                  color: '#475569',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  disabled={drawerActionLoading || drawerSelectedIds.size === 0}
                  onClick={() => handleBatchPatternAction(inspectingPattern, 'reject', Array.from(drawerSelectedIds))}
                  style={{
                    padding: '7px 12px',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    background: '#FFF5F5',
                    border: '1px solid #FECACA',
                    borderRadius: '6px',
                    color: '#DC2626',
                    cursor: drawerActionLoading || drawerSelectedIds.size === 0 ? 'not-allowed' : 'pointer'
                  }}
                >
                  ✕ Reject Selected ({drawerSelectedIds.size})
                </button>

                <button
                  type="button"
                  disabled={drawerActionLoading || drawerSelectedIds.size === 0}
                  onClick={handleApproveDrawerSelected}
                  style={{
                    padding: '7px 16px',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    background: '#16A34A',
                    border: '1px solid #15803D',
                    borderRadius: '6px',
                    color: '#FFFFFF',
                    cursor: drawerActionLoading || drawerSelectedIds.size === 0 ? 'not-allowed' : 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    boxShadow: '0 1px 3px rgba(22, 163, 74, 0.3)'
                  }}
                >
                  <Check size={14} className={drawerActionLoading ? 'spin' : ''} />
                  <span>{drawerActionLoading ? 'Certifying...' : `✓ Approve Selected (${drawerSelectedIds.size} Claims)`}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
