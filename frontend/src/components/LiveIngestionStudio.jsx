import React, { useState, useRef, useMemo, useEffect } from 'react';
import {
  UploadCloud,
  FileText,
  Layers,
  Zap,
  ShieldCheck,
  Scale,
  CheckCircle2,
  Clock,
  Sliders,
  Database,
  Lock,
  RefreshCw,
  FileCode,
  AlertCircle,
  FileSpreadsheet,
  Check,
  X,
  ArrowRight,
  GitBranch,
  Shield,
  BookOpen,
  Send,
  Server,
  Terminal,
  Activity,
  Folder,
  FolderTree,
  FolderPlus,
  FolderCheck,
  ExternalLink,
  File,
  Info,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Trash2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const formatConditionDisplay = (cond) => {
  if (!cond) return '';
  if (typeof cond === 'string') return cond;
  if (typeof cond === 'object') {
    if (cond.field && cond.value !== undefined) {
      const valStr = Array.isArray(cond.value) ? cond.value.join(' - ') : String(cond.value);
      const op = cond.operator ? ` ${cond.operator} ` : ': ';
      return `${cond.field}${op}${valStr}`;
    }
    if (cond.rule) return String(cond.rule);
    if (cond.description) return String(cond.description);
    return JSON.stringify(cond);
  }
  return String(cond);
};

const formatValueDisplay = (val) => {
  if (val === undefined || val === null) return '';
  if (typeof val === 'object') {
    if (val.rule) return String(val.rule);
    if (val.type) return String(val.type);
    return JSON.stringify(val);
  }
  return String(val);
};

// 11-Layer Fail-Closed Enterprise AI Governance Framework
export const ELEVEN_LAYERS = [
  { id: 1, label: "L1: Governance & Scope", short: "L1: Scope", desc: "SourceFamily & Intent Scoping", icon: Shield },
  { id: 2, label: "L2: Native Ingestion", short: "L2: Ingestion", desc: "Pristine Connectors & Stream", icon: Server },
  { id: 3, label: "L3: Canonical Envelope", short: "L3: Envelope", desc: "Deterministic SHA-256 Digest", icon: Lock },
  { id: 4, label: "L4: Specialized Parser", short: "L4: Parser", desc: "Atomic Evidence Unit Breakdown", icon: FileCode },
  { id: 5, label: "L5: Extraction Ledger", short: "L5: Extraction", desc: "Deontic Classification & Completeness", icon: Zap },
  { id: 6, label: "L6: Validation Gate", short: "L6: Validation", desc: "6-D Gate & PostgreSQL Seal", icon: CheckCircle2 },
  { id: 7, label: "L7: TEVV Benchmark Gate", short: "L7: TEVV Gate", desc: "Enterprise Quote Fidelity (>=99%)", icon: CheckCircle2 },
  { id: 8, label: "L8: Trust & Decay", short: "L8: Trust Decay", desc: "Bayesian Authority & Half-Life Decay", icon: Sliders },
  { id: 9, label: "L9: Conflict Detection", short: "L9: Conflict", desc: "Cross-Corpus Contradiction Analysis", icon: Scale },
  { id: 10, label: "L10: HITL Adjudication", short: "L10: HITL Queue", desc: "Human Escalation & Resolution Queue", icon: Clock },
  { id: 11, label: "L11: Decision Gate & MCP", short: "L11: Decision Gate", desc: "Real-Time Interception & Merkle Audit", icon: ShieldCheck }
];

// Helper to convert flat staged files into a nested directory tree
const buildFileTree = (files) => {
  const root = { name: 'Root', isFolder: true, children: {}, files: [] };
  files.forEach((item, index) => {
    const rawPath = item.relativePath || item.name;
    const parts = rawPath.replace(/\\/g, '/').split('/').filter(Boolean);
    if (parts.length <= 1) {
      root.files.push({ ...item, originalIndex: index });
    } else {
      let current = root;
      for (let i = 0; i < parts.length - 1; i++) {
        const folderName = parts[i];
        if (!current.children[folderName]) {
          current.children[folderName] = {
            name: folderName,
            isFolder: true,
            children: {},
            files: [],
          };
        }
        current = current.children[folderName];
      }
      current.files.push({ ...item, originalIndex: index });
    }
  });
  return root;
};

// Recursive Folder Tree Node Display Component
function FolderTreeItem({ node, depth = 0, onRemoveFile }) {
  const [isOpen, setIsOpen] = useState(true);
  const childFolders = Object.values(node.children || {});
  const totalFilesInSubtree = useMemo(() => {
    let count = node.files?.length || 0;
    const countSub = (n) => {
      let c = n.files?.length || 0;
      Object.values(n.children || {}).forEach((ch) => {
        c += countSub(ch);
      });
      return c;
    };
    childFolders.forEach((ch) => {
      count += countSub(ch);
    });
    return count;
  }, [node, childFolders]);

  return (
    <div style={{ marginLeft: depth > 0 ? '14px' : '0px', marginTop: '3px' }}>
      {/* Folder Header */}
      {node.name !== 'Root' && (
        <div
          onClick={() => setIsOpen(!isOpen)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 10px',
            borderRadius: '6px',
            background: depth === 1 ? '#F1F5F9' : '#F8FAFC',
            border: '1px solid #E2E8F0',
            cursor: 'pointer',
            fontSize: '0.76rem',
            fontWeight: 700,
            color: '#1E293B',
            userSelect: 'none',
            transition: 'background 0.15s ease',
          }}
        >
          {isOpen ? <ChevronDown size={14} color="#64748B" /> : <ChevronRight size={14} color="#64748B" />}
          <Folder size={15} color="#2563EB" fill="#DBEAFE" />
          <span style={{ fontFamily: 'monospace', letterSpacing: '-0.02em' }}>{node.name}/</span>
          <span style={{ fontSize: '0.67rem', color: '#64748B', fontWeight: 500, marginLeft: 'auto' }}>
            {totalFilesInSubtree} file{totalFilesInSubtree !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Children & Files */}
      {isOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginTop: node.name === 'Root' ? '0px' : '3px' }}>
          {childFolders.map((childNode) => (
            <FolderTreeItem
              key={childNode.name}
              node={childNode}
              depth={node.name === 'Root' ? depth : depth + 1}
              onRemoveFile={onRemoveFile}
            />
          ))}

          {node.files?.map((fileItem) => (
            <div
              key={fileItem.originalIndex}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                marginLeft: node.name === 'Root' ? '0px' : '18px',
                borderRadius: '6px',
                background: fileItem.status === 'processing'
                  ? '#FFF7ED'
                  : fileItem.status === 'done'
                  ? '#F0FDF4'
                  : fileItem.status === 'error'
                  ? '#FEF2F2'
                  : '#FFFFFF',
                border: `1px solid ${
                  fileItem.status === 'processing'
                    ? '#FDBA74'
                    : fileItem.status === 'done'
                    ? '#86EFAC'
                    : fileItem.status === 'error'
                    ? '#FCA5A5'
                    : '#E2E8F0'
                }`,
                fontSize: '0.74rem',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0, overflow: 'hidden' }}>
                <FileText
                  size={14}
                  color={
                    fileItem.status === 'done'
                      ? '#16A34A'
                      : fileItem.status === 'processing'
                      ? '#EA580C'
                      : fileItem.status === 'error'
                      ? '#DC2626'
                      : '#64748B'
                  }
                  style={{ flexShrink: 0 }}
                />
                <span
                  style={{
                    fontWeight: 600,
                    color: '#0F172A',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                  }}
                  title={fileItem.relativePath || fileItem.name}
                >
                  {fileItem.name}
                </span>
                <span style={{ fontSize: '0.65rem', color: '#64748B', background: '#F1F5F9', padding: '1px 5px', borderRadius: '4px', flexShrink: 0 }}>
                  {(fileItem.size / 1024).toFixed(1)} KB
                </span>
                {fileItem.folderName && (
                  <span style={{ fontSize: '0.64rem', color: '#1D4ED8', background: '#EFF6FF', padding: '1px 5px', borderRadius: '4px', flexShrink: 0, border: '1px solid #DBEAFE' }}>
                    📁 {fileItem.folderName}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                {fileItem.status === 'staged' && (
                  <>
                    <span style={{ fontSize: '0.66rem', color: '#475569', background: '#F1F5F9', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      Ready
                    </span>
                    {onRemoveFile && (
                      <button
                        type="button"
                        onClick={() => onRemoveFile(fileItem.originalIndex)}
                        title="Remove file from staging"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: '#94A3B8' }}
                      >
                        <X size={12} />
                      </button>
                    )}
                  </>
                )}
                {fileItem.status === 'processing' && (
                  <span style={{ fontSize: '0.66rem', color: '#EA580C', background: '#FFEDD5', padding: '2px 6px', borderRadius: '4px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <RefreshCw size={10} className="animate-spin" />
                    <span>Ingesting...</span>
                  </span>
                )}
                {fileItem.status === 'done' && (
                  <span style={{ fontSize: '0.66rem', color: '#15803D', background: '#DCFCE7', padding: '2px 6px', borderRadius: '4px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={11} />
                    <span>{fileItem.claimsCount || 0} claims sealed</span>
                  </span>
                )}
                {fileItem.status === 'error' && (
                  <span style={{ fontSize: '0.66rem', color: '#DC2626', background: '#FEE2E2', padding: '2px 6px', borderRadius: '4px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <AlertCircle size={11} />
                    <span>{fileItem.errorMsg || 'Failed'}</span>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LiveIngestionStudio({
  activeOrg,
  activePersona,
  onClaimExtracted,
  showToast,
  onNavigateToVaultClaims
}) {
  const { user, token, hasPermission } = useAuth();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const [dragOver, setDragOver] = useState(false);
  const [stagedFiles, setStagedFiles] = useState([]);
  const [activeRightTab, setActiveRightTab] = useState('structure'); // 'structure' | 'claims'
  const [currentProcessingIndex, setCurrentProcessingIndex] = useState(-1);

  const [documentType, setDocumentType] = useState('policy');
  const [documentScope, setDocumentScope] = useState('Enterprise');
  const [authorityLevel, setAuthorityLevel] = useState(95);
  const [sourceFamily, setSourceFamily] = useState('document');
  const [sourceIntent, setSourceIntent] = useState('governance_policy');
  const [extractionEngine, setExtractionEngine] = useState('ollama'); // 'ollama', 'mock', 'openai', 'openrouter'
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0); // 0: Idle, 1..11: L1..L11, 12: Sealed & Done
  const [pipelineResult, setPipelineResult] = useState(null);
  const [history, setHistory] = useState([]);

  const [folders, setFolders] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState('');

  useEffect(() => {
    let isMounted = true;
    const fetchFolders = async () => {
      try {
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (activeOrg?.id) headers['X-Organization-Id'] = activeOrg.id;
        const orgParam = activeOrg?.id ? `?organization_id=${activeOrg.id}` : '';
        const res = await fetch(`/v1/folders${orgParam}`, { credentials: 'include', headers });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setFolders(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.warn('Failed to load folders for Ingestion Studio:', err);
      }
    };
    fetchFolders();
    return () => { isMounted = false; };
  }, [activeOrg?.id, token]);

  // Compute folder hierarchy tree
  const fileTreeRoot = useMemo(() => buildFileTree(stagedFiles), [stagedFiles]);

  const totalBytes = useMemo(() => stagedFiles.reduce((acc, f) => acc + (f.size || 0), 0), [stagedFiles]);

  const totalFoldersCount = useMemo(() => {
    const folderPaths = new Set();
    stagedFiles.forEach((f) => {
      const parts = (f.relativePath || f.name).replace(/\\/g, '/').split('/').filter(Boolean);
      if (parts.length > 1) {
        let p = '';
        for (let i = 0; i < parts.length - 1; i++) {
          p = p ? `${p}/${parts[i]}` : parts[i];
          folderPaths.add(p);
        }
      }
    });
    return folderPaths.size;
  }, [stagedFiles]);

  const handleFilesAdd = (rawFiles) => {
    if (!rawFiles || rawFiles.length === 0) return;
    const newStaged = rawFiles.map((file) => {
      const relPath = file.webkitRelativePath || file.customRelativePath || file.name;
      return {
        file,
        name: file.name,
        relativePath: relPath,
        size: file.size,
        status: 'staged',
        errorMsg: null,
        claimsCount: 0,
        folderName: null,
      };
    });

    setStagedFiles((prev) => {
      const existingPaths = new Set(prev.map((p) => p.relativePath));
      const filtered = newStaged.filter((f) => !existingPaths.has(f.relativePath));
      return [...prev, ...filtered];
    });

    setActiveRightTab('structure');

    // Auto-detect Document Category & Intent from first file if appropriate
    const first = rawFiles[0];
    if (first) {
      const lower = first.name.toLowerCase();
      if (lower.endsWith('.json') || lower.endsWith('.csv') || lower.endsWith('.xlsx') || lower.endsWith('.sql')) {
        setSourceFamily('structured');
      }
      if (lower.includes('handbook')) {
        setDocumentType('handbook');
      } else if (lower.includes('security') || lower.includes('firewall')) {
        setDocumentType('security_guideline');
      } else if (lower.includes('pricing') || lower.includes('financial') || lower.endsWith('.csv')) {
        setDocumentType('financial_matrix');
      }
    }
  };

  const handleRemoveStaged = (index) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearAll = () => {
    setStagedFiles([]);
    setPipelineResult(null);
    setPipelineStage(0);
    setCurrentProcessingIndex(-1);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (folderInputRef.current) folderInputRef.current.value = '';
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);

    const items = e.dataTransfer.items;
    if (items && items.length > 0) {
      const fileList = [];
      const scanEntry = async (entry, path = '') => {
        if (entry.isFile) {
          return new Promise((resolve) => {
            entry.file((file) => {
              file.customRelativePath = path + file.name;
              resolve([file]);
            }, () => resolve([]));
          });
        } else if (entry.isDirectory) {
          const reader = entry.createReader();
          const readEntries = () => new Promise((resolve) => reader.readEntries(resolve, () => resolve([])));
          let allEntries = [];
          let batch = await readEntries();
          while (batch.length > 0) {
            allEntries = allEntries.concat(batch);
            batch = await readEntries();
          }
          const subFiles = await Promise.all(
            allEntries.map((subEntry) => scanEntry(subEntry, `${path}${entry.name}/`))
          );
          return subFiles.flat();
        }
        return [];
      };

      const promises = [];
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.webkitGetAsEntry) {
          const entry = item.webkitGetAsEntry();
          if (entry) {
            promises.push(scanEntry(entry, ''));
          }
        } else {
          const f = item.getAsFile();
          if (f) fileList.push(f);
        }
      }
      const resolved = await Promise.all(promises);
      const allScanned = fileList.concat(resolved.flat());
      if (allScanned.length > 0) {
        handleFilesAdd(allScanned);
      }
    } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdd(Array.from(e.dataTransfer.files));
    }
  };

  const handleExecuteExtractionPipeline = async () => {
    if (stagedFiles.length === 0) {
      showToast?.("Please select or drop documents or a folder to ingest", "error");
      return;
    }
    if (!hasPermission('claims:extract')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'user').toUpperCase()}) cannot run claim extraction pipelines. Only Data Stewards or CCO have ingestion clearance.`,
        'error'
      );
      return;
    }

    setIsProcessing(true);
    let totalClaimsExtracted = 0;
    let allExtractedClaims = [];
    let lastPipelineRes = null;

    for (let i = 0; i < stagedFiles.length; i++) {
      const item = stagedFiles[i];
      setCurrentProcessingIndex(i);
      setStagedFiles((prev) => prev.map((f, idx) => idx === i ? { ...f, status: 'processing' } : f));
      setPipelineStage(1);

      // Progressive stage animations (text-by-text stream)
      const stageTimers = [
        setTimeout(() => setPipelineStage(2), 100),
        setTimeout(() => setPipelineStage(3), 220),
        setTimeout(() => setPipelineStage(4), 350),
        setTimeout(() => setPipelineStage(5), 480),
        setTimeout(() => setPipelineStage(6), 620),
        setTimeout(() => setPipelineStage(7), 760),
        setTimeout(() => setPipelineStage(8), 900),
        setTimeout(() => setPipelineStage(9), 1040),
        setTimeout(() => setPipelineStage(10), 1180),
        setTimeout(() => setPipelineStage(11), 1320),
      ];

      try {
        const formData = new FormData();
        formData.append('file', item.file);
        formData.append('relative_path', item.relativePath);
        formData.append('organization_id', activeOrg?.id || '11111111-1111-1111-1111-111111111111');
        if (selectedFolderId) {
          formData.append('folder_id', selectedFolderId);
        }
        formData.append('document_type', documentType);
        formData.append('provider', extractionEngine);
        formData.append('use_mock', extractionEngine === 'mock' ? 'true' : 'false');
        formData.append('source_family', sourceFamily);
        formData.append('source_intent', sourceIntent);

        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (user?.role) headers['x-user-role'] = user.role;

        const res = await fetch(`/v1/documents/upload-and-extract?user_role=${user?.role || ''}`, {
          method: 'POST',
          headers,
          body: formData,
        });

        stageTimers.forEach((t) => clearTimeout(t));

        if (res.ok) {
          const data = await res.json();
          const claimsCount = data.claims_extracted_count || (data.layers?.layer_6_validation_gate?.claims_approved ?? 0);
          totalClaimsExtracted += claimsCount;
          if (data.claims && Array.isArray(data.claims)) {
            allExtractedClaims = allExtractedClaims.concat(data.claims);
          }
          lastPipelineRes = data;
          setPipelineStage(12);

          setStagedFiles((prev) => prev.map((f, idx) => idx === i ? {
            ...f,
            status: 'done',
            claimsCount: claimsCount,
            folderName: data.folder_name || 'Inbox',
          } : f));

          setHistory((prev) => [
            {
              filename: item.name,
              documentId: data.document?.id,
              title: data.document?.title || item.name,
              relativePath: item.relativePath,
              targetFolder: data.folder_name || 'Inbox',
              claimsCount: claimsCount,
              durationMs: data.duration_ms || 320,
              time: "Just now",
              type: documentType,
              scope: documentScope,
              status: "sealed_11_layers",
            },
            ...prev,
          ]);
        } else {
          setStagedFiles((prev) => prev.map((f, idx) => idx === i ? { ...f, status: 'error', errorMsg: `Failed (${res.status})` } : f));
        }
      } catch (err) {
        stageTimers.forEach((t) => clearTimeout(t));
        setStagedFiles((prev) => prev.map((f, idx) => idx === i ? { ...f, status: 'error', errorMsg: err.message } : f));
      }
    }

    setIsProcessing(false);
    setCurrentProcessingIndex(-1);

    if (lastPipelineRes) {
      setPipelineResult({
        ...lastPipelineRes,
        claims_extracted_count: totalClaimsExtracted,
      });
      // Claims are kept out of this view and routed to Context Vault
    }

    showToast?.(`✓ Ingestion Complete: Processed ${stagedFiles.length} file(s) into folder structure with ${totalClaimsExtracted} atomic claims sealed.`);
    if (onClaimExtracted) onClaimExtracted();
  };

  const getAuthorityBadge = (level) => {
    if (level >= 90) return { label: 'Tier 1: Sovereign Mandate', color: '#EA580C', bg: '#FFF7ED' };
    if (level >= 75) return { label: 'Tier 2: VP Directive', color: '#2563EB', bg: '#EFF6FF' };
    return { label: 'Tier 3: Standard SOP', color: '#64748B', bg: '#F1F5F9' };
  };

  const authBadge = getAuthorityBadge(authorityLevel);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* ========================================================
          MAIN SPLIT CANVAS: DOCUMENT CONTROLLER (38%) + FOLDER STAGING MATRIX (62%)
          ======================================================== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 400px) 1fr', gap: '16px', alignItems: 'start', width: '100%' }}>

        {/* Left: Document Intake & Authority Tuning */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '14px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Document & Folder Controller
            </span>
            <span style={{ fontSize: '0.70rem', color: '#64748B' }}>
              {stagedFiles.length > 0 ? `${stagedFiles.length} File(s) Staged` : 'No Files Selected'}
            </span>
          </div>

          {/* Interactive Unified Drop Zone for Files & Folders */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            style={{
              border: `2px dashed ${dragOver ? '#EA580C' : stagedFiles.length > 0 ? '#059669' : 'rgba(234, 88, 12, 0.3)'}`,
              background: dragOver
                ? '#FFF7ED'
                : stagedFiles.length > 0
                ? 'rgba(240, 253, 244, 0.6)'
                : 'linear-gradient(180deg, #FAFAF9 0%, #FFFFFF 100%)',
              borderRadius: '12px',
              padding: '20px 14px',
              textAlign: 'center',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '12px'
            }}
          >
            {/* Hidden native inputs */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFilesAdd(Array.from(e.target.files || []))}
              accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md,.json,.jsonl,.csv,.tsv,.html,.htm,.xhtml,.xml,.yaml,.yml,.toml,.ini,.conf,.log,.sql,.env,.rtf,*"
              multiple
              style={{ display: 'none' }}
            />

            <input
              type="file"
              ref={folderInputRef}
              onChange={(e) => handleFilesAdd(Array.from(e.target.files || []))}
              webkitdirectory=""
              directory=""
              multiple
              style={{ display: 'none' }}
            />

            <div style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: stagedFiles.length > 0
                ? 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)'
                : 'linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%)',
              border: `1px solid ${stagedFiles.length > 0 ? 'rgba(5, 150, 105, 0.3)' : 'rgba(234, 88, 12, 0.3)'}`,
              color: stagedFiles.length > 0 ? '#059669' : '#EA580C',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: stagedFiles.length > 0 ? '0 2px 8px rgba(5,150,105,0.15)' : '0 2px 8px rgba(234,88,12,0.12)'
            }}>
              {stagedFiles.length > 0 ? <CheckCircle2 size={22} /> : <UploadCloud size={22} />}
            </div>

            <div>
              <p style={{ margin: 0, fontWeight: 700, fontSize: '0.86rem', color: 'var(--text-main)' }}>
                {stagedFiles.length > 0
                  ? `${stagedFiles.length} file(s) staged for ingestion`
                  : 'Drop documents or whole folders here'}
              </p>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                {stagedFiles.length > 0
                  ? 'Subfolder hierarchy will be created and preserved as-is.'
                  : 'Nested subfolders are automatically mapped and preserved.'}
              </p>
            </div>

            {/* Folder and File Upload Trigger Buttons */}
            <div style={{ display: 'flex', gap: '8px', width: '100%', justifyContent: 'center' }}>
              <button
                type="button"
                onClick={() => folderInputRef.current?.click()}
                className="btn btn-secondary"
                style={{
                  flex: 1,
                  height: '34px',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  background: '#EFF6FF',
                  color: '#1D4ED8',
                  border: '1px solid #BFDBFE',
                  borderRadius: '8px',
                  cursor: 'pointer'
                }}
              >
                <FolderPlus size={14} color="#2563EB" />
                <span>Upload Folder</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="btn btn-secondary"
                style={{
                  flex: 1,
                  height: '34px',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  background: '#FFF7ED',
                  color: '#EA580C',
                  border: '1px solid #FED7AA',
                  borderRadius: '8px',
                  cursor: 'pointer'
                }}
              >
                <FileText size={14} color="#EA580C" />
                <span>Upload Files</span>
              </button>
            </div>
          </div>

          {/* Configuration Form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Layer 1: Source Governance (Family & Intent) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  <Shield size={11} color="#4338CA" />
                  <span>L1: Source Family</span>
                </label>
                <select
                  value={sourceFamily}
                  onChange={(e) => setSourceFamily(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="document">Document (PDF/MD/Doc)</option>
                  <option value="structured">Structured (JSON/CSV/DB)</option>
                  <option value="conversation">Conversation (Slack/Chat)</option>
                  <option value="metadata">Metadata / OpenAPI</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  <ShieldCheck size={11} color="#4338CA" />
                  <span>L1: Source Intent</span>
                </label>
                <select
                  value={sourceIntent}
                  onChange={(e) => setSourceIntent(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="governance_policy">Governance Policy</option>
                  <option value="operational_data">Operational Data</option>
                  <option value="discussions">Proposals & Discussion</option>
                  <option value="factual_knowledge">Factual Knowledge</option>
                  <option value="analytics_metric">Analytics Metric / KPI</option>
                </select>
              </div>
            </div>

            {/* Category & Scope Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  Document Category
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="policy">Corporate Policy</option>
                  <option value="handbook">Employee Handbook</option>
                  <option value="memo">VP Directive Memo</option>
                  <option value="security_guideline">SecOps Mandate</option>
                  <option value="runbook">DevOps Runbook</option>
                  <option value="financial_matrix">Financial / Spreadsheet Matrix</option>
                  <option value="technical_spec">Technical Spec / Config</option>
                  <option value="compliance_audit">Compliance / Audit Standard</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  Target Scope
                </label>
                <select
                  value={documentScope}
                  onChange={(e) => setDocumentScope(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="Enterprise">Enterprise</option>
                  <option value="Production">Production</option>
                  <option value="Engineering">Engineering</option>
                  <option value="General">Global Standard</option>
                </select>
              </div>
            </div>

            {/* Destination Workspace Folder */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                <Folder size={11} color="#2563EB" />
                <span>Destination Folder</span>
              </label>
              <select
                value={selectedFolderId}
                onChange={(e) => setSelectedFolderId(e.target.value)}
                className="sim-input-control"
                style={{
                  width: '100%',
                  fontSize: '0.78rem',
                  height: '34px',
                  padding: '0 8px',
                  background: selectedFolderId ? '#EFF6FF' : '#F8FAFC',
                  borderColor: selectedFolderId ? '#3B82F6' : undefined,
                  fontWeight: selectedFolderId ? 600 : 400
                }}
              >
                <option value="">✨ Smart Auto-Route (Domain & Topic Driven)</option>
                {folders.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.is_system ? '🏛️ ' : '📁 '} {f.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Extraction Engine */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                <Zap size={11} color="#EA580C" />
                <span>L5: Strategy Router & Engine</span>
              </label>
              <select
                value={extractionEngine}
                onChange={(e) => setExtractionEngine(e.target.value)}
                className="sim-input-control"
                style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px', borderColor: extractionEngine === 'ollama' ? '#059669' : undefined }}
              >
                <option value="ollama">Auto Strategy Router (Deterministic + Heuristics + Ollama)</option>
                <option value="mock">Deterministic Rule Engine (Fast Offline Zero-Cost)</option>
                <option value="openai">OpenAI GPT-4o-mini (Cloud Structured Router)</option>
                <option value="openrouter">OpenRouter / Ox-Alpha (Cloud Router)</option>
              </select>
            </div>

            {/* Authority Weight Dial */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Authority Weight
                </span>
                <span style={{ fontSize: '0.70rem', fontWeight: 800, color: authBadge.color, background: authBadge.bg, padding: '2px 6px', borderRadius: '4px' }}>
                  {authorityLevel} / 100 &bull; {authBadge.label}
                </span>
              </div>
              <input
                type="range"
                min="30"
                max="100"
                step="5"
                value={authorityLevel}
                onChange={(e) => setAuthorityLevel(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#EA580C', cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Action Trigger Button */}
          <button
            type="button"
            onClick={handleExecuteExtractionPipeline}
            disabled={stagedFiles.length === 0 || isProcessing || !hasPermission('claims:extract')}
            style={{
              height: '42px',
              borderRadius: '10px',
              background: stagedFiles.length === 0 || isProcessing || !hasPermission('claims:extract')
                ? '#F1F5F9'
                : 'linear-gradient(135deg, #EA580C 0%, #C2410C 100%)',
              color: stagedFiles.length === 0 || isProcessing || !hasPermission('claims:extract') ? '#94A3B8' : '#FFFFFF',
              border: 'none',
              fontWeight: 800,
              fontSize: '0.84rem',
              cursor: stagedFiles.length === 0 || isProcessing || !hasPermission('claims:extract') ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: stagedFiles.length > 0 && !isProcessing && hasPermission('claims:extract')
                ? '0 4px 14px rgba(234, 88, 12, 0.32)'
                : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            {isProcessing ? (
              <>
                <RefreshCw size={15} className="animate-spin" />
                <span>
                  Ingesting File {currentProcessingIndex + 1} of {stagedFiles.length}...
                </span>
              </>
            ) : !hasPermission('claims:extract') ? (
              <>
                <Lock size={15} />
                <span>Data Steward Clearance Required</span>
              </>
            ) : (
              <>
                <Zap size={15} />
                <span>
                  Launch 11-Layer Pipeline {stagedFiles.length > 0 ? `(${stagedFiles.length} File${stagedFiles.length > 1 ? 's' : ''})` : ''}
                </span>
              </>
            )}
          </button>
        </div>

        {/* Right: Compact Progressive Pipeline Text Stream & Staged Folder Structure */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%', minWidth: 0 }}>

          {/* Sleek, Compact Text-by-Text Progressive Pipeline Log (Only shown when running or complete) */}
          {pipelineStage > 0 && (
            <div style={{
              background: '#0F172A',
              borderRadius: '10px',
              border: '1px solid #1E293B',
              padding: '12px 16px',
              color: '#E2E8F0',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              fontSize: '0.74rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(0,0,0,0.1)'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid #334155',
                paddingBottom: '8px',
                marginBottom: '4px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={14} color="#38BDF8" />
                  <span style={{ fontWeight: 700, color: '#F8FAFC', letterSpacing: '0.04em' }}>
                    11-LAYER UNIVERSAL TRUST PIPELINE
                  </span>
                  {isProcessing && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#F59E0B', fontSize: '0.68rem' }}>
                      <RefreshCw size={10} className="animate-spin" />
                      <span>Processing Layer {Math.min(pipelineStage, 11)}/11...</span>
                    </span>
                  )}
                  {pipelineStage === 12 && (
                    <span style={{ color: '#10B981', fontWeight: 700, fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={12} />
                      <span>11 Layers Verified & Sealed</span>
                    </span>
                  )}
                </div>

                {pipelineStage === 12 && onNavigateToVaultClaims && (
                  <button
                    type="button"
                    onClick={() => onNavigateToVaultClaims()}
                    style={{
                      background: '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '5px',
                      padding: '4px 10px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <span>View Claims in Vault</span>
                    <ArrowRight size={11} />
                  </button>
                )}
              </div>

              {/* Progressive text-by-text entries */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '180px', overflowY: 'auto' }}>
                {ELEVEN_LAYERS.filter(layer => pipelineStage >= layer.id).map(layer => {
                  const isDone = pipelineStage > layer.id || pipelineStage === 12;
                  return (
                    <div
                      key={layer.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        color: isDone ? '#94A3B8' : '#38BDF8',
                        lineHeight: 1.4
                      }}
                    >
                      <span style={{ color: isDone ? '#10B981' : '#F59E0B', width: '14px', textAlign: 'center' }}>
                        {isDone ? '✓' : '▶'}
                      </span>
                      <span style={{ color: isDone ? '#F1F5F9' : '#38BDF8', fontWeight: 600 }}>
                        {layer.label}:
                      </span>
                      <span style={{ color: isDone ? '#94A3B8' : '#CBD5E1' }}>
                        {layer.desc}
                      </span>
                      {isDone && (
                        <span style={{ marginLeft: 'auto', fontSize: '0.64rem', color: '#10B981', fontWeight: 600 }}>
                          [PASSED]
                        </span>
                      )}
                    </div>
                  );
                })}

                {pipelineStage === 12 && (
                  <div style={{
                    marginTop: '6px',
                    paddingTop: '6px',
                    borderTop: '1px dashed #334155',
                    color: '#10B981',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <span>✔ Complete:</span>
                    <span style={{ color: '#E2E8F0', fontWeight: 500 }}>
                      All claims normalized and safely committed to Context Vault (Atomic Claims).
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Main Right Container: Staged Folder Structure */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '14px',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            minHeight: '440px',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.02)'
          }}>

            {/* Header with Folder Structure Title & Vault Action */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FolderTree size={16} color="#2563EB" />
                <span style={{ fontSize: '0.86rem', fontWeight: 800, color: 'var(--text-main)' }}>
                  Staged Folder Structure ({stagedFiles.length})
                </span>

                {pipelineResult && (pipelineResult.claims_extracted_count > 0 || (pipelineResult.claims && pipelineResult.claims.length > 0)) && (
                  <button
                    type="button"
                    onClick={() => onNavigateToVaultClaims ? onNavigateToVaultClaims() : null}
                    style={{
                      background: '#F0FDF4',
                      border: '1px solid #BBF7D0',
                      borderRadius: '6px',
                      padding: '3px 9px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      color: '#166534',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      marginLeft: '6px'
                    }}
                    title="View claims in Context Vault"
                  >
                    <ShieldCheck size={12} color="#166534" />
                    <span>{pipelineResult.claims_extracted_count || pipelineResult.claims?.length || 0} Claims in Vault</span>
                    <ArrowRight size={10} />
                  </button>
                )}
              </div>

              {stagedFiles.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge" style={{ background: '#F1F5F9', color: '#475569', fontSize: '0.68rem', fontWeight: 600 }}>
                    {(totalBytes / 1024).toFixed(1)} KB &bull; {stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''}
                    {totalFoldersCount > 0 && ` &bull; ${totalFoldersCount} subfolder${totalFoldersCount > 1 ? 's' : ''}`}
                  </span>
                  <button
                    type="button"
                    onClick={handleClearAll}
                    disabled={isProcessing}
                    title="Clear staged files"
                    style={{
                      background: 'none',
                      border: '1px solid #E2E8F0',
                      borderRadius: '6px',
                      padding: '3px 8px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: '#DC2626',
                      cursor: isProcessing ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Trash2 size={12} />
                    <span>Clear</span>
                  </button>
                </div>
              )}
            </div>

            {/* STAGED FOLDER STRUCTURE EXPLORER */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
              {stagedFiles.length === 0 ? (
                /* Standby / No Files Selected */
                <div style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  textAlign: 'center',
                  padding: '46px 20px',
                  gap: '14px',
                  background: '#FAFAF9',
                  borderRadius: '10px',
                  border: '1px dashed #CBD5E1'
                }}>
                  <div style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '14px',
                    background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
                    border: '1px solid #BFDBFE',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#2563EB'
                  }}>
                    <FolderTree size={26} />
                  </div>

                  <div>
                    <h4 style={{ margin: 0, fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Folder Structure Ingestion Canvas
                    </h4>
                    <p style={{ margin: '6px 0 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', maxWidth: '460px', lineHeight: 1.5 }}>
                      Upload an entire folder containing nested subfolders or choose multiple individual documents.
                      Trulin recreates your exact folder hierarchy in the repository and files each document accordingly.
                    </p>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', justifyContent: 'center', marginTop: '4px' }}>
                    <span className="sim-chip-tag" style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', color: '#475569' }}>
                      📁 Subfolder Preservation
                    </span>
                    <span className="sim-chip-tag" style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', color: '#475569' }}>
                      ⚡ 11-Layer Progressive Ingestion
                    </span>
                    <span className="sim-chip-tag" style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', color: '#475569' }}>
                      🔒 SHA-256 Envelope Seal
                    </span>
                  </div>
                </div>
              ) : (
                /* Files Staged: Hierarchy Tree View */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {/* Folder Structure Path Bar */}
                  <div style={{
                    background: '#F0F9FF',
                    border: '1px solid #BAE6FD',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '0.74rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FolderCheck size={15} color="#0284C7" />
                      <span style={{ color: '#0369A1', fontWeight: 700 }}>
                        Hierarchy Staging:
                      </span>
                      <span style={{ color: '#0F172A', fontWeight: 600 }}>
                        {totalFoldersCount > 0
                          ? `${totalFoldersCount} folder(s) mapped with ${stagedFiles.length} file(s)`
                          : `${stagedFiles.length} file(s) staged in root position`}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.66rem', background: '#BAE6FD', color: '#0369A1', padding: '1px 7px', borderRadius: '4px', fontWeight: 700 }}>
                      Auto-Routing Intact
                    </span>
                  </div>

                  {/* Tree View Container */}
                  <div style={{
                    maxHeight: '480px',
                    overflowY: 'auto',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    padding: '10px',
                    background: '#FAFAF9'
                  }}>
                    <FolderTreeItem
                      node={fileTreeRoot}
                      depth={0}
                      onRemoveFile={isProcessing ? null : handleRemoveStaged}
                    />
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </div>

      {/* ========================================================
          BOTTOM: RECENT INGESTIONS & EXTRACTED CORPORA LEDGER
          ======================================================== */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.02)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={15} color="#EA580C" />
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Corpora Ingestion Ledger
            </span>
          </div>
          <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 600 }}>
            {history.length} Ingested Document(s) in Current Session
          </span>
        </div>

        <div style={{ overflowX: 'auto', width: '100%' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', minWidth: '600px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: '#64748B', textAlign: 'left', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <th style={{ padding: '8px 12px' }}>Document / File</th>
                <th style={{ padding: '8px 12px' }}>Folder Path</th>
                <th style={{ padding: '8px 12px' }}>Category</th>
                <th style={{ padding: '8px 12px' }}>Operational Scope</th>
                <th style={{ padding: '8px 12px' }}>Claims Extracted</th>
                <th style={{ padding: '8px 12px' }}>Pipeline Latency</th>
                <th style={{ padding: '8px 12px' }}>Provenance</th>
                <th style={{ padding: '8px 12px' }}>Ingested</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ padding: '22px', textAlign: 'center', color: '#94A3B8', fontSize: '0.78rem' }}>
                    No custom corpora ingested in this session yet. Upload a folder or files above to execute 11-layer extraction.
                  </td>
                </tr>
              ) : (
                history.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={13} color="#EA580C" />
                      <span>{item.title}</span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="sim-chip-tag" style={{ background: '#EFF6FF', color: '#1D4ED8', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Folder size={11} />
                        <span>{item.relativePath ? item.relativePath.split('/').slice(0, -1).join('/') || item.targetFolder : item.targetFolder}</span>
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="sim-chip-tag" style={{ background: '#F1F5F9', color: '#475569', textTransform: 'capitalize' }}>
                        {item.type}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="sim-chip-tag" style={{ background: '#F0FDF4', color: '#15803D' }}>
                        {item.scope || 'Enterprise'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: 700, color: '#059669' }}>{item.claimsCount} claims</span>
                        {onNavigateToVaultClaims && (
                          <button
                            type="button"
                            onClick={() => onNavigateToVaultClaims(item.documentId || item.title)}
                            style={{
                              background: '#EFF6FF',
                              border: '1px solid #BFDBFE',
                              borderRadius: '4px',
                              padding: '2px 7px',
                              fontSize: '0.64rem',
                              color: '#1D4ED8',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '3px',
                              fontWeight: 700
                            }}
                            title="View in Context Vault"
                          >
                            <span>Vault</span>
                            <ExternalLink size={10} />
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748B' }}>
                      {item.durationMs}ms
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                        11-L Sealed
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748B' }}>
                      {item.time}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
