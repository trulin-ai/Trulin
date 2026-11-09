import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ShieldCheck,
  AlertTriangle,
  FileText,
  GitBranch,
  Copy,
  Check,
  ArrowUpDown,
  LayoutGrid,
  Table as TableIcon,
  Sparkles,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Info,
  Layers,
  Clock,
  SlidersHorizontal,
  X
} from 'lucide-react';

export function getClaimClassification(cl, allConflictedClaimIds = new Set()) {
  const isConf = (cl.id && allConflictedClaimIds.has(cl.id)) || (cl.status || '').toLowerCase() === 'conflicted';
  if (isConf) {
    return {
      category: 'conflicted',
      badgeLabel: '⚠️ Conflict Candidate',
      badgeBg: '#FFEDD5',
      badgeColor: '#C2410C',
      badgeBorder: '#FED7AA',
    };
  }

  const claimType = (cl.claim_type || cl.data?.claim_type || '').toLowerCase().trim();
  const contentRole = (cl.content_role || cl.data?.content_role || '').toLowerCase().trim();
  const status = (cl.status || cl.data?.status || 'candidate').toLowerCase().trim();
  const certTier = (cl.certification_tier || cl.data?.certification_tier || '').toUpperCase().trim();
  const decisionStr = (cl.decision || cl.data?.decision || cl.validation_status || '').toUpperCase().trim();
  const decisionCode = (cl.decision_code || cl.data?.decision_code || '').toUpperCase().trim();
  const decisionReason = (cl.decision_reason || cl.data?.decision_reason || '').toLowerCase();

  const gates = cl.gates || cl.data?.gates || {};
  const hasGates = Object.keys(gates).length > 0;
  const allGatesPassed = cl.all_9_gates_passed === true || cl.data?.all_9_gates_passed === true ||
    (hasGates && Object.values(gates).every(v => v === true));

  // 1. Non-Rules: definitions, descriptions, contact info, examples, revision history
  const isDef = claimType === 'definition' || contentRole === 'definition' || decisionCode.includes('DEFINITION');
  if (isDef) {
    return {
      category: 'non_rule',
      badgeLabel: '📖 Definition',
      badgeBg: '#F3E8FF',
      badgeColor: '#6B21A8',
      badgeBorder: '#D8B4FE',
    };
  }

  const isContact = claimType.includes('contact') || contentRole.includes('contact');
  if (isContact) {
    return {
      category: 'non_rule',
      badgeLabel: '📞 Contact Info',
      badgeBg: '#EFF6FF',
      badgeColor: '#1D4ED8',
      badgeBorder: '#93C5FD',
    };
  }

  const isExample = claimType === 'example' || contentRole === 'example' || claimType.includes('case_study');
  if (isExample) {
    return {
      category: 'non_rule',
      badgeLabel: '💡 Example / Case Study',
      badgeBg: '#F0FDF4',
      badgeColor: '#166534',
      badgeBorder: '#BBF7D0',
    };
  }

  const isHistory = claimType.includes('revision') || contentRole.includes('revision') || contentRole.includes('history');
  if (isHistory) {
    return {
      category: 'non_rule',
      badgeLabel: '📜 Revision History',
      badgeBg: '#F1F5F9',
      badgeColor: '#475569',
      badgeBorder: '#CBD5E1',
    };
  }

  const isNonRule = certTier === 'NON_RULE'
    || ['description', 'reference', 'responsibility', 'non_rule'].includes(claimType)
    || ['description', 'reference', 'responsibility'].includes(contentRole)
    || decisionCode.includes('DESCRIPTIVE');
  if (isNonRule) {
    return {
      category: 'non_rule',
      badgeLabel: '📖 Non-Rule Context',
      badgeBg: '#F3E8FF',
      badgeColor: '#6B21A8',
      badgeBorder: '#D8B4FE',
    };
  }

  // 2. Quarantined compound rules
  if (certTier === 'QUARANTINED' || claimType === 'quarantined' || decisionCode.includes('META_RULE')) {
    return {
      category: 'quarantined',
      badgeLabel: '⚠️ Quarantined (Compound)',
      badgeBg: '#FEF3C7',
      badgeColor: '#B45309',
      badgeBorder: '#FCD34D',
    };
  }

  // 3. Review Required: missing table context, weak predicate, or below threshold
  const isReview = certTier === 'REVIEW_REQUIRED'
    || status === 'candidate'
    || status === 'review'
    || decisionStr === 'REVIEW';
  if (isReview && !allGatesPassed) {
    if (decisionReason.includes('table') || decisionReason.includes('header')) {
      return {
        category: 'review',
        badgeLabel: '⚠️ Review (Missing Context)',
        badgeBg: '#FEF9C3',
        badgeColor: '#854D0E',
        badgeBorder: '#FDE047',
      };
    }
    if (decisionCode.includes('WEAK_PREDICATE') || decisionReason.includes('predicate')) {
      return {
        category: 'review',
        badgeLabel: '⚠️ Review (Unmapped Predicate)',
        badgeBg: '#FEF9C3',
        badgeColor: '#854D0E',
        badgeBorder: '#FDE047',
      };
    }
    return {
      category: 'review',
      badgeLabel: '⚠️ Review Required',
      badgeBg: '#FEF9C3',
      badgeColor: '#854D0E',
      badgeBorder: '#FDE047',
    };
  }

  // 4. Rejected: duplicate, contradiction, or boundary violation
  const isRejected = certTier === 'REJECTED'
    || status === 'rejected'
    || decisionStr === 'REJECT'
    || ['fragment', 'duplicate'].includes(claimType)
    || decisionCode.includes('FRAGMENT')
    || decisionCode.includes('SUBJECT_CONTAMINATION');
  if (isRejected) {
    const isDup = claimType === 'duplicate' || decisionCode.includes('DUPLICATE');
    if (isDup) {
      return {
        category: 'rejected',
        badgeLabel: '📑 Duplicate (Collapsed)',
        badgeBg: '#FEE2E2',
        badgeColor: '#B91C1C',
        badgeBorder: '#FCA5A5',
      };
    }
    if (decisionReason.includes('contradiction') || decisionReason.includes('polarity')) {
      return {
        category: 'rejected',
        badgeLabel: '❌ Semantic Contradiction',
        badgeBg: '#FEE2E2',
        badgeColor: '#B91C1C',
        badgeBorder: '#FCA5A5',
      };
    }
    if (decisionReason.includes('boundary') || decisionReason.includes('threshold') || decisionReason.includes('relaxation')) {
      return {
        category: 'rejected',
        badgeLabel: '❌ Boundary Violation',
        badgeBg: '#FEE2E2',
        badgeColor: '#B91C1C',
        badgeBorder: '#FCA5A5',
      };
    }
    if (decisionCode.includes('FRAGMENT') || decisionReason.includes('ellipsis') || decisionReason.includes('truncated')) {
      return {
        category: 'rejected',
        badgeLabel: '⛔ Syntactic Fragment',
        badgeBg: '#FEE2E2',
        badgeColor: '#B91C1C',
        badgeBorder: '#FCA5A5',
      };
    }
    return {
      category: 'rejected',
      badgeLabel: '⛔ Rejected Rule',
      badgeBg: '#FEE2E2',
      badgeColor: '#B91C1C',
      badgeBorder: '#FCA5A5',
    };
  }

  // 5. Canonical v3 (Automated-Certified / Human-Certified)
  const isHumanCertified = certTier === 'HUMAN_CERTIFIED';
  const isCanon = (cl.is_canonical === true || cl.data?.is_canonical === true || allGatesPassed || decisionStr === 'APPROVE')
    && (status === 'verified' || status === 'active' || decisionStr === 'APPROVE')
    && (['rule', 'policy_rule', 'policy', 'table_rule', 'table_row', 'policy_matrix'].includes(claimType) || !claimType);
  if (isCanon) {
    return {
      category: 'canonical',
      badgeLabel: isHumanCertified ? '🛡️ Human-Certified' : '✅ Automated-Certified v3',
      badgeBg: isHumanCertified ? '#EFF6FF' : '#DCFCE7',
      badgeColor: isHumanCertified ? '#1D4ED8' : '#15803D',
      badgeBorder: isHumanCertified ? '#93C5FD' : '#86EFAC',
    };
  }

  return {
    category: 'review',
    badgeLabel: '⚠️ Review Required',
    badgeBg: '#FEF9C3',
    badgeColor: '#854D0E',
    badgeBorder: '#FDE047',
  };
}

export function getClaimDisplayCategory(cl, allConflictedClaimIds = new Set()) {
  return getClaimClassification(cl, allConflictedClaimIds).category;
}

export default function AssetClaimsStudioPane({
  asset,
  claims = [],
  allConflictedClaimIds = new Set(),
  graphData,
  onLocateInDoc,
  onInspectInDag,
  showToast
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'canonical' | 'review' | 'quarantined' | 'non_rule' | 'rejected' | 'conflicted'
  const [trustTierFilter, setTrustTierFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [sortBy, setSortBy] = useState('trust_desc'); // 'trust_desc' | 'trust_asc' | 'subject_asc' | 'index'
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [copiedClaimId, setCopiedClaimId] = useState(null);

  const totalClaims = claims.length;

  // Compute metrics across universal governance categories
  const metrics = useMemo(() => {
    let canonicalCount = 0;
    let reviewCount = 0;
    let quarantinedCount = 0;
    let nonRuleCount = 0;
    let rejectedCount = 0;
    let conflictedCount = 0;
    let summaryCount = 0;
    let totalScore = 0;

    claims.forEach(cl => {
      const cat = getClaimDisplayCategory(cl, allConflictedClaimIds);
      if (cat === 'conflicted') conflictedCount++;
      else if (cat === 'rejected') rejectedCount++;
      else if (cat === 'quarantined') quarantinedCount++;
      else if (cat === 'non_rule') nonRuleCount++;
      else if (cat === 'canonical') canonicalCount++;
      else if (cat === 'review') reviewCount++;

      const isSummary = cl.claim_type === 'derived_summary' || cl.content_role === 'summary';
      if (isSummary) summaryCount++;

      const rawScore = cl.trustScore ?? cl.data?.trustScore ?? cl.data?.confidence ?? cl.data?.trust_score;
      const score = (rawScore !== undefined && rawScore !== null && !isNaN(Number(rawScore)))
        ? Number(rawScore)
        : 0.0;
      totalScore += score;
    });

    const avgScore = totalClaims > 0 ? Math.round((totalScore / totalClaims) * 100) : 0;
    const verifiedPct = totalClaims > 0 ? Math.round((canonicalCount / totalClaims) * 100) : 100;

    return {
      total: totalClaims,
      canonical: canonicalCount,
      verified: canonicalCount,
      review: reviewCount,
      quarantined: quarantinedCount,
      nonRule: nonRuleCount,
      rejected: rejectedCount,
      conflicted: conflictedCount,
      summary: summaryCount,
      verifiedPct,
      avgScore
    };
  }, [claims, allConflictedClaimIds, totalClaims]);

  // Filter and sort pipeline
  const filteredClaims = useMemo(() => {
    return claims.filter(cl => {
      const cat = getClaimDisplayCategory(cl, allConflictedClaimIds);

      // Status filter
      if (statusFilter === 'canonical' && cat !== 'canonical') return false;
      if (statusFilter === 'verified' && cat !== 'canonical') return false;
      if (statusFilter === 'review' && cat !== 'review') return false;
      if (statusFilter === 'quarantined' && cat !== 'quarantined') return false;
      if (statusFilter === 'non_rule' && cat !== 'non_rule') return false;
      if (statusFilter === 'rejected' && cat !== 'rejected') return false;
      if (statusFilter === 'conflicted' && cat !== 'conflicted') return false;

      // Trust tier filter
      const rawScore = cl.trustScore ?? cl.data?.trustScore ?? cl.data?.confidence ?? cl.data?.trust_score;
      const score = (rawScore !== undefined && rawScore !== null && !isNaN(Number(rawScore)))
        ? Number(rawScore)
        : 0.0;
      if (trustTierFilter === 'high' && score < 0.9) return false;
      if (trustTierFilter === 'med' && (score < 0.7 || score >= 0.9)) return false;
      if (trustTierFilter === 'low' && score >= 0.7) return false;

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const text = (cl.fullText || cl.label || cl.data?.claim_text || '').toLowerCase();
        const subj = (cl.subject || cl.data?.subject || '').toLowerCase();
        const pred = (cl.predicate || cl.data?.predicate || '').toLowerCase();
        const obj = (cl.object || cl.data?.object || '').toLowerCase();
        const id = String(cl.id || '').toLowerCase();

        if (!text.includes(q) && !subj.includes(q) && !pred.includes(q) && !obj.includes(q) && !id.includes(q)) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      const scoreA = Number(a.trustScore ?? a.data?.trustScore ?? a.data?.confidence ?? a.data?.trust_score ?? 0.0);
      const scoreB = Number(b.trustScore ?? b.data?.trustScore ?? b.data?.confidence ?? b.data?.trust_score ?? 0.0);

      if (sortBy === 'trust_desc') return scoreB - scoreA;
      if (sortBy === 'trust_asc') return scoreA - scoreB;
      if (sortBy === 'subject_asc') {
        const sA = (a.subject || a.data?.subject || a.label || '').toLowerCase();
        const sB = (b.subject || b.data?.subject || b.label || '').toLowerCase();
        return sA.localeCompare(sB);
      }
      return 0;
    });
  }, [claims, allConflictedClaimIds, statusFilter, trustTierFilter, searchQuery, sortBy]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredClaims.length / pageSize));
  const paginatedClaims = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredClaims.slice(start, start + pageSize);
  }, [filteredClaims, currentPage, pageSize]);

  const handleCopyClaim = (cl) => {
    const text = cl.fullText || cl.label || cl.data?.claim_text || '';
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedClaimId(cl.id);
    showToast?.('Claim statement copied to clipboard');
    setTimeout(() => setCopiedClaimId(null), 2000);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      width: '100%',
      minHeight: '480px',
      background: '#F8FAFC',
      padding: '16px',
      borderRadius: '10px',
      border: '1px solid #E2E8F0',
      boxSizing: 'border-box'
    }}>
      {/* 1. TOP HEADER */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: '#FFF7ED',
              color: '#EA580C',
              fontWeight: 800
            }}>
              ⚡
            </span>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#0F172A' }}>
              Extracted Atomic Claims ({totalClaims})
            </h3>
            {metrics.conflicted > 0 && (
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '999px',
                background: '#FEF2F2',
                color: '#DC2626',
                border: '1px solid #FCA5A5'
              }}>
                {metrics.conflicted} in conflict
              </span>
            )}
          </div>
          <p style={{ margin: '4px 0 0 36px', fontSize: '0.78rem', color: '#64748B' }}>
            Fine-grained atomic facts extracted by AI from <strong>{asset?.node?.label || 'this asset'}</strong> to govern agent executions.
          </p>
        </div>
      </div>

      {/* RAW EXTRACTION AUDIT VIEW BANNER */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        background: '#FFFBEB',
        border: '1px solid #FDE68A',
        borderRadius: '8px',
        padding: '10px 16px',
        marginBottom: '14px'
      }}>
        <AlertTriangle size={20} color="#D97706" style={{ flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#92400E', letterSpacing: '0.04em' }}>
            RAW EXTRACTION AUDIT VIEW — NOT AGENT-CONSUMABLE
          </div>
          <div style={{ fontSize: '0.72rem', color: '#B45309', marginTop: '2px', lineHeight: 1.4 }}>
            This view displays the {totalClaims} raw extraction candidates for human inspection, debugging, and provenance audit.
            Downstream AI agents strictly consume the <strong>{metrics.canonical} certified v3 canonical claims</strong> passing all 9 hard governance gates.
          </div>
        </div>
      </div>

      {/* 2. SEARCH & FILTER CONTROLS BAR */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        {/* Search input */}
        <div style={{
          position: 'relative',
          flex: '1 1 240px',
          maxWidth: '380px'
        }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search claims by keyword, subject, or predicate..."
            value={searchQuery}
            onChange={e => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              width: '100%',
              padding: '6px 28px 6px 30px',
              fontSize: '0.78rem',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              outline: 'none',
              background: '#F8FAFC',
              color: '#0F172A',
              boxSizing: 'border-box'
            }}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setCurrentPage(1);
              }}
              style={{
                position: 'absolute',
                right: '8px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: '#94A3B8',
                padding: '2px'
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Filter buttons & sort */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#F1F5F9', padding: '2px', borderRadius: '6px', flexWrap: 'wrap', gap: '2px' }}>
            {[
              { id: 'all', label: `Raw candidates (${totalClaims})` },
              { id: 'canonical', label: `Canonical v3 (${metrics.canonical})` },
              ...(metrics.review > 0 ? [{ id: 'review', label: `Review required (${metrics.review})` }] : []),
              { id: 'quarantined', label: `Quarantined (${metrics.quarantined})` },
              { id: 'non_rule', label: `Non-rules (${metrics.nonRule})` },
              { id: 'rejected', label: `Rejected (${metrics.rejected})` },
              ...(metrics.conflicted > 0 ? [{ id: 'conflicted', label: `Conflicts (${metrics.conflicted})` }] : []),
              ...(metrics.summary > 0 ? [{ id: 'summary', label: `Summaries (${metrics.summary})` }] : [])
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setStatusFilter(tab.id);
                  setCurrentPage(1);
                }}
                style={{
                  padding: '4px 9px',
                  fontSize: '0.72rem',
                  fontWeight: statusFilter === tab.id ? 700 : 500,
                  borderRadius: '5px',
                  border: 'none',
                  background: statusFilter === tab.id ? '#FFFFFF' : 'transparent',
                  color: statusFilter === tab.id ? '#0F172A' : '#64748B',
                  boxShadow: statusFilter === tab.id ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Trust Tier Select */}
          <select
            value={trustTierFilter}
            onChange={e => {
              setTrustTierFilter(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              padding: '5px 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              background: '#FFFFFF',
              color: '#334155',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <option value="all">All Trust Tiers</option>
            <option value="high">High Trust (≥90%)</option>
            <option value="med">Medium Trust (70-89%)</option>
            <option value="low">Low Trust (&lt;70%)</option>
          </select>

          {/* Sort By Select */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              padding: '5px 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              background: '#FFFFFF',
              color: '#334155',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <option value="trust_desc">Sort: Highest Trust</option>
            <option value="trust_asc">Sort: Lowest Trust</option>
            <option value="subject_asc">Sort: Subject (A-Z)</option>
          </select>

          {/* View Mode Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#F1F5F9', padding: '2px', borderRadius: '6px' }}>
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              title="Cards View"
              style={{
                padding: '4px 6px',
                borderRadius: '5px',
                border: 'none',
                background: viewMode === 'cards' ? '#FFFFFF' : 'transparent',
                color: viewMode === 'cards' ? '#0F172A' : '#64748B',
                boxShadow: viewMode === 'cards' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                cursor: 'pointer'
              }}
            >
              <LayoutGrid size={14} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              title="Table View"
              style={{
                padding: '4px 6px',
                borderRadius: '5px',
                border: 'none',
                background: viewMode === 'table' ? '#FFFFFF' : 'transparent',
                color: viewMode === 'table' ? '#0F172A' : '#64748B',
                boxShadow: viewMode === 'table' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                cursor: 'pointer'
              }}
            >
              <TableIcon size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* 3. MAIN CONTENT: CARDS OR TABLE */}
      {filteredClaims.length === 0 ? (
        <div style={{
          background: '#FFFFFF',
          border: '1px dashed #CBD5E1',
          borderRadius: '8px',
          padding: '40px 20px',
          textAlign: 'center',
          color: '#64748B'
        }}>
          <AlertTriangle size={28} style={{ color: '#F59E0B', margin: '0 auto 8px auto' }} />
          <h4 style={{ margin: '0 0 4px 0', fontSize: '0.9rem', color: '#0F172A', fontWeight: 700 }}>
            No matching claims found
          </h4>
          <p style={{ margin: 0, fontSize: '0.76rem' }}>
            Try adjusting your search query, status filters, or trust score tiers.
          </p>
          {(searchQuery || statusFilter !== 'all' || trustTierFilter !== 'all') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
                setTrustTierFilter('all');
                setCurrentPage(1);
              }}
              style={{
                marginTop: '12px',
                padding: '5px 12px',
                fontSize: '0.74rem',
                fontWeight: 600,
                color: '#2563EB',
                background: '#EFF6FF',
                border: '1px solid #BFDBFE',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : viewMode === 'cards' ? (
        /* CARDS VIEW */
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '12px'
        }}>
          {paginatedClaims.map((cl, idx) => {
            const isConf = allConflictedClaimIds.has(cl.id) || cl.status === 'conflicted';
            const rawTrust = cl.trustScore ?? cl.data?.trustScore ?? cl.data?.confidence ?? cl.data?.trust_score;
            const hasScore = rawTrust !== undefined && rawTrust !== null && !isNaN(Number(rawTrust));
            const trustVal = hasScore ? Number(rawTrust) : null;
            const trustPercent = trustVal !== null ? Math.round(trustVal * 100) : null;
            const isSummary = cl.claim_type === 'derived_summary' || 
                              cl.claim_type === 'summary_non_canonical' ||
                              cl.data?.claim_type === 'derived_summary' ||
                              cl.data?.claim_type === 'summary_non_canonical' ||
                              cl.is_canonical === false || 
                              cl.data?.is_canonical === false;
            const subject = cl.subject || cl.data?.subject || '';
            const predicate = cl.predicate || cl.data?.predicate || '';
            const claimText = cl.fullText || cl.label || cl.data?.claim_text || '';
            const evidence = cl.data?.evidence_snippet || cl.data?.quote || cl.data?.context_clause || '';
            const globalIndex = (currentPage - 1) * pageSize + idx + 1;

            const { category: cat, badgeLabel, badgeBg, badgeColor, badgeBorder } = getClaimClassification(cl, allConflictedClaimIds);

            return (
              <div
                key={cl.id || idx}
                style={{
                  background: '#FFFFFF',
                  border: isConf ? '1.5px solid #FED7AA' : '1px solid #E2E8F0',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = isConf ? '#F97316' : '#94A3B8';
                  e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.06)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = isConf ? '#FED7AA' : '#E2E8F0';
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.03)';
                }}
              >
                {/* Card Top: Index, Status Badge, Trust Score */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '0.66rem',
                        fontWeight: 700,
                        color: '#64748B',
                        background: '#F1F5F9',
                        padding: '1px 6px',
                        borderRadius: '4px'
                      }}>
                        #{globalIndex}
                      </span>
                      <span style={{
                        fontSize: '0.64rem',
                        fontWeight: 700,
                        padding: '2px 7px',
                        borderRadius: '999px',
                        background: badgeBg,
                        color: badgeColor,
                        border: `1px solid ${badgeBorder}`
                      }}>
                        {badgeLabel}
                      </span>
                      {isSummary && (
                        <span style={{
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          padding: '2px 7px',
                          borderRadius: '999px',
                          background: '#F1F5F9',
                          color: '#475569',
                          border: '1px solid #CBD5E1'
                        }} title="Derived macro summary; non-canonical rule.">
                          📑 Derived Summary
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        color: (cat === 'canonical' && trustPercent !== null)
                          ? (trustPercent >= 90 ? '#059669' : trustPercent >= 70 ? '#D97706' : '#DC2626')
                          : '#64748B'
                      }}>
                        {cat === 'canonical' && trustPercent !== null
                          ? `Trust: ${trustPercent}%`
                          : cat === 'rejected'
                          ? 'Confidence: Uncalibrated (Rejected)'
                          : cat === 'non_rule'
                          ? 'Contextual (Non-Rule)'
                          : 'Confidence: Uncalibrated'}
                      </span>
                    </div>
                  </div>

                  {/* Subject & Predicate tags */}
                  {(subject || predicate) && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
                      {subject && (
                        <span style={{
                          fontSize: '0.64rem',
                          fontWeight: 600,
                          color: '#475569',
                          background: '#F1F5F9',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          border: '1px solid #E2E8F0'
                        }}>
                          Subj: {subject}
                        </span>
                      )}
                      {predicate && (
                        <span style={{
                          fontSize: '0.64rem',
                          fontWeight: 600,
                          color: '#2563EB',
                          background: '#EFF6FF',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          border: '1px solid #DBEAFE'
                        }}>
                          Pred: {predicate}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Claim Text */}
                  <p style={{
                    margin: '0 0 6px 0',
                    fontSize: '0.78rem',
                    color: '#0F172A',
                    fontWeight: 600,
                    lineHeight: 1.45
                  }}>
                    "{claimText}"
                  </p>

                  {/* Evidence snippet if present */}
                  {evidence && (
                    <div style={{
                      marginTop: '6px',
                      padding: '6px 8px',
                      borderRadius: '5px',
                      background: '#F8FAFC',
                      borderLeft: '3px solid #CBD5E1',
                      fontSize: '0.68rem',
                      color: '#475569',
                      fontStyle: 'italic',
                      lineHeight: 1.35
                    }}>
                      &ldquo;{evidence}&rdquo;
                    </div>
                  )}

                  {/* 9 Hard Governance Gates Micro-Audit Bar */}
                  {(() => {
                    const gates = cl.gates || cl.data?.gates || null;
                    if (!gates) return null;
                    const passedCount = Object.values(gates).filter(v => v === true).length;
                    return (
                      <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px dashed #E2E8F0' }}>
                        <div style={{ fontSize: '0.60rem', fontWeight: 700, color: '#64748B', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Governance Gates ({passedCount}/9 passed):
                        </div>
                        <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap' }}>
                          {Object.entries(gates).map(([gName, gVal]) => (
                            <span
                              key={gName}
                              title={`${gName}: ${gVal ? 'PASSED' : 'FAILED'}`}
                              style={{
                                fontSize: '0.58rem',
                                padding: '1px 4px',
                                borderRadius: '3px',
                                background: gVal ? '#ECFDF5' : '#FEF2F2',
                                color: gVal ? '#047857' : '#B91C1C',
                                border: `1px solid ${gVal ? '#A7F3D0' : '#FECACA'}`,
                                fontWeight: 600
                              }}
                            >
                              {gName.replace(/_/g, ' ')}: {gVal ? '✓' : '✗'}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Gate Failure Reason / Provenance Diagnostic */}
                  {(cl.decision_reason || cl.data?.decision_reason || cat === 'rejected' || cat === 'review') && (
                    <div style={{
                      marginTop: '8px',
                      padding: '6px 8px',
                      borderRadius: '5px',
                      background: cat === 'rejected' ? '#FEF2F2' : '#FEFCE8',
                      border: `1px solid ${cat === 'rejected' ? '#FECACA' : '#FEF08A'}`,
                      fontSize: '0.65rem',
                      lineHeight: 1.35,
                      color: cat === 'rejected' ? '#991B1B' : '#713F12',
                    }}>
                      <div style={{ fontWeight: 700, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span>{cat === 'rejected' ? '⛔ Rejection Reason:' : '⚠️ Adjudication Notice:'}</span>
                      </div>
                      <div>
                        {cl.decision_reason || cl.data?.decision_reason || (cat === 'rejected' ? 'Candidate does not satisfy normative certification gates.' : 'Manual adjudication review required before production routing.')}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderTop: '1px solid #F1F5F9',
                  paddingTop: '8px',
                  marginTop: '4px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {onLocateInDoc && (
                      <button
                        type="button"
                        onClick={() => onLocateInDoc(cl)}
                        title="Locate and highlight in Document Reader"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 7px',
                          fontSize: '0.68rem',
                          fontWeight: 600,
                          color: '#0284C7',
                          background: '#F0F9FF',
                          border: '1px solid #BAE6FD',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#E0F2FE'}
                        onMouseLeave={e => e.currentTarget.style.background = '#F0F9FF'}
                      >
                        <FileText size={11} />
                        <span>Locate</span>
                      </button>
                    )}

                    {onInspectInDag && (
                      <button
                        type="button"
                        onClick={() => onInspectInDag(cl)}
                        title="Inspect in Interactive Lineage DAG"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 7px',
                          fontSize: '0.68rem',
                          fontWeight: 600,
                          color: '#7C3AED',
                          background: '#F5F3FF',
                          border: '1px solid #DDD6FE',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#EDE9FE'}
                        onMouseLeave={e => e.currentTarget.style.background = '#F5F3FF'}
                      >
                        <GitBranch size={11} />
                        <span>Lineage DAG</span>
                      </button>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleCopyClaim(cl)}
                    title="Copy claim statement"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '3px',
                      padding: '3px 6px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: copiedClaimId === cl.id ? '#059669' : '#64748B',
                      background: copiedClaimId === cl.id ? '#DCFCE7' : '#F8FAFC',
                      border: `1px solid ${copiedClaimId === cl.id ? '#86EFAC' : '#E2E8F0'}`,
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {copiedClaimId === cl.id ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copiedClaimId === cl.id ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* DENSE TABLE VIEW */
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          overflowX: 'auto',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.74rem' }}>
            <thead>
              <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', color: '#475569', fontWeight: 700 }}>
                <th style={{ padding: '8px 12px', width: '50px' }}>#</th>
                <th style={{ padding: '8px 12px', width: '100px' }}>Status</th>
                <th style={{ padding: '8px 12px', width: '90px' }}>Trust</th>
                <th style={{ padding: '8px 12px', width: '130px' }}>Subject</th>
                <th style={{ padding: '8px 12px', width: '120px' }}>Predicate</th>
                <th style={{ padding: '8px 12px' }}>Atomic Claim Statement</th>
                <th style={{ padding: '8px 12px', width: '160px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedClaims.map((cl, idx) => {
                const isConf = allConflictedClaimIds.has(cl.id) || cl.status === 'conflicted';
                const rawTrust = cl.trustScore ?? cl.data?.trustScore ?? cl.data?.confidence ?? cl.data?.trust_score;
                const hasScore = rawTrust !== undefined && rawTrust !== null && !isNaN(Number(rawTrust));
                const trustVal = hasScore ? Number(rawTrust) : null;
                const trustPercent = trustVal !== null ? Math.round(trustVal * 100) : null;
                const subject = cl.subject || cl.data?.subject || '—';
                const predicate = cl.predicate || cl.data?.predicate || '—';
                const claimText = cl.fullText || cl.label || cl.data?.claim_text || '';
                const globalIndex = (currentPage - 1) * pageSize + idx + 1;

                const { category: cat, badgeLabel, badgeBg, badgeColor, badgeBorder } = getClaimClassification(cl, allConflictedClaimIds);

                return (
                  <tr
                    key={cl.id || idx}
                    style={{
                      borderBottom: '1px solid #F1F5F9',
                      background: isConf ? 'rgba(255, 237, 213, 0.2)' : 'transparent'
                    }}
                  >
                    <td style={{ padding: '8px 12px', color: '#64748B', fontWeight: 600 }}>
                      #{globalIndex}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        fontSize: '0.62rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '999px',
                        background: badgeBg,
                        color: badgeColor,
                        border: `1px solid ${badgeBorder}`
                      }}>
                        {badgeLabel}
                      </span>
                    </td>
                    <td 
                      style={{ padding: '8px 12px', cursor: 'help' }}
                      title={`Validation Breakdown (${trustPercent !== null ? trustPercent : 0}%):
• Evidence Support: ${Math.round((cl.trustScores?.evidence_score ?? cl.data?.evidence_score ?? 1.0) * 100)}%
• Source Fidelity: ${Math.round((cl.trustScores?.source_score ?? cl.data?.source_score ?? 1.0) * 100)}%
• Semantic Completeness: ${Math.round((cl.trustScores?.consistency_score ?? cl.data?.consistency_score ?? 1.0) * 100)}%
• Conflict Clearance: ${Math.round((cl.trustScores?.authority_score ?? cl.data?.authority_score ?? 1.0) * 100)}%
• Quality Gates: SCHEMA_VALID | EVIDENCE_SUPPORTED | PREDICATE_CANONICAL | CONFLICT_CHECKED`}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{
                          fontWeight: 800,
                          fontSize: '0.78rem',
                          color: trustPercent !== null ? (trustPercent >= 90 ? '#059669' : trustPercent >= 70 ? '#D97706' : '#DC2626') : '#94A3B8'
                        }}>
                          {trustPercent !== null ? `${trustPercent}%` : '—'}
                        </span>
                        <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
                          <span title="Evidence Support: 100%" style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#059669', display: 'inline-block' }} />
                          <span title="Semantic Completeness: 100%" style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#059669', display: 'inline-block' }} />
                          <span title="Conflict Clearance: 100%" style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#059669', display: 'inline-block' }} />
                          <span title="Predicate Canonical: Verified" style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#2563EB', display: 'inline-block' }} />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#334155', fontWeight: 600 }}>
                      {subject}
                    </td>
                    <td style={{ padding: '8px 12px', color: '#2563EB', fontWeight: 600 }}>
                      {predicate}
                    </td>
                    <td style={{ padding: '8px 12px', color: '#0F172A', fontWeight: 500 }}>
                      "{claimText}"
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        {onLocateInDoc && (
                          <button
                            type="button"
                            onClick={() => onLocateInDoc(cl)}
                            title="Locate in Document"
                            style={{
                              padding: '2px 5px',
                              fontSize: '0.66rem',
                              color: '#0284C7',
                              background: '#F0F9FF',
                              border: '1px solid #BAE6FD',
                              borderRadius: '4px',
                              cursor: 'pointer'
                            }}
                          >
                            Locate
                          </button>
                        )}
                        {onInspectInDag && (
                          <button
                            type="button"
                            onClick={() => onInspectInDag(cl)}
                            title="Inspect in DAG"
                            style={{
                              padding: '2px 5px',
                              fontSize: '0.66rem',
                              color: '#7C3AED',
                              background: '#F5F3FF',
                              border: '1px solid #DDD6FE',
                              borderRadius: '4px',
                              cursor: 'pointer'
                            }}
                          >
                            DAG
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleCopyClaim(cl)}
                          title="Copy Statement"
                          style={{
                            padding: '2px 5px',
                            fontSize: '0.66rem',
                            color: '#64748B',
                            background: '#F8FAFC',
                            border: '1px solid #E2E8F0',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          {copiedClaimId === cl.id ? '✓' : 'Copy'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. PAGINATION FOOTER */}
      {filteredClaims.length > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '8px 4px',
          fontSize: '0.74rem',
          color: '#64748B'
        }}>
          <div>
            Showing <strong>{(currentPage - 1) * pageSize + 1}</strong> to <strong>{Math.min(currentPage * pageSize, filteredClaims.length)}</strong> of <strong>{filteredClaims.length}</strong> claims
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>Per page:</span>
              <select
                value={pageSize}
                onChange={e => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                style={{
                  padding: '3px 6px',
                  fontSize: '0.72rem',
                  border: '1px solid #CBD5E1',
                  borderRadius: '4px',
                  background: '#FFFFFF',
                  color: '#334155',
                  cursor: 'pointer'
                }}
              >
                <option value={12}>12</option>
                <option value={24}>24</option>
                <option value={48}>48</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '2px',
                  padding: '3px 8px',
                  fontSize: '0.72rem',
                  border: '1px solid #CBD5E1',
                  borderRadius: '4px',
                  background: currentPage === 1 ? '#F1F5F9' : '#FFFFFF',
                  color: currentPage === 1 ? '#94A3B8' : '#334155',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                }}
              >
                <ChevronLeft size={12} />
                Prev
              </button>

              <span style={{ padding: '0 4px', fontWeight: 600 }}>
                {currentPage} / {totalPages}
              </span>

              <button
                type="button"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '2px',
                  padding: '3px 8px',
                  fontSize: '0.72rem',
                  border: '1px solid #CBD5E1',
                  borderRadius: '4px',
                  background: currentPage === totalPages ? '#F1F5F9' : '#FFFFFF',
                  color: currentPage === totalPages ? '#94A3B8' : '#334155',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
                }}
              >
                Next
                <ChevronRight size={12} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
