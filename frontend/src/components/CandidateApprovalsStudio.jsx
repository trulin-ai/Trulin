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
  UserCheck
} from 'lucide-react';

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

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [trustFilter, setTrustFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [predicateFilter, setPredicateFilter] = useState('all');

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

      // Predicate filter
      if (predicateFilter !== 'all' && cl.predicate !== predicateFilter) return false;

      return true;
    });
  }, [candidates, searchQuery, trustFilter, predicateFilter, docMap]);

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', width: '100%', minHeight: '620px' }}>
      
      {/* ── TOP KPI & SUMMARY STRIP ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '12px'
      }}>
        {/* Metric 1: Pending Queue */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
        }}>
          <div>
            <div style={{ fontSize: '0.70rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em' }}>
              Pending Candidate Triage
            </div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#D97706', marginTop: '2px' }}>
              {summary?.total_queued_for_review ?? candidates.length}
            </div>
          </div>
          <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: '#FEF3C7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <AlertTriangle size={18} style={{ color: '#D97706' }} />
          </div>
        </div>

        {/* Metric 2: Certified / Approved Claims */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
        }}>
          <div>
            <div style={{ fontSize: '0.70rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em' }}>
              Certified Policy Rules
            </div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#16A34A', marginTop: '2px' }}>
              {summary?.approved_claims_count ?? '—'}
            </div>
          </div>
          <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: '#DCFCE7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCircle2 size={18} style={{ color: '#16A34A' }} />
          </div>
        </div>

        {/* Metric 3: Rejected / Filtered Noise */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
        }}>
          <div>
            <div style={{ fontSize: '0.70rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em' }}>
              Rejected / Filtered Noise
            </div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#DC2626', marginTop: '2px' }}>
              {summary?.rejected_claims_count ?? '—'}
            </div>
          </div>
          <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <XCircle size={18} style={{ color: '#DC2626' }} />
          </div>
        </div>

        {/* Metric 4: Triage Throughput & Batch Action */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
        }}>
          <div>
            <div style={{ fontSize: '0.70rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B', letterSpacing: '0.04em' }}>
              Review Throughput
            </div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#2563EB', marginTop: '2px' }}>
              {summary ? `${(summary.review_throughput_rate * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
          <button
            type="button"
            disabled={batchActionLoading || candidates.length === 0}
            onClick={handleBatchApproveHighTrust}
            style={{
              padding: '6px 11px',
              fontSize: '0.72rem',
              fontWeight: 700,
              background: '#F0FDF4',
              color: '#166534',
              border: '1px solid #BBF7D0',
              borderRadius: '6px',
              cursor: batchActionLoading || candidates.length === 0 ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
            title="Automatically approve and promote all candidate claims with >=95% confidence"
          >
            <Sparkles size={12} className={batchActionLoading ? 'spin' : ''} style={{ color: '#16A34A' }} />
            <span>{batchActionLoading ? 'Certifying...' : 'Certify ≥95%'}</span>
          </button>
        </div>
      </div>

      {/* ── FILTER & SCOPE TOOLBAR ── */}
      <div style={{
        background: '#FAF8F5',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        {/* Left: Document Scope Selector & Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', flex: 1, minWidth: '300px' }}>
          
          {/* Document Scope Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} style={{ color: '#0284C7' }} />
            <select
              value={selectedDocFilter}
              onChange={e => setSelectedDocFilter(e.target.value)}
              style={{
                height: '32px',
                padding: '2px 8px',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#0F172A',
                background: '#FFFFFF',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                outline: 'none',
                maxWidth: '220px',
                cursor: 'pointer'
              }}
            >
              <option value="all">All Documents ({documents.length})</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  {d.title || d.file_name}
                </option>
              ))}
            </select>
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', flex: 1, minWidth: '180px', maxWidth: '360px' }}>
            <Search size={13} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Filter by keyword, actor, or predicate..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                height: '32px',
                padding: '4px 10px 4px 28px',
                fontSize: '0.76rem',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                background: '#FFFFFF',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: '#94A3B8' }}
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Right: Trust Tier & Predicate Filter Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          
          {/* Trust Tier Pills */}
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

          {/* Refresh Button */}
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            style={{
              height: '30px',
              padding: '0 8px',
              fontSize: '0.72rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              color: '#475569',
              fontWeight: 600
            }}
            title="Refresh candidate review queue"
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
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
  );
}
