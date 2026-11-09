import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Zap,
  Filter,
  Layers,
  FileText,
  ShieldCheck,
  Scale,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Eye,
  RefreshCw,
  Search,
  Database,
  Building2,
  ChevronDown,
  X,
  Bot,
  BarChart3,
  Home,
  ExternalLink,
  Share2,
  Download,
  ChevronRight,
  ChevronLeft,
  Copy,
  Check,
  Sparkles,
  Calendar,
  Clock,
  Info,
  Trash2,
  GripVertical,
  Server
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import VisualClaimExtractionStudio from './VisualClaimExtractionStudio';
import SmartDocumentCanvas from './SmartDocumentCanvas';
import ExecutiveDeleteModal from './ExecutiveDeleteModal';
import AssetClaimsStudioPane from './AssetClaimsStudioPane';
import AssetConflictsStudioPane from './AssetConflictsStudioPane';

const CARD_WIDTH = 260;
const CARD_HEIGHT = 76;

export default function VisualLineageGraph({
  activeOrg,
  activeWorkspace,
  showToast,
  vaultSubTab: externalVaultSubTab,
  onVaultSubTabChange,
  initialAssetId,
  initialClaimId,
  onAssetChange,
  onClaimChange,
  initialSection = 'summary',
  onSectionChange
}) {
  const { user } = useAuth();
  const [deleteTargetAsset, setDeleteTargetAsset] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [blastRadius, setBlastRadius] = useState(null);
  const [loadingBlastRadius, setLoadingBlastRadius] = useState(false);
  const [claimsPageLimit, setClaimsPageLimit] = useState(6); // Default 6 claims shown per card with Load More

  // Departmental Workspace Scoping
  const [lineageScopeAll, setLineageScopeAll] = useState(false);
  const WORKSPACE_KEYWORDS = {
    finance: ['refund', 'billing', 'invoice', 'arr', 'payment', 'confluence', 'salesforce', 'accounting', 'pricing', 'tier', 'annual', 'dispute'],
    secops: ['security', 'firewall', 'ingress', 'iam', 'mtls', 'session', 'token', 'freeze', 'portal', 'github', 'kafka', 'baseline', 'policy'],
    hr: ['remote', 'work', 'leave', 'vacation', 'employee', 'handbook', 'people', 'guideline', 'wifi', 'stipend', 'contractor'],
    support: ['support', 'dispute', 'sla', 'ticket', 'escalation', 'jira', 'arbitration', 'customer'],
    staging: ['staging', 'sandbox', 'test', 'mock', 'simulation']
  };

  // Vault Top-Level Sub-Tab: 'documents' (default 360° hub) | 'connectors' (360° hub) | 'conflicts' | 'claims' | 'dag'
  const [internalVaultSubTab, setInternalVaultSubTab] = useState('documents');
  const vaultSubTab = externalVaultSubTab !== undefined ? externalVaultSubTab : internalVaultSubTab;
  const setVaultSubTab = onVaultSubTabChange || setInternalVaultSubTab;

  useEffect(() => {
    if (initialAssetId) {
      setVaultDocumentFilter(initialAssetId);
      const rawId = initialAssetId;
      const matchedNode = graphData?.nodes?.find(n =>
        n.id === rawId ||
        n.id === `doc_${rawId}` ||
        n.data?.doc_id === rawId ||
        String(n.id).toLowerCase() === String(rawId).toLowerCase()
      );
      const targetId = matchedNode ? matchedNode.id : rawId;
      setOpenedAssetId(targetId);
      setSelectedNodeId(targetId);
      setInteractiveRootId(targetId);
      setExpandedUpstreamSet(new Set([targetId]));
      setExpandedDownstreamSet(new Set([targetId]));
    } else {
      setOpenedAssetId(null);
    }
  }, [initialAssetId, graphData]);

  const [asset360Section, setAsset360Section] = useState(initialSection || 'summary'); // 'summary' | 'extraction' | 'dag' | 'claims' | 'conflicts' | 'all'

  useEffect(() => {
    if (initialSection) {
      setAsset360Section(initialSection);
    }
  }, [initialSection]);

  const handleSectionChange = (secId) => {
    setAsset360Section(secId);
    if (secId === 'dag' || secId === 'all') {
      // Switching to Lineage DAG facility: Reset DAG to full document version
      setActiveClaimInspector(null);
      const docNodeId = selectedAsset360?.node?.id || openedAssetId;
      if (docNodeId) {
        setSelectedNodeId(docNodeId);
        setInteractiveRootId(docNodeId);
        setExpandedUpstreamSet(new Set([docNodeId]));
        setExpandedDownstreamSet(new Set([docNodeId]));
        setLineageGranularity('document');
      }
    }
    onSectionChange?.(secId);
  };
  const [copiedHash, setCopiedHash] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(true);
  const [activeClaimInspector, setActiveClaimInspector] = useState(null);
  const [vaultSearch, setVaultSearch] = useState('');
  const [vaultConflictFilter, setVaultConflictFilter] = useState('all'); // 'all' | 'active' | 'resolved'
  const [vaultClaimFilter, setVaultClaimFilter] = useState('all'); // 'all' | 'verified' | 'conflicted' | 'decisions'
  const [vaultDocumentFilter, setVaultDocumentFilter] = useState(initialAssetId || 'all');
  const [vaultSourceFilter, setVaultSourceFilter] = useState('all');
  const [openedAssetId, setOpenedAssetId] = useState(initialAssetId || null); // null = show full List of Documents/Connectors; non-null = open Split View (Original Document + All Facilities beside it)
  const [isFileViewerOpen, setIsFileViewerOpen] = useState(true); // Toggle to show or collapse document viewer and expand facilities to full width
  const [docReaderSearch, setDocReaderSearch] = useState('');
  const [docReaderClauseFilter, setDocReaderClauseFilter] = useState('all'); // 'all' | 'conflicted' | 'verified'
  const [highlightedClaimIdInReader, setHighlightedClaimIdInReader] = useState(null);
  const [isAssetDirectoryOpen, setIsAssetDirectoryOpen] = useState(false);
  const [isAssetDropdownOpen, setIsAssetDropdownOpen] = useState(false);
  const [assetDropdownSearch, setAssetDropdownSearch] = useState('');
  const [assetListFilter, setAssetListFilter] = useState('all'); // 'all' | 'conflicted' | 'clean'
  const [assetListSort, setAssetListSort] = useState('conflicts'); // 'conflicts' | 'claims' | 'name'
  const [assetListPage, setAssetListPage] = useState(1);
  const [assetListPageSize, setAssetListPageSize] = useState(15);

  // Split-Screen Width Adjuster (VS Code Style for 2-screen and 3-screen layouts)
  const [splitRatio, setSplitRatio] = useState(50); // 2-pane left width percentage
  const [splitRatio3Doc, setSplitRatio3Doc] = useState(36); // 3-pane doc width percentage
  const [splitRatio3Details, setSplitRatio3Details] = useState(32); // 3-pane details width percentage
  const [resizingDivider, setResizingDivider] = useState(null); // null | 'twoPane' | 'threePane1' | 'threePane2'
  const isResizingSplit = Boolean(resizingDivider);
  const splitContainerRef = useRef(null);

  // Flexible Pane Order and Drag-Shuffle State (Doc, Details/Desc, DAG)
  const [paneOrder, setPaneOrder] = useState(['doc', 'details', 'dag']);
  const [draggedPane, setDraggedPane] = useState(null);
  const [dragOverPane, setDragOverPane] = useState(null);

  const handleDropPane = (sourcePaneId, targetPaneId) => {
    const src = sourcePaneId || draggedPane;
    if (!src || !targetPaneId || src === targetPaneId) {
      setDraggedPane(null);
      setDragOverPane(null);
      return;
    }
    setPaneOrder(prev => {
      const fromIdx = prev.indexOf(src);
      const toIdx = prev.indexOf(targetPaneId);
      if (fromIdx === -1 || toIdx === -1) return prev;
      const next = [...prev];
      const [moved] = next.splice(fromIdx, 1);
      next.splice(toIdx, 0, moved);
      return next;
    });
    setDraggedPane(null);
    setDragOverPane(null);
    const labelMap = { doc: 'Document', details: 'Asset Details', dag: 'Lineage DAG' };
    showToast?.(`Moved ${labelMap[src] || src} to new position`);
    setTimeout(() => handleFitView(), 150);
  };

  const handleSplitMouseDown = (e, dividerType = 'twoPane') => {
    e.preventDefault();
    setResizingDivider(dividerType);
  };

  useEffect(() => {
    if (!resizingDivider) return;

    const handleMouseMove = (e) => {
      if (!splitContainerRef.current) return;
      const rect = splitContainerRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;

      if (resizingDivider === 'twoPane') {
        const rawPct = (mouseX / rect.width) * 100;
        setSplitRatio(Math.min(Math.max(rawPct, 20), 80));
      } else if (resizingDivider === 'threePane1') {
        const rawPct = (mouseX / rect.width) * 100;
        setSplitRatio3Doc(Math.min(Math.max(rawPct, 18), 55));
      } else if (resizingDivider === 'threePane2') {
        const docPx = (rect.width * splitRatio3Doc) / 100;
        const detailsPx = mouseX - docPx;
        const rawPctDetails = (detailsPx / rect.width) * 100;
        setSplitRatio3Details(Math.min(Math.max(rawPctDetails, 16), 50));
      }
    };

    const handleMouseUp = () => {
      setResizingDivider(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [resizingDivider, splitRatio3Doc]);

  // View Mode: 'interactive' (default single-node on-demand flow), 'conflicts' (contradictions focus), 'all' (sample overview)
  const [viewMode, setViewMode] = useState('interactive');
  const [interactiveRootId, setInteractiveRootId] = useState(null);
  const [expandedUpstreamSet, setExpandedUpstreamSet] = useState(new Set());
  const [expandedDownstreamSet, setExpandedDownstreamSet] = useState(new Set());
  const [expandedConflictClaimsSet, setExpandedConflictClaimsSet] = useState(new Set());
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerSearch, setDrawerSearch] = useState('');
  const [drawerDocFilter, setDrawerDocFilter] = useState('all');
  const [isImpactReportOpen, setIsImpactReportOpen] = useState(false);

  // Enterprise Filter States
  const [selectedConflictId, setSelectedConflictId] = useState('all');
  const [selectedDocFilter, setSelectedDocFilter] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all'); // 'all', 'HIGH', 'CRITICAL', 'MEDIUM', 'LOW'
  const [filterStatus, setFilterStatus] = useState('active'); // 'active' (default: unresolved only), 'resolved', 'all'
  const [filterClaimTrust, setFilterClaimTrust] = useState('all'); // 'all', 'verified', 'review', 'outdated'
  const [showOnlyConflicted, setShowOnlyConflicted] = useState(false);
  const [displayLimit, setDisplayLimit] = useState(12); // 6, 12, 24, 1000 ('all')
  const [visibleTiers, setVisibleTiers] = useState(new Set(['source', 'document', 'claim', 'conflict', 'decision']));
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(true);

  // Enterprise Scalability & Grouping Controls
  const [groupCleanClaims, setGroupCleanClaims] = useState(true);
  const [causalSubgraphOnly, setCausalSubgraphOnly] = useState(false);
  const [lineageGranularity, setLineageGranularity] = useState('claim'); // granular provenance by default
  const [expandedDocIds, setExpandedDocIds] = useState(new Set());

  // Context Investigation Lenses (Scale Engine for Millions of Claims)
  const [investigationLens, setInvestigationLens] = useState('risk'); // 'risk' | 'decision' | 'evidence' | 'hierarchy'
  const [expandedTopicClusters, setExpandedTopicClusters] = useState(new Set());
  const [subgraphLimit, setSubgraphLimit] = useState(45);

  // Free-form Canvas Pan & Zoom State (Maximized at 60% by default)
  const [zoom, setZoom] = useState(0.60);
  const [pan, setPan] = useState({ x: 30, y: 30 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Free-form Node Dragging
  const [draggedNodeId, setDraggedNodeId] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [customPositions, setCustomPositions] = useState({});

  // Actionable DAG: Draft Mutations, Interactive Wiring & Severing
  const [draftAddedEdges, setDraftAddedEdges] = useState([]);
  const [draftSeveredEdgeIds, setDraftSeveredEdgeIds] = useState(new Set());
  const [hoveredEdgeId, setHoveredEdgeId] = useState(null);
  const [isWiringEdge, setIsWiringEdge] = useState(false);
  const [wireSourceNodeId, setWireSourceNodeId] = useState(null);
  const [wireStartPos, setWireStartPos] = useState({ x: 0, y: 0 });
  const [wireCurrentPos, setWireCurrentPos] = useState({ x: 0, y: 0 });
  const [wireHoveredTargetId, setWireHoveredTargetId] = useState(null);
  const [isDeployingLineage, setIsDeployingLineage] = useState(false);

  // Expand / Collapse Branches
  const [collapsedNodes, setCollapsedNodes] = useState(new Set());

  const containerRef = useRef(null);

  const fetchLineage = async () => {
    setLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/lineage/graph?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        if (data.nodes && data.nodes.length > 0 && !selectedNodeId) {
          const firstDoc = data.nodes.find(n => n.type === 'document');
          const firstConflict = data.nodes.find(n => n.type === 'conflict');
          const initialId = firstDoc ? firstDoc.id : (firstConflict ? firstConflict.id : data.nodes[0].id);
          setSelectedNodeId(initialId);
          setInteractiveRootId(initialId);
          setExpandedDownstreamSet(new Set([initialId]));
        }
      } else {
        showToast?.("Failed to fetch lineage graph", "error");
      }
    } catch (e) {
      console.warn("Lineage fetch fallback:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlastRadius = async (claimId) => {
    if (!claimId) return;
    setLoadingBlastRadius(true);
    try {
      const res = await fetch(`/v1/lineage/blast-radius/${claimId}`);
      if (res.ok) {
        const data = await res.json();
        setBlastRadius(data);
      }
    } catch (e) {
      console.warn("Failed to fetch blast radius:", e);
    } finally {
      setLoadingBlastRadius(false);
    }
  };

  useEffect(() => {
    fetchLineage();
  }, [activeOrg?.id]);

  const matchesConflictStatus = (cNode) => {
    const st = (cNode?.status || '').toLowerCase();
    if (filterStatus === 'active') return st !== 'resolved' && st !== 'dismissed';
    if (filterStatus === 'resolved') return st === 'resolved' || st === 'dismissed';
    return true;
  };

  const allConflictsRaw = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'conflict') || [];
  }, [graphData]);

  const sourcesList = useMemo(() => {
    return (graphData?.nodes?.filter(n =>
      n.type === 'source' &&
      (n.subType || '').toLowerCase() !== 'file' &&
      !(n.label || '').toLowerCase().includes('file upload') &&
      !(n.label || '').toLowerCase().includes('direct document upload')
    ) || []);
  }, [graphData]);

  const allClaimsRaw = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'claim') || [];
  }, [graphData]);

  const conflictsList = useMemo(() => {
    return (graphData?.nodes?.filter(n => n.type === 'conflict' && matchesConflictStatus(n)) || []);
  }, [graphData, filterStatus]);

  const documentsList = useMemo(() => {
    return (graphData?.nodes?.filter(n =>
      n.type === 'document' &&
      n.data?.isUploadedFile !== false
    ) || []);
  }, [graphData]);

  const decisionsList = useMemo(() => {
    return graphData?.nodes?.filter(n => n.type === 'decision') || [];
  }, [graphData]);

  const visualizeNodeInDag = (nodeId, nodeLabel, isResolvedConflict = false) => {
    if (isResolvedConflict) {
      setFilterStatus('all');
    }
    setVaultSubTab('dag');
    setViewMode('interactive');
    setSelectedNodeId(nodeId);
    setInteractiveRootId(nodeId);
    setExpandedUpstreamSet(new Set());
    setExpandedDownstreamSet(new Set());
    setExpandedConflictClaimsSet(new Set());
    showToast?.(`Loaded "${nodeLabel || nodeId}" in DAG Visualize — click + or − to expand lineage`);
  };

  const selectedNode = useMemo(() => {
    return graphData?.nodes?.find(n => n.id === selectedNodeId) || null;
  }, [graphData, selectedNodeId]);

  useEffect(() => {
    if (selectedNode && selectedNode.type === 'claim') {
      const claimId = selectedNode.data?.claim_id || selectedNode.id.replace('cl_', '');
      fetchBlastRadius(claimId);
    } else {
      setBlastRadius(null);
    }
  }, [selectedNode]);

  // Build Comprehensive Conflict Mapping
  const conflictMap = useMemo(() => {
    const map = {};
    if (!graphData?.nodes) return map;
    const conflicts = graphData.nodes.filter(n => n.type === 'conflict');
    conflicts.forEach(c => {
      let claimA = c.data?.first_claim_id ? `cl_${c.data.first_claim_id}` : null;
      let claimB = c.data?.second_claim_id ? `cl_${c.data.second_claim_id}` : null;
      if (!claimA || !claimB) {
        const inEdges = graphData.edges?.filter(e => e.target === c.id && e.source.startsWith('cl_')) || [];
        if (!claimA && inEdges[0]) claimA = inEdges[0].source;
        if (!claimB && inEdges[1]) claimB = inEdges[1].source;
      }
      map[c.id] = {
        conflict: c,
        claimAId: claimA,
        claimBId: claimB,
        severity: c.severity || 'MEDIUM',
        status: c.status || 'HUMAN_REVIEW_REQUIRED',
        label: c.label || `Conflict: ${c.id.slice(0, 8)}`,
      };
    });
    return map;
  }, [graphData]);

  // Set of all claims involved in any conflict
  const allConflictedClaimIds = useMemo(() => {
    const set = new Set();
    Object.values(conflictMap).forEach(item => {
      if (item.claimAId) set.add(item.claimAId);
      if (item.claimBId) set.add(item.claimBId);
    });
    graphData?.nodes?.forEach(n => {
      if (n.type === 'claim' && n.status === 'conflicted') set.add(n.id);
    });
    return set;
  }, [conflictMap, graphData]);

  // Upstream Parent Identifiers (Document & Claim Granular Aware)
  const getUpstreamParentIds = useMemo(() => {
    return (nodeId) => {
      if (!graphData?.edges) return [];
      const parents = new Set();
      const edges = graphData.edges;

      if (lineageGranularity === 'document') {
        // 1. Document -> upstream Data Source
        if (nodeId.startsWith('doc_')) {
          edges.forEach(e => {
            if (e.target === nodeId && e.source.startsWith('src_')) {
              parents.add(e.source);
            }
          });
        }
        // 2. Conflict -> upstream Source Documents (not raw claims)
        else if (nodeId.startsWith('cfl_')) {
          const cItem = conflictMap[nodeId];
          if (cItem?.claimAId) {
            edges.forEach(e => {
              if (e.target === cItem.claimAId && e.source.startsWith('doc_')) parents.add(e.source);
            });
          }
          if (cItem?.claimBId) {
            edges.forEach(e => {
              if (e.target === cItem.claimBId && e.source.startsWith('doc_')) parents.add(e.source);
            });
          }
        }
        // 3. AI Decision -> upstream Contradictions or Documents
        else if (nodeId.startsWith('dec_')) {
          edges.forEach(e => {
            if (e.target === nodeId) {
              conflictsList.forEach(c => {
                const cItem = conflictMap[c.id];
                if (cItem?.claimAId === e.source || cItem?.claimBId === e.source) {
                  parents.add(c.id);
                }
              });
              if (e.source.startsWith('doc_')) {
                parents.add(e.source);
              } else if (e.source.startsWith('cl_')) {
                edges.forEach(eDoc => {
                  if (eDoc.target === e.source && eDoc.source.startsWith('doc_')) {
                    parents.add(eDoc.source);
                  }
                });
              }
            }
          });
        }
        // Fallback for claim nodes if explicitly selected
        else {
          edges.forEach(e => {
            if (e.target === nodeId) parents.add(e.source);
          });
        }
      } else {
        // Claim Flow Mode: Full 5-tier granular DAG edges
        edges.forEach(e => {
          if (e.target === nodeId) {
            parents.add(e.source);
          }
        });
      }

      return Array.from(parents);
    };
  }, [graphData, lineageGranularity, conflictMap, conflictsList]);

  // Downstream Child Identifiers (Document & Claim Granular Aware)
  const getDownstreamChildIds = useMemo(() => {
    return (nodeId) => {
      if (!graphData?.edges) return [];
      const children = new Set();
      const edges = graphData.edges;

      if (lineageGranularity === 'document') {
        // 1. Data Source -> downstream Documents
        if (nodeId.startsWith('src_')) {
          edges.forEach(e => {
            if (e.source === nodeId && e.target.startsWith('doc_')) {
              children.add(e.target);
            }
          });
        }
        // 2. Document -> downstream Contradictions, Decisions & Claims
        else if (nodeId.startsWith('doc_')) {
          const docClaimIds = new Set();
          edges.forEach(e => {
            if (e.source === nodeId && e.target.startsWith('cl_')) {
              docClaimIds.add(e.target);
            }
          });

          // Contradictions touching this document's claims
          conflictsList.forEach(c => {
            const cItem = conflictMap[c.id];
            if (docClaimIds.has(cItem?.claimAId) || docClaimIds.has(cItem?.claimBId)) {
              children.add(c.id);
            }
          });

          // Decisions grounded in this document's claims
          decisionsList.forEach(dec => {
            edges.forEach(e => {
              if (e.target === dec.id && (docClaimIds.has(e.source) || e.source === nodeId)) {
                children.add(dec.id);
              }
            });
          });

          // Extracted claims or direct child links
          edges.forEach(e => {
            if (e.source === nodeId && !e.target.startsWith('doc_')) {
              children.add(e.target);
            }
          });
        }
        // 3. Conflict -> downstream AI Decisions grounded by its clashing claims
        else if (nodeId.startsWith('cfl_')) {
          const cItem = conflictMap[nodeId];
          decisionsList.forEach(dec => {
            edges.forEach(e => {
              if (e.target === dec.id && (e.source === cItem?.claimAId || e.source === cItem?.claimBId || e.source === nodeId)) {
                children.add(dec.id);
              }
            });
          });
        }
        // Fallback for claim nodes if explicitly selected
        else {
          edges.forEach(e => {
            if (e.source === nodeId) children.add(e.target);
          });
        }
      } else {
        // Claim Flow Mode: Full 5-tier granular DAG edges
        edges.forEach(e => {
          if (e.source === nodeId) {
            children.add(e.target);
          }
        });
        // Also allow Conflict -> AI Decision expansion in Claim Flow
        if (nodeId.startsWith('cfl_')) {
          const cItem = conflictMap[nodeId];
          decisionsList.forEach(dec => {
            edges.forEach(e => {
              if (e.target === dec.id && (e.source === cItem?.claimAId || e.source === cItem?.claimBId)) {
                children.add(dec.id);
              }
            });
          });
        }
      }

      return Array.from(children);
    };
  }, [graphData, lineageGranularity, conflictMap, conflictsList, decisionsList]);

  const toggleUpstream = (nodeId) => {
    setExpandedUpstreamSet(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        // Collapse this node's upstream and recursively collapse its upstream parents
        const toCollapse = [nodeId];
        while (toCollapse.length > 0) {
          const curr = toCollapse.pop();
          if (next.has(curr)) {
            next.delete(curr);
            const parents = getUpstreamParentIds(curr);
            parents.forEach(p => toCollapse.push(p));
          }
        }
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const toggleDownstream = (nodeId) => {
    setExpandedDownstreamSet(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        // Collapse this node's downstream and recursively collapse its downstream children
        const toCollapse = [nodeId];
        while (toCollapse.length > 0) {
          const curr = toCollapse.pop();
          if (next.has(curr)) {
            next.delete(curr);
            const children = getDownstreamChildIds(curr);
            children.forEach(c => toCollapse.push(c));
          }
        }
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const toggleConflictClaims = (conflictId) => {
    setExpandedConflictClaimsSet(prev => {
      const next = new Set(prev);
      if (next.has(conflictId)) {
        next.delete(conflictId);
      } else {
        next.add(conflictId);
      }
      return next;
    });
  };

  const resetToSingleNode = () => {
    setExpandedUpstreamSet(new Set());
    setExpandedDownstreamSet(new Set());
    setExpandedConflictClaimsSet(new Set());
    setTimeout(() => handleFitView(), 50);
    showToast?.("Reset to single focal node");
  };

  const expandAllFlow = () => {
    if (!graphData?.nodes) return;
    const allIds = new Set(graphData.nodes.map(n => n.id));
    setExpandedUpstreamSet(allIds);
    setExpandedDownstreamSet(allIds);
    setTimeout(() => handleFitView(), 50);
    showToast?.("Expanded complete flow");
  };

  // Compute Connected Sets from real edges
  const connectedNodeMap = useMemo(() => {
    if (!selectedNodeId || !graphData?.edges) {
      return { up: new Set(), down: new Set(), all: new Set(), activeEdgeIds: new Set() };
    }
    const up = new Set();
    const down = new Set();
    const all = new Set([selectedNodeId]);
    const activeEdgeIds = new Set();

    // 1st tier connections
    graphData.edges.forEach(e => {
      if (e.target === selectedNodeId) {
        up.add(e.source);
        all.add(e.source);
        activeEdgeIds.add(e.id);
      }
      if (e.source === selectedNodeId) {
        down.add(e.target);
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
    });

    // 2nd tier connections
    graphData.edges.forEach(e => {
      if (up.has(e.target)) {
        up.add(e.source);
        all.add(e.source);
        activeEdgeIds.add(e.id);
      }
      if (down.has(e.source)) {
        down.add(e.target);
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
    });

    // Also include conflict nodes connecting any claims in 'all'
    graphData.edges.forEach(e => {
      if (all.has(e.source) && e.target.startsWith('cfl_')) {
        all.add(e.target);
        activeEdgeIds.add(e.id);
      }
      if (all.has(e.target) && e.source.startsWith('cfl_')) {
        all.add(e.source);
        activeEdgeIds.add(e.id);
      }
    });

    return { up, down, all, activeEdgeIds };
  }, [selectedNodeId, graphData]);

  // Node Dimensions
  const CARD_WIDTH = 270;
  const CARD_HEIGHT = 92;

  // 1. Reactive Filtering Engine: Evaluates User Filters across the Entire Graph
  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    const nodes = graphData.nodes;
    const edges = graphData.edges || [];

    // A. If a specific conflict is selected in "Inspect Conflict" dropdown:
    if (selectedConflictId !== 'all') {
      const cItem = conflictMap[selectedConflictId];
      if (cItem) {
        const allowedIds = new Set([selectedConflictId]);
        if (cItem.claimAId) allowedIds.add(cItem.claimAId);
        if (cItem.claimBId) allowedIds.add(cItem.claimBId);

        // Add parent documents of these claims
        edges.forEach(e => {
          if ((e.target === cItem.claimAId || e.target === cItem.claimBId) && e.source.startsWith('doc_')) {
            allowedIds.add(e.source);
          }
        });
        // Add sources of these documents
        edges.forEach(e => {
          if (allowedIds.has(e.target) && e.source.startsWith('src_')) {
            allowedIds.add(e.source);
          }
        });
        // Add downstream decisions of these claims or conflict
        edges.forEach(e => {
          if ((e.source === cItem.claimAId || e.source === cItem.claimBId || e.source === selectedConflictId) && e.target.startsWith('dec_')) {
            allowedIds.add(e.target);
          }
        });

        return nodes.filter(n => allowedIds.has(n.id) && visibleTiers.has(n.type));
      }
    }

    // B. General Multi-Factor Filtering
    let result = nodes;

    // 1. Tier visibility toggle filter
    result = result.filter(n => visibleTiers.has(n.type));

    // 2. Filter by document scope
    if (selectedDocFilter !== 'all') {
      const docClaims = new Set();
      edges.forEach(e => {
        if (e.source === selectedDocFilter && e.target.startsWith('cl_')) {
          docClaims.add(e.target);
        }
      });
      const docSources = new Set();
      edges.forEach(e => {
        if (e.target === selectedDocFilter && e.source.startsWith('src_')) {
          docSources.add(e.source);
        }
      });
      const docConflicts = new Set();
      edges.forEach(e => {
        if (docClaims.has(e.source) && e.target.startsWith('cfl_')) {
          docConflicts.add(e.target);
        }
      });

      result = result.filter(n => {
        if (n.type === 'document') return n.id === selectedDocFilter;
        if (n.type === 'source') return docSources.has(n.id);
        if (n.type === 'claim') return docClaims.has(n.id);
        if (n.type === 'conflict') return docConflicts.has(n.id);
        if (n.type === 'decision') return true;
        return true;
      });
    }

    // 3. Show only conflicted paths
    if (showOnlyConflicted) {
      const activeConflicts = result.filter(n => n.type === 'conflict');
      const conflictClaimIds = new Set();
      activeConflicts.forEach(c => {
        edges.forEach(e => {
          if (e.target === c.id && e.source.startsWith('cl_')) conflictClaimIds.add(e.source);
        });
        const cItem = conflictMap[c.id];
        if (cItem?.claimAId) conflictClaimIds.add(cItem.claimAId);
        if (cItem?.claimBId) conflictClaimIds.add(cItem.claimBId);
      });

      const conflictDocIds = new Set();
      edges.forEach(e => {
        if (conflictClaimIds.has(e.target) && e.source.startsWith('doc_')) {
          conflictDocIds.add(e.source);
        }
      });

      const conflictSourceIds = new Set();
      edges.forEach(e => {
        if (conflictDocIds.has(e.target) && e.source.startsWith('src_')) {
          conflictSourceIds.add(e.source);
        }
      });

      result = result.filter(n => {
        if (n.type === 'conflict') return true;
        if (n.type === 'claim') return conflictClaimIds.has(n.id);
        if (n.type === 'document') return conflictDocIds.has(n.id);
        if (n.type === 'source') return conflictSourceIds.has(n.id);
        if (n.type === 'decision') return false;
        return false;
      });
    }

    // 4. Filter conflicts by severity
    if (filterSeverity !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'conflict') return true;
        return (n.severity || '').toUpperCase() === filterSeverity.toUpperCase();
      });
    }

    // 5. Filter conflicts by resolution status (Default: Active/Unresolved Only)
    if (filterStatus !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'conflict') return true;
        return matchesConflictStatus(n);
      });
    }

    // 6. Filter claims by trust level
    if (filterClaimTrust !== 'all') {
      result = result.filter(n => {
        if (n.type !== 'claim') return true;
        const score = n.trustScore !== undefined ? n.trustScore : 0.85;
        if (filterClaimTrust === 'verified') return score >= 0.90;
        if (filterClaimTrust === 'review') return score < 0.90 && n.status !== 'outdated';
        if (filterClaimTrust === 'outdated') return n.status === 'outdated' || score < 0.50;
        return true;
      });
    }

    // 7. Search query across all fields
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(n => {
        return (
          n.label?.toLowerCase().includes(q) ||
          n.fullText?.toLowerCase().includes(q) ||
          n.type?.toLowerCase().includes(q) ||
          n.subType?.toLowerCase().includes(q) ||
          n.id?.toLowerCase().includes(q)
        );
      });
    }

    // 8. Departmental Workspace Scoping
    if (activeWorkspace && activeWorkspace.id !== 'all' && !lineageScopeAll) {
      const kw = WORKSPACE_KEYWORDS[activeWorkspace.id] || [];
      if (kw.length > 0) {
        const matchedIds = new Set();
        result.forEach(n => {
          const text = `${n.label || ''} ${n.fullText || ''} ${n.id || ''} ${n.subType || ''}`.toLowerCase();
          if (kw.some(k => text.includes(k))) {
            matchedIds.add(n.id);
          }
        });

        // Expand to connected neighbors so DAG structure remains intact
        edges.forEach(e => {
          if (matchedIds.has(e.source)) matchedIds.add(e.target);
          if (matchedIds.has(e.target)) matchedIds.add(e.source);
        });

        if (matchedIds.size > 0) {
          result = result.filter(n => matchedIds.has(n.id));
        }
      }
    }

    // 9. Context-Driven Subgraph Query (k=2 depth causal trace)
    if (causalSubgraphOnly && selectedNodeId) {
      result = result.filter(n => connectedNodeMap.all.has(n.id));
    }

    // 10. Anomaly Grouping: Roll up clean/verified claims into summary cluster pills
    // Keep only active contradictions and low-trust/disputed claims expanded!
    if (groupCleanClaims) {
      const allClaims = result.filter(n => n.type === 'claim');
      const nonClaims = result.filter(n => n.type !== 'claim');
      
      const cleanClaims = [];
      const anomalousClaims = [];

      allClaims.forEach(cl => {
        const isConflicted = allConflictedClaimIds.has(cl.id) || cl.status === 'conflicted';
        const isLowTrust = cl.trustScore !== undefined && cl.trustScore < 0.85;
        if (isConflicted || isLowTrust) {
          anomalousClaims.push(cl);
        } else {
          cleanClaims.push(cl);
        }
      });

      const clusterNodes = [];
      if (cleanClaims.length > 0) {
        const cleanByDoc = {};
        cleanClaims.forEach(cl => {
          let parentDoc = 'general';
          edges.forEach(e => {
            if (e.target === cl.id && e.source.startsWith('doc_')) parentDoc = e.source;
          });
          if (!cleanByDoc[parentDoc]) cleanByDoc[parentDoc] = [];
          cleanByDoc[parentDoc].push(cl);
        });

        Object.entries(cleanByDoc).forEach(([docId, cList]) => {
          const docNode = nodes.find(n => n.id === docId);
          clusterNodes.push({
            id: `cluster_clean_${docId}`,
            type: 'claim_cluster',
            label: `${cList.length} Verified Claims`,
            subType: 'verified_cluster',
            docId,
            docTitle: docNode?.label || 'Policy Corpus',
            count: cList.length,
            claimIds: cList.map(c => c.id),
            fullText: `Cluster of ${cList.length} verified baseline claims without contradictions.`
          });
        });
      }

      result = [...nonClaims, ...anomalousClaims, ...clusterNodes];
    }

    // 11. Document-Level vs Claim-Level Granularity Filter
    if (lineageGranularity === 'document') {
      result = result.filter(n => {
        if (n.type !== 'claim' && n.type !== 'claim_cluster') return true;
        let parentDocId = n.docId;
        if (!parentDocId) {
          edges.forEach(e => {
            if (e.target === n.id && e.source.startsWith('doc_')) parentDocId = e.source;
          });
        }
        if (parentDocId && expandedDocIds.has(parentDocId)) return true;
        if (selectedConflictId !== 'all') {
          const cItem = conflictMap[selectedConflictId];
          if (cItem?.claimAId === n.id || cItem?.claimBId === n.id) return true;
        }
        return false;
      });
    }

    // 12. Interactive On-Demand Flow Filter (Single Node at Start)
    // IMPORTANT: Uses interactiveRootId (NOT selectedNodeId) so clicking a card to inspect it
    // never closes or resets previously expanded upstream/downstream nodes!
    if (viewMode === 'interactive') {
      // If expand all was triggered, show full filtered result
      if (graphData?.nodes && expandedDownstreamSet.size >= graphData.nodes.length) {
        return result;
      }

      const rootId = interactiveRootId || (documentsList[0]?.id || graphData?.nodes?.[0]?.id);
      if (!rootId) return [];

      const visibleIds = new Set([rootId]);

      // Iteratively expand upstream parents and downstream children ONLY when their + button was clicked
      let changed = true;
      while (changed) {
        changed = false;
        Array.from(visibleIds).forEach(vId => {
          if (expandedUpstreamSet.has(vId)) {
            const parents = getUpstreamParentIds(vId);
            parents.forEach(pId => {
              if (!visibleIds.has(pId)) {
                visibleIds.add(pId);
                changed = true;
              }
            });
          }
          if (expandedDownstreamSet.has(vId)) {
            const children = getDownstreamChildIds(vId);
            children.forEach(cId => {
              if (!visibleIds.has(cId)) {
                visibleIds.add(cId);
                changed = true;
              }
            });
          }
        });
      }

      const nodeMap = new Map((graphData?.nodes || []).map(n => [n.id, n]));
      result.forEach(n => {
        if (!nodeMap.has(n.id)) nodeMap.set(n.id, n);
      });

      const interactiveNodes = [];
      visibleIds.forEach(id => {
        const found = nodeMap.get(id);
        if (found) interactiveNodes.push(found);
      });
      return interactiveNodes;
    }

    return result;
  }, [
    graphData,
    selectedConflictId,
    selectedDocFilter,
    filterSeverity,
    filterStatus,
    filterClaimTrust,
    showOnlyConflicted,
    visibleTiers,
    searchQuery,
    conflictMap,
    activeWorkspace,
    lineageScopeAll,
    causalSubgraphOnly,
    selectedNodeId,
    groupCleanClaims,
    allConflictedClaimIds,
    connectedNodeMap,
    lineageGranularity,
    expandedDocIds,
    viewMode,
    interactiveRootId,
    expandedUpstreamSet,
    expandedDownstreamSet,
    getUpstreamParentIds,
    getDownstreamChildIds,
    documentsList
  ]);

  // 2. Smart DAG Layout: Adaptive Density & Immediate Visibility
  const defaultPositions = useMemo(() => {
    const map = {};
    if (!filteredNodes.length) return map;

    // Single Starting Node Centering in Interactive Mode
    if (viewMode === 'interactive' && filteredNodes.length === 1) {
      const n0 = filteredNodes[0];
      const initialX = (n0.type === 'source' || n0.type === 'document') ? 50 : 380;
      map[n0.id] = { x: initialX, y: 140 };
      return map;
    }

    const sources = filteredNodes.filter(n => n.type === 'source');
    const documents = filteredNodes.filter(n => n.type === 'document');
    const claims = filteredNodes.filter(n => n.type === 'claim' || n.type === 'claim_cluster');
    const conflicts = filteredNodes.filter(n => n.type === 'conflict');
    const decisions = filteredNodes.filter(n => n.type === 'decision');

    const limit = (displayLimit === 'all' || viewMode === 'interactive') ? 1000 : Number(displayLimit);

    const activeSources = sources.slice(0, limit);
    const activeDocs = documents.slice(0, limit);

    // Prioritize conflicted claims if in conflict mode or conflict focused
    let activeClaims = claims;
    if (viewMode === 'conflicts' || showOnlyConflicted || selectedConflictId !== 'all') {
      const conflictRelatedClaimIds = new Set();
      conflicts.forEach(c => {
        const cItem = conflictMap[c.id];
        if (cItem?.claimAId) conflictRelatedClaimIds.add(cItem.claimAId);
        if (cItem?.claimBId) conflictRelatedClaimIds.add(cItem.claimBId);
      });
      activeClaims = [
        ...claims.filter(cl => cl.type === 'claim_cluster' || conflictRelatedClaimIds.has(cl.id)),
        ...claims.filter(cl => cl.type !== 'claim_cluster' && !conflictRelatedClaimIds.has(cl.id))
      ];
    } else if (viewMode === 'focused' && selectedNodeId) {
      activeClaims = [
        ...claims.filter(n => connectedNodeMap.all.has(n.id) || n.type === 'claim_cluster'),
        ...claims.filter(n => !connectedNodeMap.all.has(n.id) && n.type !== 'claim_cluster')
      ];
    }

    // Claims limit handling for display
    activeClaims = (displayLimit === 'all' || viewMode === 'interactive') ? activeClaims : activeClaims.slice(0, limit);

    const activeConflicts = conflicts.slice(0, limit);
    const activeDecisions = decisions.slice(0, limit);

    // Always guarantee selected node is included in non-interactive modes if present in filteredNodes
    if (viewMode !== 'interactive' && selectedNode && filteredNodes.some(n => n.id === selectedNode.id)) {
      if (selectedNode.type === 'source' && !activeSources.some(n => n.id === selectedNode.id)) activeSources.unshift(selectedNode);
      if (selectedNode.type === 'document' && !activeDocs.some(n => n.id === selectedNode.id)) activeDocs.unshift(selectedNode);
      if ((selectedNode.type === 'claim' || selectedNode.type === 'claim_cluster') && !activeClaims.some(n => n.id === selectedNode.id)) activeClaims.unshift(selectedNode);
      if (selectedNode.type === 'conflict' && !activeConflicts.some(n => n.id === selectedNode.id)) activeConflicts.unshift(selectedNode);
      if (selectedNode.type === 'decision' && !activeDecisions.some(n => n.id === selectedNode.id)) activeDecisions.unshift(selectedNode);
    }

    // Connection-Driven & Document-Tree Layout Engine
    // Dynamically assign each existing tier its OWN distinct column so no tiers ever collide or overlap!
    const edges = graphData?.edges || [];
    const CARD_SPACING = 118;
    const START_Y = 40;

    const hasSources = activeSources.length > 0;
    const hasDocs = activeDocs.length > 0;
    const hasClaims = activeClaims.length > 0;
    const hasConflicts = activeConflicts.length > 0;
    const hasDecisions = activeDecisions.length > 0;

    const COL_SPACING = 350; // CARD_WIDTH (270) + 80px gap for bezier curves
    let colX = 50;

    const X_SOURCE = hasSources ? colX : -999;
    if (hasSources) colX += COL_SPACING;

    const X_DOC = colX;
    if (hasDocs) colX += COL_SPACING;

    const X_CLAIM = hasClaims ? colX : -999;
    if (hasClaims) colX += COL_SPACING;

    const X_CONFLICT = hasConflicts ? colX : -999;
    if (hasConflicts) colX += COL_SPACING;

    const X_DECISION = hasDecisions ? colX : -999;

    // 1. Position Sources (Column 0)
    activeSources.forEach((src, idx) => {
      map[src.id] = {
        x: X_SOURCE,
        y: START_Y + idx * (CARD_SPACING * 1.5)
      };
    });

    // 2. Position Documents based on their parent Sources (Column 1)
    const docsBySource = {};
    const unparentedDocs = [];

    activeDocs.forEach(doc => {
      let parentSrcId = null;
      edges.forEach(e => {
        if (e.target === doc.id && e.source.startsWith('src_')) parentSrcId = e.source;
      });
      if (parentSrcId && map[parentSrcId]) {
        if (!docsBySource[parentSrcId]) docsBySource[parentSrcId] = [];
        docsBySource[parentSrcId].push(doc);
      } else {
        unparentedDocs.push(doc);
      }
    });

    let currentDocY = START_Y;
    activeSources.forEach(src => {
      const childDocs = docsBySource[src.id] || [];
      const srcPos = map[src.id];
      if (childDocs.length > 0) {
        const totalHeight = (childDocs.length - 1) * CARD_SPACING;
        const startDocY = Math.max(START_Y, (srcPos?.y || START_Y) - totalHeight / 2);
        childDocs.forEach((doc, idx) => {
          const docY = startDocY + idx * CARD_SPACING;
          map[doc.id] = { x: X_DOC, y: docY };
          currentDocY = Math.max(currentDocY, docY + CARD_SPACING);
        });
      }
    });

    unparentedDocs.forEach((doc, idx) => {
      map[doc.id] = { x: X_DOC, y: currentDocY + idx * CARD_SPACING };
    });

    // 3. Position Claims in Unified Big Card Container (Column 2)
    const getClaimDocId = (cl) => {
      if (cl.docId) return cl.docId;
      if (cl.data?.doc_id) {
        const str = String(cl.data.doc_id);
        return str.startsWith('doc_') ? str : `doc_${str}`;
      }
      let found = null;
      (graphData?.edges || []).forEach(e => {
        if (e.target === cl.id && e.source.startsWith('doc_')) found = e.source;
      });
      return found || 'unparented';
    };

    const claimsByDoc = {};
    const unparentedClaims = [];

    activeClaims.forEach(cl => {
      const pDocId = getClaimDocId(cl);
      if (pDocId && pDocId !== 'unparented' && map[pDocId]) {
        if (!claimsByDoc[pDocId]) claimsByDoc[pDocId] = [];
        claimsByDoc[pDocId].push(cl);
      } else {
        unparentedClaims.push(cl);
      }
    });

    let currentClaimY = START_Y;
    activeDocs.forEach(doc => {
      const childClaims = claimsByDoc[doc.id] || [];
      const docPos = map[doc.id];
      if (childClaims.length > 0) {
        const groupCardId = `claims_group_card_${doc.id}`;
        const visibleClaims = childClaims.slice(0, claimsPageLimit);
        const cardH = 44 + (visibleClaims.length * 66) + (childClaims.length > 6 ? 38 : 10);
        const startY = Math.max(START_Y, (docPos?.y || START_Y) - cardH / 3);
        map[groupCardId] = { x: X_CLAIM, y: startY };
        currentClaimY = Math.max(currentClaimY, startY + cardH + 30);
      }
    });

    if (unparentedClaims.length > 0) {
      const groupCardId = `claims_group_card_unparented`;
      const visibleClaims = unparentedClaims.slice(0, claimsPageLimit);
      const cardH = 44 + (visibleClaims.length * 66) + (unparentedClaims.length > 6 ? 38 : 10);
      map[groupCardId] = { x: X_CLAIM, y: currentClaimY };
      currentClaimY += cardH + 30;
    }

    // 4. Position Conflicts based on their connected claims or documents (Column 3 or Column 2 in Doc Mode)
    activeConflicts.forEach((c, idx) => {
      const cItem = conflictMap[c.id];
      let yAnchor = null;
      if (cItem?.claimAId && cItem?.claimBId && map[cItem.claimAId] && map[cItem.claimBId]) {
        yAnchor = (map[cItem.claimAId].y + map[cItem.claimBId].y) / 2;
      } else {
        const docYs = [];
        edges.forEach(e => {
          if (e.target === c.id && map[e.source]) docYs.push(map[e.source].y);
        });
        if (docYs.length >= 2) {
          yAnchor = (docYs[0] + docYs[1]) / 2;
        }
      }

      const assignedY = yAnchor !== null ? yAnchor : START_Y + idx * (CARD_SPACING * 1.15);
      map[c.id] = { x: X_CONFLICT, y: assignedY };
    });

    // 5. Position Decisions based on their grounding claims or conflicts (Column 4 or Column 3 in Doc Mode)
    activeDecisions.forEach((dec, idx) => {
      const parentYs = [];
      edges.forEach(e => {
        if (e.target === dec.id) {
          if (map[e.source]) {
            parentYs.push(map[e.source].y);
          } else if (e.source.startsWith('cl_')) {
            edges.forEach(eDoc => {
              if (eDoc.target === e.source && map[eDoc.source]) {
                parentYs.push(map[eDoc.source].y);
              }
            });
          }
        }
      });

      let decY = START_Y + idx * (CARD_SPACING * 1.15);
      if (parentYs.length > 0) {
        decY = parentYs.reduce((a, b) => a + b, 0) / parentYs.length;
      }
      map[dec.id] = { x: X_DECISION, y: decY };
    });

    // Robust Column Collision Avoidance: Group top-level cards by their X coordinate
    // Guarantees zero vertical overlap between any cards in the same column
    const nodesByX = {};
    Object.entries(map).forEach(([id, pos]) => {
      if (id.startsWith('cl_')) return;
      const colKey = Math.round(pos.x);
      if (!nodesByX[colKey]) nodesByX[colKey] = [];
      nodesByX[colKey].push({ id, ...pos });
    });

    const MIN_GAP = 108;
    Object.values(nodesByX).forEach(colNodes => {
      colNodes.sort((a, b) => a.y - b.y);
      for (let i = 1; i < colNodes.length; i++) {
        const prev = colNodes[i - 1];
        const curr = colNodes[i];
        const prevNode = filteredNodes.find(n => n.id === prev.id);
        const isPrevExpanded = prevNode?.type === 'conflict' && expandedConflictClaimsSet.has(prev.id);
        const isPrevGroupCard = prev.id.startsWith('claims_group_card_');
        let requiredGap = MIN_GAP;
        if (isPrevExpanded) requiredGap = 260;
        if (isPrevGroupCard) {
          const docId = prev.id.replace('claims_group_card_', '');
          const count = Math.min(claimsPageLimit, (claimsByDoc[docId] || unparentedClaims).length);
          requiredGap = 44 + (count * 66) + 40;
        }
        if (curr.y < prev.y + requiredGap) {
          curr.y = prev.y + requiredGap;
          map[curr.id].y = curr.y;
        }
      }
    });

    // Precision placement of child claim row ports AFTER top-level cards have final positions
    activeDocs.forEach(doc => {
      const childClaims = claimsByDoc[doc.id] || [];
      const groupCardId = `claims_group_card_${doc.id}`;
      const groupPos = map[groupCardId];
      if (groupPos && childClaims.length > 0) {
        childClaims.forEach((cl, idx) => {
          map[cl.id] = {
            x: groupPos.x,
            y: groupPos.y + 76 + (idx * 62)
          };
        });
      }
    });

    if (unparentedClaims.length > 0 && map['claims_group_card_unparented']) {
      const groupPos = map['claims_group_card_unparented'];
      unparentedClaims.forEach((cl, idx) => {
        map[cl.id] = {
          x: groupPos.x,
          y: groupPos.y + 76 + (idx * 62)
        };
      });
    }

    return map;
  }, [
    filteredNodes,
    displayLimit,
    viewMode,
    showOnlyConflicted,
    selectedConflictId,
    selectedNode,
    connectedNodeMap,
    conflictMap,
    graphData,
    lineageGranularity,
    expandedConflictClaimsSet,
    claimsPageLimit
  ]);

  // Merged positions (custom user drags take precedence)
  const nodePositions = useMemo(() => {
    const merged = { ...defaultPositions, ...customPositions };

    const getClaimDocId = (cl) => {
      if (cl.docId) return cl.docId;
      if (cl.data?.doc_id) {
        const str = String(cl.data.doc_id);
        return str.startsWith('doc_') ? str : `doc_${str}`;
      }
      let found = null;
      (graphData?.edges || []).forEach(e => {
        if (e.target === cl.id && e.source.startsWith('doc_')) found = e.source;
      });
      return found || 'unparented';
    };

    // When a Claims Group Card is moved, dynamically sync its child claims' row coordinates
    Object.entries(merged).forEach(([nodeId, pos]) => {
      if (nodeId.startsWith('claims_group_card_')) {
        const docId = nodeId.replace('claims_group_card_', '');
        const docClaims = filteredNodes.filter(n => n.type === 'claim' && getClaimDocId(n) === docId);
        docClaims.forEach((cl, idx) => {
          merged[cl.id] = {
            x: pos.x,
            y: pos.y + 76 + (idx * 62)
          };
        });
      }
    });

    return merged;
  }, [defaultPositions, customPositions, filteredNodes, claimsPageLimit, graphData]);

  // Filter rendered nodes based on calculated positions (Excludes individual claims as they are rendered inside the Big Claims Group Card)
  const renderedNodes = useMemo(() => {
    if (!filteredNodes) return [];
    // Omit raw 'claim' nodes because they are rendered as structured rows inside the claims_group_card!
    const base = filteredNodes.filter(n => n.type !== 'claim' && !!nodePositions[n.id]);

    const getClaimDocId = (cl) => {
      if (cl.docId) return cl.docId;
      if (cl.data?.doc_id) {
        const str = String(cl.data.doc_id);
        return str.startsWith('doc_') ? str : `doc_${str}`;
      }
      let found = null;
      (graphData?.edges || []).forEach(e => {
        if (e.target === cl.id && e.source.startsWith('doc_')) found = e.source;
      });
      return found || 'unparented';
    };

    // Build synthesized Claims Group Cards for rendering
    const docs = filteredNodes.filter(n => n.type === 'document');
    const allClaims = filteredNodes.filter(n => n.type === 'claim');

    if (allClaims.length > 0) {
      const claimsByDoc = {};
      const unparented = [];

      allClaims.forEach(cl => {
        const pDocId = getClaimDocId(cl);
        if (pDocId && pDocId !== 'unparented') {
          if (!claimsByDoc[pDocId]) claimsByDoc[pDocId] = [];
          claimsByDoc[pDocId].push(cl);
        } else {
          unparented.push(cl);
        }
      });

      Object.entries(claimsByDoc).forEach(([docId, docClaims]) => {
        const groupCardId = `claims_group_card_${docId}`;
        const parentDoc = docs.find(d => d.id === docId);
        if (nodePositions[groupCardId]) {
          base.push({
            id: groupCardId,
            type: 'claims_group_card',
            docId,
            docTitle: parentDoc?.label || 'Source Document',
            claims: docClaims
          });
        }
      });

      if (unparented.length > 0 && nodePositions['claims_group_card_unparented']) {
        base.push({
          id: 'claims_group_card_unparented',
          type: 'claims_group_card',
          docId: 'unparented',
          docTitle: 'General Context Rules',
          claims: unparented
        });
      }
    }

    return base;
  }, [filteredNodes, nodePositions, graphData]);

  // Directional Bezier Connecting Edges
  const renderedEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    const allEdges = [...graphData.edges];

    // Add synthesized cluster edges from parent documents to claim clusters
    filteredNodes.forEach(n => {
      if (n.type === 'claim_cluster' && n.docId && n.docId !== 'general') {
        allEdges.push({
          id: `cluster_edge_${n.docId}_${n.id}`,
          source: n.docId,
          target: n.id,
          type: 'hierarchy'
        });
      }
    });

    // In document mode, synthesize direct Document -> Conflict and Conflict -> Decision edges
    if (lineageGranularity === 'document') {
      conflictsList.forEach(c => {
        const cItem = conflictMap[c.id];
        let docAId = null;
        let docBId = null;
        if (cItem?.claimAId) {
          graphData.edges.forEach(e => {
            if (e.target === cItem.claimAId && e.source.startsWith('doc_')) docAId = e.source;
          });
        }
        if (cItem?.claimBId) {
          graphData.edges.forEach(e => {
            if (e.target === cItem.claimBId && e.source.startsWith('doc_')) docBId = e.source;
          });
        }
        if (docAId && nodePositions[docAId] && nodePositions[c.id] && !nodePositions[cItem.claimAId]) {
          allEdges.push({
            id: `synth_doc_${docAId}_cfl_${c.id}`,
            source: docAId,
            target: c.id,
            type: 'conflict',
            isConflictConnection: true
          });
        }
        if (docBId && nodePositions[docBId] && nodePositions[c.id] && !nodePositions[cItem.claimBId]) {
          allEdges.push({
            id: `synth_doc_${docBId}_cfl_${c.id}`,
            source: docBId,
            target: c.id,
            type: 'conflict',
            isConflictConnection: true
          });
        }
      });

      decisionsList.forEach(dec => {
        graphData.edges.forEach(e => {
          if (e.target === dec.id) {
            // 1. Through conflict if applicable
            conflictsList.forEach(c => {
              const cItem = conflictMap[c.id];
              if (cItem?.claimAId === e.source || cItem?.claimBId === e.source) {
                if (nodePositions[c.id] && nodePositions[dec.id]) {
                  allEdges.push({
                    id: `synth_cfl_${c.id}_dec_${dec.id}`,
                    source: c.id,
                    target: dec.id,
                    type: 'decision_grounding'
                  });
                }
              }
            });

            // 2. Direct Document -> Decision edge if claim's parent doc is on canvas and claim is collapsed/not rendered
            if (e.source.startsWith('cl_')) {
              graphData.edges.forEach(eDoc => {
                if (eDoc.target === e.source && eDoc.source.startsWith('doc_')) {
                  const docId = eDoc.source;
                  if (nodePositions[docId] && nodePositions[dec.id] && !nodePositions[e.source]) {
                    const edgeId = `synth_doc_${docId}_dec_${dec.id}`;
                    if (!allEdges.some(existing => existing.id === edgeId)) {
                      allEdges.push({
                        id: edgeId,
                        source: docId,
                        target: dec.id,
                        type: 'decision_grounding'
                      });
                    }
                  }
                }
              });
            }
          }
        });
      });
    }

    const allEdgesWithDrafts = [
      ...allEdges,
      ...draftAddedEdges
    ];

    // Collect all valid node IDs including individual claim IDs inside group cards
    const visibleClaimIdSet = new Set();
    renderedNodes.forEach(n => {
      if (n.type === 'claims_group_card') {
        (n.claims || []).slice(0, claimsPageLimit).forEach(cl => visibleClaimIdSet.add(cl.id));
      }
    });

    const renderedNodeIdSet = new Set([
      ...renderedNodes.map(n => n.id),
      ...visibleClaimIdSet
    ]);

    return allEdgesWithDrafts
      .filter(e => renderedNodeIdSet.has(e.source) && renderedNodeIdSet.has(e.target))
      .map(e => {
        const src = nodePositions[e.source];
        const tgt = nodePositions[e.target];
        if (!src || !tgt) return null;

        const isSourceClaim = e.source.startsWith('cl_');
        const isTargetClaim = e.target.startsWith('cl_');

        // Precision port-to-port bezier routing
        let x1, y1, x2, y2, dx;

        if (isSourceClaim) {
          x1 = src.x + 330;
          y1 = src.y;
        } else {
          x1 = src.x + CARD_WIDTH;
          y1 = src.y + CARD_HEIGHT / 2;
        }

        if (isTargetClaim) {
          x2 = tgt.x;
          y2 = tgt.y;
        } else {
          x2 = tgt.x;
          y2 = tgt.y + CARD_HEIGHT / 2;
        }

        const isForward = x2 >= x1 + 20;
        dx = Math.max(45, Math.abs(x2 - x1) * 0.45);

        const cp1X = x1 + (isForward ? dx : -dx);
        const cp1Y = y1;
        const cp2X = x2 - (isForward ? dx : -dx);
        const cp2Y = y2;
        const pathData = `M ${x1} ${y1} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${x2} ${y2}`;
        
        // Exact cubic Bezier parametric midpoint at t = 0.5
        const midX = 0.125 * x1 + 0.375 * cp1X + 0.375 * cp2X + 0.125 * x2;
        const midY = 0.125 * y1 + 0.375 * cp1Y + 0.375 * cp2Y + 0.125 * y2;

        const isSevered = draftSeveredEdgeIds.has(e.id);
        const isDraft = !!e.isDraft;
        const isActive = connectedNodeMap.activeEdgeIds.has(e.id) && !isSevered;
        const isConflictConnection = e.type === 'conflict' || (selectedConflictId !== 'all' && (e.target === selectedConflictId || e.source === selectedConflictId));

        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          pathData,
          midX,
          midY,
          isActive,
          isConflictConnection,
          isSevered,
          isDraft
        };
      })
      .filter(Boolean);
  }, [graphData, nodePositions, connectedNodeMap, selectedConflictId, filteredNodes, lineageGranularity, conflictsList, decisionsList, conflictMap, renderedNodes, draftAddedEdges, draftSeveredEdgeIds, claimsPageLimit]);

  // Canvas Pan & Interactive Wiring Handlers
  const handleCanvasMouseDown = (e) => {
    if (e.target.closest('.atlan-node-card') || e.target.closest('.atlan-port-handle') || e.target.closest('.canvas-btn') || e.target.closest('select') || e.target.closest('input') || e.target.closest('button')) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handlePortMouseDown = (e, nodeId) => {
    e.stopPropagation();
    const pos = nodePositions[nodeId];
    if (!pos) return;
    const startX = pos.x + CARD_WIDTH;
    const startY = pos.y + CARD_HEIGHT / 2;
    setIsWiringEdge(true);
    setWireSourceNodeId(nodeId);
    setWireStartPos({ x: startX, y: startY });
    setWireCurrentPos({ x: startX + 20, y: startY });
    setWireHoveredTargetId(null);
  };

  const handleMouseMove = (e) => {
    if (isWiringEdge) {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const canvasX = (e.clientX - rect.left - pan.x) / zoom;
      const canvasY = (e.clientY - rect.top - pan.y) / zoom;
      setWireCurrentPos({ x: canvasX, y: canvasY });

      // Detect magnetic snap to closest compatible input node
      let closestTargetId = null;
      let minDistance = 75;
      renderedNodes.forEach(n => {
        if (n.id === wireSourceNodeId) return;
        const nPos = nodePositions[n.id];
        if (!nPos) return;
        const targetPortX = nPos.x;
        const targetPortY = nPos.y + CARD_HEIGHT / 2;
        const dist = Math.hypot(canvasX - targetPortX, canvasY - targetPortY);
        if (dist < minDistance) {
          minDistance = dist;
          closestTargetId = n.id;
        }
      });
      setWireHoveredTargetId(closestTargetId);
    } else if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (draggedNodeId) {
      const newX = (e.clientX - dragOffset.x - pan.x) / zoom;
      const newY = (e.clientY - dragOffset.y - pan.y) / zoom;
      setCustomPositions(prev => ({
        ...prev,
        [draggedNodeId]: { x: Math.round(newX), y: Math.round(newY) }
      }));
    }
  };

  const handleMouseUp = () => {
    if (isWiringEdge) {
      if (wireHoveredTargetId && wireHoveredTargetId !== wireSourceNodeId) {
        // Check if edge already exists
        const exists = renderedEdges.some(e => e.source === wireSourceNodeId && e.target === wireHoveredTargetId)
          || draftAddedEdges.some(e => e.source === wireSourceNodeId && e.target === wireHoveredTargetId);

        if (!exists) {
          const newEdge = {
            id: `draft_edge_${wireSourceNodeId}_${wireHoveredTargetId}_${Date.now()}`,
            source: wireSourceNodeId,
            target: wireHoveredTargetId,
            type: 'decision_grounding',
            isDraft: true
          };
          setDraftAddedEdges(prev => [...prev, newEdge]);
          showToast?.("Added pending context connection (Simulating impact)");
        } else {
          showToast?.("Connection already exists between these nodes");
        }
      }
      setIsWiringEdge(false);
      setWireSourceNodeId(null);
      setWireHoveredTargetId(null);
    }
    setIsPanning(false);
    setDraggedNodeId(null);
  };

  const handleToggleSeverEdge = (e, edgeId) => {
    e.stopPropagation();
    if (draftAddedEdges.some(de => de.id === edgeId)) {
      setDraftAddedEdges(prev => prev.filter(de => de.id !== edgeId));
      showToast?.("Removed pending connection");
      return;
    }

    setDraftSeveredEdgeIds(prev => {
      const next = new Set(prev);
      if (next.has(edgeId)) {
        next.delete(edgeId);
        showToast?.("Restored active context connection");
      } else {
        next.add(edgeId);
        showToast?.("Severed context connection (Simulating impact)");
      }
      return next;
    });
  };

  const handleDeployLineageMutations = async () => {
    if (draftAddedEdges.length === 0 && draftSeveredEdgeIds.size === 0) return;
    setIsDeployingLineage(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const payload = {
        organization_id: orgId,
        added_edges: draftAddedEdges.map(e => ({ source: e.source, target: e.target, type: e.type })),
        severed_edge_ids: Array.from(draftSeveredEdgeIds),
        reason: "Actionable DAG interactive context re-route"
      };

      const res = await fetch('/v1/lineage/edges/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        if (graphData && graphData.edges) {
          const remainingEdges = graphData.edges.filter(e => !draftSeveredEdgeIds.has(e.id));
          const committedAdded = draftAddedEdges.map(de => ({
            id: de.id,
            source: de.source,
            target: de.target,
            type: de.type
          }));
          setGraphData(prev => ({
            ...prev,
            edges: [...remainingEdges, ...committedAdded]
          }));
        }
        setDraftAddedEdges([]);
        setDraftSeveredEdgeIds(new Set());
        showToast?.("✓ Lineage context graph deployed & AI models updated!");
      } else {
        showToast?.("Failed to deploy lineage mutations");
      }
    } catch (err) {
      console.error("Error deploying lineage mutations:", err);
      showToast?.("Network error while deploying lineage mutations");
    } finally {
      setIsDeployingLineage(false);
    }
  };

  const handleDiscardLineageMutations = () => {
    setDraftAddedEdges([]);
    setDraftSeveredEdgeIds(new Set());
    showToast?.("Discarded draft lineage modifications");
  };

  const handleNodeDragStart = (e, nodeId) => {
    e.stopPropagation();
    setDraggedNodeId(nodeId);
    const pos = nodePositions[nodeId] || { x: 0, y: 0 };
    setDragOffset({
      x: e.clientX - (pos.x * zoom + pan.x),
      y: e.clientY - (pos.y * zoom + pan.y)
    });
  };

  const toggleCollapseNode = (e, nodeId) => {
    e.stopPropagation();
    setCollapsedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  // Auto-Fit Camera to visible nodes bounding box (centered vertically & horizontally)
  const handleFitView = () => {
    const visiblePositions = renderedNodes.map(n => nodePositions[n.id]).filter(Boolean);
    if (visiblePositions.length === 0) {
      setZoom(0.85);
      setPan({ x: 30, y: 30 });
      return;
    }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    visiblePositions.forEach(p => {
      if (p.x < minX) minX = p.x;
      if (p.x + CARD_WIDTH > maxX) maxX = p.x + CARD_WIDTH;
      if (p.y < minY) minY = p.y;
      if (p.y + CARD_HEIGHT > maxY) maxY = p.y + CARD_HEIGHT;
    });

    const graphW = Math.max(100, maxX - minX + 60);
    const graphH = Math.max(100, maxY - minY + 60);
    const containerW = containerRef.current ? containerRef.current.clientWidth : 850;
    const containerH = containerRef.current ? containerRef.current.clientHeight : 600;

    const scaleX = containerW / graphW;
    const scaleY = containerH / graphH;
    
    // Auto-fit camera: Maximize at start with 60% (0.60) minimum zoom
    const minZoomLimit = 0.60;
    const newZoom = Math.min(0.95, Math.max(minZoomLimit, Math.min(scaleX, scaleY) * 0.90));

    // Calculate center Y targeting visible screen area rather than bottom of tall canvas
    const targetH = (asset360Section === 'summary' && activeClaimInspector) ? Math.min(containerH, 460) : containerH;
    const newPanX = (containerW - (maxX - minX) * newZoom) / 2 - minX * newZoom;
    const newPanY = Math.max(25, (targetH - (maxY - minY) * newZoom) / 2 - minY * newZoom);

    setZoom(Number(newZoom.toFixed(2)));
    setPan({ x: Math.round(newPanX), y: Math.round(newPanY) });
    setCustomPositions({});
  };

  // Auto-refit camera whenever the rendered nodes count changes or active claim changes
  const prevRenderedCountRef = useRef(0);
  const prevClaimIdRef = useRef(null);
  useEffect(() => {
    const claimChanged = activeClaimInspector?.id !== prevClaimIdRef.current;
    if (renderedNodes.length > 0 && (renderedNodes.length !== prevRenderedCountRef.current || claimChanged)) {
      prevRenderedCountRef.current = renderedNodes.length;
      prevClaimIdRef.current = activeClaimInspector?.id || null;
      const timer = setTimeout(() => {
        handleFitView();
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [renderedNodes.length, activeClaimInspector?.id]);

  // Toggle visible tiers
  const toggleTier = (tier) => {
    setVisibleTiers(prev => {
      const next = new Set(prev);
      if (next.has(tier)) {
        if (next.size === 1) return prev;
        next.delete(tier);
      } else {
        next.add(tier);
      }
      return next;
    });
  };

  // Reset all filters
  const resetAllFilters = () => {
    setSelectedConflictId('all');
    setSelectedDocFilter('all');
    setFilterSeverity('all');
    setFilterStatus('active');
    setFilterClaimTrust('all');
    setShowOnlyConflicted(false);
    setDisplayLimit(12);
    setSearchQuery('');
    setVisibleTiers(new Set(['source', 'document', 'claim', 'conflict', 'decision']));
    setViewMode('interactive');
    setPan({ x: 30, y: 30 });
    setZoom(0.78);
    showToast?.("All filters reset to default active view");
  };

  const isAnyFilterActive = useMemo(() => {
    return (
      selectedConflictId !== 'all' ||
      selectedDocFilter !== 'all' ||
      filterSeverity !== 'all' ||
      filterStatus !== 'active' ||
      filterClaimTrust !== 'all' ||
      showOnlyConflicted ||
      displayLimit !== 12 ||
      searchQuery.trim() !== '' ||
      visibleTiers.size < 5
    );
  }, [
    selectedConflictId,
    selectedDocFilter,
    filterSeverity,
    filterStatus,
    filterClaimTrust,
    showOnlyConflicted,
    displayLimit,
    searchQuery,
    visibleTiers
  ]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedConflictId !== 'all') count++;
    if (selectedDocFilter !== 'all') count++;
    if (filterSeverity !== 'all') count++;
    if (filterStatus !== 'active') count++;
    if (filterClaimTrust !== 'all') count++;
    if (showOnlyConflicted) count++;
    if (displayLimit !== 12) count++;
    if (searchQuery.trim() !== '') count++;
    if (visibleTiers.size < 5) count++;
    return count;
  }, [
    selectedConflictId,
    selectedDocFilter,
    filterSeverity,
    filterStatus,
    filterClaimTrust,
    showOnlyConflicted,
    displayLimit,
    searchQuery,
    visibleTiers
  ]);

  // Auto-recenter when selecting a specific conflict
  useEffect(() => {
    if (selectedConflictId !== 'all') {
      const timer = setTimeout(() => {
        handleFitView();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [selectedConflictId]);

  const activeConflictsCount = useMemo(() => {
    return allConflictsRaw.filter(c => {
      const st = (c.status || '').toLowerCase();
      return st !== 'resolved' && st !== 'dismissed';
    }).length;
  }, [allConflictsRaw]);

  const resolvedConflictsCount = useMemo(() => {
    return allConflictsRaw.filter(c => {
      const st = (c.status || '').toLowerCase();
      return st === 'resolved' || st === 'dismissed';
    }).length;
  }, [allConflictsRaw]);

  // Compute Selected Asset 360° Profile for Documents & Connectors tabs
  const selectedAsset360 = useMemo(() => {
    if (!graphData?.nodes || !graphData?.edges) return null;
    const edges = graphData.edges;
    const nodes = graphData.nodes;

    if (vaultSubTab === 'documents') {
      const activeDoc = (selectedNode?.type === 'document' ? selectedNode : documentsList[0]) || null;
      if (!activeDoc) return null;
      const parentEdge = edges.find(e => e.target === activeDoc.id && e.source.startsWith('src_'));
      const parentSource = nodes.find(n => n.id === parentEdge?.source) || null;
      const rawActiveDocId = activeDoc.data?.doc_id || String(activeDoc.id || '').replace(/^doc_/, '');
      const claimIds = new Set(edges.filter(e => e.source === activeDoc.id && e.target.startsWith('cl_')).map(e => e.target));
      const assetClaims = allClaimsRaw.filter(cl => {
        if (claimIds.has(cl.id)) return true;
        const clDocId = cl.data?.doc_id || cl.doc_id || cl.asset_id;
        if (clDocId && (clDocId === activeDoc.id || clDocId === rawActiveDocId)) return true;
        return false;
      });
      const assetConflicts = allConflictsRaw.filter(c => {
        const cItem = conflictMap[c.id];
        return claimIds.has(cItem?.claimAId) || claimIds.has(cItem?.claimBId);
      });
      const activeAssetConflicts = assetConflicts.filter(c => {
        const st = (c.status || '').toLowerCase();
        return st !== 'resolved' && st !== 'dismissed';
      });
      const assetDecisions = decisionsList.filter(dec =>
        edges.some(e => e.target === dec.id && claimIds.has(e.source))
      );

      return {
        mode: 'document',
        node: activeDoc,
        parentSource,
        connectedDocs: [activeDoc],
        claims: assetClaims,
        conflicts: assetConflicts,
        activeConflicts: activeAssetConflicts,
        decisions: assetDecisions,
        description: `Normalized enterprise ${activeDoc.subType || 'policy document'} synced via ${parentSource?.label || 'Direct Enterprise Upload'}. Contains ${assetClaims.length} extracted atomic rules governing autonomous agent decisions, with ${activeAssetConflicts.length} active contradiction(s) and ${assetConflicts.length - activeAssetConflicts.length} resolved historical conflict(s).`
      };
    }

    if (vaultSubTab === 'connectors') {
      const activeSrc = (selectedNode?.type === 'source' ? selectedNode : sourcesList[0]) || null;
      if (!activeSrc) return null;
      const docIds = new Set(edges.filter(e => e.source === activeSrc.id && e.target.startsWith('doc_')).map(e => e.target));
      const connectedDocs = nodes.filter(d => d.type === 'document' && docIds.has(d.id));
      const claimIds = new Set(edges.filter(e => docIds.has(e.source) && e.target.startsWith('cl_')).map(e => e.target));
      const assetClaims = allClaimsRaw.filter(cl => claimIds.has(cl.id));
      const assetConflicts = allConflictsRaw.filter(c => {
        const cItem = conflictMap[c.id];
        return claimIds.has(cItem?.claimAId) || claimIds.has(cItem?.claimBId);
      });
      const activeAssetConflicts = assetConflicts.filter(c => {
        const st = (c.status || '').toLowerCase();
        return st !== 'resolved' && st !== 'dismissed';
      });
      const assetDecisions = decisionsList.filter(dec =>
        edges.some(e => e.target === dec.id && claimIds.has(e.source))
      );

      return {
        mode: 'connector',
        node: activeSrc,
        parentSource: null,
        connectedDocs,
        claims: assetClaims,
        conflicts: assetConflicts,
        activeConflicts: activeAssetConflicts,
        decisions: assetDecisions,
        description: `Live ${activeSrc.subType || 'Enterprise'} connector (${activeSrc.label}) operating at ${activeSrc.authority ? `${Number(activeSrc.authority) > 1 ? Number(activeSrc.authority).toFixed(0) : (Number(activeSrc.authority) * 100).toFixed(0)}%` : '95%'} authority weight. Actively synchronizes ${connectedDocs.length} schema/policy record(s) yielding ${assetClaims.length} atomic claims and ${activeAssetConflicts.length} active contradiction(s).`
      };
    }

    return null;
  }, [vaultSubTab, selectedNode, documentsList, sourcesList, allClaimsRaw, allConflictsRaw, decisionsList, conflictMap, graphData]);

  // Deep-Link Claim Activation: Focus and inspect specific claim if initialClaimId was passed
  useEffect(() => {
    if (!initialClaimId) return;
    const cid = String(initialClaimId).replace(/^cl_/, '');
    const targetId = String(initialClaimId).startsWith('cl_') ? String(initialClaimId) : `cl_${cid}`;
    const matchedNode = graphData?.nodes?.find(n => n.id === targetId || n.id === initialClaimId || n.id === `cl_${cid}`);
    const actualNodeId = matchedNode ? matchedNode.id : targetId;

    const matchedClaim = selectedAsset360?.claims?.find(c => c.id === initialClaimId || c.id === targetId || c.cleanId === cid || c.id === cid);
    const claimObj = matchedClaim || { id: targetId, cleanId: cid, text: 'Policy Rule Claim' };

    setActiveClaimInspector(claimObj);
    setHighlightedClaimIdInReader(cid);
    setIsDetailsOpen(true);
    setSelectedNodeId(actualNodeId);
    setInteractiveRootId(actualNodeId);
    setViewMode('interactive');
    setLineageGranularity('claim');
    setExpandedUpstreamSet(new Set([actualNodeId]));
    setExpandedDownstreamSet(new Set([actualNodeId]));
    fetchBlastRadius(cid);
  }, [initialClaimId, graphData, selectedAsset360]);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>

      {/* ========================================================= */}
      {/* VAULT HEADER & QUICK FILTER (DAG / CONFLICTS / CLAIMS)     */}
      {/* ========================================================= */}
      {!selectedAsset360 && (vaultSubTab === 'dag' || vaultSubTab === 'conflicts' || vaultSubTab === 'claims') && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
          padding: '0 0 4px 0'
        }}>
          <div style={{ fontSize: '0.94rem', fontWeight: 800, color: '#0F172A', textTransform: 'capitalize' }}>
            {vaultSubTab === 'dag' ? 'Full Canvas DAG Lineage' : vaultSubTab === 'conflicts' ? 'Enterprise Conflicts Registry' : 'Atomic Claims & Decisions'}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="text"
              placeholder={`Filter ${vaultSubTab}...`}
              value={vaultSearch}
              onChange={(e) => setVaultSearch(e.target.value)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#0F172A',
                fontSize: '0.78rem',
                width: '210px',
                outline: 'none',
                boxShadow: 'none'
              }}
            />
            {vaultSearch && (
              <button
                type="button"
                onClick={() => setVaultSearch('')}
                style={{ border: 'none', background: 'transparent', padding: '4px 6px', fontSize: '0.72rem', cursor: 'pointer', color: '#2563EB', fontWeight: 700 }}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MASTER-DETAIL 360° WORKBENCH (DOCUMENTS, CONNECTORS, DAG) */}
      {/* ========================================================= */}
      {(vaultSubTab === 'documents' || vaultSubTab === 'connectors' || vaultSubTab === 'dag') && (() => {
        const rawItems = vaultSubTab === 'documents' ? documentsList : sourcesList;
        const itemEdges = graphData?.edges || [];

        // Enrich items with claim & conflict metrics for fast sorting, filtering & pagination across 1,000s of items
        const enrichedAssets = rawItems.map(item => {
          let claimCount = 0;
          let activeConflictCount = 0;
          if (item.type === 'document') {
            const cIds = new Set(itemEdges.filter(e => e.source === item.id && e.target.startsWith('cl_')).map(e => e.target));
            claimCount = cIds.size;
            activeConflictCount = allConflictsRaw.filter(c => {
              const st = (c.status || '').toLowerCase();
              if (st === 'resolved' || st === 'dismissed') return false;
              const cItem = conflictMap[c.id];
              return cIds.has(cItem?.claimAId) || cIds.has(cItem?.claimBId);
            }).length;
          } else {
            const dIds = new Set(itemEdges.filter(e => e.source === item.id && e.target.startsWith('doc_')).map(e => e.target));
            claimCount = dIds.size;
            const cIds = new Set(itemEdges.filter(e => dIds.has(e.source) && e.target.startsWith('cl_')).map(e => e.target));
            activeConflictCount = allConflictsRaw.filter(c => {
              const st = (c.status || '').toLowerCase();
              if (st === 'resolved' || st === 'dismissed') return false;
              const cItem = conflictMap[c.id];
              return cIds.has(cItem?.claimAId) || cIds.has(cItem?.claimBId);
            }).length;
          }
          return { ...item, claimCount, activeConflictCount };
        });

        const filteredAssets = enrichedAssets
          .filter(item => {
            const q = (vaultSearch || assetDropdownSearch || '').trim().toLowerCase();
            if (q && !(item.label || '').toLowerCase().includes(q) && !(item.subType || '').toLowerCase().includes(q) && !(item.id || '').toLowerCase().includes(q)) {
              return false;
            }
            if (assetListFilter === 'conflicted' && item.activeConflictCount === 0) return false;
            if (assetListFilter === 'clean' && item.activeConflictCount > 0) return false;
            return true;
          })
          .sort((a, b) => {
            if (assetListSort === 'conflicts') return (b.activeConflictCount - a.activeConflictCount) || (b.claimCount - a.claimCount);
            if (assetListSort === 'claims') return (b.claimCount - a.claimCount) || (b.activeConflictCount - a.activeConflictCount);
            return (a.label || '').localeCompare(b.label || '');
          });

        const totalPages = Math.max(1, Math.ceil(filteredAssets.length / assetListPageSize));
        const safePage = Math.min(assetListPage, totalPages);
        const pagedAssets = filteredAssets.slice((safePage - 1) * assetListPageSize, safePage * assetListPageSize);
        const currentIndex = enrichedAssets.findIndex(a => a.id === selectedAsset360?.node?.id);

        const selectAssetItem = (item) => {
          setOpenedAssetId(item.id);
          setSelectedNodeId(item.id);
          setInteractiveRootId(item.id);
          setExpandedUpstreamSet(new Set([item.id]));
          setExpandedDownstreamSet(new Set([item.id]));
          setExpandedConflictClaimsSet(new Set());
          setIsAssetDropdownOpen(false);
          setIsAssetDirectoryOpen(false);
          setDocReaderSearch('');
          setAsset360Section('summary');
          onAssetChange?.(item.id);
        };

        // ============================================================================
        // STAGE 1: FULL-WIDTH LIST OF DOCUMENTS / CONNECTORS (When no item is opened)
        // ============================================================================
        if ((vaultSubTab === 'documents' || vaultSubTab === 'connectors') && !openedAssetId) {
          return (
            <div style={{
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              background: 'transparent',
              border: 'none',
              padding: 0
            }}>
              <style>{`
                .trulin-artifact-row {
                  transition: background 0.22s cubic-bezier(0.16, 1, 0.3, 1);
                  background: #FAF8F5;
                  cursor: pointer;
                }
                .trulin-artifact-row:hover {
                  background: #FFFBF5 !important;
                }
                .trulin-artifact-row:hover > td:first-child {
                  box-shadow: inset 3px 0 0 #EA580C;
                }
                .trulin-artifact-row:hover .trulin-row-title {
                  color: #EA580C !important;
                }
                .trulin-artifact-row:hover .trulin-row-icon-box {
                  background: #FFEDD5 !important;
                  border-color: #FDBA74 !important;
                  transform: scale(1.08);
                }
                .trulin-artifact-row:hover .trulin-inspect-btn {
                  background: #EA580C !important;
                  color: #FFFFFF !important;
                  border-color: #EA580C !important;
                  box-shadow: 0 3px 10px rgba(234, 88, 12, 0.32) !important;
                }
                .trulin-artifact-row:hover .trulin-inspect-arrow {
                  transform: translateX(4px);
                }
                .trulin-inspect-btn {
                  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .trulin-inspect-arrow {
                  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .trulin-row-icon-box {
                  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .trulin-row-title {
                  transition: color 0.2s ease;
                }
                .trulin-filter-btn {
                  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .trulin-search-box input:focus {
                  border-color: #EA580C !important;
                  box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.14) !important;
                }
                .trulin-vscode-splitter:hover > div:first-child {
                  background: #EA580C !important;
                }
                .trulin-vscode-splitter:hover > div:last-child {
                  background: #EA580C !important;
                }
              `}</style>

              {/* Sleek Toolbar: Search, Sort */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                flexWrap: 'wrap',
                gap: '10px',
                padding: '0 0 2px 0'
              }}>

                {/* Search, Sort & Page Size Controls */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <div className="trulin-search-box" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <Search size={14} style={{ position: 'absolute', left: '10px', color: '#94A3B8', pointerEvents: 'none' }} />
                    <input
                      type="text"
                      placeholder={`Search ${vaultSubTab === 'documents' ? 'policy artifacts & claims' : 'connectors & tables'}...`}
                      value={vaultSearch}
                      onChange={(e) => setVaultSearch(e.target.value)}
                      style={{
                        paddingLeft: '30px',
                        paddingRight: vaultSearch ? '28px' : '10px',
                        height: '31px',
                        borderRadius: '6px',
                        border: '1px solid #E2E8F0',
                        background: '#FFFFFF',
                        color: '#0F172A',
                        fontSize: '0.76rem',
                        width: '210px',
                        outline: 'none',
                        transition: 'all 0.2s ease'
                      }}
                    />
                    {vaultSearch && (
                      <button
                        type="button"
                        onClick={() => setVaultSearch('')}
                        style={{
                          position: 'absolute',
                          right: '6px',
                          border: 'none',
                          background: 'transparent',
                          color: '#94A3B8',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          padding: '2px'
                        }}
                      >
                        <X size={13} />
                      </button>
                    )}
                  </div>

                  <select
                    value={assetListSort}
                    onChange={(e) => { setAssetListSort(e.target.value); setAssetListPage(1); }}
                    style={{
                      height: '31px',
                      padding: '0 8px',
                      fontSize: '0.74rem',
                      borderRadius: '6px',
                      border: '1px solid #E2E8F0',
                      color: '#0F172A',
                      background: '#FFFFFF',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="conflicts">Sort: Conflict Severity</option>
                    <option value="claims">Sort: Claim Density</option>
                    <option value="name">Sort: Title (A–Z)</option>
                  </select>

                  <select
                    value={assetListPageSize}
                    onChange={(e) => { setAssetListPageSize(Number(e.target.value)); setAssetListPage(1); }}
                    style={{
                      height: '31px',
                      padding: '0 8px',
                      fontSize: '0.74rem',
                      borderRadius: '6px',
                      border: '1px solid #E2E8F0',
                      color: '#0F172A',
                      background: '#FFFFFF',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value={15}>15 / page</option>
                    <option value={30}>30 / page</option>
                    <option value={50}>50 / page</option>
                  </select>
                </div>
              </div>

              {/* Clean Table List of Files */}
              {filteredAssets.length === 0 ? (
                <div style={{ padding: '36px 16px', textAlign: 'center', color: '#64748B', fontSize: '0.8rem', background: '#F8FAFC', borderRadius: '8px', border: '1px dashed #CBD5E1' }}>
                  {vaultSubTab === 'documents'
                    ? 'No enterprise policy artifacts match the active governance filter or search criteria.'
                    : 'No external databases or connectors connected yet in this workspace.'}
                </div>
              ) : (
                <div style={{ overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '8px', background: '#FFFFFF' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', color: '#475569', fontSize: '0.67rem', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 700 }}>
                        <th style={{ padding: '9px 14px' }}>{vaultSubTab === 'documents' ? 'POLICY ARTIFACT' : 'CONNECTOR / SOURCE'}</th>
                        <th style={{ padding: '9px 14px' }}>CLASSIFICATION</th>
                        <th style={{ padding: '9px 14px' }}>{vaultSubTab === 'documents' ? 'VERSION & PROVENANCE' : 'AUTHORITY WEIGHT'}</th>
                        <th style={{ padding: '9px 14px', textAlign: 'right' }}>LINEAGE ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pagedAssets.map((item, idx) => (
                        <tr
                          key={item.id}
                          className="trulin-artifact-row"
                          onClick={() => selectAssetItem(item)}
                          style={{
                            borderBottom: idx < pagedAssets.length - 1 ? '1px solid #F1F5F9' : 'none'
                          }}
                        >
                          <td style={{ padding: '10px 14px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <div
                                className="trulin-row-icon-box"
                                style={{
                                  width: '30px',
                                  height: '30px',
                                  borderRadius: '6px',
                                  background: '#FFF7ED',
                                  border: '1px solid #FFEDD5',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  flexShrink: 0
                                }}
                              >
                                {vaultSubTab === 'documents' ? (
                                  <FileText size={15} color="#EA580C" />
                                ) : (
                                  <Database size={15} color="#EA580C" />
                                )}
                              </div>
                              <div style={{ minWidth: 0 }}>
                                <div
                                  className="trulin-row-title"
                                  style={{
                                    fontWeight: 700,
                                    color: '#0F172A',
                                    fontSize: '0.81rem',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis'
                                  }}
                                >
                                  {item.label}
                                </div>
                                {item.data?.external_id && (
                                  <div style={{ fontSize: '0.67rem', color: '#64748B', fontFamily: 'monospace', marginTop: '1px' }}>
                                    {item.data.external_id}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: '10px 14px' }}>
                            <span style={{
                              background: '#FFF7ED',
                              color: '#C2410C',
                              border: '1px solid #FED7AA',
                              padding: '2px 7px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              letterSpacing: '0.02em'
                            }}>
                              {item.subType || item.type}
                            </span>
                          </td>
                          <td style={{ padding: '10px 14px', color: '#64748B', fontSize: '0.73rem' }}>
                            {item.type === 'document'
                              ? `v${item.data?.version_count || 1}.0 • ${item.data?.domain || 'Enterprise'}`
                              : `${item.authority ? `${(Number(item.authority) * 100).toFixed(0)}%` : '95%'} weight`}
                          </td>

                          <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                              <button
                                type="button"
                                className="trulin-inspect-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  selectAssetItem(item);
                                }}
                                style={{
                                  padding: '4px 11px',
                                  borderRadius: '6px',
                                  border: '1px solid #FED7AA',
                                  background: '#FFF7ED',
                                  color: '#EA580C',
                                  fontSize: '0.73rem',
                                  fontWeight: 700,
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px'
                                }}
                              >
                                <span>Inspect Lineage</span>
                                <ChevronRight size={13} className="trulin-inspect-arrow" />
                              </button>

                              {user?.role === 'admin' && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDeleteTargetAsset(item);
                                  }}
                                  title={`Decommission or Purge ${item.label}`}
                                  style={{
                                    padding: '4px 8px',
                                    borderRadius: '6px',
                                    border: '1px solid #FCA5A5',
                                    background: '#FEF2F2',
                                    color: '#DC2626',
                                    fontSize: '0.71rem',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    transition: 'all 0.15s ease'
                                  }}
                                  onMouseEnter={e => { e.currentTarget.style.background = '#FEE2E2'; }}
                                  onMouseLeave={e => { e.currentTarget.style.background = '#FEF2F2'; }}
                                >
                                  <Trash2 size={12} strokeWidth={2.2} />
                                  <span>Delete</span>
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination Footer */}
              {filteredAssets.length > assetListPageSize && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.74rem', color: '#64748B', paddingTop: '4px' }}>
                  <span>
                    Showing {(safePage - 1) * assetListPageSize + 1}–{Math.min(safePage * assetListPageSize, filteredAssets.length)} of {filteredAssets.length}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <button
                      type="button"
                      disabled={safePage <= 1}
                      onClick={() => setAssetListPage(p => Math.max(1, p - 1))}
                      style={{ padding: '4px 10px', border: '1px solid #E2E8F0', borderRadius: '6px', background: '#FFFFFF', cursor: safePage > 1 ? 'pointer' : 'not-allowed', color: safePage > 1 ? '#0F172A' : '#CBD5E1' }}
                    >
                      ‹ Prev
                    </button>
                    <span>Page {safePage} of {totalPages}</span>
                    <button
                      type="button"
                      disabled={safePage >= totalPages}
                      onClick={() => setAssetListPage(p => Math.min(totalPages, p + 1))}
                      style={{ padding: '4px 10px', border: '1px solid #E2E8F0', borderRadius: '6px', background: '#FFFFFF', cursor: safePage < totalPages ? 'pointer' : 'not-allowed', color: safePage < totalPages ? '#0F172A' : '#CBD5E1' }}
                    >
                      Next ›
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        }

        // ============================================================================
        // STAGE 2: SPLIT-SCREEN WORKSPACE (LEFT: ORIGINAL DOCUMENT | RIGHT: FACILITIES)
        // ============================================================================

        const docClaimsForReader = (selectedAsset360?.claims || []).filter(cl => {
          const text = (cl.fullText || cl.label || '').toLowerCase();
          if (docReaderSearch.trim() && !text.includes(docReaderSearch.trim().toLowerCase())) return false;
          const isConf = allConflictedClaimIds.has(cl.id);
          if (docReaderClauseFilter === 'conflicted' && !isConf) return false;
          if (docReaderClauseFilter === 'verified' && isConf) return false;
          return true;
        });

        // Helper to render Asset 360 Details Card content (reused in 2-screen and 3-screen split modes)
        const renderAssetDetailsCard = () => {
          if (!selectedAsset360) return null;
          const isDoc = selectedAsset360.mode === 'document';
          const nodeData = selectedAsset360.node.data || {};
          const docId = nodeData.doc_id || String(selectedAsset360.node.id || '').replace(/^doc_/, '');
          const contentHash = nodeData.content_hash || 'e8f7a912b404d09c31405eb62a71f008432a';
          const versions = nodeData.versions || [];
          const latestVer = versions.length > 0 ? versions[0] : null;
          const trustPercent = selectedAsset360.activeConflicts.length === 0 ? 98 : Math.max(72, 98 - (selectedAsset360.activeConflicts.length * 4));
          const verifiedClaimsCount = (selectedAsset360.claims || []).filter(c =>
            c.status === 'verified' || c.status === 'ACTIVE' || !selectedAsset360.activeConflicts.some(conf => conf.claim_a_id === c.id || conf.claim_b_id === c.id)
          ).length;

          return (
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '10px',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(100vh - 108px)',
              maxHeight: 'calc(100vh - 108px)',
              minHeight: '380px',
              boxShadow: 'none'
            }}>
              {/* Header inside Details Card (Draggable Dark Titlebar) */}
              <div
                draggable={true}
                onDragStart={(e) => {
                  e.dataTransfer.setData('text/plain', 'details');
                  setDraggedPane('details');
                }}
                onDragEnd={() => {
                  setDraggedPane(null);
                  setDragOverPane(null);
                }}
                title="Hold and drag header to move/shuffle tab position"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  padding: '7px 12px',
                  background: 'linear-gradient(180deg, #1E293B 0%, #0F172A 100%)',
                  borderBottom: '1px solid #334155',
                  zIndex: 15,
                  cursor: 'grab',
                  userSelect: 'none',
                  flexShrink: 0
                }}
              >
                <div
                  onClick={(e) => e.stopPropagation()}
                  onMouseDown={(e) => e.stopPropagation()}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'default' }}
                >
                  <button
                    type="button"
                    onClick={() => setIsDetailsOpen(false)}
                    title="Close details panel"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '22px',
                      height: '22px',
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
                </div>
              </div>

              {/* Scrollable Content Body for Asset Details */}
              <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                background: '#FFFFFF'
              }}>
                {/* Governance Description */}
                <p style={{ margin: 0, fontSize: '0.78rem', color: '#475569', lineHeight: 1.5 }}>
                  {selectedAsset360.description || `Enterprise normalized governance asset. Deconstructed into atomic facts and verified against cross-policy contradictions.`}
                </p>

              {/* Core Metrics Summary */}
              <div style={{
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                overflow: 'hidden',
                background: '#FFFFFF'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.74rem' }}>
                  <tbody>
                    {[
                      {
                        label: 'Atomic Claims',
                        value: selectedAsset360.claims.length,
                        badge: `${verifiedClaimsCount} verified`,
                        badgeColor: '#16A34A',
                        badgeBg: '#DCFCE7'
                      },
                      {
                        label: 'Contradictions',
                        value: selectedAsset360.activeConflicts.length,
                        valueColor: selectedAsset360.activeConflicts.length > 0 ? '#EA580C' : '#0F172A',
                        badge: selectedAsset360.conflicts.length > 0
                          ? `${selectedAsset360.activeConflicts.length} active / ${selectedAsset360.conflicts.length} total`
                          : '0 detected',
                        badgeColor: selectedAsset360.activeConflicts.length > 0 ? '#C2410C' : '#16A34A',
                        badgeBg: selectedAsset360.activeConflicts.length > 0 ? '#FFEDD5' : '#DCFCE7'
                      },
                      {
                        label: 'Trust Integrity',
                        value: `${trustPercent}%`,
                        valueColor: '#16A34A',
                        badge: trustPercent >= 70 ? 'High Trust' : trustPercent >= 40 ? 'Moderate' : 'Low',
                        badgeColor: '#059669',
                        badgeBg: '#ECFDF5'
                      },
                      {
                        label: 'Downstream AI Impact',
                        value: selectedAsset360.decisions.length,
                        valueColor: '#0284C7',
                        badge: `${selectedAsset360.decisions.length} Decisions`,
                        badgeColor: '#0284C7',
                        badgeBg: '#E0F2FE'
                      }
                    ].map((row, idx, arr) => (
                      <tr
                        key={row.label}
                        style={{
                          borderBottom: idx < arr.length - 1 ? '1px solid #F1F5F9' : 'none'
                        }}
                      >
                        <td style={{ padding: '6px 10px', color: '#475569', fontWeight: 600, width: '40%' }}>
                          {row.label}
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '0.84rem', fontWeight: 800, color: row.valueColor || '#0F172A' }}>
                              {row.value}
                            </span>
                            {row.badge && (
                              <span style={{
                                fontSize: '0.64rem',
                                fontWeight: 700,
                                color: row.badgeColor,
                                background: row.badgeBg || '#F1F5F9',
                                padding: '1px 5px',
                                borderRadius: '4px'
                              }}>
                                {row.badge}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Complete Metadata & Technical Specifications Table */}
              <div style={{
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                <div style={{
                  padding: '8px 12px',
                  background: '#F8FAFC',
                  borderBottom: '1px solid #E2E8F0',
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  color: '#334155',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <Layers size={12} color="#475569" />
                  <span>Technical Specifications</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {[
                    { label: 'Artifact GUID', value: docId, isMono: true },
                    { label: 'Parent Source', value: selectedAsset360.parentSource?.label || 'Direct File Upload' },
                    { label: 'Classification', value: 'Restricted Policy Standard' },
                    { label: 'Active Version', value: latestVer ? `v${latestVer.version_number}` : 'v1.0' },
                    { label: 'Pipeline Engine', value: 'Trulin Semantic Deconstruction' },
                    { label: 'Department / Scope', value: nodeData.domain || (activeWorkspace?.label || 'Enterprise Unified') },
                    {
                      label: 'SHA-256 Merkle Hash',
                      value: contentHash,
                      isMono: true,
                      canCopy: true
                    }
                  ].map((row, idx, arr) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 12px',
                        borderBottom: idx < arr.length - 1 ? '1px solid #F1F5F9' : 'none',
                        gap: '8px',
                        fontSize: '0.72rem'
                      }}
                    >
                      <span style={{ color: '#64748B', fontWeight: 600 }}>
                        {row.label}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', maxWidth: '60%' }}>
                        <span style={{
                          color: '#0F172A',
                          fontWeight: 600,
                          fontFamily: row.isMono ? 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' : 'inherit',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {row.value}
                        </span>
                        {row.canCopy && (
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard?.writeText(row.value);
                              setCopiedHash(true);
                              setTimeout(() => setCopiedHash(false), 2000);
                              showToast?.("Hash copied to clipboard");
                            }}
                            style={{
                              border: 'none',
                              background: 'transparent',
                              cursor: 'pointer',
                              color: copiedHash ? '#16A34A' : '#94A3B8',
                              padding: '1px',
                              display: 'flex',
                              alignItems: 'center'
                            }}
                            title="Copy hash"
                          >
                            {copiedHash ? <Check size={12} /> : <Copy size={12} />}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            </div>
          );
        };

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', width: '100%' }}>

            {/* CLEAN MINIMALIST EXECUTIVE HEADER: MINIMAL BACK BUTTON (<), FILE NAME, TOGGLE FILE VIEW, & UNDERLINED TABS */}
            {selectedAsset360 && (
              <div style={{
                background: 'transparent',
                border: 'none',
                boxShadow: 'none',
                padding: '0',
                marginBottom: '2px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}>
                {/* Top Row: Minimal Back Button (<), File Name, and File Viewer Toggle / Stepper */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => {
                        setOpenedAssetId(null);
                        onAssetChange?.(null);
                      }}
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '6px',
                        border: '1px solid #E2E8F0',
                        background: '#FFFFFF',
                        color: '#0F172A',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        padding: 0,
                        boxShadow: 'none',
                        transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)'
                      }}
                      title={`Back to ${vaultSubTab === 'documents' ? 'Documents' : 'Connectors'} list`}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = '#FFF7ED';
                        e.currentTarget.style.borderColor = '#FED7AA';
                        e.currentTarget.style.color = '#EA580C';
                        e.currentTarget.style.transform = 'translateX(-2px)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = '#FFFFFF';
                        e.currentTarget.style.borderColor = '#E2E8F0';
                        e.currentTarget.style.color = '#0F172A';
                        e.currentTarget.style.transform = 'none';
                      }}
                    >
                      <ChevronLeft size={16} strokeWidth={2.5} />
                    </button>

                    <h2 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
                      {selectedAsset360.node.label}
                    </h2>

                    {/* Universal File Viewer Trigger Button: Available only in Overview tab when minimized */}
                    {asset360Section === 'summary' && !isFileViewerOpen && (
                      <button
                        type="button"
                        onClick={() => {
                          setIsFileViewerOpen(true);
                          showToast?.("Document preview opened");
                        }}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          border: '1px solid #EA580C',
                          background: '#FFF7ED',
                          color: '#EA580C',
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                          transition: 'all 0.15s ease'
                        }}
                        title="Open document preview"
                      >
                        <FileText size={13} color="#EA580C" />
                        <span>Open Document Preview</span>
                      </button>
                    )}

                    {selectedAsset360.mode === 'document' && (
                      <a
                        href={`/v1/documents/${selectedAsset360.node.data?.doc_id || String(selectedAsset360.node.id || '').replace(/^doc_/, '')}/file`}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '4px 9px',
                          borderRadius: '6px',
                          border: '1px solid #E2E8F0',
                          background: '#FFFFFF',
                          color: '#0284C7',
                          fontSize: '0.74rem',
                          fontWeight: 600,
                          textDecoration: 'none',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                        }}
                        title="Open document file in a new browser tab"
                      >
                        <ExternalLink size={12} />
                        <span>Open File ↗</span>
                      </a>
                    )}

                    {/* Details Symbol Toggle Button (Placed at top of filename, right after Open File) */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsDetailsOpen(prev => !prev);
                        showToast?.(!isDetailsOpen ? "Details pane opened in split view" : "Details pane closed");
                      }}
                      title={isDetailsOpen ? "Hide Asset Details" : "Show Asset Details"}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 9px',
                        borderRadius: '6px',
                        border: isDetailsOpen ? '1px solid #EA580C' : '1px solid #E2E8F0',
                        background: isDetailsOpen ? '#FFF7ED' : '#FFFFFF',
                        color: isDetailsOpen ? '#EA580C' : '#475569',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <Info size={13} color={isDetailsOpen ? '#EA580C' : '#64748B'} />
                      <span>Details</span>
                    </button>

                    {user?.role === 'admin' && (
                      <button
                        type="button"
                        onClick={() => setDeleteTargetAsset(selectedAsset360.node)}
                        title={`Decommission or Purge ${selectedAsset360.node.label}`}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          border: '1px solid #FCA5A5',
                          background: '#FEF2F2',
                          color: '#DC2626',
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          boxShadow: '0 1px 2px rgba(220,38,38,0.06)',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#FEE2E2'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = '#FEF2F2'; }}
                      >
                        <Trash2 size={13} strokeWidth={2.2} />
                        <span>Delete Asset</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Plane Text Tabs with Separator Line */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  borderBottom: '1px solid #E2E8F0',
                  paddingBottom: '0px',
                  marginTop: '0px',
                  overflowX: 'auto'
                }}>
                  {[
                    { id: 'summary', label: 'Overview' },
                    { id: 'dag', label: 'Lineage' },
                    { id: 'extraction', label: 'Visual Claim Extraction' },
                    { id: 'claims', label: `Claims (${selectedAsset360.claims.length})` },
                    { id: 'conflicts', label: `Conflicts (${selectedAsset360.conflicts.length})` },
                    { id: 'all', label: 'All Facilities' }
                  ].map(sec => {
                    const active = asset360Section === sec.id;
                    return (
                      <button
                        key={sec.id}
                        type="button"
                        onClick={() => {
                          handleSectionChange(sec.id);
                          if (sec.id === 'dag' || sec.id === 'summary') {
                            setActiveClaimInspector(null);
                            const docNodeId = selectedAsset360?.node?.id || openedAssetId;
                            if (docNodeId) {
                              setSelectedNodeId(docNodeId);
                              setInteractiveRootId(docNodeId);
                              setExpandedUpstreamSet(new Set([docNodeId]));
                              setExpandedDownstreamSet(new Set([docNodeId]));
                              setLineageGranularity('document');
                            }
                          }
                          showToast?.(`Switched facility to ${sec.label}`);
                        }}
                        onMouseEnter={e => {
                          if (!active) e.currentTarget.style.color = '#0F172A';
                        }}
                        onMouseLeave={e => {
                          if (!active) e.currentTarget.style.color = '#64748B';
                        }}
                        style={{
                          padding: '5px 2px',
                          border: 'none',
                          outline: 'none',
                          background: 'transparent',
                          boxShadow: 'none',
                          borderBottom: active ? '2px solid #EA580C' : '2px solid transparent',
                          color: active ? '#EA580C' : '#64748B',
                          fontSize: '0.84rem',
                          fontWeight: active ? 700 : 500,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          transition: 'color 0.15s ease, border-color 0.15s ease',
                          marginBottom: '-1px'
                        }}
                      >
                        {sec.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* SIDE-BY-SIDE SPLIT LAYOUT (VS CODE STYLE RESIZABLE): DYNAMIC SHUFFLEABLE PANES (DOC | DETAILS | DAG) */}
            {(() => {
              const showDoc = Boolean(isFileViewerOpen && asset360Section === 'summary' && (vaultSubTab === 'documents' || vaultSubTab === 'connectors') && selectedAsset360);
              const showDetails = Boolean(isDetailsOpen && asset360Section === 'summary' && selectedAsset360);
              const showDag = Boolean((activeClaimInspector && asset360Section === 'summary' && selectedAsset360) || asset360Section === 'dag' || asset360Section === 'all' || vaultSubTab === 'dag');

              if (selectedAsset360 && (asset360Section === 'extraction')) {
                return (
                  <VisualClaimExtractionStudio
                    documentTitle={selectedAsset360.node.label}
                    documentId={selectedAsset360.node.data?.doc_id || selectedAsset360.node.id}
                    claims={selectedAsset360.claims}
                    conflicts={selectedAsset360.conflicts}
                    rawOriginalText={selectedAsset360.node.data?.content_uri || ''}
                    onHighlightClause={(clause) => {
                      setDocReaderClauseFilter('raw');
                      showToast?.(`Locating clause in document view: "${clause.substring(0, 45)}..."`);
                    }}
                    showToast={showToast}
                  />
                );
              }

              if (selectedAsset360 && (asset360Section === 'claims')) {
                return (
                  <AssetClaimsStudioPane
                    asset={selectedAsset360}
                    claims={selectedAsset360.claims}
                    allConflictedClaimIds={allConflictedClaimIds}
                    graphData={graphData}
                    onLocateInDoc={(claim) => {
                      handleSectionChange('summary');
                      setIsFileViewerOpen(true);
                      setIsDetailsOpen(true);
                      setActiveClaimInspector(claim);
                      const cid = claim.cleanId || String(claim.id || '').replace(/^cl_/, '');
                      const targetId = claim.id.startsWith('cl_') ? claim.id : `cl_${cid}`;
                      const matchedNode = graphData?.nodes?.find(n => n.id === targetId || n.id === claim.id || n.id === `cl_${claim.id}`);
                      const actualNodeId = matchedNode ? matchedNode.id : targetId;
                      setSelectedNodeId(actualNodeId);
                      setInteractiveRootId(actualNodeId);
                      fetchBlastRadius(cid);
                      showToast?.(`Locating claim in document canvas: "${(claim.label || claim.fullText || '').substring(0, 45)}..."`);
                    }}
                    onInspectInDag={(claim) => {
                      const cid = claim.cleanId || String(claim.id || '').replace(/^cl_/, '');
                      const targetId = claim.id.startsWith('cl_') ? claim.id : `cl_${cid}`;
                      const matchedNode = graphData?.nodes?.find(n => n.id === targetId || n.id === claim.id || n.id === `cl_${claim.id}`);
                      const actualNodeId = matchedNode ? matchedNode.id : targetId;
                      setActiveClaimInspector(claim);
                      setSelectedNodeId(actualNodeId);
                      setInteractiveRootId(actualNodeId);
                      setViewMode('interactive');
                      setLineageGranularity('claim');
                      setExpandedUpstreamSet(new Set([actualNodeId, selectedAsset360.node.id]));
                      setExpandedDownstreamSet(new Set([actualNodeId]));
                      setExpandedConflictClaimsSet(new Set());
                      handleSectionChange('dag');
                      fetchBlastRadius(cid);
                      showToast?.(`Loaded claim "${(claim.label || '').substring(0, 35)}" in Interactive Lineage DAG`);
                      setTimeout(() => handleFitView(), 150);
                    }}
                    showToast={showToast}
                  />
                );
              }

              if (selectedAsset360 && (asset360Section === 'conflicts')) {
                return (
                  <AssetConflictsStudioPane
                    asset={selectedAsset360}
                    conflicts={selectedAsset360.conflicts}
                    conflictMap={conflictMap}
                    graphData={graphData}
                    onFocusInDag={(conflict) => {
                      const cItem = conflictMap[conflict.id];
                      const isResolved = (conflict.status || '').toLowerCase() === 'resolved' || (conflict.status || '').toLowerCase() === 'dismissed';
                      if (isResolved) setFilterStatus('all');
                      setSelectedNodeId(conflict.id);
                      setInteractiveRootId(conflict.id);
                      setExpandedDownstreamSet(prev => new Set(prev).add(selectedAsset360.node.id));
                      if (cItem?.claimAId) setExpandedConflictClaimsSet(prev => new Set(prev).add(cItem.claimAId));
                      if (cItem?.claimBId) setExpandedConflictClaimsSet(prev => new Set(prev).add(cItem.claimBId));
                      handleSectionChange('dag');
                      showToast?.(`Focused conflict "${conflict.label}" in Interactive Lineage DAG`);
                      setTimeout(() => handleFitView(), 150);
                    }}
                    onLocateInDoc={(claim) => {
                      handleSectionChange('summary');
                      setIsFileViewerOpen(true);
                      setIsDetailsOpen(true);
                      setActiveClaimInspector(claim);
                      const cid = claim.cleanId || String(claim.id || '').replace(/^cl_/, '');
                      const targetId = claim.id.startsWith('cl_') ? claim.id : `cl_${cid}`;
                      const matchedNode = graphData?.nodes?.find(n => n.id === targetId || n.id === claim.id || n.id === `cl_${claim.id}`);
                      const actualNodeId = matchedNode ? matchedNode.id : targetId;
                      setSelectedNodeId(actualNodeId);
                      setInteractiveRootId(actualNodeId);
                      fetchBlastRadius(cid);
                      showToast?.(`Locating assertion in document canvas: "${(claim.label || claim.fullText || '').substring(0, 45)}..."`);
                    }}
                    showToast={showToast}
                  />
                );
              }

              const activePanes = paneOrder.filter(id => {
                if (id === 'doc') return showDoc;
                if (id === 'details') return showDetails;
                if (id === 'dag') return showDag;
                return false;
              });

              const isThreePane = activePanes.length === 3;
              const isTwoPane = activePanes.length === 2;
              const isSplitActive = activePanes.length > 1;

              const renderDocPane = () => {
                const rawDocId = selectedAsset360.node.data?.doc_id || String(selectedAsset360.node.id || '').replace(/^doc_/, '');
                const rawOriginalText = selectedAsset360.node.data?.content_uri || '';

                return selectedAsset360.mode === 'document' ? (
                  <SmartDocumentCanvas
                    documentNode={selectedAsset360.node}
                    documentId={rawDocId}
                    claims={selectedAsset360.claims}
                    conflicts={selectedAsset360.conflicts}
                    rawOriginalText={rawOriginalText}
                    onVisualizeInDag={(nodeId, label) => visualizeNodeInDag(nodeId, label)}
                    onNavigateToTab={(tabName) => setVaultSubTab(tabName)}
                    showToast={showToast}
                    onDragStartHandle={() => setDraggedPane('doc')}
                    onDragEndHandle={() => {
                      setDraggedPane(null);
                      setDragOverPane(null);
                    }}
                    onMinimize={() => {
                      setIsFileViewerOpen(false);
                      showToast?.("Document preview minimized");
                    }}
                    onSelectClaim={(claim) => {
                      const cid = claim.cleanId || String(claim.id || '').replace(/^cl_/, '');
                      const targetId = claim.id.startsWith('cl_') ? claim.id : `cl_${cid}`;
                      const matchedNode = graphData?.nodes?.find(n => n.id === targetId || n.id === claim.id || n.id === `cl_${claim.id}`);
                      const actualNodeId = matchedNode ? matchedNode.id : targetId;

                      setActiveClaimInspector(claim);
                      setIsDetailsOpen(true);
                      setSelectedNodeId(actualNodeId);
                      setInteractiveRootId(actualNodeId);
                      setViewMode('interactive');
                      setLineageGranularity('claim');
                      setExpandedUpstreamSet(new Set([actualNodeId]));
                      setExpandedDownstreamSet(new Set([actualNodeId]));
                      setExpandedConflictClaimsSet(new Set());
                      fetchBlastRadius(cid);
                      setTimeout(() => handleFitView(), 120);
                      setTimeout(() => handleFitView(), 320);
                    }}
                    selectedClaimId={activeClaimInspector?.cleanId || activeClaimInspector?.id}
                  />
                ) : (
                  <div style={{
                    background: '#FFFFFF',
                    border: '1px solid #CBD5E1',
                    borderRadius: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    height: 'calc(100vh - 108px)',
                    maxHeight: 'calc(100vh - 108px)',
                    minHeight: '380px',
                    overflow: 'hidden'
                  }}>
                    <div
                      draggable={true}
                      onDragStart={(e) => {
                        e.dataTransfer.setData('text/plain', 'doc');
                        setDraggedPane('doc');
                      }}
                      onDragEnd={() => {
                        setDraggedPane(null);
                        setDragOverPane(null);
                      }}
                      title="Hold and drag header to move/shuffle tab position"
                      style={{
                        padding: '7px 12px',
                        background: 'linear-gradient(180deg, #1E293B 0%, #0F172A 100%)',
                        borderBottom: '1px solid #334155',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'flex-end',
                        gap: '8px',
                        cursor: 'grab',
                        userSelect: 'none'
                      }}
                    >
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setIsFileViewerOpen(false);
                          showToast?.("Source preview minimized");
                        }}
                        title="Minimize source preview"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '22px',
                          height: '22px',
                          borderRadius: '5px',
                          border: '1px solid rgba(255,255,255,0.15)',
                          background: 'rgba(255, 255, 255, 0.08)',
                          color: '#CBD5E1',
                          cursor: 'pointer'
                        }}
                      >
                        <X size={13} strokeWidth={2.4} />
                      </button>
                    </div>
                    <div style={{
                      flex: 1,
                      padding: '18px 20px',
                      overflowY: 'auto',
                      background: '#FFFFFF',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}>
                      <div style={{ fontSize: '0.8rem', color: '#334155', lineHeight: 1.55 }}>
                        <strong>Connector Source:</strong> {selectedAsset360.node.label}<br />
                        <strong>Source Type:</strong> {(selectedAsset360.node.subType || 'DATABASE').toUpperCase()}<br />
                        <strong>Authority Level:</strong> {selectedAsset360.node.authority ? `${(Number(selectedAsset360.node.authority) * 100).toFixed(0)}%` : '95%'}<br />
                        <strong>Synced Records:</strong> {selectedAsset360.connectedDocs.length} Objects &bull; {selectedAsset360.claims.length} Claims
                      </div>
                      {selectedAsset360.connectedDocs.map(d => (
                        <div key={d.id} style={{ padding: '10px 12px', borderRadius: '6px', border: '1px solid #E2E8F0', background: '#F8FAFC', fontSize: '0.78rem', fontWeight: 600, color: '#0F172A' }}>
                          {d.label}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              };

              const renderDetailsPane = () => (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    height: 'calc(100vh - 108px)',
                    maxHeight: 'calc(100vh - 108px)',
                    minHeight: '380px',
                    width: '100%'
                  }}
                >
                  {renderAssetDetailsCard()}
                </div>
              );

              const renderDagFacility = () => (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
{/* Unified Executive Lineage Command Card (Single Card Container) - Hidden in Overview mode as it concentrates on a single claim */}
      {asset360Section !== 'summary' && (
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '10px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.02)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        width: '100%',
        boxSizing: 'border-box'
      }}>
        {/* Row 1: Primary Command Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '6px 12px',
          background: '#F8FAFC',
          borderBottom: isFilterPanelOpen ? '1px solid #E2E8F0' : 'none'
        }}>
          {/* Left Group: Granularity & View Modes */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Context Investigation Lenses (Scaling Engine for Large-Scale Context Graphs) */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: '#EDF2F7',
              padding: '2px',
              borderRadius: '7px',
              border: '1px solid #E2E8F0',
              gap: '2px'
            }}>
              <button
                type="button"
                onClick={() => {
                  setInvestigationLens('risk');
                  setViewMode('conflicts');
                  const firstConf = conflictsList[0];
                  if (firstConf) setSelectedNodeId(firstConf.id);
                  showToast?.("Switched to Risk & Conflict Investigation Lens");
                }}
                style={{
                  padding: '3px 9px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  borderRadius: '5px',
                  border: 'none',
                  cursor: 'pointer',
                  background: investigationLens === 'risk' ? '#EA580C' : 'transparent',
                  color: investigationLens === 'risk' ? '#FFFFFF' : '#C2410C',
                  boxShadow: investigationLens === 'risk' ? '0 1px 3px rgba(234,88,12,0.3)' : 'none',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  height: '25px'
                }}
                title="Focus on contradictions, anomalies, and severed flows"
              >
                <AlertTriangle size={11} />
                <span>Risk & Conflicts ({conflictsList.length})</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setInvestigationLens('decision');
                  setViewMode('interactive');
                  showToast?.("Switched to AI Decision Impact Lens");
                }}
                style={{
                  padding: '3px 9px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  borderRadius: '5px',
                  border: 'none',
                  cursor: 'pointer',
                  background: investigationLens === 'decision' ? '#7C3AED' : 'transparent',
                  color: investigationLens === 'decision' ? '#FFFFFF' : '#6B21A8',
                  boxShadow: investigationLens === 'decision' ? '0 1px 3px rgba(124,58,237,0.3)' : 'none',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  height: '25px'
                }}
                title="Trace policy rules directly to AI Copilot decisions"
              >
                <span>🤖 AI Impact</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setInvestigationLens('evidence');
                  setViewMode('interactive');
                  showToast?.("Switched to Evidence & Provenance Trace Lens");
                }}
                style={{
                  padding: '3px 9px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  borderRadius: '5px',
                  border: 'none',
                  cursor: 'pointer',
                  background: investigationLens === 'evidence' ? '#2563EB' : 'transparent',
                  color: investigationLens === 'evidence' ? '#FFFFFF' : '#1E40AF',
                  boxShadow: investigationLens === 'evidence' ? '0 1px 3px rgba(37,99,235,0.3)' : 'none',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  height: '25px'
                }}
                title="Trace claim evidence spans back to original document text"
              >
                <ShieldCheck size={12} />
                <span>Evidence Trace</span>
              </button>
            </div>


            {/* Interactive Flow Quick Controls */}
            {viewMode === 'interactive' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <button
                  type="button"
                  onClick={resetToSingleNode}
                  style={{
                    padding: '3px 9px',
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    borderRadius: '5px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    color: '#334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    height: '25px',
                    transition: 'all 0.15s ease'
                  }}
                  title="Reset canvas to only the single starting node"
                >
                  <RotateCcw size={11} />
                  <span>Single Node</span>
                </button>

                <button
                  type="button"
                  onClick={expandAllFlow}
                  style={{
                    padding: '3px 9px',
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    borderRadius: '5px',
                    border: '1px solid #BFDBFE',
                    background: '#EFF6FF',
                    color: '#1D4ED8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    height: '25px',
                    transition: 'all 0.15s ease'
                  }}
                  title="Expand all upstream and downstream connections"
                >
                  <span>➕ Expand All</span>
                </button>
              </div>
            )}
          </div>

          {/* Right Group: Action Tools */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={() => setIsFilterPanelOpen(prev => !prev)}
              style={{
                padding: '4px 10px',
                fontSize: '0.70rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: activeFilterCount > 0 ? '1px solid #EA580C' : (isFilterPanelOpen ? '1px solid #CBD5E1' : '1px solid #E2E8F0'),
                background: isFilterPanelOpen || activeFilterCount > 0 ? '#FFF7ED' : '#FFFFFF',
                color: isFilterPanelOpen || activeFilterCount > 0 ? '#EA580C' : '#334155',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                height: '27px',
                transition: 'all 0.15s ease'
              }}
              title="Toggle Filters"
            >
              <Sliders size={12} />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span style={{
                  background: '#EA580C',
                  color: '#FFFFFF',
                  borderRadius: '10px',
                  padding: '1px 5px',
                  fontSize: '0.62rem',
                  fontWeight: 800,
                  lineHeight: 1
                }}>
                  {activeFilterCount}
                </span>
              )}
              <ChevronDown size={11} style={{ transform: isFilterPanelOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
            </button>

            <button
              onClick={() => setIsDrawerOpen(true)}
              style={{
                padding: '4px 10px',
                fontSize: '0.70rem',
                fontWeight: 600,
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#334155',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                height: '27px',
                transition: 'all 0.15s ease'
              }}
              title="Claims Drawer"
            >
              <FileText size={12} color="#64748B" />
              <span>Claims</span>
              <span style={{
                background: '#F1F5F9',
                color: '#475569',
                borderRadius: '10px',
                padding: '1px 5px',
                fontSize: '0.62rem',
                fontWeight: 700
              }}>
                {graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0}
              </span>
            </button>

            <button
              onClick={() => setIsImpactReportOpen(true)}
              style={{
                padding: '4px 10px',
                fontSize: '0.70rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: '1px solid #DDD6FE',
                background: isImpactReportOpen ? '#7C3AED' : 'linear-gradient(135deg, #FAF5FF 0%, #F3E8FF 100%)',
                color: isImpactReportOpen ? '#FFFFFF' : '#7C3AED',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                height: '27px',
                boxShadow: isImpactReportOpen ? '0 1px 3px rgba(124,58,237,0.3)' : '0 1px 2px rgba(124,58,237,0.06)',
                transition: 'all 0.15s ease'
              }}
              title="Open Proactive Impact & Blast Radius Report"
            >
              <BarChart3 size={12} />
              <span>Impact Report</span>
            </button>

            <button
              onClick={fetchLineage}
              disabled={loading}
              style={{
                padding: '4px 8px',
                fontSize: '0.70rem',
                fontWeight: 600,
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#475569',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '27px',
                transition: 'all 0.15s ease'
              }}
              title="Refresh Graph"
            >
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* Row 2: Integrated Filter Section (Inside the SAME Card) */}
        {isFilterPanelOpen && (
          <div style={{
            borderTop: '1px solid #E2E8F0',
            padding: '8px 12px',
            background: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px'
          }}>
            {/* Filter Selects Strip */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap'
            }}>
              {/* Conflict Selector */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: selectedConflictId !== 'all' ? '#FFF7ED' : '#F8FAFC',
                border: selectedConflictId !== 'all' ? '1px solid #FDBA74' : '1px solid #E2E8F0',
                padding: '2px 6px',
                borderRadius: '6px'
              }}>
                <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#EA580C', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                  Conflict
                </span>
                <select
                  value={selectedConflictId}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedConflictId(val);
                    if (val !== 'all') {
                      setSelectedNodeId(val);
                      setViewMode('conflicts');
                      showToast?.(`Spotlighted Conflict in DAG`);
                    }
                  }}
                  style={{
                    padding: '2px 4px',
                    border: 'none',
                    background: 'transparent',
                    fontSize: '0.69rem',
                    fontWeight: selectedConflictId !== 'all' ? 700 : 500,
                    color: selectedConflictId !== 'all' ? '#C2410C' : '#334155',
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="all">All ({conflictsList.length})</option>
                  {conflictsList.map((c, i) => (
                    <option key={c.id} value={c.id}>
                      #{i + 1} [{c.severity || 'HIGH'}] {c.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Conflict Status Selector */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: filterStatus === 'active' ? '#FFF7ED' : '#F8FAFC',
                border: filterStatus === 'active' ? '1px solid #FDBA74' : '1px solid #E2E8F0',
                padding: '2px 6px',
                borderRadius: '6px'
              }}>
                <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#EA580C', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                  Status
                </span>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  style={{
                    padding: '2px 4px',
                    border: 'none',
                    background: 'transparent',
                    fontSize: '0.69rem',
                    color: filterStatus === 'active' ? '#C2410C' : '#334155',
                    fontWeight: 700,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="active">Active / Unresolved Only</option>
                  <option value="resolved">Resolved Only</option>
                  <option value="all">All (Active + Resolved)</option>
                </select>
              </div>

              {/* Severity Selector */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: filterSeverity !== 'all' ? '#EFF6FF' : '#F8FAFC',
                border: filterSeverity !== 'all' ? '1px solid #BFDBFE' : '1px solid #E2E8F0',
                padding: '2px 6px',
                borderRadius: '6px'
              }}>
                <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                  Severity
                </span>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  style={{
                    padding: '2px 4px',
                    border: 'none',
                    background: 'transparent',
                    fontSize: '0.69rem',
                    color: filterSeverity !== 'all' ? '#1D4ED8' : '#334155',
                    fontWeight: filterSeverity !== 'all' ? 700 : 500,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="all">All</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="MEDIUM">Med</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              {/* Trust Selector */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: filterClaimTrust !== 'all' ? '#F0FDF4' : '#F8FAFC',
                border: filterClaimTrust !== 'all' ? '1px solid #BBF7D0' : '1px solid #E2E8F0',
                padding: '2px 6px',
                borderRadius: '6px'
              }}>
                <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#16A34A', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                  Trust
                </span>
                <select
                  value={filterClaimTrust}
                  onChange={(e) => setFilterClaimTrust(e.target.value)}
                  style={{
                    padding: '2px 4px',
                    border: 'none',
                    background: 'transparent',
                    fontSize: '0.69rem',
                    color: filterClaimTrust !== 'all' ? '#15803D' : '#334155',
                    fontWeight: filterClaimTrust !== 'all' ? 700 : 500,
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="all">All</option>
                  <option value="verified">Verified (≥90%)</option>
                  <option value="review">Review (&lt;90%)</option>
                  <option value="outdated">Outdated</option>
                </select>
              </div>

              {/* Conflicted Only Quick Toggle */}
              <button
                type="button"
                onClick={() => {
                  setShowOnlyConflicted(prev => !prev);
                  if (!showOnlyConflicted) showToast?.("Focused on contradictory paths");
                }}
                style={{
                  padding: '2px 8px',
                  borderRadius: '5px',
                  fontSize: '0.67rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: showOnlyConflicted ? '1px solid #EA580C' : '1px solid #CBD5E1',
                  background: showOnlyConflicted ? '#EA580C' : '#FFFFFF',
                  color: showOnlyConflicted ? '#FFFFFF' : '#475569',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  height: '24px'
                }}
              >
                <AlertTriangle size={11} />
                <span>Conflicted Only</span>
                {showOnlyConflicted && <span>✓</span>}
              </button>
            </div>

            {/* Reset Filters (Only when a filter is active) */}
            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={resetAllFilters}
                style={{
                  padding: '3px 8px',
                  borderRadius: '5px',
                  border: '1px solid #FCA5A5',
                  background: '#FEF2F2',
                  color: '#DC2626',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                  height: '24px'
                }}
                title="Reset all filters"
              >
                <RotateCcw size={10} />
                <span>Reset Filters</span>
              </button>
            )}
          </div>
        )}
      </div>
      )}

      {/* 3. Interactive DAG Canvas */}
      <div style={{
        position: 'relative',
        width: '100%',
        borderRadius: '10px',
        overflow: 'hidden',
        border: '1px solid #CBD5E1',
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        height: isSplitActive ? 'calc(100vh - 108px)' : 'auto',
        maxHeight: isSplitActive ? 'calc(100vh - 108px)' : 'none',
        minHeight: isSplitActive ? '380px' : 'auto'
      }}>
        
        {/* Sticky Top Header Bar for DAG (Draggable in Split View, Normal White Header in Individual Lineage View) */}
        <div
          draggable={isSplitActive}
          onDragStart={isSplitActive ? (e) => {
            e.dataTransfer.setData('text/plain', 'dag');
            setDraggedPane('dag');
          } : undefined}
          onDragEnd={isSplitActive ? () => {
            setDraggedPane(null);
            setDragOverPane(null);
          } : undefined}
          title={isSplitActive ? "Hold and drag header to move/shuffle tab position" : undefined}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            padding: '6px 12px',
            background: isSplitActive ? 'linear-gradient(180deg, #1E293B 0%, #0F172A 100%)' : '#FFFFFF',
            borderBottom: isSplitActive ? '1px solid #334155' : '1px solid #E2E8F0',
            zIndex: 30,
            cursor: isSplitActive ? 'grab' : 'default',
            userSelect: isSplitActive ? 'none' : 'auto',
            flexShrink: 0
          }}
        >
          {/* Right: Floating Controls (Search, Zoom, Fit, Close) */}
          <div
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: isSplitActive ? 'rgba(255, 255, 255, 0.10)' : '#F8FAFC',
              padding: '2px 5px',
              borderRadius: '6px',
              border: isSplitActive ? '1px solid rgba(255,255,255,0.15)' : '1px solid #E2E8F0',
              cursor: 'default'
            }}
          >
            {/* Find in canvas (Global across all nodes) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '3px', paddingRight: '4px', borderRight: isSplitActive ? '1px solid rgba(255,255,255,0.15)' : '1px solid #E2E8F0' }}>
              <span style={{ fontSize: '0.66rem', color: isSplitActive ? '#94A3B8' : '#64748B' }}>🔍</span>
              <input
                type="text"
                placeholder="Find..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  fontSize: '0.68rem',
                  outline: 'none',
                  width: isThreePane ? '56px' : '82px',
                  color: isSplitActive ? '#F8FAFC' : '#0F172A',
                  transition: 'width 0.15s ease'
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: isSplitActive ? '#CBD5E1' : '#64748B', fontSize: '0.66rem', padding: '0 2px' }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* Zoom Controls */}
            <button
              onClick={() => setZoom(z => Math.max(0.4, Number((z - 0.1).toFixed(2))))}
              className="canvas-btn"
              style={{
                width: '19px',
                height: '19px',
                borderRadius: '4px',
                border: isSplitActive ? '1px solid rgba(255,255,255,0.2)' : '1px solid #E2E8F0',
                background: isSplitActive ? 'rgba(255,255,255,0.1)' : '#FFFFFF',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '0.74rem',
                color: isSplitActive ? '#F8FAFC' : '#334155',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0
              }}
              title="Zoom Out"
            >
              -
            </button>
            <span style={{ fontSize: '0.65rem', fontWeight: 700, minWidth: '25px', textAlign: 'center', color: isSplitActive ? '#CBD5E1' : '#475569' }}>
              {(zoom * 100).toFixed(0)}%
            </span>
            <button
              onClick={() => setZoom(z => Math.min(1.4, Number((z + 0.1).toFixed(2))))}
              className="canvas-btn"
              style={{
                width: '19px',
                height: '19px',
                borderRadius: '4px',
                border: isSplitActive ? '1px solid rgba(255,255,255,0.2)' : '1px solid #E2E8F0',
                background: isSplitActive ? 'rgba(255,255,255,0.1)' : '#FFFFFF',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '0.74rem',
                color: isSplitActive ? '#F8FAFC' : '#334155',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0
              }}
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={handleFitView}
              className="canvas-btn"
              style={{
                padding: '0 6px',
                height: '20px',
                borderRadius: '4px',
                border: isSplitActive ? '1px solid #3B82F6' : '1px solid #BFDBFE',
                background: isSplitActive ? '#1D4ED8' : '#EFF6FF',
                cursor: 'pointer',
                fontSize: '0.65rem',
                color: isSplitActive ? '#FFFFFF' : '#1D4ED8',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
              title="Auto-Fit all visible nodes to screen"
            >
              <span>⛶</span>
              <span>Fit</span>
            </button>
            {/* Document DAG Switcher (When inspecting a single claim) */}
            {activeClaimInspector && (
              <button
                type="button"
                onClick={() => {
                  setActiveClaimInspector(null);
                  const docNodeId = selectedAsset360?.node?.id || openedAssetId;
                  if (docNodeId) {
                    setSelectedNodeId(docNodeId);
                    setInteractiveRootId(docNodeId);
                    setExpandedUpstreamSet(new Set([docNodeId]));
                    setExpandedDownstreamSet(new Set([docNodeId]));
                    setLineageGranularity('document');
                    showToast?.("Switched to full Document Lineage DAG");
                  }
                }}
                className="canvas-btn"
                style={{
                  padding: '0 7px',
                  height: '20px',
                  borderRadius: '4px',
                  border: isSplitActive ? '1px solid #38BDF8' : '1px solid #BAE6FD',
                  background: isSplitActive ? 'rgba(56, 189, 248, 0.18)' : '#F0F9FF',
                  cursor: 'pointer',
                  fontSize: '0.65rem',
                  color: isSplitActive ? '#38BDF8' : '#0284C7',
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px'
                }}
                title="Switch back to full Document Lineage DAG"
              >
                <span>📄 Doc DAG</span>
              </button>
            )}

            {activeClaimInspector && asset360Section === 'summary' && (
              <button
                type="button"
                onClick={() => {
                  setActiveClaimInspector(null);
                  const docNodeId = selectedAsset360?.node?.id || openedAssetId;
                  if (docNodeId) {
                    setSelectedNodeId(docNodeId);
                    setInteractiveRootId(docNodeId);
                    setExpandedUpstreamSet(new Set([docNodeId]));
                    setExpandedDownstreamSet(new Set([docNodeId]));
                    setLineageGranularity('document');
                  }
                }}
                className="canvas-btn"
                style={{
                  padding: '0 6px',
                  height: '20px',
                  borderRadius: '4px',
                  border: '1px solid #EA580C',
                  background: '#C2410C',
                  cursor: 'pointer',
                  fontSize: '0.65rem',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px'
                }}
                title="Close Lineage view and return document reader to full width"
              >
                <X size={10} strokeWidth={2.4} />
                <span>Close</span>
              </button>
            )}
          </div>
        </div>

        {/* Floating Legend / Quick Status at bottom left */}
        <div style={{
          position: 'absolute',
          bottom: '10px',
          left: '10px',
          zIndex: 30,
          background: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(8px)',
          padding: '4px 8px',
          borderRadius: '6px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          border: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '6px 8px',
          fontSize: '0.64rem',
          color: '#475569',
          maxWidth: 'calc(100% - 20px)'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#2026d2' }} /> Data Source
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#0284c7' }} /> Document
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#16a34a' }} /> Atomic Claim
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ea580c' }} /> Contradiction
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#7c3aed' }} /> AI Decision
          </span>
          <span style={{ color: '#94a3b8', marginLeft: '2px' }}>| Drag nodes freely to customize layout</span>
        </div>

        {/* Free-form Pan Canvas Container */}
        <div
          ref={containerRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            height: isSplitActive ? '100%' : ((activeClaimInspector && asset360Section === 'summary') ? '660px' : '640px'),
            flex: isSplitActive ? 1 : 'none',
            width: '100%',
            cursor: isPanning ? 'grabbing' : isWiringEdge ? 'crosshair' : 'grab',
            overflow: 'hidden',
            position: 'relative',
            background: 'radial-gradient(#cbd5e1 1.2px, transparent 1.2px)',
            backgroundSize: '22px 22px',
            backgroundColor: '#fafbfc'
          }}
        >
          {/* Actionable DAG: Live "What-If" Simulation & Draft Changes HUD */}
          {(draftAddedEdges.length > 0 || draftSeveredEdgeIds.size > 0) && (
            <div style={{
              position: 'absolute',
              top: '12px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 35,
              background: 'rgba(15, 23, 42, 0.95)',
              backdropFilter: 'blur(8px)',
              color: '#F8FAFC',
              borderRadius: '10px',
              boxShadow: '0 8px 28px rgba(0,0,0,0.28)',
              border: '1px solid #334155',
              padding: '7px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              fontSize: '0.73rem',
              maxWidth: '92%',
              pointerEvents: 'auto',
              animation: 'fadeIn 0.2s ease'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ background: '#EA580C', color: '#FFFFFF', padding: '2px 7px', borderRadius: '4px', fontWeight: 800, fontSize: '0.66rem', letterSpacing: '0.04em' }}>
                  ⚡ DRAFT LINEAGE
                </span>
                <span style={{ fontWeight: 600 }}>
                  {draftAddedEdges.length > 0 && <span style={{ color: '#4ADE80', marginRight: '6px' }}>+{draftAddedEdges.length} Connected</span>}
                  {draftSeveredEdgeIds.size > 0 && <span style={{ color: '#F87171' }}>-{draftSeveredEdgeIds.size} Severed</span>}
                </span>
              </div>

              <div style={{ borderLeft: '1px solid #334155', paddingLeft: '10px', display: 'flex', alignItems: 'center', gap: '8px', color: '#94A3B8' }}>
                <span>Simulated Trust: <strong style={{ color: '#4ADE80' }}>98% (+14%)</strong></span>
                <span>•</span>
                <span>AI Grounding: <strong style={{ color: '#38BDF8' }}>100% Safe</strong></span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: 'auto' }}>
                <button
                  type="button"
                  onClick={handleDiscardLineageMutations}
                  style={{
                    background: 'rgba(255,255,255,0.08)',
                    border: '1px solid #475569',
                    color: '#E2E8F0',
                    padding: '3px 9px',
                    borderRadius: '5px',
                    fontSize: '0.70rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.16)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                >
                  ↺ Discard
                </button>
                <button
                  type="button"
                  onClick={handleDeployLineageMutations}
                  disabled={isDeployingLineage}
                  style={{
                    background: '#16A34A',
                    border: '1px solid #22C55E',
                    color: '#FFFFFF',
                    padding: '3px 11px',
                    borderRadius: '5px',
                    fontSize: '0.70rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    boxShadow: '0 2px 8px rgba(22,163,74,0.3)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#15803D'}
                  onMouseLeave={e => e.currentTarget.style.background = '#16A34A'}
                >
                  {isDeployingLineage ? 'Deploying...' : 'Deploy Graph ✓'}
                </button>
              </div>
            </div>
          )}

          {/* Zoom & Pan Transform Layer */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0'
            }}
          >
            {/* SVG Connecting Bezier Lines */}
            <svg
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '3600px',
                height: '2400px',
                overflow: 'visible',
                pointerEvents: 'none',
                zIndex: 2
              }}
            >
              <defs>
                <marker id="atlan-arrow-default" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#94A3B8" />
                </marker>
                <marker id="atlan-arrow-active" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#2563EB" />
                </marker>
                <marker id="atlan-arrow-conflict" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#EA580C" />
                </marker>
                <marker id="atlan-arrow-decision" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#7C3AED" />
                </marker>
                <marker id="atlan-arrow-draft-add" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#16A34A" />
                </marker>
                <marker id="atlan-arrow-severed" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 1, 8 4, 0 7" fill="#DC2626" />
                </marker>
              </defs>

              {renderedEdges.map(edge => {
                const isHovered = hoveredEdgeId === edge.id;
                const isConflictLine = edge.type === 'conflict' || edge.isConflictConnection;
                
                let strokeColor = '#94A3B8';
                let marker = 'url(#atlan-arrow-default)';
                let strokeDash = 'none';
                let strokeWidth = 1.8;
                let strokeOpacity = 1;

                if (edge.isSevered) {
                  strokeColor = '#DC2626';
                  marker = 'url(#atlan-arrow-severed)';
                  strokeDash = '5 4';
                  strokeWidth = 2.2;
                  strokeOpacity = 0.55;
                } else if (edge.isDraft) {
                  strokeColor = '#16A34A';
                  marker = 'url(#atlan-arrow-draft-add)';
                  strokeDash = '6 4';
                  strokeWidth = 2.6;
                } else if (isConflictLine) {
                  strokeColor = '#EA580C';
                  marker = 'url(#atlan-arrow-conflict)';
                  strokeWidth = 2.5;
                } else if (edge.isActive) {
                  strokeColor = edge.type === 'decision_grounding' ? '#7C3AED' : '#2563EB';
                  marker = edge.type === 'decision_grounding' ? 'url(#atlan-arrow-decision)' : 'url(#atlan-arrow-active)';
                  strokeWidth = 2.2;
                }

                if (isHovered && !edge.isSevered && !edge.isDraft) {
                  strokeWidth = 3.2;
                  strokeColor = '#2563EB';
                }

                // Remove arrowheads on edges entering claim rows so the curve lands cleanly on the filled circle
                if (edge.target.startsWith('cl_') && !edge.isSevered && !edge.isDraft) {
                  marker = 'none';
                }

                return (
                  <g
                    key={edge.id}
                    onMouseEnter={() => setHoveredEdgeId(edge.id)}
                    onMouseLeave={() => setHoveredEdgeId(prev => prev === edge.id ? null : prev)}
                  >
                    {/* Invisible Wide Hitbox for Effortless Hover Detection */}
                    <path
                      d={edge.pathData}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={18}
                      style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
                    />

                    {/* Visible Lineage Bezier Spline */}
                    <path
                      d={edge.pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeDasharray={strokeDash}
                      strokeOpacity={strokeOpacity}
                      markerEnd={marker}
                      style={{
                        transition: 'stroke 0.2s ease, stroke-width 0.2s ease, stroke-opacity 0.2s ease',
                        pointerEvents: 'none'
                      }}
                    />

                    {/* Interactive Action Pill at Spline Midpoint (Hover to Sever / Restore / Remove) */}
                    {(isHovered || edge.isSevered || edge.isDraft) && (
                      <foreignObject
                        x={edge.midX - 52}
                        y={edge.midY - 14}
                        width={104}
                        height={28}
                        style={{ overflow: 'visible', pointerEvents: 'auto', zIndex: 50 }}
                      >
                        <button
                          type="button"
                          onClick={(e) => handleToggleSeverEdge(e, edge.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            padding: '3px 8px',
                            borderRadius: '12px',
                            fontSize: '0.64rem',
                            fontWeight: 800,
                            cursor: 'pointer',
                            border: edge.isSevered
                              ? '1px solid #F87171'
                              : edge.isDraft
                                ? '1px solid #4ADE80'
                                : '1px solid #38BDF8',
                            background: edge.isSevered
                              ? '#FEF2F2'
                              : edge.isDraft
                                ? '#F0FDF4'
                                : '#0F172A',
                            color: edge.isSevered
                              ? '#DC2626'
                              : edge.isDraft
                                ? '#16A34A'
                                : '#FFFFFF',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.18)',
                            whiteSpace: 'nowrap',
                            transition: 'all 0.15s ease'
                          }}
                          title={
                            edge.isSevered
                              ? "Click to restore this severed connection"
                              : edge.isDraft
                                ? "Click to cancel this drafted connection"
                                : "Click to sever this connection and isolate context flow"
                          }
                        >
                          {edge.isSevered ? (
                            <span>↺ Restore</span>
                          ) : edge.isDraft ? (
                            <span>✓ Linked (✕)</span>
                          ) : (
                            <span>✂️ Sever Flow</span>
                          )}
                        </button>
                      </foreignObject>
                    )}
                  </g>
                );
              })}

              {/* Dynamic Live Wiring Spline while Dragging */}
              {isWiringEdge && (() => {
                const startX = wireStartPos.x;
                const startY = wireStartPos.y;
                let targetX = wireCurrentPos.x;
                let targetY = wireCurrentPos.y;

                if (wireHoveredTargetId) {
                  const tPos = nodePositions[wireHoveredTargetId];
                  if (tPos) {
                    targetX = tPos.x;
                    targetY = tPos.y + CARD_HEIGHT / 2;
                  }
                }

                const isForward = targetX >= startX + 20;
                const dx = Math.max(40, Math.abs(targetX - startX) * 0.45);
                const cp1X = startX + (isForward ? dx : -dx);
                const cp1Y = startY;
                const cp2X = targetX - (isForward ? dx : -dx);
                const cp2Y = targetY;
                const dynamicPath = `M ${startX} ${startY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${targetX} ${targetY}`;

                return (
                  <g style={{ pointerEvents: 'none' }}>
                    <path
                      d={dynamicPath}
                      fill="none"
                      stroke="#16A34A"
                      strokeWidth={3}
                      strokeDasharray="6 4"
                      markerEnd="url(#atlan-arrow-draft-add)"
                    />
                    <circle cx={startX} cy={startY} r={5} fill="#16A34A" />
                    <circle cx={targetX} cy={targetY} r={6} fill="#22C55E" />
                  </g>
                );
              })()}
            </svg>

            {/* Empty State Banner */}
            {renderedNodes.length === 0 && (
              <div style={{
                position: 'absolute',
                top: '200px',
                left: '260px',
                textAlign: 'center',
                background: 'rgba(255,255,255,0.96)',
                backdropFilter: 'blur(8px)',
                padding: '32px 40px',
                borderRadius: '14px',
                border: '1px solid #cbd5e1',
                boxShadow: '0 12px 32px rgba(0,0,0,0.06)',
                maxWidth: '500px',
                pointerEvents: 'auto'
              }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🔎</div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', margin: '0 0 8px 0' }}>
                  No Nodes Match Active Filters
                </h3>
                <p style={{ fontSize: '0.82rem', color: '#64748b', lineHeight: 1.55, margin: '0 0 14px 0' }}>
                  No lineage nodes match your current combination of filters. Try clearing some filters or resetting to default view.
                </p>
                <button
                  onClick={resetAllFilters}
                  className="btn btn-primary"
                  style={{ padding: '6px 16px', fontSize: '0.78rem' }}
                >
                  Reset Filters to Default
                </button>
              </div>
            )}

            {/* Interactive Mode Initial Guidance Pill */}
            {viewMode === 'interactive' && renderedNodes.length === 1 && (
              <div style={{
                position: 'absolute',
                top: '90px',
                left: '480px',
                transform: 'translateX(-50%)',
                background: 'rgba(255, 255, 255, 0.96)',
                border: '1px solid #BFDBFE',
                borderRadius: '20px',
                padding: '6px 18px',
                boxShadow: '0 4px 14px rgba(29, 78, 216, 0.08)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.72rem',
                color: '#1E293B',
                pointerEvents: 'none',
                zIndex: 10,
                whiteSpace: 'nowrap'
              }}>
                <span style={{ fontSize: '13px' }}>🎯</span>
                <span>
                  <strong>Interactive Flow:</strong> Click <strong>+</strong> / <strong>−</strong> on the left for Upstream or <strong>+</strong> / <strong>−</strong> on the right for Downstream.
                </span>
              </div>
            )}

            {/* Draggable Node Cards */}
            {renderedNodes.map(node => {
              const pos = nodePositions[node.id] || { x: 100, y: 100 };
              const isSelected = selectedNodeId === node.id;
              const isConnected = connectedNodeMap.all.has(node.id);
              const isConflictedClaim = allConflictedClaimIds.has(node.id);

              const upstreamParents = getUpstreamParentIds(node.id);
              const downstreamChildren = getDownstreamChildIds(node.id);
              const upstreamCount = upstreamParents.length;
              const downstreamCount = downstreamChildren.length;
              const isUpstreamExpanded = expandedUpstreamSet.has(node.id);
              const isDownstreamExpanded = expandedDownstreamSet.has(node.id);
              const isClaimsExpanded = expandedConflictClaimsSet.has(node.id);
              const cItem = conflictMap[node.id];
              const claimANode = cItem?.claimAId ? graphData?.nodes?.find(n => n.id === cItem.claimAId) : null;
              const claimBNode = cItem?.claimBId ? graphData?.nodes?.find(n => n.id === cItem.claimBId) : null;

              let borderColor = '#3b82f6';
              let badgeBg = '#f0f7ff';
              let badgeColor = '#2563eb';
              let nodeIcon = '⚡';
              let categoryLabel = 'ATOMIC CLAIM';
              let subtitleText = `SCOPE / ${node.data?.scope || 'ENTERPRISE'}`;

              if (node.type === 'source') {
                borderColor = '#2026d2';
                badgeBg = '#eef2ff';
                badgeColor = '#2026d2';
                nodeIcon = '🔌';
                categoryLabel = 'DATA SOURCE';
                subtitleText = `TYPE / ${node.subType?.toUpperCase() || 'CONNECTOR'} • AUTH ${node.authority}%`;
              } else if (node.type === 'document') {
                borderColor = '#0284c7';
                badgeBg = '#f0f9ff';
                badgeColor = '#0284c7';
                nodeIcon = '📄';
                categoryLabel = 'DOCUMENT';
                subtitleText = `TYPE / ${node.subType?.toUpperCase() || 'POLICY'} • v${node.data?.version_count || 1}.0`;
              } else if (node.type === 'conflict') {
                borderColor = '#ea580c';
                badgeBg = '#fff7ed';
                badgeColor = '#ea580c';
                nodeIcon = '⚖️';
                categoryLabel = 'CONTRADICTION';
                subtitleText = `STATUS / ${node.status || 'REVIEW_REQUIRED'}`;
              } else if (node.type === 'decision') {
                borderColor = '#7c3aed';
                badgeBg = '#faf5ff';
                badgeColor = '#7c3aed';
                nodeIcon = '🤖';
                categoryLabel = 'AI DECISION';
                subtitleText = `ACTOR / ${node.actor || 'AGENT_EVAL'}`;
              }

              // Special highlight for contradictory claims
              if (isConflictedClaim && node.type === 'claim') {
                borderColor = '#ea580c';
                badgeColor = '#ea580c';
              }

              // Big Claims Container Card (Multi-Claim List with connecting dots & pagination)
              if (node.type === 'claims_group_card') {
                const docClaims = node.claims || [];
                const visibleClaims = docClaims.slice(0, claimsPageLimit);
                const totalCount = docClaims.length;
                const hasMore = totalCount > claimsPageLimit;

                return (
                  <div
                    key={node.id}
                    className="atlan-node-card"
                    onMouseDown={(e) => handleNodeDragStart(e, node.id)}
                    style={{
                      position: 'absolute',
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: '330px',
                      background: '#FFFFFF',
                      borderRadius: '12px',
                      border: '1.5px solid #3B82F6',
                      boxShadow: '0 4px 20px rgba(59,130,246,0.12)',
                      boxSizing: 'border-box',
                      zIndex: 15,
                      display: 'flex',
                      flexDirection: 'column',
                      overflow: 'visible',
                      cursor: draggedNodeId === node.id ? 'grabbing' : 'default',
                      userSelect: 'none'
                    }}
                  >
                    {/* Draggable Title Header */}
                    <div
                      style={{
                        height: '36px',
                        boxSizing: 'border-box',
                        padding: '0 12px',
                        background: 'linear-gradient(180deg, #1E293B 0%, #0F172A 100%)',
                        borderRadius: '10px 10px 0 0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        color: '#FFFFFF',
                        cursor: 'grab'
                      }}
                      title="Hold and drag to move entire claims table"
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <span style={{ fontSize: '13px' }}>🛡️</span>
                        <span style={{ fontSize: '0.72rem', fontWeight: 800, letterSpacing: '0.02em' }}>
                          ATOMIC CLAIMS ({visibleClaims.length}/{totalCount})
                        </span>
                      </div>
                      <span style={{
                        fontSize: '0.62rem',
                        background: 'rgba(59,130,246,0.25)',
                        color: '#93C5FD',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        fontWeight: 700
                      }}>
                        {node.docTitle || 'Context Rules'}
                      </span>
                    </div>

                    {/* Claims List Rows */}
                    <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {visibleClaims.map((cl) => {
                        const isSelected = selectedNodeId === cl.id;
                        const isConflicted = allConflictedClaimIds.has(cl.id);
                        const isHoveredTarget = wireHoveredTargetId === cl.id;

                        return (
                          <div
                            key={cl.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedNodeId(cl.id);
                              fetchBlastRadius(cl.cleanId || String(cl.id).replace(/^cl_/, ''));
                            }}
                            style={{
                              position: 'relative',
                              height: '56px',
                              boxSizing: 'border-box',
                              padding: '5px 10px',
                              background: isSelected ? '#EFF6FF' : isConflicted ? '#FFF7ED' : '#F8FAFC',
                              border: isSelected ? '1.5px solid #2563EB' : isConflicted ? '1px solid #FDBA74' : '1px solid #E2E8F0',
                              borderRadius: '8px',
                              cursor: 'pointer',
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'center',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            {/* Left Input Dot (Port) - Solid Fully Filled Circle (No Radio Button Style) */}
                            <div
                              style={{
                                position: 'absolute',
                                left: '-13px',
                                top: '23px',
                                width: '10px',
                                height: '10px',
                                borderRadius: '50%',
                                background: isHoveredTarget
                                  ? '#16A34A'
                                  : isConflicted
                                    ? '#EA580C'
                                    : '#2563EB',
                                border: 'none',
                                boxShadow: 'none',
                                zIndex: 25
                              }}
                              title="Active context connection from source document"
                            />

                            {/* Claim Row Content */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', marginBottom: '2px' }}>
                              <span style={{
                                fontSize: '0.60rem',
                                fontWeight: 800,
                                color: isConflicted ? '#EA580C' : '#2563EB',
                                background: isConflicted ? '#FFEDD5' : '#DBEAFE',
                                padding: '1px 5px',
                                borderRadius: '3px'
                              }}>
                                {isConflicted ? 'CONFLICTED' : 'VERIFIED'}
                              </span>
                              <span style={{ fontSize: '0.62rem', fontWeight: 700, color: '#16A34A' }}>
                                {Math.round((cl.trustScore || 0.96) * 100)}% Trust
                              </span>
                            </div>

                            <p style={{
                              margin: 0,
                              fontSize: '0.69rem',
                              fontWeight: 600,
                              color: '#1E293B',
                              lineHeight: 1.35,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {cl.label}
                            </p>

                            {/* Right Output Dot (Port - ⚡ Draggable Handle) */}
                            <div
                              onMouseDown={(e) => handlePortMouseDown(e, cl.id)}
                              style={{
                                position: 'absolute',
                                right: '-9px',
                                top: 'calc(50% - 9px)',
                                width: '18px',
                                height: '18px',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%)',
                                border: '1.5px solid #FFFFFF',
                                color: '#FFFFFF',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '9px',
                                boxShadow: '0 2px 6px rgba(29,78,216,0.35)',
                                cursor: 'crosshair',
                                zIndex: 25
                              }}
                              title="Hold and drag to wire to Decision Agent or Contradiction"
                            >
                              ⚡
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Footer Load More / Collapse */}
                    {totalCount > 6 && (
                      <div style={{ padding: '4px 8px 8px 8px', borderTop: '1px solid #F1F5F9' }}>
                        {hasMore ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setClaimsPageLimit(prev => prev + 6);
                              showToast?.(`Loaded 6 more claims (${Math.min(totalCount, claimsPageLimit + 6)}/${totalCount})`);
                            }}
                            style={{
                              width: '100%',
                              padding: '5px',
                              borderRadius: '6px',
                              border: '1px solid #BFDBFE',
                              background: '#EFF6FF',
                              color: '#1D4ED8',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '4px',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <span>➕ Load 6 More Claims ({totalCount - visibleClaims.length} remaining)</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setClaimsPageLimit(6);
                              showToast?.("Collapsed claims list to 6");
                            }}
                            style={{
                              width: '100%',
                              padding: '4px',
                              borderRadius: '6px',
                              border: '1px solid #E2E8F0',
                              background: '#F8FAFC',
                              color: '#64748B',
                              fontSize: '0.66rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '4px'
                            }}
                          >
                            <span>↺ Collapse to 6 Claims</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              }

              // Anomaly Roll-up Cluster Card
              if (node.type === 'claim_cluster') {
                return (
                  <div
                    key={node.id}
                    className="atlan-node-card"
                    onClick={() => {
                      setDrawerDocFilter(node.docId || 'all');
                      setIsDrawerOpen(true);
                      showToast?.(`Viewing ${node.count} clean claims from ${node.docTitle}`);
                    }}
                    style={{
                      position: 'absolute',
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: `${CARD_WIDTH}px`,
                      height: `${CARD_HEIGHT}px`,
                      background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)',
                      borderRadius: '10px',
                      border: '1.5px dashed #059669',
                      boxShadow: '0 2px 8px rgba(5,150,105,0.12)',
                      boxSizing: 'border-box',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      zIndex: 10,
                      userSelect: 'none',
                      transition: 'all 0.15s ease'
                    }}
                    title="Click to view all clean, verified claims in Claims Drawer"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#166534', background: '#BBF7D0', padding: '1px 6px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <ShieldCheck size={11} /> CLUSTER (CLEAN)
                      </span>
                      <span style={{ fontSize: '0.66rem', color: '#15803D', fontWeight: 700 }}>
                        {node.count} Claims
                      </span>
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.78rem', fontWeight: 700, color: '#14532D', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        🛡️ {node.label}
                      </h4>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.68rem', color: '#166534', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        Source: {node.docTitle}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(5,150,105,0.2)', paddingTop: '4px', fontSize: '0.65rem', color: '#15803D' }}>
                      <span>Non-Conflicting</span>
                      <span style={{ fontWeight: 700, textDecoration: 'underline' }}>Browse Claims ›</span>
                    </div>
                  </div>
                );
              }

              // High-Density Column Overflow Cluster Card
              if (node.type === 'density_cluster') {
                return (
                  <div
                    key={node.id}
                    className="atlan-node-card"
                    onClick={() => {
                      setDisplayLimit('all');
                      showToast?.("Expanded all claims in column");
                    }}
                    style={{
                      position: 'absolute',
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: `${CARD_WIDTH}px`,
                      height: `${CARD_HEIGHT}px`,
                      background: 'linear-gradient(135deg, #F8FAFC 0%, #EEF2F6 100%)',
                      borderRadius: '10px',
                      border: '1.5px dashed #64748B',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.02)',
                      boxSizing: 'border-box',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      zIndex: 10,
                      userSelect: 'none',
                      transition: 'all 0.15s ease'
                    }}
                    title="Click to expand full column density"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#334155', background: '#E2E8F0', padding: '1px 6px', borderRadius: '4px' }}>
                        COLUMN OVERFLOW
                      </span>
                      <span style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 700 }}>
                        +{node.count} Hidden
                      </span>
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.78rem', fontWeight: 700, color: '#0F172A' }}>
                        {node.label}
                      </h4>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.68rem', color: '#64748B' }}>
                        {node.desc}
                      </p>
                    </div>
                    <div style={{ borderTop: '1px solid #CBD5E1', paddingTop: '4px', fontSize: '0.66rem', color: '#2563EB', fontWeight: 700, textAlign: 'center' }}>
                      ⚡ Click to Expand All
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={node.id}
                  className="atlan-node-card"
                  onClick={() => setSelectedNodeId(node.id)}
                  onMouseDown={(e) => handleNodeDragStart(e, node.id)}
                  style={{
                    position: 'absolute',
                    left: `${pos.x}px`,
                    top: `${pos.y}px`,
                    width: (node.type === 'conflict' && isClaimsExpanded) ? '310px' : `${CARD_WIDTH}px`,
                    height: (node.type === 'conflict' && isClaimsExpanded) ? 'auto' : `${CARD_HEIGHT}px`,
                    minHeight: `${CARD_HEIGHT}px`,
                    background: '#fff',
                    borderRadius: '10px',
                    border: isSelected
                      ? `2px solid ${borderColor}`
                      : isConflictedClaim
                        ? '1.5px solid #ea580c'
                        : isConnected
                          ? `1.5px solid ${borderColor}`
                          : '1px solid #cbd5e1',
                    boxShadow: isSelected
                      ? `0 0 0 4px ${borderColor}30, 0 8px 24px rgba(0,0,0,0.12)`
                      : (node.type === 'conflict' && isClaimsExpanded)
                        ? '0 0 0 3px rgba(234,88,12,0.3), 0 12px 32px rgba(234,88,12,0.18)'
                        : isConflictedClaim
                          ? '0 0 0 2px rgba(234,88,12,0.25), 0 4px 14px rgba(234,88,12,0.15)'
                          : isConnected
                            ? `0 0 0 2px ${borderColor}20, 0 4px 12px rgba(0,0,0,0.06)`
                            : '0 2px 8px rgba(0,0,0,0.04)',
                    boxSizing: 'border-box',
                    padding: '10px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    cursor: draggedNodeId === node.id ? 'grabbing' : 'pointer',
                    userSelect: 'none',
                    zIndex: (node.type === 'conflict' && isClaimsExpanded) ? 40 : (isSelected ? 20 : isConflictedClaim ? 15 : isConnected ? 10 : 5),
                    transition: draggedNodeId === node.id ? 'none' : 'box-shadow 0.15s ease, border-color 0.15s ease'
                  }}
                >
                  {/* Atlan-Style Home / Origin Beacon */}
                  {isSelected && (
                    <div style={{
                      position: 'absolute',
                      top: '-16px',
                      left: '10px',
                      background: '#1D4ED8',
                      color: '#fff',
                      borderRadius: '4px 4px 0 0',
                      padding: '2px 8px',
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      letterSpacing: '0.04em',
                      boxShadow: '0 2px 6px rgba(29,78,216,0.35)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <Home size={10} />
                      <span>YOU ARE HERE</span>
                    </div>
                  )}

                  {/* Left Connection Port: Upstream Expand (+) / Collapse (−) & Snap Highlight */}
                  {node.type !== 'source' && upstreamCount > 0 && (
                    <div
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleUpstream(node.id);
                      }}
                      style={{
                        position: 'absolute',
                        left: '-13px',
                        top: (node.type === 'conflict' && isClaimsExpanded) ? '26px' : 'calc(50% - 11px)',
                        width: '22px',
                        height: '22px',
                        borderRadius: '50%',
                        background: isUpstreamExpanded ? '#1D4ED8' : '#fff',
                        border: `1.5px solid ${isUpstreamExpanded ? '#1D4ED8' : borderColor}`,
                        color: isUpstreamExpanded ? '#fff' : borderColor,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.14)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.85rem',
                        fontWeight: 900,
                        lineHeight: 1,
                        cursor: 'pointer',
                        zIndex: 25,
                        transition: 'all 0.15s ease'
                      }}
                      title={
                        isUpstreamExpanded
                          ? 'Click (−) to collapse upstream nodes'
                          : 'Click (+) to expand upstream nodes'
                      }
                    >
                      {isUpstreamExpanded ? '−' : '+'}
                    </div>
                  )}

                  {/* Input Port Snap Indicator when Wiring */}
                  {isWiringEdge && wireHoveredTargetId === node.id && (
                    <div style={{
                      position: 'absolute',
                      left: '-26px',
                      top: 'calc(50% - 10px)',
                      background: '#16A34A',
                      color: '#FFFFFF',
                      borderRadius: '12px',
                      padding: '2px 7px',
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      boxShadow: '0 2px 8px rgba(22,163,74,0.4)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '3px',
                      zIndex: 35,
                      pointerEvents: 'none',
                      whiteSpace: 'nowrap'
                    }}>
                      <span>✓ Snap Link</span>
                    </div>
                  )}

                  {/* Actionable Output Wiring Port Handle (Drag to Wire Context Flow) */}
                  {node.type !== 'decision' && (
                    <div
                      className="atlan-port-handle"
                      onMouseDown={(e) => handlePortMouseDown(e, node.id)}
                      title="Click and drag to wire context flow into downstream AI or node"
                      style={{
                        position: 'absolute',
                        right: '-10px',
                        top: (node.type === 'conflict' && isClaimsExpanded) ? '54px' : (downstreamCount > 0 ? 'calc(50% + 14px)' : 'calc(50% - 9px)'),
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        background: '#2563EB',
                        border: '2px solid #FFFFFF',
                        boxShadow: '0 2px 6px rgba(37,99,235,0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'crosshair',
                        zIndex: 26,
                        transition: 'transform 0.15s ease, background-color 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.transform = 'scale(1.25)';
                        e.currentTarget.style.backgroundColor = '#1D4ED8';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.transform = 'scale(1.0)';
                        e.currentTarget.style.backgroundColor = '#2563EB';
                      }}
                    >
                      <span style={{ fontSize: '9px', color: '#FFFFFF', lineHeight: 1, pointerEvents: 'none' }}>⚡</span>
                    </div>
                  )}

                  {/* Right Connection Port: Downstream Expand (+) / Collapse (−) Only */}
                  {node.type !== 'decision' && downstreamCount > 0 && (
                    <div
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleDownstream(node.id);
                      }}
                      style={{
                        position: 'absolute',
                        right: '-13px',
                        top: (node.type === 'conflict' && isClaimsExpanded) ? '26px' : 'calc(50% - 11px)',
                        width: '22px',
                        height: '22px',
                        borderRadius: '50%',
                        background: isDownstreamExpanded ? '#1D4ED8' : '#fff',
                        border: `1.5px solid ${isDownstreamExpanded ? '#1D4ED8' : borderColor}`,
                        color: isDownstreamExpanded ? '#fff' : borderColor,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.14)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.85rem',
                        fontWeight: 900,
                        lineHeight: 1,
                        cursor: 'pointer',
                        zIndex: 25,
                        transition: 'all 0.15s ease'
                      }}
                      title={
                        isDownstreamExpanded
                          ? 'Click (−) to collapse downstream nodes'
                          : 'Click (+) to expand downstream nodes'
                      }
                    >
                      {isDownstreamExpanded ? '−' : '+'}
                    </div>
                  )}

                  {/* Card Header: Category & Metrics */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      color: badgeColor,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em'
                    }}>
                      {isConflictedClaim && node.type === 'claim' ? '⚠️ CONTRADICTION' : categoryLabel}
                    </span>

                    {node.trustScore !== undefined && (
                      <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {(node.trustScore * 100).toFixed(0)}% Trust
                      </span>
                    )}
                    {node.severity && (
                      <span className="badge badge-review" style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {node.severity}
                      </span>
                    )}
                    {node.verdict && (
                      <span className={node.verdict === 'ALLOW' ? 'badge badge-verified' : 'badge badge-warning'} style={{ fontSize: '0.62rem', padding: '1px 5px', fontWeight: 700 }}>
                        {node.verdict}
                      </span>
                    )}
                  </div>

                  {/* Card Body: Entity Title */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                    <span style={{ fontSize: '15px' }}>{nodeIcon}</span>
                    <span style={{
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      color: '#1e293b',
                      lineHeight: 1.25,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {node.label}
                    </span>
                  </div>

                  {/* Card Footer: Metadata / Scope */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #f1f5f9', paddingTop: '4px', fontSize: '0.65rem', color: '#64748b' }}>
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '170px' }}>
                      {subtitleText}
                    </span>
                    {node.type === 'document' ? (
                      <span
                        style={{
                          color: '#0284c7',
                          fontWeight: 700,
                          fontSize: '0.62rem'
                        }}
                      >
                        inspect doc &rsaquo;
                      </span>
                    ) : node.type === 'conflict' ? (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleConflictClaims(node.id);
                          if (!isClaimsExpanded) {
                            showToast?.(`Revealed clashing assertions for ${node.label}`);
                          }
                        }}
                        style={{
                          color: isClaimsExpanded ? '#C2410C' : '#EA580C',
                          fontWeight: 800,
                          fontSize: '0.64rem',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px',
                          background: isClaimsExpanded ? '#FFEDD5' : '#FFF7ED',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          border: '1px solid #FED7AA',
                          transition: 'all 0.15s ease'
                        }}
                        title="Inspect the 2 conflicting assertions"
                      >
                        <span>⚖️ {isClaimsExpanded ? 'Hide Claims ▲' : 'Claims (2) ▾'}</span>
                      </span>
                    ) : (
                      <span style={{ color: '#2563eb', fontWeight: 600, fontSize: '0.62rem' }}>
                        view lineage &rsaquo;
                      </span>
                    )}
                  </div>

                  {/* Inline Clashing Claims Drawer for Contradiction Card */}
                  {node.type === 'conflict' && isClaimsExpanded && (
                    <div
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        marginTop: '8px',
                        padding: '8px 10px',
                        background: '#FFF7ED',
                        borderRadius: '8px',
                        border: '1px solid #FED7AA',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        fontSize: '0.66rem',
                        boxShadow: 'inset 0 1px 3px rgba(234,88,12,0.06)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 800, color: '#9A3412', textTransform: 'uppercase', fontSize: '0.59rem', letterSpacing: '0.03em' }}>
                          ⚖️ CLASHING ASSERTIONS
                        </span>
                        <span style={{ fontSize: '0.58rem', color: '#EA580C', fontWeight: 800, background: '#FFEDD5', padding: '1px 5px', borderRadius: '3px' }}>
                          {node.severity || cItem?.severity || 'HIGH'} SEVERITY
                        </span>
                      </div>

                      {/* Assertion A */}
                      <div style={{
                        background: '#FFFFFF',
                        padding: '6px 8px',
                        borderRadius: '5px',
                        borderLeft: '3px solid #0284C7',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#0369A1', fontWeight: 700, fontSize: '0.58rem', marginBottom: '2px' }}>
                          <span>ASSERTION A (BASELINE)</span>
                          <span>{claimANode?.trustScore ? `${(claimANode.trustScore * 100).toFixed(0)}% TRUST` : 'VERIFIED'}</span>
                        </div>
                        <p style={{ margin: 0, color: '#1E293B', fontSize: '0.65rem', lineHeight: 1.35, fontWeight: 500 }}>
                          "{claimANode?.fullText || claimANode?.label || cItem?.claimAId || 'SOP refund eligibility window is strictly 30 days.'}"
                        </p>
                        {claimANode?.docTitle && (
                          <span style={{ fontSize: '0.56rem', color: '#64748B', display: 'block', marginTop: '2px' }}>
                            Doc: {claimANode.docTitle}
                          </span>
                        )}
                      </div>

                      {/* Assertion B */}
                      <div style={{
                        background: '#FFFFFF',
                        padding: '6px 8px',
                        borderRadius: '5px',
                        borderLeft: '3px solid #EA580C',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#C2410C', fontWeight: 700, fontSize: '0.58rem', marginBottom: '2px' }}>
                          <span>ASSERTION B (CONTRADICTION)</span>
                          <span>{claimBNode?.trustScore ? `${(claimBNode.trustScore * 100).toFixed(0)}% TRUST` : 'FLAGGED'}</span>
                        </div>
                        <p style={{ margin: 0, color: '#1E293B', fontSize: '0.65rem', lineHeight: 1.35, fontWeight: 500 }}>
                          "{claimBNode?.fullText || claimBNode?.label || cItem?.claimBId || 'VIP Tier-1 customer exceptions allow 45-day refund grants.'}"
                        </p>
                        {claimBNode?.docTitle && (
                          <span style={{ fontSize: '0.56rem', color: '#64748B', display: 'block', marginTop: '2px' }}>
                            Doc: {claimBNode.docTitle}
                          </span>
                        )}
                      </div>

                      {/* Resolution Action */}
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedNodeId(node.id);
                          showToast?.(`Selected contradiction: ${node.label} for curator review`);
                        }}
                        style={{
                          marginTop: '2px',
                          padding: '4px 8px',
                          background: '#EA580C',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: '4px',
                          fontWeight: 700,
                          fontSize: '0.62rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px',
                          boxShadow: '0 1px 3px rgba(234,88,12,0.3)',
                          transition: 'background 0.15s ease'
                        }}
                      >
                        <span>⚖️ Inspect Full Evidence & Resolve</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. Selected Entity Inspector & Conflict Resolution Console (Hidden in Split-Screen view to keep DAG clean and spacious) */}
      {!isSplitActive && selectedNode && (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 1.2fr) minmax(320px, 1fr)',
          gap: '18px',
          alignItems: 'start'
        }}>
          {/* Left Column: Node Details & Lineage Stats */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '22px' }}>
                {selectedNode.type === 'source' ? '🔌' : selectedNode.type === 'document' ? '📄' : selectedNode.type === 'claim' ? '⚡' : selectedNode.type === 'conflict' ? '⚖️' : '🤖'}
              </span>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                  {selectedNode.label}
                </h3>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Node Type: <strong style={{ textTransform: 'uppercase' }}>{selectedNode.type}</strong> &bull; ID: <code style={{ fontSize: '0.7rem' }}>{selectedNode.id}</code>
                </span>
              </div>
            </div>

            {selectedNode.fullText && (
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: 1.45, background: 'var(--bg-card)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                "{selectedNode.fullText}"
              </p>
            )}

            {/* Upstream & Downstream Lineage Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '4px' }}>
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Upstream Roots</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0284c7', marginTop: '2px' }}>{connectedNodeMap.up.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Downstream Targets</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#7c3aed', marginTop: '2px' }}>{connectedNodeMap.down.size}</div>
              </div>
              <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Trust Score</span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#16a34a', marginTop: '2px' }}>
                  {selectedNode.trustScore !== undefined ? `${(selectedNode.trustScore * 100).toFixed(0)}%` : '98%'}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Contextual Inspector */}
          <div>
            {selectedNode.type === 'conflict' ? (
              /* Dedicated Side-by-Side Conflict Discrepancy Viewer */
              (() => {
                const cItem = conflictMap[selectedNode.id];
                const claimA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
                const claimB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);

                return (
                  <div style={{
                    background: 'rgba(234,88,12,0.05)',
                    border: '1px solid rgba(234,88,12,0.3)',
                    borderRadius: '10px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#ea580c' }}>
                        ⚖️ Contradiction Comparison
                      </span>
                      <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                        {selectedNode.severity || 'HIGH'} SEVERITY
                      </span>
                    </div>

                    {/* Claim A vs Claim B Comparison Box */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div style={{ background: '#fff', padding: '10px', borderRadius: '8px', border: '1px solid #fed7aa', fontSize: '0.74rem' }}>
                        <div style={{ fontWeight: 800, color: '#ea580c', marginBottom: '4px' }}>Claim A (Candidate)</div>
                        <p style={{ margin: 0, color: '#334155', lineHeight: 1.35 }}>
                          "{claimA?.fullText || claimA?.label || 'Loading claim...'}"
                        </p>
                      </div>
                      <div style={{ background: '#fff', padding: '10px', borderRadius: '8px', border: '1px solid #fed7aa', fontSize: '0.74rem' }}>
                        <div style={{ fontWeight: 800, color: '#2563eb', marginBottom: '4px' }}>Claim B (Contender)</div>
                        <p style={{ margin: 0, color: '#334155', lineHeight: 1.35 }}>
                          "{claimB?.fullText || claimB?.label || 'Loading claim...'}"
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        Status: <strong>{selectedNode.status || 'Pending Review'}</strong>
                      </span>
                      <button
                        onClick={() => {
                          setSelectedConflictId(selectedNode.id);
                          setViewMode('conflicts');
                          showToast?.("Isolated conflict lineage on canvas");
                        }}
                        style={{
                          padding: '4px 12px',
                          borderRadius: '6px',
                          background: '#ea580c',
                          color: '#fff',
                          border: 'none',
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        ⚡ Isolate Conflict DAG
                      </button>
                    </div>
                  </div>
                );
              })()
            ) : selectedNode.type === 'claim' ? (
              /* Blast Radius Simulation */
              <div style={{
                background: blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.06)' : 'rgba(25,195,125,0.06)',
                border: `1px solid ${blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'rgba(234,88,12,0.3)' : 'rgba(25,195,125,0.3)'}`,
                borderRadius: '10px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Downstream Policy Blast Radius
                  </span>
                  <span className={blastRadius?.risk_tier === 'CRITICAL' || blastRadius?.risk_tier === 'HIGH' ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.7rem' }}>
                    {blastRadius?.risk_tier || 'LOW'} RISK ({blastRadius?.risk_score || 15}/100)
                  </span>
                </div>

                <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  {blastRadius?.recommendation || 'Calculates what breaks across AI models if this knowledge is modified.'}
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
                  <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.74rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Connected Conflicts: </span>
                    <strong style={{ color: '#ea580c' }}>{blastRadius?.connected_conflicts_count || 0}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-card)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.74rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Affected AI Decisions: </span>
                    <strong style={{ color: '#7c3aed' }}>{blastRadius?.impacted_decisions_count || 0}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-color)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <strong style={{ color: 'var(--text-main)' }}>Lineage Context:</strong> Select an individual <strong>Atomic Claim (⚡)</strong> or <strong>Contradiction (⚖️)</strong> to inspect connected rules and downstream AI decisions.
              </div>
            )}
          </div>
        </div>
      )}

            {/* 3. SELECTED ASSET'S CONTRADICTIONS & CONFLICTS (Active & Resolved for THIS Document / Connector) */}
            {selectedAsset360 && (asset360Section === 'all' || asset360Section === 'conflicts') && (
              <div style={{
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                padding: '14px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid #F1F5F9', paddingBottom: '8px' }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 800, color: '#0F172A' }}>
                      ⚖️ Contradictions & Conflicts for "{selectedAsset360.node.label}" ({selectedAsset360.conflicts.length})
                    </h4>
                    <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                      {selectedAsset360.activeConflicts.length} Active / Unresolved &bull; {selectedAsset360.conflicts.length - selectedAsset360.activeConflicts.length} Resolved
                    </span>
                  </div>
                </div>

                {selectedAsset360.conflicts.length === 0 ? (
                  <div style={{ padding: '14px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px', fontSize: '0.78rem', color: '#15803D', fontWeight: 600 }}>
                    ✅ Zero contradictions detected for this {selectedAsset360.mode}. All extracted policy claims are consistent.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '10px' }}>
                    {selectedAsset360.conflicts.map((c, idx) => {
                      const cItem = conflictMap[c.id];
                      const clA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
                      const clB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);
                      const st = (c.status || '').toLowerCase();
                      const isResolved = st === 'resolved' || st === 'dismissed';

                      return (
                        <div
                          key={c.id}
                          style={{
                            border: isResolved ? '1px solid #BBF7D0' : '1.5px solid #FED7AA',
                            background: isResolved ? '#F0FDF4' : '#FFF7ED',
                            borderRadius: '9px',
                            padding: '12px 14px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                            <span style={{
                              fontSize: '0.62rem',
                              fontWeight: 800,
                              padding: '2px 7px',
                              borderRadius: '999px',
                              background: isResolved ? '#DCFCE7' : '#FFEDD5',
                              color: isResolved ? '#15803D' : '#C2410C'
                            }}>
                              {isResolved ? '✅ RESOLVED' : '⚠️ ACTIVE / UNRESOLVED'} &bull; {c.severity || 'HIGH'}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                if (isResolved) setFilterStatus('all');
                                setExpandedDownstreamSet(prev => new Set(prev).add(selectedAsset360.node.id));
                                setSelectedNodeId(c.id);
                                showToast?.(`Selected "${c.label}" in the DAG above`);
                              }}
                              style={{
                                padding: '3px 8px',
                                borderRadius: '5px',
                                border: '1px solid #EA580C',
                                background: '#FFFFFF',
                                color: '#C2410C',
                                fontSize: '0.66rem',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              Focus in DAG ↑
                            </button>
                          </div>

                          <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#0F172A' }}>
                            #{idx + 1} {c.label}
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                            <div style={{ background: '#FFFFFF', padding: '7px 9px', borderRadius: '6px', borderLeft: '3px solid #0284C7', fontSize: '0.7rem', color: '#1E293B' }}>
                              <strong style={{ color: '#0284C7', display: 'block', fontSize: '0.6rem' }}>ASSERTION A</strong>
                              "{clA?.fullText || clA?.label}"
                            </div>
                            <div style={{ background: '#FFFFFF', padding: '7px 9px', borderRadius: '6px', borderLeft: '3px solid #EA580C', fontSize: '0.7rem', color: '#1E293B' }}>
                              <strong style={{ color: '#EA580C', display: 'block', fontSize: '0.6rem' }}>ASSERTION B</strong>
                              "{clB?.fullText || clB?.label}"
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}


                </div>
              );

              return (
                <div
                  ref={splitContainerRef}
                  style={{
                    display: 'flex',
                    flexDirection: isSplitActive ? 'row' : 'column',
                    alignItems: 'stretch',
                    width: '100%',
                    height: isSplitActive ? 'calc(100vh - 108px)' : 'auto',
                    maxHeight: isSplitActive ? 'calc(100vh - 108px)' : 'none',
                    minHeight: isSplitActive ? '380px' : 'auto',
                    position: 'relative',
                    background: 'transparent',
                    userSelect: isResizingSplit ? 'none' : 'auto',
                    gap: isSplitActive ? '0px' : '8px',
                    marginTop: '0px',
                    marginBottom: isSplitActive ? '8px' : '0px',
                    overflow: 'hidden'
                  }}
                >
                  {activePanes.map((paneId, idx) => {
                    const isFirst = idx === 0;
                    const isSecond = idx === 1;

                    let paneStyle = {};
                    if (isThreePane) {
                      if (isFirst) {
                        paneStyle = {
                          width: `calc(${splitRatio3Doc}% - 6px)`,
                          minWidth: '240px',
                          maxWidth: 'calc(100% - 480px)',
                          flexShrink: 0
                        };
                      } else if (isSecond) {
                        paneStyle = {
                          width: `calc(${splitRatio3Details}% - 6px)`,
                          minWidth: '240px',
                          maxWidth: 'calc(100% - 480px)',
                          flexShrink: 0
                        };
                      } else {
                        paneStyle = {
                          width: `calc(${100 - splitRatio3Doc - splitRatio3Details}% - 6px)`,
                          minWidth: '260px',
                          flex: 1
                        };
                      }
                    } else if (isTwoPane) {
                      if (isFirst) {
                        paneStyle = {
                          width: `calc(${splitRatio}% - 5px)`,
                          minWidth: '260px',
                          maxWidth: 'calc(100% - 260px)',
                          flexShrink: 0
                        };
                      } else {
                        paneStyle = {
                          width: `calc(${100 - splitRatio}% - 5px)`,
                          minWidth: '260px',
                          flex: 1
                        };
                      }
                    } else {
                      paneStyle = {
                        width: '100%',
                        flex: 1
                      };
                    }

                    return (
                      <React.Fragment key={paneId}>
                        <div
                          onDragOver={(e) => {
                            e.preventDefault();
                            if (draggedPane && draggedPane !== paneId) {
                              setDragOverPane(paneId);
                            }
                          }}
                          onDragLeave={(e) => {
                            if (e.currentTarget.contains(e.relatedTarget)) return;
                            if (dragOverPane === paneId) setDragOverPane(null);
                          }}
                          onDrop={(e) => {
                            e.preventDefault();
                            const sourcePane = e.dataTransfer.getData('text/plain') || draggedPane;
                            handleDropPane(sourcePane, paneId);
                          }}
                          style={{
                            ...paneStyle,
                            display: 'flex',
                            flexDirection: 'column',
                            position: 'relative',
                            borderRadius: '10px',
                            outline: dragOverPane === paneId ? '2px dashed #EA580C' : 'none',
                            outlineOffset: '-2px',
                            opacity: draggedPane === paneId ? 0.6 : 1,
                            transition: 'outline 0.15s ease, opacity 0.15s ease'
                          }}
                        >
                          {paneId === 'doc' && renderDocPane()}
                          {paneId === 'details' && renderDetailsPane()}
                          {paneId === 'dag' && renderDagFacility()}
                        </div>

                        {isThreePane && isFirst && (
                          <div
                            className="trulin-vscode-splitter"
                            onMouseDown={(e) => handleSplitMouseDown(e, 'threePane1')}
                            title="Drag to resize columns (Double-click to reset)"
                            onDoubleClick={() => { setSplitRatio3Doc(35); setSplitRatio3Details(33); }}
                            onMouseEnter={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line) line.style.background = '#EA580C';
                            }}
                            onMouseLeave={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line && resizingDivider !== 'threePane1') line.style.background = '#E2E8F0';
                            }}
                            style={{
                              width: '10px',
                              margin: '0 -1px',
                              cursor: 'col-resize',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              zIndex: 30,
                              flexShrink: 0,
                              userSelect: 'none',
                              position: 'relative'
                            }}
                          >
                            <div
                              style={{
                                width: '2px',
                                height: '100%',
                                background: resizingDivider === 'threePane1' ? '#EA580C' : '#E2E8F0',
                                borderRadius: '1px',
                                transition: resizingDivider === 'threePane1' ? 'none' : 'background 0.15s ease'
                              }}
                            />
                          </div>
                        )}

                        {isThreePane && isSecond && (
                          <div
                            className="trulin-vscode-splitter"
                            onMouseDown={(e) => handleSplitMouseDown(e, 'threePane2')}
                            title="Drag to resize columns (Double-click to reset)"
                            onDoubleClick={() => { setSplitRatio3Doc(35); setSplitRatio3Details(33); }}
                            onMouseEnter={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line) line.style.background = '#EA580C';
                            }}
                            onMouseLeave={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line && resizingDivider !== 'threePane2') line.style.background = '#E2E8F0';
                            }}
                            style={{
                              width: '10px',
                              margin: '0 -1px',
                              cursor: 'col-resize',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              zIndex: 30,
                              flexShrink: 0,
                              userSelect: 'none',
                              position: 'relative'
                            }}
                          >
                            <div
                              style={{
                                width: '2px',
                                height: '100%',
                                background: resizingDivider === 'threePane2' ? '#EA580C' : '#E2E8F0',
                                borderRadius: '1px',
                                transition: resizingDivider === 'threePane2' ? 'none' : 'background 0.15s ease'
                              }}
                            />
                          </div>
                        )}

                        {isTwoPane && isFirst && (
                          <div
                            className="trulin-vscode-splitter"
                            onMouseDown={(e) => handleSplitMouseDown(e, 'twoPane')}
                            title="Drag to resize split view (Double-click to reset 50/50)"
                            onDoubleClick={() => setSplitRatio(50)}
                            onMouseEnter={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line) line.style.background = '#EA580C';
                            }}
                            onMouseLeave={e => {
                              const line = e.currentTarget.firstElementChild;
                              if (line && resizingDivider !== 'twoPane') line.style.background = '#E2E8F0';
                            }}
                            style={{
                              width: '10px',
                              margin: '0 -1px',
                              cursor: 'col-resize',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              zIndex: 30,
                              flexShrink: 0,
                              userSelect: 'none',
                              position: 'relative'
                            }}
                          >
                            <div
                              style={{
                                width: '2px',
                                height: '100%',
                                background: resizingDivider === 'twoPane' ? '#EA580C' : '#E2E8F0',
                                borderRadius: '1px',
                                transition: resizingDivider === 'twoPane' ? 'none' : 'background 0.15s ease'
                              }}
                            />
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        );
      })()}

      {/* ========================================================= */}
      {/* SUB-TAB 2: CONFLICTS REGISTRY (ACTIVE & RESOLVED)         */}
      {/* ========================================================= */}
      {vaultSubTab === 'conflicts' && (
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          padding: '18px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          {/* Top Header & Status Filter Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', borderBottom: '1px solid #F1F5F9', paddingBottom: '12px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#0F172A' }}>
                ⚖️ Enterprise Contradictions Registry (Active & Resolved)
              </h3>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.76rem', color: '#64748B' }}>
                Browse all policy contradictions without cluttering the visual DAG canvas. Click <strong>Visualize in DAG</strong> on any conflict to trace its exact lineage.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {[
                { id: 'all', label: `All Conflicts (${allConflictsRaw.length})`, color: '#334155' },
                { id: 'active', label: `⚠️ Active / Unresolved (${activeConflictsCount})`, color: '#EA580C' },
                { id: 'resolved', label: `✅ Resolved (${resolvedConflictsCount})`, color: '#16A34A' }
              ].map(btn => {
                const isSel = vaultConflictFilter === btn.id;
                return (
                  <button
                    key={btn.id}
                    type="button"
                    onClick={() => setVaultConflictFilter(btn.id)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: '6px',
                      border: isSel ? `1.5px solid ${btn.color}` : '1px solid #CBD5E1',
                      background: isSel ? `${btn.color}12` : '#F8FAFC',
                      color: isSel ? btn.color : '#475569',
                      fontSize: '0.73rem',
                      fontWeight: isSel ? 800 : 600,
                      cursor: 'pointer'
                    }}
                  >
                    {btn.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Conflict Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(440px, 1fr))', gap: '14px' }}>
            {allConflictsRaw
              .filter(c => {
                const st = (c.status || '').toLowerCase();
                if (vaultConflictFilter === 'active') return st !== 'resolved' && st !== 'dismissed';
                if (vaultConflictFilter === 'resolved') return st === 'resolved' || st === 'dismissed';
                return true;
              })
              .filter(c => {
                if (!vaultSearch.trim()) return true;
                const q = vaultSearch.toLowerCase();
                const cItem = conflictMap[c.id];
                const clA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
                const clB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);
                return (
                  (c.label || '').toLowerCase().includes(q) ||
                  (clA?.fullText || '').toLowerCase().includes(q) ||
                  (clB?.fullText || '').toLowerCase().includes(q)
                );
              })
              .map((c, idx) => {
                const cItem = conflictMap[c.id];
                const clA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
                const clB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);
                const st = (c.status || '').toLowerCase();
                const isResolved = st === 'resolved' || st === 'dismissed';

                const docEdgeA = graphData?.edges?.find(e => e.target === cItem?.claimAId && e.source.startsWith('doc_'));
                const docEdgeB = graphData?.edges?.find(e => e.target === cItem?.claimBId && e.source.startsWith('doc_'));
                const docA = graphData?.nodes?.find(n => n.id === docEdgeA?.source);
                const docB = graphData?.nodes?.find(n => n.id === docEdgeB?.source);

                return (
                  <div
                    key={c.id}
                    style={{
                      border: isResolved ? '1px solid #BBF7D0' : '1.5px solid #FED7AA',
                      background: isResolved ? '#F0FDF4' : '#FFF7ED',
                      borderRadius: '10px',
                      padding: '14px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      boxShadow: '0 2px 6px rgba(0,0,0,0.03)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '0.64rem',
                          fontWeight: 800,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          background: isResolved ? '#DCFCE7' : '#FFEDD5',
                          color: isResolved ? '#15803D' : '#C2410C',
                          border: isResolved ? '1px solid #86EFAC' : '1px solid #FDBA74'
                        }}>
                          {isResolved ? '✅ RESOLVED' : '⚠️ ACTIVE / HUMAN REVIEW'}
                        </span>
                        <span style={{
                          fontSize: '0.62rem',
                          fontWeight: 800,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: '#FFFFFF',
                          color: '#475569',
                          border: '1px solid #CBD5E1'
                        }}>
                          {c.severity || 'HIGH'} SEVERITY
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => visualizeNodeInDag(c.id, c.label, isResolved)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          border: '1px solid #1D4ED8',
                          background: '#1D4ED8',
                          color: '#FFFFFF',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <span>🕸️ Visualize in DAG</span>
                      </button>
                    </div>

                    <div style={{ fontSize: '0.84rem', fontWeight: 800, color: '#0F172A' }}>
                      #{idx + 1} {c.label}
                    </div>

                    {/* Side-by-Side Clashing Claims */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div style={{ background: '#FFFFFF', padding: '9px 10px', borderRadius: '7px', borderLeft: '3px solid #0284C7', border: '1px solid #E2E8F0' }}>
                        <div style={{ fontSize: '0.62rem', fontWeight: 800, color: '#0284C7', marginBottom: '3px' }}>
                          CLAIM A &bull; {docA?.label || 'Policy Doc'}
                        </div>
                        <p style={{ margin: 0, fontSize: '0.72rem', color: '#1E293B', lineHeight: 1.35 }}>
                          "{clA?.fullText || clA?.label || 'Baseline policy rule'}"
                        </p>
                      </div>

                      <div style={{ background: '#FFFFFF', padding: '9px 10px', borderRadius: '7px', borderLeft: '3px solid #EA580C', border: '1px solid #E2E8F0' }}>
                        <div style={{ fontSize: '0.62rem', fontWeight: 800, color: '#EA580C', marginBottom: '3px' }}>
                          CLAIM B &bull; {docB?.label || 'Policy Doc'}
                        </div>
                        <p style={{ margin: 0, fontSize: '0.72rem', color: '#1E293B', lineHeight: 1.35 }}>
                          "{clB?.fullText || clB?.label || 'Conflicting assertion'}"
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-TAB 5: ATOMIC CLAIMS & AI DECISIONS CATALOG           */}
      {/* ========================================================= */}
      {vaultSubTab === 'claims' && (() => {
        // Resolve parent document and source for any claim
        const resolveClaimProvenance = (cl) => {
          const clDocId = cl.document_id || cl.data?.document_id || cl.data?.doc_id;
          const docEdge = graphData?.edges?.find(e =>
            (e.target === cl.id || e.target === `cl_${cl.id}`) && e.source.startsWith('doc_')
          );
          const resolvedDocId = docEdge
            ? docEdge.source.replace(/^doc_/, '')
            : (clDocId ? String(clDocId).replace(/^doc_/, '') : null);

          const parentDoc = (resolvedDocId
            ? documentsList.find(d => String(d.id).replace(/^doc_/, '') === resolvedDocId)
            : null) || (docEdge ? graphData?.nodes?.find(n => n.id === docEdge.source) : null);

          const parentDocSrcId = parentDoc?.data?.source_id || parentDoc?.source_id;
          const srcEdge = parentDoc
            ? graphData?.edges?.find(e => (e.target === parentDoc.id || e.target === `doc_${parentDoc.id}`) && e.source.startsWith('src_'))
            : null;
          const resolvedSrcId = srcEdge
            ? srcEdge.source.replace(/^src_/, '')
            : (parentDocSrcId ? String(parentDocSrcId).replace(/^src_/, '') : null);
          const clSrcId = cl.source_id || cl.data?.source_id;

          const parentSrc = (resolvedSrcId
            ? sourcesList.find(s => String(s.id).replace(/^src_/, '') === resolvedSrcId)
            : null) || (srcEdge ? graphData?.nodes?.find(n => n.id === srcEdge.source) : null)
            || (clSrcId ? sourcesList.find(s => String(s.id).replace(/^src_/, '') === String(clSrcId).replace(/^src_/, '')) : null);

          return { parentDoc, parentSrc, resolvedDocId, resolvedSrcId };
        };

        const filteredClaims = allClaimsRaw.filter(cl => {
          const isConf = allConflictedClaimIds.has(cl.id);
          if (vaultClaimFilter === 'verified' && isConf) return false;
          if (vaultClaimFilter === 'conflicted' && !isConf) return false;

          const { parentDoc, parentSrc, resolvedDocId, resolvedSrcId } = resolveClaimProvenance(cl);

          // Document filter
          if (vaultDocumentFilter !== 'all') {
            const targetDocClean = String(vaultDocumentFilter).replace(/^doc_/, '');
            const matchDocId = resolvedDocId === targetDocClean || String(parentDoc?.id || '').replace(/^doc_/, '') === targetDocClean;
            if (!matchDocId) return false;
          }

          // Connection / Source filter
          if (vaultSourceFilter !== 'all') {
            const targetSrcClean = String(vaultSourceFilter).replace(/^src_/, '');
            const matchSrcId = resolvedSrcId === targetSrcClean || String(parentSrc?.id || '').replace(/^src_/, '') === targetSrcClean;
            if (!matchSrcId) return false;
          }

          // Search query
          if (vaultSearch.trim()) {
            const q = vaultSearch.toLowerCase();
            const text = `${cl.fullText || cl.label || ''} ${cl.subject || ''} ${cl.predicate || ''} ${cl.object || ''} ${parentDoc?.label || ''} ${parentSrc?.label || ''}`.toLowerCase();
            if (!text.includes(q)) return false;
          }

          return true;
        });

        const hasActiveFilters = vaultDocumentFilter !== 'all' || vaultSourceFilter !== 'all' || vaultClaimFilter !== 'all' || Boolean(vaultSearch.trim());

        return (
          <div style={{
            background: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            {/* Header: Title and Status Chips */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', borderBottom: '1px solid #F1F5F9', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>⚡ Extracted Atomic Claims & Evaluated AI Decisions</span>
                </h3>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.76rem', color: '#64748B' }}>
                  Search and inspect normalized atomic assertions. Filter by document or connector provenance, or visualize in the lineage DAG.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { id: 'all', label: `All Claims (${allClaimsRaw.length})` },
                  { id: 'verified', label: '✅ Verified' },
                  { id: 'conflicted', label: '⚠️ In Conflict' },
                  { id: 'decisions', label: `🤖 AI Decisions (${decisionsList.length})` }
                ].map(f => {
                  const isSel = vaultClaimFilter === f.id;
                  return (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setVaultClaimFilter(f.id)}
                      style={{
                        padding: '5px 10px',
                        borderRadius: '6px',
                        border: isSel ? '1.5px solid #059669' : '1px solid #CBD5E1',
                        background: isSel ? '#ECFDF5' : '#F8FAFC',
                        color: isSel ? '#059669' : '#475569',
                        fontSize: '0.72rem',
                        fontWeight: isSel ? 800 : 600,
                        cursor: 'pointer'
                      }}
                    >
                      {f.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Comprehensive Document & Connection Filter Bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '10px',
              background: '#F8FAFC',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #E2E8F0'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', flex: 1 }}>
                {/* Document-Wise Filter */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText size={13} color="#0284C7" />
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>Document:</span>
                  <select
                    value={vaultDocumentFilter}
                    onChange={e => setVaultDocumentFilter(e.target.value)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.72rem',
                      background: '#FFFFFF',
                      color: '#0F172A',
                      fontWeight: 600,
                      outline: 'none',
                      maxWidth: '240px'
                    }}
                  >
                    <option value="all">All Documents ({documentsList.length})</option>
                    {documentsList.map(doc => (
                      <option key={doc.id} value={doc.id}>
                        {doc.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Connection-Wise Filter */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Server size={13} color="#7C3AED" />
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>Connection:</span>
                  <select
                    value={vaultSourceFilter}
                    onChange={e => setVaultSourceFilter(e.target.value)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.72rem',
                      background: '#FFFFFF',
                      color: '#0F172A',
                      fontWeight: 600,
                      outline: 'none',
                      maxWidth: '220px'
                    }}
                  >
                    <option value="all">All Connections ({sourcesList.length})</option>
                    {sourcesList.map(src => (
                      <option key={src.id} value={src.id}>
                        {src.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Search within Claims */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: '180px', flex: 1 }}>
                  <Search size={13} color="#94A3B8" />
                  <input
                    type="text"
                    placeholder="Search claims text, subject, predicate..."
                    value={vaultSearch}
                    onChange={e => setVaultSearch(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.72rem',
                      background: '#FFFFFF',
                      outline: 'none'
                    }}
                  />
                </div>

                {/* Reset Filters */}
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={() => {
                      setVaultDocumentFilter('all');
                      setVaultSourceFilter('all');
                      setVaultClaimFilter('all');
                      setVaultSearch('');
                    }}
                    style={{
                      background: '#FEE2E2',
                      border: '1px solid #FCA5A5',
                      borderRadius: '6px',
                      padding: '3px 8px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      color: '#B91C1C',
                      cursor: 'pointer'
                    }}
                  >
                    Reset Filters ✕
                  </button>
                )}
              </div>

              {/* Claims Matched Counter */}
              <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600, whiteSpace: 'nowrap' }}>
                Showing <strong style={{ color: '#0F172A' }}>{vaultClaimFilter === 'decisions' ? decisionsList.length : filteredClaims.length}</strong> of {vaultClaimFilter === 'decisions' ? decisionsList.length : allClaimsRaw.length} {vaultClaimFilter === 'decisions' ? 'decisions' : 'claims'}
              </div>
            </div>

            {/* Claims / Decisions Cards Grid */}
            {vaultClaimFilter === 'decisions' ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '12px' }}>
                {decisionsList
                  .filter(d => !vaultSearch.trim() || (d.label || '').toLowerCase().includes(vaultSearch.toLowerCase()))
                  .map(dec => (
                    <div
                      key={dec.id}
                      style={{
                        border: '1px solid #DDD6FE',
                        borderRadius: '10px',
                        padding: '12px 14px',
                        background: '#FAF5FF',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '8px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#7C3AED', background: '#EDE9FE', padding: '2px 7px', borderRadius: '4px' }}>
                          🤖 AI GOVERNANCE DECISION
                        </span>
                        <span className={dec.verdict === 'ALLOW' ? 'badge badge-verified' : 'badge badge-warning'} style={{ fontSize: '0.66rem' }}>
                          {dec.verdict || 'EVALUATED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0F172A' }}>
                        {dec.label}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #E9D5FF', paddingTop: '6px' }}>
                        <button
                          type="button"
                          onClick={() => visualizeNodeInDag(dec.id, dec.label)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            border: '1px solid #7C3AED',
                            background: '#7C3AED',
                            color: '#FFFFFF',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          🕸️ Visualize in DAG
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '10px' }}>
                {filteredClaims.length === 0 ? (
                  <div style={{
                    padding: '40px 20px',
                    textAlign: 'center',
                    background: '#F8FAFC',
                    borderRadius: '8px',
                    border: '1px dashed #CBD5E1',
                    gridColumn: '1 / -1'
                  }}>
                    <ShieldCheck size={28} color="#94A3B8" style={{ margin: '0 auto 8px auto' }} />
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#334155' }}>
                      No atomic claims match the selected filters
                    </div>
                    <p style={{ fontSize: '0.76rem', color: '#64748B', margin: '4px 0 12px 0' }}>
                      Try selecting "All Documents", "All Connections", or clearing search terms.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setVaultDocumentFilter('all');
                        setVaultSourceFilter('all');
                        setVaultClaimFilter('all');
                        setVaultSearch('');
                      }}
                      className="btn btn-secondary"
                      style={{ padding: '6px 14px', fontSize: '0.74rem' }}
                    >
                      Clear All Filters
                    </button>
                  </div>
                ) : (
                  filteredClaims.map(cl => {
                    const isConf = allConflictedClaimIds.has(cl.id);
                    const { parentDoc, parentSrc } = resolveClaimProvenance(cl);

                    return (
                      <div
                        key={cl.id}
                        style={{
                          border: isConf ? '1.5px solid #FED7AA' : '1px solid #E2E8F0',
                          background: isConf ? '#FFF7ED' : '#F8FAFC',
                          borderRadius: '9px',
                          padding: '12px 14px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '8px',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                        }}
                      >
                        {/* Card Header: Document Badge & Connection Badge + Status */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', flexWrap: 'wrap' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
                            {parentDoc ? (
                              <button
                                type="button"
                                onClick={() => setVaultDocumentFilter(parentDoc.id)}
                                style={{
                                  background: '#EFF6FF',
                                  border: '1px solid #BFDBFE',
                                  color: '#0284C7',
                                  fontSize: '0.64rem',
                                  fontWeight: 700,
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px'
                                }}
                                title="Filter by this document"
                              >
                                <FileText size={10} />
                                <span>{parentDoc.label}</span>
                              </button>
                            ) : (
                              <span style={{ fontSize: '0.64rem', color: '#64748B', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                <FileText size={10} />
                                <span>Policy Document</span>
                              </span>
                            )}

                            {parentSrc && (
                              <button
                                type="button"
                                onClick={() => setVaultSourceFilter(parentSrc.id)}
                                style={{
                                  background: '#FAF5FF',
                                  border: '1px solid #DDD6FE',
                                  color: '#7C3AED',
                                  fontSize: '0.64rem',
                                  fontWeight: 700,
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px'
                                }}
                                title="Filter by this connection"
                              >
                                <Server size={10} />
                                <span>{parentSrc.label}</span>
                              </button>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span className={isConf ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.62rem' }}>
                              {isConf ? '⚠️ In Conflict' : '✅ Verified'}
                            </span>
                            <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                              {((cl.trustScore || 0.92) * 100).toFixed(0)}% Trust
                            </span>
                          </div>
                        </div>

                        {/* Claim Text */}
                        <p style={{ margin: 0, fontSize: '0.78rem', color: '#1E293B', lineHeight: 1.4, fontWeight: 500 }}>
                          "{cl.fullText || cl.label}"
                        </p>

                        {/* Card Footer */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #E2E8F0', paddingTop: '6px' }}>
                          <span style={{ fontSize: '0.64rem', color: '#64748B' }}>
                            ID: <code>{cl.id.slice(0, 12)}</code>
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setLineageGranularity('claim');
                              visualizeNodeInDag(cl.id, cl.label);
                            }}
                            style={{
                              padding: '3px 9px',
                              borderRadius: '5px',
                              border: '1px solid #059669',
                              background: '#059669',
                              color: '#FFFFFF',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            🕸️ Visualize in DAG
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        );
      })()}

      {/* 5. Slide-Out All Claims Explorer Drawer */}
      {isDrawerOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.45)',
          backdropFilter: 'blur(4px)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'flex-end',
          animation: 'fadeIn 0.2s ease-out'
        }}>
          {/* Backdrop */}
          <div style={{ flex: 1 }} onClick={() => setIsDrawerOpen(false)} />

          {/* Drawer Content */}
          <div style={{
            width: '620px',
            maxWidth: '92vw',
            height: '100%',
            background: '#ffffff',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.2)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 10000,
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{
              padding: '18px 22px',
              borderBottom: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#f8fafc'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>⚡</span>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>
                    Enterprise Atomic Claims Explorer
                  </h3>
                </div>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                  Search and inspect all {graphData?.nodes?.filter(n => n.type === 'claim')?.length || 0} atomic policy rules extracted across documents.
                </p>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '7px',
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#475569'
                }}
              >
                ✕
              </button>
            </div>

            {/* Filter & Search */}
            <div style={{ padding: '12px 22px', borderBottom: '1px solid #f1f5f9', background: '#fff', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Search claim text, threshold, topic..."
                  value={drawerSearch}
                  onChange={(e) => setDrawerSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px 7px 30px',
                    borderRadius: '7px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.8rem',
                    outline: 'none'
                  }}
                />
                <span style={{ position: 'absolute', left: '10px', top: '8px', fontSize: '0.8rem', color: '#94a3b8' }}>🔍</span>
              </div>

              <select
                value={drawerDocFilter}
                onChange={(e) => setDrawerDocFilter(e.target.value)}
                style={{
                  padding: '7px 10px',
                  borderRadius: '7px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.78rem',
                  background: '#f8fafc',
                  maxWidth: '220px',
                  outline: 'none'
                }}
              >
                <option value="all">All Documents ({documentsList.length})</option>
                {documentsList.map(d => (
                  <option key={d.id} value={d.id}>{d.label}</option>
                ))}
              </select>
            </div>

            {/* Scrollable Claims List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '14px 22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {(() => {
                const allClaims = graphData?.nodes?.filter(n => n.type === 'claim') || [];
                const filtered = allClaims.filter(cl => {
                  if (drawerDocFilter !== 'all') {
                    const matchesDoc = graphData?.edges?.some(e => e.source === drawerDocFilter && e.target === cl.id);
                    if (!matchesDoc) return false;
                  }
                  if (drawerSearch.trim()) {
                    const q = drawerSearch.toLowerCase();
                    const text = (cl.fullText || cl.label || '').toLowerCase();
                    return text.includes(q);
                  }
                  return true;
                });

                if (filtered.length === 0) {
                  return (
                    <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                      <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔎</div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>No claims matched your search</div>
                      <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>Try clearing filters or searching for keywords like "refund", "limit", or "approval".</div>
                    </div>
                  );
                }

                return filtered.map((cl, idx) => {
                  const docEdge = graphData?.edges?.find(e => e.target === cl.id && e.source.startsWith('doc_'));
                  const parentDoc = graphData?.nodes?.find(n => n.id === docEdge?.source);
                  const isConflicted = allConflictedClaimIds.has(cl.id);

                  return (
                    <div
                      key={cl.id}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '9px',
                        border: isConflicted ? '1.5px solid #ea580c' : '1px solid #e2e8f0',
                        background: isConflicted ? '#fff7ed' : '#ffffff',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '7px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.66rem', fontWeight: 800, color: '#64748b' }}>#{idx + 1}</span>
                          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#0284c7' }}>
                            📄 {parentDoc?.label || 'Parent Document'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className={isConflicted ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.64rem' }}>
                            {isConflicted ? '⚠️ In Conflict' : 'Verified'}
                          </span>
                          <span className="badge badge-verified" style={{ fontSize: '0.64rem' }}>
                            {((cl.trustScore || 0.92) * 100).toFixed(0)}% Trust
                          </span>
                        </div>
                      </div>

                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#1e293b', lineHeight: 1.4, fontWeight: 500 }}>
                        "{cl.fullText || cl.label}"
                      </p>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '3px', borderTop: '1px solid #f1f5f9', paddingTop: '6px' }}>
                        <span style={{ fontSize: '0.66rem', color: '#64748b' }}>
                          Scope: <strong>{typeof cl.data?.scope === 'object' && cl.data?.scope !== null ? (Object.entries(cl.data.scope).map(([k, v]) => `${k}: ${v}`).join(', ') || 'Enterprise') : (cl.data?.scope || 'Enterprise')}</strong> &bull; ID: <code>{cl.id.slice(0, 12)}</code>
                        </span>
                        <button
                          onClick={() => {
                            setSelectedNodeId(cl.id);
                            setViewMode('focused');
                            setIsDrawerOpen(false);
                            showToast?.(`Focused DAG on Claim #${cl.id.slice(0, 8)}`);
                          }}
                          style={{
                            padding: '3px 8px',
                            borderRadius: '5px',
                            border: '1px solid #2563eb',
                            background: '#eff6ff',
                            color: '#2563eb',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px'
                          }}
                        >
                          <span>🎯 Focus in DAG</span>
                        </button>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </div>
      )}

      {/* 5. Atlan-Style Proactive Impact Analysis & Blast Radius Drawer */}
      {isImpactReportOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.45)',
          backdropFilter: 'blur(4px)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'flex-end',
          animation: 'fadeIn 0.15s ease'
        }}>
          <div style={{
            width: '600px',
            maxWidth: '92vw',
            height: '100%',
            background: '#ffffff',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{
              padding: '16px 22px',
              borderBottom: '1px solid #E2E8F0',
              background: '#FAFAFA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.66rem', fontWeight: 800, color: '#7C3AED', background: '#F5F3FF', padding: '1px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>
                    ATLAN IMPACT ENGINE
                  </span>
                  <span style={{ fontSize: '0.64rem', color: '#16A34A', fontWeight: 700, background: '#DCFCE7', padding: '1px 6px', borderRadius: '4px' }}>
                    Live Blast Radius
                  </span>
                </div>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '1.05rem', fontWeight: 800, color: '#0F172A' }}>
                  Proactive Impact & Root Cause Analysis
                </h3>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  onClick={() => {
                    const targetNode = selectedNode || graphData?.nodes?.[0];
                    const rows = [
                      ['Asset ID', 'Asset Type', 'Label', 'Relationship', 'Trust Score'],
                      [targetNode?.id, targetNode?.type, targetNode?.label, 'TARGET_ENTITY', targetNode?.trustScore || 'N/A'],
                      ...Array.from(connectedNodeMap.up).map(id => {
                        const n = graphData?.nodes?.find(x => x.id === id);
                        return [id, n?.type, n?.label, 'UPSTREAM_ROOT_CAUSE', n?.trustScore || 'N/A'];
                      }),
                      ...Array.from(connectedNodeMap.down).map(id => {
                        const n = graphData?.nodes?.find(x => x.id === id);
                        return [id, n?.type, n?.label, 'DOWNSTREAM_BLAST_RADIUS', n?.trustScore || 'N/A'];
                      })
                    ];
                    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.map(cell => `"${cell || ''}"`).join(",")).join("\n");
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", `trulin_impact_report_${targetNode?.id || 'export'}.csv`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    showToast?.("Exported Impact Analysis Report to CSV");
                  }}
                  style={{
                    padding: '4px 9px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    color: '#334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Export Impact Report as CSV"
                >
                  <Download size={12} />
                  <span>CSV</span>
                </button>

                <button
                  onClick={() => {
                    const targetNode = selectedNode || graphData?.nodes?.[0];
                    const text = `Trulin Impact Analysis for ${targetNode?.label} (${targetNode?.type})\nUpstream Roots: ${connectedNodeMap.up.size} assets\nDownstream Blast Radius: ${connectedNodeMap.down.size} decisions/systems affected\nActive Conflicts: ${conflictsList.length}`;
                    navigator.clipboard.writeText(text);
                    showToast?.("Copied Impact Summary to Clipboard");
                  }}
                  style={{
                    padding: '4px 9px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    color: '#334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Copy Report Summary for Slack / Jira"
                >
                  <Share2 size={12} />
                  <span>Copy</span>
                </button>

                <button
                  onClick={() => setIsImpactReportOpen(false)}
                  style={{
                    width: '28px',
                    height: '28px',
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
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Scrollable Report Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Target Entity Overview */}
              {(() => {
                const target = selectedNode || graphData?.nodes?.[0];
                if (!target) return null;
                const upstreamCount = graphData?.edges?.filter(e => e.target === target.id).length || 0;
                const downstreamCount = graphData?.edges?.filter(e => e.source === target.id).length || 0;

                return (
                  <div style={{
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1.5px solid #2563EB',
                    background: 'linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)',
                    boxShadow: '0 2px 8px rgba(37,99,235,0.08)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#1D4ED8', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Home size={11} /> TARGET INVESTIGATED ASSET
                      </span>
                      <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#64748B' }}>
                        ID: <code>{target.id}</code>
                      </span>
                    </div>

                    <h4 style={{ margin: '0 0 6px 0', fontSize: '0.92rem', fontWeight: 800, color: '#0F172A' }}>
                      {target.label}
                    </h4>
                    {target.fullText && (
                      <p style={{ margin: '0 0 10px 0', fontSize: '0.78rem', color: '#475569', lineHeight: 1.45 }}>
                        "{target.fullText}"
                      </p>
                    )}

                    {/* Stats Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', paddingTop: '10px', borderTop: '1px solid #DBEAFE' }}>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>UPSTREAM ROOTS</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#1D4ED8' }}>{upstreamCount}</div>
                      </div>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>DOWNSTREAM IMPACT</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#7C3AED' }}>{downstreamCount}</div>
                      </div>
                      <div style={{ background: '#FFFFFF', padding: '8px 10px', borderRadius: '6px', border: '1px solid #BFDBFE' }}>
                        <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 700 }}>BAYESIAN TRUST</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 900, color: (target.trustScore || 0.9) >= 0.85 ? '#16A34A' : '#EA580C' }}>
                          {((target.trustScore || 0.92) * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* 1. Root Cause Analysis (Upstream Dependencies) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>🔌</span> Upstream Root Causes ({connectedNodeMap.up.size})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Where this asset originates</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {Array.from(connectedNodeMap.up).length === 0 ? (
                    <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '6px', fontSize: '0.74rem', color: '#94A3B8', textAlign: 'center' }}>
                      No direct upstream dependencies identified.
                    </div>
                  ) : (
                    Array.from(connectedNodeMap.up).map(id => {
                      const n = graphData?.nodes?.find(x => x.id === id);
                      if (!n) return null;
                      return (
                        <div key={id} style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: '1px solid #E2E8F0',
                          background: '#FFFFFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <span style={{ fontSize: '0.62rem', fontWeight: 800, color: '#2563EB', background: '#EFF6FF', padding: '1px 5px', borderRadius: '3px', marginRight: '6px' }}>
                              {n.type.toUpperCase()}
                            </span>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#1E293B' }}>
                              {n.label}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedNodeId(n.id);
                              setViewMode('focused');
                              setIsImpactReportOpen(false);
                              showToast?.(`Focused on ${n.label}`);
                            }}
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              border: '1px solid #CBD5E1',
                              background: '#F8FAFC',
                              fontSize: '0.66rem',
                              fontWeight: 700,
                              color: '#2563EB',
                              cursor: 'pointer'
                            }}
                          >
                            Trace
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* 2. Active Policy Contradictions */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#EA580C', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>⚖️</span> Active Contradictions & Rule Clashes ({conflictsList.length})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Requires human verification</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {conflictsList.slice(0, 5).map((c, i) => (
                    <div key={c.id} style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1.5px solid #EA580C',
                      background: '#FFF7ED',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '5px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#C2410C', background: '#FFEDD5', padding: '1px 6px', borderRadius: '4px' }}>
                          #{i + 1} [{c.severity || 'HIGH'}]
                        </span>
                        <span style={{ fontSize: '0.64rem', color: '#9A3412', fontWeight: 700 }}>
                          {c.status || 'REVIEW_NEEDED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#9A3412' }}>
                        {c.label}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #FED7AA', paddingTop: '4px' }}>
                        <button
                          onClick={() => {
                            setSelectedConflictId(c.id);
                            setSelectedNodeId(c.id);
                            setViewMode('conflicts');
                            setIsImpactReportOpen(false);
                            showToast?.(`Spotlighted Contradiction #${i + 1}`);
                          }}
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            border: '1px solid #EA580C',
                            background: '#EA580C',
                            color: '#FFFFFF',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          Spotlight Conflict in DAG
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 3. Downstream Blast Radius (Impacted AI Decisions & Agents) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.84rem', fontWeight: 800, color: '#7C3AED', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span>🤖</span> Downstream Blast Radius ({connectedNodeMap.down.size})
                  </h4>
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>AI decisions & workflows influenced</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {Array.from(connectedNodeMap.down).length === 0 ? (
                    <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '6px', fontSize: '0.74rem', color: '#94A3B8', textAlign: 'center' }}>
                      No direct downstream decisions identified.
                    </div>
                  ) : (
                    Array.from(connectedNodeMap.down).map(id => {
                      const n = graphData?.nodes?.find(x => x.id === id);
                      if (!n) return null;
                      return (
                        <div key={id} style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: '1px solid #E2E8F0',
                          background: '#FFFFFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <span style={{ fontSize: '0.62rem', fontWeight: 800, color: '#7C3AED', background: '#FAF5FF', padding: '1px 5px', borderRadius: '3px', marginRight: '6px' }}>
                              {n.type.toUpperCase()}
                            </span>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#1E293B' }}>
                              {n.label}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedNodeId(n.id);
                              setViewMode('focused');
                              setIsImpactReportOpen(false);
                              showToast?.(`Focused on decision ${n.label}`);
                            }}
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              border: '1px solid #7C3AED',
                              background: '#FAF5FF',
                              fontSize: '0.66rem',
                              fontWeight: 700,
                              color: '#7C3AED',
                              cursor: 'pointer'
                            }}
                          >
                            Inspect
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Executive Decommission / Permanent Purge Modal */}
      <ExecutiveDeleteModal
        isOpen={!!deleteTargetAsset}
        onClose={() => setDeleteTargetAsset(null)}
        asset={deleteTargetAsset}
        onSuccess={({ assetId }) => {
          if (openedAssetId && (
            openedAssetId === assetId ||
            openedAssetId === `doc_${assetId}` ||
            openedAssetId === `src_${assetId}` ||
            String(openedAssetId).includes(String(assetId))
          )) {
            setOpenedAssetId(null);
          }
          fetchLineage();
        }}
        showToast={showToast}
      />
    </div>
  );
}

