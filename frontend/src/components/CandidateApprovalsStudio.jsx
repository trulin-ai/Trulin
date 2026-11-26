import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Edit3,
  Search,
  Filter,
  FileText,
  ExternalLink,
  RefreshCw,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Check,
  X,
  Trash2,
  SlidersHorizontal,
  ArrowUpRight,
  Layers,
  Inbox,
  UserCheck,
  Zap
} from 'lucide-react';
import PatternApprovalBoard from './PatternApprovalBoard';

export default function CandidateApprovalsStudio({
  activeOrg,
  token,
  user,
  showToast,
  initialDocId = null,
  onNavigateToDocument
}) {
  const [candidates, setCandidates] = useState([]);
  const [summary, setSummary] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocFilter, setSelectedDocFilter] = useState(initialDocId || 'all');
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [batchActionLoading, setBatchActionLoading] = useState(false);

  // View Mode: 'patterns' (10-minute batch adjudication) vs 'stream' (individual HITL)
  const [viewMode, setViewMode] = useState('patterns');

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [trustFilter, setTrustFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [predicateFilter, setPredicateFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [patternCategories, setPatternCategories] = useState([]);

  // Inline editing state
  const [editingClaimId, setEditingClaimId] = useState(null);
  const [editForm, setEditForm] = useState({
    claim_text: '',
    subject: '',
    predicate: '',
    object: ''
  });

  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';

  // 1. Fetch Review Queue & Summary
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let queueUrl = `/v1/review/queue?organization_id=${orgId}&limit=200`;
      if (selectedDocFilter && selectedDocFilter !== 'all') {
        queueUrl += `&document_id=${selectedDocFilter}`;
      }

      const [queueRes, sumRes, docsRes] = await Promise.all([
        fetch(queueUrl, { headers }),
        fetch(`/v1/review/summary?organization_id=${orgId}`, { headers }),
        fetch(`/v1/documents?organization_id=${orgId}&limit=500`, { headers })
      ]);

      if (queueRes.ok) {
        const queueData = await queueRes.json();
        setCandidates(queueData);
        if (queueData.length > 0 && !selectedClaimId) {
          setSelectedClaimId(queueData[0].id);
        }
      }

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(Array.isArray(docsData) ? docsData : []);
      }
    } catch (err) {
      console.error('Failed to fetch candidate review queue:', err);
      showToast?.('Error loading review queue', 'error');
    } finally {
      setLoading(false);
    }
  }, [orgId, token, selectedDocFilter, showToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync initialDocId if changed
  useEffect(() => {
    if (initialDocId) {
      setSelectedDocFilter(initialDocId);
    }
  }, [initialDocId]);

  // Document title lookup map
  const docMap = useMemo(() => {
    const map = {};
    for (const d of documents) {
      map[d.id] = d.title || d.file_name || 'Document';
    }
    return map;
  }, [documents]);

  // Dynamic list of unique predicates
  const uniquePredicates = useMemo(() => {
    const set = new Set();
    candidates.forEach(c => {
      if (c.predicate) set.add(c.predicate);
    });
    return Array.from(set).sort();
  }, [candidates]);

  // Combined available categories from patterns and candidate predicates
  const availableCategories = useMemo(() => {
    const set = new Set(patternCategories);
    candidates.forEach(c => {
      if (c.predicate) set.add(c.predicate);
      if (c.claim_type) set.add(c.claim_type);
    });
    return Array.from(set).sort();
  }, [patternCategories, candidates]);

  // Filtered candidate claims
  const filteredCandidates = useMemo(() => {
    return candidates.filter(cl => {
      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const textMatch = (cl.claim_text || '').toLowerCase().includes(q);
        const subjMatch = (cl.subject || '').toLowerCase().includes(q);
        const predMatch = (cl.predicate || '').toLowerCase().includes(q);
        const objMatch = (cl.object || '').toLowerCase().includes(q);
        const docMatch = (docMap[cl.document_id] || '').toLowerCase().includes(q);
        if (!textMatch && !subjMatch && !predMatch && !objMatch && !docMatch) return false;
      }

      // Trust tier filter
      const trust = cl.effective_trust_score ?? cl.confidence ?? 0.85;
      if (trustFilter === 'high' && trust < 0.90) return false;
      if (trustFilter === 'med' && (trust < 0.80 || trust >= 0.90)) return false;
      if (trustFilter === 'low' && trust >= 0.80) return false;

      // Category / Predicate filter
      if (categoryFilter !== 'all' && cl.predicate !== categoryFilter && cl.claim_type !== categoryFilter) return false;
      if (predicateFilter !== 'all' && cl.predicate !== predicateFilter) return false;

      return true;
    });
  }, [candidates, searchQuery, trustFilter, predicateFilter, categoryFilter, docMap]);

  // Active selected claim object
  const activeClaim = useMemo(() => {
    if (!selectedClaimId) return filteredCandidates[0] || null;
    return candidates.find(c => c.id === selectedClaimId) || filteredCandidates[0] || null;
  }, [candidates, filteredCandidates, selectedClaimId]);

  // 2. Action Handler: Approve, Reject, Edit
  const handleReviewAction = async (claimId, action, customData = {}) => {
    if (!claimId) return;
    setActionLoading(true);

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const payload = {
        action,
        reviewer_id: user?.id || null,
        reviewer_notes: customData.notes || `HITL ${action.toUpperCase()} action in Context Curator`
      };

      if (action === 'edit') {
        payload.edited_claim_text = customData.claim_text || editForm.claim_text;
        payload.edited_subject = customData.subject || editForm.subject;
        payload.edited_predicate = customData.predicate || editForm.predicate;
        payload.edited_object = customData.object || editForm.object;
      }

      const res = await fetch(`/v1/review/${claimId}/action`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        showToast?.(
          action === 'approve'
            ? '✓ Candidate claim certified & verified!'
            : action === 'reject'
            ? 'Claim rejected from policy baseline.'
            : '✓ Claim updated & certified!',
          action === 'reject' ? 'warning' : 'success'
        );

        // Optimistically remove from candidate queue
        setCandidates(prev => prev.filter(c => c.id !== claimId));
        setEditingClaimId(null);

        // Advance to next claim
        const nextIndex = filteredCandidates.findIndex(c => c.id === claimId);
        if (nextIndex >= 0 && nextIndex < filteredCandidates.length - 1) {
          setSelectedClaimId(filteredCandidates[nextIndex + 1].id);
        } else if (filteredCandidates.length > 1) {
          setSelectedClaimId(filteredCandidates[0].id);
        } else {
          setSelectedClaimId(null);
        }

        // Refresh summary metrics
        fetch(`/v1/review/summary?organization_id=${orgId}`, { headers })
          .then(r => r.ok && r.json())
          .then(s => s && setSummary(s))
          .catch(() => {});
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to process claim review', 'error');
      }
    } catch (err) {
      console.error('Error applying review action:', err);
      showToast?.('Network error applying action', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 3. Batch Action: Auto-approve high trust candidates
  const handleBatchApproveHighTrust = async () => {
    const highTrust = candidates.filter(c => (c.effective_trust_score ?? c.confidence ?? 0.85) >= 0.95);
    if (highTrust.length === 0) {
      showToast?.('No candidate claims with >=95% trust available for auto-certification.', 'info');
      return;
    }

    if (!window.confirm(`Auto-approve and certify all ${highTrust.length} high-trust candidates (>=95% confidence)?`)) {
      return;
    }

    setBatchActionLoading(true);
    let successCount = 0;

    for (const c of highTrust) {
      try {
        const res = await fetch(`/v1/review/${c.id}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'approve',
            reviewer_id: user?.id || null,
            reviewer_notes: 'Batch auto-approval of >=95% confidence candidate claims'
          })
        });
        if (res.ok) successCount++;
      } catch (err) {
        console.error('Failed to auto-approve claim:', c.id, err);
      }
    }

    setBatchActionLoading(false);
    showToast?.(`Successfully certified ${successCount} high-trust claims!`, 'success');
    fetchData();
  };

  // Metrics calculation
  const queuedCount = summary?.total_queued_for_review ?? candidates.length;
  const approvedCount = summary?.approved_claims_count ?? 0;
  const rejectedCount = summary?.rejected_claims_count ?? 0;
  const totalMetricsCount = queuedCount + approvedCount + rejectedCount;

  const queuedPct = totalMetricsCount > 0 ? Math.round((queuedCount / totalMetricsCount) * 100) : 0;
  const approvedPct = totalMetricsCount > 0 ? Math.round((approvedCount / totalMetricsCount) * 100) : 0;
  const rejectedPct = totalMetricsCount > 0 ? Math.round((rejectedCount / totalMetricsCount) * 100) : 0;

  const throughputRate = summary?.review_throughput_rate ?? (totalMetricsCount > 0 ? (approvedCount + rejectedCount) / totalMetricsCount : 0.0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', width: '100%', minHeight: '620px' }}>
      
      {/* ── TOP HEADER CONTROLS ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select
            value={selectedDocFilter}
            onChange={e => setSelectedDocFilter(e.target.value)}
            style={{
              height: '34px',
              padding: '0 10px',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: '#0F172A',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="all">All Documents ({documents.length})</option>
            {documents.map(d => (
              <option key={d.id} value={d.id}>{d.title || d.file_name}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              border: '1px solid #E2E8F0',
              background: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: loading ? 'not-allowed' : 'pointer',
              color: '#64748B',
              transition: 'all 0.15s ease'
            }}
            title="Refresh review queue"
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* ── TWO-COLUMN MAIN WORKBENCH ── */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '16px',
        width: '100%'
      }}>
        
        {/* ── LEFT COLUMN: METRICS & SCOPE SIDEBAR (~250px) ── */}
        <div style={{
          width: '250px',
          flexShrink: 0,
          background: '#FFFFFF',
          border: '1px solid #E8E3DC',
          borderRadius: '10px',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
        }}>
          {/* Document Scope */}
          <div>
            <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#1E293B', marginBottom: '8px' }}>
              Document Scope
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <select
                value={selectedDocFilter}
                onChange={e => setSelectedDocFilter(e.target.value)}
                style={{
                  flex: 1,
                  height: '32px',
                  padding: '0 8px',
                  fontSize: '0.74rem',
                  fontWeight: 500,
                  color: '#0F172A',
                  background: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  outline: 'none',
                  cursor: 'pointer',
                  minWidth: 0
                }}
              >
                <option value="all">All Documents ({documents.length})</option>
                {documents.map(d => (
                  <option key={d.id} value={d.id}>{d.title || d.file_name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={fetchData}
                disabled={loading}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '6px',
                  border: '1px solid #E2E8F0',
                  background: '#FFFFFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  color: '#64748B',
                  flexShrink: 0
                }}
                title="Refresh"
              >
                <RefreshCw size={12} className={loading ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Review Throughput */}
          <div>
            <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#1E293B', marginBottom: '6px' }}>
              Review Throughput
            </div>
            <div style={{ position: 'relative', width: '116px', height: '116px', margin: '4px auto 0 auto' }}>
              <svg width="116" height="116" viewBox="0 0 116 116">
                <circle cx="58" cy="58" r="46" stroke="#EFECE6" strokeWidth="9" fill="none" />
                <circle
                  cx="58"
                  cy="58"
                  r="46"
                  stroke={throughputRate >= 0.95 ? '#10B981' : throughputRate > 0 ? '#CBD5E1' : '#E2E8F0'}
                  strokeWidth="9"
                  fill="none"
                  strokeDasharray={289.02}
                  strokeDashoffset={289.02 * (1 - Math.min(Math.max(throughputRate, 0), 1))}
                  strokeLinecap="round"
                  transform="rotate(-90 58 58)"
                  style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                />
              </svg>
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#1E293B', lineHeight: 1.1 }}>
                  {(throughputRate * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.66rem', fontWeight: 600, color: '#64748B', marginTop: '3px' }}>
                  Target ≥95%
                </div>
              </div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid #F1F5F9' }} />

          {/* 3 Metric Rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Pending Triage */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#F59E0B' }} />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#334155' }}>Pending Triage</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '4px 0 6px 0' }}>
                <span style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0F172A' }}>{queuedCount}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748B' }}>{queuedPct}%</span>
              </div>
              <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${queuedPct}%`, height: '100%', background: '#F59E0B', borderRadius: '2px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Certified Rules */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10B981' }} />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#334155' }}>Certified Rules</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '4px 0 6px 0' }}>
                <span style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0F172A' }}>{approvedCount}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748B' }}>{approvedPct}%</span>
              </div>
              <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${approvedPct}%`, height: '100%', background: '#10B981', borderRadius: '2px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Rejected / Filtered Noise */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#EF4444' }} />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#334155' }}>Rejected / Filtered Noise</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '4px 0 6px 0' }}>
                <span style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0F172A' }}>{rejectedCount}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748B' }}>{rejectedPct}%</span>
              </div>
              <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${rejectedPct}%`, height: '100%', background: '#EF4444', borderRadius: '2px', transition: 'width 0.3s ease' }} />
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT MAIN AREA (FLEX: 1) ── */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '14px' }}>
          
          {/* Top Toolbar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            flexWrap: 'wrap'
          }}>
            {/* Segmented Toggle: Batch Patterns | Individual Stream */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              background: '#EFECE6',
              padding: '3px',
              borderRadius: '8px',
              gap: '2px'
            }}>
              <button
                type="button"
                onClick={() => setViewMode('patterns')}
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: viewMode === 'patterns' ? 700 : 500,
                  color: viewMode === 'patterns' ? '#0F172A' : '#64748B',
                  background: viewMode === 'patterns' ? '#FFFFFF' : 'transparent',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  boxShadow: viewMode === 'patterns' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                Batch Patterns
              </button>
              <button
                type="button"
                onClick={() => setViewMode('stream')}
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: viewMode === 'stream' ? 700 : 500,
                  color: viewMode === 'stream' ? '#0F172A' : '#64748B',
                  background: viewMode === 'stream' ? '#FFFFFF' : 'transparent',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  boxShadow: viewMode === 'stream' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                Individual Stream
              </button>
            </div>

            {/* Search & Category Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, justifyContent: 'flex-end' }}>
              <div style={{ position: 'relative', width: '100%', maxWidth: '300px' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                <input
                  type="text"
                  placeholder="Filter by keyword, actor, or predicate..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    height: '32px',
                    padding: '0 10px 0 32px',
                    fontSize: '0.76rem',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    background: '#FFFFFF',
                    outline: 'none',
                    boxSizing: 'border-box',
                    color: '#0F172A'
                  }}
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    style={{
                      position: 'absolute',
                      right: '8px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#94A3B8',
                      padding: 0
                    }}
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              <select
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
                style={{
                  height: '32px',
                  padding: '0 10px',
                  fontSize: '0.76rem',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  background: '#FFFFFF',
                  outline: 'none',
                  cursor: 'pointer',
                  color: '#475569',
                  minWidth: '170px'
                }}
              >
                <option value="all">Category or quick filter</option>
                {availableCategories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>

          {/* View Mode 1: 3-Column Kanban Board */}
          {viewMode === 'patterns' ? (
            <PatternApprovalBoard
              activeOrg={activeOrg}
              token={token}
              user={user}
              showToast={showToast}
              selectedDocFilter={selectedDocFilter}
              documents={documents}
              searchQuery={searchQuery}
              categoryFilter={categoryFilter}
              onCategoriesLoaded={setPatternCategories}
              onReviewSuccess={fetchData}
            />
          ) : (
            /* View Mode 2: Individual Stream */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Stream Trust Level sub-bar */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: '#FAF8F5',
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid #E8E3DC'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                    Trust Level:
                  </span>
                  <div style={{ display: 'inline-flex', background: '#E2E8F0', padding: '2px', borderRadius: '6px', gap: '2px' }}>
                    {[
                      { id: 'all', label: 'All Trust' },
                      { id: 'high', label: 'High (≥90%)' },
                      { id: 'med', label: 'Med (80-89%)' },
                      { id: 'low', label: 'Low (<80%)' }
                    ].map(pill => {
                      const isActive = trustFilter === pill.id;
                      return (
                        <button
                          key={pill.id}
                          type="button"
                          onClick={() => setTrustFilter(pill.id)}
                          style={{
                            padding: '3px 8px',
                            fontSize: '0.70rem',
                            fontWeight: isActive ? 700 : 500,
                            borderRadius: '4px',
                            border: 'none',
                            background: isActive ? '#FFFFFF' : 'transparent',
                            color: isActive ? '#0F172A' : '#64748B',
                            cursor: 'pointer',
                            boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
                          }}
                        >
                          {pill.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ fontSize: '0.72rem', color: '#64748B' }}>
                  {filteredCandidates.length} candidate claims in stream
                </div>
              </div>
      {/* ── MAIN WORKSPACE: DUAL-PANE TRIAGE STREAM ── */}
      <div style={{
        display: 'flex',
        gap: '14px',
        flex: 1,
        minHeight: '480px',
        alignItems: 'stretch'
      }}>
        
        {/* ── LEFT PANE: CANDIDATE CLAIMS QUEUE (38% WIDTH) ── */}
        <div style={{
          width: '40%',
          minWidth: '320px',
          maxWidth: '460px',
          background: '#FFFFFF',
          borderRadius: '10px',
          border: '1px solid #E2E8F0',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Queue Header */}
          <div style={{
            padding: '10px 14px',
            borderBottom: '1px solid #E2E8F0',
            background: '#FAF8F5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.74rem',
            color: '#64748B',
            fontWeight: 700
          }}>
            <span>Candidates Queued ({filteredCandidates.length})</span>
            {selectedDocFilter !== 'all' && (
              <span style={{ fontSize: '0.68rem', color: '#0284C7', fontWeight: 600 }}>
                Scoped to Document
              </span>
            )}
          </div>

          {/* Claims Scroll List */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px 10px', color: '#94A3B8', fontSize: '0.78rem' }}>
                <RefreshCw size={18} className="spin" style={{ margin: '0 auto 8px auto', display: 'block', color: '#2563EB' }} />
                <span>Loading candidate review queue...</span>
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '50px 16px', color: '#64748B' }}>
                <CheckCircle2 size={32} style={{ color: '#16A34A', margin: '0 auto 10px auto', display: 'block' }} />
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>
                  Queue Fully Triaged!
                </div>
                <div style={{ fontSize: '0.76rem', color: '#64748B', maxWidth: '240px', margin: '0 auto' }}>
                  All candidate claims for this scope have been reviewed, certified, or rejected.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {filteredCandidates.map(claim => {
                  const isSelected = activeClaim?.id === claim.id;
                  const trust = claim.effective_trust_score ?? claim.confidence ?? 0.85;
                  const trustPercent = Math.round(trust * 100);
                  const docTitle = docMap[claim.document_id] || 'Document';

                  return (
                    <div
                      key={claim.id}
                      onClick={() => {
                        setSelectedClaimId(claim.id);
                        setEditingClaimId(null);
                      }}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: isSelected ? '1.5px solid #2563EB' : '1px solid #E2E8F0',
                        background: isSelected ? '#EFF6FF' : '#FFFFFF',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: isSelected ? '0 2px 6px rgba(37,99,235,0.08)' : '0 1px 2px rgba(0,0,0,0.02)'
                      }}
                      onMouseEnter={e => {
                        if (!isSelected) e.currentTarget.style.background = '#F8FAFC';
                      }}
                      onMouseLeave={e => {
                        if (!isSelected) e.currentTarget.style.background = '#FFFFFF';
                      }}
                    >
                      {/* Top Row: Subject & Trust Score */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', marginBottom: '5px' }}>
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 800,
                          textTransform: 'uppercase',
                          color: '#1D4ED8',
                          background: 'rgba(37, 99, 235, 0.08)',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          letterSpacing: '0.03em'
                        }}>
                          {claim.subject || 'ACTOR'}
                        </span>

                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 800,
                          color: trust >= 0.90 ? '#166534' : trust >= 0.80 ? '#B45309' : '#DC2626',
                          background: trust >= 0.90 ? '#DCFCE7' : trust >= 0.80 ? '#FEF3C7' : '#FEE2E2',
                          padding: '1px 6px',
                          borderRadius: '10px'
                        }}>
                          {trustPercent}% Trust
                        </span>
                      </div>

                      {/* Statement Text Snippet */}
                      <div style={{
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: isSelected ? '#1E3A8A' : '#1E293B',
                        lineHeight: 1.4,
                        marginBottom: '6px',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden'
                      }}>
                        {claim.claim_text || 'Atomic statement'}
                      </div>

                      {/* Bottom Row: Predicate & Document Title Badge */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', fontSize: '0.68rem', color: '#64748B' }}>
                        <span style={{
                          color: '#475569',
                          fontFamily: 'monospace',
                          background: '#F1F5F9',
                          padding: '1px 5px',
                          borderRadius: '3px'
                        }}>
                          {claim.predicate || 'asserts'}
                        </span>
                        <span
                          style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px', color: '#94A3B8' }}
                          title={docTitle}
                        >
                          {docTitle}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT PANE: DEEP-DIVE REVIEW & TRIAGE ACTION PANEL (60% WIDTH) ── */}
        <div style={{
          flex: 1,
          background: '#FFFFFF',
          borderRadius: '10px',
          border: '1px solid #E2E8F0',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {activeClaim ? (
            <>
              {/* Header: Claim Title & Status */}
              <div style={{
                padding: '12px 18px',
                borderBottom: '1px solid #E2E8F0',
                background: '#FAF8F5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    fontSize: '0.66rem',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: '#B45309',
                    background: '#FEF3C7',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    border: '1px solid #FDE68A'
                  }}>
                    ⚠️ CANDIDATE FOR APPROVAL
                  </span>
                  <span style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>
                    ID: {String(activeClaim.id || '').substring(0, 8)}...
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {activeClaim.document_id && onNavigateToDocument && (
                    <button
                      type="button"
                      onClick={() => onNavigateToDocument(activeClaim.document_id)}
                      style={{
                        padding: '3px 8px',
                        fontSize: '0.70rem',
                        fontWeight: 600,
                        background: '#FFFFFF',
                        border: '1px solid #CBD5E1',
                        borderRadius: '5px',
                        color: '#0284C7',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title="View original document in Document Explorer"
                    >
                      <FileText size={11} />
                      <span>Locate in Doc ↗</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Body: Statement, SPO Breakdown, Quote, & 9 Gates */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* 1. ATOMIC STATEMENT */}
                <div>
                  <div style={{ fontSize: '0.70rem', fontWeight: 800, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em', marginBottom: '5px' }}>
                    Atomic Statement
                  </div>
                  {editingClaimId === activeClaim.id ? (
                    <textarea
                      value={editForm.claim_text}
                      onChange={e => setEditForm(prev => ({ ...prev, claim_text: e.target.value }))}
                      rows={3}
                      style={{
                        width: '100%',
                        fontSize: '0.84rem',
                        lineHeight: 1.45,
                        padding: '8px 10px',
                        border: '1.5px solid #2563EB',
                        borderRadius: '6px',
                        outline: 'none',
                        boxSizing: 'border-box',
                        fontFamily: 'inherit'
                      }}
                    />
                  ) : (
                    <div style={{
                      fontSize: '0.90rem',
                      fontWeight: 600,
                      color: '#0F172A',
                      lineHeight: 1.5,
                      background: '#F8FAFC',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0'
                    }}>
                      "{activeClaim.claim_text}"
                    </div>
                  )}
                </div>

                {/* 2. NORMALIZED TRIPLE (SPO) */}
                <div>
                  <div style={{ fontSize: '0.70rem', fontWeight: 800, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em', marginBottom: '6px' }}>
                    Normalized Logical Triple (Subject • Predicate • Object)
                  </div>
                  {editingClaimId === activeClaim.id ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: '8px' }}>
                      <div>
                        <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '3px' }}>Subject</label>
                        <input
                          type="text"
                          value={editForm.subject}
                          onChange={e => setEditForm(prev => ({ ...prev, subject: e.target.value }))}
                          style={{ width: '100%', padding: '4px 8px', fontSize: '0.76rem', border: '1px solid #CBD5E1', borderRadius: '4px', boxSizing: 'border-box' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '3px' }}>Predicate</label>
                        <input
                          type="text"
                          value={editForm.predicate}
                          onChange={e => setEditForm(prev => ({ ...prev, predicate: e.target.value }))}
                          style={{ width: '100%', padding: '4px 8px', fontSize: '0.76rem', border: '1px solid #CBD5E1', borderRadius: '4px', boxSizing: 'border-box' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '3px' }}>Object / Target</label>
                        <input
                          type="text"
                          value={editForm.object}
                          onChange={e => setEditForm(prev => ({ ...prev, object: e.target.value }))}
                          style={{ width: '100%', padding: '4px 8px', fontSize: '0.76rem', border: '1px solid #CBD5E1', borderRadius: '4px', boxSizing: 'border-box' }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      flexWrap: 'wrap',
                      background: '#F1F5F9',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      fontSize: '0.76rem'
                    }}>
                      <span style={{ fontWeight: 800, color: '#1D4ED8', background: '#DBEAFE', padding: '2px 8px', borderRadius: '4px' }}>
                        Subject: {activeClaim.subject || 'N/A'}
                      </span>
                      <span style={{ color: '#94A3B8', fontWeight: 700 }}>➔</span>
                      <span style={{ fontWeight: 800, color: '#7C3AED', background: '#EDE9FE', padding: '2px 8px', borderRadius: '4px' }}>
                        Predicate: {activeClaim.predicate || 'asserts'}
                      </span>
                      <span style={{ color: '#94A3B8', fontWeight: 700 }}>➔</span>
                      <span style={{ fontWeight: 700, color: '#0F172A', background: '#E2E8F0', padding: '2px 8px', borderRadius: '4px' }}>
                        Object: {activeClaim.object || '—'}
                      </span>
                    </div>
                  )}
                </div>

                {/* 3. EXACT SOURCE QUOTE & CITATION */}
                {activeClaim.evidence?.quote && (
                  <div>
                    <div style={{ fontSize: '0.70rem', fontWeight: 800, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em', marginBottom: '5px' }}>
                      Verifiable Evidence Span (Source Quote)
                    </div>
                    <div style={{
                      fontSize: '0.78rem',
                      fontStyle: 'italic',
                      color: '#475569',
                      lineHeight: 1.5,
                      background: '#FAF8F5',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      borderLeft: '3px solid #2563EB'
                    }}>
                      "{activeClaim.evidence.quote}"
                    </div>
                  </div>
                )}

                {/* 4. 9-GATE COMPLIANCE VERIFICATION CHECKLIST */}
                <div>
                  <div style={{ fontSize: '0.70rem', fontWeight: 800, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em', marginBottom: '8px' }}>
                    Universal 9-Gate Verification Matrix
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '6px'
                  }}>
                    {[
                      { key: 'evidence_exists', label: 'Evidence Grounded' },
                      { key: 'clause_entails_claim', label: 'Clause Entails Claim' },
                      { key: 'subject_valid', label: 'Subject Valid' },
                      { key: 'predicate_valid', label: 'Predicate Valid' },
                      { key: 'is_atomic', label: 'Atomic Fact' },
                      { key: 'duplicate_valid', label: 'Not Duplicate' },
                      { key: 'clean_prose', label: 'Clean Prose Standard' }
                    ].map(gate => {
                      const isPassed = activeClaim.gates?.[gate.key] !== false;
                      return (
                        <div
                          key={gate.key}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '5px 8px',
                            borderRadius: '5px',
                            background: isPassed ? '#F0FDF4' : '#FEF2F2',
                            border: `1px solid ${isPassed ? '#BBF7D0' : '#FECACA'}`,
                            fontSize: '0.70rem',
                            fontWeight: 600,
                            color: isPassed ? '#166534' : '#DC2626'
                          }}
                        >
                          {isPassed ? <Check size={11} style={{ color: '#16A34A' }} /> : <X size={11} style={{ color: '#DC2626' }} />}
                          <span>{gate.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* ── ACTION FOOTER: APPROVE, EDIT, REJECT ── */}
              <div style={{
                padding: '12px 18px',
                borderTop: '1px solid #E2E8F0',
                background: '#FAF8F5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '10px'
              }}>
                {editingClaimId === activeClaim.id ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => setEditingClaimId(null)}
                      style={{
                        padding: '6px 14px',
                        fontSize: '0.76rem',
                        fontWeight: 600,
                        background: '#FFFFFF',
                        border: '1px solid #CBD5E1',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        color: '#475569'
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => handleReviewAction(activeClaim.id, 'edit')}
                      style={{
                        padding: '6px 16px',
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        background: '#2563EB',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: actionLoading ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                    >
                      <CheckCircle2 size={13} />
                      <span>{actionLoading ? 'Saving...' : 'Save & Certify'}</span>
                    </button>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* 1. APPROVE & CERTIFY */}
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleReviewAction(activeClaim.id, 'approve')}
                        style={{
                          padding: '6px 16px',
                          fontSize: '0.76rem',
                          fontWeight: 700,
                          background: '#16A34A',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: actionLoading ? 'not-allowed' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          boxShadow: '0 1px 3px rgba(22, 163, 74, 0.25)'
                        }}
                        title="Promote this candidate claim to verified production standard"
                      >
                        <CheckCircle2 size={13} />
                        <span>{actionLoading ? 'Certifying...' : '✓ Approve & Certify'}</span>
                      </button>

                      {/* 2. EDIT & CERTIFY */}
                      <button
                        type="button"
                        onClick={() => {
                          setEditingClaimId(activeClaim.id);
                          setEditForm({
                            claim_text: activeClaim.claim_text || '',
                            subject: activeClaim.subject || '',
                            predicate: activeClaim.predicate || '',
                            object: activeClaim.object || ''
                          });
                        }}
                        style={{
                          padding: '6px 14px',
                          fontSize: '0.76rem',
                          fontWeight: 600,
                          background: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: '6px',
                          color: '#1E293B',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                        title="Edit statement, subject, or predicate before certifying"
                      >
                        <Edit3 size={12} style={{ color: '#2563EB' }} />
                        <span>Edit Statement</span>
                      </button>
                    </div>

                    {/* 3. REJECT */}
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => handleReviewAction(activeClaim.id, 'reject')}
                      style={{
                        padding: '6px 14px',
                        fontSize: '0.76rem',
                        fontWeight: 600,
                        background: '#FEF2F2',
                        border: '1px solid #FECACA',
                        borderRadius: '6px',
                        color: '#DC2626',
                        cursor: actionLoading ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        marginLeft: 'auto'
                      }}
                      title="Reject this claim from policy knowledge base"
                    >
                      <Trash2 size={12} style={{ color: '#DC2626' }} />
                      <span>Reject</span>
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94A3B8' }}>
              <Inbox size={32} style={{ color: '#CBD5E1', margin: '0 auto 10px auto', display: 'block' }} />
              <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0F172A' }}>No Claim Selected</div>
              <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '4px' }}>Select a candidate claim on the left to inspect and certify.</div>
            </div>
          )}
        </div>
      </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
