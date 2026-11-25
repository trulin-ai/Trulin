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
  HelpCircle,
  Ban
} from 'lucide-react';

export default function PatternApprovalBoard({
  activeOrg,
  token,
  user,
  showToast,
  selectedDocFilter = 'all',
  documents = [],
  searchQuery = '',
  categoryFilter = 'all',
  onCategoriesLoaded,
  onReviewSuccess
}) {
  const [data, setData] = useState({ patterns: [], summary: null });
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [revertLoading, setRevertLoading] = useState(false);
  const [lastBatchReversible, setLastBatchReversible] = useState(null);

  // Certified Rules state for Column 3
  const [certifiedRules, setCertifiedRules] = useState([]);
  const [certifiedLoading, setCertifiedLoading] = useState(false);

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

  // 2. Fetch Certified Rules for Column 3
  const fetchCertifiedRules = useCallback(async () => {
    setCertifiedLoading(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let url = `/v1/claims?organization_id=${orgId}&status=verified&limit=50`;
      const res = await fetch(url, { headers });
      if (res.ok) {
        const claims = await res.json();
        setCertifiedRules(Array.isArray(claims) ? claims : []);
      }
    } catch (err) {
      console.error('Error fetching certified claims:', err);
    } finally {
      setCertifiedLoading(false);
    }
  }, [orgId, token]);

  useEffect(() => {
    fetchPatterns();
    fetchCertifiedRules();
  }, [fetchPatterns, fetchCertifiedRules]);

  // Unique categories list
  const categories = useMemo(() => {
    const set = new Set();
    (data.patterns || []).forEach(p => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set).sort();
  }, [data.patterns]);

  // Notify parent of available categories
  useEffect(() => {
    if (onCategoriesLoaded && categories.length > 0) {
      onCategoriesLoaded(categories);
    }
  }, [categories, onCategoriesLoaded]);

  // Filtered patterns
  const filteredPatterns = useMemo(() => {
    return (data.patterns || []).filter(p => {
      // Category filter
      if (categoryFilter && categoryFilter !== 'all' && p.category !== categoryFilter) return false;

      // Search query
      if (searchQuery && searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const nameMatch = (p.pattern_name || '').toLowerCase().includes(q);
        const catMatch = (p.category || '').toLowerCase().includes(q);
        const predMatch = (p.canonical_predicate || '').toLowerCase().includes(q);
        const quoteMatch = (p.representative_claim?.claim_text || '').toLowerCase().includes(q);
        if (!nameMatch && !catMatch && !predMatch && !quoteMatch) return false;
      }

      return true;
    });
  }, [data.patterns, categoryFilter, searchQuery]);

  // Partition patterns into Safe vs Held
  const safePatterns = useMemo(() => filteredPatterns.filter(p => p.is_safe), [filteredPatterns]);
  const heldPatterns = useMemo(() => filteredPatterns.filter(p => !p.is_safe), [filteredPatterns]);

  // Filter certified rules for Column 3
  const filteredCertifiedRules = useMemo(() => {
    return certifiedRules.filter(r => {
      if (selectedDocFilter && selectedDocFilter !== 'all' && r.document_id !== selectedDocFilter) return false;
      if (searchQuery && searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const textMatch = (r.claim_text || '').toLowerCase().includes(q);
        const subjMatch = (r.subject || '').toLowerCase().includes(q);
        const predMatch = (r.predicate || '').toLowerCase().includes(q);
        const objMatch = (r.object || '').toLowerCase().includes(q);
        if (!textMatch && !subjMatch && !predMatch && !objMatch) return false;
      }
      return true;
    });
  }, [certifiedRules, selectedDocFilter, searchQuery]);

  // Execute Batch Action on a Pattern
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
        await fetchCertifiedRules();
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

  // Revert Last Batch Transaction
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
        await fetchCertifiedRules();
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

  // Open Outlier Inspection Drawer
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

  const docMap = useMemo(() => {
    const map = {};
    for (const d of documents) {
      map[d.id] = d.title || d.file_name || 'Document';
    }
    return map;
  }, [documents]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      
      {/* Undo Last Batch Alert Banner (if applicable) */}
      {lastBatchReversible && (
        <div style={{
          background: '#FFFBEB',
          border: '1px solid #FDE68A',
          borderRadius: '8px',
          padding: '8px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.78rem'
        }}>
          <div style={{ color: '#92400E', fontWeight: 600 }}>
            Batch action completed: <strong>{lastBatchReversible.count} claims</strong> for "{lastBatchReversible.pattern_name}".
          </div>
          <button
            type="button"
            disabled={revertLoading}
            onClick={handleRevertLastBatch}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              borderRadius: '6px',
              background: '#FFFFFF',
              border: '1px solid #F59E0B',
              color: '#B45309',
              fontSize: '0.74rem',
              fontWeight: 700,
              cursor: revertLoading ? 'not-allowed' : 'pointer'
            }}
          >
            <Undo2 size={13} className={revertLoading ? 'spin' : ''} />
            <span>Undo Batch</span>
          </button>
        </div>
      )}

      {/* ── 3-COLUMN KANBAN BOARD ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
        gap: '14px',
        alignItems: 'stretch'
      }}>
        
        {/* ========================================================= */}
        {/* COLUMN 1: Ready for Batch Approval                        */}
        {/* ========================================================= */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid #E8E3DC',
          background: '#FFFFFF',
          minHeight: '520px'
        }}>
          {/* Column Header */}
          <div style={{
            background: '#EFECE6',
            padding: '10px 14px',
            fontSize: '0.80rem',
            fontWeight: 700,
            color: '#292524',
            borderBottom: '1px solid #E8E3DC',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span>Ready for Batch Approval ({safePatterns.length})</span>
            {loading && <RefreshCw size={12} className="spin" style={{ color: '#78716C' }} />}
          </div>

          {/* Column Body */}
          <div style={{
            flex: 1,
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            justifyContent: safePatterns.length === 0 ? 'center' : 'flex-start',
            alignItems: safePatterns.length === 0 ? 'center' : 'stretch'
          }}>
            {safePatterns.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#94A3B8', padding: '40px 16px' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  border: '2px solid #CBD5E1',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 8px auto',
                  color: '#94A3B8'
                }}>
                  <Ban size={20} strokeWidth={1.75} />
                </div>
                <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#475569' }}>Empty</div>
                <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '2px' }}>0 items</div>
              </div>
            ) : (
              safePatterns.map(pat => {
                const isActing = actionLoadingId === pat.pattern_id;
                return (
                  <div
                    key={pat.pattern_id}
                    style={{
                      background: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      borderLeft: '4px solid #10B981',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                    }}
                  >
                    {/* Header Badges */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontSize: '0.64rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '1px 6px',
                        background: '#F1F5F9',
                        color: '#475569',
                        borderRadius: '4px'
                      }}>
                        {pat.category || 'POLICY'}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '1px 7px',
                          background: '#DCFCE7',
                          color: '#166534',
                          borderRadius: '10px'
                        }}>
                          {pat.claim_count} claims
                        </span>
                        <span style={{ fontSize: '0.68rem', color: '#15803D', fontWeight: 700 }}>
                          {pat.confidence}
                        </span>
                      </div>
                    </div>

                    {/* Pattern Name */}
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A', lineHeight: 1.3 }}>
                      {pat.pattern_name}
                    </div>

                    {/* Predicate */}
                    {pat.canonical_predicate && (
                      <div style={{ fontSize: '0.70rem', color: '#64748B' }}>
                        Predicate: <code style={{ background: '#F8FAFC', padding: '1px 5px', borderRadius: '3px', border: '1px solid #E2E8F0', color: '#0284C7' }}>{pat.canonical_predicate}</code>
                      </div>
                    )}

                    {/* Representative Claim Quote */}
                    {pat.representative_claim?.claim_text && (
                      <div style={{
                        fontSize: '0.72rem',
                        color: '#475569',
                        fontStyle: 'italic',
                        background: '#F8FAFC',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        lineHeight: 1.35
                      }}>
                        "{pat.representative_claim.claim_text.length > 90 ? pat.representative_claim.claim_text.substring(0, 90) + '...' : pat.representative_claim.claim_text}"
                      </div>
                    )}

                    {/* Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginTop: '4px' }}>
                      <button
                        type="button"
                        onClick={() => handleInspectOutliers(pat)}
                        style={{
                          padding: '4px 8px',
                          fontSize: '0.70rem',
                          fontWeight: 600,
                          background: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: '5px',
                          color: '#475569',
                          cursor: 'pointer'
                        }}
                      >
                        Inspect
                      </button>
                      <button
                        type="button"
                        disabled={isActing}
                        onClick={() => handleBatchPatternAction(pat, 'approve')}
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          background: '#10B981',
                          border: '1px solid #059669',
                          borderRadius: '5px',
                          color: '#FFFFFF',
                          cursor: isActing ? 'not-allowed' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Check size={12} className={isActing ? 'spin' : ''} />
                        <span>{isActing ? 'Certifying...' : '✓ Certify Batch'}</span>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ========================================================= */}
        {/* COLUMN 2: Held for Safety Review                          */}
        {/* ========================================================= */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid #E8E3DC',
          background: '#FFFFFF',
          minHeight: '520px'
        }}>
          {/* Column Header */}
          <div style={{
            background: '#EFECE6',
            padding: '10px 14px',
            fontSize: '0.80rem',
            fontWeight: 700,
            color: '#292524',
            borderBottom: '1px solid #E8E3DC',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span>Held for Safety Review ({heldPatterns.length})</span>
            {loading && <RefreshCw size={12} className="spin" style={{ color: '#78716C' }} />}
          </div>

          {/* Column Body */}
          <div style={{
            flex: 1,
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            justifyContent: heldPatterns.length === 0 ? 'center' : 'flex-start',
            alignItems: heldPatterns.length === 0 ? 'center' : 'stretch'
          }}>
            {heldPatterns.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#94A3B8', padding: '40px 16px' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  background: '#E2E8F0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 8px auto',
                  color: '#64748B'
                }}>
                  <Check size={20} strokeWidth={2.5} />
                </div>
                <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#475569' }}>Empty</div>
                <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '2px' }}>No items to display</div>
              </div>
            ) : (
              heldPatterns.map(pat => {
                const isActing = actionLoadingId === pat.pattern_id;
                return (
                  <div
                    key={pat.pattern_id}
                    style={{
                      background: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #FED7AA',
                      borderLeft: '4px solid #F59E0B',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                    }}
                  >
                    {/* Header Badges */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontSize: '0.64rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '1px 6px',
                        background: '#FEF3C7',
                        color: '#92400E',
                        borderRadius: '4px'
                      }}>
                        {pat.category || 'HELD'}
                      </span>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '1px 7px',
                        background: '#FEF3C7',
                        color: '#92400E',
                        borderRadius: '10px'
                      }}>
                        {pat.claim_count} claims
                      </span>
                    </div>

                    {/* Pattern Name */}
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#0F172A', lineHeight: 1.3 }}>
                      {pat.pattern_name}
                    </div>

                    {/* Hold Reason / Description */}
                    <div style={{ fontSize: '0.70rem', color: '#B45309', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <AlertTriangle size={12} />
                      <span>Individual human verification required for deontic scope</span>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginTop: '4px' }}>
                      <button
                        type="button"
                        disabled={isActing}
                        onClick={() => handleBatchPatternAction(pat, 'reject')}
                        style={{
                          padding: '4px 8px',
                          fontSize: '0.70rem',
                          fontWeight: 600,
                          background: '#FFF5F5',
                          border: '1px solid #FECACA',
                          borderRadius: '5px',
                          color: '#DC2626',
                          cursor: isActing ? 'not-allowed' : 'pointer'
                        }}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleInspectOutliers(pat)}
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.72rem',
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
                        <span>Inspect & Resolve</span>
                        <ChevronRight size={12} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ========================================================= */}
        {/* COLUMN 3: Certified Rules                                 */}
        {/* ========================================================= */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid #E8E3DC',
          background: '#FFFFFF',
          minHeight: '520px'
        }}>
          {/* Column Header */}
          <div style={{
            background: '#EFECE6',
            padding: '10px 14px',
            fontSize: '0.80rem',
            fontWeight: 700,
            color: '#292524',
            borderBottom: '1px solid #E8E3DC',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span>Certified Rules ({filteredCertifiedRules.length})</span>
            {certifiedLoading && <RefreshCw size={12} className="spin" style={{ color: '#78716C' }} />}
          </div>

          {/* Column Body */}
          <div style={{
            flex: 1,
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            justifyContent: filteredCertifiedRules.length === 0 ? 'center' : 'flex-start',
            alignItems: filteredCertifiedRules.length === 0 ? 'center' : 'stretch'
          }}>
            {filteredCertifiedRules.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#94A3B8', padding: '40px 16px' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  background: '#E2E8F0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 8px auto',
                  color: '#64748B'
                }}>
                  <Check size={20} strokeWidth={2.5} />
                </div>
                <div style={{ fontSize: '0.78rem', color: '#94A3B8', marginTop: '6px' }}>
                  No items to display
                </div>
              </div>
            ) : (
              filteredCertifiedRules.map(rule => (
                <div
                  key={rule.id}
                  style={{
                    background: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #DCFCE7',
                    borderLeft: '4px solid #16A34A',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                    <span style={{
                      fontSize: '0.64rem',
                      fontWeight: 700,
                      color: '#166534',
                      background: '#DCFCE7',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '3px'
                    }}>
                      <CheckCircle2 size={10} /> Certified Rule
                    </span>
                    <span style={{ fontSize: '0.68rem', color: '#64748B' }}>
                      {docMap[rule.document_id] || 'Policy Document'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.80rem', fontWeight: 600, color: '#0F172A', lineHeight: 1.4 }}>
                    {rule.subject ? (
                      <div>
                        <strong>{rule.subject}</strong>{' '}
                        <code style={{ fontSize: '0.70rem', background: '#F8FAFC', padding: '1px 4px', borderRadius: '3px', color: '#0284C7', border: '1px solid #E2E8F0' }}>
                          {rule.predicate}
                        </code>{' '}
                        <span>{rule.object}</span>
                      </div>
                    ) : (
                      rule.claim_text
                    )}
                  </div>

                  {rule.created_at && (
                    <div style={{ fontSize: '0.66rem', color: '#94A3B8', marginTop: '2px' }}>
                      Verified {new Date(rule.created_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

      </div>

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
                drawerClaims.map((claim) => {
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
                          <span style={{ fontWeight: 600, color: '#0284C7' }}>{claim.document_title || docMap[claim.document_id] || 'Document'}</span>
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
