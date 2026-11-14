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
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  AlignRight,
  ExternalLink
} from 'lucide-react';

export function getClaimClassification(cl, allConflictedClaimIds = new Set()) {
  const isConf = (cl.id && allConflictedClaimIds.has(cl.id)) || (cl.status || '').toLowerCase() === 'conflicted';
  if (isConf) {
    return {
      category: 'conflicted',
      badgeLabel: 'Conflict Candidate',
      badgeBg: 'rgba(249, 115, 22, 0.12)',
      badgeColor: '#C2410C',
      badgeBorder: 'rgba(249, 115, 22, 0.25)',
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
      badgeLabel: 'Definition',
      badgeBg: 'rgba(168, 85, 247, 0.10)',
      badgeColor: '#6B21A8',
      badgeBorder: 'rgba(168, 85, 247, 0.22)',
    };
  }

  const isContact = claimType.includes('contact') || contentRole.includes('contact');
  if (isContact) {
    return {
      category: 'non_rule',
      badgeLabel: 'Contact Info',
      badgeBg: 'rgba(59, 130, 246, 0.10)',
      badgeColor: '#1D4ED8',
      badgeBorder: 'rgba(59, 130, 246, 0.22)',
    };
  }

  const isExample = claimType === 'example' || contentRole === 'example' || claimType.includes('case_study');
  if (isExample) {
    return {
      category: 'non_rule',
      badgeLabel: 'Example / Case Study',
      badgeBg: 'rgba(34, 197, 94, 0.10)',
      badgeColor: '#166534',
      badgeBorder: 'rgba(34, 197, 94, 0.22)',
    };
  }

  const isHistory = claimType.includes('revision') || contentRole.includes('revision') || contentRole.includes('history');
  if (isHistory) {
    return {
      category: 'non_rule',
      badgeLabel: 'Revision History',
      badgeBg: 'rgba(100, 116, 139, 0.10)',
      badgeColor: '#475569',
      badgeBorder: 'rgba(100, 116, 139, 0.22)',
    };
  }

  const isNonRule = certTier === 'NON_RULE'
    || ['description', 'reference', 'responsibility', 'non_rule'].includes(claimType)
    || ['description', 'reference', 'responsibility'].includes(contentRole)
    || decisionCode.includes('DESCRIPTIVE');
  if (isNonRule) {
    return {
      category: 'non_rule',
      badgeLabel: 'Non-Rule Context',
      badgeBg: 'rgba(59, 130, 246, 0.10)',
      badgeColor: '#0369A1',
      badgeBorder: 'rgba(59, 130, 246, 0.22)',
    };
  }

  // 2. Quarantined compound rules
  if (certTier === 'QUARANTINED' || claimType === 'quarantined' || decisionCode.includes('META_RULE')) {
    return {
      category: 'quarantined',
      badgeLabel: 'Quarantined',
      badgeBg: 'rgba(168, 85, 247, 0.10)',
      badgeColor: '#7E22CE',
      badgeBorder: 'rgba(168, 85, 247, 0.22)',
    };
  }

  // 3. Review Required: missing table context, weak predicate, or below threshold
  const isReview = certTier === 'REVIEW_REQUIRED'
    || status === 'candidate'
    || status === 'review'
    || decisionStr === 'REVIEW';
  if (isReview && !allGatesPassed) {
    return {
      category: 'review',
      badgeLabel: 'Review Required',
      badgeBg: 'rgba(234, 179, 8, 0.14)',
      badgeColor: '#B45309',
      badgeBorder: 'rgba(234, 179, 8, 0.28)',
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
    return {
      category: 'rejected',
      badgeLabel: 'Rejected',
      badgeBg: 'rgba(239, 68, 68, 0.10)',
      badgeColor: '#B91C1C',
      badgeBorder: 'rgba(239, 68, 68, 0.22)',
    };
  }

  // 5. Canonical v3 (Automated-Certified / Human-Certified)
  const isCanon = (cl.is_canonical === true || cl.data?.is_canonical === true || allGatesPassed || decisionStr === 'APPROVE')
    && (status === 'verified' || status === 'active' || decisionStr === 'APPROVE')
    && (['rule', 'policy_rule', 'policy', 'table_rule', 'table_row', 'policy_matrix'].includes(claimType) || !claimType);
  if (isCanon) {
    return {
      category: 'canonical',
      badgeLabel: 'Canonical v3',
      badgeBg: 'rgba(34, 197, 94, 0.12)',
      badgeColor: '#15803D',
      badgeBorder: 'rgba(34, 197, 94, 0.25)',
    };
  }

  return {
    category: 'review',
    badgeLabel: 'Review Required',
    badgeBg: 'rgba(234, 179, 8, 0.14)',
    badgeColor: '#B45309',
    badgeBorder: 'rgba(234, 179, 8, 0.28)',
  };
}

export function getClaimDisplayCategory(cl, allConflictedClaimIds = new Set()) {
  return getClaimClassification(cl, allConflictedClaimIds).category;
}

// Low-opacity, very light shade color palettes matching status categories & mockup
export const STATUS_ROW_THEME = {
  canonical: {
    bg: 'rgba(34, 197, 94, 0.035)',       // Very light shade, low opacity green
    hoverBg: 'rgba(34, 197, 94, 0.08)',   // Low opacity green hover
    border: '#E2E8F0',
    accent: '#15803D'
  },
  review: {
    bg: 'rgba(234, 179, 8, 0.04)',        // Very light shade, low opacity amber
    hoverBg: 'rgba(234, 179, 8, 0.09)',   // Low opacity amber hover
    border: '#E2E8F0',
    accent: '#B45309'
  },
  non_rule: {
    bg: 'rgba(59, 130, 246, 0.035)',      // Very light shade, low opacity blue
    hoverBg: 'rgba(59, 130, 246, 0.08)',  // Low opacity blue hover
    border: '#E2E8F0',
    accent: '#0369A1'
  },
  rejected: {
    bg: 'rgba(239, 68, 68, 0.035)',       // Very light shade, low opacity red
    hoverBg: 'rgba(239, 68, 68, 0.08)',   // Low opacity red hover
    border: '#E2E8F0',
    accent: '#B91C1C'
  },
  quarantined: {
    bg: 'rgba(168, 85, 247, 0.035)',     // Very light shade, low opacity purple
    hoverBg: 'rgba(168, 85, 247, 0.08)', // Low opacity purple hover
    border: '#E2E8F0',
    accent: '#7E22CE'
  },
  conflicted: {
    bg: 'rgba(249, 115, 22, 0.04)',       // Very light shade, low opacity orange
    hoverBg: 'rgba(249, 115, 22, 0.09)',  // Low opacity orange hover
    border: '#E2E8F0',
    accent: '#C2410C'
  }
};

const STANDARD_GATES = [
  { key: 'span_exists', altKey: 'evidence_exists', label: 'Span exists' },
  { key: 'clause_entails_claim', altKey: 'clause_entails_claim', label: 'Clause entails claim' },
  { key: 'subject_valid', altKey: 'subject_valid', label: 'Subject valid' },
  { key: 'counterparty_resolved', altKey: 'counterparty_resolved', label: 'Counterparty resolved' },
  { key: 'predicate_valid', altKey: 'predicate_valid', label: 'Predicate valid' },
  { key: 'is_atomic', altKey: 'atomicity_valid', label: 'Is atomic' },
  { key: 'is_not_duplicate', altKey: 'duplicate_valid', label: 'Is not duplicate' },
  { key: 'claim_type_allowed', altKey: 'claim_type_allowed', label: 'Claim type allowed' },
  { key: 'human_approved_if_required', altKey: 'human_approved_if_required', label: 'Human approved if required' },
  { key: 'text_integrity', altKey: 'text_integrity', label: 'Text integrity' }
];

export default function AssetClaimsStudioPane({
  asset,
  claims = [],
  allConflictedClaimIds = new Set(),
  graphData,
  onLocateInDoc,
  onLocateSource,
  onInspectInDag,
  showToast
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'canonical' | 'review' | 'quarantined' | 'non_rule' | 'rejected' | 'conflicted'
  const [trustTierFilter, setTrustTierFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [sortBy, setSortBy] = useState('subject_asc'); // 'subject_asc' | 'trust_desc' | 'trust_asc' | 'index'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20); // 20, 50, 80, 100
  const [copiedClaimId, setCopiedClaimId] = useState(null);

  // Selection states
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [selectedCheckboxIds, setSelectedCheckboxIds] = useState(new Set());

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

  // Stable document identifier for claim titles
  const docIdentifier = useMemo(() => {
    const raw = asset?.node?.label || asset?.node?.data?.title || 'DOC';
    const cleaned = raw.replace(/[^a-zA-Z0-9]/g, '').slice(0, 10).toUpperCase();
    return cleaned || 'NORTHWINDR';
  }, [asset]);

  // Helper to format clean Claim Title
  const getClaimDisplayTitle = (cl, index) => {
    if (cl.title && String(cl.title).startsWith('Claim_')) return cl.title;
    if (cl.display_id) return cl.display_id;
    if (cl.claim_code) return cl.claim_code;
    const numStr = String(index).padStart(3, '0');
    return `Claim_${docIdentifier}_${numStr}`;
  };

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

  // Current active inspected claim in right pane
  const selectedClaim = useMemo(() => {
    if (!filteredClaims || filteredClaims.length === 0) return null;
    if (selectedClaimId) {
      const found = filteredClaims.find(c => (c.id || c._tempId) === selectedClaimId);
      if (found) return found;
    }
    return paginatedClaims[0] || filteredClaims[0];
  }, [filteredClaims, paginatedClaims, selectedClaimId]);

  // Computed data for active inspected claim
  const selectedClaimIndex = useMemo(() => {
    if (!selectedClaim) return 1;
    const idx = filteredClaims.findIndex(c => (c.id || c._tempId) === (selectedClaim.id || selectedClaim._tempId));
    return idx >= 0 ? idx + 1 : 1;
  }, [filteredClaims, selectedClaim]);

  const selectedTitle = useMemo(() => {
    if (!selectedClaim) return `Claim_${docIdentifier}_001`;
    return getClaimDisplayTitle(selectedClaim, selectedClaimIndex);
  }, [selectedClaim, selectedClaimIndex, docIdentifier]);

  const selectedTrustPercent = useMemo(() => {
    if (!selectedClaim) return 95;
    const raw = selectedClaim.trustScore ?? selectedClaim.data?.trustScore ?? selectedClaim.data?.confidence ?? selectedClaim.data?.trust_score;
    if (raw !== undefined && raw !== null && !isNaN(Number(raw))) {
      return Math.round(Number(raw) * 100);
    }
    const cat = getClaimDisplayCategory(selectedClaim, allConflictedClaimIds);
    return cat === 'canonical' ? 95 : 82;
  }, [selectedClaim, allConflictedClaimIds]);

  const getGateStatus = (cl, gate) => {
    if (!cl) return true;
    const gates = cl.gates || cl.data?.gates || {};
    if (gates[gate.key] !== undefined) return Boolean(gates[gate.key]);
    if (gates[gate.altKey] !== undefined) return Boolean(gates[gate.altKey]);
    const cat = getClaimDisplayCategory(cl, allConflictedClaimIds);
    if (cat === 'canonical' || cl.all_9_gates_passed === true || cl.data?.all_9_gates_passed === true) {
      return true;
    }
    if (cat === 'rejected') {
      if (gate.key === 'is_not_duplicate' && (cl.claim_type === 'duplicate' || cl.decision_code?.includes('DUPLICATE'))) return false;
      if (gate.key === 'clause_entails_claim' && cl.decision_reason?.includes('contradiction')) return false;
      if (gate.key === 'predicate_valid' && cl.decision_code?.includes('PREDICATE')) return false;
    }
    if (cat === 'review') {
      if (gate.key === 'counterparty_resolved' && cl.decision_reason?.includes('counterparty')) return false;
      if (gate.key === 'is_atomic' && cl.decision_reason?.includes('compound')) return false;
    }
    return true;
  };

  const passedGatesCount = useMemo(() => {
    if (!selectedClaim) return 10;
    return STANDARD_GATES.filter(g => getGateStatus(selectedClaim, g)).length;
  }, [selectedClaim]);

  const handleCopyClaim = (cl) => {
    const text = cl.fullText || cl.label || cl.data?.claim_text || '';
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedClaimId(cl.id);
    showToast?.('Claim statement copied to clipboard');
    setTimeout(() => setCopiedClaimId(null), 2000);
  };

  const handleCopyAll = () => {
    const targetClaims = selectedCheckboxIds.size > 0
      ? filteredClaims.filter(c => selectedCheckboxIds.has(c.id || c._tempId))
      : filteredClaims;

    if (targetClaims.length === 0) {
      showToast?.('No claims available to copy', 'error');
      return;
    }

    const payload = targetClaims.map((c, idx) => {
      const title = getClaimDisplayTitle(c, idx + 1);
      const cat = getClaimDisplayCategory(c, allConflictedClaimIds);
      const text = c.fullText || c.label || c.data?.claim_text || '';
      return `${title} [${cat}]: ${text}`;
    }).join('\n\n');

    navigator.clipboard.writeText(payload);
    showToast?.(`Copied ${targetClaims.length} claims to clipboard`);
  };

  const toggleSelectAllPage = () => {
    const next = new Set(selectedCheckboxIds);
    const allPageSelected = paginatedClaims.every(c => next.has(c.id || c._tempId));
    if (allPageSelected) {
      paginatedClaims.forEach(c => next.delete(c.id || c._tempId));
    } else {
      paginatedClaims.forEach(c => next.add(c.id || c._tempId));
    }
    setSelectedCheckboxIds(next);
  };

  const toggleSelectOne = (claimId) => {
    const next = new Set(selectedCheckboxIds);
    if (next.has(claimId)) next.delete(claimId);
    else next.add(claimId);
    setSelectedCheckboxIds(next);
  };

  const handleEscalate = () => {
    showToast?.(`Claim "${selectedTitle}" escalated for auditor resolution.`);
  };

  const handleResolve = () => {
    showToast?.(`Claim "${selectedTitle}" validated and marked authoritative.`);
  };

  // Locate Source Action: Opens the document where this claim is located in Document Explorer
  const handleLocateSource = () => {
    const targetDocId = selectedClaim?.document_id 
      || selectedClaim?.data?.document_id 
      || selectedClaim?.data?.doc_id 
      || selectedClaim?.doc_id
      || asset?.node?.data?.doc_id 
      || asset?.node?.data?.document_id
      || asset?.node?.id 
      || '';
    const cleanDocId = String(targetDocId).replace(/^doc_/, '');

    showToast?.('Opening source document in Document Explorer...');
    if (onLocateSource) {
      onLocateSource(selectedClaim, cleanDocId);
    } else {
      const wsId = (typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('workspace') : '') || 'ws_d0d0b1a7ca';
      window.location.href = `/documents?workspace=${wsId}&doc=${cleanDocId}`;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Nov 14, 2026';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return 'Nov 14, 2026';
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return 'Nov 14, 2026';
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      width: '100%',
      background: 'transparent',
      padding: '0',
      margin: '0',
      border: 'none',
      boxSizing: 'border-box'
    }}>
      {/* 1. TOP SEARCH & FILTER CONTROLS BAR (Matches Image 2 & page background) */}
      <div style={{
        background: '#FAF8F5',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '6px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        boxShadow: 'none'
      }}>
        {/* Left: Search input */}
        <div style={{
          position: 'relative',
          flex: '1 1 240px',
          maxWidth: '320px'
        }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search claims by keyword, subject"
            value={searchQuery}
            onChange={e => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              width: '100%',
              padding: '6px 28px 6px 32px',
              fontSize: '0.78rem',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              outline: 'none',
              background: '#FAF8F5',
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

        {/* Middle: Category Pills */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          background: '#EAE5DE',
          padding: '2px',
          borderRadius: '6px',
          flexWrap: 'wrap',
          gap: '2px'
        }}>
          {[
            { id: 'all', label: `Raw candidates (${totalClaims})` },
            { id: 'canonical', label: `Canonical v3 (${metrics.canonical})` },
            { id: 'review', label: `Review required (${metrics.review})` },
            { id: 'quarantined', label: `Quarantined (${metrics.quarantined})` },
            { id: 'non_rule', label: `Non-rules (${metrics.nonRule})` },
            { id: 'rejected', label: `Rejected (${metrics.rejected})` }
          ].map(tab => {
            const isActive = statusFilter === tab.id;
            return (
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
                  fontWeight: isActive ? 700 : 500,
                  borderRadius: '5px',
                  border: 'none',
                  background: isActive ? '#FAF8F5' : 'transparent',
                  color: isActive ? '#0F172A' : '#64748B',
                  boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Right: Dropdowns & Copy All */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* All Trust Tiers */}
          <select
            value={trustTierFilter}
            onChange={e => {
              setTrustTierFilter(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              padding: '5px 8px',
              fontSize: '0.72rem',
              fontWeight: 500,
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              background: '#FAF8F5',
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

          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              padding: '5px 8px',
              fontSize: '0.72rem',
              fontWeight: 500,
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              background: '#FAF8F5',
              color: '#334155',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <option value="subject_asc">Sort: Subject (A-Z)</option>
            <option value="trust_desc">Sort: Highest Trust</option>
            <option value="trust_asc">Sort: Lowest Trust</option>
          </select>

          {/* Copy All Button */}
          <button
            type="button"
            onClick={handleCopyAll}
            title="Copy filtered or selected claims"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              fontSize: '0.72rem',
              fontWeight: 600,
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              background: '#FAF8F5',
              color: '#334155',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#F3EFEA'}
            onMouseLeave={e => e.currentTarget.style.background = '#FAF8F5'}
          >
            <Copy size={13} />
            <span>Copy all</span>
          </button>
        </div>
      </div>

      {/* 2. SPLIT-PANE BODY: CLAIMS TABLE (LEFT) + CLAIM INSPECTOR (RIGHT) */}
      <div style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: '10px',
        width: '100%',
        boxSizing: 'border-box'
      }}>
        {/* ======================================================== */}
        {/* LEFT PANE: CLAIMS TABLE (Takes ~58-60% width)            */}
        {/* ======================================================== */}
        <div style={{
          flex: '1 1 58%',
          background: '#FAF8F5',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh - 190px)',
          minHeight: '480px',
          boxShadow: 'none'
        }}>
          {filteredClaims.length === 0 ? (
            <div style={{
              padding: '60px 20px',
              textAlign: 'center',
              color: '#64748B'
            }}>
              <AlertTriangle size={32} style={{ color: '#F59E0B', margin: '0 auto 10px auto' }} />
              <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', color: '#0F172A', fontWeight: 700 }}>
                No matching claims found
              </h4>
              <p style={{ margin: 0, fontSize: '0.78rem' }}>
                Adjust your search query, status filters, or trust score tiers.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('all');
                  setTrustTierFilter('all');
                  setCurrentPage(1);
                }}
                style={{
                  marginTop: '14px',
                  padding: '6px 14px',
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
            </div>
          ) : (
            /* Scrollable claims listing container with thin light status background per card */
            <div style={{ overflowY: 'auto', overflowX: 'auto', flex: 1 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.76rem' }}>
                <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: '#FAF8F5' }}>
                  <tr style={{ background: '#FAF8F5', borderBottom: '1px solid #CBD5E1', color: '#475569', fontWeight: 700 }}>
                    {/* Checkbox column */}
                    <th style={{ padding: '8px 12px', width: '34px', background: '#FAF8F5' }}>
                      <input
                        type="checkbox"
                        checked={paginatedClaims.length > 0 && paginatedClaims.every(c => selectedCheckboxIds.has(c.id || c._tempId))}
                        onChange={toggleSelectAllPage}
                        style={{ cursor: 'pointer', borderRadius: '3px' }}
                      />
                    </th>
                    {/* Claim Title */}
                    <th style={{ padding: '8px 12px', background: '#FAF8F5' }}>Claim Title</th>
                    {/* Status with inline filter */}
                    <th style={{ padding: '8px 12px', width: '170px', background: '#FAF8F5' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <span>Status</span>
                        <select
                          value={statusFilter}
                          onChange={e => {
                            setStatusFilter(e.target.value);
                            setCurrentPage(1);
                          }}
                          style={{
                            border: 'none',
                            background: 'transparent',
                            color: '#64748B',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            outline: 'none',
                            padding: 0
                          }}
                        >
                          <option value="all">All statuses</option>
                          <option value="canonical">Canonical v3</option>
                          <option value="review">Review Required</option>
                          <option value="non_rule">Non-Rule Context</option>
                          <option value="quarantined">Quarantined</option>
                          <option value="rejected">Rejected</option>
                        </select>
                      </div>
                    </th>
                    {/* Trigger */}
                    <th style={{ padding: '8px 12px', width: '85px', background: '#FAF8F5' }}>Trigger</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedClaims.map((cl, idx) => {
                    const globalIdx = (currentPage - 1) * pageSize + idx + 1;
                    const claimTitle = getClaimDisplayTitle(cl, globalIdx);
                    const { category: cat, badgeLabel, badgeBg, badgeColor, badgeBorder } = getClaimClassification(cl, allConflictedClaimIds);
                    const claimKey = cl.id || cl._tempId || `cl_${idx}`;
                    const isSelected = (selectedClaim && (selectedClaim.id || selectedClaim._tempId) === claimKey);
                    const isChecked = selectedCheckboxIds.has(claimKey);
                    const isTrigger = cat === 'canonical' || cl.is_trigger === true || cl.data?.is_trigger === true;
                    
                    // Thin light background color & border theme mapped to the status tab
                    const theme = STATUS_ROW_THEME[cat] || STATUS_ROW_THEME.non_rule;

                    return (
                      <tr
                        key={claimKey}
                        onClick={() => setSelectedClaimId(claimKey)}
                        style={{
                          borderBottom: '1px solid #E2E8F0',
                          borderLeft: isSelected ? `4px solid ${theme.accent}` : '4px solid transparent',
                          background: isSelected ? theme.hoverBg : theme.bg,
                          cursor: 'pointer',
                          transition: 'all 0.12s ease'
                        }}
                        onMouseEnter={e => {
                          if (!isSelected) e.currentTarget.style.background = theme.hoverBg;
                        }}
                        onMouseLeave={e => {
                          if (!isSelected) e.currentTarget.style.background = theme.bg;
                        }}
                      >
                        {/* Checkbox */}
                        <td
                          style={{ padding: '9px 12px', width: '34px' }}
                          onClick={e => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleSelectOne(claimKey)}
                            style={{ cursor: 'pointer', borderRadius: '3px' }}
                          />
                        </td>

                        {/* Title */}
                        <td style={{ padding: '9px 12px', fontWeight: 600, color: '#0F172A' }}>
                          {claimTitle}
                        </td>

                        {/* Status badge */}
                        <td style={{ padding: '9px 12px' }}>
                          <span style={{
                            display: 'inline-block',
                            fontSize: '0.69rem',
                            fontWeight: 700,
                            padding: '2px 7px',
                            borderRadius: '5px',
                            background: badgeBg,
                            color: badgeColor,
                            border: `1px solid ${badgeBorder}`
                          }}>
                            {badgeLabel}
                          </span>
                        </td>

                        {/* Trigger */}
                        <td style={{ padding: '9px 12px' }}>
                          {isTrigger ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#15803D', fontWeight: 600, fontSize: '0.73rem' }}>
                              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
                              Yes
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#64748B', fontWeight: 500, fontSize: '0.73rem' }}>
                              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#94A3B8', display: 'inline-block' }} />
                              No
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer with 20, 50, 80, 100 selector beside Next button */}
          {filteredClaims.length > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderTop: '1px solid #E2E8F0',
              background: '#FAF8F5',
              fontSize: '0.73rem',
              color: '#64748B',
              flexShrink: 0
            }}>
              <div>
                Showing <strong>{(currentPage - 1) * pageSize + 1}</strong> to <strong>{Math.min(currentPage * pageSize, filteredClaims.length)}</strong> of <strong>{filteredClaims.length}</strong>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <button
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  style={{
                    padding: '3px 7px',
                    fontSize: '0.72rem',
                    border: '1px solid #CBD5E1',
                    borderRadius: '4px',
                    background: currentPage === 1 ? '#EAE5DE' : '#FAF8F5',
                    color: currentPage === 1 ? '#94A3B8' : '#334155',
                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '2px'
                  }}
                >
                  <ChevronLeft size={12} />
                  Prev
                </button>
                <span style={{ fontWeight: 600, padding: '0 4px' }}>
                  {currentPage} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  style={{
                    padding: '3px 7px',
                    fontSize: '0.72rem',
                    border: '1px solid #CBD5E1',
                    borderRadius: '4px',
                    background: currentPage === totalPages ? '#EAE5DE' : '#FAF8F5',
                    color: currentPage === totalPages ? '#94A3B8' : '#334155',
                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '2px'
                  }}
                >
                  Next
                  <ChevronRight size={12} />
                </button>

                {/* Per page selector (20, 50, 80, 100) beside Next button */}
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginLeft: '6px' }}>
                  <span style={{ fontSize: '0.71rem', color: '#64748B' }}>Per page:</span>
                  <select
                    value={pageSize}
                    onChange={e => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    style={{
                      padding: '3px 6px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      border: '1px solid #CBD5E1',
                      borderRadius: '4px',
                      background: '#FAF8F5',
                      color: '#334155',
                      cursor: 'pointer',
                      outline: 'none'
                    }}
                  >
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={80}>80</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ======================================================== */}
        {/* RIGHT PANE: CLAIM DETAILS INSPECTOR (Same #FAF8F5 bg)    */}
        {/* ======================================================== */}
        <div style={{
          flex: '1 1 42%',
          background: '#FAF8F5',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          height: 'calc(100vh - 190px)',
          minHeight: '480px',
          overflowY: 'auto',
          boxShadow: 'none',
          boxSizing: 'border-box'
        }}>
          {selectedClaim ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Header: Title and Options Icon */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '8px',
                borderBottom: '1px solid #E2E8F0'
              }}>
                <h3 style={{ margin: 0, fontSize: '1.02rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
                  {selectedTitle}
                </h3>
                <button
                  type="button"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#64748B',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Claim Inspector Options"
                >
                  <AlignRight size={16} />
                </button>
              </div>

              {/* Section 1: Claim details + Trust Score */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A' }}>
                    Claim details
                  </span>
                  <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#15803D' }}>
                    Trust Score {selectedTrustPercent}%
                  </span>
                </div>

                {/* 3 Input/Key-Value Boxes */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  {/* Subject */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    background: '#F3EFEA'
                  }}>
                    <span style={{ width: '75px', color: '#64748B', fontSize: '0.75rem', fontWeight: 500 }}>
                      Subject
                    </span>
                    <span style={{ color: '#0F172A', fontSize: '0.78rem', fontWeight: 600 }}>
                      {selectedClaim.subject || selectedClaim.data?.subject || 'Apparel'}
                    </span>
                  </div>

                  {/* Predicate */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    background: '#F3EFEA'
                  }}>
                    <span style={{ width: '75px', color: '#64748B', fontSize: '0.75rem', fontWeight: 500 }}>
                      Predicate
                    </span>
                    <span style={{ color: '#0F172A', fontSize: '0.78rem', fontWeight: 600 }}>
                      {selectedClaim.predicate || selectedClaim.data?.predicate || 'has_warranty_period'}
                    </span>
                  </div>

                  {/* Object */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    background: '#F3EFEA'
                  }}>
                    <span style={{ width: '75px', color: '#64748B', fontSize: '0.75rem', fontWeight: 500 }}>
                      Object
                    </span>
                    <span style={{ color: '#0F172A', fontSize: '0.78rem', fontWeight: 600 }}>
                      {selectedClaim.object || selectedClaim.data?.object || selectedClaim.fullText || selectedClaim.label || '1 year'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Section 2: Raw extracted claim */}
              <div>
                <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginBottom: '5px' }}>
                  Raw extracted claim
                </div>
                <div style={{
                  background: '#F3EFEA',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  padding: '10px 12px',
                  fontSize: '0.75rem',
                  lineHeight: '1.45',
                  color: '#334155'
                }}>
                  {selectedClaim.data?.evidence_snippet
                    || selectedClaim.data?.quote
                    || selectedClaim.data?.context_clause
                    || selectedClaim.fullText
                    || selectedClaim.label
                    || '| Apparel | 1 year | Replace or refund |'}
                </div>
              </div>

              {/* Section 3: Governance gates */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A' }}>
                    Governance gates
                  </span>
                  <span style={{ fontSize: '0.76rem', fontWeight: 800, color: '#15803D' }}>
                    {passedGatesCount}/10 passed
                  </span>
                </div>

                {/* 2-Column Gate Pills Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '5px'
                }}>
                  {STANDARD_GATES.map(gate => {
                    const isOk = getGateStatus(selectedClaim, gate);
                    return (
                      <div
                        key={gate.key}
                        style={{
                          background: isOk ? '#ECFDF5' : '#FEF2F2',
                          border: `1px solid ${isOk ? '#A7F3D0' : '#FECACA'}`,
                          borderRadius: '5px',
                          padding: '5px 7px',
                          fontSize: '0.69rem',
                          color: isOk ? '#065F46' : '#B91C1C',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                      >
                        <span style={{ color: isOk ? '#059669' : '#DC2626', fontWeight: 800 }}>
                          {isOk ? '✓' : '✗'}
                        </span>
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {gate.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Section 4: Metadata (Date ingested, Evidence, Owner) */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '8px',
                paddingTop: '6px',
                borderTop: '1px solid #E2E8F0'
              }}>
                <div>
                  <div style={{ fontSize: '0.69rem', color: '#94A3B8' }}>Date ingested</div>
                  <div style={{ fontSize: '0.75rem', color: '#334155', fontWeight: 600, marginTop: '1px' }}>
                    {formatDate(selectedClaim.created_at || selectedClaim.data?.created_at || asset?.node?.data?.created_at)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.69rem', color: '#94A3B8' }}>Evidence</div>
                  <div style={{ fontSize: '0.75rem', color: '#334155', fontWeight: 600, marginTop: '1px' }}>
                    {selectedClaim.data?.citation || selectedClaim.data?.page ? `Page ${selectedClaim.data.page}` : 'None'}
                  </div>
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <div style={{ fontSize: '0.69rem', color: '#94A3B8' }}>Owner</div>
                  <div style={{ fontSize: '0.75rem', color: '#334155', fontWeight: 600, marginTop: '1px' }}>
                    {selectedClaim.owner || selectedClaim.data?.owner || asset?.node?.data?.author || 'Jane Doe'}
                  </div>
                </div>
              </div>

              {/* Section 5: Claim actions */}
              <div>
                <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Claim actions
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
                  {/* Locate Source: Maps directly to the document in Document Explorer */}
                  <button
                    type="button"
                    onClick={handleLocateSource}
                    title="Open source document in Document Explorer"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 8px',
                      fontSize: '0.71rem',
                      fontWeight: 600,
                      color: '#0F172A',
                      background: '#FAF8F5',
                      border: '1px solid #CBD5E1',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F3EFEA'}
                    onMouseLeave={e => e.currentTarget.style.background = '#FAF8F5'}
                  >
                    <FileText size={11} color="#059669" />
                    <span>Locate Source</span>
                  </button>

                  {onLocateInDoc && (
                    <button
                      type="button"
                      onClick={() => onLocateInDoc(selectedClaim)}
                      title="Locate assertion in document reader"
                      style={{
                        padding: '4px 8px',
                        fontSize: '0.71rem',
                        fontWeight: 600,
                        color: '#0F172A',
                        background: '#FAF8F5',
                        border: '1px solid #CBD5E1',
                        borderRadius: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      Locate Claim
                    </button>
                  )}

                  {onInspectInDag && (
                    <button
                      type="button"
                      onClick={() => onInspectInDag(selectedClaim)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '0.71rem',
                        fontWeight: 600,
                        color: '#7C3AED',
                        background: '#F5F3FF',
                        border: '1px solid #DDD6FE',
                        borderRadius: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      Lineage DAG
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleCopyClaim(selectedClaim)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 8px',
                      fontSize: '0.71rem',
                      fontWeight: 600,
                      color: copiedClaimId === selectedClaim.id ? '#059669' : '#0F172A',
                      background: copiedClaimId === selectedClaim.id ? '#DCFCE7' : '#FAF8F5',
                      border: `1px solid ${copiedClaimId === selectedClaim.id ? '#86EFAC' : '#CBD5E1'}`,
                      borderRadius: '5px',
                      cursor: 'pointer'
                    }}
                  >
                    {copiedClaimId === selectedClaim.id ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copiedClaimId === selectedClaim.id ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              {/* Section 6: Escalate & Resolve Buttons */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '6px'
              }}>
                <button
                  type="button"
                  onClick={handleEscalate}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    color: '#0F172A',
                    background: '#FAF8F5',
                    border: '1px solid #CBD5E1',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F3EFEA'}
                  onMouseLeave={e => e.currentTarget.style.background = '#FAF8F5'}
                >
                  Escalate
                </button>

                <button
                  type="button"
                  onClick={handleResolve}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    color: '#FFFFFF',
                    background: '#15803D',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#166534'}
                  onMouseLeave={e => e.currentTarget.style.background = '#15803D'}
                >
                  Resolve
                </button>
              </div>
            </div>
          ) : (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#94A3B8' }}>
              Select a claim to inspect details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
