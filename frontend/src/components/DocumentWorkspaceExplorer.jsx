import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Folder,
  FolderPlus,
  ChevronRight,
  ChevronDown,
  Upload,
  Move,
  Trash2,
  Edit3,
  FileText,
  ShieldCheck,
  RefreshCw,
  Plus,
  X,
  Search,
  Inbox,
  Layers,
  Copy,
  Eye,
  Check,
  BarChart2,
  Maximize2,
  ExternalLink,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
  Info,
  Network,
  Sparkles,
  BookOpen,
  Bot,
  Shield,
  Lock,
  Scale,
  Coins,
  Users,
  MessageSquare,
  MessageCircle,
  Hash,
  CheckSquare,
  Briefcase,
  ArrowLeft,
  ChevronLeft
} from 'lucide-react';

// Lightweight Executive Markdown & Document Formatter
const renderFormattedMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let currentList = [];
  let inCodeBlock = false;
  let codeBuffer = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} style={{ margin: '4px 0 6px 0', paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {currentList.map((item, idx) => (
            <li key={idx} style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.45 }}>
              {item}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushCode = () => {
    if (codeBuffer.length > 0) {
      elements.push(
        <pre key={`code-${elements.length}`} style={{
          background: '#0F172A',
          color: '#F8FAFC',
          padding: '10px 14px',
          borderRadius: 0,
          fontSize: '0.74rem',
          fontFamily: 'Consolas, Monaco, monospace',
          overflowX: 'auto',
          margin: '6px 0 10px 0',
          lineHeight: 1.45
        }}>
          <code>{codeBuffer.join('\n')}</code>
        </pre>
      );
      codeBuffer = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(rawLine);
      continue;
    }

    if (!trimmed) {
      flushList();
      continue;
    }

    // Heading 1: # Title
    if (trimmed.startsWith('# ')) {
      flushList();
      const title = trimmed.substring(2).replace(/^#+\s*/, '');
      elements.push(
        <div key={`h1-${i}`} style={{
          fontSize: '1.10rem',
          fontWeight: 800,
          color: '#0F172A',
          margin: '6px 0 8px 0',
          lineHeight: 1.3,
          letterSpacing: '-0.01em',
          borderBottom: '1px solid #F1F5F9',
          paddingBottom: '4px'
        }}>
          {title}
        </div>
      );
    }
    // Heading 2: ## Subtitle
    else if (trimmed.startsWith('## ')) {
      flushList();
      const sub = trimmed.substring(3).trim();
      elements.push(
        <div key={`h2-${i}`} style={{
          fontSize: '0.92rem',
          fontWeight: 700,
          color: '#1E293B',
          margin: '8px 0 4px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span style={{ width: '3px', height: '12px', background: '#3B82F6', display: 'inline-block' }} />
          <span>{sub}</span>
        </div>
      );
    }
    // Heading 3: ### Subtitle
    else if (trimmed.startsWith('### ')) {
      flushList();
      const sub = trimmed.substring(4).trim();
      elements.push(
        <div key={`h3-${i}`} style={{
          fontSize: '0.84rem',
          fontWeight: 700,
          color: '#334155',
          margin: '6px 0 3px 0'
        }}>
          {sub}
        </div>
      );
    }
    // Bullet item (- or *)
    else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      currentList.push(trimmed.substring(2));
    }
    // Numbered item (e.g. 1. or 2.)
    else if (/^\d+\.\s/.test(trimmed)) {
      currentList.push(trimmed.replace(/^\d+\.\s*/, ''));
    }
    // Regular text paragraph
    else {
      flushList();
      elements.push(
        <p key={`p-${i}`} style={{
          fontSize: '0.82rem',
          color: '#334155',
          lineHeight: 1.5,
          margin: '0 0 6px 0',
          wordBreak: 'break-word'
        }}>
          {trimmed}
        </p>
      );
    }
  }

  flushList();
  flushCode();

  return elements;
};

export default function DocumentWorkspaceExplorer({
  activeOrg,
  token,
  user,
  showToast,
  onInspectDocument,
  onViewClaims,
  onNavigateToCuratorApprovals,
  onClaimExtracted,
  onDocumentUploaded,
  readOnly = false,
}) {
  // Folder tree & all documents state
  const [folders, setFolders] = useState([]);
  const [folderTree, setFolderTree] = useState([]);
  const [allDocuments, setAllDocuments] = useState([]);
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [initialLoading, setInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadingFolderIds, setLoadingFolderIds] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  // Selected file & preview state
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedDocDetails, setSelectedDocDetails] = useState(null);
  const [selectedDocArtifacts, setSelectedDocArtifacts] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [activeFacilityTab, setActiveFacilityTab] = useState('preview'); // 'preview' | 'claims'
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [claimSearchQuery, setClaimSearchQuery] = useState('');
  const [claimTriageFilter, setClaimTriageFilter] = useState('candidate'); // 'candidate' | 'verified' | 'all'
  const [isReviewingClaim, setIsReviewingClaim] = useState(false);
  const [editingClaimId, setEditingClaimId] = useState(null);
  const [editClaimForm, setEditClaimForm] = useState({
    claim_text: '',
    subject: '',
    predicate: '',
    object: ''
  });
  const [isFullFileReaderOpen, setIsFullFileReaderOpen] = useState(false);
  const [fullReaderSearch, setFullReaderSearch] = useState('');
  const [readerViewMode, setReaderViewMode] = useState('text'); // 'text' | 'pdf'
  const [copiedReaderText, setCopiedReaderText] = useState(false);

  // Close reader modal on Escape key
  useEffect(() => {
    if (!isFullFileReaderOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsFullFileReaderOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullFileReaderOpen]);

  // Folder Insights state
  const [metrics, setMetrics] = useState(null);
  const [showInsightsModal, setShowInsightsModal] = useState(false);

  // Context Menu state
  const [contextMenu, setContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    type: null, // 'folder' | 'document' | 'canvas'
    target: null,
  });

  // Inline folder creation state (OS / Drive style in-place creation)
  const [creatingInParentId, setCreatingInParentId] = useState(undefined); // undefined = none, null = root, string = folderId
  const [creatingFolderName, setCreatingFolderName] = useState('New folder');
  const [isSavingNewFolder, setIsSavingNewFolder] = useState(false);
  const inlineCreateInputRef = useRef(null);
  const creatingInParentIdRef = useRef(creatingInParentId);
  creatingInParentIdRef.current = creatingInParentId;

  // Inline rename state (OS / Drive style in-place editing)
  const [renamingFolderId, setRenamingFolderId] = useState(null);
  const [renameInputVal, setRenameInputVal] = useState('');
  const [isSavingRename, setIsSavingRename] = useState(false);
  const inlineRenameInputRef = useRef(null);

  const [showMoveFolderModal, setShowMoveFolderModal] = useState(false);
  const [movingFolder, setMovingFolder] = useState(null);
  const [moveFolderTargetId, setMoveFolderTargetId] = useState('');

  const [showMoveDocModal, setShowMoveDocModal] = useState(false);
  const [movingDoc, setMovingDoc] = useState(null);
  const [moveDocTargetFolderId, setMoveDocTargetFolderId] = useState('');

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFolderId, setUploadFolderId] = useState(null);
  const [uploadDocType, setUploadDocType] = useState('policy');
  const [isUploading, setIsUploading] = useState(false);

  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
  const directoryContainerRef = useRef(null);

  // Dismiss context menu
  useEffect(() => {
    const handleDismiss = () => {
      if (contextMenu.visible) {
        setContextMenu(prev => ({ ...prev, visible: false }));
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') handleDismiss();
    };
    window.addEventListener('click', handleDismiss);
    window.addEventListener('scroll', handleDismiss, true);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('click', handleDismiss);
      window.removeEventListener('scroll', handleDismiss, true);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenu.visible]);

  // Auto-focus and highlight folder text when entering inline rename mode
  useEffect(() => {
    if (renamingFolderId) {
      const timer = setTimeout(() => {
        if (inlineRenameInputRef.current) {
          inlineRenameInputRef.current.focus();
          inlineRenameInputRef.current.select();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [renamingFolderId]);

  // Auto-focus and highlight folder text when entering inline create mode
  useEffect(() => {
    if (creatingInParentId !== undefined) {
      const timer = setTimeout(() => {
        if (inlineCreateInputRef.current) {
          inlineCreateInputRef.current.focus();
          inlineCreateInputRef.current.select();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [creatingInParentId]);

  // Keyboard shortcuts: F2 for Rename, Ctrl+Shift+N for New Folder
  useEffect(() => {
    const handleGlobalFolderKeys = (e) => {
      if (readOnly) return;
      if (e.key === 'F2' && activeFolderId && !renamingFolderId && creatingInParentId === undefined) {
        const f = folders.find(item => item.id === activeFolderId);
        if (f && !f.is_system) {
          e.preventDefault();
          setRenamingFolderId(f.id);
          setRenameInputVal(f.name);
        }
      } else if (e.ctrlKey && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
        e.preventDefault();
        startInlineCreate(activeFolderId || null);
      }
    };
    window.addEventListener('keydown', handleGlobalFolderKeys);
    return () => window.removeEventListener('keydown', handleGlobalFolderKeys);
  }, [activeFolderId, renamingFolderId, creatingInParentId, folders, readOnly]);

  // 1. Fetch folders and documents (initial or full reload)
  const fetchData = useCallback(async (isManual = false) => {
    if (isManual) {
      setIsRefreshing(true);
    }
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const [flatRes, treeRes, docsRes] = await Promise.all([
        fetch(`/v1/folders?organization_id=${orgId}&tree=false`, { headers }),
        fetch(`/v1/folders?organization_id=${orgId}&tree=true`, { headers }),
        fetch(`/v1/documents?organization_id=${orgId}&limit=1000`, { headers })
      ]);

      if (flatRes.ok) {
        const flatData = await flatRes.json();
        setFolders(flatData);
        setActiveFolderId(prev => {
          if (prev && flatData.some(f => f.id === prev)) return prev;
          const inbox = flatData.find(f => f.is_system) || flatData[0];
          if (inbox) {
            setExpandedFolders(exp => new Set([...exp, inbox.id]));
            return inbox.id;
          }
          return null;
        });
      }

      if (treeRes.ok) {
        const treeData = await treeRes.json();
        setFolderTree(treeData);
      }

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        const activeDocs = (Array.isArray(docsData) ? docsData : []).filter(d => {
          const st = (d.status || '').toLowerCase();
          return st !== 'inactive' && st !== 'deleted' && st !== 'archived';
        });
        setAllDocuments(activeDocs);
        setSelectedDocId(prev => {
          if (prev && activeDocs.some(d => d.id === prev)) return prev;
          return null;
        });
      }
    } catch (err) {
      console.error('Failed to load workspace directory:', err);
      showToast?.('Error loading directory', 'error');
    } finally {
      setInitialLoading(false);
      setIsRefreshing(false);
    }
  }, [orgId, token, showToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Group documents by folder_id
  const docsByFolder = useMemo(() => {
    const map = {};
    for (const doc of allDocuments) {
      const fId = doc.folder_id || 'unassigned';
      if (!map[fId]) map[fId] = [];
      map[fId].push(doc);
    }
    return map;
  }, [allDocuments]);

  // Active folder object
  const activeFolder = useMemo(() => {
    return folders.find(f => f.id === activeFolderId) || null;
  }, [folders, activeFolderId]);

  // Breadcrumb path from root to active folder
  const breadcrumbs = useMemo(() => {
    if (!activeFolderId) return [{ id: null, name: 'Vault Root' }];
    const chain = [];
    let cur = folders.find(f => f.id === activeFolderId);
    while (cur) {
      chain.unshift(cur);
      if (!cur.parent_id) break;
      cur = folders.find(f => f.id === cur.parent_id);
    }
    return [{ id: null, name: 'Vault Root' }, ...chain];
  }, [folders, activeFolderId]);

  // Direct subfolders for current folder
  const currentChildFolders = useMemo(() => {
    return folders.filter(f => f.parent_id === activeFolderId);
  }, [folders, activeFolderId]);

  // Direct documents for current folder
  const currentFolderDocs = useMemo(() => {
    let rawDocs = [];
    if (!activeFolderId) {
      const inbox = folders.find(f => f.is_system && f.folder_type === 'inbox');
      rawDocs = inbox ? (docsByFolder[inbox.id] || docsByFolder['unassigned'] || []) : allDocuments;
    } else {
      const current = folders.find(f => f.id === activeFolderId);
      if (current?.is_system && current?.folder_type === 'inbox') {
        rawDocs = (docsByFolder[activeFolderId] || []).concat(docsByFolder['unassigned'] || []);
      } else {
        rawDocs = docsByFolder[activeFolderId] || [];
      }
    }
    // Deduplicate by unique document id and title/content_hash to prevent duplicate table rows
    const seenIds = new Set();
    const uniqueDocs = [];
    for (const d of rawDocs) {
      if (!d || !d.id) continue;
      if (seenIds.has(d.id)) continue;
      seenIds.add(d.id);
      uniqueDocs.push(d);
    }
    return uniqueDocs;
  }, [activeFolderId, folders, docsByFolder, allDocuments]);

  // Handler for intelligent auto-organize
  const [isAutoOrganizing, setIsAutoOrganizing] = useState(false);
  const handleAutoOrganize = async () => {
    setIsAutoOrganizing(true);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      showToast?.('Intelligently auto-organizing documents into enterprise folders...');
      const res = await fetch(`/v1/folders/auto-organize?organization_id=${orgId}`, {
        method: 'POST',
        headers
      });

      if (res.ok) {
        const data = await res.json();
        showToast?.(`Successfully filed ${data.organized_count} document${data.organized_count === 1 ? '' : 's'} into enterprise domain & connector folders!`);
        await fetchData(true);
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Auto-organize failed', 'error');
      }
    } catch (err) {
      showToast?.('Error organizing documents: ' + err.message, 'error');
    } finally {
      setIsAutoOrganizing(false);
    }
  };

  // Helper to render icon for folders
  const renderFolderIcon = (node, size = 15) => {
    const color = node.color || '#FFAB4A';
    if (node.is_system && node.folder_type === 'inbox') {
      return <Inbox size={size} style={{ color: '#6366F1', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'governance') {
      return <Shield size={size} style={{ color: '#FFAB4A', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'connectors') {
      return <Network size={size} style={{ color: '#6366F1', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'connector_service' || node.name === 'Slack') {
      return <MessageCircle size={size} style={{ color: '#4A154B', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'slack_channels_root' || node.name === 'Slack Channels') {
      return <Hash size={size} style={{ color: '#E11D48', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'slack_channel' || (node.name && node.name.startsWith('#'))) {
      return <Hash size={size} style={{ color: '#3B82F6', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'slack_messages' || node.name === 'Slack Messages') {
      return <MessageSquare size={size} style={{ color: '#8B5CF6', flexShrink: 0 }} />;
    }
    if (node.folder_type === 'slack_documents' || node.name === 'Slack Documents') {
      return <FileText size={size} style={{ color: '#10B981', flexShrink: 0 }} />;
    }
    if (node.icon === 'lock') return <Lock size={size} style={{ color: '#3B82F6', flexShrink: 0 }} />;
    if (node.icon === 'scale') return <Scale size={size} style={{ color: '#8B5CF6', flexShrink: 0 }} />;
    if (node.icon === 'dollar-sign') return <Coins size={size} style={{ color: '#10B981', flexShrink: 0 }} />;
    if (node.icon === 'users') return <Users size={size} style={{ color: '#F59E0B', flexShrink: 0 }} />;
    if (node.icon === 'message-square') return <MessageSquare size={size} style={{ color: '#E11D48', flexShrink: 0 }} />;
    if (node.icon === 'git-branch') return <GitBranch size={size} style={{ color: '#334155', flexShrink: 0 }} />;
    if (node.icon === 'book-open') return <BookOpen size={size} style={{ color: '#0284C7', flexShrink: 0 }} />;
    if (node.icon === 'check-square') return <CheckSquare size={size} style={{ color: '#0284C7', flexShrink: 0 }} />;
    if (node.icon === 'briefcase') return <Briefcase size={size} style={{ color: '#64748B', flexShrink: 0 }} />;
    return <Folder size={size} style={{ color, flexShrink: 0 }} />;
  };

  // Helper to render source badge
  const renderSourceBadge = (doc) => {
    const title = (doc.title || '').toLowerCase();
    const type = (doc.document_type || '').toLowerCase();
    if (type === 'slack_message' || title.includes('slack')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#FEE2E2', color: '#991B1B', fontWeight: 600 }}>
          <MessageSquare size={10} /> Slack
        </span>
      );
    }
    if (title.includes('github')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#F1F5F9', color: '#334155', fontWeight: 600 }}>
          <GitBranch size={10} /> GitHub
        </span>
      );
    }
    if (title.includes('confluence')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#E0F2FE', color: '#0369A1', fontWeight: 600 }}>
          <BookOpen size={10} /> Confluence
        </span>
      );
    }
    if (title.includes('jira')) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#E0F2FE', color: '#0284C7', fontWeight: 600 }}>
          <CheckSquare size={10} /> Jira
        </span>
      );
    }
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 7px', borderRadius: '4px', background: '#FFF7ED', color: '#C2410C', fontWeight: 600 }}>
        <Upload size={10} /> Manual Upload
      </span>
    );
  };

  // 2. Fetch details & artifacts for selected document (Live Preview)
  useEffect(() => {
    if (!selectedDocId) {
      setSelectedDocDetails(null);
      setSelectedDocArtifacts(null);
      setSelectedClaimId(null);
      return;
    }

    let isMounted = true;
    async function loadDocPreview() {
      setLoadingPreview(true);
      try {
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        headers['X-Organization-Id'] = orgId;

        const [docRes, artRes] = await Promise.all([
          fetch(`/v1/documents/${selectedDocId}`, { headers }),
          fetch(`/v1/documents/${selectedDocId}/artifacts`, { headers })
        ]);

        if (isMounted) {
          if (docRes.ok) {
            const docData = await docRes.json();
            setSelectedDocDetails(docData);
          }
          if (artRes.ok) {
            const artData = await artRes.json();
            setSelectedDocArtifacts(artData);
            if (artData.claims && artData.claims.length > 0) {
              setSelectedClaimId(artData.claims[0].id);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load document preview:', err);
      } finally {
        if (isMounted) setLoadingPreview(false);
      }
    }

    loadDocPreview();
    return () => {
      isMounted = false;
    };
  }, [selectedDocId, orgId, token]);

  // Handle candidate claim review triage action (approve, reject, edit)
  const handleClaimReviewAction = useCallback(async (claimId, action, customData = null) => {
    if (!claimId) return;
    setIsReviewingClaim(true);
    try {
      const payload = {
        action,
        reviewer_id: user?.id || undefined,
        reviewer_notes: customData?.notes || `Triage action '${action}' from Document Workspace`
      };
      if (action === 'edit' && customData) {
        payload.edited_claim_text = customData.claim_text;
        payload.edited_subject = customData.subject;
        payload.edited_predicate = customData.predicate;
        payload.edited_object = customData.object;
      }

      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (orgId) headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/review/${claimId}/action`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Action failed with status ${res.status}`);
      }

      // Optimistically update selectedDocArtifacts
      setSelectedDocArtifacts(prev => {
        if (!prev || !prev.claims) return prev;
        const nextClaims = prev.claims.map(c => {
          if (c.id === claimId) {
            return {
              ...c,
              status: action === 'reject' ? 'rejected' : 'verified',
              trust_score: action === 'reject' ? c.trust_score : 1.0,
              confidence: action === 'reject' ? c.confidence : 1.0,
              ...(action === 'edit' && customData ? customData : {})
            };
          }
          return c;
        });
        return { ...prev, claims: nextClaims };
      });

      setEditingClaimId(null);
      showToast?.(
        action === 'approve'
          ? '✓ Claim certified & verified for autonomous agents!'
          : action === 'edit'
          ? '✓ Claim edited & certified successfully!'
          : 'Claim rejected & removed from active context.',
        'success'
      );
      onClaimExtracted?.();
    } catch (err) {
      console.error('Review action failed:', err);
      showToast?.(err.message || 'Failed to complete review action.', 'error');
    } finally {
      setIsReviewingClaim(false);
    }
  }, [token, orgId, user, showToast, onClaimExtracted]);

  // 3. Fetch folder metrics for Insights modal
  const fetchFolderMetrics = useCallback(async (folderId) => {
    if (!folderId) return;
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(
        `/v1/folders/${folderId}/metrics?organization_id=${orgId}&recursive=true`,
        { headers }
      );
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Failed to load folder metrics:', err);
    }
  }, [orgId, token]);

  // Handle clicking or expanding a specific folder
  // Loads contents & displays spinner ONLY at that particular folder, never hiding the tree
  const handleFolderClick = async (node, e) => {
    e?.stopPropagation();
    if (!node?.id) return;
    const folderId = node.id;
    setActiveFolderId(folderId);

    const isExpanded = expandedFolders.has(folderId);

    if (isExpanded) {
      // Collapse folder immediately without loading
      setExpandedFolders(prev => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
      return;
    }

    // Expanding: expand immediately in UI
    setExpandedFolders(prev => new Set(prev).add(folderId));

    // Show loading spinner ONLY on this specific folder
    setLoadingFolderIds(prev => new Set(prev).add(folderId));

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folderId}/documents?organization_id=${orgId}&recursive=false`, { headers });
      if (res.ok) {
        const data = await res.json();
        const folderDocs = (data.items || []).filter(d => {
          const st = (d.status || '').toLowerCase();
          return st !== 'inactive' && st !== 'deleted' && st !== 'archived';
        });
        setAllDocuments(prev => {
          const map = new Map(
            prev
              .filter(d => {
                const st = (d.status || '').toLowerCase();
                return st !== 'inactive' && st !== 'deleted' && st !== 'archived';
              })
              .map(d => [d.id, d])
          );
          folderDocs.forEach(d => map.set(d.id, d));
          return Array.from(map.values());
        });
      }
    } catch (err) {
      console.error('Error fetching documents for folder:', folderId, err);
    } finally {
      setLoadingFolderIds(prev => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
    }
  };

  const toggleExpand = (folderId, e) => {
    e?.stopPropagation();
    const folderNode = folders.find(f => f.id === folderId);
    if (folderNode) {
      handleFolderClick(folderNode, e);
    } else {
      setExpandedFolders(prev => {
        const next = new Set(prev);
        if (next.has(folderId)) next.delete(folderId);
        else next.add(folderId);
        return next;
      });
    }
  };

  // Open context menu
  const openContextMenu = (e, type, target) => {
    e.preventDefault();
    e.stopPropagation();

    const menuWidth = 200;
    const menuHeight = 250;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    setContextMenu({
      visible: true,
      x: Math.max(10, x),
      y: Math.max(10, y),
      type,
      target
    });
  };

  // Start inline folder creation in a parent folder (or root if null)
  const startInlineCreate = (parentId = null) => {
    if (readOnly) return;
    setCreatingInParentId(parentId);
    setCreatingFolderName('New folder');
    if (parentId) {
      setExpandedFolders(prev => new Set([...prev, parentId]));
    }
  };

  // Commit inline folder creation (called on Enter or blur)
  const commitInlineCreate = async (overrideName) => {
    const parentIdToUse = creatingInParentIdRef.current;
    if (isSavingNewFolder || parentIdToUse === undefined) return;
    const trimmed = (overrideName !== undefined ? overrideName : creatingFolderName || '').trim();
    if (!trimmed) {
      setCreatingInParentId(undefined);
      return;
    }

    setIsSavingNewFolder(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders?organization_id=${orgId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: trimmed,
          parent_id: parentIdToUse,
          color: '#3B82F6',
          icon: 'folder'
        })
      });

      if (res.ok) {
        const created = await res.json();
        showToast?.(`Folder '${created.name}' created.`);
        setCreatingInParentId(undefined);
        if (parentIdToUse) {
          setExpandedFolders(prev => new Set([...prev, parentIdToUse]));
        }
        await fetchData();
        setActiveFolderId(created.id);
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to create folder', 'error');
        setCreatingInParentId(undefined);
      }
    } catch (err) {
      showToast?.('Error creating folder: ' + err.message, 'error');
      setCreatingInParentId(undefined);
    } finally {
      setIsSavingNewFolder(false);
    }
  };

  // Inline rename commit handler (called on Enter or blur)
  const commitInlineRename = async (folderId, newName) => {
    if (isSavingRename) return;

    const trimmed = (newName || '').trim();
    const originalFolder = folders.find(f => f.id === folderId);

    // If empty or unchanged, cancel cleanly
    if (!trimmed || (originalFolder && originalFolder.name === trimmed)) {
      setRenamingFolderId(null);
      return;
    }

    setIsSavingRename(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folderId}?organization_id=${orgId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ name: trimmed })
      });

      if (res.ok) {
        const updated = await res.json();
        showToast?.(`Folder renamed to '${updated.name}'.`);
        // Immediately update folders and tree in memory without full-page reloads
        setFolders(prev => prev.map(f => f.id === folderId ? { ...f, name: updated.name } : f));
        setFolderTree(prev => {
          const updateTree = (nodes) => nodes.map(n => {
            if (n.id === folderId) return { ...n, name: updated.name };
            if (n.children && n.children.length > 0) return { ...n, children: updateTree(n.children) };
            return n;
          });
          return updateTree(prev);
        });
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Rename failed', 'error');
      }
    } catch (err) {
      showToast?.('Error renaming folder: ' + err.message, 'error');
    } finally {
      setIsSavingRename(false);
      setRenamingFolderId(null);
    }
  };

  // Move folder handler
  const handleMoveFolder = async (e) => {
    e?.preventDefault();
    if (!movingFolder) return;

    const targetParentId = moveFolderTargetId === 'root' || !moveFolderTargetId ? null : moveFolderTargetId;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${movingFolder.id}/move?organization_id=${orgId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ new_parent_id: targetParentId })
      });

      if (res.ok) {
        showToast?.(`Folder moved successfully.`);
        setShowMoveFolderModal(false);
        setMovingFolder(null);
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Move failed', 'error');
      }
    } catch (err) {
      showToast?.('Error moving folder: ' + err.message, 'error');
    }
  };

  // Delete folder handler
  const handleDeleteFolder = async (folder) => {
    if (folder.is_system) {
      showToast?.('System Inbox cannot be deleted.', 'error');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete folder '${folder.name}'? It must be completely empty.`)) {
      return;
    }

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/folders/${folder.id}?organization_id=${orgId}`, {
        method: 'DELETE',
        headers
      });

      if (res.ok) {
        showToast?.(`Folder '${folder.name}' deleted.`);
        if (activeFolderId === folder.id) {
          const inbox = folders.find(f => f.is_system);
          setActiveFolderId(inbox ? inbox.id : null);
        }
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Delete failed', 'error');
      }
    } catch (err) {
      showToast?.('Error deleting folder: ' + err.message, 'error');
    }
  };

  // Delete document handler
  const handleDeleteDocument = async (doc) => {
    if (!doc || !doc.id) return;
    if (!window.confirm(`Are you sure you want to delete document '${doc.title}'?`)) {
      return;
    }

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const userRole = user?.role || 'admin';
      const userName = user?.name || 'Administrator';
      const userId = user?.id || '';

      const res = await fetch(`/v1/documents/${doc.id}?mode=permanent&user_role=${encodeURIComponent(userRole)}&user_name=${encodeURIComponent(userName)}&user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE',
        headers
      });

      if (res.ok) {
        showToast?.(`Document '${doc.title}' deleted.`);
        if (selectedDocId === doc.id) {
          setSelectedDocId(null);
          setSelectedDocDetails(null);
          setSelectedDocArtifacts(null);
        }
        // Immediately remove from allDocuments so folder structure and files list update instantly
        setAllDocuments(prev => prev.filter(d => d.id !== doc.id));
        await fetchData(true);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast?.(err.detail || 'Delete failed', 'error');
      }
    } catch (err) {
      showToast?.('Error deleting document: ' + err.message, 'error');
    }
  };

  // Move document handler
  const handleMoveDocument = async (e) => {
    e?.preventDefault();
    if (!movingDoc || !moveDocTargetFolderId) return;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['X-Organization-Id'] = orgId;

      const res = await fetch(`/v1/documents/${movingDoc.id}/move`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ destination_folder_id: moveDocTargetFolderId })
      });

      if (res.ok) {
        showToast?.(`Document moved successfully.`);
        setShowMoveDocModal(false);
        setMovingDoc(null);
        await fetchData();
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Failed to move document', 'error');
      }
    } catch (err) {
      showToast?.('Error moving document: ' + err.message, 'error');
    }
  };

  // Upload document handler
  const handleUploadDocument = async (e) => {
    e?.preventDefault();
    if (!uploadFile) {
      showToast?.('Please select a file to upload.', 'error');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('organization_id', orgId);
      if (uploadFolderId) formData.append('folder_id', uploadFolderId);
      formData.append('document_type', uploadDocType);

      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`/v1/documents/upload-and-extract`, {
        method: 'POST',
        headers,
        body: formData
      });

      if (res.ok) {
        const result = await res.json();
        showToast?.(`Uploaded & extracted '${uploadFile.name}' successfully.`);
        setShowUploadModal(false);
        setUploadFile(null);
        await fetchData();
        if (result.document?.id) {
          setSelectedDocId(result.document.id);
        }
        onClaimExtracted?.();
        onDocumentUploaded?.(result);
      } else {
        const err = await res.json();
        showToast?.(err.detail || 'Upload failed', 'error');
      }
    } catch (err) {
      showToast?.('Error uploading file: ' + err.message, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  // Copy helper
  const handleCopy = (text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
    showToast?.('Copied to clipboard');
  };

  // Render an inline editable row for creating a new folder (Drive / OS style)
  const renderInlineCreateRow = (depth = 0) => (
    <div
      key="inline-new-folder-row"
      onClick={e => e.stopPropagation()}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '5px 8px',
        paddingLeft: `${depth * 16 + 8}px`,
        borderRadius: '4px',
        background: '#FFFFFF',
        gap: '6px'
      }}
    >
      {/* Spacer matching chevron width */}
      <span style={{ width: 14, height: 14, display: 'inline-block', flexShrink: 0 }} />

      {/* Folder Icon */}
      <Folder size={15} style={{ color: '#3B82F6', flexShrink: 0 }} />

      {/* Inline Input Box */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '4px', minWidth: 0 }}>
        <input
          ref={inlineCreateInputRef}
          type="text"
          value={creatingFolderName}
          onChange={e => setCreatingFolderName(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {
              e.preventDefault();
              e.stopPropagation();
              commitInlineCreate(creatingFolderName);
            } else if (e.key === 'Escape') {
              e.preventDefault();
              e.stopPropagation();
              setCreatingInParentId(undefined);
            }
          }}
          onBlur={() => {
            commitInlineCreate(creatingFolderName);
          }}
          disabled={isSavingNewFolder}
          style={{
            flex: 1,
            height: '24px',
            padding: '1px 6px',
            fontSize: '0.80rem',
            fontFamily: 'inherit',
            fontWeight: 500,
            color: '#0F172A',
            background: '#FFFFFF',
            border: '1.5px solid #2563EB',
            borderRadius: '3px',
            outline: 'none',
            boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.20)',
            minWidth: '70px'
          }}
        />
        {isSavingNewFolder && (
          <RefreshCw size={11} className="spin" style={{ color: '#2563EB', flexShrink: 0 }} />
        )}
      </div>
    </div>
  );

  // Recursive Directory Tree Renderer: Renders folders AND files (No Numbers!)
  const renderDirectoryTree = (nodes, depth = 0) => {
    const q = searchQuery.toLowerCase().trim();

    return nodes.map(node => {
      const isExpanded = expandedFolders.has(node.id);
      const isFolderActive = activeFolderId === node.id;
      const isFolderLoading = loadingFolderIds.has(node.id);
      const childFolders = node.children || [];

      // Get files belonging to this folder (or inbox if system inbox)
      const folderFiles = (docsByFolder[node.id] || []).concat(
        node.is_system ? (docsByFolder['unassigned'] || []) : []
      );

      // Deduplicate files by id
      const uniqueFiles = Array.from(new Map(folderFiles.map(f => [f.id, f])).values());
      const hasContent = childFolders.length > 0 || uniqueFiles.length > 0 || creatingInParentId === node.id;

      // Filter check
      if (q && !node.name.toLowerCase().includes(q) && !uniqueFiles.some(f => f.title.toLowerCase().includes(q))) {
        return null;
      }

      return (
        <div key={node.id} style={{ display: 'flex', flexDirection: 'column' }}>
          {/* FOLDER ROW */}
          <div
            onClick={(e) => {
              if (renamingFolderId === node.id) return;
              handleFolderClick(node, e);
            }}
            onContextMenu={(e) => {
              if (renamingFolderId === node.id) return;
              openContextMenu(e, 'folder', node);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '5px 8px',
              paddingLeft: `${depth * 16 + 8}px`,
              borderRadius: '4px',
              cursor: 'pointer',
              userSelect: 'none',
              background: isFolderActive ? 'rgba(37, 99, 235, 0.08)' : 'transparent',
              color: isFolderActive ? '#1E40AF' : 'var(--text-main)',
              fontWeight: isFolderActive ? 600 : 500,
              fontSize: '0.80rem',
              transition: 'background 0.1s ease',
              gap: '6px'
            }}
            onMouseEnter={e => {
              if (!isFolderActive) e.currentTarget.style.background = '#F8FAFC';
            }}
            onMouseLeave={e => {
              if (!isFolderActive) e.currentTarget.style.background = 'transparent';
            }}
          >
            {/* Expand / Collapse Chevron OR Folder-specific Loading Spinner */}
            <span
              style={{
                width: 14,
                height: 14,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              {isFolderLoading ? (
                <RefreshCw size={12} className="spin" style={{ color: '#2563EB' }} />
              ) : (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFolderClick(node, e);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    color: isExpanded ? '#2563EB' : '#64748B',
                    width: 14
                  }}
                  title={isExpanded ? 'Collapse folder' : 'Expand folder to view files'}
                >
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
              )}
            </span>

            {/* Folder Icon (Customized per folder type/domain) */}
            {renderFolderIcon(node, 15)}

            {/* Folder Name OR Inline Rename Input (Just like Drive / Windows Explorer) */}
            {renamingFolderId === node.id ? (
              <div
                onClick={e => e.stopPropagation()}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  minWidth: 0
                }}
              >
                <input
                  ref={inlineRenameInputRef}
                  type="text"
                  value={renameInputVal}
                  onChange={e => setRenameInputVal(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      e.stopPropagation();
                      commitInlineRename(node.id, renameInputVal);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      e.stopPropagation();
                      setRenamingFolderId(null);
                    }
                  }}
                  onBlur={() => {
                    commitInlineRename(node.id, renameInputVal);
                  }}
                  disabled={isSavingRename}
                  style={{
                    flex: 1,
                    height: '24px',
                    padding: '1px 6px',
                    fontSize: '0.80rem',
                    fontFamily: 'inherit',
                    fontWeight: 500,
                    color: '#0F172A',
                    background: '#FFFFFF',
                    border: '1.5px solid #2563EB',
                    borderRadius: '3px',
                    outline: 'none',
                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.20)',
                    minWidth: '60px'
                  }}
                />
                {isSavingRename && (
                  <RefreshCw size={11} className="spin" style={{ color: '#2563EB', flexShrink: 0 }} />
                )}
              </div>
            ) : (
              <span
                style={{
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  flex: 1
                }}
                title={node.name}
              >
                {node.name}
              </span>
            )}

            {/* Folder-specific loading spinner at right side of this folder row */}
            {isFolderLoading && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  color: '#2563EB',
                  marginLeft: 'auto',
                  flexShrink: 0
                }}
              >
                <RefreshCw size={11} className="spin" />
              </span>
            )}
          </div>

          {/* SUBFOLDERS AND FILES LISTING (Visible when folder is expanded) */}
          {(isExpanded || creatingInParentId === node.id) && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {/* Inline new folder creation row if creating inside this folder */}
              {creatingInParentId === node.id && renderInlineCreateRow(depth + 1)}

              {/* 1. Child Subfolders */}
              {childFolders.length > 0 && renderDirectoryTree(childFolders, depth + 1)}

              {/* 2. Files directly inside this folder */}
              {uniqueFiles.map(file => {
                const isSelected = selectedDocId === file.id;

                return (
                  <div
                    key={file.id}
                    onClick={() => {
                      setSelectedDocId(file.id);
                      setActiveFolderId(node.id);
                    }}
                    onDoubleClick={() => onInspectDocument?.(file)}
                    onContextMenu={(e) => openContextMenu(e, 'document', file)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '5px 8px',
                      paddingLeft: `${(depth + 1) * 16 + 8}px`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      background: isSelected ? '#EFF6FF' : 'transparent',
                      color: isSelected ? '#1E40AF' : 'var(--text-secondary)',
                      fontWeight: isSelected ? 600 : 400,
                      fontSize: '0.78rem',
                      gap: '7px',
                      transition: 'background 0.1s ease',
                      borderLeft: isSelected ? '2px solid #2563EB' : '2px solid transparent'
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = '#F8FAFC';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <FileText
                      size={14}
                      style={{
                        color: isSelected ? '#2563EB' : '#94A3B8',
                        flexShrink: 0
                      }}
                    />
                    <span
                      style={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        flex: 1
                      }}
                      title={file.title}
                    >
                      {file.title}
                    </span>
                  </div>
                );
              })}

              {/* 3. Empty folder notice if expanded and no contents */}
              {childFolders.length === 0 && uniqueFiles.length === 0 && !isFolderLoading && creatingInParentId !== node.id && (
                <div
                  style={{
                    padding: '3px 8px',
                    paddingLeft: `${(depth + 1) * 16 + 8}px`,
                    fontSize: '0.74rem',
                    color: '#94A3B8',
                    fontStyle: 'italic'
                  }}
                >
                  Empty folder
                </div>
              )}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: 0,
        width: '100%',
        maxWidth: '100%',
        minHeight: 0,
        height: '100%',
        flex: 1,
        background: '#FFFFFF',
        borderRadius: 0,
        border: '1px solid var(--border-subtle, #E2E8F0)',
        borderLeft: 'none',
        borderRight: 'none',
        borderBottom: 'none',
        overflow: 'hidden',
        boxShadow: 'none',
        alignItems: 'stretch',
        boxSizing: 'border-box'
      }}
    >
      
      {/* ── LEFT PANE: DIRECTORY TREE (FOLDERS & FILES) ── */}
      <div
        ref={directoryContainerRef}
        onContextMenu={(e) => {
          if (e.target === directoryContainerRef.current || e.target.classList.contains('tree-blank-area')) {
            openContextMenu(e, 'canvas', activeFolder);
          }
        }}
        style={{
          width: '260px',
          minWidth: '220px',
          maxWidth: '280px',
          flexShrink: 0,
          background: '#FFFFFF',
          borderRadius: 0,
          borderRight: '1px solid var(--border-subtle, #E2E8F0)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          boxSizing: 'border-box'
        }}
      >
        {/* Directory Top Bar */}
        <div
          style={{
            padding: '8px 12px',
            borderBottom: '1px solid var(--border-subtle, #E2E8F0)',
            background: '#faf8f5',
            borderRadius: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            flexShrink: 0
          }}
        >
          {/* Header Title + Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Directory
              </span>
              <span
                title="Tip: Right-click any folder or file for options (rename, move, delete, upload)"
                style={{ display: 'inline-flex', alignItems: 'center', cursor: 'help' }}
              >
                <Info size={13} style={{ color: '#94A3B8' }} />
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {readOnly && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    padding: '2px 8px',
                    borderRadius: 0,
                    background: '#F1F5F9',
                    color: '#64748B',
                    fontWeight: 600,
                    letterSpacing: '0.3px',
                    border: '1px solid #E2E8F0',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="Vault is read-only. File and folder management is enabled in Document Explorer."
                >
                  <ShieldCheck size={11} style={{ color: '#10B981' }} />
                  Read-Only
                </span>
              )}

              {/* + New Root Folder Action */}
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => startInlineCreate(null)}
                  style={{
                    background: '#F8FAFC',
                    border: '1px solid #CBD5E1',
                    borderRadius: 0,
                    cursor: 'pointer',
                    color: '#2563EB',
                    padding: '2px 6px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    fontSize: '0.70rem',
                    fontWeight: 600,
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#EFF6FF'; e.currentTarget.style.borderColor = '#93C5FD'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = '#F8FAFC'; e.currentTarget.style.borderColor = '#CBD5E1'; }}
                  title="Create New Root Folder (or right-click canvas)"
                >
                  <FolderPlus size={13} />
                  <span>+ Root</span>
                </button>
              )}

              {/* Refresh */}
              <button
                type="button"
                onClick={() => fetchData(true)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: '3px' }}
                title="Refresh Directory"
              >
                <RefreshCw size={13} className={isRefreshing ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Search Filter input */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={13} style={{ position: 'absolute', left: '8px', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Filter files... (right-click for options)"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '4px 8px 4px 26px',
                fontSize: '0.76rem',
                borderRadius: 0,
                
                background: '#FFFFFF'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '6px', background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: 0 }}
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Directory Items List (Scrollable Tree) */}
        <div
          className="tree-blank-area"
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            padding: '6px 2px 24px 2px',
            background: '#faf8f5',
            boxSizing: 'border-box'
          }}
        >
          {initialLoading && folderTree.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', fontSize: '0.78rem' }}>
              <RefreshCw size={15} className="spin" style={{ margin: '0 auto 6px auto', display: 'block' }} />
              Loading directory...
            </div>
          ) : (
            <>
              {creatingInParentId === null && renderInlineCreateRow(0)}
              {folderTree.length === 0 && creatingInParentId !== null ? (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', fontSize: '0.78rem' }}>
                  No folders found.
                </div>
              ) : (
                renderDirectoryTree(folderTree)
              )}
            </>
          )}
        </div>
      </div>

      {/* ── RIGHT PANE: LIVE DOCUMENT PREVIEW & WORKSPACE ── */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          maxWidth: '100%',
          overflowX: 'hidden',
          background: '#FFFFFF',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          boxSizing: 'border-box'
        }}
      >
        {selectedDocDetails ? (() => {
          const claimsList = selectedDocArtifacts?.claims || [];
          const conflictsList = selectedDocArtifacts?.conflicts || [];
          const verifiedCount = claimsList.filter(c => (c.status || '').toLowerCase() === 'verified' || (c.status || '').toLowerCase() === 'active').length;
          const candidateCount = claimsList.filter(c => {
            const st = (c.status || '').toLowerCase();
            return st === 'candidate' || st === 'review' || st === 'pending' || !st;
          }).length;
          const trustPercent = conflictsList.length === 0 ? 98 : Math.max(72, 98 - (conflictsList.length * 4));
          const filteredDocClaims = claimsList.filter(c => {
            const st = (c.status || 'candidate').toLowerCase();
            if (claimTriageFilter === 'candidate' && st !== 'candidate' && st !== 'review' && st !== 'pending' && st !== '') return false;
            if (claimTriageFilter === 'verified' && st !== 'verified' && st !== 'active') return false;
            if (!claimSearchQuery.trim()) return true;
            const q = claimSearchQuery.toLowerCase();
            return (
              (c.claim_text || '').toLowerCase().includes(q) ||
              (c.subject || '').toLowerCase().includes(q) ||
              (c.predicate || '').toLowerCase().includes(q) ||
              (c.object || '').toLowerCase().includes(q)
            );
          });
          const activeClaimObj = claimsList.find(c => c.id === selectedClaimId) || (filteredDocClaims.length > 0 ? filteredDocClaims[0] : (claimsList.length > 0 ? claimsList[0] : null));

          const rawReaderContent = (() => {
            if (!selectedDocDetails) return '';
            if (selectedDocDetails.content_uri && selectedDocDetails.content_uri.trim().length > 0) {
              return selectedDocDetails.content_uri;
            }
            const verUri = selectedDocDetails.versions?.[0]?.content_uri;
            if (verUri && verUri.trim().length > 0) {
              return verUri;
            }
            if (claimsList.length > 0) {
              const quotes = claimsList
                .map((c, i) => `${i + 1}. [${c.subject || 'Rule'}] ${c.claim_text || ''}${c.evidence?.[0]?.text_span ? `\n   Quote: "${c.evidence[0].text_span}"` : ''}`)
                .filter(l => l.trim().length > 0);
              if (quotes.length > 0) {
                return `## Extracted Atomic Policy Rules & Verified Assertions\n\n${quotes.join('\n\n')}`;
              }
            }
            return '';
          })();

          return (
            <>
              {/* Full Document Content & Ingestion Preview (Seamless white surface, edge-to-edge) */}
              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflowY: 'auto',
                  overflowX: 'hidden',
                  background: '#FFFFFF',
                  padding: '14px 24px 20px 24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  boxSizing: 'border-box'
                }}
              >
                {loadingPreview ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', fontSize: '0.80rem' }}>
                    <RefreshCw size={18} className="spin" style={{ margin: '0 auto 8px auto', display: 'block', color: '#2563EB' }} />
                    <span>Loading policy document preview...</span>
                  </div>
                ) : (
                  <div style={{ minHeight: '80px' }}>
                    {rawReaderContent ? (
                      renderFormattedMarkdown(rawReaderContent)
                    ) : (
                      <div style={{ padding: '20px 10px', textAlign: 'center', color: '#94A3B8', fontSize: '0.80rem' }}>
                        No text content available for this document.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom Metadata & Navigation Bridges to Curator and Vault */}
              <div
                style={{
                  padding: '8px 16px',
                  borderTop: '1px solid #E2E8F0',
                  background: '#FFFFFF',
                  borderRadius: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.74rem',
                  gap: '10px',
                  flexWrap: 'wrap',
                  flexShrink: 0,
                  minHeight: '40px',
                  boxSizing: 'border-box'
                }}
              >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '0.68rem',
                        padding: '2px 8px',
                        borderRadius: 0,
                        background: '#F0FDF4',
                        color: '#15803D',
                        border: '1px solid #BBF7D0',
                        fontWeight: 700
                      }}
                    >
                      {claimsList.length} Extracted Claim{claimsList.length === 1 ? '' : 's'}
                    </span>
                    <span style={{ color: '#64748B' }}>
                      Hash: <code style={{ fontSize: '0.70rem', background: '#F1F5F9', padding: '1px 4px', borderRadius: 0 }}>{selectedDocDetails.content_hash?.substring(0, 10)}...</code>
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(selectedDocDetails.content_hash)}
                      style={{ background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', padding: 0, display: 'inline-flex', alignItems: 'center' }}
                      title="Copy SHA-256 hash"
                    >
                      {copiedHash ? <Check size={13} style={{ color: '#16A34A' }} /> : <Copy size={13} />}
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {/* Bridge 1: Curator Approvals */}
                    <button
                      type="button"
                      onClick={() => {
                        if (onNavigateToCuratorApprovals) {
                          onNavigateToCuratorApprovals(selectedDocDetails.id);
                        } else {
                          window.location.href = `/curator/approvals?doc=${selectedDocDetails.id}`;
                        }
                      }}
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: candidateCount > 0 ? '#FEF3C7' : '#F1F5F9',
                        border: `1px solid ${candidateCount > 0 ? '#FDE68A' : '#CBD5E1'}`,
                        borderRadius: 0,
                        cursor: 'pointer',
                        color: candidateCount > 0 ? '#B45309' : '#475569',
                        fontWeight: 700,
                        transition: 'all 0.15s ease'
                      }}
                      title="Open Candidate Claim Approvals in Context Curator"
                    >
                      <ShieldCheck size={13} style={{ color: candidateCount > 0 ? '#D97706' : '#64748B' }} />
                      <span>{candidateCount > 0 ? `Review ${candidateCount} Candidates in Curator ➔` : 'Approvals in Curator ➔'}</span>
                    </button>

                    {/* Bridge 2: 360 Lineage in Vault */}
                    <button
                      type="button"
                      onClick={() => {
                        if (onViewClaims) {
                          onViewClaims(selectedDocDetails, 'summary');
                        } else {
                          window.location.href = `/vault?doc=${selectedDocDetails.id}`;
                        }
                      }}
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: 'linear-gradient(135deg, #EA580C 0%, #F97316 100%)',
                        border: 'none',
                        color: '#FFFFFF',
                        borderRadius: 0,
                        cursor: 'pointer',
                        fontWeight: 700,
                        transition: 'all 0.15s ease'
                      }}
                      title="Inspect full 360° Lineage DAG & Evidence in Context Vault"
                    >
                      <Sparkles size={12} />
                      <span>View 360° in Vault ↗</span>
                    </button>
                  </div>
                </div>

            </>
          );
        })() : (
          /* INDUSTRIAL FOLDER WORKSPACE & BREADCRUMB NAVIGATION */
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              background: '#FFFFFF',
              overflowY: 'auto',
              minHeight: 0,
              boxSizing: 'border-box'
            }}
          >
            {/* 1. TOP BREADCRUMB BAR */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                borderBottom: '1px solid var(--border-subtle, #E2E8F0)',
                background: '#FFFFFF',
                flexWrap: 'wrap',
                gap: '8px'
              }}
            >
              {/* Interactive Clickable Breadcrumb Trail */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {breadcrumbs.map((crumb, idx) => {
                  const isLast = idx === breadcrumbs.length - 1;
                  return (
                    <React.Fragment key={crumb.id || 'root'}>
                      {idx > 0 && <ChevronRight size={12} style={{ color: '#94A3B8' }} />}
                      <span
                        onClick={() => {
                          setActiveFolderId(crumb.id);
                          setSelectedDocId(null);
                        }}
                        style={{
                          cursor: isLast ? 'default' : 'pointer',
                          fontWeight: isLast ? 700 : 500,
                          color: isLast ? 'var(--text-main)' : '#0284C7',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={e => {
                          if (!isLast) e.currentTarget.style.background = '#F8FAFC';
                        }}
                        onMouseLeave={e => {
                          if (!isLast) e.currentTarget.style.background = 'transparent';
                        }}
                        title={isLast ? 'Current folder' : `Jump to ${crumb.name}`}
                      >
                        {crumb.name}
                      </span>
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Action Toolbar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  onClick={handleAutoOrganize}
                  disabled={isAutoOrganizing}
                  className="btn btn-secondary"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    background: '#FFFFFF',
                    border: '1px solid #CBD5E1',
                    borderRadius: '6px',
                    cursor: isAutoOrganizing ? 'not-allowed' : 'pointer',
                    color: '#D97706'
                  }}
                  title="Automatically organize all unclassified files into domain & connector folders"
                >
                  <Sparkles size={13} className={isAutoOrganizing ? 'spin' : ''} style={{ color: '#F59E0B' }} />
                  <span>{isAutoOrganizing ? 'Filing...' : 'Auto-Organize'}</span>
                </button>
              </div>
            </div>

            {/* 4. DOCUMENTS TABLE SECTION */}
            <div style={{ padding: '16px 20px', flex: 1 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.04em' }}>
                Documents ({currentFolderDocs.length})
              </div>

              {currentFolderDocs.length === 0 ? (
                <div
                  style={{
                    padding: '36px 20px',
                    textAlign: 'center',
                    background: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px dashed var(--border-subtle)',
                    color: 'var(--text-muted)'
                  }}
                >
                  <FileText size={28} style={{ color: '#CBD5E1', marginBottom: '8px' }} />
                  <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                    No documents in this folder
                  </div>
                  <div style={{ fontSize: '0.74rem', maxWidth: '320px', margin: '0 auto 12px auto' }}>
                    Upload a policy document, connect an integration, or click Auto-Organize to file unclassified documents.
                  </div>
                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => {
                        setUploadFolderId(activeFolderId);
                        setShowUploadModal(true);
                      }}
                      className="btn btn-primary"
                      style={{ padding: '5px 14px', fontSize: '0.74rem' }}
                    >
                      Upload to this folder
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ overflowX: 'auto', background: '#FFFFFF', borderRadius: '8px', border: '1px solid var(--border-subtle, #E2E8F0)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.76rem' }}>
                    <thead>
                      <tr style={{ background: '#F8FAFC', borderBottom: '1px solid var(--border-subtle, #E2E8F0)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Document</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Origin Source</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Domain</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Claims</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600 }}>Trust Status</th>
                        <th style={{ padding: '8px 12px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentFolderDocs.map(doc => (
                        <tr
                          key={doc.id}
                          style={{ borderBottom: '1px solid #F1F5F9', transition: 'background 0.1s ease' }}
                          onMouseEnter={e => e.currentTarget.style.background = '#F8FAFC'}
                          onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        >
                          <td style={{ padding: '8px 12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <FileText size={14} style={{ color: '#0284C7', flexShrink: 0 }} />
                              <div style={{ minWidth: 0 }}>
                                <div
                                  onClick={() => setSelectedDocId(doc.id)}
                                  style={{ fontWeight: 600, color: 'var(--text-main)', cursor: 'pointer', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '280px' }}
                                  title={doc.title}
                                >
                                  {doc.title}
                                </div>
                                <div style={{ fontSize: '0.66rem', color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>
                                  {doc.content_hash ? `sha256:${doc.content_hash.slice(0, 8)}...` : 'hash pending'}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            {renderSourceBadge(doc)}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#F1F5F9', color: '#475569', fontWeight: 600 }}>
                              {doc.domain || 'General'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#EFF6FF', color: '#1D4ED8', fontWeight: 700 }}>
                              {doc.claims_count !== undefined ? `${doc.claims_count} Claims` : (doc.id === selectedDocId && selectedDocArtifacts?.claims ? `${selectedDocArtifacts.claims.length} Claims` : 'Claims ready')}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#F0FDF4', color: '#166534', fontWeight: 600 }}>
                              <CheckCircle2 size={11} style={{ color: '#16A34A' }} /> Verified
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                              <button
                                type="button"
                                onClick={() => setSelectedDocId(doc.id)}
                                className="btn btn-secondary"
                                style={{ padding: '2px 8px', fontSize: '0.70rem', background: '#FFFFFF', border: '1px solid #CBD5E1', cursor: 'pointer' }}
                                title="Inspect live content & extracted claims"
                              >
                                Preview
                              </button>
                              {!readOnly && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMovingDoc(doc);
                                    setMoveDocTargetFolderId(doc.folder_id || '');
                                    setShowMoveDocModal(true);
                                  }}
                                  className="btn btn-secondary"
                                  style={{ padding: '2px 6px', fontSize: '0.70rem', background: '#FFFFFF', border: '1px solid #CBD5E1', cursor: 'pointer' }}
                                  title="Move to another folder"
                                >
                                  <Move size={11} />
                                </button>
                              )}
                              {!readOnly && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteDocument(doc);
                                  }}
                                  className="btn btn-secondary"
                                  style={{ padding: '2px 6px', fontSize: '0.70rem', background: '#FEF2F2', border: '1px solid #FECACA', color: '#DC2626', cursor: 'pointer' }}
                                  title="Delete document"
                                >
                                  <Trash2 size={11} style={{ color: '#DC2626' }} />
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
            </div>
          </div>
        )}
      </div>

      {/* ── CONTEXT MENU (RIGHT-CLICK) ── */}
      {contextMenu.visible && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'fixed',
            top: contextMenu.y,
            left: contextMenu.x,
            zIndex: 9999,
            minWidth: '180px',
            background: '#FFFFFF',
            borderRadius: '6px',
            border: '1px solid #CBD5E1',
            boxShadow: '0 6px 18px rgba(0,0,0,0.12), 0 2px 4px rgba(0,0,0,0.06)',
            padding: '4px',
            display: 'flex',
            flexDirection: 'column',
            gap: '1px'
          }}
        >
          {/* Header */}
          <div style={{ padding: '5px 8px', fontSize: '0.68rem', fontWeight: 700, color: '#64748B', borderBottom: '1px solid #F1F5F9', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {contextMenu.type === 'folder' ? `Folder: ${contextMenu.target?.name || ''}`
              : contextMenu.type === 'document' ? `File: ${contextMenu.target?.title || ''}`
              : 'Directory Options'}
          </div>

          {/* FOLDER OPTIONS */}
          {contextMenu.type === 'folder' && (
            <>
              {!readOnly && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      startInlineCreate(contextMenu.target.id);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <FolderPlus size={13} style={{ color: '#2563EB' }} />
                    <span>New subfolder</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUploadFolderId(contextMenu.target.id);
                      setShowUploadModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Upload size={13} style={{ color: '#16A34A' }} />
                    <span>Upload file here...</span>
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => {
                  fetchFolderMetrics(contextMenu.target.id);
                  setShowInsightsModal(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <BarChart2 size={13} style={{ color: '#7E22CE' }} />
                <span>Folder insights</span>
              </button>

              {!readOnly && !contextMenu.target?.is_system && (
                <>
                  <div style={{ height: '1px', background: '#F1F5F9', margin: '2px 0' }} />

                  <button
                    type="button"
                    onClick={() => {
                      const target = contextMenu.target;
                      setRenamingFolderId(target.id);
                      setRenameInputVal(target.name);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Edit3 size={13} />
                    <span>Rename</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setMovingFolder(contextMenu.target);
                      setMoveFolderTargetId(contextMenu.target.parent_id || 'root');
                      setShowMoveFolderModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Move size={13} />
                    <span>Move...</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      handleDeleteFolder(contextMenu.target);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#DC2626' }}
                  >
                    <Trash2 size={13} />
                    <span>Delete</span>
                  </button>
                </>
              )}
            </>
          )}

          {/* DOCUMENT OPTIONS */}
          {contextMenu.type === 'document' && (
            <>
              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('preview');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Eye size={13} style={{ color: '#2563EB' }} />
                <span>Open File Preview</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  window.open(`/v1/documents/${contextMenu.target.id}/file`, '_blank');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#0284C7' }}
              >
                <ExternalLink size={13} style={{ color: '#0284C7' }} />
                <span>Open File in New Tab ↗</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setIsFullFileReaderOpen(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <BookOpen size={13} style={{ color: '#0F172A' }} />
                <span>Full Document Reader</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('description');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Info size={13} style={{ color: '#64748B' }} />
                <span>Description & Specifications</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('claims');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Search size={13} style={{ color: '#7E22CE' }} />
                <span>Claim Selecting Across Document</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSelectedDocId(contextMenu.target.id);
                  setActiveFacilityTab('lineage');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <Network size={13} style={{ color: '#16A34A' }} />
                <span>Document-Wise Lineage DAG</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  onViewClaims?.(contextMenu.target, 'summary');
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#EA580C', fontWeight: 700 }}
              >
                <Sparkles size={13} style={{ color: '#EA580C' }} />
                <span>Open 360° Studio ↗</span>
              </button>

              <div style={{ height: '1px', background: '#F1F5F9', margin: '2px 0' }} />

              {!readOnly && (
                <button
                  type="button"
                  onClick={() => {
                    setMovingDoc(contextMenu.target);
                    setMoveDocTargetFolderId(contextMenu.target.folder_id || activeFolderId);
                    setShowMoveDocModal(true);
                    setContextMenu(prev => ({ ...prev, visible: false }));
                  }}
                  className="context-menu-item"
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                >
                  <Move size={13} style={{ color: '#2563EB' }} />
                  <span>Move to...</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  handleCopy(contextMenu.target.content_hash);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-muted)' }}
              >
                <Copy size={13} />
                <span>Copy SHA-256</span>
              </button>

              {!readOnly && (
                <button
                  type="button"
                  onClick={() => {
                    handleDeleteDocument(contextMenu.target);
                    setContextMenu(prev => ({ ...prev, visible: false }));
                  }}
                  className="context-menu-item"
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: '#DC2626' }}
                >
                  <Trash2 size={13} />
                  <span>Delete</span>
                </button>
              )}
            </>
          )}

          {/* CANVAS EMPTY SPACE OPTIONS */}
          {contextMenu.type === 'canvas' && (
            <>
              {!readOnly && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      startInlineCreate(activeFolderId || null);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <FolderPlus size={13} style={{ color: '#3B82F6' }} />
                    <span>New folder</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUploadFolderId(activeFolderId);
                      setShowUploadModal(true);
                      setContextMenu(prev => ({ ...prev, visible: false }));
                    }}
                    className="context-menu-item"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
                  >
                    <Upload size={13} style={{ color: '#16A34A' }} />
                    <span>Upload file here</span>
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => {
                  fetchData(true);
                  setContextMenu(prev => ({ ...prev, visible: false }));
                }}
                className="context-menu-item"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', fontSize: '0.76rem', border: 'none', background: 'none', borderRadius: '4px', cursor: 'pointer', textAlign: 'left', color: 'var(--text-main)' }}
              >
                <RefreshCw size={13} />
                <span>Refresh directory</span>
              </button>
            </>
          )}
        </div>
      )}

      {/* ── MODAL: FOLDER INSIGHTS ── */}
      {showInsightsModal && (
        <div className="modal-backdrop" onClick={() => setShowInsightsModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '520px', padding: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BarChart2 size={16} style={{ color: '#2563EB' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
                  Folder Insights: {activeFolder?.name || 'Vault Root'}
                </h3>
              </div>
              <button type="button" onClick={() => setShowInsightsModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '14px' }}>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Total Documents</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '2px' }}>{metrics?.documents?.total ?? allDocuments.length}</div>
              </div>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#F0FDF4', border: '1px solid #DCFCE7' }}>
                <div style={{ fontSize: '0.68rem', color: '#166534' }}>Completed</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#15803D', marginTop: '2px' }}>{metrics?.documents?.by_processing_state?.completed ?? 0}</div>
              </div>
              <div style={{ padding: '8px 10px', borderRadius: '6px', background: '#FEF2F2', border: '1px solid #FEE2E2' }}>
                <div style={{ fontSize: '0.68rem', color: '#991B1B' }}>Failures</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#B91C1C', marginTop: '2px' }}>{metrics?.documents?.by_processing_state?.failed ?? 0}</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="button" onClick={() => setShowInsightsModal(false)} className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}





      {/* ── MODAL: MOVE FOLDER ── */}
      {showMoveFolderModal && movingFolder && (
        <div className="modal-backdrop" onClick={() => setShowMoveFolderModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Move size={16} style={{ color: '#3B82F6' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Move '{movingFolder.name}'</h3>
              </div>
              <button type="button" onClick={() => setShowMoveFolderModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <form onSubmit={handleMoveFolder}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Destination</label>
                <select
                  value={moveFolderTargetId}
                  onChange={e => setMoveFolderTargetId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  <option value="root">-- Vault Root --</option>
                  {folders
                    .filter(f => f.id !== movingFolder.id && !f.is_system)
                    .map(f => (
                      <option key={f.id} value={f.id}>
                        {'- '.repeat(f.depth)} {f.name}
                      </option>
                    ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button type="button" onClick={() => setShowMoveFolderModal(false)} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.76rem' }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                  Move
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: MOVE DOCUMENT ── */}
      {showMoveDocModal && movingDoc && (
        <div className="modal-backdrop" onClick={() => setShowMoveDocModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Move size={16} style={{ color: '#3B82F6' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Move Document</h3>
              </div>
              <button type="button" onClick={() => setShowMoveDocModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Moving: <strong>{movingDoc.title}</strong>
            </div>

            <form onSubmit={handleMoveDocument}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Destination Folder</label>
                <select
                  value={moveDocTargetFolderId}
                  onChange={e => setMoveDocTargetFolderId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                  required
                >
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.is_system ? '📥 ' : '- '.repeat(f.depth) + '📁 '} {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button type="button" onClick={() => setShowMoveDocModal(false)} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.76rem' }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ padding: '5px 14px', fontSize: '0.76rem' }}>
                  Move
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: UPLOAD FILE ── */}
      {showUploadModal && (
        <div className="modal-backdrop" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '420px', padding: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Upload size={16} style={{ color: '#2563EB' }} />
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Upload Document</h3>
              </div>
              <button type="button" onClick={() => setShowUploadModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>

            <form onSubmit={handleUploadDocument}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Folder</label>
                <select
                  value={uploadFolderId || ''}
                  onChange={e => setUploadFolderId(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.is_system ? '📥 ' : '- '.repeat(f.depth) + '📁 '} {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>Classification</label>
                <select
                  value={uploadDocType}
                  onChange={e => setUploadDocType(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.78rem', borderRadius: '5px', border: '1px solid #CBD5E1' }}
                >
                  <option value="policy">Governance Policy</option>
                  <option value="contract">Legal Agreement / Contract</option>
                  <option value="sla">SLA & Terms</option>
                  <option value="compliance">Compliance Guideline</option>
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, marginBottom: '5px' }}>File (.md, .txt, .pdf, .docx)</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.txt,.md,.json,.csv"
                  onChange={e => setUploadFile(e.target.files?.[0] || null)}
                  style={{ width: '100%', padding: '6px', fontSize: '0.78rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="btn btn-secondary"
                  disabled={isUploading}
                  style={{ padding: '5px 12px', fontSize: '0.76rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isUploading || !uploadFile}
                  style={{ padding: '5px 14px', fontSize: '0.76rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  {isUploading ? (
                    <>
                      <RefreshCw size={13} className="spin" />
                      <span>Ingesting...</span>
                    </>
                  ) : (
                    <>
                      <Upload size={13} />
                      <span>Upload</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: FULL DOCUMENT READER ── */}
      {isFullFileReaderOpen && (() => {
        const modalClaims = selectedDocArtifacts?.claims || [];
        const readerContent = (() => {
          if (!selectedDocDetails) return '';
          if (selectedDocDetails.content_uri && selectedDocDetails.content_uri.trim().length > 0) {
            return selectedDocDetails.content_uri;
          }
          const verUri = selectedDocDetails.versions?.[0]?.content_uri;
          if (verUri && verUri.trim().length > 0) {
            return verUri;
          }
          if (modalClaims.length > 0) {
            const quotes = modalClaims
              .map((c, i) => `${i + 1}. [${c.subject || 'Rule'}] ${c.claim_text || ''}${c.evidence?.[0]?.text_span ? `\n   Quote: "${c.evidence[0].text_span}"` : ''}`)
              .filter(l => l.trim().length > 0);
            if (quotes.length > 0) {
              return `## Extracted Atomic Policy Rules & Verified Assertions\n\n${quotes.join('\n\n')}`;
            }
          }
          return '';
        })();

        const searchMatchesCount = (fullReaderSearch.trim() && readerContent)
          ? (readerContent.match(new RegExp(fullReaderSearch.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'), 'gi')) || []).length
          : 0;

        const handleCopyText = (text) => {
          if (!text) return;
          navigator.clipboard?.writeText(text);
          setCopiedReaderText(true);
          setTimeout(() => setCopiedReaderText(false), 2000);
          showToast?.('Document text copied to clipboard');
        };

        return (
          <div
            className="modal-backdrop"
            onClick={() => setIsFullFileReaderOpen(false)}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              width: '100vw',
              height: '100vh',
              background: 'rgba(15, 23, 42, 0.65)',
              backdropFilter: 'blur(5px)',
              WebkitBackdropFilter: 'blur(5px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px',
              boxSizing: 'border-box',
              zIndex: 99999
            }}
          >
            <div
              className="modal-content"
              onClick={e => e.stopPropagation()}
              style={{
                maxWidth: '920px',
                width: '100%',
                maxHeight: '90vh',
                height: '88vh',
                display: 'flex',
                flexDirection: 'column',
                padding: 0,
                overflow: 'hidden',
                borderRadius: '12px',
                background: '#FFFFFF',
                border: '1px solid #CBD5E1',
                boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.35)',
                boxSizing: 'border-box',
                margin: 'auto'
              }}
            >
              {/* Header: Clean, Uncluttered, No space-consuming filename */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 18px',
                  borderBottom: '1px solid #E2E8F0',
                  background: '#F8FAFC',
                  gap: '10px',
                  flexWrap: 'nowrap',
                  overflow: 'hidden',
                  flexShrink: 0
                }}
              >
                {/* Left: Compact Reader Icon & Label (File name removed to avoid overflow) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                  <div style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '6px',
                    background: '#EFF6FF',
                    border: '1px solid #BFDBFE',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#2563EB'
                  }}>
                    <BookOpen size={15} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.86rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
                      Document Reader
                    </span>
                    {selectedDocDetails?.document_type && (
                      <span style={{
                        fontSize: '0.62rem',
                        fontWeight: 800,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: '#EFF6FF',
                        color: '#2563EB',
                        border: '1px solid #DBEAFE',
                        textTransform: 'uppercase'
                      }}>
                        {selectedDocDetails.document_type}
                      </span>
                    )}
                  </div>
                </div>

                {/* Center: View Mode Toggle */}
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: '#E2E8F0',
                  padding: '3px',
                  borderRadius: '7px',
                  gap: '2px',
                  flexShrink: 0
                }}>
                  <button
                    type="button"
                    onClick={() => setReaderViewMode('text')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 11px',
                      fontSize: '0.73rem',
                      fontWeight: readerViewMode === 'text' ? 700 : 500,
                      borderRadius: '5px',
                      border: 'none',
                      background: readerViewMode === 'text' ? '#FFFFFF' : 'transparent',
                      color: readerViewMode === 'text' ? '#1D4ED8' : '#475569',
                      cursor: 'pointer',
                      boxShadow: readerViewMode === 'text' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <FileText size={13} style={{ color: readerViewMode === 'text' ? '#2563EB' : '#64748B' }} />
                    <span>Formatted Text</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setReaderViewMode('pdf')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 11px',
                      fontSize: '0.73rem',
                      fontWeight: readerViewMode === 'pdf' ? 700 : 500,
                      borderRadius: '5px',
                      border: 'none',
                      background: readerViewMode === 'pdf' ? '#FFFFFF' : 'transparent',
                      color: readerViewMode === 'pdf' ? '#1D4ED8' : '#475569',
                      cursor: 'pointer',
                      boxShadow: readerViewMode === 'pdf' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <ExternalLink size={13} style={{ color: readerViewMode === 'pdf' ? '#2563EB' : '#64748B' }} />
                    <span>Original File</span>
                  </button>
                </div>

                {/* Right: Search, Copy & ALWAYS-VISIBLE Close Button */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                  {readerViewMode === 'text' && (
                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                      <Search size={12} style={{ position: 'absolute', left: '7px', color: '#94A3B8' }} />
                      <input
                        type="text"
                        placeholder="Search text..."
                        value={fullReaderSearch}
                        onChange={e => setFullReaderSearch(e.target.value)}
                        style={{
                          padding: '4px 22px 4px 24px',
                          fontSize: '0.72rem',
                          borderRadius: '6px',
                          border: '1px solid #CBD5E1',
                          width: '120px',
                          outline: 'none',
                          background: '#FFFFFF'
                        }}
                      />
                      {fullReaderSearch && (
                        <button
                          type="button"
                          onClick={() => setFullReaderSearch('')}
                          style={{
                            position: 'absolute',
                            right: '5px',
                            border: 'none',
                            background: 'transparent',
                            color: '#94A3B8',
                            cursor: 'pointer',
                            padding: 0
                          }}
                        >
                          <X size={11} />
                        </button>
                      )}
                    </div>
                  )}

                  {fullReaderSearch.trim() && readerViewMode === 'text' && (
                    <span style={{ fontSize: '0.68rem', color: searchMatchesCount > 0 ? '#15803D' : '#DC2626', fontWeight: 700, whiteSpace: 'nowrap' }}>
                      {searchMatchesCount} {searchMatchesCount === 1 ? 'match' : 'matches'}
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={() => handleCopyText(readerContent || selectedDocDetails?.title || '')}
                    className="btn btn-secondary"
                    style={{
                      padding: '4px 9px',
                      fontSize: '0.72rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: '#FFFFFF',
                      border: '1px solid #CBD5E1',
                      borderRadius: '6px',
                      color: copiedReaderText ? '#16A34A' : '#1E293B',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                    title="Copy full document text"
                  >
                    {copiedReaderText ? <Check size={12} style={{ color: '#16A34A' }} /> : <Copy size={12} />}
                    <span>{copiedReaderText ? 'Copied' : 'Copy'}</span>
                  </button>

                  {/* PROMINENT CLOSE BUTTON - NEVER OVERFLOWS */}
                  <button
                    type="button"
                    onClick={() => setIsFullFileReaderOpen(false)}
                    style={{
                      width: '30px',
                      height: '30px',
                      borderRadius: '6px',
                      border: '1.5px solid #CBD5E1',
                      background: '#FFFFFF',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#0F172A',
                      flexShrink: 0,
                      marginLeft: '3px',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = '#FEE2E2'; e.currentTarget.style.color = '#DC2626'; e.currentTarget.style.borderColor = '#FCA5A5'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; e.currentTarget.style.color = '#0F172A'; e.currentTarget.style.borderColor = '#CBD5E1'; }}
                    title="Close Reader (Esc)"
                  >
                    <X size={16} strokeWidth={2.5} />
                  </button>
                </div>
              </div>

              {/* Reader Body */}
              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', background: readerViewMode === 'pdf' ? '#334155' : '#F8FAFC' }}>
                {loadingPreview || !selectedDocDetails ? (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', gap: '12px' }}>
                    <RefreshCw size={26} className="spin" style={{ color: '#2563EB' }} />
                    <span style={{ fontSize: '0.86rem', color: '#64748B', fontWeight: 600 }}>Loading document contents...</span>
                  </div>
                ) : readerViewMode === 'pdf' ? (
                  <div style={{ flex: 1, width: '100%', height: '100%', minHeight: '500px', display: 'flex' }}>
                    <iframe
                      src={`/v1/documents/${selectedDocDetails.id}/file`}
                      title={`${selectedDocDetails.title || 'Document'} PDF Viewer`}
                      style={{
                        width: '100%',
                        height: '100%',
                        minHeight: '500px',
                        border: 'none',
                        flex: 1
                      }}
                    />
                  </div>
                ) : (
                  <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
                    {readerContent ? (
                      <div
                        style={{
                          maxWidth: '820px',
                          margin: '0 auto',
                          background: '#FFFFFF',
                          padding: '32px 36px',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          boxShadow: '0 4px 16px -2px rgba(15, 23, 42, 0.06)',
                          fontSize: '0.88rem',
                          lineHeight: 1.7,
                          color: '#0F172A',
                          wordBreak: 'break-word',
                          fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                        }}
                      >
                        {/* Header Inside the Paper Sheet */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1.5px solid #F1F5F9', paddingBottom: '14px', marginBottom: '20px', gap: '16px' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                              <span style={{ fontSize: '0.64rem', fontWeight: 800, padding: '2px 7px', borderRadius: '4px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #DBEAFE', textTransform: 'uppercase' }}>
                                {selectedDocDetails.document_type || 'Policy'}
                              </span>
                              <span style={{ fontSize: '0.68rem', color: '#16A34A', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                                <CheckCircle2 size={12} /> Verified Ingestion
                              </span>
                              <span style={{ fontSize: '0.68rem', color: '#64748B' }}>
                                • v{selectedDocDetails.versions?.length || 1}.0
                              </span>
                            </div>
                            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', lineHeight: 1.3 }}>
                              {selectedDocDetails.title}
                            </h1>
                          </div>
                          <div style={{ textAlign: 'right', fontSize: '0.68rem', color: '#64748B', flexShrink: 0 }}>
                            <div style={{ fontWeight: 600, color: '#475569' }}>
                              {readerContent.split(/\s+/).filter(Boolean).length} words • ~{Math.max(1, Math.ceil(readerContent.split(/\s+/).filter(Boolean).length / 200))} min read
                            </div>
                            <div style={{ fontFamily: 'monospace', fontSize: '0.64rem', color: '#94A3B8', marginTop: '2px' }}>
                              SHA: {selectedDocDetails.content_hash?.substring(0, 10)}...
                            </div>
                          </div>
                        </div>

                        {fullReaderSearch.trim() ? (
                          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65, fontSize: '0.84rem', color: '#334155' }}>
                            {readerContent.split(new RegExp(`(${fullReaderSearch.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi')).map((part, i) =>
                              part.toLowerCase() === fullReaderSearch.toLowerCase() ? (
                                <mark key={i} style={{ background: '#FEF08A', color: '#854D0E', padding: '1px 4px', borderRadius: '3px', fontWeight: 700 }}>
                                  {part}
                                </mark>
                              ) : (
                                part
                              )
                            )}
                          </div>
                        ) : (
                          renderFormattedMarkdown(readerContent)
                        )}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '50px 20px', background: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', maxWidth: '520px', margin: '40px auto' }}>
                        <FileText size={38} style={{ color: '#0284C7', margin: '0 auto 12px auto', display: 'block' }} />
                        <div style={{ fontSize: '1rem', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>
                          Document Available as Original File
                        </div>
                        <p style={{ fontSize: '0.80rem', color: '#64748B', lineHeight: 1.5, marginBottom: '18px' }}>
                          This document was uploaded as a PDF file. Use the built-in PDF viewer to inspect the document in its native layout.
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                          <button
                            type="button"
                            onClick={() => setReaderViewMode('pdf')}
                            className="btn btn-primary"
                            style={{ padding: '6px 16px', fontSize: '0.80rem', background: '#2563EB', borderColor: '#2563EB', color: '#FFFFFF', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          >
                            <BookOpen size={14} />
                            <span>Switch to PDF Viewer</span>
                          </button>
                          <a
                            href={`/v1/documents/${selectedDocDetails.id}/file`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-secondary"
                            style={{ padding: '6px 14px', fontSize: '0.80rem', display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
                          >
                            <ExternalLink size={14} />
                            <span>Open in Tab ↗</span>
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 18px',
                  borderTop: '1px solid #CBD5E1',
                  background: '#FFFFFF',
                  fontSize: '0.74rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.68rem', fontWeight: 700 }}>
                    {modalClaims.length} Extracted Claims
                  </span>
                  <span style={{ color: '#64748B' }}>
                    Verified with SHA-256 Provenance
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setIsFullFileReaderOpen(false);
                      setActiveFacilityTab('claims');
                    }}
                    className="btn btn-secondary"
                    style={{ padding: '5px 12px', fontSize: '0.74rem', fontWeight: 600 }}
                  >
                    Select Claims ({modalClaims.length})
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIsFullFileReaderOpen(false);
                      onViewClaims?.(selectedDocDetails, 'summary');
                    }}
                    className="btn btn-primary"
                    style={{ padding: '5px 14px', fontSize: '0.74rem', background: '#EA580C', borderColor: '#EA580C', color: '#FFFFFF', fontWeight: 700 }}
                  >
                    <Sparkles size={13} style={{ marginRight: '5px', display: 'inline' }} />
                    <span>Open 360° Studio ↗</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
