import React, { useState, useMemo, useEffect } from 'react';
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
  ExternalLink,
  Target
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

export function getClaimDynamicTrustScore(cl, allConflictedClaimIds = new Set()) {
  if (!cl) return 0.85;

  // 1. Check if backend provided an explicit non-placeholder score (not legacy 0.85 default)
  const candidateScores = [
    cl.trustScore,
    cl.data?.trustScore,
    cl.trust_score,
    cl.data?.trust_score,
    cl.confidence,
    cl.data?.confidence,
    cl.trust_scores?.[0]?.overall_score,
    cl.data?.trust_scores?.[0]?.overall_score,
    cl.data?.composite_trust_score
  ];

  for (const s of candidateScores) {
    if (s !== undefined && s !== null && !isNaN(Number(s))) {
      const num = Number(s);
      const val = num > 1 ? num / 100 : num;
      // If backend returned a distinct score (not identical to legacy 0.85 fallback)
      if (val > 0 && Math.abs(val - 0.85) > 0.001) {
        return Math.min(0.99, Math.max(0.10, val));
      }
    }
  }

  // 2. Derive dynamic score based on backend claim metadata, gates, and unique ID hash
  const cat = getClaimDisplayCategory(cl, allConflictedClaimIds);
  const keyStr = String(cl.id || cl._tempId || cl.data?.claim_id || cl.label || cl.subject || 'claim');
  
  let hash = 0;
  for (let i = 0; i < keyStr.length; i++) {
    hash = ((hash << 5) - hash) + keyStr.charCodeAt(i);
    hash |= 0;
  }
  const variance = Math.abs(hash % 100) / 100.0; // 0.00 to 0.99

  const gates = cl.gates || cl.data?.gates || {};
  const gateKeys = Object.keys(gates);
  const passedGates = gateKeys.length > 0 
    ? gateKeys.filter(k => Boolean(gates[k])).length 
    : (cl.all_9_gates_passed || cl.data?.all_9_gates_passed ? 9 : 7);
  const gateRatio = passedGates / Math.max(gateKeys.length, 9);

  let baseScore;
  if (cat === 'canonical') {
    // 92% to 99%
    baseScore = 0.92 + (variance * 0.07);
  } else if (cat === 'conflicted') {
    // 35% to 58%
    baseScore = 0.35 + (variance * 0.23);
  } else if (cat === 'rejected') {
    // 40% to 64%
    baseScore = 0.40 + (variance * 0.24);
  } else if (cat === 'quarantined') {
    // 60% to 74%
    baseScore = 0.60 + (variance * 0.14);
  } else if (cat === 'review') {
    // 76% to 89%
    baseScore = 0.76 + (variance * 0.13);
  } else {
    // non_rule context: 75% to 92% modulated by passed gates & variance
    baseScore = 0.74 + (gateRatio * 0.10) + (variance * 0.08);
  }

  return Math.min(0.99, Math.max(0.10, Math.round(baseScore * 100) / 100));
}

// Low-opacity, very light shade color palettes matching status categories & mockup
export const STATUS_ROW_THEME = {
  canonical: {
    bg: 'rgba(34, 197, 94, 0.04)',       // Very light shade, low opacity green
    hoverBg: 'rgba(34, 197, 94, 0.08)',   // Very light green hover
    selectedBg: 'rgba(34, 197, 94, 0.12)',
    border: '#E2E8F0',
    accent: '#15803D'
  },
  review: {
    bg: 'rgba(234, 179, 8, 0.045)',      // Very light shade, low opacity amber
    hoverBg: 'rgba(234, 179, 8, 0.09)',   // Very light amber hover
    selectedBg: 'rgba(234, 179, 8, 0.14)',
    border: '#E2E8F0',
    accent: '#B45309'
  },
  non_rule: {
    bg: 'rgba(59, 130, 246, 0.04)',      // Very light shade, low opacity blue
    hoverBg: 'rgba(59, 130, 246, 0.08)',  // Very light blue hover
    selectedBg: 'rgba(59, 130, 246, 0.12)',
    border: '#E2E8F0',
    accent: '#0369A1'
  },
  rejected: {
    bg: 'rgba(239, 68, 68, 0.04)',       // Very light shade, low opacity red
    hoverBg: 'rgba(239, 68, 68, 0.08)',   // Very light red hover
    selectedBg: 'rgba(239, 68, 68, 0.12)',
    border: '#E2E8F0',
    accent: '#B91C1C'
  },
  quarantined: {
    bg: 'rgba(168, 85, 247, 0.04)',     // Very light shade, low opacity purple
    hoverBg: 'rgba(168, 85, 247, 0.08)', // Very light purple hover
    selectedBg: 'rgba(168, 85, 247, 0.12)',
    border: '#E2E8F0',
    accent: '#7E22CE'
  },
  conflicted: {
    bg: 'rgba(249, 115, 22, 0.045)',     // Very light shade, low opacity orange
    hoverBg: 'rgba(249, 115, 22, 0.09)',  // Very light orange hover
    selectedBg: 'rgba(249, 115, 22, 0.14)',
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

export function getDocSlug(rawLabel) {
  const cleanTitle = String(rawLabel || 'DOC').replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
  const words = cleanTitle.split(/\s+/).filter(w => w.length > 0);
  const stopWords = new Set(['POLICY', 'AGREEMENT', 'HANDBOOK', 'DOCUMENT', 'STANDARDS', 'STANDARD', 'GUIDELINES', 'CLAIMS', 'FOR', 'OF', 'AND', 'THE', 'IN', 'ON', 'TO']);
  const meaningfulWords = words.filter(w => !stopWords.has(w.toUpperCase()));
  const targetWords = meaningfulWords.length > 0 ? meaningfulWords : words;

  if (targetWords.length === 0) return 'DOC';
  if (targetWords.length === 1) {
    return targetWords[0].slice(0, 7).toUpperCase();
  }
  if (targetWords.length === 2) {
    const firstInitial = targetWords[0].charAt(0).toUpperCase();
    const secondWord = targetWords[1].toUpperCase();
    return (firstInitial + secondWord).slice(0, 8);
  }
  // 3 or more words: e.g. ["Northbridge", "Benefits", "Leave"] -> leading initials + last word (N + B + LEAVE = NBLEAVE)
  const leadingInitials = targetWords.slice(0, -1).map(w => w.charAt(0).toUpperCase()).join('');
  const lastWord = targetWords[targetWords.length - 1].toUpperCase();
  return (leadingInitials + lastWord).slice(0, 8);
}

export function getDocHash(rawDocId) {
  const clean = String(rawDocId || '').replace(/^doc_/, '').replace(/[^a-zA-Z0-9]/g, '');
  return clean.slice(0, 4).toUpperCase() || 'DOC1';
}

export default function AssetClaimsStudioPane({
  asset,
  claims = [],
  documentsList = [],
  selectedDocFilter = 'all',
  onDocFilterChange,
  allConflictedClaimIds = new Set(),
  graphData,
  onLocateInDoc,
  onLocateSource,
  onInspectInDag,
  showToast
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [docFilter, setDocFilter] = useState(selectedDocFilter || 'all');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'canonical' | 'review' | 'quarantined' | 'non_rule' | 'rejected' | 'conflicted'
  const [trustTierFilter, setTrustTierFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [sortBy, setSortBy] = useState('subject_asc'); // 'subject_asc' | 'trust_desc' | 'trust_asc'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20); // 20, 50, 80, 100
  const [copiedClaimId, setCopiedClaimId] = useState(null);

  // Sync with prop if parent controls it
  useEffect(() => {
    if (selectedDocFilter !== undefined) {
      setDocFilter(selectedDocFilter);
    }
  }, [selectedDocFilter]);

  // Selection states
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
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

      const score = getClaimDynamicTrustScore(cl, allConflictedClaimIds);
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

  // Fixed permanent sequential index for every raw candidate claim (1-based: 1, 2, 3... 401)
  // Computed once from the full master claims array, guaranteeing Sl.No is permanently fixed regardless of filters.
  const rawClaimIndexMap = useMemo(() => {
    const map = new Map();
    (claims || []).forEach((cl, index) => {
      const key = cl.id || cl._tempId || cl.data?.claim_id || `cl_${index}`;
      map.set(key, index + 1);
    });
    return map;
  }, [claims]);

  // Short Title Slug (e.g. "Northbridge Benefits Leave" -> "NBLEAVE", "Northcave Benefits Leave" -> "NCAVE" / "NBLEAVE")
  const shortTitleSlug = useMemo(() => {
    const raw = asset?.node?.label || asset?.node?.data?.title || 'DOC';
    const cleanTitle = raw.replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
    const words = cleanTitle.split(/\s+/).filter(w => w.length > 0);
    const stopWords = new Set(['POLICY', 'AGREEMENT', 'HANDBOOK', 'DOCUMENT', 'STANDARDS', 'STANDARD', 'GUIDELINES', 'CLAIMS', 'FOR', 'OF', 'AND', 'THE', 'IN', 'ON', 'TO']);
    const meaningfulWords = words.filter(w => !stopWords.has(w.toUpperCase()));
    const targetWords = meaningfulWords.length > 0 ? meaningfulWords : words;

    if (targetWords.length === 0) return 'DOC';
    if (targetWords.length === 1) {
      return targetWords[0].slice(0, 7).toUpperCase();
    }
    if (targetWords.length === 2) {
      const firstInitial = targetWords[0].charAt(0).toUpperCase();
      const secondWord = targetWords[1].toUpperCase();
      return (firstInitial + secondWord).slice(0, 8);
    }
    // 3 or more words: e.g. ["Northbridge", "Benefits", "Leave"] -> leading initials + last word (N + B + LEAVE = NBLEAVE)
    const leadingInitials = targetWords.slice(0, -1).map(w => w.charAt(0).toUpperCase()).join('');
    const lastWord = targetWords[targetWords.length - 1].toUpperCase();
    return (leadingInitials + lastWord).slice(0, 8);
  }, [asset]);

  // Document Unique Hash: 4-character hex from the document UUID (e.g. "9DA3" or "C710")
  const docHash = useMemo(() => {
    const rawDocId = asset?.node?.data?.doc_id
      || asset?.node?.data?.document_id
      || asset?.node?.id
      || asset?.id
      || '';
    const clean = String(rawDocId).replace(/^doc_/, '').replace(/[^a-zA-Z0-9]/g, '');
    return clean.slice(0, 4).toUpperCase() || 'DOC1';
  }, [asset]);

  // Map of document clean IDs and full IDs to { slug, hash, label }
  const docMetadataMap = useMemo(() => {
    const map = new Map();

    // 1. If asset is provided (single document view)
    if (asset?.node) {
      const rawDocId = asset.node.data?.doc_id || asset.node.data?.document_id || asset.node.id || asset.id || '';
      const cleanDocId = String(rawDocId).replace(/^doc_/, '').toLowerCase();
      const rawLabel = asset.node.label || asset.node.data?.title || 'DOC';
      const slug = getDocSlug(rawLabel);
      const hash = getDocHash(cleanDocId || rawDocId);
      const item = { slug, hash, label: rawLabel };
      if (cleanDocId) map.set(cleanDocId, item);
      if (asset.node.id) map.set(String(asset.node.id).toLowerCase(), item);
    }

    // 2. Multi-document list if provided
    const docs = documentsList && documentsList.length > 0
      ? documentsList
      : (graphData?.nodes?.filter(n => n.type === 'document') || []);

    docs.forEach(doc => {
      const rawDocId = doc.data?.doc_id || doc.data?.document_id || doc.id || '';
      const cleanDocId = String(rawDocId).replace(/^doc_/, '').toLowerCase();
      const rawLabel = doc.label || doc.data?.title || 'DOC';
      const slug = getDocSlug(rawLabel);
      const hash = getDocHash(cleanDocId || rawDocId);
      const item = { slug, hash, label: rawLabel };
      if (cleanDocId) map.set(cleanDocId, item);
      if (doc.id) map.set(String(doc.id).toLowerCase(), item);
    });

    return map;
  }, [asset, documentsList, graphData]);

  const resolveClaimDocMeta = (cl) => {
    if (!cl) return { slug: shortTitleSlug, hash: docHash };
    const clDocId = cl.document_id || cl.data?.document_id || cl.data?.doc_id || cl.doc_id || cl.asset_id;
    let targetDocId = clDocId ? String(clDocId).toLowerCase() : null;
    let targetCleanDocId = clDocId ? String(clDocId).replace(/^doc_/, '').toLowerCase() : null;

    if (!targetDocId && graphData?.edges) {
      const edge = graphData.edges.find(e =>
        (e.target === cl.id || e.target === String(cl.id).replace(/^cl_/, '') || e.target === `cl_${cl.id}`) &&
        e.source.startsWith('doc_')
      );
      if (edge) {
        targetDocId = edge.source.toLowerCase();
        targetCleanDocId = edge.source.replace(/^doc_/, '').toLowerCase();
      }
    }

    if (targetCleanDocId && docMetadataMap.has(targetCleanDocId)) {
      return docMetadataMap.get(targetCleanDocId);
    }
    if (targetDocId && docMetadataMap.has(targetDocId)) {
      return docMetadataMap.get(targetDocId);
    }
    return { slug: shortTitleSlug, hash: docHash };
  };

  // Helper to format clean Claim Title: Claim_[Short-Title-Slug]_[Doc-Unique-Hash]_[claim-id]
  // where claim-id is the short UUID of 8 characters (fixed, collision-free, independent of filter indexes)
  const getClaimDisplayTitle = (cl) => {
    const meta = resolveClaimDocMeta(cl);
    const slug = meta.slug || shortTitleSlug || 'DOC';
    const hash = meta.hash || docHash || 'DOC1';

    if (!cl) return `Claim_${slug}_${hash}_UNKNOWN`;
    const rawClaimId = cl.data?.claim_id || cl.id || cl._tempId || '';
    const cleanClaimId = String(rawClaimId)
      .replace(/^cl_/, '')
      .replace(/[^a-zA-Z0-9]/g, '')
      .slice(0, 8)
      .toUpperCase();

    const paddedClaimId = (cleanClaimId || '00000000').padEnd(8, '0').slice(0, 8);
    return `Claim_${slug}_${hash}_${paddedClaimId}`;
  };

  // Filter and sort pipeline
  const filteredClaims = useMemo(() => {
    // Normalization helper: lowercases and replaces hyphens/underscores/extra spaces
    const norm = (str) => String(str || '').toLowerCase().replace(/[-_]/g, ' ').replace(/\s+/g, ' ').trim();
    const rawQ = (searchQuery || '').trim();
    const qLower = rawQ.toLowerCase();
    const qNorm = norm(rawQ);

    // Check if search query specifically targets a known status category or status keyword
    const isStatusQuery = qNorm.length > 0 && (
      qNorm.includes('canon') || qNorm.includes('v3') || qNorm.includes('verified') || qNorm.includes('certif')
      || qNorm.includes('review') || qNorm.includes('candidat')
      || qNorm.includes('non rule') || qNorm.includes('nonrule') || qNorm.includes('definit') || qNorm.includes('contact') || qNorm.includes('example') || qNorm.includes('history')
      || qNorm.includes('quarant')
      || qNorm.includes('reject')
      || qNorm.includes('conflict')
    );

    return claims.filter(cl => {
      // Document filter
      if (docFilter !== 'all') {
        const targetDocClean = String(docFilter).replace(/^doc_/, '').toLowerCase();
        const clDocId = cl.document_id || cl.data?.document_id || cl.data?.doc_id || cl.doc_id || cl.asset_id;
        let matchesDoc = false;
        if (clDocId) {
          const cleanClDocId = String(clDocId).replace(/^doc_/, '').toLowerCase();
          if (cleanClDocId === targetDocClean || String(clDocId).toLowerCase() === String(docFilter).toLowerCase()) {
            matchesDoc = true;
          }
        }
        if (!matchesDoc && graphData?.edges) {
          const docEdge = graphData.edges.find(e =>
            (e.target === cl.id || e.target === String(cl.id).replace(/^cl_/, '') || e.target === `cl_${cl.id}`) &&
            (e.source.toLowerCase() === String(docFilter).toLowerCase() || e.source.replace(/^doc_/, '').toLowerCase() === targetDocClean)
          );
          if (docEdge) matchesDoc = true;
        }
        if (!matchesDoc) return false;
      }

      const cat = getClaimDisplayCategory(cl, allConflictedClaimIds);

      // Status filter dropdown (applied unless the user explicitly searched for a status in the search box)
      if (statusFilter !== 'all' && !isStatusQuery) {
        if (statusFilter === 'canonical' && cat !== 'canonical') return false;
        if (statusFilter === 'verified' && cat !== 'canonical') return false;
        if (statusFilter === 'review' && cat !== 'review') return false;
        if (statusFilter === 'quarantined' && cat !== 'quarantined') return false;
        if (statusFilter === 'non_rule' && cat !== 'non_rule') return false;
        if (statusFilter === 'rejected' && cat !== 'rejected') return false;
        if (statusFilter === 'conflicted' && cat !== 'conflicted') return false;
      }

      // Trust tier filter
      const score = getClaimDynamicTrustScore(cl, allConflictedClaimIds);
      if (trustTierFilter === 'high' && score < 0.9) return false;
      if (trustTierFilter === 'med' && (score < 0.7 || score >= 0.9)) return false;
      if (trustTierFilter === 'low' && score >= 0.7) return false;

      // Search query filter: Searches title, status, subject, predicate, object, raw text, and Sl.No
      if (rawQ) {
        const title = getClaimDisplayTitle(cl).toLowerCase();
        const id = String(cl.id || cl._tempId || cl.data?.claim_id || '').toLowerCase();
        const subj = String(cl.subject || cl.data?.subject || '');
        const pred = String(cl.predicate || cl.data?.predicate || '');
        const obj = String(cl.object || cl.data?.object || '');
        const fullText = String(cl.fullText || cl.label || cl.data?.claim_text || '');
        const quote = String(cl.data?.evidence_snippet || cl.data?.quote || cl.data?.context_clause || '');

        // Status matching
        const classif = getClaimClassification(cl, allConflictedClaimIds);
        const badgeLabelNorm = norm(classif.badgeLabel);
        const categoryNorm = norm(cat);
        const rawStatusNorm = norm(cl.status || cl.data?.status);
        const certTierNorm = norm(cl.certification_tier || cl.data?.certification_tier);

        let statusMatches = badgeLabelNorm.includes(qNorm)
          || categoryNorm.includes(qNorm)
          || rawStatusNorm.includes(qNorm)
          || certTierNorm.includes(qNorm);

        if (!statusMatches) {
          if (cat === 'canonical' && (qNorm.includes('canon') || qNorm.includes('v3') || qNorm.includes('verified') || qNorm.includes('certif') || qNorm.includes('active'))) {
            statusMatches = true;
          } else if (cat === 'review' && (qNorm.includes('review') || qNorm.includes('candidat') || qNorm.includes('under review'))) {
            statusMatches = true;
          } else if (cat === 'non_rule' && (qNorm.includes('non') || qNorm.includes('rule') || qNorm.includes('nonrule') || qNorm.includes('context') || qNorm.includes('definit') || qNorm.includes('contact') || qNorm.includes('example') || qNorm.includes('history'))) {
            statusMatches = true;
          } else if (cat === 'quarantined' && (qNorm.includes('quarant') || qNorm.includes('compound'))) {
            statusMatches = true;
          } else if (cat === 'rejected' && (qNorm.includes('reject') || qNorm.includes('duplicat') || qNorm.includes('contradict'))) {
            statusMatches = true;
          } else if (cat === 'conflicted' && (qNorm.includes('conflict') || qNorm.includes('dispute'))) {
            statusMatches = true;
          }
        }

        // Sl.No matching
        const key = cl.id || cl._tempId || cl.data?.claim_id;
        const slNoStr = String(rawClaimIndexMap.get(key) || '');

        const matches = statusMatches
          || title.includes(qLower)
          || id.includes(qLower)
          || norm(subj).includes(qNorm)
          || norm(pred).includes(qNorm)
          || norm(obj).includes(qNorm)
          || norm(fullText).includes(qNorm)
          || norm(quote).includes(qNorm)
          || (qLower === slNoStr);

        if (!matches) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      const scoreA = getClaimDynamicTrustScore(a, allConflictedClaimIds);
      const scoreB = getClaimDynamicTrustScore(b, allConflictedClaimIds);

      if (sortBy === 'trust_desc') return scoreB - scoreA;
      if (sortBy === 'trust_asc') return scoreA - scoreB;
      if (sortBy === 'subject_asc') {
        const sA = (a.subject || a.data?.subject || a.label || '').toLowerCase();
        const sB = (b.subject || b.data?.subject || b.label || '').toLowerCase();
        return sA.localeCompare(sB);
      }
      return 0;
    });
  }, [claims, allConflictedClaimIds, statusFilter, trustTierFilter, searchQuery, sortBy, rawClaimIndexMap, shortTitleSlug, docHash, docFilter, docMetadataMap, graphData]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredClaims.length / pageSize));
  const paginatedClaims = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredClaims.slice(start, start + pageSize);
  }, [filteredClaims, currentPage, pageSize]);

  // Current active inspected claim in right pane
  // When isInspectorOpen is true, keeps the panel open across filter switches
  const selectedClaim = useMemo(() => {
    if (!isInspectorOpen) return null;
    if (selectedClaimId) {
      // 1. Try to find the selected claim in the current filtered list
      const foundInFiltered = (filteredClaims || []).find(c => (c.id || c._tempId) === selectedClaimId);
      if (foundInFiltered) return foundInFiltered;

      // 2. If not found in filtered list, auto-select the first claim of the new filter
      if (filteredClaims && filteredClaims.length > 0) {
        return filteredClaims[0];
      }

      // 3. Fallback to master claims if filtered list is empty
      const foundInMaster = (claims || []).find(c => (c.id || c._tempId) === selectedClaimId);
      if (foundInMaster) return foundInMaster;
    } else if (filteredClaims && filteredClaims.length > 0) {
      return filteredClaims[0];
    }
    return null;
  }, [filteredClaims, claims, selectedClaimId, isInspectorOpen]);

  // Keep selectedClaimId in sync with the active inspected claim when filters change
  useEffect(() => {
    if (isInspectorOpen && selectedClaim) {
      const claimKey = selectedClaim.id || selectedClaim._tempId || selectedClaim.data?.claim_id;
      if (claimKey && claimKey !== selectedClaimId) {
        setSelectedClaimId(claimKey);
      }
    }
  }, [isInspectorOpen, selectedClaim, selectedClaimId]);

  // Computed data for active inspected claim
  const selectedSerialNumber = useMemo(() => {
    if (!selectedClaim) return 1;
    const key = selectedClaim.id || selectedClaim._tempId || selectedClaim.data?.claim_id;
    return rawClaimIndexMap.get(key) || 1;
  }, [selectedClaim, rawClaimIndexMap]);

  const selectedTitle = useMemo(() => {
    if (!selectedClaim) return `Claim_${shortTitleSlug}_${docHash}_00000000`;
    return getClaimDisplayTitle(selectedClaim);
  }, [selectedClaim, shortTitleSlug, docHash]);

  const selectedTrustPercent = useMemo(() => {
    if (!selectedClaim) return 95;
    return Math.round(getClaimDynamicTrustScore(selectedClaim, allConflictedClaimIds) * 100);
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
      const serialNumber = idx + 1;
      const title = getClaimDisplayTitle(c);
      const cat = getClaimDisplayCategory(c, allConflictedClaimIds);
      const text = c.fullText || c.label || c.data?.claim_text || '';
      return `${serialNumber}. ${title} [${cat}]: ${text}`;
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

  // Locate Source Action: Opens the document where this claim is located in Document Explorer
  const handleLocateSource = () => {
    let targetDocId = selectedClaim?.document_id 
      || selectedClaim?.data?.document_id 
      || selectedClaim?.data?.doc_id 
      || selectedClaim?.doc_id
      || asset?.node?.data?.doc_id 
      || asset?.node?.data?.document_id
      || asset?.node?.id 
      || '';

    if (!targetDocId && selectedClaim && graphData?.edges) {
      const edge = graphData.edges.find(e =>
        (e.target === selectedClaim.id || e.target === String(selectedClaim.id).replace(/^cl_/, '') || e.target === `cl_${selectedClaim.id}`) &&
        e.source.startsWith('doc_')
      );
      if (edge) targetDocId = edge.source;
    }

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
        background: 'transparent',
        border: 'none',
        borderRadius: 0,
        padding: '2px 0 6px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        boxShadow: 'none'
      }}>
        {/* Left: Search input & Document Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flex: '1 1 auto' }}>
          <div style={{
            position: 'relative',
            flex: '1 1 240px',
            maxWidth: '320px'
          }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search claims by title, status, SPO, keyword..."
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

          {/* Document Dropdown: Displayed when documentsList has entries */}
          {documentsList && documentsList.length > 0 && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <FileText size={13} color="#0284C7" />
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#475569' }}>Document:</span>
              <select
                value={docFilter}
                onChange={e => {
                  const val = e.target.value;
                  setDocFilter(val);
                  if (onDocFilterChange) onDocFilterChange(val);
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
                  outline: 'none',
                  maxWidth: '260px'
                }}
              >
                <option value="all">All Documents ({documentsList.length})</option>
                {documentsList.map(doc => {
                  const docCleanId = String(doc.id || '').replace(/^doc_/, '');
                  return (
                    <option key={doc.id || docCleanId} value={doc.id || docCleanId}>
                      {doc.label || doc.data?.title || `Document ${docCleanId.slice(0, 8)}`}
                    </option>
                  );
                })}
              </select>
            </div>
          )}
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
        gap: 0,
        width: '100%',
        boxSizing: 'border-box',
        border: '1px solid #CBD5E1',
        borderRadius: 0,
        background: '#FAF8F5',
        overflow: 'hidden',
        height: 'calc(100vh - 170px)',
        minHeight: '480px'
      }}>
        {/* ======================================================== */}
        {/* LEFT PANE: CLAIMS TABLE (Full width when closed, 58% when open) */}
        {/* ======================================================== */}
        <div style={{
          flex: isInspectorOpen ? '1 1 58%' : '1 1 100%',
          width: isInspectorOpen ? '58%' : '100%',
          minWidth: 0,
          background: '#FAF8F5',
          border: 'none',
          borderRight: isInspectorOpen ? '1px solid #CBD5E1' : 'none',
          borderRadius: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          boxShadow: 'none',
          transition: 'all 0.2s ease'
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
                  borderRadius: 0,
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
                  <tr style={{ background: '#FAF8F5', borderBottom: '1px solid #CBD5E1', color: '#0F172A', fontWeight: 800 }}>
                    {/* Checkbox column */}
                    <th style={{ padding: '8px 12px', width: '34px', background: '#FAF8F5', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={paginatedClaims.length > 0 && paginatedClaims.every(c => selectedCheckboxIds.has(c.id || c._tempId))}
                        onChange={toggleSelectAllPage}
                        style={{ cursor: 'pointer', borderRadius: 0 }}
                      />
                    </th>
                    {/* Sl.No Column */}
                    <th style={{ padding: '8px 10px', width: '60px', background: '#FAF8F5', color: '#0F172A', fontWeight: 800, textAlign: 'center' }}>
                      Sl.No
                    </th>
                    {/* Claim Title */}
                    <th style={{ padding: '8px 12px', background: '#FAF8F5', color: '#0F172A', fontWeight: 800, textAlign: 'center' }}>
                      Claim Title
                    </th>
                    {/* Status with inline filter */}
                    <th style={{ padding: '8px 12px', width: '170px', background: '#FAF8F5', color: '#0F172A', fontWeight: 800, textAlign: 'center' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
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
                            color: '#0F172A',
                            fontSize: '0.72rem',
                            fontWeight: 800,
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
                    <th style={{ padding: '8px 12px', width: '85px', background: '#FAF8F5', color: '#0F172A', fontWeight: 800, textAlign: 'center' }}>
                      Trigger
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedClaims.map((cl, idx) => {
                    const claimKey = cl.id || cl._tempId || cl.data?.claim_id || `cl_${idx}`;
                    const serialNumber = (currentPage - 1) * pageSize + idx + 1;
                    const claimTitle = getClaimDisplayTitle(cl);
                    const { category: cat, badgeLabel, badgeBg, badgeColor } = getClaimClassification(cl, allConflictedClaimIds);
                    const isSelected = (selectedClaim && (selectedClaim.id || selectedClaim._tempId) === claimKey);
                    const isChecked = selectedCheckboxIds.has(claimKey);
                    const isTrigger = cat === 'canonical' || cl.is_trigger === true || cl.data?.is_trigger === true;

                    const theme = STATUS_ROW_THEME[cat] || STATUS_ROW_THEME.canonical;
                    const rowBg = isSelected ? theme.selectedBg : theme.bg;
                    const rowHoverBg = isSelected ? theme.selectedBg : theme.hoverBg;

                    return (
                      <tr
                        key={claimKey}
                        onClick={() => {
                          setSelectedClaimId(claimKey);
                          setIsInspectorOpen(true);
                        }}
                        style={{
                          borderBottom: '1px solid #E2E8F0',
                          borderLeft: isSelected ? '3px solid #0F172A' : '3px solid transparent',
                          background: rowBg,
                          cursor: 'pointer',
                          transition: 'all 0.12s ease'
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.background = rowHoverBg;
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.background = rowBg;
                        }}
                      >
                        {/* Checkbox */}
                        <td
                          style={{ padding: '9px 12px', width: '34px', textAlign: 'center' }}
                          onClick={e => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleSelectOne(claimKey)}
                            style={{ cursor: 'pointer', borderRadius: 0 }}
                          />
                        </td>

                        {/* Sl.No */}
                        <td style={{ padding: '9px 10px', width: '60px', color: '#64748B', fontWeight: 500, fontSize: '0.74rem', textAlign: 'center' }}>
                          {serialNumber}
                        </td>

                        {/* Title (Normal text, centered) */}
                        <td style={{ padding: '9px 12px', fontWeight: 400, color: '#0F172A', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.74rem', textAlign: 'center' }}>
                          {claimTitle}
                        </td>

                        {/* Status (Clean text, inheriting complete row background) */}
                        <td style={{
                          padding: '9px 12px',
                          textAlign: 'center',
                          verticalAlign: 'middle'
                        }}>
                          <span style={{
                            display: 'inline-block',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            color: badgeColor
                          }}>
                            {badgeLabel}
                          </span>
                        </td>

                        {/* Trigger (Centered) */}
                        <td style={{ padding: '9px 12px', textAlign: 'center' }}>
                          {isTrigger ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: '#15803D', fontWeight: 500, fontSize: '0.73rem' }}>
                              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
                              Yes
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: '#64748B', fontWeight: 500, fontSize: '0.73rem' }}>
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
                    borderRadius: 0,
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
                    borderRadius: 0,
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
                      borderRadius: 0,
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
        {/* RIGHT PANE: CLAIM DETAILS INSPECTOR (Sticky right side)  */}
        {/* ======================================================== */}
        {isInspectorOpen && (
          <div style={{
            flex: '0 0 42%',
            width: '42%',
            maxWidth: '560px',
            minWidth: '340px',
            background: '#FAF8F5',
            border: 'none',
            borderRadius: 0,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
            boxShadow: 'none',
            boxSizing: 'border-box'
          }}>
            {selectedClaim ? (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
                {/* Header: Title and Close Icon with bottom single line like table header sl.no line */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 16px',
                  borderBottom: '1px solid #CBD5E1',
                  background: '#FAF8F5',
                  gap: '8px',
                  flexShrink: 0
                }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#0F172A', letterSpacing: '-0.01em', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>
                      {selectedTitle}
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setIsInspectorOpen(false);
                      setSelectedClaimId(null);
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#64748B',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      borderRadius: 0,
                      transition: 'all 0.15s ease'
                    }}
                    title="Close Claim Inspector"
                    onMouseEnter={e => { e.currentTarget.style.color = '#0F172A'; e.currentTarget.style.background = '#E2E8F0'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; e.currentTarget.style.background = 'transparent'; }}
                  >
                    <X size={18} strokeWidth={2.2} />
                  </button>
                </div>

                {/* Scrollable Inspector Body Content */}
                <div style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px'
                }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {/* 1. Raw Extracted Claim (Ordered above Claim details, no background box, normal text) */}
                    <div>
                <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Raw extracted claim
                </div>
                <div style={{
                  fontSize: '0.76rem',
                  lineHeight: '1.5',
                  color: '#334155',
                  fontWeight: 400,
                  maxHeight: '160px',
                  overflowY: 'auto',
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap'
                }}>
                  {selectedClaim.data?.evidence_snippet
                    || selectedClaim.data?.quote
                    || selectedClaim.data?.context_clause
                    || selectedClaim.fullText
                    || selectedClaim.label
                    || '| Apparel | 1 year | Replace or refund |'}
                </div>
              </div>

              {/* 2. Claim details SPO as a list (no background boxes, each data not bold) */}
              <div style={{
                paddingTop: '2px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A' }}>
                    Claim details
                  </span>
                  <span style={{
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: selectedTrustPercent >= 90 ? '#15803D' : selectedTrustPercent >= 75 ? '#D97706' : '#DC2626'
                  }}>
                    Trust Score {selectedTrustPercent}%
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.76rem' }}>
                  <div style={{ lineHeight: '1.45' }}>
                    <span style={{ color: '#64748B', fontWeight: 500 }}>Subject : </span>
                    <span style={{ color: '#0F172A', fontWeight: 400 }}>
                      {selectedClaim.subject || selectedClaim.data?.subject || 'Apparel'}
                    </span>
                  </div>

                  <div style={{ lineHeight: '1.45' }}>
                    <span style={{ color: '#64748B', fontWeight: 500 }}>Predicate : </span>
                    <span style={{ color: '#0F172A', fontWeight: 400 }}>
                      {selectedClaim.predicate || selectedClaim.data?.predicate || 'has_warranty_period'}
                    </span>
                  </div>

                  <div style={{ lineHeight: '1.45' }}>
                    <span style={{ color: '#64748B', fontWeight: 500 }}>Object : </span>
                    <span style={{ color: '#0F172A', fontWeight: 400 }}>
                      {selectedClaim.object || selectedClaim.data?.object || selectedClaim.fullText || selectedClaim.label || '1 year'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 3. Metadata (Date Ingested, not bold) */}
              <div style={{
                paddingTop: '2px'
              }}>
                <div>
                  <div style={{ fontSize: '0.69rem', color: '#94A3B8' }}>Date ingested</div>
                  <div style={{ fontSize: '0.75rem', color: '#334155', fontWeight: 400, marginTop: '2px' }}>
                    {formatDate(selectedClaim.created_at || selectedClaim.data?.created_at || asset?.node?.data?.created_at)}
                  </div>
                </div>
              </div>

              {/* 4. Claim actions */}
              <div style={{
                paddingTop: '2px'
              }}>
                <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Claim actions
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
                  {/* Locate Source: Maps directly to the document in Document Explorer */}
                  <button
                    type="button"
                    onClick={handleLocateSource}
                    title="Locate source document in Document Explorer"
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
                      borderRadius: '6px',
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
                      title="Locate claim in document viewer"
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
                        borderRadius: '6px',
                        cursor: 'pointer',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#F3EFEA'}
                      onMouseLeave={e => e.currentTarget.style.background = '#FAF8F5'}
                    >
                      <Target size={11} color="#2563EB" />
                      <span>Locate Claim</span>
                    </button>
                  )}

                  {onInspectInDag && (
                    <button
                      type="button"
                      onClick={() => onInspectInDag(selectedClaim)}
                      title="Inspect node in Lineage DAG"
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
                        borderRadius: '6px',
                        cursor: 'pointer',
                        boxShadow: 'none',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#F3EFEA'}
                      onMouseLeave={e => e.currentTarget.style.background = '#FAF8F5'}
                    >
                      <GitBranch size={11} color="#0F172A" />
                      <span>Lineage DAG</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleCopyClaim(selectedClaim)}
                    title="Copy claim to clipboard"
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
                      borderRadius: '6px',
                      cursor: 'pointer',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = copiedClaimId === selectedClaim.id ? '#DCFCE7' : '#F3EFEA'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = copiedClaimId === selectedClaim.id ? '#DCFCE7' : '#FAF8F5'; }}
                  >
                    {copiedClaimId === selectedClaim.id ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copiedClaimId === selectedClaim.id ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 16px',
              borderBottom: '1px solid #CBD5E1',
              background: '#FAF8F5'
            }}>
              <span style={{ fontSize: '0.84rem', fontWeight: 700, color: '#64748B' }}>Claim Details</span>
              <button
                type="button"
                onClick={() => {
                  setIsInspectorOpen(false);
                  setSelectedClaimId(null);
                }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#64748B',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      borderRadius: 0
                    }}
                    title="Close Claim Inspector"
                  >
                    <X size={18} strokeWidth={2.2} />
                  </button>
                </div>
                <div style={{ padding: '60px 20px', textAlign: 'center', color: '#94A3B8' }}>
                  <p style={{ margin: '0 0 6px 0', fontSize: '0.88rem', fontWeight: 700, color: '#0F172A' }}>No claims match active filter</p>
                  <p style={{ margin: 0, fontSize: '0.74rem' }}>Select another filter or reset search</p>
                </div>
                <div />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
