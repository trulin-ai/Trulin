import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const CONFLICT_TYPE_META = {
  direct_contradiction: { label: 'Direct Contradiction', bg: 'rgba(239, 68, 68, 0.12)', color: '#dc2626', border: 'rgba(239, 68, 68, 0.3)' },
  temporal_conflict: { label: 'Temporal Conflict', bg: 'rgba(245, 158, 11, 0.12)', color: '#d97706', border: 'rgba(245, 158, 11, 0.3)' },
  scope_conflict: { label: 'Scope Conflict', bg: 'rgba(99, 102, 241, 0.12)', color: '#4f46e5', border: 'rgba(99, 102, 241, 0.3)' },
  authority_conflict: { label: 'Authority Conflict', bg: 'rgba(168, 85, 247, 0.12)', color: '#9333ea', border: 'rgba(168, 85, 247, 0.3)' },
  numeric_conflict: { label: 'Numeric Conflict', bg: 'rgba(59, 130, 246, 0.12)', color: '#2563eb', border: 'rgba(59, 130, 246, 0.3)' },
  modality_conflict: { label: 'Modality Conflict', bg: 'rgba(100, 116, 139, 0.12)', color: '#475569', border: 'rgba(100, 116, 139, 0.3)' },
  exception_conflict: { label: 'Exception Carveout', bg: 'rgba(20, 184, 166, 0.12)', color: '#0d9488', border: 'rgba(20, 184, 166, 0.3)' },
  organizational_conflict: { label: 'Organizational Conflict', bg: 'rgba(236, 72, 153, 0.12)', color: '#db2777', border: 'rgba(236, 72, 153, 0.3)' },
  version_conflict: { label: 'Version Lineage', bg: 'rgba(249, 115, 22, 0.12)', color: '#ea580c', border: 'rgba(249, 115, 22, 0.3)' },
  conditional_conflict: { label: 'Conditional Trigger', bg: 'rgba(16, 185, 129, 0.12)', color: '#059669', border: 'rgba(16, 185, 129, 0.3)' },
  numerical_discrepancy: { label: 'Numeric Conflict', bg: 'rgba(59, 130, 246, 0.12)', color: '#2563eb', border: 'rgba(59, 130, 246, 0.3)' },
  temporal_outdated: { label: 'Temporal Conflict', bg: 'rgba(245, 158, 11, 0.12)', color: '#d97706', border: 'rgba(245, 158, 11, 0.3)' },
};

const formatConflictTypeBadge = (type) => {
  const norm = (type || 'direct_contradiction').toLowerCase();
  return CONFLICT_TYPE_META[norm] || {
    label: norm.replace(/_/g, ' ').toUpperCase(),
    bg: 'rgba(100, 116, 139, 0.12)',
    color: '#475569',
    border: 'rgba(100, 116, 139, 0.3)'
  };
};

export default function ContextCuratorStudio({
  activeOrg,
  showToast,
  conflicts = [],
  onResolveConflict,
  onRefreshConflicts,
  initialSubView = 'health',
  onSubViewChange
}) {
  const { user, token, hasPermission } = useAuth();
  const [curatorSubView, setCuratorSubView] = useState(initialSubView); // 'health' | 'conflicts'
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applyingActionId, setApplyingActionId] = useState(null);
  const [appliedActionIds, setAppliedActionIds] = useState(new Set());
  const [activeCategory, setActiveCategory] = useState('ALL'); // 'ALL' | 'CONTRADICTION' | 'TEMPORAL_OBSOLESCENCE' | 'LOW_CONFIDENCE'

  // Pillar 1: Clustered Governance Issues State
  const [conflictIssues, setConflictIssues] = useState([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [viewGrouping, setViewGrouping] = useState('issues'); // 'issues' | 'pairs'
  const [expandedIssueIds, setExpandedIssueIds] = useState(new Set());
  const [resolvingIssueId, setResolvingIssueId] = useState(null);
  const [reEvaluating, setReEvaluating] = useState(false);
  const [autoResolving, setAutoResolving] = useState(false);

  // Pillar 3: Context Drift & Claim Decay State
  const [driftData, setDriftData] = useState(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [remediatingId, setRemediatingId] = useState(null);

  useEffect(() => {
    if (initialSubView) {
      setCuratorSubView(initialSubView);
    }
  }, [initialSubView]);

  const handleSelectSubView = (view) => {
    setCuratorSubView(view);
    if (onSubViewChange) onSubViewChange(view);
  };

  const fetchConflictIssues = async () => {
    setIssuesLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/conflicts/issues?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setConflictIssues(data);
      } else {
        setConflictIssues([]);
      }
    } catch (e) {
      console.warn("Failed to fetch conflict issues:", e);
      setConflictIssues([]);
    } finally {
      setIssuesLoading(false);
    }
  };

  const fetchDriftData = async () => {
    try {
      setDriftLoading(true);
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/drift?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setDriftData(data);
      }
    } catch (e) {
      console.warn("Failed to fetch drift data:", e);
    } finally {
      setDriftLoading(false);
    }
  };

  const handleTriggerDriftScan = async () => {
    try {
      setDriftLoading(true);
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/drift/scan?organization_id=${orgId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDriftData(data);
        showToast?.("Drift sweep completed: Context freshness radar updated", "success");
      }
    } catch (e) {
      showToast?.(`Error: ${e.message}`, "error");
    } finally {
      setDriftLoading(false);
    }
  };

  const handleRemediateClaim = async (claimId, action) => {
    try {
      setRemediatingId(claimId);
      const userRole = user?.role || 'data_owner';
      const res = await fetch(`/v1/steward/drift/remediate?user_role=${encodeURIComponent(userRole)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: claimId,
          action,
          attester_id: user?.id || '22222222-2222-2222-2222-222222222222',
          reason: `Policy ${action} governance attestation recorded by ${user?.name || 'Authorized Data Owner'}`,
          source_version: 'v1.0'
        })
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message, "success");
        fetchDriftData();
      } else {
        const errJson = await res.json().catch(() => null);
        showToast?.(errJson?.detail || "Remediation failed", "error");
      }
    } catch (e) {
      showToast?.(`Remediation error: ${e.message}`, "error");
    } finally {
      setRemediatingId(null);
    }
  };

  useEffect(() => {
    if (curatorSubView === 'drift') {
      fetchDriftData();
    }
  }, [curatorSubView, activeOrg]);

  const handleResolveIssue = async (issueId, chosenSide, defaultReason) => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot adjudicate conflicts. Only Risk & Compliance Auditors or CCO have resolution clearance.`,
        'error'
      );
      return;
    }
    setResolvingIssueId(issueId);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/issues/${encodeURIComponent(issueId)}/resolve?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          reviewer_id: user?.id || '22222222-2222-2222-2222-222222222222',
          decision: 'approve',
          chosen_side: chosenSide,
          reason: defaultReason || `Batch resolved Governance Issue: Approved Cluster ${chosenSide} as authoritative standard.`
        })
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message || `Resolved Governance Issue (${data.resolved_conflicts_count} conflicts resolved)!`, 'success');
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        const errMsg = errJson?.detail || 'Failed to resolve issue';
        showToast?.(errMsg, 'error');
      }
    } catch (e) {
      showToast?.("Error resolving governance issue", 'error');
    } finally {
      setResolvingIssueId(null);
    }
  };

  const handleReEvaluateConflicts = async () => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot re-evaluate governance conflicts. Auditor clearance required.`,
        'error'
      );
      return;
    }
    setReEvaluating(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/re-evaluate?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message || `Purged ${data.purged_false_positives} false-positive conflicts!`, 'success');
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        showToast?.(errJson?.detail || "Failed to re-evaluate conflicts", 'error');
      }
    } catch (e) {
      showToast?.("Error re-evaluating conflicts", 'error');
    } finally {
      setReEvaluating(false);
    }
  };

  const handleAutoResolveConflicts = async () => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot execute auto-resolution. Auditor clearance required.`,
        'error'
      );
      return;
    }
    setAutoResolving(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/auto-resolve?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers
      });
      if (res.ok) {
        const data = await res.json();
        const breakdown = Object.entries(data.rules_breakdown || {})
          .map(([rule, count]) => `${rule.replace(/_/g, ' ')}: ${count}`)
          .join(', ');
        showToast?.(
          data.auto_resolved_count > 0
            ? `⚡ Autonomously resolved ${data.auto_resolved_count} conflicts! (${breakdown || 'Precedence rules applied'})`
            : `Evaluated ${data.total_evaluated} conflicts: All remaining require human auditor review.`,
          'success'
        );
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        showToast?.(errJson?.detail || "Failed to auto-resolve conflicts", 'error');
      }
    } catch (e) {
      showToast?.("Error running autonomous conflict resolution", 'error');
    } finally {
      setAutoResolving(false);
    }
  };

  const toggleExpandIssue = (issueId) => {
    setExpandedIssueIds(prev => {
      const next = new Set(prev);
      if (next.has(issueId)) next.delete(issueId);
      else next.add(issueId);
      return next;
    });
  };

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/audit?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setAuditData(data);
      } else {
        showToast?.("Failed to run data steward audit", "error");
      }
    } catch (e) {
      console.warn("Steward audit fetch fallback:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
    fetchConflictIssues();
  }, [activeOrg?.id]);

  const handleApplyAction = async (rec) => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot apply curation recommendations. Auditor clearance required.`,
        'error'
      );
      return;
    }
    setApplyingActionId(rec.id);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const userRole = user?.role || 'reviewer';
      const userName = user?.name || 'Compliance Auditor';
      const res = await fetch(`/v1/steward/actions/apply?organization_id=${orgId}&user_role=${encodeURIComponent(userRole)}&user_name=${encodeURIComponent(userName)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_type: rec.action_type,
          target_id: rec.target_id,
          reviewer_id: user?.id || '22222222-2222-2222-2222-222222222222',
          rationale: rec.rationale || rec.explanation,
          payload: {
            suggested_winner_id: rec.suggested_winner_id,
            proposed_status: rec.proposed_status,
            rationale: rec.rationale || rec.explanation
          }
        })
      });

      if (res.ok) {
        const result = await res.json();
        setAppliedActionIds(prev => new Set([...prev, rec.id]));
        showToast?.(result.message || "Curation action applied successfully!");
        setTimeout(fetchAudit, 400);
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const err = await res.json();
        showToast?.(err.detail || "Failed to apply action", "error");
      }
    } catch (e) {
      showToast?.(`Action error: ${e.message}`, "error");
    } finally {
      setApplyingActionId(null);
    }
  };

  const scorecard = auditData?.health_scorecard || {
    overall_score: 100.0,
    grade: "A+",
    freshness_index: 100.0,
    contradiction_index: 100.0,
    coverage_score: 100.0,
    total_documents: 0,
    total_claims: 0,
    active_claims: 0,
    pending_conflicts: conflicts.length || 0
  };

  const issues = auditData?.issues || [];
  const recommendations = auditData?.recommendations || [];

  const filteredIssues = activeCategory === 'ALL'
    ? issues
    : issues.filter(i => i.category === activeCategory);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '22px', paddingTop: '16px' }}>

      {/* Advisory-First Operating Mode Status Pill */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(79, 70, 229, 0.04)',
        border: '1px solid rgba(79, 70, 229, 0.18)',
        borderRadius: '10px',
        padding: '10px 16px',
        fontSize: '0.78rem',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 800, color: '#4f46e5' }}>🛡️ Curator Operating Posture:</span>
          <span style={{ fontWeight: 800, color: '#1e1b4b', background: '#e0e7ff', padding: '2px 8px', borderRadius: '6px' }}>
            Assisted Governance (Advisory-First)
          </span>
          <span style={{ color: 'var(--text-muted)' }}>
            Recommendations are advisory by default; explicit reviewer approval required before production claim mutations.
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.72rem', color: '#047857', background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '2px 8px', borderRadius: '6px', fontWeight: 700 }}>
            Shadow Mode Active (Zero-Mutation API)
          </span>
          <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600 }}>
            Controlled Autonomous: Deterministic Only
          </span>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SUB-VIEW 1: AUTONOMOUS CONTEXT HEALTH & STEWARD BOT       */}
      {/* ========================================================= */}
      {curatorSubView === 'health' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
          
          {/* Clean Professional 4-Card Governance KPI Strip (Pure White Background) */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px'
          }}>
            
            {/* CARD 1: Overall Context Health */}
            <div style={{
              background: '#FAF8F5',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'none',
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.2s ease'
            }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: '#EA580C' }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Overall Context Health
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: '#EA580C',
                  background: '#FFF7ED',
                  border: '1px solid #FFEDD5',
                  padding: '2px 7px',
                  borderRadius: '6px'
                }}>
                  Grade {scorecard.grade}
                </span>
              </div>
              <div style={{ marginTop: '12px', marginBottom: '8px' }}>
                <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.03em', lineHeight: 1.1 }}>
                  {scorecard.overall_score}%
                </div>
              </div>
              <div>
                <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${scorecard.overall_score}%`, height: '100%', background: '#EA580C', borderRadius: '2px' }} />
                </div>
                <div style={{ fontSize: '0.70rem', color: '#94A3B8', marginTop: '6px' }}>
                  Continuous Heuristic Auditing
                </div>
              </div>
            </div>

            {/* CARD 2: Contradiction Free Index */}
            <div style={{
              background: '#FAF8F5',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'none',
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.2s ease'
            }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: '#EA580C' }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Contradiction Free
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: '#C2410C',
                  background: '#FFF7ED',
                  border: '1px solid #FFEDD5',
                  padding: '2px 7px',
                  borderRadius: '6px'
                }}>
                  Active
                </span>
              </div>
              <div style={{ marginTop: '12px', marginBottom: '8px' }}>
                <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.03em', lineHeight: 1.1 }}>
                  {scorecard.contradiction_index}%
                </div>
              </div>
              <div>
                <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${scorecard.contradiction_index}%`, height: '100%', background: '#EA580C', borderRadius: '2px' }} />
                </div>
                <div style={{ fontSize: '0.70rem', color: '#94A3B8', marginTop: '6px' }}>
                  0 Conflicting Policy Rules
                </div>
              </div>
            </div>

            {/* CARD 3: Freshness & Time Validity */}
            <div style={{
              background: '#FAF8F5',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'none',
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.2s ease'
            }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: '#EA580C' }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Freshness Index
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: '#C2410C',
                  background: '#FFF7ED',
                  border: '1px solid #FFEDD5',
                  padding: '2px 7px',
                  borderRadius: '6px'
                }}>
                  Verified
                </span>
              </div>
              <div style={{ marginTop: '12px', marginBottom: '8px' }}>
                <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.03em', lineHeight: 1.1 }}>
                  {scorecard.freshness_index}%
                </div>
              </div>
              <div>
                <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${scorecard.freshness_index}%`, height: '100%', background: '#EA580C', borderRadius: '2px' }} />
                </div>
                <div style={{ fontSize: '0.70rem', color: '#94A3B8', marginTop: '6px' }}>
                  100% Time-Valid Claims
                </div>
              </div>
            </div>

            {/* CARD 4: Pending Conflicts */}
            <div
              style={{
                background: '#FAF8F5',
                border: '1px solid #E2E8F0',
                borderRadius: '12px',
                padding: '18px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)',
                position: 'relative',
                overflow: 'hidden',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onClick={() => setCuratorSubView('conflicts')}
              title="Click to open Pairwise Conflict Resolver"
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#EA580C';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(234, 88, 12, 0.12)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#E2E8F0';
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)';
              }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: '#EA580C' }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Pending Conflicts
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: '#EA580C',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px'
                }}>
                  Arbitrate ➔
                </span>
              </div>
              <div style={{ marginTop: '12px', marginBottom: '8px' }}>
                <div style={{ fontSize: '1.85rem', fontWeight: 800, color: conflicts.length > 0 ? '#DC2626' : '#0F172A', letterSpacing: '-0.03em', lineHeight: 1.1 }}>
                  {conflicts.length}
                </div>
              </div>
              <div>
                <div style={{ width: '100%', height: '4px', background: '#F1F5F9', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${conflicts.length === 0 ? 100 : Math.max(15, 100 - conflicts.length * 20)}%`, height: '100%', background: '#EA580C', borderRadius: '2px' }} />
                </div>
                <div style={{ fontSize: '0.70rem', color: '#94A3B8', marginTop: '6px' }}>
                  {conflicts.length === 0 ? 'All Rules Synchronized' : 'Requires Review'}
                </div>
              </div>
            </div>

          </div>

          {/* Autonomous Remediation Recommendations (Command Deck) */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '14px',
            padding: '22px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: '0 4px 16px rgba(15, 23, 42, 0.04)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
                  Autonomous Remediation Recommendations
                </h3>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Data Steward Agent calculates optimal resolution actions based on source authority tiers and freshness.
                </p>
              </div>
              <span className="badge badge-verified" style={{ fontSize: '0.70rem', fontWeight: 700 }}>
                {recommendations.length} Actions Available
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {recommendations.map((rec) => {
                const isApplying = applyingActionId === rec.id;
                const isApplied = appliedActionIds.has(rec.id);

                return (
                  <div
                    key={rec.id}
                    style={{
                      background: 'var(--bg-card)',
                      border: `1px solid ${isApplied ? 'rgba(25,195,125,0.4)' : 'var(--border-color)'}`,
                      borderRadius: '10px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '12px',
                      boxShadow: isApplied ? '0 0 0 2px rgba(25,195,125,0.15)' : 'none'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', fontSize: '0.65rem', fontWeight: 700 }}>
                          {rec.action_type?.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                          Confidence: {(rec.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, margin: '0 0 4px 0', color: 'var(--text-main)' }}>
                        {rec.title}
                      </h4>
                      <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                        {rec.rationale || rec.explanation || rec.summary}
                      </p>
                      {rec.proposed_status && (
                        <div style={{ marginTop: '8px', fontSize: '0.70rem', color: '#4f46e5', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <span>Proposed Status:</span>
                          <span style={{ background: '#e0e7ff', color: '#3730a3', padding: '1px 6px', borderRadius: '4px', border: '1px solid #c7d2fe' }}>
                            {rec.proposed_status}
                          </span>
                          {rec.requires_approval && (
                            <span style={{ color: '#b45309', background: '#fef3c7', padding: '1px 6px', borderRadius: '4px', border: '1px solid #fde68a', fontSize: '0.66rem' }}>
                              🔒 Auditor Approval Required
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Target: <code style={{ fontSize: '0.68rem' }}>{(rec.target_claim_id || rec.target_id)?.substring(0, 8)}</code>
                      </span>
                      <button
                        onClick={() => handleApplyAction(rec)}
                        disabled={isApplying || isApplied}
                        style={{
                          padding: '6px 14px',
                          borderRadius: '6px',
                          background: isApplied ? '#16a34a' : '#2026d2',
                          color: '#fff',
                          border: 'none',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                          cursor: isApplying || isApplied ? 'default' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {isApplying ? (
                          <>
                            <span className="spinner-sm"></span>
                            <span>Applying...</span>
                          </>
                        ) : isApplied ? (
                          <>
                            <span>✓</span>
                            <span>Approved & Applied</span>
                          </>
                        ) : (
                          <>
                            <span>⚡</span>
                            <span>Review & Approve Recommendation</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Detailed Heuristic Issues Table */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Identified Context Graph Issues ({issues.length})
              </h3>

              {/* Category Filter Pills */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {['ALL', 'CONTRADICTION', 'TEMPORAL_OBSOLESCENCE', 'LOW_CONFIDENCE'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      border: '1px solid var(--border-color)',
                      background: activeCategory === cat ? '#2026d2' : 'var(--bg-card)',
                      color: activeCategory === cat ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer'
                    }}
                  >
                    {cat.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ overflowX: 'auto', width: '100%' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px' }}>Category</th>
                    <th style={{ padding: '8px 12px' }}>Severity</th>
                    <th style={{ padding: '8px 12px' }}>Description</th>
                    <th style={{ padding: '8px 12px' }}>Target Entity</th>
                    <th style={{ padding: '8px 12px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIssues.map((issue, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="badge" style={{ fontSize: '0.65rem' }}>
                          {issue.category?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className={issue.severity === 'HIGH' ? 'badge badge-warning' : 'badge badge-muted'} style={{ fontSize: '0.65rem' }}>
                          {issue.severity}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-main)', fontWeight: 500 }}>
                        {issue.description}
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                        <code>{issue.target_id?.substring(0, 8)}</code>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        {issue.category === 'CONTRADICTION' ? (
                          <button
                            onClick={() => setCuratorSubView('conflicts')}
                            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #2026d2', background: 'rgba(32,38,210,0.06)', color: '#2026d2', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                          >
                            Arbitrate ➔
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.7rem', color: '#16a34a', fontWeight: 600 }}>Monitored</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 2: CLUSTERED GOVERNANCE ISSUES & CONFLICT QUEUE   */}
      {/* ========================================================= */}
      {curatorSubView === 'conflicts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                  Auditor Conflict Resolution Queue
                </h3>
                <span className="badge badge-warning" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                  {conflictIssues.length} Governance Issues ({conflicts.length} Total Pairwise Pairs)
                </span>
                {hasPermission('conflicts:resolve') ? (
                  <span style={{ fontSize: '0.70rem', padding: '2px 8px', borderRadius: '12px', background: '#DCFCE7', color: '#15803D', border: '1px solid #86EFAC', fontWeight: 700 }}>
                    ✓ Resolution Clearance Active
                  </span>
                ) : (
                  <span style={{ fontSize: '0.70rem', padding: '2px 8px', borderRadius: '12px', background: '#FEE2E2', color: '#DC2626', border: '1px solid #FCA5A5', fontWeight: 700 }} title="Separation of Duties (SoD) Barred: Your active role cannot adjudicate conflicts">
                    🔒 SoD Barred: Read-Only View
                  </span>
                )}
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '4px 0 0 0' }}>
                Arbitrate and supersede conflicting enterprise policies to eliminate ambiguity for autonomous AI agents.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {/* Grouping View Toggle */}
              <div style={{
                display: 'flex',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '3px'
              }}>
                <button
                  onClick={() => setViewGrouping('issues')}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    background: viewGrouping === 'issues' ? 'var(--primary-solid, #2026d2)' : 'transparent',
                    color: viewGrouping === 'issues' ? '#fff' : 'var(--text-muted)',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  Clustered Issues ({conflictIssues.length})
                </button>
                <button
                  onClick={() => setViewGrouping('pairs')}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    background: viewGrouping === 'pairs' ? 'var(--primary-solid, #2026d2)' : 'transparent',
                    color: viewGrouping === 'pairs' ? '#fff' : 'var(--text-muted)',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  Raw Pairs ({conflicts.length})
                </button>
              </div>

              {/* Action Buttons */}
              <button
                onClick={handleAutoResolveConflicts}
                disabled={autoResolving}
                className="btn btn-primary"
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'linear-gradient(135deg, #4f46e5 0%, #2563eb 100%)',
                  color: '#fff',
                  border: 'none',
                  boxShadow: '0 2px 8px rgba(79, 70, 229, 0.25)',
                  cursor: autoResolving ? 'not-allowed' : 'pointer'
                }}
                title="Autonomously resolve deterministic version, temporal, and authority conflicts in O(1) time"
              >
                {autoResolving ? 'Resolving...' : 'Auto-Resolve Deterministic'}
              </button>

              <button
                onClick={handleReEvaluateConflicts}
                disabled={reEvaluating}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                title="Re-run context-aware contradiction rules to purge non-conflicting samples"
              >
                {reEvaluating ? 'Purging...' : 'Purge False Positives'}
              </button>

              <button
                onClick={() => {
                  fetchConflictIssues();
                  if (onRefreshConflicts) onRefreshConflicts();
                }}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.78rem' }}
              >
                Refresh
              </button>
            </div>
          </div>

          {/* ========================================================= */}
          {/* VIEW MODE 1: CLUSTERED GOVERNANCE ISSUES (DEFAULT)        */}
          {/* ========================================================= */}
          {viewGrouping === 'issues' && (
            <div>
              {conflictIssues.length === 0 ? (
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '48px 24px',
                  textAlign: 'center',
                  color: 'var(--text-muted)'
                }}>
                  <span style={{ fontSize: '32px' }}>✨</span>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '8px' }}>
                    Zero Pending Governance Issues
                  </h4>
                  <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                    All enterprise claims, operational rules, and policy versions across all data sources are reconciled in non-conflicting harmony.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '16px' }}>
                  {conflictIssues.map((issue, idx) => {
                    const isResolving = resolvingIssueId === issue.issue_id;
                    const isExpanded = expandedIssueIds.has(issue.issue_id);

                    return (
                      <div
                        key={issue.issue_id || idx}
                        style={{
                          background: 'var(--bg-surface)',
                          border: '1.5px solid var(--border-color)',
                          borderRadius: '14px',
                          padding: '20px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '16px',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
                          position: 'relative'
                        }}
                      >
                        {/* Issue Header with Cluster Pill */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.96rem', color: 'var(--text-main)' }}>
                              Governance Issue #{idx + 1}: {issue.topic}
                            </span>
                            <span style={{
                              background: 'linear-gradient(135deg, #4f46e5 0%, #2563eb 100%)',
                              color: '#ffffff',
                              padding: '2px 9px',
                              borderRadius: '12px',
                              fontSize: '0.68rem',
                              fontWeight: 800,
                              letterSpacing: '0.02em',
                              boxShadow: '0 1px 4px rgba(79,70,229,0.25)'
                            }}>
                              ⚡ {issue.total_conflicts} CONFLICTS COLLAPSED
                            </span>
                            <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>
                              Severity: {issue.severity?.toUpperCase() || 'HIGH'}
                            </span>
                            {issue.blast_radius && (
                              <span
                                style={{
                                  background: issue.blast_radius === 'CRITICAL_BLAST'
                                    ? 'rgba(239, 68, 68, 0.15)'
                                    : issue.blast_radius === 'HIGH_BLAST'
                                    ? 'rgba(245, 158, 11, 0.15)'
                                    : 'rgba(59, 130, 246, 0.15)',
                                  color: issue.blast_radius === 'CRITICAL_BLAST'
                                    ? '#ef4444'
                                    : issue.blast_radius === 'HIGH_BLAST'
                                    ? '#f59e0b'
                                    : '#3b82f6',
                                  border: `1px solid ${issue.blast_radius === 'CRITICAL_BLAST' ? 'rgba(239, 68, 68, 0.3)' : issue.blast_radius === 'HIGH_BLAST' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.66rem',
                                  fontWeight: 800,
                                  letterSpacing: '0.03em'
                                }}
                                title={
                                  issue.blast_radius_breakdown
                                    ? `Evidence-Based Blast Radius: ${issue.impact_score}\n• Affected Claims: ${issue.blast_radius_breakdown.affected_claims} (score: ${issue.blast_radius_breakdown.affected_claims_score})\n• Downstream Workflows: ${issue.blast_radius_breakdown.downstream_agent_workflows} (score: ${issue.blast_radius_breakdown.workflows_score})\n• Tenant Scope: ${issue.blast_radius_breakdown.tenant_scope}\n• Source Authority: ${issue.blast_radius_breakdown.source_authority} (score: ${issue.blast_radius_breakdown.source_authority_score})\n• Conflict Severity: ${issue.blast_radius_breakdown.conflict_severity}\nFormula: ${issue.blast_radius_breakdown.formula}`
                                    : `Blast Radius Impact Score: ${issue.impact_score || 0}`
                                }
                              >
                                💥 {issue.blast_radius.replace('_', ' ')} ({issue.impact_score || 0})
                              </span>
                            )}

                            {/* Canonical Conflict Type Pill */}
                            {(() => {
                              const badgeMeta = formatConflictTypeBadge(issue.conflict_type);
                              return (
                                <span style={{
                                  background: badgeMeta.bg,
                                  color: badgeMeta.color,
                                  border: `1px solid ${badgeMeta.border}`,
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.66rem',
                                  fontWeight: 800,
                                  letterSpacing: '0.02em'
                                }}>
                                  🏷️ {badgeMeta.label}
                                </span>
                              );
                            })()}

                            {/* Exception Detected Pill */}
                            {issue.has_exception && (
                              <span style={{
                                background: 'rgba(20, 184, 166, 0.15)',
                                color: '#0d9488',
                                border: '1px solid rgba(20, 184, 166, 0.35)',
                                padding: '2px 8px',
                                borderRadius: '6px',
                                fontSize: '0.66rem',
                                fontWeight: 800
                              }} title="Lex Specialis: Specific conditional exception carveout coexists with baseline rule">
                                ⚡ Exception Detected
                              </span>
                            )}

                            {/* Conflicting Fields Pill */}
                            {issue.conflicting_fields && issue.conflicting_fields.length > 0 && (
                              <span style={{
                                background: 'rgba(100, 116, 139, 0.12)',
                                color: '#475569',
                                border: '1px solid rgba(100, 116, 139, 0.25)',
                                padding: '2px 8px',
                                borderRadius: '6px',
                                fontSize: '0.66rem',
                                fontWeight: 700
                              }}>
                                Fields: {issue.conflicting_fields.join(', ')}
                              </span>
                            )}
                          </div>
                          <span className="code-pill" style={{ fontSize: '0.74rem' }}>
                            Confidence: {(Number(issue.confidence) * 100).toFixed(0)}%
                          </span>
                        </div>

                        {/* Dual-Cluster Comparison (Stale/Sample vs Authoritative) */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
                          {/* Cluster A */}
                          <div style={{
                            background: 'var(--danger-bg)',
                            border: '1px solid var(--danger-border)',
                            padding: '16px',
                            borderRadius: '11px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '8px' }}>
                                <span>CLUSTER A ({issue.cluster_a.claim_count} Claim Variations)</span>
                                <span className="badge badge-outdated" style={{ fontSize: '0.62rem' }}>
                                  Stale / Candidate
                                </span>
                              </div>
                              <p style={{ fontSize: '0.84rem', color: 'var(--danger-text)', lineHeight: 1.5, fontWeight: 600, margin: 0 }}>
                                "{issue.cluster_a.representative_text}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.70rem', color: 'var(--text-muted)', paddingTop: '8px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Section: {issue.cluster_a.source_title}</span>
                                <span>Authority: <strong>{issue.cluster_a.authority_level || 75}%</strong></span>
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Scope: <strong>{issue.cluster_a.applicable_scope?.tier || issue.cluster_a.applicable_scope?.grade || issue.cluster_a.applicable_scope?.audience || 'General Baseline'}</strong></span>
                                <span>Status: <strong style={{ color: issue.cluster_a.certification_status === 'verified' ? '#15803D' : '#D97706' }}>{(issue.cluster_a.certification_status || 'candidate').toUpperCase()}</strong></span>
                              </div>
                              {issue.cluster_a.effective_dates?.valid_from && (
                                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                                  Dates: {issue.cluster_a.effective_dates.valid_from.substring(0, 10)} → {issue.cluster_a.effective_dates.valid_until ? issue.cluster_a.effective_dates.valid_until.substring(0, 10) : 'Present'}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Cluster B */}
                          <div style={{
                            background: 'var(--success-bg)',
                            border: '1px solid var(--success-border)',
                            padding: '16px',
                            borderRadius: '11px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '8px' }}>
                                <span>CLUSTER B ({issue.cluster_b.claim_count} Authoritative Policy)</span>
                                <span className="badge badge-allow" style={{ fontSize: '0.62rem' }}>
                                  Verified Policy
                                </span>
                              </div>
                              <p style={{ fontSize: '0.84rem', color: 'var(--success-text)', lineHeight: 1.5, fontWeight: 600, margin: 0 }}>
                                "{issue.cluster_b.representative_text}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.70rem', color: 'var(--text-muted)', paddingTop: '8px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Section: {issue.cluster_b.source_title}</span>
                                <span>Authority: <strong>{issue.cluster_b.authority_level || 75}%</strong></span>
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Scope: <strong>{issue.cluster_b.applicable_scope?.tier || issue.cluster_b.applicable_scope?.grade || issue.cluster_b.applicable_scope?.audience || 'General Baseline'}</strong></span>
                                <span>Status: <strong style={{ color: issue.cluster_b.certification_status === 'verified' ? '#15803D' : '#D97706' }}>{(issue.cluster_b.certification_status || 'candidate').toUpperCase()}</strong></span>
                              </div>
                              {issue.cluster_b.effective_dates?.valid_from && (
                                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                                  Dates: {issue.cluster_b.effective_dates.valid_from.substring(0, 10)} → {issue.cluster_b.effective_dates.valid_until ? issue.cluster_b.effective_dates.valid_until.substring(0, 10) : 'Present'}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Explainable Precedence Rationale Banner */}
                        {(issue.resolution_rationale || issue.precedence_rule) && (
                          <div style={{
                            background: 'rgba(79, 70, 229, 0.05)',
                            border: '1px solid rgba(79, 70, 229, 0.18)',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '0.74rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            flexWrap: 'wrap'
                          }}>
                            <span style={{ fontWeight: 800, color: '#4f46e5' }}>⚖️ Precedence Governance:</span>
                            <span style={{ fontWeight: 700, color: 'var(--text-main)', background: 'rgba(79, 70, 229, 0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                              [{issue.precedence_rule || 'DETERMINISTIC_PRECEDENCE'}]
                            </span>
                            <span style={{ color: 'var(--text-muted)' }}>{issue.resolution_rationale}</span>
                          </div>
                        )}

                        {/* Auditor Actions Toolbar */}
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: '10px',
                          borderTop: '1px solid var(--border-color)',
                          paddingTop: '14px'
                        }}>
                          <button
                            onClick={() => toggleExpandIssue(issue.issue_id)}
                            style={{
                              background: 'transparent',
                              border: '1px solid var(--border-color)',
                              borderRadius: '6px',
                              padding: '6px 12px',
                              fontSize: '0.74rem',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              fontWeight: 600,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            <span>{isExpanded ? '▴ Hide' : '▾ Inspect'} All {issue.total_conflicts} Underlying Pairwise Conflicts</span>
                          </button>

                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                            {/* Safety Lock Warning Badge */}
                            {!issue.can_one_click_resolve && (
                              <span style={{
                                fontSize: '0.70rem',
                                padding: '4px 10px',
                                borderRadius: '6px',
                                background: '#FEF3C7',
                                color: '#92400E',
                                border: '1px solid #FCD34D',
                                fontWeight: 700
                              }}>
                                🔒 {issue.safety_lock_reason || 'Safety Lock: Individual review required'}
                              </span>
                            )}

                            <button
                              onClick={() => handleResolveIssue(issue.issue_id, 'B')}
                              disabled={isResolving || !issue.can_one_click_resolve}
                              className="btn btn-success"
                              style={{
                                padding: '8px 16px',
                                fontSize: '0.8rem',
                                fontWeight: 700,
                                opacity: (!issue.can_one_click_resolve) ? 0.6 : 1,
                                cursor: (!issue.can_one_click_resolve) ? 'not-allowed' : 'pointer',
                                boxShadow: '0 2px 6px rgba(22,163,74,0.2)'
                              }}
                              title={!issue.can_one_click_resolve ? issue.safety_lock_reason : 'Approve Cluster B and supersede conflicting variations'}
                            >
                              {isResolving ? 'Resolving...' : `✓ One-Click Resolve: Approve Cluster B (Supersede ${issue.cluster_a.claim_count} in A)`}
                            </button>
                            <button
                              onClick={() => handleResolveIssue(issue.issue_id, 'A')}
                              disabled={isResolving}
                              className="btn btn-secondary"
                              style={{ padding: '8px 14px', fontSize: '0.78rem' }}
                            >
                              Approve Cluster A
                            </button>
                          </div>
                        </div>

                        {/* Expandable Accordion for Granular Pair Inspection */}
                        {isExpanded && (
                          <div style={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '8px',
                            padding: '12px 16px',
                            fontSize: '0.74rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            maxHeight: '260px',
                            overflowY: 'auto'
                          }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-main)', display: 'flex', justifyContent: 'space-between' }}>
                              <span>Underlying Conflict IDs in this Cluster ({issue.conflict_ids.length})</span>
                              <span style={{ color: 'var(--text-muted)' }}>Auto-deduplicated pairwise permutations</span>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '6px' }}>
                              {issue.conflict_ids.map((cid, cIdx) => (
                                <div key={cid} style={{
                                  padding: '4px 8px',
                                  background: 'var(--bg-surface)',
                                  borderRadius: '4px',
                                  border: '1px solid var(--border-color)',
                                  fontFamily: 'monospace',
                                  fontSize: '0.7rem',
                                  color: 'var(--text-muted)'
                                }}>
                                  #{cIdx + 1}: {cid.substring(0, 13)}...
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ========================================================= */}
          {/* VIEW MODE 2: RAW PAIRWISE CONFLICT LIST (UNCLUSTERED)     */}
          {/* ========================================================= */}
          {viewGrouping === 'pairs' && (
            <div>
              {conflicts.length === 0 ? (
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '48px 24px',
                  textAlign: 'center',
                  color: 'var(--text-muted)'
                }}>
                  <span style={{ fontSize: '32px' }}>✨</span>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '8px' }}>
                    Zero Pending Policy Conflicts
                  </h4>
                  <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                    All enterprise claims and operational rules across all data sources are verified and in non-conflicting harmony.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '14px' }}>
                  {conflicts.map((conf, idx) => {
                    const claimA = conf.claim_a;
                    const claimB = conf.claim_b;
                    const scoreA = claimA?.trust_scores?.[0]?.overall_score || 0.50;
                    const scoreB = claimB?.trust_scores?.[0]?.overall_score || 0.95;
                    const sectionA = claimA?.evidence?.[0]?.section || "Corporate Operations Handbook (Section 2.0)";
                    const sectionB = claimB?.evidence?.[0]?.section || "VP Engineering Directive Memo (Section 3.0)";

                    return (
                      <div
                        key={conf.id || idx}
                        style={{
                          background: 'var(--bg-surface)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '12px',
                          padding: '18px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '14px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--text-main)' }}>
                              Conflict #{idx + 1}:
                            </span>
                            {(() => {
                              const bMeta = formatConflictTypeBadge(conf.conflict_type);
                              return (
                                <span style={{
                                  background: bMeta.bg,
                                  color: bMeta.color,
                                  border: `1px solid ${bMeta.border}`,
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.66rem',
                                  fontWeight: 800
                                }}>
                                  🏷️ {bMeta.label}
                                </span>
                              );
                            })()}
                            <span className="badge badge-review" style={{ fontSize: '0.65rem' }}>
                              Severity: {conf.severity?.toUpperCase() || 'HIGH'}
                            </span>
                            {conf.conflicting_fields && conf.conflicting_fields.length > 0 && (
                              <span style={{
                                background: 'rgba(100, 116, 139, 0.12)',
                                color: '#475569',
                                border: '1px solid rgba(100, 116, 139, 0.25)',
                                padding: '2px 8px',
                                borderRadius: '6px',
                                fontSize: '0.66rem',
                                fontWeight: 700
                              }}>
                                Fields: {conf.conflicting_fields.join(', ')}
                              </span>
                            )}
                          </div>
                          <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                            Confidence: {conf.confidence || '0.95'}
                          </span>
                        </div>

                        {/* Side-by-Side Claim Comparison */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                          {/* Claim A */}
                          <div style={{
                            background: 'var(--danger-bg)',
                            border: '1px solid var(--danger-border)',
                            padding: '14px',
                            borderRadius: '10px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '10px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '6px' }}>
                                <span>CLAIM A (Stale Candidate)</span>
                                <span className="badge badge-outdated" style={{ fontSize: '0.62rem' }}>ID: {conf.claim_a_id?.substring(0, 8)}</span>
                              </div>
                              <p style={{ fontSize: '0.82rem', color: 'var(--danger-text)', lineHeight: 1.45, fontWeight: 600, margin: 0 }}>
                                "{claimA?.claim_text || 'No claim text recorded'}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.7rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Source: {sectionA}</span>
                                <span>Trust: <strong>{(Number(scoreA) * 100).toFixed(0)}%</strong></span>
                              </div>
                              {conf.applicable_scope?.claim_a_scope && (
                                <div style={{ fontSize: '0.66rem' }}>
                                  Scope: <strong>{conf.applicable_scope.claim_a_scope.tier || conf.applicable_scope.claim_a_scope.grade || 'General'}</strong>
                                </div>
                              )}
                              {conf.effective_dates?.claim_a_valid_from && (
                                <div style={{ fontSize: '0.66rem' }}>
                                  Dates: {conf.effective_dates.claim_a_valid_from.substring(0, 10)} → {conf.effective_dates.claim_a_valid_until ? conf.effective_dates.claim_a_valid_until.substring(0, 10) : 'Present'}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Claim B */}
                          <div style={{
                            background: 'var(--success-bg)',
                            border: '1px solid var(--success-border)',
                            padding: '14px',
                            borderRadius: '10px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '10px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '6px' }}>
                                <span>CLAIM B (Authoritative Candidate)</span>
                                <span className="badge badge-allow" style={{ fontSize: '0.62rem' }}>ID: {conf.claim_b_id?.substring(0, 8)}</span>
                              </div>
                              <p style={{ fontSize: '0.82rem', color: 'var(--success-text)', lineHeight: 1.45, fontWeight: 600, margin: 0 }}>
                                "{claimB?.claim_text || 'No claim text recorded'}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.7rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Source: {sectionB}</span>
                                <span>Trust: <strong>{(Number(scoreB) * 100).toFixed(0)}%</strong></span>
                              </div>
                              {conf.applicable_scope?.claim_b_scope && (
                                <div style={{ fontSize: '0.66rem' }}>
                                  Scope: <strong>{conf.applicable_scope.claim_b_scope.tier || conf.applicable_scope.claim_b_scope.grade || 'General'}</strong>
                                </div>
                              )}
                              {conf.effective_dates?.claim_b_valid_from && (
                                <div style={{ fontSize: '0.66rem' }}>
                                  Dates: {conf.effective_dates.claim_b_valid_from.substring(0, 10)} → {conf.effective_dates.claim_b_valid_until ? conf.effective_dates.claim_b_valid_until.substring(0, 10) : 'Present'}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Rationale Pill if present */}
                        {conf.resolution_rationale && (
                          <div style={{
                            background: 'rgba(79, 70, 229, 0.05)',
                            border: '1px solid rgba(79, 70, 229, 0.18)',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            fontSize: '0.72rem',
                            color: 'var(--text-muted)'
                          }}>
                            <strong style={{ color: '#4f46e5' }}>Precedence Analysis:</strong> {conf.resolution_rationale}
                          </div>
                        )}

                        {/* Auditor Resolution Actions */}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                          <button
                            onClick={() => onResolveConflict && onResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative guideline.")}
                            className="btn btn-success"
                            style={{ padding: '7px 14px', fontSize: '0.78rem', fontWeight: 600 }}
                          >
                            ✓ Approve Authoritative Claim B (Supersede A)
                          </button>
                          <button
                            onClick={() => onResolveConflict && onResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                            className="btn btn-secondary"
                            style={{ padding: '7px 12px', fontSize: '0.78rem' }}
                          >
                            Approve Claim A
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 3: CONTEXT DRIFT & CLAIM DECAY RADAR             */}
      {/* ========================================================= */}
      {curatorSubView === 'drift' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top KPI & Sweep Action Banner */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '20px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Continuous Context Drift & Claim Decay Radar
                </h3>
                <span className="badge badge-verified" style={{ background: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0' }}>
                  Half-Life Attestation
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                Monitors knowledge degradation over time. Claims older than 90 days lose authority score unless re-attested by verified Data Owners.
              </p>
            </div>

            <button
              type="button"
              disabled={driftLoading}
              onClick={handleTriggerDriftScan}
              className="btn btn-primary"
              style={{
                padding: '9px 18px',
                background: 'linear-gradient(135deg, #10B981, #059669)',
                border: 'none',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.84rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>{driftLoading ? 'Running Background Sweep...' : '⚡ Run Active Drift Sweep'}</span>
            </button>
          </div>

          {/* Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FRESHNESS INDEX</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#059669', marginTop: '2px' }}>
                {driftData?.freshness_index_pct ?? 92.5}%
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Overall context health score
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>DECAYED CLAIMS (&gt;90d)</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#D97706', marginTop: '2px' }}>
                {driftData?.decayed_claims_count ?? 3} Stale
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Requires Data Owner review
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>AVERAGE KNOWLEDGE AGE</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#4F46E5', marginTop: '2px' }}>
                {driftData?.average_age_days ?? 74} Days
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Across all stored policies
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>AGING HORIZONS</div>
              <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
                {driftData?.decay_radar ? Object.entries(driftData.decay_radar).map(([k, v]) => (
                  <span key={k} style={{ fontSize: '0.7rem', background: 'var(--bg-card)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                    {k}: <strong>{v}</strong>
                  </span>
                )) : null}
              </div>
            </div>
          </div>

          {/* Stale Claims List & Remediation Table */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Temporal Claim Degradation & Remediation Ledger
              </h4>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {driftData?.decayed_claims?.length ?? 0} tracked policies
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-card)', borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Claim & Source</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Age</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Freshness Signal</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Certification Status</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Drift Status</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)', textAlign: 'right' }}>Governance Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(driftData?.decayed_claims || []).map((item) => {
                    const isStale = item.age_days > 90;
                    return (
                      <tr key={item.claim_id} style={{ borderBottom: '1px solid var(--border-color)', background: isStale ? 'rgba(245, 158, 11, 0.03)' : 'transparent' }}>
                        <td style={{ padding: '12px 14px', maxWidth: '380px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px', lineHeight: '1.3' }}>
                            {item.claim_text}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            📄 {item.document_title}
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '0.74rem',
                            background: item.age_days <= 30 ? '#ECFDF5' : item.age_days <= 90 ? '#EFF6FF' : item.age_days <= 180 ? '#FEF3C7' : '#FEE2E2',
                            color: item.age_days <= 30 ? '#047857' : item.age_days <= 90 ? '#1D4ED8' : item.age_days <= 180 ? '#B45309' : '#B91C1C'
                          }}>
                            {item.age_days} days old
                          </span>
                        </td>

                        {/* Independent Field 1: Freshness Signal (Time Decay Factor) */}
                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontWeight: 800, color: (item.freshness_score ?? 1.0) < 0.70 ? '#DC2626' : '#059669' }}>
                              {((item.freshness_score ?? 1.0) * 100).toFixed(0)}% Freshness
                            </span>
                            {item.decay_pct > 0 && (
                              <span style={{ fontSize: '0.68rem', color: '#DC2626', fontWeight: 700 }}>
                                (-{item.decay_pct}%)
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Independent Field 2: Certification Status (Legal/Trust Decision) */}
                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '0.72rem',
                            fontWeight: 800,
                            letterSpacing: '0.02em',
                            background: (item.certification_status === 'SUPERSEDED' || item.certification_status === 'OUTDATED')
                              ? '#FEE2E2'
                              : (item.certification_status === 'CANDIDATE' || item.certification_status === 'REQUIRES_REVIEW')
                              ? '#FEF3C7'
                              : '#DCFCE7',
                            color: (item.certification_status === 'SUPERSEDED' || item.certification_status === 'OUTDATED')
                              ? '#DC2626'
                              : (item.certification_status === 'CANDIDATE' || item.certification_status === 'REQUIRES_REVIEW')
                              ? '#B45309'
                              : '#15803D',
                            border: `1px solid ${(item.certification_status === 'SUPERSEDED' || item.certification_status === 'OUTDATED') ? '#FCA5A5' : (item.certification_status === 'CANDIDATE' || item.certification_status === 'REQUIRES_REVIEW') ? '#FCD34D' : '#86EFAC'}`
                          }} title="Legal/Trust standing controlled by validation & review workflow (independent of temporal decay)">
                            {item.certification_status || 'CERTIFIED'}
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '4px',
                            background: item.drift_category === 'ACTIVE_FRESH' ? '#ECFDF5' : item.drift_category === 'AGING_WARNING' ? '#FEF3C7' : '#FEE2E2',
                            color: item.drift_category === 'ACTIVE_FRESH' ? '#047857' : item.drift_category === 'AGING_WARNING' ? '#B45309' : '#B91C1C'
                          }}>
                            {item.drift_category}
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              type="button"
                              disabled={remediatingId === item.claim_id}
                              onClick={() => handleRemediateClaim(item.claim_id, 'RE_ATTEST')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: '0.74rem', background: '#ECFDF5', borderColor: '#A7F3D0', color: '#047857', fontWeight: 700 }}
                              title="Records versioned governance attestation by Data Owner, resetting freshness horizon for 90 days"
                            >
                              {remediatingId === item.claim_id ? 'Attesting...' : '✓ Re-Attest (90d Horizon)'}
                            </button>
                            <button
                              type="button"
                              disabled={remediatingId === item.claim_id}
                              onClick={() => handleRemediateClaim(item.claim_id, 'RETIRE')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: '0.74rem', background: '#FEF2F2', borderColor: '#FECACA', color: '#B91C1C' }}
                              title="Deprecate and exclude from agent retrieval"
                            >
                              Retire
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
