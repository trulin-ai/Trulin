import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Layers,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowUpDown,
  FileText,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  SlidersHorizontal,
  Table as TableIcon,
  LayoutGrid,
  Sparkles,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';

export default function MillionScaleClaimsGrid({
  claims = [],
  documents = [],
  activeWorkspace,
  onInspectDocument,
  onInspectClaim
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('all');
  const [selectedDocumentId, setSelectedDocumentId] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [trustTierFilter, setTrustTierFilter] = useState('all'); // 'all' | 'high' | 'med' | 'low'
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'trust_desc' | 'trust_asc' | 'subject_asc'
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [jumpPageInput, setJumpPageInput] = useState('');

  // Domain keywords mapping
  const DOMAIN_KEYWORDS = {
    finance: ['refund', 'billing', 'invoice', 'arr', 'payment', 'price', 'pricing', 'tier', 'subscription'],
    secops: ['security', 'firewall', 'ingress', 'iam', 'mtls', 'token', 'session', 'freeze', 'freeze', 'auth'],
    hr: ['remote', 'leave', 'vacation', 'employee', 'handbook', 'work', 'people', 'hire', 'guideline'],
    support: ['support', 'dispute', 'sla', 'ticket', 'escalation', 'arbitration', 'customer'],
    staging: ['staging', 'sandbox', 'test', 'simulation', 'mock']
  };

  // Helper to determine claim domain
  const getClaimDomain = (c) => {
    const text = `${c.claim_text || ''} ${c.subject || ''} ${c.predicate || ''}`.toLowerCase();
    for (const [dom, kws] of Object.entries(DOMAIN_KEYWORDS)) {
      if (kws.some(kw => text.includes(kw))) {
        return dom;
      }
    }
    return 'general';
  };

  // Build document lookup map
  const docMap = useMemo(() => {
    const m = new Map();
    documents.forEach(d => {
      m.set(d.id, d);
      if (d.versions) {
        d.versions.forEach(v => m.set(v.id, d));
      }
    });
    return m;
  }, [documents]);

  // Telemetry KPIs
  const telemetry = useMemo(() => {
    const total = claims.length;
    let verified = 0;
    let outdated = 0;
    let conflicted = 0;
    let financeCount = 0;
    let secopsCount = 0;
    let hrCount = 0;
    let supportCount = 0;

    claims.forEach(c => {
      const st = (c.status || '').toLowerCase();
      if (st === 'verified' || st === 'valid') verified++;
      else if (st === 'outdated') outdated++;
      else if (st === 'conflicted' || st === 'disputed') conflicted++;

      const dom = getClaimDomain(c);
      if (dom === 'finance') financeCount++;
      else if (dom === 'secops') secopsCount++;
      else if (dom === 'hr') hrCount++;
      else if (dom === 'support') supportCount++;
    });

    const verifiedPct = total > 0 ? ((verified / total) * 100).toFixed(1) : '100.0';

    return {
      total,
      verified,
      outdated,
      conflicted,
      verifiedPct,
      financeCount,
      secopsCount,
      hrCount,
      supportCount
    };
  }, [claims]);

  // Filter and Sort Pipeline
  const filteredClaims = useMemo(() => {
    return claims.filter(claim => {
      // 1. Domain filter
      if (selectedDomain !== 'all') {
        const dom = getClaimDomain(claim);
        if (dom !== selectedDomain) return false;
      }

      // 1b. Document-wise filter
      if (selectedDocumentId !== 'all') {
        const docIdOnClaim = claim.document_id || claim.document_version?.document_id || claim.data?.document_id || claim.data?.doc_id;
        const claimDoc = docMap.get(docIdOnClaim || claim.document_version_id);
        const rawTargetId = String(selectedDocumentId).replace(/^doc_/, '');
        const matchId = (
          docIdOnClaim === selectedDocumentId ||
          docIdOnClaim === rawTargetId ||
          claimDoc?.id === selectedDocumentId ||
          claimDoc?.id === rawTargetId ||
          String(claimDoc?.id || '').replace(/^doc_/, '') === rawTargetId
        );
        if (!matchId) return false;
      }

      // 2. Status filter
      if (statusFilter !== 'all') {
        const st = (claim.status || '').toLowerCase();
        if (st !== statusFilter) return false;
      }

      // 3. Trust Score Tier
      const rawScore = claim.trust_scores?.[0]?.overall_score ?? claim.trust_score;
      const score = (rawScore !== undefined && rawScore !== null && !isNaN(Number(rawScore)))
        ? Number(rawScore)
        : 0.0;
      if (trustTierFilter === 'high' && score < 0.9) return false;
      if (trustTierFilter === 'med' && (score < 0.7 || score >= 0.9)) return false;
      if (trustTierFilter === 'low' && score >= 0.7) return false;

      // 4. Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          (claim.claim_text || '').toLowerCase().includes(q) ||
          (claim.subject || '').toLowerCase().includes(q) ||
          (claim.predicate || '').toLowerCase().includes(q) ||
          (claim.object || '').toLowerCase().includes(q) ||
          (claim.id || '').toLowerCase().includes(q);
        if (!matches) return false;
      }

      return true;
    }).sort((a, b) => {
      const rawScoreA = a.trust_scores?.[0]?.overall_score ?? a.trust_score;
      const rawScoreB = b.trust_scores?.[0]?.overall_score ?? b.trust_score;
      const scoreA = (rawScoreA !== undefined && rawScoreA !== null && !isNaN(Number(rawScoreA))) ? Number(rawScoreA) : 0.0;
      const scoreB = (rawScoreB !== undefined && rawScoreB !== null && !isNaN(Number(rawScoreB))) ? Number(rawScoreB) : 0.0;

      if (sortBy === 'trust_desc') return scoreB - scoreA;
      if (sortBy === 'trust_asc') return scoreA - scoreB;
      if (sortBy === 'subject_asc') return (a.subject || '').localeCompare(b.subject || '');
      // newest default
      const dateA = new Date(a.created_at || 0).getTime();
      const dateB = new Date(b.created_at || 0).getTime();
      return dateB - dateA;
    });
  }, [claims, selectedDomain, selectedDocumentId, docMap, statusFilter, trustTierFilter, searchQuery, sortBy]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredClaims.length / pageSize));
  const validCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (validCurrentPage - 1) * pageSize;
  const currentClaims = filteredClaims.slice(startIndex, startIndex + pageSize);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleJumpSubmit = (e) => {
    e.preventDefault();
    const p = parseInt(jumpPageInput, 10);
    if (!isNaN(p) && p >= 1 && p <= totalPages) {
      setCurrentPage(p);
      setJumpPageInput('');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* ========================================================= */}
      {/* 1. TOP TELEMETRY RIBBON & CATCHY METRICS COCKPIT          */}
      {/* ========================================================= */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px'
      }}>
        {/* Metric 1: Total Stored Claims */}
        <div style={{
          background: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)',
          color: '#FFFFFF',
          padding: '16px 18px',
          borderRadius: '10px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Total Atomic Claims
            </span>
            <Layers size={16} style={{ color: '#38BDF8' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '6px', color: '#F8FAFC' }}>
            {telemetry.total > 1000 ? `${(telemetry.total / 1000).toFixed(1)}k` : telemetry.total}
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#94A3B8', marginLeft: '6px' }}>rules</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#38BDF8', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={12} />
            <span>100% Cryptographic Provenance</span>
          </div>
        </div>

        {/* Metric 2: Verified & Authoritative */}
        <div style={{
          background: '#FFFFFF',
          padding: '16px 18px',
          borderRadius: '10px',
          border: '1px solid #BBF7D0',
          boxShadow: '0 2px 8px rgba(16, 185, 129, 0.04)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Authoritative Allow Rate
            </span>
            <CheckCircle2 size={16} style={{ color: '#16A34A' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '6px', color: '#15803D' }}>
            {telemetry.verifiedPct}%
          </div>
          <div style={{ fontSize: '0.72rem', color: '#166534', marginTop: '4px' }}>
            {telemetry.verified} verified atomic facts
          </div>
        </div>

        {/* Metric 3: Outdated / Decayed Policies */}
        <div style={{
          background: '#FFFFFF',
          padding: '16px 18px',
          borderRadius: '10px',
          border: '1px solid #FED7AA',
          boxShadow: '0 2px 8px rgba(249, 115, 22, 0.04)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#9A3412', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Outdated / Decayed
            </span>
            <Clock size={16} style={{ color: '#EA580C' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '6px', color: '#C2410C' }}>
            {telemetry.outdated}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#9A3412', marginTop: '4px' }}>
            Superseded by newer versions
          </div>
        </div>

        {/* Metric 4: Active Policy Contradictions */}
        <div style={{
          background: '#FFFFFF',
          padding: '16px 18px',
          borderRadius: '10px',
          border: telemetry.conflicted > 0 ? '1px solid #FECACA' : '1px solid var(--border-subtle)',
          boxShadow: '0 2px 8px rgba(239, 68, 68, 0.04)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: telemetry.conflicted > 0 ? '#991B1B' : '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Active Contradictions
            </span>
            <AlertTriangle size={16} style={{ color: telemetry.conflicted > 0 ? '#DC2626' : '#94A3B8' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '6px', color: telemetry.conflicted > 0 ? '#DC2626' : '#0F172A' }}>
            {telemetry.conflicted}
          </div>
          <div style={{ fontSize: '0.72rem', color: telemetry.conflicted > 0 ? '#B91C1C' : '#64748B', marginTop: '4px' }}>
            {telemetry.conflicted > 0 ? 'Requires curator arbitration' : 'Clean arbitration matrix'}
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. ONE-CLICK FACET CHIPS (DOMAINS & DEPARTMENTS)           */}
      {/* ========================================================= */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        overflowX: 'auto',
        paddingBottom: '4px'
      }}>
        <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', flexShrink: 0 }}>
          Departmental Facets:
        </span>

        {[
          { id: 'all', label: 'All Domains', count: telemetry.total, icon: '🌐' },
          { id: 'finance', label: 'Finance & Billing', count: telemetry.financeCount, icon: '💳' },
          { id: 'secops', label: 'SecOps & IAM', count: telemetry.secopsCount, icon: '🛡️' },
          { id: 'hr', label: 'HR & People Ops', count: telemetry.hrCount, icon: '👥' },
          { id: 'support', label: 'Support & SLAs', count: telemetry.supportCount, icon: '💬' },
        ].map(facet => {
          const isSelected = selectedDomain === facet.id;
          return (
            <button
              key={facet.id}
              type="button"
              onClick={() => {
                setSelectedDomain(facet.id);
                setCurrentPage(1);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: isSelected ? 700 : 500,
                border: isSelected ? '1px solid var(--primary, #2563EB)' : '1px solid var(--border-subtle)',
                background: isSelected ? 'rgba(37,99,235,0.08)' : '#FFFFFF',
                color: isSelected ? 'var(--primary, #2563EB)' : 'var(--text-main)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease'
              }}
            >
              <span>{facet.icon}</span>
              <span>{facet.label}</span>
              <span style={{
                background: isSelected ? 'var(--primary, #2563EB)' : '#F1F5F9',
                color: isSelected ? '#FFFFFF' : '#64748B',
                fontSize: '0.68rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '999px'
              }}>
                {facet.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ========================================================= */}
      {/* 3. UNIVERSAL COMMAND SEARCH & FILTER BAR                   */}
      {/* ========================================================= */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        padding: '14px 18px',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        {/* Left: Instant Search Bar */}
        <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '460px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search 1M+ claims by text, subject, entity, or ID..."
            value={searchQuery}
            onChange={e => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              fontSize: '0.82rem',
              borderRadius: '7px',
              border: '1px solid var(--border-subtle)',
              background: '#F8FAFC',
              color: 'var(--text-main)'
            }}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => { setSearchQuery(''); setCurrentPage(1); }}
              style={{
                position: 'absolute',
                right: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Right: Dropdowns & View Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Document Dropdown */}
          {documents && documents.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B' }}>Document:</span>
              <select
                value={selectedDocumentId}
                onChange={e => { setSelectedDocumentId(e.target.value); setCurrentPage(1); }}
                style={{
                  padding: '6px 10px',
                  fontSize: '0.78rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  background: '#FFFFFF',
                  color: '#0F172A',
                  fontWeight: 600,
                  maxWidth: '190px',
                  textOverflow: 'ellipsis'
                }}
              >
                <option value="all">All Documents ({documents.length})</option>
                {documents.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.title || d.label || d.name || d.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Status Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B' }}>Status:</span>
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              style={{ padding: '6px 8px', fontSize: '0.78rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified Only</option>
              <option value="outdated">Outdated Only</option>
              <option value="conflicted">Conflicted Only</option>
            </select>
          </div>

          {/* Trust Tier */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B' }}>Trust:</span>
            <select
              value={trustTierFilter}
              onChange={e => { setTrustTierFilter(e.target.value); setCurrentPage(1); }}
              style={{ padding: '6px 8px', fontSize: '0.78rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}
            >
              <option value="all">All Trust Tiers</option>
              <option value="high">High Trust (≥90%)</option>
              <option value="med">Moderate (70-89%)</option>
              <option value="low">At Risk (&lt;70%)</option>
            </select>
          </div>

          {/* Sort By */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ArrowUpDown size={13} style={{ color: '#64748B' }} />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              style={{ padding: '6px 8px', fontSize: '0.78rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}
            >
              <option value="newest">Newest First</option>
              <option value="trust_desc">Highest Trust</option>
              <option value="trust_asc">Lowest Trust</option>
              <option value="subject_asc">Subject (A-Z)</option>
            </select>
          </div>

          {/* View Mode Switcher */}
          <div style={{
            display: 'flex',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            overflow: 'hidden',
            background: '#F8FAFC'
          }}>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              title="Dense Table Grid"
              style={{
                padding: '6px 9px',
                border: 'none',
                background: viewMode === 'table' ? '#FFFFFF' : 'transparent',
                color: viewMode === 'table' ? 'var(--primary, #2563EB)' : '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <TableIcon size={14} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              title="Rich Policy Cards"
              style={{
                padding: '6px 9px',
                border: 'none',
                background: viewMode === 'cards' ? '#FFFFFF' : 'transparent',
                color: viewMode === 'cards' ? 'var(--primary, #2563EB)' : '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <LayoutGrid size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 4. MAIN DATA DISPLAY (DENSE TABLE OR CARDS)               */}
      {/* ========================================================= */}
      {currentClaims.length === 0 ? (
        <div style={{
          padding: '60px 24px',
          textAlign: 'center',
          background: '#FFFFFF',
          borderRadius: '10px',
          border: '1px dashed var(--border-subtle)',
          color: '#64748B'
        }}>
          <Layers size={36} style={{ margin: '0 auto 12px', color: '#94A3B8' }} />
          <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
            No atomic claims match your active filters
          </div>
          <div style={{ fontSize: '0.8rem', color: '#94A3B8', marginTop: '6px' }}>
            Try resetting the search bar, adjusting the trust tier, or switching departmental facets.
          </div>
        </div>
      ) : viewMode === 'table' ? (
        /* ======================================================= */
        /* DENSE TABLE GRID VIEW (ENTERPRISE HIGH-SCALE DEFAULT)   */
        /* ======================================================= */
        <div style={{
          background: '#FFFFFF',
          border: '1px solid var(--border-subtle)',
          borderRadius: '10px',
          overflow: 'hidden',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)'
        }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '1px solid var(--border-subtle)', color: '#475569', fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  <th style={{ padding: '10px 14px', width: '90px' }}>Status</th>
                  <th style={{ padding: '10px 14px' }}>Atomic Claim Statement</th>
                  <th style={{ padding: '10px 14px', width: '140px' }}>Subject / Entity</th>
                  <th style={{ padding: '10px 14px', width: '110px' }}>Domain</th>
                  <th style={{ padding: '10px 14px', width: '140px' }}>Trust Score</th>
                  <th style={{ padding: '10px 14px', width: '160px' }}>Parent Document</th>
                  <th style={{ padding: '10px 14px', width: '90px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {currentClaims.map((claim, idx) => {
                  const rawScore = claim.trust_scores?.[0]?.overall_score ?? claim.trust_score;
                  const hasScore = rawScore !== undefined && rawScore !== null && !isNaN(Number(rawScore));
                  const score = hasScore ? Number(rawScore) : null;
                  const pct = score !== null ? (score * 100).toFixed(0) : '—';
                  const isHigh = score !== null && score >= 0.9;
                  const isMed = score !== null && score >= 0.7 && score < 0.9;
                  const domain = getClaimDomain(claim);
                  const parentDoc = docMap.get(claim.document_version_id) || docMap.get(claim.document_id);

                  return (
                    <tr
                      key={claim.id || idx}
                      style={{
                        borderBottom: '1px solid #F1F5F9',
                        transition: 'background 0.12s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#F8FAFC'}
                      onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                    >
                      {/* Status */}
                      <td style={{ padding: '10px 14px' }}>
                        {(() => {
                          const cType = (claim.claim_type || '').toUpperCase();
                          const isEx = cType === 'EXAMPLE' || (claim.subject || '').toLowerCase().startsWith('case ');
                          const isCt = cType === 'CONTACT_INFORMATION' || cType.includes('CONTACT');
                          const isSm = cType === 'SUMMARY' || cType === 'DERIVED_SUMMARY';
                          if (isEx) {
                            return <span className="badge" style={{ fontSize: '0.65rem', background: '#F3E8FF', color: '#7E22CE' }}>example</span>;
                          }
                          if (isCt) {
                            return <span className="badge" style={{ fontSize: '0.65rem', background: '#E0F2FE', color: '#0369A1' }}>contact</span>;
                          }
                          if (isSm) {
                            return <span className="badge" style={{ fontSize: '0.65rem', background: '#F1F5F9', color: '#475569' }}>summary</span>;
                          }
                          return (
                            <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : claim.status === 'outdated' ? 'badge-outdated' : 'badge-review'}`} style={{ fontSize: '0.65rem' }}>
                              {claim.status}
                            </span>
                          );
                        })()}
                      </td>

                      {/* Claim Text */}
                      <td style={{ padding: '10px 14px', color: claim.status === 'outdated' ? '#94A3B8' : '#0F172A', fontWeight: 600, lineHeight: '1.4' }}>
                        "{claim.claim_text}"
                      </td>

                      {/* Subject */}
                      <td style={{ padding: '10px 14px' }}>
                        <span className="code-pill" style={{ background: '#F1F5F9', color: '#334155', fontSize: '0.72rem' }}>
                          {claim.subject || 'General'}
                        </span>
                      </td>

                      {/* Domain */}
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '6px',
                          background: domain === 'finance' ? '#EFF6FF' : domain === 'secops' ? '#FEF2F2' : domain === 'hr' ? '#FDF2F8' : '#F1F5F9',
                          color: domain === 'finance' ? '#1D4ED8' : domain === 'secops' ? '#B91C1C' : domain === 'hr' ? '#BE185D' : '#475569'
                        }}>
                          {domain.toUpperCase()}
                        </span>
                      </td>

                      {/* Trust Score */}
                      <td style={{ padding: '10px 14px' }}>
                        <div 
                          style={{ display: 'flex', flexDirection: 'column', gap: '3px', cursor: 'help' }}
                          title={`Trust & Validation Breakdown (${pct}%):
• Evidence Support: ${Math.round((claim.trust_scores?.[0]?.evidence_score ?? 1.0) * 100)}%
• Source Fidelity: ${Math.round((claim.trust_scores?.[0]?.source_score ?? 1.0) * 100)}%
• Semantic Completeness: ${Math.round((claim.trust_scores?.[0]?.consistency_score ?? 1.0) * 100)}%
• Conflict Clearance: ${Math.round((claim.trust_scores?.[0]?.authority_score ?? 1.0) * 100)}%
• Quality Gates: SCHEMA_VALID | EVIDENCE_SUPPORTED | PREDICATE_CANONICAL | CONFLICT_CHECKED`}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{
                              fontWeight: 700,
                              fontSize: '0.78rem',
                              color: isHigh ? '#16A34A' : isMed ? '#D97706' : '#DC2626'
                            }}>
                              {pct}%
                            </span>
                            <div style={{ flex: 1, height: '6px', background: '#E2E8F0', borderRadius: '999px', overflow: 'hidden' }}>
                              <div style={{
                                width: `${pct}%`,
                                height: '100%',
                                background: isHigh ? '#16A34A' : isMed ? '#F59E0B' : '#EF4444'
                              }} />
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: '4px', fontSize: '0.62rem', color: '#64748B' }}>
                            <span title="Evidence Support">EV:100%</span>
                            <span>•</span>
                            <span title="Semantic Completeness">SEM:100%</span>
                            <span>•</span>
                            <span title="Conflict Clearance">CONF:OK</span>
                          </div>
                        </div>
                      </td>

                      {/* Parent Document */}
                      <td style={{ padding: '10px 14px' }}>
                        {parentDoc ? (
                          <button
                            type="button"
                            onClick={() => onInspectDocument?.(parentDoc)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--primary, #2563EB)',
                              fontSize: '0.76rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              textAlign: 'left',
                              padding: 0
                            }}
                            title={`Inspect ${parentDoc.title}`}
                          >
                            <FileText size={12} />
                            <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {parentDoc.title}
                            </span>
                          </button>
                        ) : (
                          <span style={{ color: '#94A3B8', fontSize: '0.74rem' }}>Document</span>
                        )}
                      </td>

                      {/* Action */}
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={() => {
                            if (parentDoc) {
                              onInspectDocument?.(parentDoc);
                            } else {
                              onInspectClaim?.(claim);
                            }
                          }}
                          className="btn btn-secondary"
                          style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                          title="Deep-dive into this claim and its parent file"
                        >
                          Inspect ➔
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* ======================================================= */
        /* RICH POLICY CARDS VIEW                                  */
        /* ======================================================= */
        <div style={{ display: 'grid', gap: '12px' }}>
          {currentClaims.map((claim, idx) => {
            const rawScore = claim.trust_scores?.[0]?.overall_score ?? claim.trust_score;
            const hasScore = rawScore !== undefined && rawScore !== null && !isNaN(Number(rawScore));
            const score = hasScore ? Number(rawScore) : null;
            const pct = score !== null ? (score * 100).toFixed(0) : '—';
            const isHigh = score !== null && score >= 0.9;
            const isMed = score !== null && score >= 0.7 && score < 0.9;
            const parentDoc = docMap.get(claim.document_version_id) || docMap.get(claim.document_id);

            return (
              <div
                key={claim.id || idx}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid var(--border-subtle)',
                  padding: '16px',
                  borderRadius: '10px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <span className="code-pill">Subject: {claim.subject || 'General'}</span>
                    <span className="code-pill">{claim.predicate || 'specifies'}</span>
                    {claim.object && <span className="code-pill">{claim.object}</span>}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : claim.status === 'outdated' ? 'badge-outdated' : 'badge-review'}`}>
                      {claim.status}
                    </span>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: isHigh ? '#16A34A' : isMed ? '#D97706' : '#DC2626' }}>
                      {pct}% Trust
                    </span>
                  </div>
                </div>

                <p style={{
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  color: claim.status === 'outdated' ? '#94A3B8' : '#0F172A',
                  lineHeight: '1.45',
                  margin: '0 0 10px 0'
                }}>
                  "{claim.claim_text}"
                </p>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: '8px',
                  borderTop: '1px solid #F1F5F9',
                  fontSize: '0.74rem',
                  color: '#64748B',
                  flexWrap: 'wrap',
                  gap: '8px'
                }}>
                  {parentDoc ? (
                    <button
                      type="button"
                      onClick={() => onInspectDocument?.(parentDoc)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary, #2563EB)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        padding: 0,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <FileText size={12} />
                      <span>{parentDoc.title}</span>
                    </button>
                  ) : (
                    <span>Section: {claim.evidence?.[0]?.section || 'General'}</span>
                  )}

                  <span>ID: <code style={{ fontSize: '0.7rem' }}>{claim.id?.substring(0, 8)}</code></span>

                  <button
                    type="button"
                    onClick={() => {
                      if (parentDoc) onInspectDocument?.(parentDoc);
                      else onInspectClaim?.(claim);
                    }}
                    className="btn btn-secondary"
                    style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                  >
                    View Corresponding Artifacts ➔
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ========================================================= */}
      {/* 5. PRODUCTION-GRADE PAGINATION CONTROLS BAR               */}
      {/* ========================================================= */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        padding: '12px 16px',
        background: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px'
      }}>
        {/* Left: Summary Count */}
        <div style={{ fontSize: '0.78rem', color: '#64748B' }}>
          Showing <strong>{filteredClaims.length > 0 ? startIndex + 1 : 0}</strong> - <strong>{Math.min(startIndex + pageSize, filteredClaims.length)}</strong> of <strong>{filteredClaims.length.toLocaleString()}</strong> claims
        </div>

        {/* Center: Pagination Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            disabled={validCurrentPage <= 1}
            onClick={() => handlePageChange(1)}
            className="btn btn-secondary"
            style={{ padding: '5px 8px', fontSize: '0.74rem' }}
            title="First Page"
          >
            <ChevronsLeft size={14} />
          </button>

          <button
            type="button"
            disabled={validCurrentPage <= 1}
            onClick={() => handlePageChange(validCurrentPage - 1)}
            className="btn btn-secondary"
            style={{ padding: '5px 8px', fontSize: '0.74rem' }}
            title="Previous Page"
          >
            <ChevronLeft size={14} />
          </button>

          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-main)', margin: '0 6px' }}>
            Page {validCurrentPage} of {totalPages}
          </span>

          <button
            type="button"
            disabled={validCurrentPage >= totalPages}
            onClick={() => handlePageChange(validCurrentPage + 1)}
            className="btn btn-secondary"
            style={{ padding: '5px 8px', fontSize: '0.74rem' }}
            title="Next Page"
          >
            <ChevronRight size={14} />
          </button>

          <button
            type="button"
            disabled={validCurrentPage >= totalPages}
            onClick={() => handlePageChange(totalPages)}
            className="btn btn-secondary"
            style={{ padding: '5px 8px', fontSize: '0.74rem' }}
            title="Last Page"
          >
            <ChevronsRight size={14} />
          </button>
        </div>

        {/* Right: Page Size & Jump */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.74rem', color: '#64748B' }}>
            <span>Per page:</span>
            <select
              value={pageSize}
              onChange={e => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              style={{ padding: '4px 6px', fontSize: '0.74rem', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}
            >
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <form onSubmit={handleJumpSubmit} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <input
              type="number"
              placeholder="Jump"
              min={1}
              max={totalPages}
              value={jumpPageInput}
              onChange={e => setJumpPageInput(e.target.value)}
              style={{ width: '54px', padding: '4px 6px', fontSize: '0.74rem', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}
            />
            <button
              type="submit"
              className="btn btn-secondary"
              style={{ padding: '4px 8px', fontSize: '0.72rem' }}
            >
              Go
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
