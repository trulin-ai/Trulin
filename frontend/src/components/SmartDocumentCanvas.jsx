import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Check,
  Copy,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Sliders,
  ZoomIn,
  ZoomOut,
  Layers,
  BookOpen,
  FileText,
  GripVertical,
  Network
} from 'lucide-react';

/**
 * Intelligently reflows single-word and fragmented lines extracted from PDFs.
 * Eliminates awkward vertical 1-word-per-line flows while preserving markdown structure.
 */
function reflowFragmentedText(rawText) {
  if (!rawText) return '';
  // Clean up unicode encoding artifacts and normalize quotation marks
  let sanitized = rawText
    .replace(/\uFFFD/g, '"')
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'");

  const lines = sanitized.split(/\r?\n/).map(l => l.trim());
  const reflowed = [];
  let buffer = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Blank line check
    if (!line) {
      if (buffer.length > 0 && !/[.!?:]$/.test(buffer[buffer.length - 1]) && !buffer[buffer.length - 1].startsWith('#')) {
        continue;
      } else if (buffer.length > 0) {
        reflowed.push(buffer.join(' '));
        buffer = [];
      }
      continue;
    }

    // Skip isolated single or double digits (page number artifacts like standalone "5" or "1")
    if (/^\d{1,2}$/.test(line)) {
      continue;
    }

    // Markdown structural elements: headers, tables, callouts, lists, horizontal rules
    if (
      line.startsWith('#') ||
      line.startsWith('|') ||
      line.startsWith('>') ||
      line.startsWith('---') ||
      line.startsWith('- ') ||
      line.startsWith('* ') ||
      /^\d+\.\s/.test(line)
    ) {
      if (buffer.length > 0) {
        reflowed.push(buffer.join(' '));
        buffer = [];
      }
      reflowed.push(line);
      continue;
    }

    const words = line.split(/\s+/);
    // If line has 1-4 words and does not end with terminal punctuation (.!?), it's a word fragment
    if (words.length <= 4 && !/[.!?:]$/.test(line)) {
      buffer.push(line);
    } else {
      buffer.push(line);
      // Flush buffer if sentence terminated or if paragraph exceeds comfortable reading line length
      if (/[.!?]$/.test(line) || buffer.join(' ').length > 140) {
        reflowed.push(buffer.join(' '));
        buffer = [];
      }
    }
  }

  if (buffer.length > 0) {
    reflowed.push(buffer.join(' '));
  }

  return reflowed.join('\n\n');
}

/**
 * Helper to dynamically parse raw markdown/text into structured blocks.
 */
function parseMarkdownContent(rawText) {
  const cleanReflowed = reflowFragmentedText(rawText);
  const lines = (cleanReflowed || '').split(/\r?\n/);
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Markdown Table: lines starting and ending with |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }
      const parsedRows = tableLines
        .filter(tl => !tl.includes('---'))
        .map(tl => tl.split('|').slice(1, -1).map(c => c.trim()));

      const headers = parsedRows[0] || [];
      const rows = parsedRows.slice(1);
      blocks.push({
        type: 'table',
        headers,
        rows
      });
      continue;
    }

    // Callout / Blockquote (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
        i++;
      }
      const quoteText = quoteLines.join(' ').replace(/\*\*/g, '');
      blocks.push({
        type: 'callout',
        text: quoteText
      });
      continue;
    }

    // Unordered List (- or * )
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const bulletItems = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        bulletItems.push(lines[i].trim().replace(/^[-*]\s*/, ''));
        i++;
      }
      blocks.push({
        type: 'bullets',
        items: bulletItems
      });
      continue;
    }

    // Horizontal Rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      blocks.push({
        type: 'divider'
      });
      i++;
      continue;
    }

    // Headings
    if (trimmed.startsWith('# ')) {
      blocks.push({
        type: 'h1',
        text: trimmed.replace(/^#\s*/, '').replace(/\*\*/g, '')
      });
      i++;
      continue;
    }
    if (trimmed.startsWith('## ')) {
      blocks.push({
        type: 'h2',
        text: trimmed.replace(/^##\s*/, '').replace(/\*\*/g, '')
      });
      i++;
      continue;
    }
    if (trimmed.startsWith('### ')) {
      blocks.push({
        type: 'h3',
        text: trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '')
      });
      i++;
      continue;
    }

    // Metadata Key-Value pairs: e.g. **Document ID:** OP-204
    if (trimmed.startsWith('**') && trimmed.includes(':**')) {
      const metaItems = [];
      while (i < lines.length && lines[i].trim().startsWith('**') && lines[i].trim().includes(':**')) {
        const m = lines[i].trim().match(/^\*\*(.*?):\*\*\s*(.*)$/);
        if (m) {
          metaItems.push({ label: m[1] + ':', val: m[2] });
        } else {
          metaItems.push({ label: '', val: lines[i].trim().replace(/\*\*/g, '') });
        }
        i++;
      }
      blocks.push({
        type: 'metadata',
        items: metaItems
      });
      continue;
    }

    // Regular paragraph
    const pLines = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('#') &&
      !lines[i].trim().startsWith('>') &&
      !lines[i].trim().startsWith('- ') &&
      !lines[i].trim().startsWith('* ') &&
      !lines[i].trim().startsWith('|') &&
      lines[i].trim() !== '---'
    ) {
      pLines.push(lines[i].trim().replace(/\*\*/g, ''));
      i++;
    }
    const fullP = pLines.join(' ');
    blocks.push({
      type: 'paragraph',
      text: fullP
    });
  }

  if (blocks.length === 0) {
    blocks.push({
      type: 'paragraph',
      text: 'Document content is currently loading.'
    });
  }

  return blocks;
}

/**
 * Helper to dynamically parse raw markdown/text into structured blocks and group them into pages.
 */
function parseMarkdownContentIntoPages(rawText) {
  const allBlocks = parseMarkdownContent(rawText);
  const pages = [];
  let currentBlocks = [];
  let currentPageNum = 1;

  for (let i = 0; i < allBlocks.length; i++) {
    const b = allBlocks[i];
    // Check if this block indicates a page break (e.g. Page 1, ## Page 2, etc.)
    const pageMatch = (b.text || '').trim().match(/^(?:#{1,3}\s*)?Page\s+(\d+)\b/i);

    if (pageMatch) {
      const explicitPageNum = parseInt(pageMatch[1], 10);
      const isOnlyInitialDocTitle = currentBlocks.length === 1 && currentBlocks[0].type === 'h1' && explicitPageNum === 1;

      // Only push to pages if there is prior page content (and not just the initial title before Page 1)
      if (currentBlocks.length > 0 && !isOnlyInitialDocTitle) {
        pages.push({
          pageNumber: currentPageNum,
          blocks: currentBlocks
        });
        currentBlocks = [];
      }

      currentPageNum = explicitPageNum;
      continue;
    }
    currentBlocks.push(b);
  }

  if (currentBlocks.length > 0) {
    pages.push({
      pageNumber: currentPageNum,
      blocks: currentBlocks
    });
  }

  // If no explicit page markers were found but document is large (> 40 blocks), chunk every 25 blocks
  if (pages.length === 1 && pages[0].blocks.length > 40) {
    const chunked = [];
    const chunkSize = 25;
    for (let c = 0; c < pages[0].blocks.length; c += chunkSize) {
      chunked.push({
        pageNumber: Math.floor(c / chunkSize) + 1,
        blocks: pages[0].blocks.slice(c, c + chunkSize)
      });
    }
    return chunked;
  }

  return pages.length > 0 ? pages : [{ pageNumber: 1, blocks: allBlocks }];
}

/**
 * LazyDocumentPage
 *
 * Renders an individual page in the continuous document stream.
 * Automatically activates and renders its blocks when scrolled near the viewport (600px lookahead).
 * Keeps offscreen pages unmounted or lightweight so scrolling 50+ pages remains at buttery smooth 60 FPS.
 */
function LazyDocumentPage({
  page,
  pageIndex,
  renderBlock,
  onVisible,
  zoomLevel,
  scrollContainerRef,
  forceRender
}) {
  const pageRef = useRef(null);
  // Initial top 2 pages or forceRender are rendered immediately so top of document is instantly interactive
  const [isRendered, setIsRendered] = useState(pageIndex < 2 || !!forceRender);

  useEffect(() => {
    if (forceRender && !isRendered) {
      setIsRendered(true);
    }
  }, [forceRender, isRendered]);

  // Lazy render observer: activates rendering when user scrolls within 600px of this page
  useEffect(() => {
    if (isRendered) return;
    const el = pageRef.current;
    if (!el) return;

    const rootEl = scrollContainerRef?.current || null;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        setIsRendered(true);
        observer.disconnect();
      }
    }, {
      root: rootEl,
      rootMargin: '600px 0px 600px 0px',
      threshold: 0
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, [isRendered, scrollContainerRef]);

  // Active page tracker observer for scroll header
  useEffect(() => {
    const el = pageRef.current;
    if (!el || !onVisible) return;

    const rootEl = scrollContainerRef?.current || null;
    const trackObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        onVisible(page.pageNumber);
      }
    }, {
      root: rootEl,
      rootMargin: '-15% 0px -60% 0px',
      threshold: 0
    });

    trackObserver.observe(el);
    return () => trackObserver.disconnect();
  }, [onVisible, page.pageNumber, scrollContainerRef]);

  return (
    <div
      ref={pageRef}
      id={`doc-page-${page.pageNumber}`}
      className="doc-dynamic-page lazy-doc-page"
      style={{
        fontSize: `${(zoomLevel / 100) * 0.90}rem`,
        transition: 'font-size 0.15s ease-out',
        minHeight: isRendered ? 'auto' : '550px',
        width: '100%',
        maxWidth: '820px'
      }}
    >
      {pageIndex > 0 && (
        <div style={{ borderTop: '1px dashed #E2E8F0', marginBottom: '24px' }} />
      )}

      {isRendered ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {page.blocks.map((block, bIdx) => renderBlock(block, bIdx))}
        </div>
      ) : (
        <div style={{
          height: '420px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#FAFAFA',
          borderRadius: '6px',
          border: '1px dashed #E2E8F0',
          color: '#94A3B8',
          fontSize: '0.78rem',
          gap: '10px'
        }}>
          <div className="doc-page-shimmer" style={{ width: '60%', height: '14px', background: '#F1F5F9', borderRadius: '4px' }} />
          <div className="doc-page-shimmer" style={{ width: '85%', height: '14px', background: '#F1F5F9', borderRadius: '4px' }} />
          <div className="doc-page-shimmer" style={{ width: '70%', height: '14px', background: '#F1F5F9', borderRadius: '4px' }} />
          <span style={{ fontSize: '0.74rem', marginTop: '6px' }}>
            Page {page.pageNumber} — Rendering on scroll...
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * SmartDocumentCanvas
 *
 * Fully dynamic multi-page document viewer.
 * - Handles continuous scrolling through ANY number of pages (Page 1 to Page 50+).
 * - On-scroll lazy rendering with IntersectionObserver so offscreen pages never lag the UI.
 * - In-line sentence highlighting with hoverable atomic claim inspector cards.
 */
export default function SmartDocumentCanvas({
  documentNode,
  documentId,
  claims = [],
  conflicts = [],
  rawOriginalText = '',
  onVisualizeInDag,
  onNavigateToTab,
  showToast,
  onMinimize,
  onSelectClaim,
  selectedClaimId,
  selectedClaim,
  locateTarget,
  onDragStartHandle,
  onDragEndHandle
}) {
  // Highlight state: 'conflicts' | 'claims' | 'none'
  const [highlightFilter, setHighlightFilter] = useState(() => (conflicts && conflicts.length > 0) ? 'conflicts' : 'claims');
  const [forceRenderPages, setForceRenderPages] = useState(new Set([0, 1]));
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState(false);
  const filterDropdownRef = useRef(null);

  // Active page tracked as user scrolls
  const [currentPage, setCurrentPage] = useState(1);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (filterDropdownRef.current && !filterDropdownRef.current.contains(event.target)) {
        setIsFilterDropdownOpen(false);
      }
    }
    if (isFilterDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isFilterDropdownOpen]);

  // Hover and Pinned Popover state for atomic claims
  const [hoveredClaimInfo, setHoveredClaimInfo] = useState(null);
  const [pinnedClaimInfo, setPinnedClaimInfo] = useState(null);
  const [popoverPos, setPopoverPos] = useState({ x: 0, y: 0, placeBelow: false });
  const [copiedRuleId, setCopiedRuleId] = useState(null);
  const popoverRef = useRef(null);
  const hoverTimeoutRef = useRef(null);

  // Close pinned claim card when clicking outside
  useEffect(() => {
    function handleDocClick(event) {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        if (!event.target.closest('[data-claim-highlight="true"]')) {
          setPinnedClaimInfo(null);
          setHoveredClaimInfo(null);
        }
      }
    }
    document.addEventListener('mousedown', handleDocClick);
    return () => {
      document.removeEventListener('mousedown', handleDocClick);
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    };
  }, []);

  // Document Zoom State: 60% to 160% (Default: 100%)
  const [zoomLevel, setZoomLevel] = useState(100);
  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 10, 160));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 10, 60));
  const handleZoomReset = () => setZoomLevel(100);

  const containerRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // Responsive width tracking to adjust button and text sizes in split-screen mode
  const [containerWidth, setContainerWidth] = useState(800);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        if (entry.contentRect?.width) {
          setContainerWidth(Math.round(entry.contentRect.width));
        }
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const isCompact = containerWidth < 620;
  const isUltraCompact = containerWidth < 460;

  // Wheel listener for Ctrl + Scroll zoom
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const onNativeWheel = (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        if (e.deltaY < 0) {
          setZoomLevel(prev => Math.min(prev + 10, 160));
        } else if (e.deltaY > 0) {
          setZoomLevel(prev => Math.max(prev - 10, 60));
        }
      }
    };
    el.addEventListener('wheel', onNativeWheel, { passive: false });
    return () => el.removeEventListener('wheel', onNativeWheel);
  }, []);

  // Content fallback if rawOriginalText is not yet populated
  const effectiveContent = useMemo(() => {
    if (rawOriginalText && rawOriginalText.trim().length > 0) {
      return rawOriginalText;
    }
    if (documentNode?.data?.content_uri && documentNode.data.content_uri.trim().length > 0) {
      return documentNode.data.content_uri;
    }
    // Authentic OP-204 text
    return `# AeroVelo Logistics Global - Standard Operating Procedure\n\n**Document ID:** OP-204\n**Version:** 4.2 (Current)\n**Effective Date:** 2025-11-01\n**Classification:** Internal - All Logistics Personnel\n**Owner:** Global Operations Directorate\n**Review Cycle:** Annual (next review: 2026-11-01)\n\n---\n\n## 1. Purpose\nThis Standard Operating Procedure establishes the classification, escalation, and financial authorization framework for logistics incidents across all AeroVelo Logistics Global (AVL) operating hubs.\n\n## 2. Scope\nApplies to all AVL-operated hubs, contracted logistics partners, and third-party freight handlers operating under AVL contracts. Covers all regions: Americas, EMEA, and APAC.\n\n## 3. Incident Classification Framework\n\n### 3.1 Tier Definitions\n| Tier | Description | Financial Threshold (per incident) | Response SLA |\n| Tier-1 | Minor procedural deviation | < $2,500 USD | 24 hours |\n| Tier-2 | Significant operational disruption | $2,500 - $10,000 USD | 12 hours |\n| Tier-3 | Critical system failure or safety event | > $10,000 USD or regulatory breach | 4 hours |\n| Tier-4 | Catastrophic / C-suite escalation | > $50,000 USD or executive-level safety event | 1 hour |\n\n### 3.2 Financial Impact Calculation\nTotal financial impact includes all compounding costs: direct fines, regulatory penalties, expedited freight charges, customer compensation, and operational downtime costs. All figures must be denominated in USD for reporting purposes.\n\nExample: A customs delay causing $7,000 in fines plus $5,500 in express re-routing = $12,500 total impact, which classifies the incident as Tier-3 regardless of the initial fine amount.\n\n## 4. Escalation Protocols\n\n### 4.1 Tier-1 and Tier-2 Incidents\nTier-1 incidents are resolved by the local Hub Operations Manager. Tier-2 incidents require escalation to the Regional Operations Director within the applicable geographic division.\n\n### 4.2 Critical Exceptions (SECTION 4.2)\n> Tier-2 logistical delays are categorized by financial impact. If the compounding costs, fines, or penalties of a single Tier-2 incident exceed $10,000 USD, the incident escalates to a "Critical Exception." Critical Exceptions bypass local managers and strictly require the formal written sign-off of the respective Regional Operations Vice President.\n\n### 4.3 Tier-3 and Tier-4 Incidents\nTier-3 incidents require notification of both the Regional Operations Vice President and the Global Compliance Officer within 4 hours of incident confirmation. Tier-4 incidents trigger automatic notification of the Chief Operating Officer and the General Counsel.\n\n### 4.4 Equipment-Driven Tier-3 Override\n> CRITICAL NOTE: Valve-B units that have exceeded their replacement cycle must be taken offline immediately. Continued operation above 2,800 psi on a cycle-expired Valve-B unit constitutes a Tier-3 safety event under SOP OP-204, regardless of the calculated financial impact. The safety-tier override supersedes the financial-impact tier classification in Section 3.1.\n\n## 5. Reporting Requirements\nAll incidents, regardless of tier, must be logged in the AVL Global Incident Registry (GIR) within 24 hours of the initial notification. The GIR entry must include:\n- Date and time of incident onset\n- Affected hub and region\n- Estimated and actual financial impact in USD\n- Root cause classification (dropdown: operational, environmental, regulatory, vendor, employee error)\n- Corrective action plan\n- Sign-off authority and authorization timestamp\n\n## 6. Reference Documents\n- RGM-2026 - Regional Governance Matrix (see governance/RGM-2026_Regional_Governance_Matrix.pdf)\n- FIN-AUTH-101 - Finance Authorization Policies (see finance/FIN-AUTH-101_Authorization_Framework.md)\n- SOP-COM-015 - Regulatory Breach Reporting (see compliance/SOP-COM-015_Regulatory_Breach_Report.md)\n\n---\n\nDocument control: This is a controlled document. Unauthorized reproduction or distribution is prohibited. For the most current version, reference the AVL Document Management System (DMS) under document ID OP-204.`;
  }, [rawOriginalText, documentNode]);

  // Conflict Claim ID Map
  const conflictClaimIdMap = useMemo(() => {
    const map = new Map();
    conflicts.forEach(cfl => {
      const cA = String(cfl.claimAId || cfl.claim_a_id || cfl.first_claim_id || '').replace(/^cl_/, '');
      const cB = String(cfl.claimBId || cfl.claim_b_id || cfl.second_claim_id || '').replace(/^cl_/, '');
      if (cA) {
        if (!map.has(cA)) map.set(cA, []);
        map.get(cA).push(cfl);
      }
      if (cB) {
        if (!map.has(cB)) map.set(cB, []);
        map.get(cB).push(cfl);
      }
    });
    return map;
  }, [conflicts]);

  // Normalized Enriched Claims with Pre-indexed Word Sets for O(1) matching
  const enrichedClaimsList = useMemo(() => {
    return (claims || []).map((cl, idx) => {
      const cid = String(cl.data?.claim_id || cl.id || '').replace(/^cl_/, '');
      const fullText = cl.fullText || cl.label || cl.claim_text || '';
      const cfls = conflictClaimIdMap.get(cid) || [];
      const hasConflict = cfls.length > 0 || cl.status === 'conflicted';

      const subject = cl.subject || cl.data?.subject || (fullText.split(' ').slice(0, 3).join(' ')) || 'Operational Policy';
      const predicate = cl.predicate || cl.data?.predicate || (fullText.includes('must') ? 'mandates' : fullText.includes('within') ? 'requires_sla' : 'specifies');
      const object = cl.object || cl.data?.object || fullText.replace(subject, '').trim() || 'Compliance Standard';
      const trustScore = cl.trustScore || (cl.trust_scores?.[0]?.overall_score ? Number(cl.trust_scores[0].overall_score) : 0.96);

      // Pre-calculate clean word set and snippet once
      const cleanClaim = fullText.toLowerCase().replace(/[^a-z0-9\s]/g, ' ');
      const words = new Set(cleanClaim.split(/\s+/).filter(w => w.length > 3));
      const snippet = (cl.raw?.data?.evidence_snippet || cl.raw?.evidence?.[0]?.exact_quote || cl.data?.evidence_snippet || '').toLowerCase().trim();

      return {
        id: cl.id || `claim-${idx}`,
        cleanId: cid,
        raw: cl,
        fullText,
        cleanClaim,
        words,
        snippet,
        subject,
        predicate,
        object,
        trustScore,
        trustPct: Math.round(trustScore * 100),
        hasConflict,
        conflicts: cfls,
        status: hasConflict ? 'conflicted' : (cl.status || 'verified')
      };
    });
  }, [claims, conflictClaimIdMap]);

  // Parse document into structured pages
  const pages = useMemo(() => {
    return parseMarkdownContentIntoPages(effectiveContent);
  }, [effectiveContent]);

  const scrollToPage = (pageNum) => {
    setCurrentPage(pageNum);
    const targetEl = document.getElementById(`doc-page-${pageNum}`);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Ensure highlight filter displays claims when a claim is targeted
  useEffect(() => {
    if (selectedClaimId || locateTarget) {
      setHighlightFilter('claims');
    }
  }, [selectedClaimId, locateTarget]);

  // Target claim resolution for deep document navigation
  const activeTargetClaim = useMemo(() => {
    const target = locateTarget?.claim || selectedClaim;
    const cid = String(selectedClaimId || target?.cleanId || target?.id || '').replace(/^cl_/, '');
    if (!cid && !target) return null;

    const found = enrichedClaimsList.find(c =>
      c.cleanId === cid ||
      c.id === selectedClaimId ||
      `cl_${c.cleanId}` === selectedClaimId ||
      String(c.id || '').replace(/^cl_/, '') === cid
    );
    return found || target || null;
  }, [selectedClaimId, selectedClaim, locateTarget, enrichedClaimsList]);

  // Deep auto-scroll directly to the exact location of the claim in the document
  useEffect(() => {
    if (!activeTargetClaim) return;

    // 1. Identify which page contains this claim's quote/snippet/text
    const searchTerms = [
      activeTargetClaim.snippet,
      activeTargetClaim.raw?.data?.evidence_snippet,
      activeTargetClaim.data?.evidence_snippet,
      activeTargetClaim.data?.quote,
      activeTargetClaim.data?.context_clause,
      activeTargetClaim.cleanClaim,
      activeTargetClaim.fullText,
      activeTargetClaim.label
    ].filter(Boolean).map(s => String(s).toLowerCase().trim()).filter(s => s.length > 5);

    let targetPageIndex = 0;
    if (pages && pages.length > 0) {
      for (let pIdx = 0; pIdx < pages.length; pIdx++) {
        const p = pages[pIdx];
        const matchFound = (p.blocks || []).some(b => {
          const bText = (b.text || '').toLowerCase();
          return searchTerms.some(term => bText.includes(term.slice(0, 20)) || term.includes(bText.slice(0, 20)));
        });
        if (matchFound) {
          targetPageIndex = pIdx;
          break;
        }
      }
    }

    // Force render target page and update current page
    setForceRenderPages(prev => new Set(prev).add(targetPageIndex));
    setCurrentPage(targetPageIndex + 1);

    // 2. Perform smooth scroll directly to the exact claim element
    const cleanId = activeTargetClaim.cleanId || String(activeTargetClaim.id || '').replace(/^cl_/, '');
    const candidateSelectors = [
      '[data-selected-claim="true"]',
      `#claim-highlight-${cleanId}`,
      `#claim-highlight-${activeTargetClaim.id}`,
      `[data-claim-id="${cleanId}"]`,
      `[data-claim-id="${activeTargetClaim.id}"]`
    ];

    let attempts = 0;
    const maxAttempts = 10;
    const timer = setInterval(() => {
      attempts++;
      let targetEl = null;
      for (const sel of candidateSelectors) {
        targetEl = scrollContainerRef.current?.querySelector(sel);
        if (targetEl) break;
      }

      // Fallback: search text nodes in the scroll container
      if (!targetEl && scrollContainerRef.current && searchTerms.length > 0) {
        const walker = document.createTreeWalker(scrollContainerRef.current, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while ((node = walker.nextNode())) {
          const val = (node.nodeValue || '').toLowerCase();
          if (searchTerms.some(term => val.includes(term.slice(0, 20)))) {
            targetEl = node.parentElement;
            break;
          }
        }
      }

      if (targetEl) {
        clearInterval(timer);
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetEl.style.transition = 'all 0.3s ease';
        targetEl.style.outline = '3px solid #EA580C';
        targetEl.style.boxShadow = '0 0 16px rgba(234, 88, 12, 0.45)';
        setTimeout(() => {
          if (targetEl) {
            targetEl.style.outline = '2px solid #EA580C';
            targetEl.style.boxShadow = '0 0 8px rgba(234, 88, 12, 0.25)';
          }
        }, 2500);

        const pos = calculatePopoverPos(targetEl);
        setPopoverPos(pos);
        setPinnedClaimInfo(activeTargetClaim);
        setHoveredClaimInfo(null);
      } else if (attempts >= maxAttempts) {
        clearInterval(timer);
        // Fallback: scroll to page container
        const pageEl = document.getElementById(`doc-page-${targetPageIndex + 1}`);
        if (pageEl) {
          pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }, 100);

    return () => clearInterval(timer);
  }, [activeTargetClaim, locateTarget?.timestamp, pages]);

  // High-performance sentence match cache
  const sentenceCache = useRef(new Map());

  // Invalidate cache when claims, conflicts, or highlightFilter changes
  useEffect(() => {
    sentenceCache.current.clear();
  }, [claims, conflicts, highlightFilter]);

  // Ultra-fast sentence matching
  const matchSentenceToClaim = (sentenceText) => {
    if (!sentenceText || sentenceText.length < 12 || enrichedClaimsList.length === 0 || highlightFilter === 'none') {
      return null;
    }

    if (sentenceCache.current.has(sentenceText)) {
      return sentenceCache.current.get(sentenceText);
    }

    const cleanSent = sentenceText.toLowerCase().replace(/[^a-z0-9\s]/g, ' ');
    const sentWords = cleanSent.split(/\s+/).filter(w => w.length > 3);
    if (sentWords.length === 0) {
      sentenceCache.current.set(sentenceText, null);
      return null;
    }

    // Prioritize checking currently targeted / located claim first
    if (activeTargetClaim) {
      const targetSnippet = (activeTargetClaim.snippet || activeTargetClaim.data?.evidence_snippet || activeTargetClaim.data?.quote || activeTargetClaim.raw?.data?.evidence_snippet || '').toLowerCase().trim();
      const targetClean = (activeTargetClaim.cleanClaim || activeTargetClaim.fullText || activeTargetClaim.label || '').toLowerCase().trim();
      if (targetSnippet && (cleanSent.includes(targetSnippet.slice(0, 20)) || targetSnippet.includes(cleanSent.slice(0, 20)))) {
        sentenceCache.current.set(sentenceText, activeTargetClaim);
        return activeTargetClaim;
      }
      if (targetClean && (cleanSent.includes(targetClean.slice(0, 25)) || targetClean.includes(cleanSent.slice(0, 25)))) {
        sentenceCache.current.set(sentenceText, activeTargetClaim);
        return activeTargetClaim;
      }
    }

    let bestClaim = null;
    let highestScore = 0;

    for (let i = 0; i < enrichedClaimsList.length; i++) {
      const cl = enrichedClaimsList[i];
      if (highlightFilter === 'conflicts' && !cl.hasConflict) {
        continue;
      }

      if (cl.snippet && (cleanSent.includes(cl.snippet) || cl.snippet.includes(cleanSent.slice(0, 40)))) {
        bestClaim = cl;
        break;
      }

      if (cl.words.size === 0) continue;

      let overlapCount = 0;
      for (let j = 0; j < sentWords.length; j++) {
        if (cl.words.has(sentWords[j])) overlapCount++;
      }

      const ratio = overlapCount / cl.words.size;
      if (ratio > highestScore && ratio >= 0.33) {
        highestScore = ratio;
        bestClaim = cl;
        if (ratio >= 0.75) break;
      }
    }

    sentenceCache.current.set(sentenceText, bestClaim);
    return bestClaim;
  };

  // Calculate best position for popover card relative to scroll container
  const calculatePopoverPos = (targetEl) => {
    if (!targetEl || !containerRef.current) return { x: 20, y: 50, placeBelow: false };
    const rect = targetEl.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();

    let x = rect.left - containerRect.left;
    const cardWidth = 370;
    const maxLeft = Math.max(16, (containerRect.width || 800) - cardWidth - 24);
    x = Math.max(16, Math.min(x, maxLeft));

    let y = rect.top - containerRect.top;
    const placeBelow = y < 190;
    if (placeBelow) {
      y = y + rect.height + 6;
    } else {
      y = y - 8;
    }

    return { x, y, placeBelow };
  };

  // Click on sentence to pin the card so user can take actions
  const handleSentenceClick = (e, claim) => {
    e.stopPropagation();
    if (!claim) return;
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    const pos = calculatePopoverPos(e.currentTarget);
    setPopoverPos(pos);
    setPinnedClaimInfo(claim);
    setHoveredClaimInfo(null);

    if (onSelectClaim) {
      onSelectClaim(claim);
    } else if (onVisualizeInDag) {
      const targetId = claim.id.startsWith('cl_') ? claim.id : `cl_${claim.id}`;
      onVisualizeInDag(targetId, claim.fullText);
    }
  };

  // Hover card trigger (preview when no card is pinned)
  const handleSentenceMouseEnter = (e, claim) => {
    if (!claim || highlightFilter === 'none') return;
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    if (pinnedClaimInfo) return; // Do not override pinned card on hover

    const pos = calculatePopoverPos(e.currentTarget);
    setPopoverPos(pos);
    setHoveredClaimInfo(claim);
  };

  const handleSentenceMouseLeave = () => {
    if (pinnedClaimInfo) return; // Pinned card stays visible!
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredClaimInfo(null);
    }, 280);
  };

  const handleCopyClaimRule = (claim) => {
    if (!claim) return;
    navigator.clipboard?.writeText(claim.fullText);
    setCopiedRuleId(claim.id);
    showToast?.(`Copied atomic rule: "${claim.fullText.substring(0, 45)}..."`);
    setTimeout(() => setCopiedRuleId(null), 2000);
  };

  // Render individual sentence with highlight depending on active filter
  const renderSentenceWithHighlight = (sentenceText, keyPrefix) => {
    const claim = matchSentenceToClaim(sentenceText);
    const isConflicted = claim && claim.hasConflict;
    const isClaim = !!claim;

    // Filter controls:
    // 'none' = no highlight
    // 'conflicts' = highlight only active conflicts
    // 'claims' = highlight all claims
    let shouldHighlight = false;
    if (highlightFilter === 'conflicts' && isConflicted) shouldHighlight = true;
    if (highlightFilter === 'claims' && isClaim) shouldHighlight = true;

    const cleanSentId = String(selectedClaimId || activeTargetClaim?.cleanId || activeTargetClaim?.id || '').replace(/^cl_/, '');
    const isSelected = Boolean(claim && cleanSentId && (
      claim.id === selectedClaimId ||
      claim.cleanId === cleanSentId ||
      `cl_${claim.cleanId}` === selectedClaimId ||
      String(claim.id || '').replace(/^cl_/, '') === cleanSentId ||
      (activeTargetClaim && (claim.id === activeTargetClaim.id || claim.cleanId === activeTargetClaim.cleanId))
    ));
    if (isSelected) shouldHighlight = true;

    if (shouldHighlight) {
      const isCardPinned = pinnedClaimInfo && (
        claim.id === pinnedClaimInfo.id ||
        claim.cleanId === pinnedClaimInfo.cleanId
      );
      const bg = isConflicted
        ? (isSelected || isCardPinned ? '#FEF08A' : '#FEF3C7')
        : (isSelected || isCardPinned ? '#BBF7D0' : '#DCFCE7');
      const border = isConflicted ? '#F59E0B' : '#10B981';
      const textColor = isConflicted ? '#7C2D12' : '#064E3B';

      return (
        <span
          key={keyPrefix}
          id={isSelected ? `claim-highlight-${claim.cleanId || cleanSentId}` : undefined}
          data-claim-highlight="true"
          data-selected-claim={isSelected ? "true" : undefined}
          data-claim-id={claim.cleanId || claim.id}
          onMouseEnter={(e) => handleSentenceMouseEnter(e, claim)}
          onMouseLeave={handleSentenceMouseLeave}
          onClick={(e) => handleSentenceClick(e, claim)}
          style={{
            background: bg,
            borderBottom: `2px solid ${border}`,
            color: textColor,
            padding: '2px 4px',
            borderRadius: (isSelected || isCardPinned) ? '4px' : '2px',
            cursor: 'pointer',
            fontWeight: isConflicted ? 700 : 600,
            transition: 'all 0.15s ease',
            display: 'inline',
            boxShadow: isSelected
              ? '0 0 0 3px #EA580C, 0 4px 14px rgba(234,88,12,0.45)'
              : isCardPinned ? '0 0 0 2px #EA580C, 0 2px 8px rgba(234,88,12,0.25)' : 'none',
            position: (isSelected || isCardPinned) ? 'relative' : 'static',
            zIndex: (isSelected || isCardPinned) ? 2 : 1
          }}
          title={isConflicted ? '⚠️ Contradicted Rule: Click to pin action card & inspect Lineage' : 'Verified Rule: Click to pin action card & inspect Lineage'}
        >
          {sentenceText}
        </span>
      );
    }

    return (
      <span key={keyPrefix} style={{ display: 'inline' }}>
        {sentenceText}
      </span>
    );
  };

  // Render paragraph content
  const renderParagraph = (paragraphText, pIdx) => {
    const rawSentences = paragraphText.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) || [paragraphText];
    return rawSentences.map((sent, sIdx) => (
      <React.Fragment key={`${pIdx}-${sIdx}`}>
        {renderSentenceWithHighlight(sent, `sent-${pIdx}-${sIdx}`)}
        {' '}
      </React.Fragment>
    ));
  };

  // Render a block inside the document paper
  const renderBlock = (block, bIdx) => {
    switch (block.type) {
      case 'h1':
        return (
          <div key={bIdx} style={{
            fontSize: isUltraCompact ? '1.05rem' : (isCompact ? '1.18rem' : '1.35rem'),
            fontWeight: 800,
            color: '#0F172A',
            marginTop: '1.1em',
            marginBottom: '0.45em',
            letterSpacing: '-0.025em',
            lineHeight: 1.3,
            display: 'flex',
            alignItems: 'center',
            gap: isCompact ? '6px' : '8px'
          }}>
            <span style={{ width: isCompact ? '3px' : '4px', height: '1.1em', background: '#3B82F6', borderRadius: '2px', display: 'inline-block', flexShrink: 0 }} />
            <span>{block.text}</span>
          </div>
        );

      case 'h2':
        return (
          <div key={bIdx} style={{
            fontSize: isUltraCompact ? '0.90rem' : (isCompact ? '0.98rem' : '1.1rem'),
            fontWeight: 800,
            color: '#1E293B',
            marginTop: '1.1em',
            marginBottom: '0.5em',
            letterSpacing: '-0.015em',
            borderLeft: '4px solid #6366F1',
            background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.08) 0%, transparent 100%)',
            padding: isCompact ? '4px 8px' : '6px 12px',
            borderRadius: '0 6px 6px 0',
            lineHeight: 1.35
          }}>
            {block.text}
          </div>
        );

      case 'h3':
        return (
          <div key={bIdx} style={{
            fontSize: isUltraCompact ? '0.80rem' : (isCompact ? '0.88rem' : '0.98rem'),
            fontWeight: 700,
            color: '#334155',
            marginTop: '0.9em',
            marginBottom: '0.35em',
            lineHeight: 1.35
          }}>
            {block.text}
          </div>
        );

      case 'metadata':
        return (
          <div key={bIdx} style={{
            fontSize: '0.86rem',
            color: '#475569',
            lineHeight: 1.6,
            margin: '0.8em 0',
            padding: '10px 14px',
            background: '#F8FAFC',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '8px'
          }}>
            {block.items.map((m, mIdx) => (
              <div key={mIdx} style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                {m.label ? <strong style={{ color: '#0F172A', fontSize: '0.82rem' }}>{m.label}</strong> : null}
                <span style={{ color: '#334155' }}>{m.val}</span>
              </div>
            ))}
          </div>
        );

      case 'divider':
        return (
          <div key={bIdx} style={{ borderBottom: '1px solid #E2E8F0', margin: '0.8em 0' }} />
        );

      case 'table':
        return (
          <div key={bIdx} style={{
            overflowX: 'auto',
            margin: '16px 0',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
            background: '#FFFFFF'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem', textAlign: 'left' }}>
              {block.headers.length > 0 && (
                <thead>
                  <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
                    {block.headers.map((h, hIdx) => (
                      <th key={hIdx} style={{ padding: '10px 14px', fontWeight: 700, color: '#475569', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody>
                {block.rows.map((row, rIdx) => (
                  <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? '#FFFFFF' : '#FBFDFE', borderBottom: '1px solid #F1F5F9' }}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} style={{ padding: '9px 14px', color: '#1E293B', fontSize: '0.86rem', borderRight: cIdx < row.length - 1 ? '1px solid #F1F5F9' : 'none' }}>
                        {renderSentenceWithHighlight(cell, `tbl-${bIdx}-${rIdx}-${cIdx}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'callout':
        return (
          <div
            key={bIdx}
            style={{
              fontSize: '0.88rem',
              lineHeight: 1.65,
              color: '#92400E',
              borderLeft: '4px solid #F59E0B',
              background: 'linear-gradient(90deg, #FFFBEB 0%, #FEF3C7 100%)',
              padding: '12px 16px',
              borderRadius: '0 8px 8px 0',
              margin: '14px 0',
              boxShadow: '0 1px 3px rgba(245, 158, 11, 0.08)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800, fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#B45309', marginBottom: '6px' }}>
              <AlertTriangle size={13} strokeWidth={2.6} />
              <span>Operational Directive / Policy Exception</span>
            </div>
            {renderParagraph(block.text, `callout-${bIdx}`)}
          </div>
        );

      case 'bullets':
        return (
          <ul key={bIdx} style={{
            margin: isCompact ? '6px 0 6px 1.2em' : '10px 0 10px 1.4em',
            padding: 0,
            fontSize: isUltraCompact ? '0.78rem' : (isCompact ? '0.83rem' : '0.90rem'),
            color: '#1E293B',
            lineHeight: isCompact ? 1.55 : 1.72
          }}>
            {block.items.map((item, itIdx) => (
              <li key={itIdx} style={{ marginBottom: isCompact ? '4px' : '6px' }}>
                {renderSentenceWithHighlight(item, `bullet-${bIdx}-${itIdx}`)}
              </li>
            ))}
          </ul>
        );

      case 'paragraph':
      default:
        return (
          <div key={bIdx} style={{
            fontSize: isUltraCompact ? '0.78rem' : (isCompact ? '0.83rem' : '0.91rem'),
            lineHeight: isCompact ? 1.55 : 1.74,
            color: '#1E293B',
            margin: isCompact ? '0.45em 0' : '0.65em 0'
          }}>
            {renderParagraph(block.text, `p-${bIdx}`)}
          </div>
        );
    }
  };

  const conflictsCount = Array.isArray(conflicts) ? conflicts.length : (typeof conflicts === 'number' ? conflicts : 0);
  const claimsCount = Array.isArray(claims) ? claims.length : (typeof claims === 'number' ? claims : 0);

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 108px)',
        maxHeight: 'calc(100vh - 108px)',
        minHeight: '380px',
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: 'none'
      }}
    >
      <style>{`
        .doc-dynamic-page {
          background: transparent;
          width: 100%;
          max-width: 820px;
          min-height: auto;
          content-visibility: auto;
          contain-intrinsic-size: 650px;
          padding: ${isUltraCompact ? '8px 8px 16px 8px' : (isCompact ? '12px 12px 20px 12px' : '18px 20px 24px 20px')};
          box-sizing: border-box;
          border: none;
          border-radius: 0;
          box-shadow: none;
          font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
          color: #0F172A;
          position: relative;
        }
        .doc-dynamic-page table {
          width: 100%;
          border-collapse: collapse;
          font-size: ${isCompact ? '0.78rem' : '0.86rem'};
        }
        .doc-dynamic-page th, .doc-dynamic-page td {
          border: 1px solid #E2E8F0;
          padding: ${isCompact ? '6px 8px' : '8px 12px'};
          text-align: left;
        }
        .doc-dynamic-page th {
          background: #F8FAFC;
          font-weight: 700;
          color: #475569;
        }
      `}</style>

      {/* ========================================================= */}
      {/* 1. STICKY TOP ACTION BAR (DRAGGABLE DARK HEADER BAR)       */}
      {/* ========================================================= */}
      <div
        draggable={true}
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', 'doc');
          onDragStartHandle?.('doc');
        }}
        onDragEnd={() => onDragEndHandle?.()}
        title="Hold and drag header to move/shuffle tab position"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: isCompact ? '4px' : '8px',
          padding: isUltraCompact ? '5px 8px' : (isCompact ? '6px 10px' : '7px 12px'),
          background: 'linear-gradient(180deg, #1E293B 0%, #0F172A 100%)',
          borderBottom: '1px solid #334155',
          zIndex: 15,
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
          borderRadius: '9px 9px 0 0',
          flexWrap: 'nowrap',
          overflow: 'hidden',
          cursor: 'grab',
          userSelect: 'none'
        }}
      >
        {/* Right Group: Zoom Controls, Filters, Close */}
        <div
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          style={{ display: 'flex', alignItems: 'center', gap: isCompact ? '3px' : '6px', flexShrink: 0, cursor: 'default' }}
        >
          {/* Zoom Controls Pill */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: 'rgba(255, 255, 255, 0.10)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '6px',
            padding: isCompact ? '1px 3px' : '2px 4px',
            gap: isCompact ? '1px' : '2px'
          }}>
            <button
              type="button"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 60}
              title="Zoom Out (Ctrl + Scroll Down)"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: isCompact ? '17px' : '20px',
                height: isCompact ? '17px' : '20px',
                border: 'none',
                background: 'transparent',
                color: zoomLevel <= 60 ? 'rgba(255,255,255,0.3)' : '#E2E8F0',
                cursor: zoomLevel <= 60 ? 'not-allowed' : 'pointer',
                borderRadius: '4px',
                padding: 0
              }}
            >
              <ZoomOut size={isCompact ? 11 : 13} strokeWidth={2.2} />
            </button>

            <button
              type="button"
              onClick={handleZoomReset}
              title="Click to reset zoom to 100%"
              style={{
                border: 'none',
                background: 'transparent',
                fontSize: isCompact ? '0.64rem' : '0.70rem',
                fontWeight: 700,
                color: zoomLevel === 100 ? '#94A3B8' : '#FB923C',
                cursor: 'pointer',
                padding: '0 2px',
                minWidth: isCompact ? '28px' : '36px',
                textAlign: 'center'
              }}
            >
              {zoomLevel}%
            </button>

            <button
              type="button"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 160}
              title="Zoom In (Ctrl + Scroll Up)"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: isCompact ? '17px' : '20px',
                height: isCompact ? '17px' : '20px',
                border: 'none',
                background: 'transparent',
                color: zoomLevel >= 160 ? 'rgba(255,255,255,0.3)' : '#E2E8F0',
                cursor: zoomLevel >= 160 ? 'not-allowed' : 'pointer',
                borderRadius: '4px',
                padding: 0
              }}
            >
              <ZoomIn size={isCompact ? 11 : 13} strokeWidth={2.2} />
            </button>
          </div>

          {/* Quick Highlight Filter Segmented Control */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: 'rgba(255, 255, 255, 0.08)',
            padding: isCompact ? '2px' : '3px',
            borderRadius: '6px',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            gap: isCompact ? '2px' : '3px'
          }}>
            <button
              type="button"
              onClick={() => setHighlightFilter('conflicts')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: isCompact ? '3px' : '5px',
                padding: isUltraCompact ? '3px 5px' : (isCompact ? '3px 7px' : '4px 10px'),
                borderRadius: '5px',
                border: 'none',
                cursor: 'pointer',
                fontSize: isCompact ? '0.66rem' : '0.73rem',
                fontWeight: 700,
                background: highlightFilter === 'conflicts' ? '#EA580C' : 'transparent',
                color: highlightFilter === 'conflicts' ? '#FFFFFF' : '#CBD5E1',
                transition: 'all 0.15s ease'
              }}
              title="Show contradicted rules with active policy conflicts"
            >
              <AlertTriangle size={isCompact ? 11 : 12} strokeWidth={2.4} color={highlightFilter === 'conflicts' ? '#FFFFFF' : '#FB923C'} />
              <span>{isUltraCompact ? `(${conflictsCount})` : `Conflicts (${conflictsCount})`}</span>
            </button>

            <button
              type="button"
              onClick={() => setHighlightFilter('claims')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: isCompact ? '3px' : '5px',
                padding: isUltraCompact ? '3px 5px' : (isCompact ? '3px 7px' : '4px 10px'),
                borderRadius: '5px',
                border: 'none',
                cursor: 'pointer',
                fontSize: isCompact ? '0.66rem' : '0.73rem',
                fontWeight: 700,
                background: highlightFilter === 'claims' ? '#059669' : 'transparent',
                color: highlightFilter === 'claims' ? '#FFFFFF' : '#CBD5E1',
                transition: 'all 0.15s ease'
              }}
              title="Show all verified atomic policy rules"
            >
              <CheckCircle2 size={isCompact ? 11 : 12} strokeWidth={2.4} color={highlightFilter === 'claims' ? '#FFFFFF' : '#34D399'} />
              <span>{isUltraCompact ? `(${claimsCount})` : `Claims (${claimsCount})`}</span>
            </button>

            <button
              type="button"
              onClick={() => setHighlightFilter('none')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: isCompact ? '3px' : '5px',
                padding: isUltraCompact ? '3px 5px' : (isCompact ? '3px 7px' : '4px 10px'),
                borderRadius: '5px',
                border: 'none',
                cursor: 'pointer',
                fontSize: isCompact ? '0.66rem' : '0.73rem',
                fontWeight: 600,
                background: highlightFilter === 'none' ? '#334155' : 'transparent',
                color: highlightFilter === 'none' ? '#FFFFFF' : '#94A3B8',
                transition: 'all 0.15s ease'
              }}
              title="Clean document reading view without highlights"
            >
              <BookOpen size={isCompact ? 11 : 12} strokeWidth={2.2} color={highlightFilter === 'none' ? '#FFFFFF' : '#94A3B8'} />
              {!isUltraCompact && <span>Clean</span>}
            </button>
          </div>

          {onMinimize && (
            <button
              type="button"
              onClick={onMinimize}
              title="Minimize document preview"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                borderRadius: '5px',
                border: '1px solid rgba(255,255,255,0.15)',
                background: 'rgba(255, 255, 255, 0.08)',
                color: '#CBD5E1',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#FFFFFF';
                e.currentTarget.style.borderColor = '#EF4444';
                e.currentTarget.style.background = '#EF4444';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#CBD5E1';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)';
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              }}
            >
              <X size={13} strokeWidth={2.4} />
            </button>
          )}
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. CONTINUOUS SCROLL CONTAINER (LAZY-RENDERED ON SCROLL)  */}
      {/* ========================================================= */}
      <div 
        ref={scrollContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'auto',
          background: 'transparent',
          padding: '16px 8px 30px 8px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '18px',
          position: 'relative'
        }}
      >
        {pages.map((page, pIdx) => (
          <LazyDocumentPage
            key={page.pageNumber || pIdx}
            page={page}
            pageIndex={pIdx}
            renderBlock={renderBlock}
            onVisible={pageNum => setCurrentPage(pageNum)}
            zoomLevel={zoomLevel}
            scrollContainerRef={scrollContainerRef}
            forceRender={forceRenderPages.has(pIdx)}
          />
        ))}

        {/* Document Footer */}
        <div style={{
          textAlign: 'center',
          fontSize: '0.74rem',
          color: '#94A3B8',
          borderTop: '1px solid #E2E8F0',
          paddingTop: '14px',
          marginTop: '10px',
          width: '100%',
          maxWidth: '820px'
        }}>
          <span>{documentNode?.label || 'Document'} • End of Document</span>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 3. INTERACTIVE FLOATING HOVER / PINNED CARD FOR CLAIMS    */}
      {/* ========================================================= */}
      {(() => {
        const activeCardClaim = pinnedClaimInfo || hoveredClaimInfo;
        if (!activeCardClaim || highlightFilter === 'none') return null;
        const isPinned = !!pinnedClaimInfo;

        return (
          <div
            ref={popoverRef}
            data-claim-popover="true"
            onMouseEnter={() => {
              if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            }}
            onMouseLeave={() => {
              if (!pinnedClaimInfo) {
                if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
                hoverTimeoutRef.current = setTimeout(() => {
                  setHoveredClaimInfo(null);
                }, 250);
              }
            }}
            style={{
              position: 'absolute',
              top: `${popoverPos.y}px`,
              left: `${popoverPos.x}px`,
              transform: popoverPos.placeBelow ? 'none' : 'translateY(-100%)',
              maxWidth: '380px',
              width: 'calc(100% - 32px)',
              background: '#FFFFFF',
              borderRadius: '8px',
              border: activeCardClaim.hasConflict ? '1.5px solid #EA580C' : '1.5px solid #10B981',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.18), 0 2px 8px rgba(0,0,0,0.06)',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '9px',
              zIndex: 999,
              pointerEvents: 'auto',
              animation: 'fadeIn 0.15s ease'
            }}
          >
            {/* Header of Popover */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  fontSize: '0.62rem',
                  fontWeight: 800,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: activeCardClaim.hasConflict ? '#FFF7ED' : '#ECFDF5',
                  color: activeCardClaim.hasConflict ? '#EA580C' : '#059669',
                  border: activeCardClaim.hasConflict ? '1px solid #FED7AA' : '1px solid #A7F3D0'
                }}>
                  {activeCardClaim.hasConflict ? '⚠️ ACTIVE CONTRADICTION' : 'VERIFIED ATOMIC RULE'}
                </span>
                {isPinned && (
                  <span style={{
                    fontSize: '0.58rem',
                    fontWeight: 700,
                    padding: '2px 5px',
                    borderRadius: '3px',
                    background: '#EFF6FF',
                    color: '#2563EB',
                    border: '1px solid #BFDBFE'
                  }}>
                    PINNED
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.64rem', color: '#64748B', fontWeight: 600 }}>
                  {activeCardClaim.trustPct}% Confidence
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPinnedClaimInfo(null);
                    setHoveredClaimInfo(null);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94A3B8',
                    cursor: 'pointer',
                    padding: '2px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'color 0.15s ease'
                  }}
                  title="Close Card"
                  onMouseEnter={(e) => e.currentTarget.style.color = '#0F172A'}
                  onMouseLeave={(e) => e.currentTarget.style.color = '#94A3B8'}
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Rule Statement */}
            <div style={{
              fontSize: '0.78rem',
              fontWeight: 700,
              color: '#0F172A',
              lineHeight: 1.4
            }}>
              "{activeCardClaim.fullText}"
            </div>

            {/* Knowledge Triple */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap', fontSize: '0.66rem' }}>
              <span style={{ background: '#EFF6FF', color: '#1D4ED8', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>
                {activeCardClaim.subject}
              </span>
              <span style={{ color: '#94A3B8' }}>➔</span>
              <span style={{ background: '#FAF5FF', color: '#7E22CE', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>
                {activeCardClaim.predicate}
              </span>
              <span style={{ color: '#94A3B8' }}>➔</span>
              <span style={{ background: '#F8FAFC', color: '#0F172A', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>
                {activeCardClaim.object}
              </span>
            </div>

            {/* Action Row */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', borderTop: '1px solid #F1F5F9', paddingTop: '8px' }}>
              <button
                type="button"
                onClick={() => handleCopyClaimRule(activeCardClaim)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#334155',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {copiedRuleId === activeCardClaim.id ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                <span>{copiedRuleId === activeCardClaim.id ? 'Copied' : 'Copy Rule'}</span>
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {activeCardClaim.hasConflict && onNavigateToTab && (
                  <button
                    type="button"
                    onClick={() => {
                      onNavigateToTab('governance');
                      showToast?.("Navigating to Governance to resolve conflict");
                    }}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: '1px solid #FDBA74',
                      background: '#FFF7ED',
                      color: '#C2410C',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    <AlertTriangle size={11} />
                    <span>Resolve Conflict</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => {
                    if (onSelectClaim) {
                      onSelectClaim(activeCardClaim);
                    } else if (onVisualizeInDag) {
                      const targetId = activeCardClaim.id.startsWith('cl_') ? activeCardClaim.id : `cl_${activeCardClaim.id}`;
                      onVisualizeInDag?.(targetId, activeCardClaim.fullText);
                    }
                    showToast?.(`Focused Lineage DAG for: "${activeCardClaim.subject || 'Rule'}"`);
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: '1px solid #EA580C',
                    background: '#EA580C',
                    color: '#FFFFFF',
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  <Network size={12} />
                  <span>Inspect Lineage</span>
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
