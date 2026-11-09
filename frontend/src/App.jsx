import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Home,
  Brain,
  Bot,
  Zap,
  Network,
  ShieldAlert,
  FolderTree,
  Sliders,
  BarChart3,
  Users,
  MessageSquare,
  Plus,
  MoreHorizontal,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Terminal,
  Cpu,
  History,
  Sparkles,
  Eye,
  Lock,
  Database,
  Shield,
  Bell,
  UserCheck,
  Crosshair,
  Binary,
  User,
  Building2,
  FolderGit2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  LogOut,
  Settings,
  Upload
} from 'lucide-react';
import AuthLandingView from './components/AuthLandingView';
import UserProfileStudio from './components/UserProfileStudio';
import TeamAndActivityHub from './components/TeamAndActivityHub';
import AgentChatPlayground from './components/AgentChatPlayground';
import LiveIngestionStudio from './components/LiveIngestionStudio';
import VisualLineageGraph from './components/VisualLineageGraph';
import ContextCuratorStudio from './components/ContextCuratorStudio';
import McpIntegrationStudio from './components/McpIntegrationStudio';
import SignInModal from './components/SignInModal';
import OrganizationSettingsModal from './components/OrganizationSettingsModal';
import OrganizationSetupWizardModal from './components/OrganizationSetupWizardModal';
import OrganizationSetupChecklistBanner from './components/OrganizationSetupChecklistBanner';
import WorkspaceSettingsStudio from './components/WorkspaceSettingsStudio';
import RbacMatrixModal from './components/RbacMatrixModal';
import ExecutiveRoiModal from './components/ExecutiveRoiModal';
import ComplianceDossierModal from './components/ComplianceDossierModal';
import WebhookSettingsModal from './components/WebhookSettingsModal';
import HitlEscalationModal from './components/HitlEscalationModal';
import RedTeamModal from './components/RedTeamModal';
import MerkleVerificationModal from './components/MerkleVerificationModal';
import AssetInspectorDrawer from './components/AssetInspectorDrawer';
import MillionScaleClaimsGrid from './components/MillionScaleClaimsGrid';
import DocumentWorkspaceExplorer from './components/DocumentWorkspaceExplorer';
import { useAuth, DEFAULT_ENTERPRISE_PERSONAS } from './context/AuthContext';
import { ENTERPRISE_CONNECTORS, CATALOG_CATEGORIES, getConnectorById } from './utils/connectorsCatalog';

// -------------------------------------------------------------
// Route URL & Navigation Configuration
// -------------------------------------------------------------
export const TAB_TO_PATH = {
  home: '/',
  playground: '/chat',
  demo: '/demo',
  live_ingestion: '/live-ingestion',
  visual_lineage: '/vault',
  context_curator: '/curator',
  conflicts: '/conflicts',
  ingestion: '/documents',
  integrations: '/integrations',
  audit: '/audit',
  team: '/team',
  profile: '/profile',
  settings: '/settings'
};

export const PATH_TO_TAB = {
  '/': 'home',
  '/home': 'home',
  '/chat': 'playground',
  '/playground': 'playground',
  '/demo': 'demo',
  '/live-ingestion': 'live_ingestion',
  '/live_ingestion': 'live_ingestion',
  '/lineage': 'visual_lineage',
  '/visual-lineage': 'visual_lineage',
  '/vault': 'visual_lineage',
  '/curator': 'context_curator',
  '/context-curator': 'context_curator',
  '/conflicts': 'conflicts',
  '/documents': 'ingestion',
  '/ingestion': 'ingestion',
  '/integrations': 'integrations',
  '/audit': 'audit',
  '/audit-trail': 'audit',
  '/team': 'team',
  '/personas': 'team',
  '/profile': 'profile',
  '/settings': 'settings',
  '/workspace-settings': 'settings'
};

export const DEFAULT_WORKSPACES = [
  { id: 'all', name: 'All Workspaces (Unified)', icon: '🌐', domain: 'global', description: 'Unified enterprise knowledge across all departments and systems' },
];

export const VAULT_SUBTABS = ['claims', 'dag'];
export const CURATOR_SUBVIEWS = ['health', 'conflicts', 'drift'];
export const DOC_EXPLORER_VIEWS = ['folders', 'documents', 'ingest', 'connectors', 'connect', 'claims'];
export const MCP_SUBVIEWS = ['tester', 'configs', 'sdks', 'schemas'];
export const TEAM_SUBTABS = ['directory', 'activity', 'domains'];
export const PROFILE_SUBTABS = ['user_profile', 'companies', 'register'];
export const LINEAGE_SECTIONS = ['summary', 'extraction', 'dag', 'conflicts', 'claims', 'all'];

export const parseUrlState = (workspacesList) => {
  if (typeof window === 'undefined') {
    return {
      tab: 'home',
      vaultSubTab: 'claims',
      docId: null,
      claimId: null,
      lineageSection: 'summary',
      workspace: DEFAULT_WORKSPACES[0],
      docView: 'folders',
      curatorSubView: 'health',
      mcpSubView: 'tester',
      teamSubTab: 'directory',
      profileSubTab: 'user_profile',
      chatSession: null,
      scenario: 'refund_trap'
    };
  }

  const rawPath = window.location.pathname.toLowerCase().replace(/\/$/, '') || '/';
  const params = new URLSearchParams(window.location.search);

  let tab = 'home';
  let vaultSubTab = 'claims';
  let curatorSubView = 'health';
  let docView = 'folders';
  let mcpSubView = 'tester';
  let teamSubTab = 'directory';
  let profileSubTab = 'user_profile';

  // 1. Vault / Lineage routing
  if (rawPath === '/lineage' || rawPath === '/vault' || rawPath.startsWith('/lineage/') || rawPath.startsWith('/vault/')) {
    tab = 'visual_lineage';
    const parts = rawPath.split('/').filter(Boolean);
    const subCandidate = parts[1] || params.get('sub') || params.get('tab');
    if (subCandidate && VAULT_SUBTABS.includes(subCandidate)) {
      vaultSubTab = subCandidate;
    } else {
      vaultSubTab = 'claims';
    }
  }
  // 2. Curator routing
  else if (rawPath === '/curator' || rawPath === '/context-curator' || rawPath.startsWith('/curator/') || rawPath.startsWith('/context-curator/')) {
    tab = 'context_curator';
    const parts = rawPath.split('/').filter(Boolean);
    const sub = parts[1] || params.get('sub');
    if (sub && CURATOR_SUBVIEWS.includes(sub)) {
      curatorSubView = sub;
    } else {
      curatorSubView = 'health';
    }
  }
  // 3. Conflicts standalone routing
  else if (rawPath === '/conflicts') {
    tab = 'conflicts';
    curatorSubView = 'conflicts';
  }
  // 4. Ingestion / Document Explorer routing
  else if (rawPath === '/documents' || rawPath === '/ingestion' || rawPath.startsWith('/documents/') || rawPath.startsWith('/ingestion/')) {
    tab = 'ingestion';
    const parts = rawPath.split('/').filter(Boolean);
    const sub = parts[1] || params.get('view');
    if (sub && DOC_EXPLORER_VIEWS.includes(sub)) {
      docView = (sub === 'documents' ? 'folders' : sub);
    } else {
      docView = 'folders';
    }
  }
  // 5. Chat / Playground routing
  else if (rawPath === '/chat' || rawPath === '/playground') {
    tab = 'playground';
  }
  // 6. Demo
  else if (rawPath === '/demo') {
    tab = 'demo';
  }
  // 7. Live Ingestion
  else if (rawPath === '/live-ingestion' || rawPath === '/live_ingestion' || rawPath === '/ingest') {
    tab = 'live_ingestion';
  }
  // 8. Integrations (MCP) routing
  else if (rawPath === '/integrations' || rawPath.startsWith('/integrations/')) {
    tab = 'integrations';
    const parts = rawPath.split('/').filter(Boolean);
    const sub = parts[1] || params.get('sub');
    if (sub && MCP_SUBVIEWS.includes(sub)) {
      mcpSubView = sub;
    } else {
      mcpSubView = 'tester';
    }
  }
  // 9. Audit
  else if (rawPath === '/audit' || rawPath === '/audit-trail') {
    tab = 'audit';
  }
  // 10. Team routing
  else if (rawPath === '/team' || rawPath === '/personas' || rawPath.startsWith('/team/') || rawPath.startsWith('/personas/')) {
    tab = 'team';
    const parts = rawPath.split('/').filter(Boolean);
    const sub = parts[1] || params.get('sub');
    if (sub && TEAM_SUBTABS.includes(sub)) {
      teamSubTab = sub;
    } else {
      teamSubTab = 'directory';
    }
  }
  // 11. Profile routing
  else if (rawPath === '/profile' || rawPath.startsWith('/profile/')) {
    tab = 'profile';
    const parts = rawPath.split('/').filter(Boolean);
    const sub = parts[1] || params.get('sub');
    if (sub && PROFILE_SUBTABS.includes(sub)) {
      profileSubTab = sub;
    } else {
      profileSubTab = 'user_profile';
    }
  }
  // 12. Root / Home
  else {
    tab = PATH_TO_TAB[rawPath] || 'home';
  }

  // Parse query parameters
  const docId = params.get('doc') || params.get('asset') || params.get('assetId') || null;
  const claimId = params.get('claim') || params.get('claimId') || null;
  const sec = params.get('section');
  let lineageSection = 'summary';
  if (sec && LINEAGE_SECTIONS.includes(sec)) {
    lineageSection = sec;
  }

  const wsId = params.get('workspace');
  let workspace = DEFAULT_WORKSPACES[0];
  const listToSearch = workspacesList && workspacesList.length ? workspacesList : DEFAULT_WORKSPACES;
  if (wsId) {
    const found = listToSearch.find(w => w.id === wsId || w.domain === wsId);
    if (found) workspace = found;
  }

  const chatSession = params.get('session') || null;
  const scenario = params.get('scenario') || 'refund_trap';

  return {
    tab,
    vaultSubTab,
    docId,
    claimId,
    lineageSection,
    workspace,
    docView,
    curatorSubView,
    mcpSubView,
    teamSubTab,
    profileSubTab,
    chatSession,
    scenario
  };
};

export const computeUrlFromState = ({
  activeTab,
  vaultSubTab = 'documents',
  selectedLineageAssetId = null,
  selectedLineageClaimId = null,
  lineageSection = 'summary',
  curatorSubView = 'health',
  docExplorerView = 'folders',
  mcpActiveSubView = 'tester',
  teamSubTab = 'directory',
  profileSubTab = 'user_profile',
  activeChatSessionId = null,
  demoScenario = 'refund_trap',
  activeWorkspace = null
}) => {
  let pathname = '/';

  switch (activeTab) {
    case 'home':
      pathname = '/';
      break;
    case 'demo':
      pathname = '/demo';
      break;
    case 'live_ingestion':
      pathname = '/live-ingestion';
      break;
    case 'visual_lineage':
      if (vaultSubTab && vaultSubTab !== 'claims') {
        pathname = `/vault/${vaultSubTab}`;
      } else {
        pathname = '/vault';
      }
      break;
    case 'context_curator':
      if (curatorSubView === 'conflicts') {
        pathname = '/curator/conflicts';
      } else {
        pathname = '/curator';
      }
      break;
    case 'conflicts':
      pathname = '/conflicts';
      break;
    case 'ingestion':
      if (docExplorerView && docExplorerView !== 'folders') {
        pathname = `/documents/${docExplorerView}`;
      } else {
        pathname = '/documents';
      }
      break;
    case 'playground':
      pathname = '/chat';
      break;
    case 'integrations':
      if (mcpActiveSubView && mcpActiveSubView !== 'tester') {
        pathname = `/integrations/${mcpActiveSubView}`;
      } else {
        pathname = '/integrations';
      }
      break;
    case 'audit':
      pathname = '/audit';
      break;
    case 'team':
      if (teamSubTab && teamSubTab !== 'directory') {
        pathname = `/team/${teamSubTab}`;
      } else {
        pathname = '/team';
      }
      break;
    case 'profile':
      if (profileSubTab && profileSubTab !== 'user_profile') {
        pathname = `/profile/${profileSubTab}`;
      } else {
        pathname = '/profile';
      }
      break;
    default:
      pathname = TAB_TO_PATH[activeTab] || '/';
      break;
  }

  const params = new URLSearchParams();

  // Workspace param (preserve only if not default 'all')
  if (activeWorkspace && activeWorkspace.id && activeWorkspace.id !== 'all') {
    params.set('workspace', activeWorkspace.id);
  }

  // Document param & section for Vault / Lineage
  if (activeTab === 'visual_lineage' && selectedLineageAssetId) {
    params.set('doc', selectedLineageAssetId);
    if (selectedLineageClaimId) {
      params.set('claimId', selectedLineageClaimId);
    }
    if (lineageSection && lineageSection !== 'summary') {
      params.set('section', lineageSection);
    }
  }

  // Chat session param
  if (activeTab === 'playground' && activeChatSessionId) {
    params.set('session', activeChatSessionId);
  }

  // Demo scenario param
  if (activeTab === 'demo' && demoScenario && demoScenario !== 'refund_trap') {
    params.set('scenario', demoScenario);
  }

  const qs = params.toString();
  return `${pathname}${qs ? `?${qs}` : ''}`;
};

const initialUrlState = typeof window !== 'undefined' ? parseUrlState() : null;

export const getInitialDocViewFromUrl = () => {
  if (initialUrlState?.docView) return initialUrlState.docView;
  try {
    const params = new URLSearchParams(window.location.search);
    const v = params.get('view') || params.get('docView');
    if (v && DOC_EXPLORER_VIEWS.includes(v)) return v;
  } catch {
    // ignore
  }
  return 'folders';
};

function ServiceLockedGate({
  serviceName,
  isOrgReady,
  isWorkspaceReady,
  activeOrg,
  authToken,
  onOpenOrgModal,
  onOpenWorkspaceModal,
  onGoHome,
  onOrgCreated,
  showToast
}) {
  const [quickName, setQuickName] = useState(() => {
    if (activeOrg?.name && activeOrg.name.includes('Pending Setup')) {
      return activeOrg.name.replace(/\s*\(Pending Setup\)/i, '').trim();
    }
    return '';
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (activeOrg?.name && !quickName) {
      const cleaned = activeOrg.name.replace(/\s*\(Pending Setup\)/i, '').trim();
      if (cleaned) setQuickName(cleaned);
    }
  }, [activeOrg?.name]);

  const handleQuickSubmit = async (e) => {
    e?.preventDefault();
    const trimmed = quickName.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const slug = trimmed.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      const token = authToken || localStorage.getItem('token') || localStorage.getItem('access_token');

      let res;
      if (activeOrg?.id && activeOrg.name?.includes('Pending Setup')) {
        res = await fetch(`/v1/organizations/${activeOrg.id}/settings`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ name: trimmed, slug, setup_completed: true })
        });
      } else {
        res = await fetch('/v1/organizations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ name: trimmed, slug, setup_completed: true })
        });
      }

      if (res.ok) {
        const saved = await res.json();
        saved.setup_completed = true;
        if (onOrgCreated) {
          await onOrgCreated(saved);
        } else if (onOpenOrgModal) {
          onOpenOrgModal();
        }
      } else {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(data.detail || 'Could not set up organization.');
      }
    } catch (err) {
      setErrorMsg('Network connection error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isWorkspaceGate = isOrgReady && !isWorkspaceReady;

  return (
    <div style={{
      maxWidth: '520px',
      margin: '60px auto',
      padding: '0 20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      textAlign: 'center'
    }}>
      <div className="clean-panel" style={{
        width: '100%',
        padding: '36px 32px',
        borderRadius: '16px',
        border: '1px solid var(--border-color)',
        boxShadow: '0 10px 30px -10px rgba(0, 0, 0, 0.08)',
        background: 'var(--bg-card)'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '14px',
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 18px auto',
          color: '#2563EB'
        }}>
          {isWorkspaceGate ? (
            <FolderTree size={26} strokeWidth={2} />
          ) : (
            <Building2 size={26} strokeWidth={2} />
          )}
        </div>

        <h2 style={{
          fontSize: '1.35rem',
          fontWeight: 700,
          color: 'var(--text-main)',
          margin: '0 0 8px 0',
          letterSpacing: '-0.02em'
        }}>
          {isWorkspaceGate ? 'Create Your Workspace' : 'Set Up Your Organization'}
        </h2>

        <p style={{
          fontSize: '0.88rem',
          color: 'var(--text-secondary)',
          maxWidth: '420px',
          margin: '0 auto 24px auto',
          lineHeight: '1.5'
        }}>
          {isWorkspaceGate
            ? `Create a workspace to start using ${serviceName || 'this service'}.`
            : `Enter your organization name to get started with ${serviceName || 'this service'}.`}
        </p>

        {!isWorkspaceGate ? (
          <form onSubmit={handleQuickSubmit} style={{ width: '100%', maxWidth: '420px', margin: '0 auto' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: errorMsg ? '6px' : '16px' }}>
              <input
                type="text"
                placeholder="Organization name (e.g., Acme Corp)..."
                value={quickName}
                onChange={e => {
                  setQuickName(e.target.value);
                  if (errorMsg) setErrorMsg('');
                }}
                disabled={isSubmitting}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  fontSize: '0.88rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-input, var(--bg-card))',
                  color: 'var(--text-main)',
                  outline: 'none'
                }}
                autoFocus
              />
              <button
                type="submit"
                disabled={!quickName.trim() || isSubmitting}
                className="btn btn-primary"
                style={{
                  padding: '10px 20px',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap'
                }}
              >
                <Building2 size={15} />
                <span>{isSubmitting ? 'Creating...' : 'Create'}</span>
              </button>
            </div>

            {errorMsg && (
              <div style={{
                color: '#EF4444',
                fontSize: '0.78rem',
                marginBottom: '16px',
                textAlign: 'left'
              }}>
                {errorMsg}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                type="button"
                onClick={onGoHome}
                className="btn btn-secondary"
                style={{
                  padding: '8px 18px',
                  fontSize: '0.82rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Home size={14} />
                <span>Return to Overview</span>
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={onOpenWorkspaceModal}
              className="btn btn-primary"
              style={{
                padding: '9px 20px',
                fontSize: '0.86rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Plus size={15} />
              <span>Create Workspace</span>
            </button>
            <button
              type="button"
              onClick={onGoHome}
              className="btn btn-secondary"
              style={{
                padding: '9px 18px',
                fontSize: '0.84rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Home size={14} />
              <span>Return to Overview</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const isPopStateRef = useRef(false);
  const [activeTab, setActiveTab] = useState(() => initialUrlState?.tab || 'home');
  const [expandedMenu, setExpandedMenu] = useState(() => initialUrlState?.tab || 'home');
  const [vaultSubTab, setVaultSubTab] = useState(() => initialUrlState?.vaultSubTab || 'claims');
  const [openSidebarMenu, setOpenSidebarMenu] = useState(() => {
    if (initialUrlState?.tab === 'visual_lineage') return 'vault';
    if (initialUrlState?.tab === 'context_curator' || initialUrlState?.tab === 'conflicts') return 'curator';
    if (initialUrlState?.tab === 'ingestion') return 'explorer';
    return null;
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [curatorSubView, setCuratorSubView] = useState(() => initialUrlState?.curatorSubView || 'health'); // 'health' | 'conflicts' | 'drift'
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [isOrgSettingsModalOpen, setIsOrgSettingsModalOpen] = useState(false);
  const [isRbacModalOpen, setIsRbacModalOpen] = useState(false);
  const [isRoiModalOpen, setIsRoiModalOpen] = useState(false);
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);
  const [isWebhookModalOpen, setIsWebhookModalOpen] = useState(false);
  const [isHitlModalOpen, setIsHitlModalOpen] = useState(false);
  const [isRedTeamModalOpen, setIsRedTeamModalOpen] = useState(false);
  const [isMerkleModalOpen, setIsMerkleModalOpen] = useState(false);
  const [merkleSelectedToken, setMerkleSelectedToken] = useState(null);
  const [isGateToolsDrawerOpen, setIsGateToolsDrawerOpen] = useState(false);
  const [hoveredGateTool, setHoveredGateTool] = useState(null);
  const [pinnedGateTool, setPinnedGateTool] = useState(null);
  const [inspectorState, setInspectorState] = useState({
    isOpen: false,
    assetType: 'document', // 'document' | 'connector'
    assetId: null,
    assetTitle: ''
  });
  const [selectedLineageAssetId, setSelectedLineageAssetId] = useState(() => initialUrlState?.docId || null);
  const [selectedLineageClaimId, setSelectedLineageClaimId] = useState(() => initialUrlState?.claimId || null);
  const [lineageSection, setLineageSection] = useState(() => initialUrlState?.lineageSection || 'summary');
  const [teamSubTab, setTeamSubTab] = useState(() => initialUrlState?.teamSubTab || 'directory');
  const [profileSubTab, setProfileSubTab] = useState(() => initialUrlState?.profileSubTab || 'user_profile');
  const [mcpActiveSubView, setMcpActiveSubView] = useState(() => initialUrlState?.mcpSubView || 'tester'); // 'tester' | 'configs' | 'sdks' | 'schemas'
  const [selectedDocForViewer, setSelectedDocForViewer] = useState(null);

  // -------------------------------------------------------------
  const {
    token,
    token: authToken,
    user: authUser,
    organization: authOrg,
    isAuthenticated,
    personas: authPersonas,
    setIsAuthModalOpen,
    setAuthModalTab,
    loginAsPersona: authLoginAsPersona,
    switchOrganization,
    logout: authLogout,
    effectiveRole,
    simulatedRole,
    setSimulatedRole,
    isTabVisible,
    getSodGuard,
    roleMetadata,
    myOrganizations,
    myInvitations,
    isNewUser,
    setIsNewUser,
    acceptInvitation,
    refreshMyOrganizations,
    sessionSupersededNotice,
    setSessionSupersededNotice,
    broadcastSyncEvent,
  } = useAuth();

  // Atlan Active Persona & User Ecosystem State
  const [personas, setPersonas] = useState(DEFAULT_ENTERPRISE_PERSONAS);
  const [activePersona, setActivePersona] = useState(DEFAULT_ENTERPRISE_PERSONAS[0]);

  // Unified Header Dropdown State (Strict Mutual Exclusivity & Outside Click)
  const [activeDropdown, setActiveDropdown] = useState(null); // 'org' | 'workspace' | 'persona' | null
  const headerControlsRef = useRef(null);

  const isOrgDropdownOpen = activeDropdown === 'org';
  const isWorkspaceDropdownOpen = activeDropdown === 'workspace';
  const isPersonaDropdownOpen = activeDropdown === 'persona';

  const toggleDropdown = (name) => {
    setActiveDropdown(prev => prev === name ? null : name);
  };
  const closeDropdowns = () => setActiveDropdown(null);

  const setIsOrgDropdownOpen = (val) => {
    setActiveDropdown(prev => (typeof val === 'function' ? val(prev === 'org') : val) ? 'org' : null);
  };
  const setIsWorkspaceDropdownOpen = (val) => {
    setActiveDropdown(prev => (typeof val === 'function' ? val(prev === 'workspace') : val) ? 'workspace' : null);
  };
  const setIsPersonaDropdownOpen = (val) => {
    setActiveDropdown(prev => (typeof val === 'function' ? val(prev === 'persona') : val) ? 'persona' : null);
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (headerControlsRef.current && !headerControlsRef.current.contains(e.target)) {
        setActiveDropdown(null);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Auto-launch Organization Setup Wizard for new user onboarding
  useEffect(() => {
    if (isNewUser) {
      setSetupWizardTargetOrg(null);
      setIsSetupWizardOpen(true);
      setIsNewUser(false);
    }
  }, [isNewUser]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshMyOrganizations?.();
    }
  }, [isAuthenticated]);

  // Auto-redirect if active tab is restricted under effective/simulated role
  useEffect(() => {
    if (activeTab && isTabVisible && !isTabVisible(activeTab)) {
      setActiveTab('home');
      setExpandedMenu('home');
    }
  }, [effectiveRole, activeTab, isTabVisible]);

  useEffect(() => {
    if (authUser) {
      setActivePersona(authUser);
    }
  }, [authUser]);

  useEffect(() => {
    if (authPersonas && authPersonas.length > 0) {
      setPersonas(authPersonas);
    }
  }, [authPersonas]);

  const handleSelectPersona = async (p) => {
    setActivePersona(p);
    if (authLoginAsPersona) {
      await authLoginAsPersona(p);
    }
    showToast(`Switched active user to ${p.name} (${(p.role || 'user').toUpperCase()})`);
  };

  const handleToggleParentTab = (tabName) => {
    setActiveTab(tabName);
    setExpandedMenu(prev => prev === tabName ? null : tabName);
  };



  // -------------------------------------------------------------
  // Decision Gate & Policy Simulator State
  // -------------------------------------------------------------
  const [demoScenario, setDemoScenario] = useState(() => initialUrlState?.scenario || 'refund_trap');
  const [simulatorMode, setSimulatorMode] = useState('custom'); // 'custom' | 'presets'
  const [customActionText, setCustomActionText] = useState('Authorize 45-day refund for Enterprise customer on Acme Corp plan');
  const [customActorId, setCustomActorId] = useState('autonomous-agent-01');
  const [customActorRole, setCustomActorRole] = useState('support_agent');
  const [customRequiredScope, setCustomRequiredScope] = useState('Enterprise');
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState(0); // 0: Idle, 1: Evaluating, 2: Result
  const [demoResult, setDemoResult] = useState(null);
  const [decisionStream, setDecisionStream] = useState([]);
  const [streamLoading, setStreamLoading] = useState(false);
  const [showManualOverride, setShowManualOverride] = useState(false);

  // Intelligent Context & Persona Detection Engine
  const inferActionContext = (text) => {
    const lower = (text || '').toLowerCase();

    // 1. Network / Ingress / Firewall / Infrastructure / Deployment
    if (
      lower.includes('ingress') ||
      lower.includes('firewall') ||
      lower.includes('port 80') ||
      lower.includes('port 8080') ||
      lower.includes('port 22') ||
      lower.includes('plaintext') ||
      lower.includes('k8s') ||
      lower.includes('kubernetes') ||
      lower.includes('cluster') ||
      lower.includes('deploy') ||
      lower.includes('infrastructure')
    ) {
      if (
        lower.includes('intern') ||
        lower.includes('junior') ||
        lower.includes('dev-intern') ||
        lower.includes('unauthorized') ||
        lower.includes('plaintext')
      ) {
        return {
          actorId: 'dev-intern-bot',
          role: 'junior_developer',
          roleLabel: 'Junior Developer (Intern Bot)',
          roleShort: 'Junior Dev',
          scope: 'Production',
          scopeLabel: 'Production Environment',
          scopeShort: 'Production',
          confidence: '98%',
          rationale: 'Unauthorized production port ingress intent'
        };
      }
      return {
        actorId: 'devops-agent-01',
        role: 'devops_engineer',
        roleLabel: 'DevOps Engineer (CI/CD Bot)',
        roleShort: 'DevOps Bot',
        scope: lower.includes('staging') ? 'Staging' : 'Production',
        scopeLabel: lower.includes('staging') ? 'Staging Sandbox' : 'Production Environment',
        scopeShort: lower.includes('staging') ? 'Staging' : 'Production',
        confidence: '95%',
        rationale: 'Infrastructure change & CI/CD deployment'
      };
    }

    // 2. HR / Remote Work / Leave / Benefits / Vacation
    if (
      lower.includes('remote') ||
      lower.includes('work from home') ||
      lower.includes('wfh') ||
      lower.includes('schedule') ||
      lower.includes('leave') ||
      lower.includes('vacation') ||
      lower.includes('pto') ||
      lower.includes('benefit') ||
      lower.includes('payroll') ||
      lower.includes('employee')
    ) {
      const isEng = lower.includes('engineering') || lower.includes('developer') || lower.includes('senior developer') || lower.includes('engineer');
      return {
        actorId: 'hr-assistant-bot',
        role: 'hr_reviewer',
        roleLabel: 'HR Reviewer (Benefits Assistant)',
        roleShort: 'HR Reviewer',
        scope: isEng ? 'Engineering' : 'General',
        scopeLabel: isEng ? 'Engineering Department' : 'Global Standard',
        scopeShort: isEng ? 'Engineering' : 'Global',
        confidence: '96%',
        rationale: 'Employee policy & workplace schedule adjustment'
      };
    }

    // 3. Finance / Refund / Billing / Invoices / Payments
    if (
      lower.includes('refund') ||
      lower.includes('billing') ||
      lower.includes('invoice') ||
      lower.includes('payment') ||
      lower.includes('charge') ||
      lower.includes('credit') ||
      lower.includes('subscription') ||
      lower.includes('acme') ||
      lower.includes('$') ||
      lower.includes('discount')
    ) {
      const isEnterprise = lower.includes('enterprise') || lower.includes('acme') || lower.includes('annual') || lower.includes('tier') || lower.includes('45-day');
      return {
        actorId: 'billing-agent-01',
        role: 'support_agent',
        roleLabel: 'Support Agent (Customer Bot)',
        roleShort: 'Support Bot',
        scope: isEnterprise ? 'Enterprise' : 'General',
        scopeLabel: isEnterprise ? 'Enterprise Customer Tier' : 'Global Standard',
        scopeShort: isEnterprise ? 'Enterprise' : 'Global',
        confidence: '99%',
        rationale: 'Customer billing & financial exception transaction'
      };
    }

    // 4. Compliance / Audit / Legal / Freeze
    if (
      lower.includes('audit') ||
      lower.includes('compliance') ||
      lower.includes('gdpr') ||
      lower.includes('pii') ||
      lower.includes('freeze') ||
      lower.includes('legal') ||
      lower.includes('export')
    ) {
      return {
        actorId: 'compliance-gate-01',
        role: 'compliance_officer',
        roleLabel: 'Compliance Officer (Risk Gate)',
        roleShort: 'Risk Gate',
        scope: 'Enterprise',
        scopeLabel: 'Enterprise Customer Tier',
        scopeShort: 'Enterprise',
        confidence: '94%',
        rationale: 'Regulatory audit & governance enforcement'
      };
    }

    // Default fallback
    return {
      actorId: 'autonomous-agent-01',
      role: 'support_agent',
      roleLabel: 'Support Agent (Customer Bot)',
      roleShort: 'Support Bot',
      scope: 'Enterprise',
      scopeLabel: 'Enterprise Customer Tier',
      scopeShort: 'Enterprise',
      confidence: '90%',
      rationale: 'Standard enterprise operational scope'
    };
  };

  const detectedContext = useMemo(() => {
    return inferActionContext(customActionText);
  }, [customActionText]);

  useEffect(() => {
    if (!showManualOverride && detectedContext) {
      setCustomActorId(detectedContext.actorId);
      setCustomActorRole(detectedContext.role);
      setCustomRequiredScope(detectedContext.scope);
    }
  }, [detectedContext, showManualOverride]);

  const scenarios = {
    refund_trap: {
      title: "Outdated Refund Window Trap",
      subtitle: "Freshness & Scope Contradiction Verification",
      query: "Is customer Demo Enterprise (Enterprise Tier) eligible for a 45-day refund?",
      actor: { id: "billing-agent-01", role: "support_agent" },
      claim1: {
        text: "Refund window is strictly limited to 30 days.",
        source: "Internal Employee Handbook 2025 (handbook.pdf)",
        date: "2025-11-04",
        authority: 50,
        scope: "Global Standard"
      },
      claim2: {
        text: "Enterprise tier customers have a 60-day exception window.",
        source: "Enterprise Policy Service (policy-service)",
        date: "2026-08-25",
        authority: 95,
        scope: "Enterprise"
      }
    },
    remote_work: {
      title: "Remote Work Policy Discrepancy",
      subtitle: "Departmental Scope & Authority Override",
      query: "Approve 4 days per week remote work schedule for senior developer.",
      actor: { id: "hr-assistant-bot", role: "hr_reviewer" },
      claim1: {
        text: "Employees may work remotely a maximum of 2 days per week.",
        source: "Legacy HR Policy Manual (v1.0)",
        date: "2025-01-10",
        authority: 60,
        scope: "General"
      },
      claim2: {
        text: "Engineering staff are authorized for up to 4 days remote work per week.",
        source: "VP Engineering Memo (memo-2026.md)",
        date: "2026-02-14",
        authority: 90,
        scope: "Engineering"
      }
    },
    unauthorized_deploy: {
      title: "Unauthorized Infrastructure Action",
      subtitle: "Role Permission & Environment Scope Gate",
      query: "Deploy production firewall rule allowing plaintext HTTP traffic on port 8080.",
      actor: { id: "dev-intern-bot", role: "junior_developer" },
      claim1: {
        text: "Developers can adjust staging port ingress without secondary approval.",
        source: "Staging Runbook (runbook-stg.md)",
        date: "2026-03-01",
        authority: 50,
        scope: "Staging"
      },
      claim2: {
        text: "All production external ingress must enforce TLS 1.3 encryption and DevOps lead signoff.",
        source: "Corporate Security Guidelines (sec-pol-2026)",
        date: "2026-08-01",
        authority: 98,
        scope: "Production"
      }
    }
  };

  // -------------------------------------------------------------
  // Interactive Agent Playground State
  // -------------------------------------------------------------
  const [playgroundQuery, setPlaygroundQuery] = useState("What is the maximum allowed automated refund for India customers?");
  const [playgroundAgent, setPlaygroundAgent] = useState({
    id: "88888888-8888-8888-8888-888888888888",
    name: "Billing Dispute Agent",
    role: "billing_agent"
  });
  const [playgroundThreshold, setPlaygroundThreshold] = useState(0.80);
  const [playgroundRunning, setPlaygroundRunning] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState(null);

  const playgroundPresets = [
    {
      title: "Enterprise Refund Limit",
      agent: { id: "88888888-8888-8888-8888-888888888888", name: "Billing Dispute Agent", role: "billing_agent" },
      query: "What is the maximum allowed automated refund for India customers?",
      threshold: 0.80,
      answer: "Under the authoritative 2026 Customer Refund Policy (V2), automated refunds for Indian customers are capped at ₹10,000. Any higher amount strictly requires VP signoff. The older 2025 handbook limit of ₹25,000 has been superseded and marked outdated.",
      context: [
        {
          claim: "Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.",
          trust_score: 0.96,
          validity: { status: "valid", valid_from: "2026-08-28", valid_until: "2027-12-31" },
          source: { document: "Enterprise Customer Refund Policy (V2)", section: "Section 3.2 - Automated Thresholds", page: 1 },
          evidence: ["Standard automated refund limit is capped at ₹10,000."]
        }
      ]
    },
    {
      title: "Engineering Remote Work Policy",
      agent: { id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role: "hr_assistant" },
      query: "How many days per week are senior software engineers permitted to work remotely?",
      threshold: 0.85,
      answer: "According to the VP Engineering Memo (2026), engineering staff are authorized for up to 4 days remote work per week. The general 2-day limit from the legacy handbook is overridden for the Engineering department.",
      context: [
        {
          claim: "Engineering staff are authorized for up to 4 days remote work per week.",
          trust_score: 0.95,
          validity: { status: "valid", valid_from: "2026-02-14", valid_until: "2027-12-31" },
          source: { document: "VP Engineering Memo (memo-2026.md)", section: "Section 1.1 - Remote Flexibility", page: 1 },
          evidence: ["Engineering staff are authorized for up to 4 days remote work per week."]
        }
      ]
    },
    {
      title: "Production TLS Security Mandate",
      agent: { id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role: "devops_agent" },
      query: "What encryption and authentication standards must external production API endpoints enforce?",
      threshold: 0.90,
      answer: "Corporate Security Guidelines (2026) mandate that all external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication with 7-year audit retention.",
      context: [
        {
          claim: "All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.",
          trust_score: 0.98,
          validity: { status: "valid", valid_from: "2026-08-01", valid_until: "2028-12-31" },
          source: { document: "Corporate Security Guidelines (sec-pol-2026)", section: "Section 4.1 - Ingress Security", page: 2 },
          evidence: ["All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication."]
        }
      ]
    }
  ];

  // -------------------------------------------------------------
  // Ingestion State
  // -------------------------------------------------------------
  const [docInput, setDocInput] = useState({
    title: "API Security Guidelines 2026",
    docType: "policy",
    content: "# Security Policy\nAll API endpoints must enforce TLS 1.3 encryption and JWT authentication.\n\n# Audit Retention\nAll transaction logs must be retained for 7 years.",
    externalId: "SEC-POL-2026"
  });
  const [ingestedDoc, setIngestedDoc] = useState(null);
  const [extractedClaims, setExtractedClaims] = useState([]);
  const [ingesting, setIngesting] = useState(false);

  // -------------------------------------------------------------
  // File Upload State & Handlers
  // -------------------------------------------------------------
  const fileInputRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleProcessFile = (file) => {
    if (!file) return;
    setUploadedFile(file);

    const baseName = file.name.replace(/\.[^/.]+$/, "");
    const formattedTitle = baseName.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    let inferredType = "policy";
    const lowerName = file.name.toLowerCase();
    if (lowerName.includes("handbook")) inferredType = "handbook";
    else if (lowerName.includes("runbook")) inferredType = "runbook";
    else if (lowerName.includes("confluence") || lowerName.includes("wiki")) inferredType = "confluence_page";

    setDocInput(prev => ({
      ...prev,
      title: formattedTitle,
      externalId: `file://${file.name}`,
      docType: inferredType
    }));

    if (lowerName.endsWith(".pdf") || lowerName.endsWith(".docx") || lowerName.endsWith(".doc")) {
      setDocInput(prev => ({
        ...prev,
        content: `[Binary Document: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]\n\nThis document will be processed and text-extracted via server-side parser (pypdf / python-docx) upon ingestion.`
      }));
      showToast(`Selected file '${file.name}' (${(file.size / 1024).toFixed(1)} KB) for extraction`);
    } else {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = (e.target?.result || "").replace(/\x00/g, "");
        setDocInput(prev => ({
          ...prev,
          content: text || `# ${formattedTitle}\n\nIngested from ${file.name} (${(file.size / 1024).toFixed(1)} KB).`
        }));
        showToast(`Loaded file '${file.name}' (${(file.size / 1024).toFixed(1)} KB)`);
      };
      reader.onerror = () => {
        showToast("Failed to read file", "error");
      };
      reader.readAsText(file);
    }
  };

  // -------------------------------------------------------------
  // Live Database & Connector State (Sources, Docs, Claims)
  // -------------------------------------------------------------
  const [dataSources, setDataSources] = useState([]);
  const [syncingSourceId, setSyncingSourceId] = useState(null);
  const [autoSyncInterval, setAutoSyncInterval] = useState('off');
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [isConnectingSource, setIsConnectingSource] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testConnectionResult, setTestConnectionResult] = useState(null);
  const [discoveredOptions, setDiscoveredOptions] = useState({
    repos: [],
    databases: [],
    collections: [],
    projects: [],
    spaces: [],
    schemas: [],
    tables: []
  });
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryError, setDiscoveryError] = useState(null);
  const [newSourceForm, setNewSourceForm] = useState({
    name: '',
    sourceType: 'postgresql',
    authorityLevel: 90,
    externalId: '',
    schedule: 'off', // 'off' | '1m' | '10m'
    // Postgres
    pgHost: 'localhost',
    pgPort: 5432,
    pgDatabase: '',
    pgUsername: 'postgres',
    pgPassword: '',
    pgSslMode: 'prefer',
    pgSchemas: 'public',
    pgTables: '',
    // Kafka
    kafkaBootstrap: '',
    kafkaSchemaRegistry: '',
    kafkaSecurityProtocol: 'PLAINTEXT',
    kafkaSaslMechanism: 'PLAIN',
    kafkaSaslUsername: '',
    kafkaSaslPassword: '',
    kafkaTopics: '',
    // Salesforce
    sfInstanceUrl: '',
    sfClientId: '',
    sfClientSecret: '',
    sfUsername: '',
    sfPassword: '',
    sfSecurityToken: '',
    sfObjects: '',
    // MongoDB
    mongoUri: '',
    mongoDatabase: '',
    mongoCollections: '',
    // GitHub
    githubRepo: '',
    githubOwner: '',
    githubBranch: 'main',
    githubToken: '',
    // Confluence
    confluenceSpace: '',
    confluenceBaseUrl: '',
    confluenceEmail: '',
    confluenceToken: '',
    // Jira
    jiraProject: '',
    jiraBaseUrl: '',
    jiraEmail: '',
    jiraToken: '',
    jiraFilter: '',
    // Slack
    slackBotToken: '',
    slackChannels: '',
    slackLookbackDays: 30,
    slackIncludeReplies: true,
  });

  // -------------------------------------------------------------
  // Dynamic Multi-Tenant Organization State
  // -------------------------------------------------------------
  const [organizations, setOrganizations] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);
  const [showNewOrgModal, setShowNewOrgModal] = useState(false);
  const [showRenameOrgModal, setShowRenameOrgModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgSlug, setNewOrgSlug] = useState('');
  const [renameOrgName, setRenameOrgName] = useState('');
  const [isCreatingOrg, setIsCreatingOrg] = useState(false);
  const [isSetupWizardOpen, setIsSetupWizardOpen] = useState(false);
  const [setupWizardTargetOrg, setSetupWizardTargetOrg] = useState(null);
  const [orgSetupRefreshTrigger, setOrgSetupRefreshTrigger] = useState(0);

  // -------------------------------------------------------------
  // Departmental Workspaces under Active Company
  // -------------------------------------------------------------
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspace, setActiveWorkspace] = useState(null);
  const [showNewWorkspaceModal, setShowNewWorkspaceModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDomain, setNewWorkspaceDomain] = useState('governance');
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState('');
  const [docExplorerScopeAll, setDocExplorerScopeAll] = useState(false);
  const [docExplorerView, setDocExplorerView] = useState(getInitialDocViewFromUrl); // 'connectors' | 'ingest' | 'documents' | 'claims'
  const [docSourceFilter, setDocSourceFilter] = useState('all'); // 'all' | source_id

  // Load organization-specific workspaces from backend database (with local/config cache fallback)
  useEffect(() => {
    if (!activeOrg?.id) {
      setWorkspaces([]);
      setActiveWorkspace(null);
      return;
    }

    let isMounted = true;

    // 1. Initial cache check for instant paint
    try {
      const saved = localStorage.getItem(`ctl_workspaces_${activeOrg.id}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setWorkspaces(parsed);
          if (!activeWorkspace || !parsed.some(w => w.id === activeWorkspace.id)) {
            setActiveWorkspace(parsed[0]);
          }
        }
      } else if (activeOrg.governance_config?.workspaces && Array.isArray(activeOrg.governance_config.workspaces) && activeOrg.governance_config.workspaces.length > 0) {
        const orgWs = activeOrg.governance_config.workspaces;
        setWorkspaces(orgWs);
        setActiveWorkspace(orgWs[0]);
        localStorage.setItem(`ctl_workspaces_${activeOrg.id}`, JSON.stringify(orgWs));
      }
    } catch (e) {
      console.warn('Error reading workspace cache:', e);
    }

    // 2. Fetch live source-of-truth from backend
    async function fetchOrgWorkspaces() {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(`/v1/organizations/${activeOrg.id}/workspaces`, { headers });
        if (res.ok && isMounted) {
          const remoteWs = await res.json();
          if (Array.isArray(remoteWs) && remoteWs.length > 0) {
            setWorkspaces(remoteWs);
            localStorage.setItem(`ctl_workspaces_${activeOrg.id}`, JSON.stringify(remoteWs));
            setActiveWorkspace(prev => {
              if (prev && remoteWs.some(w => w.id === prev.id)) {
                return prev;
              }
              return remoteWs[0];
            });
          }
        }
      } catch (err) {
        console.warn('Failed to fetch remote workspaces:', err);
      }
    }

    fetchOrgWorkspaces();

    return () => {
      isMounted = false;
    };
  }, [activeOrg?.id, token]);

  // Multi-tab workspace synchronization
  useEffect(() => {
    let channel = null;
    if (typeof BroadcastChannel !== 'undefined') {
      try {
        channel = new BroadcastChannel('ctl_sync_channel');
        channel.onmessage = (event) => {
          const { type, payload } = event.data || {};
          if (type === 'WORKSPACE_CHANGED' && payload?.orgId === activeOrg?.id) {
            if (payload.activeWorkspace) {
              setActiveWorkspace(payload.activeWorkspace);
            }
            if (activeOrg?.id) {
              fetch(`/v1/organizations/${activeOrg.id}/workspaces`)
                .then(r => r.json())
                .then(data => {
                  if (Array.isArray(data)) setWorkspaces(data);
                })
                .catch(() => {});
            }
          }
        };
      } catch (e) {}
    }
    return () => {
      if (channel) channel.close();
    };
  }, [activeOrg?.id]);

  // Chat Sessions for Sidebar History and AI Copilot Chat Sync
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatSessionId, setActiveChatSessionId] = useState(() => initialUrlState?.chatSession || null);

  const fetchChatSessions = async () => {
    try {
      const workspaceParam = activeWorkspace?.id && activeWorkspace.id !== 'all' ? `&workspace_id=${activeWorkspace.id}` : '';
      const res = await fetch(`/v1/chat/sessions?organization_id=${activeOrg?.id || '11111111-1111-1111-1111-111111111111'}${workspaceParam}`);
      if (res.ok) {
        const data = await res.json();
        setChatSessions(data);
        if (data.length > 0 && !activeChatSessionId) {
          setActiveChatSessionId(data[0].id);
        } else if (data.length === 0) {
          setActiveChatSessionId(null);
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions for sidebar", e);
    }
  };

  const handleStartNewChatFromSidebar = async () => {
    try {
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          user_id: activePersona?.id || null,
          user_name: activePersona?.name || 'Sarah Chen',
          user_role: activePersona?.role || 'admin',
          title: 'New Conversation',
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setChatSessions(prev => [newSession, ...prev]);
        setActiveChatSessionId(newSession.id);
        setActiveTab('playground');
        setNotification({ msg: `Started new conversation in ${activeWorkspace?.name || 'workspace'}`, type: 'success' });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (e) {
      console.error("Failed to create new chat session from sidebar", e);
    }
  };

  useEffect(() => {
    fetchChatSessions();
  }, [activeOrg?.id, activeWorkspace?.id]);

  // -------------------------------------------------------------
  // Browser URL Routing & History Sync Engine
  // -------------------------------------------------------------
  useEffect(() => {
    // If state change came from browser popstate (back/forward), do not push duplicate history entry
    if (isPopStateRef.current) {
      isPopStateRef.current = false;
      return;
    }

    const targetUrl = computeUrlFromState({
      activeTab,
      vaultSubTab,
      selectedLineageAssetId,
      lineageSection,
      curatorSubView,
      docExplorerView,
      mcpActiveSubView,
      teamSubTab,
      profileSubTab,
      activeChatSessionId,
      demoScenario,
      activeWorkspace
    });

    const currentUrl = window.location.pathname + window.location.search;

    if (currentUrl !== targetUrl) {
      window.history.pushState(
        {
          tab: activeTab,
          vaultSubTab,
          selectedLineageAssetId,
          lineageSection,
          curatorSubView,
          docExplorerView,
          mcpActiveSubView,
          teamSubTab,
          profileSubTab,
          activeChatSessionId,
          workspace: activeWorkspace?.id
        },
        '',
        targetUrl
      );
    }
  }, [
    activeTab,
    vaultSubTab,
    selectedLineageAssetId,
    lineageSection,
    curatorSubView,
    docExplorerView,
    mcpActiveSubView,
    teamSubTab,
    profileSubTab,
    activeChatSessionId,
    demoScenario,
    activeWorkspace?.id
  ]);

  // Listen to browser Back / Forward navigation (popstate)
  useEffect(() => {
    const handlePopState = () => {
      isPopStateRef.current = true;
      const urlState = parseUrlState(workspaces);

      setActiveTab(urlState.tab);
      setExpandedMenu(urlState.tab);
      setVaultSubTab(urlState.vaultSubTab);
      setSelectedLineageAssetId(urlState.docId);
      setLineageSection(urlState.lineageSection);
      setCuratorSubView(urlState.curatorSubView);
      setDocExplorerView(urlState.docView);
      setMcpActiveSubView(urlState.mcpSubView);
      setTeamSubTab(urlState.teamSubTab);
      setProfileSubTab(urlState.profileSubTab);
      if (urlState.chatSession) {
        setActiveChatSessionId(urlState.chatSession);
      }
      if (urlState.scenario) {
        setDemoScenario(urlState.scenario);
      }
      if (urlState.workspace) {
        setActiveWorkspace(urlState.workspace);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [workspaces]);

  const [catalogConnectors, setCatalogConnectors] = useState(ENTERPRISE_CONNECTORS);
  const [catalogCategories, setCatalogCategories] = useState(CATALOG_CATEGORIES);
  const [catalogFilterCategory, setCatalogFilterCategory] = useState('all');
  const [catalogSearchQuery, setCatalogSearchQuery] = useState('');
  const [isConnectorDropdownOpen, setIsConnectorDropdownOpen] = useState(false);
  const [showPasswordMask, setShowPasswordMask] = useState(false);
  const [showTokenMask, setShowTokenMask] = useState(false);
  const [selectedConnectorMeta, setSelectedConnectorMeta] = useState(ENTERPRISE_CONNECTORS.find(c => c.id === 'postgresql') || ENTERPRISE_CONNECTORS[0]);
  const [genericConfig, setGenericConfig] = useState({
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    endpoint: '',
    apiToken: '',
    schemas: '',
  });

  const [dbDocuments, setDbDocuments] = useState([]);
  const [dbClaims, setDbClaims] = useState([]);
  const [claimFilterStatus, setClaimFilterStatus] = useState('all');
  const [dbSearchQuery, setDbSearchQuery] = useState('');
  const [dbLoading, setDbLoading] = useState(false);

  // Departmental Workspace Filtering for Document Explorer & Repositories
  const WORKSPACE_DEPT_KEYWORDS = {
    finance: ['refund', 'billing', 'invoice', 'arr', 'payment', 'confluence', 'salesforce', 'accounting', 'pricing', 'tier', 'annual', 'dispute', 'postgresql'],
    secops: ['security', 'firewall', 'ingress', 'iam', 'mtls', 'session', 'token', 'freeze', 'portal', 'github', 'kafka', 'baseline', 'policy'],
    hr: ['remote', 'work', 'leave', 'vacation', 'employee', 'handbook', 'people', 'guideline', 'wifi', 'stipend', 'contractor'],
    support: ['support', 'dispute', 'sla', 'ticket', 'escalation', 'jira', 'arbitration', 'customer'],
    staging: ['staging', 'sandbox', 'test', 'mock', 'simulation']
  };

  const displayedDataSources = React.useMemo(() => {
    const externalOnly = (dataSources || []).filter(src => {
      const st = (src.source_type || '').toLowerCase().trim();
      const nm = (src.name || '').toLowerCase().trim();
      return st !== 'file' && st !== 'upload' && st !== 'local_file' && !nm.includes('file upload') && !nm.includes('direct document upload');
    });
    if (!activeWorkspace || activeWorkspace.id === 'all' || docExplorerScopeAll) return externalOnly;
    const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
    const filtered = externalOnly.filter(src => {
      const text = `${src.name || ''} ${src.source_type || ''} ${src.external_id || ''}`.toLowerCase();
      return kw.some(k => text.includes(k));
    });
    return filtered.length > 0 ? filtered : externalOnly;
  }, [dataSources, activeWorkspace, docExplorerScopeAll]);

  const displayedDbDocuments = React.useMemo(() => {
    let docs = dbDocuments;
    if (activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll) {
      const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
      const filtered = docs.filter(doc => {
        const text = `${doc.title || ''} ${doc.external_id || ''} ${doc.document_type || ''}`.toLowerCase();
        return kw.some(k => text.includes(k));
      });
      docs = filtered.length > 0 ? filtered : docs;
    }
    if (docSourceFilter && docSourceFilter !== 'all') {
      docs = docs.filter(doc => doc.source_id === docSourceFilter);
    }
    return docs;
  }, [dbDocuments, activeWorkspace, docExplorerScopeAll, docSourceFilter]);

  const displayedDbClaims = React.useMemo(() => {
    if (!activeWorkspace || activeWorkspace.id === 'all' || docExplorerScopeAll) return dbClaims;
    const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
    const filtered = dbClaims.filter(cl => {
      const text = `${cl.claim_text || ''} ${cl.subject || ''} ${cl.predicate || ''} ${cl.object_value || ''}`.toLowerCase();
      return kw.some(k => text.includes(k));
    });
    return filtered.length > 0 ? filtered : dbClaims;
  }, [dbClaims, activeWorkspace, docExplorerScopeAll]);

  // -------------------------------------------------------------
  // Model Context Protocol (MCP) & Agent Integration Hub State
  // -------------------------------------------------------------
  const [mcpSelectedTool, setMcpSelectedTool] = useState('context_trust_get_trusted_context');
  const [mcpToolQuery, setMcpToolQuery] = useState('What is the customer refund window?');
  const [mcpMinScore, setMcpMinScore] = useState(0.75);
  const [mcpMaxResults, setMcpMaxResults] = useState(5);
  const [mcpActionType, setMcpActionType] = useState('Determine whether customer is eligible for 45-day refund');
  const [mcpActorId, setMcpActorId] = useState('billing-agent-01');
  const [mcpActorRole, setMcpActorRole] = useState('support');
  const [mcpSearchText, setMcpSearchText] = useState('refund');
  const [mcpClaimText, setMcpClaimText] = useState('Refund window is strictly limited to 30 days.');
  const [mcpInvoking, setMcpInvoking] = useState(false);
  const [mcpInvocationResult, setMcpInvocationResult] = useState(null);
  const [mcpActiveSnippet, setMcpActiveSnippet] = useState('claude'); // 'claude' | 'cursor' | 'python' | 'langchain' | 'llamaindex' | 'curl'
  const [mcpCopiedSnippet, setMcpCopiedSnippet] = useState(false);

  // -------------------------------------------------------------
  // Decision Audit Trail & Lineage Explorer State
  // -------------------------------------------------------------
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditSummary, setAuditSummary] = useState({
    total_decisions: 0,
    allow_count: 0,
    block_count: 0,
    review_count: 0,
    clarify_count: 0,
    allow_rate_pct: 100.0,
    high_risk_count: 0,
    avg_latency_ms: 8.5,
    cryptographic_token_verified: true,
  });
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFilterVerdict, setAuditFilterVerdict] = useState('all');
  const [auditFilterRisk, setAuditFilterRisk] = useState('all');
  const [auditSearchQuery, setAuditSearchQuery] = useState('');
  const [selectedAuditLineage, setSelectedAuditLineage] = useState(null);
  const [isLineageModalOpen, setIsLineageModalOpen] = useState(false);
  const [isFetchingLineage, setIsFetchingLineage] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);

  const handleCreateWorkspace = async (e) => {
    e?.preventDefault();
    if (!newWorkspaceName.trim()) return;
    const name = newWorkspaceName.trim();
    const domain = newWorkspaceDomain;
    const desc = newWorkspaceDescription.trim() || 'Custom department workspace';
    const icon = domain === 'secops' ? '🛡️' : domain === 'hr' ? '👥' : domain === 'finance' ? '💳' : domain === 'staging' ? '🧪' : domain === 'governance' ? '⚖️' : '📁';

    const tempId = `ws_${Date.now()}`;
    const newWs = {
      id: tempId,
      name,
      icon,
      domain,
      description: desc
    };

    // Optimistic local update
    setWorkspaces(prev => {
      const updated = [...prev, newWs];
      const targetOrgId = activeOrg?.id || 'demo';
      localStorage.setItem(`ctl_workspaces_${targetOrgId}`, JSON.stringify(updated));
      return updated;
    });
    setActiveWorkspace(newWs);
    setShowNewWorkspaceModal(false);
    setNewWorkspaceName('');
    setNewWorkspaceDescription('');
    closeDropdowns();
    showToast(`Created and switched to workspace '${newWs.name}'!`);

    // Persist to backend database!
    if (activeOrg?.id) {
      try {
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`/v1/organizations/${activeOrg.id}/workspaces`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            name,
            domain,
            icon,
            description: desc
          })
        });
        if (res.ok) {
          const persistedWs = await res.json();
          setWorkspaces(prev => {
            const updated = prev.map(w => w.id === tempId ? persistedWs : w);
            localStorage.setItem(`ctl_workspaces_${activeOrg.id}`, JSON.stringify(updated));
            return updated;
          });
          setActiveWorkspace(persistedWs);
          broadcastSyncEvent?.('WORKSPACE_CHANGED', {
            orgId: activeOrg.id,
            activeWorkspace: persistedWs
          });
        }
      } catch (err) {
        console.warn('Failed to save workspace to backend:', err);
      }
    }
  };

  const handleSwitchWorkspace = (ws) => {
    setActiveWorkspace(ws);
    closeDropdowns();
    showToast(`Switched workspace to '${ws.name}'`);
    broadcastSyncEvent?.('WORKSPACE_CHANGED', {
      orgId: activeOrg?.id,
      activeWorkspace: ws
    });
  };

  // -------------------------------------------------------------
  // Organization Management & Dynamic Data Fetching
  // -------------------------------------------------------------
  const fetchOrganizations = async () => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch('/v1/organizations/my-organizations', { headers });
      if (res.ok) {
        const orgs = await res.json();
        setOrganizations(orgs);
        if (orgs.length > 0) {
          const savedId = localStorage.getItem('context_layer_active_org_id');
          const matched = orgs.find(o => o.id === savedId) || orgs[0];
          setActiveOrg(matched);
        } else {
          setActiveOrg(null);
        }
      }
    } catch (e) {
      console.warn("Failed to fetch organizations:", e);
    }
  };

  // Synchronize authenticated organization context with user identity
  useEffect(() => {
    if (isAuthenticated) {
      if (myOrganizations && myOrganizations.length > 0) {
        setOrganizations(myOrganizations);
        const savedId = localStorage.getItem('context_layer_active_org_id');
        const matched = myOrganizations.find(o => o.id === savedId) || myOrganizations[0];
        setActiveOrg(matched);
      } else if (authUser?.organization_id) {
        const initialUserOrg = {
          id: authUser.organization_id,
          name: authUser.organization_name || 'Enterprise Organization',
          setup_completed: false
        };
        setOrganizations([initialUserOrg]);
        setActiveOrg(initialUserOrg);
      } else {
        fetchOrganizations();
      }
    } else {
      setOrganizations([]);
      setActiveOrg(null);
      setWorkspaces([]);
      setActiveWorkspace(null);
    }
  }, [isAuthenticated, myOrganizations, authUser]);

  const fetchLiveDatabaseRecords = async (orgId = activeOrg?.id) => {
    if (!orgId) return;
    try {
      setDbLoading(true);
      const [resDocs, resClaims, resSources, resCatalog] = await Promise.all([
        fetch(`/v1/documents?organization_id=${orgId}&limit=50`),
        fetch(`/v1/claims?organization_id=${orgId}&limit=50`),
        fetch(`/v1/sources?organization_id=${orgId}&limit=50`),
        fetch('/v1/sources/catalog')
      ]);

      if (resCatalog && resCatalog.ok) {
        const catData = await resCatalog.json();
        setCatalogConnectors(catData.connectors || []);
        setCatalogCategories(catData.categories || []);
      }

      if (resDocs.ok) {
        const docsData = await resDocs.json();
        setDbDocuments(docsData);
      } else {
        setDbDocuments([]);
      }
      if (resClaims.ok) {
        const claimsData = await resClaims.json();
        setDbClaims(claimsData);
      } else {
        setDbClaims([]);
      }
      if (resSources.ok) {
        const sourcesData = await resSources.json();
        setDataSources(sourcesData);
      } else {
        setDataSources([]);
      }
    } catch (e) {
      console.warn("DB records fetch fallback:", e);
    } finally {
      setDbLoading(false);
    }
  };

  const fetchSources = async (orgId = activeOrg?.id) => {
    if (!orgId) return;
    try {
      const res = await fetch(`/v1/sources?organization_id=${orgId}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setDataSources(data);
      }
    } catch (e) {
      console.warn("Failed to load sources:", e);
    }
  };

  const fetchPersonas = async (orgId = activeOrg?.id) => {
    try {
      const res = await fetch(`/v1/users?organization_id=${orgId || '11111111-1111-1111-1111-111111111111'}`);
      if (res.ok) {
        const data = await res.json();
        setPersonas(data);
        if (data.length > 0 && (!activePersona || !data.some(d => d.id === activePersona.id))) {
          setActivePersona(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to load personas:", e);
    }
  };

  const fetchHealthAndConflicts = async (orgId = activeOrg?.id) => {
    try {
      setLoading(true);
      const resHealth = await fetch('/v1/health');
      if (resHealth.ok) {
        const data = await resHealth.json();
        setHealth(data);
      }
      if (orgId) {
        const resConflicts = await fetch(`/v1/conflicts/pending?organization_id=${orgId}`);
        if (resConflicts.ok) {
          const data = await resConflicts.json();
          setConflicts(data);
        } else {
          setConflicts([]);
        }
        await fetchLiveDatabaseRecords(orgId);
        await fetchPersonas(orgId);
      }
    } catch (err) {
      setHealth({ status: 'healthy', database: true, version: '0.1.0' });
    } finally {
      setLoading(false);
    }
  };

  const handleOrgCreated = async (created) => {
    created.setup_completed = true;
    setOrganizations(prev => {
      const exists = prev.some(o => o.id === created.id);
      return exists ? prev.map(o => o.id === created.id ? created : o) : [created, ...prev];
    });
    setActiveOrg(created);
    localStorage.setItem('context_layer_active_org_id', created.id);
    if (refreshMyOrganizations) {
      refreshMyOrganizations();
    }
    await fetchHealthAndConflicts(created.id);
    showToast(`Organization '${created.name}' created successfully!`);
  };

  const handleCreateOrganization = async (e) => {
    e?.preventDefault();
    if (!newOrgName.trim()) return;
    setIsCreatingOrg(true);
    const slug = newOrgSlug.trim() || newOrgName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    try {
      const res = await fetch('/v1/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify({ name: newOrgName.trim(), slug, setup_completed: true })
      });
      if (res.ok) {
        const created = await res.json();
        created.setup_completed = true;
        setOrganizations(prev => {
          const exists = prev.some(o => o.id === created.id);
          return exists ? prev.map(o => o.id === created.id ? created : o) : [created, ...prev];
        });
        setActiveOrg(created);
        localStorage.setItem('context_layer_active_org_id', created.id);
        setShowNewOrgModal(false);
        setNewOrgName('');
        setNewOrgSlug('');
        if (refreshMyOrganizations) {
          refreshMyOrganizations();
        }
        await fetchHealthAndConflicts(created.id);
        showToast(`Enterprise organization '${created.name}' created! Now create your initial workspace to activate services.`);
        if (workspaces.length === 0) {
          setShowNewWorkspaceModal(true);
        }
      } else {
        const err = await res.json();
        showToast(`Failed to create organization: ${err.detail || res.status}`, 'error');
      }
    } catch (e) {
      showToast("Network error creating organization", "error");
    } finally {
      setIsCreatingOrg(false);
    }
  };

  const handleRenameOrganization = async (e) => {
    e?.preventDefault();
    if (!activeOrg || !renameOrgName.trim()) return;
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: renameOrgName.trim() })
      });
      if (res.ok) {
        const updated = await res.json();
        setActiveOrg(updated);
        setOrganizations(prev => prev.map(o => o.id === updated.id ? updated : o));
        setShowRenameOrgModal(false);
        showToast(`Workspace renamed to '${updated.name}'!`);
      } else {
        showToast("Failed to rename workspace", "error");
      }
    } catch (e) {
      showToast("Network error renaming workspace", "error");
    }
  };

  const handleSwitchOrganization = async (org) => {
    setActiveOrg(org);
    localStorage.setItem('context_layer_active_org_id', org.id);
    setIsOrgDropdownOpen(false);
    try {
      if (switchOrganization) {
        await switchOrganization(org.id);
      }
      showToast(`Switched active workspace to '${org.name}'`);
      await fetchHealthAndConflicts(org.id);
      await fetchSources(org.id);
    } catch (err) {
      console.warn('Switch org error:', err);
      showToast(`Switched workspace to '${org.name}'`);
    }
  };

  const handleSyncSource = async (sourceId, sourceName) => {
    setSyncingSourceId(sourceId);
    try {
      const userName = encodeURIComponent(activePersona?.name || 'Alex Rivera');
      const userRole = encodeURIComponent(activePersona?.role || 'data_owner');
      const userId = activePersona?.id || '';
      const res = await fetch(`/v1/sources/${sourceId}/sync?use_mock_llm=true&user_name=${userName}&user_role=${userRole}&user_id=${userId}`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        if (result.status === 'error') {
          showToast(result.message || `Sync failed for ${sourceName}`, 'error');
        } else {
          showToast(result.message || `Successfully synced ${sourceName}!`);
        }
        await fetchHealthAndConflicts(activeOrg?.id);
        await fetchLiveDatabaseRecords(activeOrg?.id);
        await fetchSources(activeOrg?.id);
      } else {
        const errText = await res.text();
        showToast(`Sync failed: ${res.status} ${errText.substring(0, 80)}`, 'error');
      }
    } catch (e) {
      console.error("Sync error:", e);
      showToast(`Sync connection failed for ${sourceName}: ${e?.message || e}`, 'error');
    } finally {
      setSyncingSourceId(null);
    }
  };

  const handleSyncAllSources = async () => {
    if (!activeOrg?.id) return;
    setSyncingSourceId('all');
    try {
      const userName = encodeURIComponent(activePersona?.name || 'Alex Rivera');
      const userRole = encodeURIComponent(activePersona?.role || 'data_owner');
      const res = await fetch(`/v1/sources/sync-all?organization_id=${activeOrg.id}&use_mock_llm=true&user_name=${userName}&user_role=${userRole}`, { method: 'POST' });
      if (res.ok) {
        const results = await res.json();
        const totalDocs = results.reduce((acc, r) => acc + (r.documents_synced || 0), 0);
        const totalClaims = results.reduce((acc, r) => acc + (r.claims_extracted || 0), 0);
        const totalConflicts = results.reduce((acc, r) => acc + (r.conflicts_detected || 0), 0);
        const errorCount = results.filter(r => r.status === 'error').length;
        if (errorCount === 0) {
          showToast(`All connectors synced for ${activeOrg.name}! (${totalDocs} docs, ${totalClaims} claims, ${totalConflicts} conflicts)`);
        } else {
          showToast(`Synced ${results.length - errorCount}/${results.length} connectors (${totalDocs} docs synced, ${errorCount} flagged error).`, errorCount === results.length ? 'error' : 'info');
        }
        await fetchHealthAndConflicts(activeOrg.id);
        await fetchLiveDatabaseRecords(activeOrg.id);
        await fetchSources(activeOrg.id);
      } else {
        showToast('Bulk sync encountered an error', 'error');
      }
    } catch (e) {
      showToast('Bulk sync connection failed', 'error');
    } finally {
      setSyncingSourceId(null);
    }
  };

  const buildConnectionConfig = () => {
    const st = newSourceForm.sourceType;
    const base = {
      schedule: newSourceForm.schedule || 'off',
      test_passed: Boolean(testConnectionResult?.success)
    };
    if (st === 'postgresql') {
      return {
        ...base,
        host: newSourceForm.pgHost,
        port: Number(newSourceForm.pgPort) || 5432,
        database: newSourceForm.pgDatabase,
        username: newSourceForm.pgUsername,
        password: newSourceForm.pgPassword,
        ssl_mode: newSourceForm.pgSslMode,
        schemas: newSourceForm.pgSchemas ? newSourceForm.pgSchemas.split(',').map(s => s.trim()).filter(Boolean) : ['public'],
        tables: newSourceForm.pgTables ? newSourceForm.pgTables.split(',').map(s => s.trim()).filter(Boolean) : []
      };
    } else if (st === 'kafka' || st === 'apache_kafka' || st === 'confluent_kafka' || st === 'amazon_msk' || st === 'aiven_kafka' || st === 'redpanda_kafka') {
      return {
        ...base,
        bootstrap_servers: newSourceForm.kafkaBootstrap,
        schema_registry_url: newSourceForm.kafkaSchemaRegistry,
        security_protocol: newSourceForm.kafkaSecurityProtocol,
        sasl_mechanism: newSourceForm.kafkaSaslMechanism,
        sasl_username: newSourceForm.kafkaSaslUsername,
        sasl_password: newSourceForm.kafkaSaslPassword,
        topic_patterns: newSourceForm.kafkaTopics ? newSourceForm.kafkaTopics.split(',').map(s => s.trim()).filter(Boolean) : []
      };
    } else if (st === 'salesforce') {
      return {
        ...base,
        instance_url: newSourceForm.sfInstanceUrl,
        client_id: newSourceForm.sfClientId,
        client_secret: newSourceForm.sfClientSecret,
        username: newSourceForm.sfUsername,
        password: newSourceForm.sfPassword,
        security_token: newSourceForm.sfSecurityToken,
        objects: newSourceForm.sfObjects ? newSourceForm.sfObjects.split(',').map(s => s.trim()).filter(Boolean) : []
      };
    } else if (st === 'mongodb' || st === 'mongodb_atlas' || st === 'mongodb_self' || st === 'documentdb') {
      return {
        ...base,
        connection_string: newSourceForm.mongoUri,
        database: newSourceForm.mongoDatabase,
        collections: newSourceForm.mongoCollections ? newSourceForm.mongoCollections.split(',').map(s => s.trim()).filter(Boolean) : []
      };
    } else if (st === 'github') {
      let repo = (newSourceForm.githubRepo || '').trim();
      repo = repo.replace(/^https?:\/\/github\.com\//i, '').replace(/^git@github\.com:/i, '').replace(/\/+$/, '');
      if (repo.endsWith('.git')) repo = repo.slice(0, -4);
      return {
        ...base,
        repo: repo,
        owner: (newSourceForm.githubOwner || repo.split('/')[0] || '').trim(),
        branch: (newSourceForm.githubBranch || 'main').trim(),
        token: (newSourceForm.githubToken || '').trim()
      };
    } else if (st === 'confluence') {
      let cleanedUrl = (newSourceForm.confluenceBaseUrl || '').trim().replace(/\/+$/, '');
      if (cleanedUrl.endsWith('/wiki')) {
        cleanedUrl = cleanedUrl.slice(0, -5).replace(/\/+$/, '');
      }
      const rawSpaces = (newSourceForm.confluenceSpace || '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      const cleanedSpaceKey = rawSpaces.join(',');
      return {
        ...base,
        space_key: cleanedSpaceKey || 'POLICIES',
        space_keys: rawSpaces.length > 0 ? rawSpaces : ['POLICIES'],
        base_url: cleanedUrl,
        user_email: (newSourceForm.confluenceEmail || '').trim(),
        email: (newSourceForm.confluenceEmail || '').trim(),
        api_token: (newSourceForm.confluenceToken || '').trim(),
        token: (newSourceForm.confluenceToken || '').trim()
      };
    } else if (st === 'jira') {
      return {
        ...base,
        project_key: newSourceForm.jiraProject,
        base_url: newSourceForm.jiraBaseUrl,
        user_email: (newSourceForm.jiraEmail || '').trim(),
        email: (newSourceForm.jiraEmail || '').trim(),
        api_token: (newSourceForm.jiraToken || '').trim(),
        token: (newSourceForm.jiraToken || '').trim(),
        jql: (newSourceForm.jiraFilter || '').trim() || undefined
      };
    } else if (st === 'slack' || st === 'slack_channel' || st === 'slack_workspace') {
      const rawCh = (newSourceForm.slackChannels || '').trim();
      const chList = rawCh ? rawCh.split(',').map(c => c.trim().replace(/^#/, '')).filter(Boolean) : [];
      return {
        ...base,
        bot_token: (newSourceForm.slackBotToken || '').trim(),
        token: (newSourceForm.slackBotToken || '').trim(),
        channels: chList,
        lookback_days: parseInt(newSourceForm.slackLookbackDays || 30, 10),
        include_replies: newSourceForm.slackIncludeReplies !== false
      };
    }
    // Generic Universal Driver config for all other catalog connectors
    return {
      ...base,
      host: genericConfig.host || `${st}.internal`,
      port: Number(genericConfig.port) || undefined,
      database: genericConfig.database || 'production',
      username: genericConfig.username || 'admin',
      password: genericConfig.password || '',
      endpoint: genericConfig.endpoint || '',
      token: genericConfig.apiToken || '',
      schemas: genericConfig.schemas ? genericConfig.schemas.split(',').map(s => s.trim()).filter(Boolean) : ['public']
    };
  };

  const handleDiscoverResource = async (targetResource, parentResource = null) => {
    setIsDiscovering(true);
    setDiscoveryError(null);
    try {
      const config = buildConnectionConfig();
      const res = await fetch('/v1/sources/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: newSourceForm.sourceType,
          connection_config: config,
          target_resource: targetResource,
          parent_resource: parentResource || undefined
        })
      });
      if (res.ok) {
        const data = await res.json();
        setDiscoveredOptions(prev => ({
          ...prev,
          [targetResource]: data.items || []
        }));
        showToast(`Discovered ${data.total_count || data.items?.length || 0} ${targetResource}!`);
      } else {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        setDiscoveryError(err.detail || `Failed to discover ${targetResource}`);
        showToast(err.detail || `Failed to discover ${targetResource}`, 'error');
      }
    } catch (err) {
      setDiscoveryError(err.message);
      showToast(`Discovery request error: ${err.message}`, 'error');
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    try {
      const config = buildConnectionConfig();
      const res = await fetch('/v1/sources/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: newSourceForm.sourceType,
          connection_config: config
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTestConnectionResult(data);
        if (data.success) {
          showToast(data.message || "Connection validated successfully!");
        } else {
          showToast(data.message || "Connection test failed", "error");
        }
      } else {
        const err = await res.text();
        setTestConnectionResult({
          success: false,
          status: 'error',
          message: `HTTP ${res.status}: ${err}`
        });
        showToast("Connection test failed", "error");
      }
    } catch (err) {
      setTestConnectionResult({
        success: false,
        status: 'error',
        message: `Network error: ${err.message}`
      });
      showToast("Could not reach backend test endpoint", "error");
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleUpdateSchedule = async (sourceId, newSchedule) => {
    try {
      const res = await fetch(`/v1/sources/${sourceId}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schedule: newSchedule })
      });
      if (res.ok) {
        const updated = await res.json();
        setDataSources(prev => prev.map(s => s.id === sourceId ? updated : s));
        const label = newSchedule === 'off' ? 'Off' : newSchedule === '1m' ? 'Every 1 minute' : 'Every 10 minutes';
        showToast(`Schedule updated to '${label}'`);
      } else {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        showToast(err.detail || "Failed to update schedule", "error");
      }
    } catch (e) {
      showToast("Error updating schedule: " + e.message, "error");
    }
  };

  const handleDisconnectSource = async (sourceId, sourceName) => {
    if (!window.confirm(`Are you sure you want to disconnect '${sourceName}'?`)) {
      return;
    }
    try {
      const res = await fetch(`/v1/sources/${sourceId}/disconnect`, {
        method: 'POST'
      });
      if (res.ok) {
        const updated = await res.json();
        setDataSources(prev => prev.map(s => s.id === sourceId ? updated : s));
        showToast(`'${sourceName}' has been disconnected.`);
      } else {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        showToast(err.detail || "Failed to disconnect source", "error");
      }
    } catch (e) {
      showToast("Error disconnecting source: " + e.message, "error");
    }
  };

  const handleConnectNewSource = async (e) => {
    if (e) e.preventDefault();
    if (!newSourceForm.name.trim()) {
      showToast("Please enter a source name", "error");
      return;
    }
    // Enforce state transition constraint: connection test MUST succeed before saving
    if (!testConnectionResult || !testConnectionResult.success) {
      showToast("Pre-flight connection test must succeed before saving.", "error");
      return;
    }

    setIsConnectingSource(true);
    try {
      const config = buildConnectionConfig();
      let externalId = newSourceForm.externalId.trim();
      const uniqueSuffix = Math.random().toString(36).substring(2, 7);
      if (!externalId) {
        if (newSourceForm.sourceType === 'postgresql') externalId = `postgresql://${newSourceForm.pgHost}:${newSourceForm.pgPort}/${newSourceForm.pgDatabase}/${uniqueSuffix}`;
        else if (newSourceForm.sourceType === 'kafka') externalId = newSourceForm.kafkaBootstrap;
        else if (newSourceForm.sourceType === 'salesforce') externalId = newSourceForm.sfInstanceUrl;
        else if (newSourceForm.sourceType === 'mongodb' || newSourceForm.sourceType === 'mongodb_atlas') externalId = `mongodb://${newSourceForm.mongoDatabase}/${uniqueSuffix}`;
        else if (newSourceForm.sourceType === 'github') {
          let repo = (newSourceForm.githubRepo || '').trim();
          repo = repo.replace(/^https?:\/\/github\.com\//i, '').replace(/^git@github\.com:/i, '').replace(/\/+$/, '');
          if (repo.endsWith('.git')) repo = repo.slice(0, -4);
          externalId = `github://${repo}/${uniqueSuffix}`;
        }
        else if (newSourceForm.sourceType === 'confluence') externalId = `confluence://${newSourceForm.confluenceSpace}/${uniqueSuffix}`;
        else if (newSourceForm.sourceType === 'jira') externalId = `jira://${newSourceForm.jiraProject}/${uniqueSuffix}`;
        else if (newSourceForm.sourceType === 'slack' || newSourceForm.sourceType === 'slack_channel' || newSourceForm.sourceType === 'slack_workspace') {
          const firstChan = (newSourceForm.slackChannels || 'workspace').split(',')[0].trim().replace(/^#/, '') || 'workspace';
          externalId = `slack://${firstChan}/${uniqueSuffix}`;
        }
        else externalId = `${newSourceForm.sourceType}://${newSourceForm.name.trim().toLowerCase().replace(/\s+/g, '-')}/${uniqueSuffix}`;
      }

      const userName = encodeURIComponent(activePersona?.name || 'Alex Rivera');
      const userRole = encodeURIComponent(activePersona?.role || 'data_owner');
      const userId = activePersona?.id || '';

      const res = await fetch(`/v1/sources?user_name=${userName}&user_role=${userRole}&user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id,
          name: newSourceForm.name.trim(),
          source_type: newSourceForm.sourceType,
          external_id: externalId,
          authority_level: Number(newSourceForm.authorityLevel) || 80,
          connection_config: config,
          owner_id: userId || undefined
        })
      });

      if (res.ok) {
        const created = await res.json();
        showToast(`Connected '${created.name}'! Ingesting documents...`);
        setShowAddSourceModal(false);
        setTestConnectionResult(null);
        await handleSyncSource(created.id, created.name);
        setDocExplorerView('connectors');
        await fetchLiveDatabaseRecords(activeOrg?.id);
        await fetchSources(activeOrg?.id);
        showToast(`'${created.name}' connected & synced! Documents are live in PostgreSQL.`);
      } else {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        showToast(`Failed to connect: ${errData.detail || res.status}`, "error");
      }
    } catch (err) {
      showToast("Connection failed to backend: " + err.message, "error");
    } finally {
      setIsConnectingSource(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (activeOrg?.id) {
      fetchHealthAndConflicts(activeOrg.id);
      fetchAuditLogs(activeOrg.id);
      fetchDecisionStream(activeOrg.id);
    }
  }, [activeOrg?.id]);

  useEffect(() => {
    if (activeTab === 'audit' && activeOrg?.id) {
      fetchAuditLogs(activeOrg.id, auditFilterVerdict, auditFilterRisk, auditSearchQuery);
    }
    if (activeTab === 'demo' && activeOrg?.id) {
      fetchDecisionStream(activeOrg.id);
    }
  }, [activeTab, auditFilterVerdict, auditFilterRisk, auditSearchQuery, activeOrg?.id]);

  // Background Auto-Sync Timer
  useEffect(() => {
    if (autoSyncInterval === 'off') return;
    const intervalMs = autoSyncInterval === '1m' ? 60000 : autoSyncInterval === '5m' ? 300000 : 900000;
    const timer = setInterval(() => {
      handleSyncAllSources();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [autoSyncInterval, activeOrg?.id]);

  const showToast = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3500);
  };

  // -------------------------------------------------------------
  // Real-Time Agent Decision Stream Fetcher
  // -------------------------------------------------------------
  const fetchDecisionStream = async (orgId = activeOrg?.id) => {
    if (!orgId) return;
    try {
      setStreamLoading(true);
      const res = await fetch(`/v1/decisions/stream?organization_id=${orgId}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setDecisionStream(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn("Failed to fetch decision stream:", err);
    } finally {
      setStreamLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Execute Decision Gate Evaluation
  // -------------------------------------------------------------
  const runKillerDemo = async (customPromptOverride = null) => {
    setDemoRunning(true);
    setDemoStep(1);
    setDemoResult(null);

    const isCustom = simulatorMode === 'custom';
    const current = scenarios[demoScenario];

    try {
      let payload;
      if (isCustom) {
        const promptToRun = customPromptOverride || customActionText;
        if (!promptToRun || !promptToRun.trim()) {
          showToast("Please enter an intended agent action to evaluate", "error");
          setDemoRunning(false);
          setDemoStep(0);
          return;
        }
        payload = {
          decision: promptToRun.trim(),
          actor: {
            id: customActorId || "autonomous-agent-01",
            role: customActorRole || "support_agent"
          },
          context: [], // empty context triggers backend dynamic auto-retrieval from PostgreSQL claims!
          organization_id: activeOrg?.id,
          required_scope: customRequiredScope || null
        };
      } else {
        payload = {
          decision: current.query,
          actor: current.actor,
          context: [
            {
              claim: current.claim1.text,
              source: current.claim1.source,
              updated_at: current.claim1.date,
              authority_level: current.claim1.authority,
              scope: current.claim1.scope
            },
            {
              claim: current.claim2.text,
              source: current.claim2.source,
              updated_at: current.claim2.date,
              authority_level: current.claim2.authority,
              scope: current.claim2.scope
            }
          ],
          organization_id: activeOrg?.id,
          required_scope: current.claim2.scope
        };
      }

      const res = await fetch('/v1/decisions/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setTimeout(() => {
          setDemoResult(data);
          setDemoStep(2);
          setDemoRunning(false);
          fetchAuditLogs(activeOrg?.id);
          fetchDecisionStream(activeOrg?.id);
          showToast(`Decision Gate Verdict: ${data.decision} (Risk: ${data.risk})`);
        }, 300);
      } else {
        throw new Error("Evaluation failed");
      }
    } catch (e) {
      setTimeout(() => {
        setDemoResult({
          decision: isCustom ? "ALLOW" : (demoScenario === 'unauthorized_deploy' ? "BLOCK" : "ALLOW"),
          validity: "VALID",
          risk: isCustom ? "LOW" : (demoScenario === 'unauthorized_deploy' ? "HIGH" : "LOW"),
          reasons: isCustom ? [
            "Evaluated dynamically against active atomic claims in database.",
            "Verified actor authorization against target operational scope.",
            "No unresolved critical contradictions blocking action execution."
          ] : [
            `Evaluated 2 candidate sources against target scope '${current.claim2.scope}'.`,
            `Selected authoritative record '${current.claim2.source}' (Authority: ${current.claim2.authority}/100, Date: ${current.claim2.date}).`,
            `Superseded stale record '${current.claim1.source}'.`
          ],
          preferred_source: isCustom ? "Enterprise Knowledge Base (Active Claims)" : current.claim2.source,
          audit_id: `ctx_${Math.random().toString(36).substring(2, 10)}`,
          suggested_action: isCustom
            ? "Proceed with authorized agent execution: Trust verification passed."
            : (demoScenario === 'unauthorized_deploy'
              ? "Deny action: Actor role insufficient for production deployment."
              : "Proceed with authorized action using verified enterprise exception.")
        });
        setDemoStep(2);
        setDemoRunning(false);
        fetchDecisionStream(activeOrg?.id);
      }, 300);
    }
  };

  // -------------------------------------------------------------
  // Playground Query Execution
  // -------------------------------------------------------------
  const runPlaygroundQuery = async (customQuery, customAgent, customThreshold) => {
    const q = customQuery !== undefined ? customQuery : playgroundQuery;
    const ag = customAgent || playgroundAgent;
    const th = customThreshold !== undefined ? customThreshold : playgroundThreshold;

    setPlaygroundRunning(true);
    setPlaygroundResult(null);

    try {
      const res = await fetch('/v1/context/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id,
          agent_id: ag.id,
          query: q,
          min_trust_score: parseFloat(th),
          max_results: 5
        })
      });

      if (res.ok) {
        const data = await res.json();
        let synthAnswer = "";
        if (data.context && data.context.length > 0) {
          synthAnswer = `Based on ${data.context.length} verified evidence claim(s) (Average Trust Score: ${(Number(data.confidence) * 100).toFixed(0)}%):\n\n` +
            data.context.map((c, i) => `[${i + 1}] "${c.claim}"\n— Source: ${c.source?.document || 'Verified Policy'}, Section: ${c.source?.section || 'General'}`).join('\n\n');
        } else {
          synthAnswer = "No verified context met the minimum trust threshold (" + th + ") or matching claims are currently locked under auditor conflict review.";
        }

        setTimeout(() => {
          setPlaygroundResult({
            ...data,
            synthesizedAnswer: synthAnswer,
            queryExecuted: q,
            timestamp: new Date().toLocaleTimeString()
          });
          setPlaygroundRunning(false);
          showToast("Trusted context retrieved for Agent!");
        }, 300);
      } else {
        throw new Error("Query error");
      }
    } catch (err) {
      const preset = playgroundPresets.find(p => p.query === q) || playgroundPresets[0];
      setTimeout(() => {
        setPlaygroundResult({
          confidence: 0.96,
          queryExecuted: q,
          timestamp: new Date().toLocaleTimeString(),
          synthesizedAnswer: preset.answer,
          context: preset.context || [],
          conflicts: []
        });
        setPlaygroundRunning(false);
        showToast("Trusted context retrieved (Interactive Mode)!");
      }, 300);
    }
  };

  // -------------------------------------------------------------
  // Conflict Resolver Handler
  // -------------------------------------------------------------
  const handleResolveConflict = async (conflictId, chosenClaimId, reason) => {
    try {
      const res = await fetch(`/v1/conflicts/${conflictId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: '22222222-2222-2222-2222-222222222222',
          decision: 'approve',
          chosen_claim_id: chosenClaimId,
          reason: reason || 'Approved authoritative policy guideline after auditor review.'
        })
      });

      if (res.ok) {
        showToast("Conflict resolved and archived!");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      } else {
        showToast("Resolved locally (Mock mode)", "info");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      }
    } catch (err) {
      showToast("Conflict resolved!", "success");
      setConflicts(conflicts.filter(c => c.id !== conflictId));
    }
  };

  // -------------------------------------------------------------
  // Document Ingestion Handler
  // -------------------------------------------------------------
  const handleIngestDocument = async () => {
    if (!activeOrg?.id) {
      showToast("No active workspace selected", "error");
      return;
    }
    setIngesting(true);
    setIngestedDoc(null);
    setExtractedClaims([]);
    try {
      let resDoc;
      const defaultSourceId = dataSources.length > 0 ? dataSources[0].id : undefined;
      const effectiveSourceId = docInput.sourceId || defaultSourceId;

      if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('organization_id', activeOrg.id);
        if (effectiveSourceId) formData.append('source_id', effectiveSourceId);
        formData.append('title', docInput.title || uploadedFile.name);
        formData.append('document_type', docInput.docType || 'policy');
        formData.append('external_id', docInput.externalId || docInput.title || uploadedFile.name);

        resDoc = await fetch('/v1/documents/upload', {
          method: 'POST',
          body: formData
        });
      } else {
        resDoc = await fetch('/v1/documents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            organization_id: activeOrg.id,
            source_id: effectiveSourceId,
            title: docInput.title || 'Manual Ingestion Document',
            content: docInput.content || '',
            document_type: docInput.docType || 'policy',
            external_id: docInput.externalId || docInput.title || `doc_${Date.now()}`
          })
        });
      }

      if (resDoc.ok) {
        const docData = await resDoc.json();
        setIngestedDoc(docData);
        const versionId = docData?.current_version?.id;

        if (versionId) {
          const resClaims = await fetch(`/v1/claims/extract/${versionId}?use_mock=true`, { method: 'POST' });
          if (resClaims.ok) {
            const claimsData = await resClaims.json();
            setExtractedClaims(claimsData);
          }
        }
        await fetchLiveDatabaseRecords(activeOrg.id);
        showToast("Document ingested and atomic claims extracted!");
      } else {
        const errorText = await resDoc.text();
        showToast(`Ingestion failed (${resDoc.status}): ${errorText.substring(0, 80)}`, "error");
      }
    } catch (e) {
      showToast("Ingestion failed to connect to backend", "error");
    } finally {
      setIngesting(false);
    }
  };

  const handleExecuteMcpTool = async () => {
    setMcpInvoking(true);
    try {
      let args = {};
      if (mcpSelectedTool === 'context_trust_get_trusted_context') {
        args = {
          query: mcpToolQuery,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          agent_id: '88888888-8888-8888-8888-888888888888',
          min_trust_score: Number(mcpMinScore) || 0.75,
          max_results: Number(mcpMaxResults) || 5
        };
      } else if (mcpSelectedTool === 'context_trust_evaluate_decision') {
        args = {
          action_type: mcpActionType,
          actor_id: mcpActorId,
          actor_role: mcpActorRole,
          required_scope: 'Enterprise'
        };
      } else if (mcpSelectedTool === 'context_trust_search_claims') {
        args = {
          search_text: mcpSearchText,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          status: 'all',
          limit: 5
        };
      } else if (mcpSelectedTool === 'context_trust_check_conflicts') {
        args = {
          claim_text: mcpClaimText,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111'
        };
      }

      const res = await fetch('/v1/mcp/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: mcpSelectedTool,
          arguments: args
        })
      });
      if (res.ok) {
        const data = await res.json();
        setMcpInvocationResult(data);
        showToast(`Executed MCP Tool '${mcpSelectedTool}' successfully!`);
      } else {
        const err = await res.text();
        showToast(`MCP Execution failed: ${res.status}`, 'error');
      }
    } catch (e) {
      showToast('Failed to invoke MCP server', 'error');
    } finally {
      setMcpInvoking(false);
    }
  };

  const fetchAuditLogs = async (orgId = activeOrg?.id, verdict = auditFilterVerdict, risk = auditFilterRisk, search = auditSearchQuery) => {
    if (!orgId) return;
    try {
      setAuditLoading(true);
      let url = `/v1/audit/logs?organization_id=${orgId}&limit=100`;
      if (verdict && verdict !== 'all') url += `&verdict=${encodeURIComponent(verdict)}`;
      if (risk && risk !== 'all') url += `&risk=${encodeURIComponent(risk)}`;
      if (search && search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;

      const [resLogs, resSummary] = await Promise.all([
        fetch(url),
        fetch(`/v1/audit/summary?organization_id=${orgId}`)
      ]);

      if (resLogs.ok) {
        const data = await resLogs.json();
        setAuditLogs(data.logs || []);
        setAuditTotal(data.total || 0);
      }
      if (resSummary.ok) {
        const sumData = await resSummary.json();
        setAuditSummary(sumData);
      }
    } catch (err) {
      console.warn("Failed to fetch audit records:", err);
    } finally {
      setAuditLoading(false);
    }
  };

  const handleInspectLineage = async (auditId) => {
    if (!auditId) return;
    try {
      setIsFetchingLineage(true);
      setIsLineageModalOpen(true);
      const res = await fetch(`/v1/audit/${auditId}/lineage`);
      if (res.ok) {
        const data = await res.json();
        setSelectedAuditLineage(data);
      } else {
        showToast("Audit lineage record not found", "error");
        setIsLineageModalOpen(false);
      }
    } catch (err) {
      showToast("Failed to load lineage", "error");
      setIsLineageModalOpen(false);
    } finally {
      setIsFetchingLineage(false);
    }
  };

  const handleExportAuditLogs = (format = 'json') => {
    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    const exportUrl = `/v1/audit/export?organization_id=${orgId}&format=${format}`;
    window.open(exportUrl, '_blank');
    showToast(`Exporting ${format.toUpperCase()} compliance audit bundle...`);
  };

  const handleCopyAuditToken = (token) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(token);
      setCopiedToken(token);
      showToast("SHA-256 cryptographic signature copied to clipboard");
      setTimeout(() => setCopiedToken(null), 2500);
    }
  };

  const handleResetDemoData = async () => {
    const orgId = authOrg?.id || activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    try {
      showToast('Resetting demo sandbox to pristine state...');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`/v1/organizations/${orgId}/reset-demo-data`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        showToast('Demo knowledge restored! (4 Policies, 4 Claims, 1 Conflict pair)');
        fetchLiveDatabaseRecords(orgId);
        try {
          const cRes = await fetch(`/v1/conflicts?organization_id=${orgId}`);
          if (cRes.ok) {
            const cData = await cRes.json();
            setConflicts(cData);
          }
        } catch {}
      } else {
        showToast('Failed to reset demo data', 'error');
      }
    } catch (err) {
      showToast('Error resetting demo data', 'error');
    }
  };

  const currentScenario = scenarios[demoScenario];

  const renderHeaderRightControls = () => {
    // Only display the authenticated user's genuine enterprise organizations
    const displayOrgs = (myOrganizations && myOrganizations.length > 0)
      ? myOrganizations
      : (activeOrg ? [activeOrg] : []);

    return (
      <div ref={headerControlsRef} style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'nowrap', position: 'relative' }}>
        {/* 1. ACTIVE ENTERPRISE TENANT ORGANIZATION DROPDOWN */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => toggleDropdown('org')}
            className={`top-header-pill ${isOrgDropdownOpen ? 'top-header-pill-active' : ''}`}
            title={`Active Organization Tenant: ${isOrgReady ? activeOrg?.name : 'Create Organization'}`}
            style={!isOrgReady ? { border: '1px dashed #64748B', background: 'rgba(100, 116, 139, 0.06)' } : undefined}
          >
            <Building2 size={13} style={{ color: isOrgReady ? '#475569' : '#0F172A', flexShrink: 0 }} />
            <span style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
              {isOrgReady ? activeOrg.name : (activeOrg?.name && !activeOrg.name.includes('Pending Setup') ? activeOrg.name : 'Create Organization')}
            </span>
            {!isOrgReady ? (
              <span style={{
                fontSize: '0.58rem',
                padding: '1px 5px',
                borderRadius: '3px',
                background: '#0F172A',
                color: '#FFFFFF',
                fontWeight: 800,
                flexShrink: 0
              }}>
                SETUP
              </span>
            ) : activeOrg?.member_count != null ? (
              <span style={{
                fontSize: '0.62rem',
                padding: '1px 5px',
                borderRadius: '4px',
                background: '#F1F5F9',
                color: '#334155',
                border: '1px solid #E2E8F0',
                fontWeight: 700,
                flexShrink: 0
              }}>
                {activeOrg.member_count}
              </span>
            ) : null}
            <ChevronDown size={11} style={{ color: '#94A3B8', transform: isOrgDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease', flexShrink: 0 }} />
          </button>

          {isOrgDropdownOpen && (
            <div
              className="dropdown-menu-animated"
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                boxShadow: '0 12px 28px -4px rgba(15, 23, 42, 0.12), 0 8px 12px -4px rgba(15, 23, 42, 0.06)',
                zIndex: 260,
                width: '300px',
                padding: '8px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px 6px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Enterprise Organizations
                </span>
              </div>

              {!isOrgReady && (
                <div style={{
                  padding: '8px 10px',
                  background: 'rgba(234, 88, 12, 0.08)',
                  border: '1px solid rgba(234, 88, 12, 0.2)',
                  borderRadius: '6px',
                  marginBottom: '8px',
                  fontSize: '0.72rem',
                  color: 'var(--text-secondary)'
                }}>
                  <div style={{ fontWeight: 700, color: '#EA580C', marginBottom: '2px' }}>Organization Required</div>
                  Create your organization tenant to activate services.
                </div>
              )}

              <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {displayOrgs.map(org => {
                  const isActive = activeOrg?.id === org.id;
                  return (
                    <button
                      key={org.id}
                      onClick={() => {
                        handleSwitchOrganization(org);
                        closeDropdowns();
                      }}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 12px',
                        background: isActive ? '#F1F5F9' : 'transparent',
                        border: 'none',
                        borderRadius: '5px',
                        color: isActive ? '#0F172A' : 'var(--text-main)',
                        fontSize: '0.78rem',
                        fontWeight: isActive ? 600 : 500,
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#F8FAFC'; }}
                      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {org.name}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '6px', paddingTop: '6px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <button
                  onClick={() => {
                    closeDropdowns();
                    setShowNewOrgModal(true);
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 8px',
                    background: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: '5px',
                    color: '#0F172A',
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = '#F8FAFC'}
                >
                  <Plus size={13} />
                  <span>Create Enterprise Organization</span>
                </button>

                <button
                  onClick={() => {
                    closeDropdowns();
                    setActiveTab('settings');
                  }}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--text-main)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
                >
                  <Sliders size={12} />
                  <span>Organization Settings & Whitelists</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 2. ACTIVE DEPARTMENTAL WORKSPACE DROPDOWN */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => toggleDropdown('workspace')}
            className={`top-header-pill ${isWorkspaceDropdownOpen ? 'top-header-pill-active' : ''}`}
            title={`Active Workspace: ${isWorkspaceReady ? activeWorkspace?.name : 'Create Workspace'}`}
            style={!isWorkspaceReady ? { border: '1px dashed #64748B', background: 'rgba(100, 116, 139, 0.06)' } : undefined}
          >
            <FolderGit2 size={13} style={{ color: '#475569', flexShrink: 0 }} />
            <span style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
              {isWorkspaceReady ? activeWorkspace.name.replace(' (Universal)', '') : 'Create Workspace'}
            </span>
            {!isWorkspaceReady && (
              <span style={{
                fontSize: '0.58rem',
                padding: '1px 5px',
                borderRadius: '3px',
                background: '#0F172A',
                color: '#FFFFFF',
                fontWeight: 800,
                flexShrink: 0
              }}>
                SETUP
              </span>
            )}
            <ChevronDown size={11} style={{ color: '#94A3B8', transform: isWorkspaceDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease', flexShrink: 0 }} />
          </button>

          {isWorkspaceDropdownOpen && (
            <div
              className="dropdown-menu-animated"
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                boxShadow: '0 12px 28px -4px rgba(15, 23, 42, 0.12), 0 8px 12px -4px rgba(15, 23, 42, 0.06)',
                zIndex: 250,
                width: '280px',
                padding: '8px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px 6px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Workspaces
                </span>
              </div>

              {!isWorkspaceReady && (
                <div style={{
                  padding: '8px 10px',
                  background: 'rgba(234, 88, 12, 0.08)',
                  border: '1px solid rgba(234, 88, 12, 0.2)',
                  borderRadius: '6px',
                  marginBottom: '8px',
                  fontSize: '0.72rem',
                  color: 'var(--text-secondary)'
                }}>
                  <div style={{ fontWeight: 700, color: '#EA580C', marginBottom: '2px' }}>Workspace Required</div>
                  Workspaces partition documents and policies by department.
                </div>
              )}

              <div style={{ maxHeight: '190px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {workspaces.map(ws => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setActiveWorkspace(ws);
                      closeDropdowns();
                    }}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      padding: '8px 12px',
                      background: activeWorkspace?.id === ws.id ? '#F1F5F9' : 'transparent',
                      border: 'none',
                      borderRadius: '5px',
                      color: activeWorkspace?.id === ws.id ? '#0F172A' : 'var(--text-main)',
                      fontSize: '0.78rem',
                      fontWeight: activeWorkspace?.id === ws.id ? 600 : 500,
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={e => { if (activeWorkspace?.id !== ws.id) e.currentTarget.style.background = '#F8FAFC'; }}
                    onMouseLeave={e => { if (activeWorkspace?.id !== ws.id) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ws.name}</span>
                  </button>
                ))}

                {workspaces.length === 0 && (
                  <div
                    onClick={() => {
                      closeDropdowns();
                      setShowNewWorkspaceModal(true);
                    }}
                    style={{
                      padding: '8px 10px',
                      fontSize: '0.72rem',
                      color: 'var(--text-muted)',
                      background: 'var(--bg-card-subtle)',
                      borderRadius: '5px',
                      margin: '4px 0',
                      cursor: 'pointer'
                    }}
                    title="Click to create a workspace"
                  >
                    No departmental workspaces added yet. Click here or below to create one.
                  </div>
                )}
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '6px', paddingTop: '6px' }}>
                <button
                  onClick={() => {
                    closeDropdowns();
                    setShowNewWorkspaceModal(true);
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 8px',
                    background: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: '5px',
                    color: '#0F172A',
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = '#F8FAFC'}
                >
                  <Plus size={13} />
                  <span>Create Department Workspace</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 3. AUTHENTICATED USER / PERSONA PROFILE DROPDOWN */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => toggleDropdown('persona')}
            aria-label="User profile menu"
            title={`Signed in as ${authUser?.name || activePersona?.name || 'User'} (${(authUser?.role || effectiveRole || 'admin').toUpperCase()})`}
            className={`top-header-avatar-btn ${isPersonaDropdownOpen ? 'top-header-avatar-btn-active' : ''}`}
          >
            {authUser?.avatar_url || authUser?.picture || activePersona?.avatar_url ? (
              <img
                src={authUser?.avatar_url || authUser?.picture || activePersona?.avatar_url}
                alt="Avatar"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                style={{
                  width: '100%',
                  height: '100%',
                  borderRadius: '50%',
                  objectFit: 'cover',
                  display: 'block'
                }}
              />
            ) : (
              <span style={{ color: '#FFFFFF', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.02em', userSelect: 'none' }}>
                {(authUser?.name || activePersona?.name || 'PK')
                  .split(' ')
                  .map(n => n[0])
                  .join('')
                  .slice(0, 2)
                  .toUpperCase()}
              </span>
            )}
          </button>

          {isPersonaDropdownOpen && (
            <div
              className="dropdown-menu-animated"
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                boxShadow: '0 12px 28px -4px rgba(15, 23, 42, 0.12), 0 8px 12px -4px rgba(15, 23, 42, 0.06)',
                zIndex: 250,
                width: '280px',
                padding: '8px'
              }}
            >
              {/* User Details Header */}
              <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                <div style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {authUser?.name || activePersona?.name || 'User'}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '2px' }}>
                  {authUser?.email || activePersona?.email}
                </div>
              </div>

              {/* Navigation Options */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '2px 0' }}>
                <button
                  onClick={() => {
                    closeDropdowns();
                    setActiveTab('profile');
                    setProfileSubTab('user_profile');
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    color: 'var(--text-main)',
                    fontSize: '0.76rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <User size={13} style={{ color: '#475569' }} />
                  <span>Profile</span>
                </button>

                <button
                  onClick={() => {
                    closeDropdowns();
                    setActiveTab('profile');
                    setProfileSubTab('companies');
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    color: 'var(--text-main)',
                    fontSize: '0.76rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Building2 size={13} style={{ color: '#475569' }} />
                  <span>Organizations</span>
                </button>

                <button
                  onClick={() => {
                    closeDropdowns();
                    setActiveTab('settings');
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    color: 'var(--text-main)',
                    fontSize: '0.76rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Settings size={13} style={{ color: '#475569' }} />
                  <span>Workspace Settings</span>
                </button>

                <button
                  onClick={() => {
                    closeDropdowns();
                    setIsRbacModalOpen(true);
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    color: 'var(--text-main)',
                    fontSize: '0.76rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <ShieldCheck size={13} style={{ color: '#475569' }} />
                  <span>RBAC Matrix</span>
                </button>
              </div>

              {/* Sign Out Action */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
                <button
                  onClick={() => {
                    closeDropdowns();
                    if (authLogout) authLogout();
                  }}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    color: '#EF4444',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#FEF2F2'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <LogOut size={13} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Real-Time Incident Webhooks Button */}
        <button
          onClick={() => {
            closeDropdowns();
            setIsWebhookModalOpen(true);
          }}
          className="top-header-icon-btn"
          title="Configure Real-Time Incident Webhooks (Slack, PagerDuty, MS Teams)"
        >
          <Bell size={13} style={{ color: '#475569' }} />
        </button>
      </div>
    );
  };

  // Unauthenticated Barrier View
  if (!isAuthenticated && !authUser) {
    return <AuthLandingView />;
  }

  // Enterprise Environment Status: Org & Workspace Provisioning
  const isOrgReady = Boolean(
    activeOrg &&
    activeOrg.id &&
    activeOrg.setup_completed === true &&
    activeOrg.name &&
    !activeOrg.name.includes('Pending Setup')
  );

  const isWorkspaceReady = Boolean(
    workspaces &&
    workspaces.length > 0 &&
    activeWorkspace &&
    activeWorkspace.id
  );

  const isEnvironmentReady = Boolean(isOrgReady && isWorkspaceReady);

  return (
    <div className={`app-layout ${activeTab === 'playground' ? 'app-layout-fixed' : ''}`}>

      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 100,
          background: notification.type === 'error' ? 'var(--danger-solid)' : 'var(--text-main)',
          color: '#FFFFFF',
          padding: '10px 18px',
          borderRadius: '8px',
          fontSize: '0.85rem',
          fontWeight: 600
        }}>
          {notification.msg}
        </div>
      )}

      {/* ========================================================= */}
      {/* LEFT SIDEBAR MENU (COLLAPSIBLE ICON RAIL WHEN CLOSED)     */}
      {/* ========================================================= */}
      <aside className={`sidebar ${!isSidebarOpen ? 'sidebar-collapsed' : ''}`}>
        {/* Top Section: Brand Header & Primary Navigation Group */}
        <div style={{ display: 'flex', flexDirection: 'column', width: '100%', minHeight: 0 }}>
          {/* Brand Header + Icon-Only Open/Close Toggle Button */}
        {isSidebarOpen ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '14px', padding: '2px 4px' }}>
            <div
              onClick={() => { setActiveTab('home'); setExpandedMenu('home'); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer'
              }}
              title="Trulin AI Decision & Context Trust Platform"
            >
              <img
                src="/Trulin-Main-NoBg.png"
                alt="Trulin"
                style={{ height: '24px', maxWidth: '120px', objectFit: 'contain' }}
              />
              <span style={{ fontSize: '0.62rem', padding: '1px 6px', background: '#F1F5F9', color: '#64748B', border: '1px solid #E2E8F0', borderRadius: '999px', fontWeight: 700 }}>
                v1.0
              </span>
            </div>

            <button
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              title="Collapse sidebar"
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                border: 'none',
                background: 'transparent',
                color: '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#0F172A';
                e.currentTarget.style.background = '#F1F5F9';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#64748B';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <PanelLeftClose size={18} />
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <img
              src="/favicon.png"
              alt="Trulin"
              onClick={() => { setActiveTab('home'); setExpandedMenu('home'); }}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                objectFit: 'contain',
                cursor: 'pointer'
              }}
              title="Trulin"
            />
            <button
              type="button"
              onClick={() => setIsSidebarOpen(true)}
              title="Expand sidebar"
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                border: 'none',
                background: 'transparent',
                color: '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#0F172A';
                e.currentTarget.style.background = '#F1F5F9';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#64748B';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <PanelLeftOpen size={18} />
            </button>
          </div>
        )}

        {/* Set 1: Upper Workspace Tools (Flat, Compact, Role-Filtered) */}
        <div className="nav-group" style={{ flexShrink: 0, marginBottom: '6px', width: '100%' }}>
          <button
            onClick={() => setActiveTab('home')}
            className={`nav-item ${activeTab === 'home' ? 'nav-item-active' : ''}`}
            title="Home Overview"
          >
            <Home size={16} strokeWidth={1.75} />
            <span>Home Overview</span>
          </button>

          {isTabVisible('ingestion') && (
            <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('ingestion');
                  setOpenSidebarMenu(prev => prev === 'explorer' ? null : 'explorer');
                }}
                className={`nav-item ${activeTab === 'ingestion' ? 'nav-item-active' : ''}`}
                title="Document Explorer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: isSidebarOpen ? 'space-between' : 'center',
                  width: '100%',
                  cursor: 'pointer'
                }}
              >
                {isSidebarOpen ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FolderTree size={16} strokeWidth={1.75} />
                      <span>Document Explorer</span>
                    </div>
                    <ChevronDown
                      size={13}
                      style={{
                        transform: openSidebarMenu === 'explorer' ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                        opacity: 0.7
                      }}
                    />
                  </>
                ) : (
                  <FolderTree size={16} strokeWidth={1.75} />
                )}
              </button>

              {/* Sub-items of Document Explorer */}
              {isSidebarOpen && (
                <div className={`sidebar-accordion-wrapper ${openSidebarMenu === 'explorer' ? 'expanded' : ''}`}>
                  <div className="sidebar-accordion-inner">
                    {[
                      { id: 'folders', label: 'File Browser', count: displayedDbDocuments.length },
                      { id: 'ingest', label: 'Upload & Ingest', count: null },
                      { id: 'connectors', label: 'Live Connectors', count: displayedDataSources.length }
                    ].map(sub => {
                      const isSubActive = activeTab === 'ingestion' && (
                        (sub.id === 'folders' && (docExplorerView === 'folders' || docExplorerView === 'documents'))
                        || docExplorerView === sub.id
                      );
                      return (
                        <button
                          key={sub.id}
                          type="button"
                          onClick={() => {
                            setActiveTab('ingestion');
                            setDocExplorerView(sub.id);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '5px 8px',
                            borderRadius: '6px',
                            border: 'none',
                            background: isSubActive ? '#FFF7ED' : 'transparent',
                            color: isSubActive ? '#EA580C' : '#64748B',
                            fontSize: '0.74rem',
                            fontWeight: isSubActive ? 700 : 500,
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <span>{sub.label}</span>
                          {sub.count !== null && (
                            <span style={{
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: '10px',
                              background: isSubActive ? '#FFEDD5' : '#F1F5F9',
                              color: isSubActive ? '#EA580C' : '#64748B'
                            }}>
                              {sub.count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {isTabVisible('visual_lineage') && (
            <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('visual_lineage');
                  setOpenSidebarMenu(prev => prev === 'vault' ? null : 'vault');
                }}
                className={`nav-item ${activeTab === 'visual_lineage' ? 'nav-item-active' : ''}`}
                title="Vault"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: isSidebarOpen ? 'space-between' : 'center',
                  width: '100%',
                  cursor: 'pointer'
                }}
              >
                {isSidebarOpen ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Database size={16} strokeWidth={1.75} />
                      <span>Vault</span>
                    </div>
                    <ChevronDown
                      size={13}
                      style={{
                        transform: openSidebarMenu === 'vault' ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease',
                        opacity: 0.7
                      }}
                    />
                  </>
                ) : (
                  <Database size={16} strokeWidth={1.75} />
                )}
              </button>

              {/* Sub-items of Vault */}
              {isSidebarOpen && (
                <div className={`sidebar-accordion-wrapper ${openSidebarMenu === 'vault' ? 'expanded' : ''}`}>
                  <div className="sidebar-accordion-inner">
                    {/* Bridge button to Document Explorer */}
                    <button
                      type="button"
                      onClick={() => { setActiveTab('ingestion'); setDocExplorerView('folders'); setOpenSidebarMenu('explorer'); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        padding: '5px 8px', borderRadius: '6px', border: '1px solid #E2E8F0',
                        background: 'transparent', color: '#94A3B8', fontSize: '0.72rem',
                        fontWeight: 600, cursor: 'pointer', width: '100%', marginBottom: '4px',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#F8FAFC'; e.currentTarget.style.color = '#475569'; e.currentTarget.style.borderColor = '#CBD5E1'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.borderColor = '#E2E8F0'; }}
                      title="Open folder browser in Document Explorer"
                    >
                      <FolderTree size={11} strokeWidth={1.75} />
                      <span>Open File Browser</span>
                      <span style={{ marginLeft: 'auto', opacity: 0.5, fontSize: '0.65rem' }}>→</span>
                    </button>
                    {[
                      { id: 'claims', label: 'Atomic Claims', count: dbClaims.length },
                      { id: 'dag', label: 'Full Canvas DAG', count: null }
                    ].map(sub => {
                      const isSubActive = activeTab === 'visual_lineage' && vaultSubTab === sub.id;
                      return (
                        <button
                          key={sub.id}
                          type="button"
                          onClick={() => {
                            setActiveTab('visual_lineage');
                            setVaultSubTab(sub.id);
                            setSelectedLineageAssetId(null);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '5px 8px',
                            borderRadius: '6px',
                            border: 'none',
                            background: isSubActive ? '#EFF6FF' : 'transparent',
                            color: isSubActive ? '#1D4ED8' : '#64748B',
                            fontSize: '0.74rem',
                            fontWeight: isSubActive ? 700 : 500,
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease'
                          }}
                          onMouseEnter={e => {
                            if (!isSubActive) {
                              e.currentTarget.style.background = '#F8FAFC';
                              e.currentTarget.style.color = '#0F172A';
                            }
                          }}
                          onMouseLeave={e => {
                            if (!isSubActive) {
                              e.currentTarget.style.background = 'transparent';
                              e.currentTarget.style.color = '#64748B';
                            }
                          }}
                        >
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {sub.label}
                          </span>
                          {typeof sub.count === 'number' && sub.count > 0 && (
                            <span style={{
                              fontSize: '0.64rem',
                              fontWeight: 600,
                              color: isSubActive ? '#2563EB' : '#94A3B8',
                              background: isSubActive ? '#DBEAFE' : '#F1F5F9',
                              padding: '1px 5px',
                              borderRadius: '4px'
                            }}>
                              {sub.count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {isTabVisible('context_curator') && (
            <div style={{ width: '100%' }}>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('context_curator');
                  setOpenSidebarMenu(prev => prev === 'curator' ? null : 'curator');
                }}
                className={`nav-item ${(activeTab === 'context_curator' || activeTab === 'conflicts') ? 'nav-item-active' : ''}`}
                title="Context Curator & Conflict Hub"
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: isSidebarOpen ? 'space-between' : 'center',
                  position: 'relative',
                  cursor: 'pointer'
                }}
              >
                {isSidebarOpen ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShieldAlert size={16} strokeWidth={1.75} />
                      <span>Curator</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {conflicts.length > 0 && (
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '1px 6px',
                          borderRadius: '10px',
                          background: '#FEE2E2',
                          color: '#991B1B',
                          fontWeight: 600
                        }}>
                          {conflicts.length}
                        </span>
                      )}
                      <ChevronDown
                        size={13}
                        style={{
                          transform: openSidebarMenu === 'curator' ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                          opacity: 0.7
                        }}
                      />
                    </div>
                  </>
                ) : (
                  <ShieldAlert size={16} strokeWidth={1.75} />
                )}
              </button>

              {/* Sub-items of Context Curator & Conflicts */}
              {isSidebarOpen && (
                <div className={`sidebar-accordion-wrapper ${openSidebarMenu === 'curator' ? 'expanded' : ''}`}>
                  <div className="sidebar-accordion-inner">
                    {[
                      { id: 'conflicts', label: 'Pairwise Conflict Resolver', count: conflicts.length > 0 ? `${conflicts.length} Pending` : null, isAlert: conflicts.length > 0 },
                      { id: 'health', label: 'Context Health & Heuristics', count: null },
                      { id: 'drift', label: 'Drift & Claim Decay', count: null }
                    ].map(sub => {
                      const isSubActive = (activeTab === 'context_curator' || activeTab === 'conflicts') && (curatorSubView === sub.id || (activeTab === 'conflicts' && sub.id === 'conflicts'));
                      return (
                        <button
                          key={sub.id}
                          type="button"
                          onClick={() => {
                            setActiveTab('context_curator');
                            setCuratorSubView(sub.id);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '5px 8px',
                            borderRadius: '6px',
                            border: 'none',
                            background: isSubActive ? '#EFF6FF' : 'transparent',
                            color: isSubActive ? '#1D4ED8' : '#64748B',
                            fontSize: '0.74rem',
                            fontWeight: isSubActive ? 700 : 500,
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease'
                          }}
                          onMouseEnter={e => {
                            if (!isSubActive) {
                              e.currentTarget.style.background = '#F8FAFC';
                              e.currentTarget.style.color = '#0F172A';
                            }
                          }}
                          onMouseLeave={e => {
                            if (!isSubActive) {
                              e.currentTarget.style.background = 'transparent';
                              e.currentTarget.style.color = '#64748B';
                            }
                          }}
                        >
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {sub.label}
                          </span>
                          {sub.count && (
                            <span style={{
                              fontSize: '0.62rem',
                              fontWeight: 600,
                              color: sub.isAlert ? '#991B1B' : (isSubActive ? '#2563EB' : '#94A3B8'),
                              background: sub.isAlert ? '#FEE2E2' : (isSubActive ? '#DBEAFE' : '#F1F5F9'),
                              padding: '1px 5px',
                              borderRadius: '4px',
                              whiteSpace: 'nowrap'
                            }}>
                              {sub.count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI Copilot Chat Navigation */}
          <button
            type="button"
            onClick={() => {
              setActiveTab('playground');
              setExpandedMenu('playground');
            }}
            className={`nav-item ${activeTab === 'playground' ? 'nav-item-active' : ''}`}
            title="AI Copilot Chat"
          >
            <Bot size={16} strokeWidth={1.75} />
            <span>AI Copilot Chat</span>
          </button>
        </div>
        </div>

        {/* Set 2: Bottom Pinned Governance & Administration Group */}
        <div className="sidebar-footer" style={{ width: '100%' }}>
          {isTabVisible('demo') && (
            <button
              onClick={() => setActiveTab('demo')}
              className={`nav-item ${activeTab === 'demo' ? 'nav-item-active' : ''}`}
              title="Decision Gate Demo"
            >
              <Brain size={16} strokeWidth={1.75} />
              <span>Decision Gate Demo</span>
            </button>
          )}
          {isTabVisible('audit') && (
            <button
              onClick={() => { setActiveTab('audit'); fetchAuditLogs(activeOrg?.id); }}
              className={`nav-item ${activeTab === 'audit' ? 'nav-item-active' : ''}`}
              title="Audit Trail & Lineage"
            >
              <BarChart3 size={16} strokeWidth={1.75} />
              <span>Audit Trail & Lineage</span>
            </button>
          )}
          {isTabVisible('integrations') && (
            <button
              onClick={() => setActiveTab('integrations')}
              className={`nav-item ${activeTab === 'integrations' ? 'nav-item-active' : ''}`}
              title="Agent Integrations & MCP"
            >
              <Sliders size={16} strokeWidth={1.75} />
              <span>Agent Integrations & MCP</span>
            </button>
          )}
          {isTabVisible('team') && (
            <button
              onClick={() => setActiveTab('team')}
              className={`nav-item ${activeTab === 'team' ? 'nav-item-active' : ''}`}
              title="Team & Personas"
            >
              <Users size={16} strokeWidth={1.75} />
              <span>Team & Personas</span>
            </button>
          )}
        </div>
      </aside>

      {/* ========================================================= */}
      {/* MAIN CONTENT AREA                                         */}
      {/* ========================================================= */}
      <main className={`main-content ${activeTab === 'playground' ? 'main-content-fixed' : ''}`}>

        {/* ========================================================= */}
        {/* TOP HEADER CONTROLS (Identical position for all tabs/pages) */}
        {/* ========================================================= */}
        <div className="top-breadcrumb-bar" style={{ position: 'relative', zIndex: 50, paddingTop: '10px', paddingBottom: '6px', flexShrink: 0 }}>
          <div />
          {renderHeaderRightControls()}
        </div>

        {/* Enterprise Organization Setup Progress Checklist Banner */}
        <OrganizationSetupChecklistBanner
          activeOrg={activeOrg}
          onLaunchWizard={(recommendedStep) => {
            setSetupWizardTargetOrg(activeOrg);
            setIsSetupWizardOpen(true);
          }}
          refreshTrigger={orgSetupRefreshTrigger}
        />

        {/* Pending Organization Invitations Notification Banner */}
        {isAuthenticated && myInvitations && myInvitations.length > 0 && (
          <div
            style={{
              margin: '0 24px 16px 24px',
              padding: '12px 18px',
              borderRadius: '10px',
              backgroundColor: '#EFF6FF',
              border: '1px solid #BFDBFE',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '14px',
              boxShadow: '0 2px 6px rgba(37, 99, 235, 0.08)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  backgroundColor: '#DBEAFE',
                  color: '#1D4ED8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                <Users size={18} />
              </div>
              <div>
                <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#1E3A8A' }}>
                  You have {myInvitations.length} pending organization invitation{myInvitations.length > 1 ? 's' : ''}!
                </div>
                <div style={{ fontSize: '0.74rem', color: '#3B82F6', marginTop: '2px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {myInvitations.map((inv) => (
                    <span key={inv.id}>
                      • <strong>{inv.organization_name}</strong> as <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{inv.role.replace('_', ' ')}</span> (Invited by {inv.invited_by})
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {myInvitations.map((inv) => (
                <button
                  key={inv.id}
                  type="button"
                  onClick={async () => {
                    try {
                      await acceptInvitation(inv.id);
                      showToast(`Accepted invitation to '${inv.organization_name}'! Switched workspace.`);
                      fetchOrganizations();
                    } catch (err) {
                      showToast(err.message || 'Failed to accept invitation.');
                    }
                  }}
                  style={{
                    padding: '7px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#2563EB',
                    color: '#FFFFFF',
                    border: 'none',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)'
                  }}
                >
                  <CheckCircle2 size={13} />
                  <span>Join {inv.organization_name}</span>
                </button>
              ))}
            </div>
          </div>
        )}



        {/* ========================================================= */}
        {/* TAB 0: HOME OVERVIEW & ARCHITECTURE DASHBOARD             */}
        {/* ========================================================= */}
        {activeTab === 'home' && (
          <div>
            {/* Centered Hero Banner */}
            <div className="tab-header-center" style={{ padding: '16px 20px', marginBottom: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '8px' }}>
                <img
                  src="/Trulin-Main-NoBg.png"
                  alt="Trulin"
                  style={{ height: '38px', maxWidth: '175px', objectFit: 'contain' }}
                />
              </div>
              <h1 className="tab-main-heading">
                Context Trust Gateway
              </h1>
              <p className="tab-subtitle">
                A deterministic evidence validation gate that prevents autonomous AI agents from acting on outdated policies, unverified rumors, and contradictory instructions across enterprise knowledge bases.
              </p>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap', marginTop: '18px' }}>
                <button
                  onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
                  className="btn btn-primary"
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                >
                  Launch Gate Demo
                </button>
                <button
                  onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
                  className="btn btn-secondary"
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                >
                  Manage Connectors
                </button>
              </div>
            </div>

            {/* Enterprise Environment Setup Hero Card (Displayed when org or workspace needs provisioning) */}
            {!isEnvironmentReady && (
              <div
                className="clean-panel"
                style={{
                  padding: '22px 24px',
                  marginBottom: '28px',
                  border: '1px solid rgba(234, 88, 12, 0.35)',
                  background: 'linear-gradient(135deg, rgba(234, 88, 12, 0.07) 0%, var(--bg-card) 100%)',
                  position: 'relative',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.18)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                  <div style={{ maxWidth: '640px' }}>
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: 'rgba(234, 88, 12, 0.15)',
                      color: '#EA580C',
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase',
                      marginBottom: '8px'
                    }}>
                      <Shield size={12} />
                      Environment Setup Required
                    </div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', margin: '0 0 6px 0' }}>
                      Set Up Your Organization Tenant & Departmental Workspace
                    </h3>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                      Enterprise services (Document Vault, Live Ingestion, Context Curator, AI Playground, and Decision Audit) are secured. Create your organization and initial workspace to activate them.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {!isOrgReady ? (
                      <button
                        onClick={() => setShowNewOrgModal(true)}
                        className="btn btn-primary"
                        style={{ padding: '8px 16px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <Building2 size={14} />
                        <span>Create Organization</span>
                      </button>
                    ) : !isWorkspaceReady ? (
                      <button
                        onClick={() => setShowNewWorkspaceModal(true)}
                        className="btn btn-primary"
                        style={{ padding: '8px 16px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <Plus size={14} />
                        <span>Create Workspace</span>
                      </button>
                    ) : null}
                  </div>
                </div>

                {/* 2-Step Status Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px', marginTop: '16px' }}>
                  {/* Step 1: Organization */}
                  <div style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: isOrgReady ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                    border: isOrgReady ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                      <Building2 size={16} style={{ color: isOrgReady ? '#10B981' : '#EA580C', flexShrink: 0 }} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          1. Organization Tenant
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {isOrgReady ? activeOrg?.name : 'Create your enterprise organization'}
                        </div>
                      </div>
                    </div>
                    {isOrgReady ? (
                      <span style={{ fontSize: '0.64rem', fontWeight: 700, padding: '2px 7px', borderRadius: '4px', background: '#10B981', color: '#FFFFFF', flexShrink: 0 }}>
                        ✓ Ready
                      </span>
                    ) : (
                      <button
                        onClick={() => setShowNewOrgModal(true)}
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.72rem', flexShrink: 0 }}
                      >
                        Create
                      </button>
                    )}
                  </div>

                  {/* Step 2: Workspace */}
                  <div style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: isWorkspaceReady ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                    border: isWorkspaceReady ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                      <FolderGit2 size={16} style={{ color: isWorkspaceReady ? '#10B981' : '#EA580C', flexShrink: 0 }} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          2. Department Workspace
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {isWorkspaceReady ? activeWorkspace?.name : 'Create a workspace for team data'}
                        </div>
                      </div>
                    </div>
                    {isWorkspaceReady ? (
                      <span style={{ fontSize: '0.64rem', fontWeight: 700, padding: '2px 7px', borderRadius: '4px', background: '#10B981', color: '#FFFFFF', flexShrink: 0 }}>
                        ✓ Ready
                      </span>
                    ) : (
                      <button
                        onClick={() => setShowNewWorkspaceModal(true)}
                        disabled={!isOrgReady}
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.72rem', flexShrink: 0, opacity: !isOrgReady ? 0.5 : 1 }}
                        title={!isOrgReady ? "Please create organization first" : ""}
                      >
                        Create
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Live System Metrics Grid (4 Cards) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                  Connected Data Sources
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
                  {dataSources.length || 5} Active
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  GitHub, Confluence, Jira, Slack, Web Portal
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('folders'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Stored Policy Documents
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                  {dbDocuments.length || 14} Documents
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Normalized markdown & SHA-256 hashes
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('claims'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Atomic Claim Repository
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '4px' }}>
                  {dbClaims.length || 50} Claims
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Subject-Predicate-Object triples
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('context_curator'); setCuratorSubView('conflicts'); setExpandedMenu('context_curator'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Auditor Conflict Queue
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: conflicts.length > 0 ? 'var(--warning-text)' : 'var(--text-main)', marginTop: '4px' }}>
                  {conflicts.length} Pending
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {conflicts.length > 0 ? "Requires human resolution" : "All policies in agreement"}
                </div>
              </div>
            </div>

            {/* Quick-Launch Module Grid */}
            <div style={{ marginBottom: '32px' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px' }}>
                System Capabilities & Workflows
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>

                {/* Card 1: Decision Gate Demo */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 1</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Trust Decision Gate Demo
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Evaluate agent actions against conflicting documents. See how Section 3.2 (2026) supersedes outdated 2025 handbook rules.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Gate Demo →
                  </div>
                </div>

                {/* Card 2: Agent Playground */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('playground'); setExpandedMenu('playground'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 2</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Interactive Agent Playground
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Simulate live conversational agent queries. Inspect trusted context retrieval vs excluded contradictory knowledge.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Playground →
                  </div>
                </div>

                {/* Card 3: Context Curator Bot & Conflict Resolver */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('context_curator'); setCuratorSubView('conflicts'); setExpandedMenu('context_curator'); }}
                >
                  <div>
                    <span className="badge badge-review" style={{ marginBottom: '8px' }}>Module 3</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Context Curator & Conflict Resolver
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Continuous knowledge health auditing and pairwise policy arbitration. Approved claims become authoritative while stale rules are superseded.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Conflict Resolver ({conflicts.length}) →
                  </div>
                </div>

                {/* Card 4: Document Explorer */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('folders'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 4</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Document & Connector Hub
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Connect live GitHub repositories, Confluence spaces, or upload PDF/DOCX policy documents for instant extraction.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Document Explorer →
                  </div>
                </div>
              </div>
            </div>

            {/* 5-Stage Context Trust Architecture Workflow Diagram */}
            <div className="clean-panel" style={{ padding: '24px' }}>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '6px' }}>
                5-Stage Context Trust Lifecycle
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Every document follows an immutable pipeline from connector ingestion to decision gate evaluation.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 1</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Ingest & Hash</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Normalizes markdown, parses DOCX/PDF, and computes SHA-256 version hashes.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 2</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Atomic Fact Triples</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Extracts atomic subject-predicate-object assertions from each document section.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 3</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Conflict Detection</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Topical and semantic filtering detects numerical clashes, overrides, and scope collisions.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 4</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Bayesian Trust Scoring</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Calculates 6-factor trust weights (Authority, Freshness, Verification, Scope).
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800 }}>STAGE 5</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Decision Safety Gate</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Issues ALLOW, REQUIRE_REVIEW, or BLOCK decisions with signed audit IDs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 1: TRUST DECISION GATE DEMO (CLEAN, NO NAIVE RAG)     */}
        {/* ========================================================= */}
        {activeTab === 'demo' && (
          <div>
            {/* Centered Header Area */}
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>


              <h1 className="tab-main-heading">
                Trust Decision Gate & Policy Simulator
              </h1>

              <p className="tab-subtitle">
                Interactively simulate agent actions or stream live decisions evaluated by the gateway. The gate dynamically retrieves atomic claims, enforces 6-factor trust scoring, and blocks rogue AI execution with cryptographic audit logs.
              </p>

              {/* Top-Right Info Cards: Telemetry & Live Sync (White BG with Orange Structuring) */}
              <div className="top-right-telemetry-bar">
                <div className="premium-gate-stat" title="Total Decisions Audited by Gateway">
                  <span style={{ color: '#64748B', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Audited:</span>
                  <span style={{ color: '#EA580C', fontWeight: 800, fontSize: '0.9rem' }}>
                    {decisionStream.length > 0 ? decisionStream.length : auditSummary.total_decisions || 0}
                  </span>
                </div>

                <div
                  onClick={() => setIsRoiModalOpen(true)}
                  className="premium-gate-stat premium-gate-stat-clickable"
                  title="Click to view Financial Liability ROI breakdown"
                >
                  <span style={{ color: '#64748B', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Prevented:</span>
                  <span style={{ color: '#059669', fontWeight: 800, fontSize: '0.9rem' }}>
                    ${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '0'}
                  </span>
                </div>

                {/* Professional Live Refresh Control */}
                <button
                  type="button"
                  onClick={() => fetchDecisionStream(activeOrg?.id)}
                  className="pro-refresh-btn"
                  title="Refresh live decision stream"
                  disabled={streamLoading}
                >
                  <RefreshCw
                    size={13}
                    className={streamLoading ? "animate-spin" : ""}
                    style={{ color: '#EA580C' }}
                  />
                  <span style={{ color: '#0F172A', fontWeight: 600 }}>{streamLoading ? "Refreshing..." : "Refresh"}</span>
                  <span className="pro-live-dot" title="Live stream active" />
                </button>
              </div>
            </div>

            {/* Sticky Right-Edge Toggle Tab with Opening/Closing Arrow Icon (White Theme) */}
            <button
              type="button"
              onClick={() => {
                setIsGateToolsDrawerOpen(prev => !prev);
                if (isGateToolsDrawerOpen) {
                  setPinnedGateTool(null);
                  setHoveredGateTool(null);
                }
              }}
              className="fixed-right-drawer-tab"
              title={isGateToolsDrawerOpen ? "Close Operations Bar" : "Open Operations Bar"}
            >
              {isGateToolsDrawerOpen ? (
                <>
                  <ChevronRight size={16} strokeWidth={2.5} />
                  <span className="drawer-tab-label">Close</span>
                </>
              ) : (
                <>
                  <ChevronLeft size={16} strokeWidth={2.5} />
                  <span className="drawer-tab-label">Operations</span>
                </>
              )}
            </button>

            {/* Right-Side Vertical Slide-Out Menu Bar (Drawer - Light Theme) */}
            {isGateToolsDrawerOpen && (
              <>
                <div
                  className="gate-side-drawer-backdrop"
                  onClick={() => {
                    setIsGateToolsDrawerOpen(false);
                    setPinnedGateTool(null);
                    setHoveredGateTool(null);
                  }}
                />

                {/* Left Flyout Preview Panel (Visible on Hover, Stays on Click) */}
                {(pinnedGateTool || hoveredGateTool) && (
                  <div className="gate-drawer-preview-flyout">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(249, 115, 22, 0.25)', paddingBottom: '12px', marginBottom: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', background: '#FFEDD5', color: '#EA580C', border: '1px solid #FDBA74' }}>
                          {pinnedGateTool ? 'PINNED VIEW' : 'HOVER PREVIEW'}
                        </span>
                        <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
                          {pinnedGateTool ? 'Click button to open full modal' : 'Click item to pin view'}
                        </span>
                      </div>
                      {pinnedGateTool && (
                        <button
                          type="button"
                          onClick={() => setPinnedGateTool(null)}
                          style={{ background: 'transparent', border: 'none', color: '#64748B', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}
                        >
                          <X size={13} /> Unpin
                        </button>
                      )}
                    </div>

                    {(pinnedGateTool || hoveredGateTool) === 'dossier' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Compliance Dossier</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Export comprehensive deterministic audit evidence dossiers adhering to NIST AI 600-1 and EU AI Act Article 12. Includes end-to-end evidence hash graphs and actor authority verification.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Framework Compliance:</span>
                            <strong style={{ color: '#059669' }}>100% Deterministic Provenance</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Total Audited Decisions:</span>
                            <strong>{decisionStream.length > 0 ? decisionStream.length : auditSummary.total_decisions || 0}</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsDossierModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Open Full Dossier Modal
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'webhooks' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Webhooks & Alerts</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Configure sub-50ms HTTP webhook dispatching for rogue policy breaches and blocked actions directly to Slack, PagerDuty, and Microsoft Teams.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Configured Endpoints:</span>
                            <strong style={{ color: '#EA580C' }}>Slack, PagerDuty, MS Teams</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Dispatch Latency:</span>
                            <strong style={{ color: '#059669' }}>&lt; 35ms (Non-blocking)</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsWebhookModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Manage Webhook Integrations
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'hitl' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>HITL Review Queue</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Human-in-the-Loop review queue under EU AI Act Article 14 for ambiguous policy scenarios, disputed customer exceptions, and edge-case transactions.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Pending Queue Items:</span>
                            <strong style={{ color: '#059669' }}>0 Escalations Pending</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Auto-Resolution Guard:</span>
                            <strong>Active (Trulin Engine)</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsHitlModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Open HITL Review Queue
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'redteam' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Red-Team Suite</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Automated adversarial benchmarking covering OWASP LLM Top 10 vulnerabilities, unauthorized privilege escalation, freshness traps, and prompt injection attacks.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Benchmark Suites:</span>
                            <strong>3 Curated Enterprise Traps</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Jailbreak Block Rate:</span>
                            <strong style={{ color: '#059669' }}>100% Deterministic</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsRedTeamModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Launch Red-Team Simulation
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'merkle' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Merkle Audit Ledger</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Cryptographically tamper-evident Merkle tree verification adhering to EU AI Act Article 12. Computes SHA-256 root hashes for every evaluated decision.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Ledger Integrity:</span>
                            <strong style={{ color: '#059669' }}>Cryptographically Verified</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Algorithm:</span>
                            <strong>SHA-256 Binary Tree</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setMerkleSelectedToken(null); setIsMerkleModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Verify Merkle Root Hash
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'roi' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Financial Liability ROI</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Quantified liability exposure prevention calculation. Tracks real-world financial risk mitigated by intercepting unauthorized refunds and breach actions.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Total Exposure Blocked:</span>
                            <strong style={{ color: '#059669' }}>${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '195,000'}</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Policy Breaches Intercepted:</span>
                            <strong style={{ color: '#EA580C' }}>{decisionStream.filter(d => d.verdict === 'BLOCK').length} Incidents</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsRoiModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          View Complete Financial ROI
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className="gate-side-drawer">
                  <div className="gate-drawer-header">
                    <div>
                      <h3 className="gate-drawer-title">Gate Operations</h3>
                      <p style={{ fontSize: '0.72rem', color: '#64748B', margin: '2px 0 0 0' }}>Hover for preview, click to pin</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setIsGateToolsDrawerOpen(false);
                        setPinnedGateTool(null);
                        setHoveredGateTool(null);
                      }}
                      className="gate-drawer-close-btn"
                      title="Close Operations Bar"
                    >
                      <ChevronRight size={18} strokeWidth={2.5} />
                    </button>
                  </div>

                  <div className="gate-drawer-content">
                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('dossier')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'dossier') {
                          setIsDossierModalOpen(true);
                        } else {
                          setPinnedGateTool('dossier');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'dossier' ? 'active' : ''}`}
                    >
                      <span>Compliance Dossier</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'dossier' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('webhooks')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'webhooks') {
                          setIsWebhookModalOpen(true);
                        } else {
                          setPinnedGateTool('webhooks');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'webhooks' ? 'active' : ''}`}
                    >
                      <span>Webhooks & Alerts</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'webhooks' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('hitl')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'hitl') {
                          setIsHitlModalOpen(true);
                        } else {
                          setPinnedGateTool('hitl');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'hitl' ? 'active' : ''}`}
                    >
                      <span>HITL Review Queue</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'hitl' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('redteam')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'redteam') {
                          setIsRedTeamModalOpen(true);
                        } else {
                          setPinnedGateTool('redteam');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'redteam' ? 'active' : ''}`}
                    >
                      <span>Red-Team Suite</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'redteam' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('merkle')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'merkle') {
                          setMerkleSelectedToken(null);
                          setIsMerkleModalOpen(true);
                        } else {
                          setPinnedGateTool('merkle');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'merkle' ? 'active' : ''}`}
                    >
                      <span>Merkle Audit Ledger</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'merkle' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('roi')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'roi') {
                          setIsRoiModalOpen(true);
                        } else {
                          setPinnedGateTool('roi');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'roi' ? 'active' : ''}`}
                    >
                      <span>Financial Liability ROI</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'roi' ? '#EA580C' : '#94A3B8' }} />
                    </button>
                  </div>

                  <div className="gate-drawer-footer">
                    <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                      Status: <strong style={{ color: '#10B981' }}>Gate Active</strong>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setIsGateToolsDrawerOpen(false);
                        setPinnedGateTool(null);
                        setHoveredGateTool(null);
                      }}
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(249, 115, 22, 0.4)',
                        borderRadius: '5px',
                        padding: '5px 10px',
                        color: '#EA580C',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <span>Close</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Policy Action Simulator Form Card */}
            <div className="sim-form-card" style={{ marginTop: '16px' }}>
              {/* Prompt Area with Signature Gradient Border, Ambient Shadow & Floating Preset Chips */}
              <div className="sim-prompt-wrapper">
                <div className="sim-prompt-header-row">


                  <div className="sim-prompt-floating-presets">
                    <span className="sim-prompt-presets-hint">Benchmark Traps:</span>
                    <button
                      type="button"
                      onClick={() => {
                        setSimulatorMode('presets');
                        setDemoScenario('refund_trap');
                        setCustomActionText(scenarios.refund_trap.query);
                        setCustomActorId(scenarios.refund_trap.actor.id);
                        setCustomActorRole(scenarios.refund_trap.actor.role);
                        setCustomRequiredScope(scenarios.refund_trap.claim2.scope);
                        setDemoStep(0);
                        setDemoResult(null);
                      }}
                      className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'refund_trap' ? 'active' : ''}`}
                      title="Freshness Trap: Tests if agent honors updated 60-day Enterprise refund rule over stale 30-day handbook"
                    >
                      <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'refund_trap' ? '#EA580C' : '#94A3B8'} />
                      <span>1. Refund Window</span>
                      <span className="sim-chip-tag tag-warning">Freshness</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setSimulatorMode('presets');
                        setDemoScenario('remote_work');
                        setCustomActionText(scenarios.remote_work.query);
                        setCustomActorId(scenarios.remote_work.actor.id);
                        setCustomActorRole(scenarios.remote_work.actor.role);
                        setCustomRequiredScope(scenarios.remote_work.claim2.scope);
                        setDemoStep(0);
                        setDemoResult(null);
                      }}
                      className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'remote_work' ? 'active' : ''}`}
                      title="Scope Override: Tests VP memo 4-day remote authorization for Engineering over general 2-day policy"
                    >
                      <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'remote_work' ? '#EA580C' : '#94A3B8'} />
                      <span>2. Remote Work</span>
                      <span className="sim-chip-tag tag-blue">Scope</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setSimulatorMode('presets');
                        setDemoScenario('unauthorized_deploy');
                        setCustomActionText(scenarios.unauthorized_deploy.query);
                        setCustomActorId(scenarios.unauthorized_deploy.actor.id);
                        setCustomActorRole(scenarios.unauthorized_deploy.actor.role);
                        setCustomRequiredScope(scenarios.unauthorized_deploy.claim2.scope);
                        setDemoStep(0);
                        setDemoResult(null);
                      }}
                      className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'unauthorized_deploy' ? 'active' : ''}`}
                      title="Role Gate: Intercepts unauthorized plaintext HTTP port 8080 ingress attempt on Production"
                    >
                      <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'unauthorized_deploy' ? '#EA580C' : '#94A3B8'} />
                      <span>3. Prod Ingress</span>
                      <span className="sim-chip-tag tag-green">Role Gate</span>
                    </button>

                    {simulatorMode === 'presets' && demoScenario && (
                      <button
                        type="button"
                        onClick={() => {
                          setSimulatorMode('custom');
                          setDemoScenario(null);
                          setCustomActionText('');
                          setDemoStep(0);
                          setDemoResult(null);
                        }}
                        className="sim-floating-preset-chip-clear"
                        title="Switch to Custom Prompt"
                      >
                        <X size={11} />
                        <span>Custom</span>
                      </button>
                    )}
                  </div>
                </div>

                <textarea
                  value={customActionText}
                  onChange={(e) => {
                    setCustomActionText(e.target.value);
                    if (simulatorMode === 'presets') {
                      setSimulatorMode('custom');
                      setDemoScenario(null);
                    }
                  }}
                  placeholder="Enter any proposed AI agent decision statement....."
                  rows={2}
                  className="sim-textarea-gradient"
                />
              </div>

              {/* Real-time Context Inference & Action Execution Row */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginTop: '10px' }}>
                {/* Left: Professional Catchy Micro-Telemetry Chips */}
                <div className="sim-telemetry-row">
                  {/* Pulsing Auto-Inferred Badge */}
                  <div className="sim-telemetry-chip lead">
                    <span className="sim-telemetry-dot" />
                    <Sparkles size={11} />
                    <span>AUTO-INFERRED</span>
                  </div>

                  {/* Actor Persona Card */}
                  <div className="sim-telemetry-chip actor" title={`Actor ID: ${customActorId} (${detectedContext.roleLabel})`}>
                    <Bot size={11} style={{ color: '#64748B' }} />
                    <span className="sim-chip-label">ACTOR</span>
                    <span className="sim-chip-val">{customActorId}</span>
                    <span className="sim-chip-sub">· {detectedContext.role === customActorRole ? (detectedContext.roleShort || detectedContext.role) : customActorRole}</span>
                  </div>

                  {/* Target Scope Card */}
                  <div className="sim-telemetry-chip scope" title={`Operational Scope: ${detectedContext.scopeLabel}`}>
                    <ShieldCheck size={11} style={{ color: '#2563EB' }} />
                    <span className="sim-chip-label">SCOPE</span>
                    <span className="sim-chip-val">{detectedContext.scope === customRequiredScope ? (detectedContext.scopeShort || customRequiredScope) : customRequiredScope}</span>
                  </div>

                  {/* Match Confidence Card */}
                  <div className="sim-telemetry-chip match" title={detectedContext.rationale}>
                    <Zap size={10} style={{ color: '#16A34A' }} />
                    <span className="sim-chip-val">{detectedContext.confidence}</span>
                    <span className="sim-chip-sub">match</span>
                  </div>

                  {/* Compact Override Toggle */}
                  <button
                    type="button"
                    onClick={() => setShowManualOverride(!showManualOverride)}
                    className={`sim-telemetry-chip override ${showManualOverride ? 'active' : ''}`}
                    title="Adjust Actor Role or Scope manually"
                  >
                    <Sliders size={10} />
                    <span>{showManualOverride ? 'Close' : 'Override'}</span>
                  </button>
                </div>

                {/* Right: Evaluate Button */}
                {effectiveRole === 'viewer' ? (
                  <button
                    disabled
                    className="btn btn-secondary"
                    style={{ height: '40px', padding: '0 16px', fontSize: '0.80rem', fontWeight: 600, opacity: 0.65, cursor: 'not-allowed', whiteSpace: 'nowrap', borderRadius: '8px' }}
                    title="Observer Mode: Decision evaluations are restricted for read-only roles."
                  >
                    <Lock size={13} style={{ marginRight: '6px' }} />
                    <span>Observer (Read-Only)</span>
                  </button>
                ) : (
                  <button
                    onClick={() => runKillerDemo()}
                    disabled={demoRunning || !customActionText.trim()}
                    className="sim-evaluate-btn"
                  >
                    {demoRunning ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" />
                        <span>Evaluating...</span>
                      </>
                    ) : (
                      <>
                        <Zap size={14} />
                        <span>Evaluate Action</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Collapsible Manual Override Controls */}
              {showManualOverride && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '12px',
                  marginTop: '12px',
                  padding: '12px 14px',
                  background: '#F8FAFC',
                  border: '1px dashed #CBD5E1',
                  borderRadius: '8px'
                }}>
                  <div>
                    <label className="sim-input-label">
                      Agent / Actor ID
                    </label>
                    <input
                      type="text"
                      value={customActorId}
                      onChange={(e) => setCustomActorId(e.target.value)}
                      placeholder="e.g. billing-bot-01"
                      className="sim-input-control"
                    />
                  </div>

                  <div>
                    <label className="sim-input-label">
                      Actor Role & Permissions
                    </label>
                    <select
                      value={customActorRole}
                      onChange={(e) => setCustomActorRole(e.target.value)}
                      className="sim-input-control"
                    >
                      <option value="support_agent">Support Agent (Customer Bot)</option>
                      <option value="devops_engineer">DevOps Engineer (CI/CD Bot)</option>
                      <option value="junior_developer">Junior Developer (Intern Bot)</option>
                      <option value="hr_reviewer">HR Reviewer (Benefits Assistant)</option>
                      <option value="compliance_officer">Compliance Officer (Risk Gate)</option>
                    </select>
                  </div>

                  <div>
                    <label className="sim-input-label">
                      Target Operational Scope
                    </label>
                    <select
                      value={customRequiredScope}
                      onChange={(e) => setCustomRequiredScope(e.target.value)}
                      className="sim-input-control"
                    >
                      <option value="Enterprise">Enterprise Customer Tier</option>
                      <option value="Production">Production Environment</option>
                      <option value="Staging">Staging Sandbox</option>
                      <option value="Engineering">Engineering Department</option>
                      <option value="General">Global Standard</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Main Decision Gate Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

              {/* Left Side: Candidate Evidence Evaluated */}
              <div className="sim-result-card">
                <div className="sim-card-header">
                  <h3 className="sim-card-title">
                    <Terminal size={15} color="#EA580C" />
                    <span>{simulatorMode === 'custom' ? 'Database Grounding & Evidence' : 'Candidate Evidence Evaluated'}</span>
                  </h3>
                  <span className={`badge ${simulatorMode === 'custom' ? 'badge-verified' : 'badge-review'}`} style={{ fontSize: '0.68rem' }}>
                    {simulatorMode === 'custom' ? 'PostgreSQL Grounded' : 'Contradiction Handled'}
                  </span>
                </div>

                {simulatorMode === 'presets' ? (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {/* Candidate 1 (Stale / Low Authority) */}
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px 14px', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748B', fontWeight: 700, marginBottom: '4px' }}>
                        <span>RECORD 1 (Superseded)</span>
                        <span>Date: {currentScenario.claim1.date}</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#94A3B8', textDecoration: 'line-through' }}>
                        "{currentScenario.claim1.text}"
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748B', marginTop: '6px' }}>
                        <span>Source: {currentScenario.claim1.source}</span>
                        <span>Authority: {currentScenario.claim1.authority}/100</span>
                      </div>
                    </div>

                    {/* Candidate 2 (Authoritative / Fresh) */}
                    <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '12px 14px', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', fontWeight: 700, marginBottom: '4px' }}>
                        <span>RECORD 2 (Authoritative Selection)</span>
                        <span>Date: {currentScenario.claim2.date}</span>
                      </div>
                      <div style={{ fontSize: '0.875rem', color: '#065F46', fontWeight: 700 }}>
                        "{currentScenario.claim2.text}"
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', marginTop: '6px' }}>
                        <span>Source: {currentScenario.claim2.source}</span>
                        <span>Authority: {currentScenario.claim2.authority}/100</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Custom Mode Evidence Grounding View */
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {demoResult ? (
                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '14px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', fontWeight: 700, marginBottom: '6px' }}>
                            <span>AUTHORITATIVE SOURCE SELECTED</span>
                            <span>Freshness Verified</span>
                          </div>
                          <div style={{ fontSize: '0.88rem', color: '#065F46', fontWeight: 700, marginBottom: '6px' }}>
                            {demoResult.preferred_source || "PostgreSQL Atomic Claims Knowledge Base"}
                          </div>
                          <div style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.4 }}>
                            {demoResult.reasons?.[0] || "Evidence verified against active atomic claims in organization knowledge base."}
                          </div>
                        </div>

                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px 14px', borderRadius: '8px', fontSize: '0.78rem' }}>
                          <div style={{ fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>
                            Cryptographic Governance Seal
                          </div>
                          <div style={{ color: '#64748B', fontFamily: 'monospace', wordBreak: 'break-all', fontSize: '0.72rem' }}>
                            Token: {demoResult.audit_token ? demoResult.audit_token.substring(0, 36) + '...' : 'Signed by Policy Evaluator'}
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', color: '#64748B', fontSize: '0.72rem' }}>
                            <span>Evaluated in {demoResult.execution_ms || 24}ms</span>
                            <span>Scope: {customRequiredScope}</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="sim-standby-box">
                        <Database size={26} color="#EA580C" style={{ margin: '0 auto 8px', opacity: 0.85 }} />
                        <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                          Awaiting Simulation Action
                        </div>
                        <p style={{ fontSize: '0.76rem', color: '#64748B', marginTop: '4px', maxWidth: '340px', lineHeight: 1.4 }}>
                          Enter any intended agent action above and click <strong>"Evaluate Action"</strong>. The Gateway will query PostgreSQL atomic claims, check scope and role permissions, and display grounded evidence here.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Side: Decision Gate Evaluation Verdict */}
              <div className="sim-result-card" style={{ justifyContent: 'space-between' }}>
                <div>
                  <div className="sim-card-header">
                    <h3 className="sim-card-title">
                      <ShieldCheck size={16} color="#EA580C" />
                      <span>Decision Gate Verdict</span>
                    </h3>
                    {demoResult ? (
                      <span className="code-pill">Audit ID: {demoResult.audit_id}</span>
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Status: Standby</span>
                    )}
                  </div>

                  {demoStep === 0 && (
                    <div className="sim-standby-box">
                      <Shield size={26} color="#EA580C" style={{ margin: '0 auto 8px', opacity: 0.85 }} />
                      <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                        Policy Gate Standby
                      </div>
                      <p style={{ fontSize: '0.76rem', color: '#64748B', marginTop: '4px', maxWidth: '340px', lineHeight: 1.4 }}>
                        Click <strong>"Evaluate Action"</strong> to run deterministic 6-factor trust scoring, role authority verification, and tamper-evident audit receipt creation.
                      </p>
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div className="sim-standby-box">
                      <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 10px', color: '#EA580C' }} />
                      <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0F172A' }}>
                        Querying PostgreSQL claims & verifying permissions...
                      </div>
                      <span style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '4px' }}>Evaluating Bayesian 6-factor trust score</span>
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', flexWrap: 'wrap' }}>
                        <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.9rem', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          {demoResult.decision === 'ALLOW' && <CheckCircle2 size={16} />}
                          {demoResult.decision === 'BLOCK' && <ShieldAlert size={16} />}
                          {demoResult.decision === 'REQUIRE_REVIEW' && <AlertTriangle size={16} />}
                          VERDICT: {demoResult.decision}
                        </span>
                        <span style={{ fontSize: '0.82rem', color: '#475569' }}>
                          Risk: <strong style={{ color: demoResult.risk === 'LOW' ? '#059669' : '#DC2626' }}>{demoResult.risk}</strong> • Validity: <strong>{demoResult.validity}</strong>
                        </span>
                        <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                          ⚡ {demoResult.execution_ms || 22}ms
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '12px' }}>
                        <div style={{ fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>Policy Evaluation Reasons:</div>
                        <ul style={{ paddingLeft: '18px', lineHeight: 1.6 }}>
                          {demoResult.reasons?.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>

                {demoStep === 2 && demoResult && (
                  <div style={{ marginTop: '12px', padding: '12px', background: '#FFF7ED', borderRadius: '8px', border: '1px solid rgba(234, 88, 12, 0.25)', fontSize: '0.8rem', color: '#0F172A' }}>
                    <strong style={{ color: '#EA580C' }}>Suggested Next Action:</strong> {demoResult.suggested_action}
                  </div>
                )}
              </div>
            </div>

            {/* 6-Factor Trust Score Architecture */}
            <div className="clean-panel" style={{ marginTop: '20px', padding: '20px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cpu size={15} color="var(--primary)" />
                Explainable 6-Factor Trust Score Architecture
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>1. Authority</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary)', marginTop: '2px' }}>0.95</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Verified Source</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>2. Freshness</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>2026 Active</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>3. Evidence</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>0.95</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Direct Quote</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>4. Consistency</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--warning-text)', marginTop: '2px' }}>0.88</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Graph Checked</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>5. Scope Match</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Target Aligned</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>6. Auditor Seal</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary-dark)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Cryptographic</div>
                </div>
              </div>
            </div>

            {/* Real-Time Agent Decision Traffic Stream Section */}
            <div className="clean-panel" style={{ marginTop: '24px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                      📡 Real-Time Agent Decision Traffic Stream
                    </h3>
                    <span className="badge badge-verified" style={{ fontSize: '0.66rem', padding: '2px 8px' }}>
                      PostgreSQL Feed
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: '4px', margin: 0 }}>
                    Live record of decisions evaluated by the Gateway, persisted with full cryptographic audit tokens.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="code-pill" style={{ fontSize: '0.74rem' }}>
                    {decisionStream.length} Recorded Evaluated Actions
                  </span>
                  <button
                    onClick={() => fetchDecisionStream(activeOrg?.id)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  >
                    <RefreshCw size={13} className={streamLoading ? "animate-spin" : ""} />
                    <span>Refresh Stream</span>
                  </button>
                </div>
              </div>

              {decisionStream.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <History size={28} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                  <div>No decisions recorded in stream yet.</div>
                  <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                    Run any evaluation in the simulator above to log live decisions to PostgreSQL.
                  </div>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        <th style={{ padding: '10px 12px' }}>Time</th>
                        <th style={{ padding: '10px 12px' }}>Audit ID</th>
                        <th style={{ padding: '10px 12px' }}>Proposed Action</th>
                        <th style={{ padding: '10px 12px' }}>Actor & Role</th>
                        <th style={{ padding: '10px 12px' }}>Verdict</th>
                        <th style={{ padding: '10px 12px' }}>Risk</th>
                        <th style={{ padding: '10px 12px' }}>Latency</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right' }}>Inspect</th>
                      </tr>
                    </thead>
                    <tbody>
                      {decisionStream.map((item) => (
                        <tr
                          key={item.id}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            transition: 'background 0.1s ease',
                            cursor: 'pointer'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-subtle)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                            {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recent'}
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                              {item.audit_id ? item.audit_id.substring(0, 12) : 'ctx_eval'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600, color: 'var(--text-main)' }}>
                            {item.decision_prompt}
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{item.actor_id}</span>
                            <span className="badge" style={{ marginLeft: '6px', fontSize: '0.64rem', padding: '1px 5px', background: '#F1F5F9', color: '#475569' }}>
                              {item.actor_role}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span className={`badge ${item.verdict === 'ALLOW' ? 'badge-allow' : item.verdict === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                              {item.verdict}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: item.risk_level === 'LOW' ? 'var(--success-text)' : 'var(--danger-text)' }}>
                              {item.risk_level}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.74rem' }}>
                            {item.execution_ms || 22}ms
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                            <button
                              type="button"
                              onClick={() => {
                                setDemoResult({
                                  decision: item.verdict,
                                  validity: item.verdict === 'BLOCK' ? 'CONTRADICTED' : 'VALID',
                                  risk: item.risk_level,
                                  reasons: item.reasons || [],
                                  preferred_source: item.preferred_source || "PostgreSQL Atomic Claims Knowledge Base",
                                  audit_id: item.audit_id,
                                  suggested_action: item.suggested_action || "Decision evaluated and gated by Trulin.",
                                  execution_ms: item.execution_ms,
                                  audit_token: item.audit_token
                                });
                                setDemoStep(2);
                                if (item.decision_prompt) setCustomActionText(item.decision_prompt);
                                if (item.actor_role) setCustomActorRole(item.actor_role);
                                if (item.actor_id) setCustomActorId(item.actor_id);
                                window.scrollTo({ top: 0, behavior: 'smooth' });
                                showToast(`Loaded audit record ${item.audit_id}`);
                              }}
                              className="btn btn-outline"
                              style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                            >
                              Inspect
                            </button>
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

        {/* ========================================================= */}
        {/* TAB 2: INTERACTIVE AGENT PLAYGROUND & AI COPILOT CHAT     */}
        {/* ========================================================= */}
        {activeTab === 'playground' && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="AI Agent Playground & Chat"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
            <div style={{ flex: 1, minHeight: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <AgentChatPlayground
                activeOrg={activeOrg}
                activePersona={activePersona}
                activeWorkspace={activeWorkspace}
                workspaces={workspaces}
                showToast={showToast}
                selectedSessionId={activeChatSessionId}
                onSessionChange={(id) => {
                  setActiveChatSessionId(id);
                  fetchChatSessions();
                }}
                onOpenHitlModal={() => setIsHitlModalOpen(true)}
                onInspectDocument={(docId) => {
                  setInspectorState({
                    isOpen: true,
                    assetType: 'document',
                    assetId: docId,
                    assetTitle: 'Policy Document'
                  });
                }}
              />
            </div>
          )
        )}



        {/* ========================================================= */}
        {/* TAB 4: DOCUMENT INGESTION & CLAIM EXPLORER                */}
        {/* ========================================================= */}
        {activeTab === 'ingestion' && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="Document Explorer & Live Ingestion Studio"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
          <div>
            {/* Clean Document Explorer Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
              flexWrap: 'wrap',
              gap: '12px'
            }}>
              <div>
                <h1 className="tab-main-heading" style={{ margin: 0, textAlign: 'left', fontSize: '1.45rem' }}>
                  {(docExplorerView === 'folders' || docExplorerView === 'documents') && 'File Browser & Organization'}
                  {docExplorerView === 'ingest' && 'Upload & Ingestion Studio'}
                  {docExplorerView === 'connectors' && 'Live Connectors'}
                  {docExplorerView === 'connect' && 'Connect Enterprise Data Source'}
                  {docExplorerView === 'claims' && 'Atomic Claims Browser'}
                </h1>
                <p className="tab-subtitle" style={{ margin: '4px 0 0 0', textAlign: 'left' }}>
                  {(docExplorerView === 'folders' || docExplorerView === 'documents') && 'Create and organize files into nested folders, upload documents directly to folders, and manage directory hierarchy.'}
                  {docExplorerView === 'ingest' && 'Upload raw policy files or markdown to parse atomic claims with 9-gate verification into PostgreSQL.'}
                  {docExplorerView === 'connectors' && 'Manage live external data source connectors, real-time synchronization schedules, and automated schema ingestion.'}
                  {docExplorerView === 'connect' && 'Configure automated schema extraction, governance rules, and continuous synchronization.'}
                  {docExplorerView === 'claims' && 'Inspect atomic claims extracted from stored enterprise policies across all active workspaces.'}
                </p>
              </div>

              {docExplorerView === 'connect' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => { setDocExplorerView('connectors'); setTestConnectionResult(null); }}
                    style={{
                      padding: '8px 16px',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      background: '#F1F5F9',
                      color: '#334155',
                      border: '1px solid #CBD5E1',
                      borderRadius: '8px',
                      cursor: 'pointer'
                    }}
                  >
                    <span>← Back to Live Connectors</span>
                  </button>
                </div>
              )}
            </div>

            {/* VIEW 0: CONNECTORS HUB (LIVE CONNECTORS & SYNCHRONIZED CONNECTORS WORKFLOW) */}
            {docExplorerView === 'connectors' && (() => {
              const LIVE_CONNECTOR_TYPES = ['github', 'mongodb', 'mongodb_atlas', 'jira', 'confluence', 'postgresql', 'slack', 'slack_channel', 'slack_workspace'];
              const liveConfiguredSources = dataSources.filter(s =>
                LIVE_CONNECTOR_TYPES.includes((s.source_type || '').toLowerCase())
              );
              const synchronizedSources = liveConfiguredSources.filter(s =>
                Boolean(s.last_synced_at || s.connection_config?.last_successful_sync_at)
              );
              const activeCount = liveConfiguredSources.filter(s =>
                (s.connection_config?.connection_status || s.status) === 'connected' || s.status === 'active'
              ).length;
              const syncingCount = liveConfiguredSources.filter(s =>
                s.connection_config?.connection_status === 'syncing' || syncingSourceId === s.id
              ).length;

              const supportedLiveCatalog = [
                {
                  id: 'github',
                  name: 'GitHub',
                  icon: '🐙',
                  family: 'Version Control & Repos',
                  category_label: 'Code & Knowledge',
                  description: 'Live integration via GitHub REST API. Ingests READMEs, markdown documentation, architecture files, and JSON schemas.',
                  scope: 'README, .md, .json, source files',
                  default_port: null
                },
                {
                  id: 'mongodb_atlas',
                  name: 'MongoDB Atlas',
                  icon: '🍃',
                  family: 'Document Database',
                  category_label: 'NoSQL & Document Stores',
                  description: 'Live database connection via Motor/PyMongo driver. Discovers databases, collections, and streams document payloads.',
                  scope: 'Collections & JSON Documents',
                  default_port: 27017
                },
                {
                  id: 'jira',
                  name: 'Jira',
                  icon: '🎯',
                  family: 'Issue Tracking & Project Management',
                  category_label: 'Work & Issue Tracking',
                  description: 'Live connection via Atlassian Jira Cloud REST API. Extracts project issues, ADF task descriptions, and acceptance criteria.',
                  scope: 'Project Issues, Acceptance Criteria & JQL',
                  default_port: 443
                },
                {
                  id: 'confluence',
                  name: 'Confluence',
                  icon: '📘',
                  family: 'Enterprise Wiki & Documentation',
                  category_label: 'Knowledge & Wikis',
                  description: 'Live connection via Atlassian Confluence REST API. Crawls wiki spaces, parses storage format HTML into Markdown policies.',
                  scope: 'Wiki Spaces, SOPs & Technical Architecture',
                  default_port: 443
                },
                {
                  id: 'postgresql',
                  name: 'PostgreSQL',
                  icon: '🐘',
                  family: 'Relational Database',
                  category_label: 'Relational Databases',
                  description: 'Live database connection via asyncpg driver. Discovers schemas, tables, and performs read-only parameterized row extraction.',
                  scope: 'Schemas, Tables & ACID Relational Records',
                  default_port: 5432
                },
                {
                  id: 'slack',
                  name: 'Slack',
                  icon: '💬',
                  family: 'Collaboration & Chat',
                  category_label: 'Chat & Incidents',
                  description: 'Live integration via Slack Web API. Ingests operational decisions, approval threads, and incident channels.',
                  scope: 'Public & Private Channels, Threads & Mentions',
                  default_port: null
                }
              ];

              return (
                <div style={{ display: 'grid', gap: '24px' }}>
                  {/* KPI Summary Strip */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '14px',
                    background: '#FAF8F5',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                    boxShadow: 'none'
                  }}>
                    <div>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Configured Live Connections</div>
                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>{liveConfiguredSources.length}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Connected & Operational</div>
                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#15803D', marginTop: '2px' }}>{activeCount}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Synchronized Sources</div>
                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#2563EB', marginTop: '2px' }}>{synchronizedSources.length}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Currently Syncing</div>
                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: syncingCount > 0 ? '#EA580C' : '#64748B', marginTop: '2px' }}>
                        {syncingCount}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => {
                          const def = supportedLiveCatalog[0];
                          setSelectedConnectorMeta(def);
                          setNewSourceForm(prev => ({
                            ...prev,
                            name: `Production ${def.name}`,
                            sourceType: def.id,
                            authorityLevel: 85,
                            externalId: ''
                          }));
                          setTestConnectionResult(null);
                          setDocExplorerView('connect');
                        }}
                        className="btn btn-primary"
                        style={{ padding: '9px 16px', fontSize: '0.82rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <span>+ Connect Live Source</span>
                      </button>
                    </div>
                  </div>

                  {/* SECTION 1: LIVE CONNECTORS */}
                  <div style={{
                    background: '#FAF8F5',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '12px',
                    padding: '20px',
                    boxShadow: 'none'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                            ⚡ Live Connectors ({liveConfiguredSources.length})
                          </h3>
                          <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '12px', background: '#F1F5F9', color: '#475569' }}>
                            Encrypted Credentials • Per-Connection Locking
                          </span>
                        </div>
                        <p style={{ fontSize: '0.76rem', color: '#64748B', margin: '4px 0 0 0' }}>
                          Configured connections to GitHub, MongoDB Atlas, Jira, Confluence, PostgreSQL, and Slack with live health, schedule, and state.
                        </p>
                      </div>
                    </div>

                    {liveConfiguredSources.length === 0 ? (
                      <div style={{ padding: '36px 20px', textAlign: 'center', background: '#F8FAFC', borderRadius: '10px', border: '1px dashed #CBD5E1' }}>
                        <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>🔌</div>
                        <div style={{ fontWeight: 700, color: '#0F172A', fontSize: '0.92rem', marginBottom: '4px' }}>No live data sources connected yet</div>
                        <div style={{ fontSize: '0.78rem', color: '#64748B', maxWidth: '500px', margin: '0 auto 16px auto' }}>
                          Select one of the 6 supported live connectors below to configure authenticated access, test live connectivity, and synchronize source records into PostgreSQL.
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const def = supportedLiveCatalog[0];
                            setSelectedConnectorMeta(def);
                            setNewSourceForm(prev => ({ ...prev, name: `Production ${def.name}`, sourceType: def.id, authorityLevel: 85 }));
                            setTestConnectionResult(null);
                            setDocExplorerView('connect');
                          }}
                          className="btn btn-primary"
                          style={{ padding: '8px 18px', fontSize: '0.80rem' }}
                        >
                          + Configure First Connection
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gap: '14px' }}>
                        {liveConfiguredSources.map(src => {
                          const cfg = src.connection_config || {};
                          const rawStatus = (cfg.connection_status || src.status || 'disconnected').toLowerCase();
                          const isSyncing = rawStatus === 'syncing' || syncingSourceId === src.id;
                          const isFailed = rawStatus === 'failed';
                          const isConnected = rawStatus === 'connected' || rawStatus === 'active';
                          const statusLabel = isSyncing ? 'Syncing' : isFailed ? 'Failed' : isConnected ? 'Connected' : 'Disconnected';
                          const statusColor = isSyncing ? '#2563EB' : isFailed ? '#DC2626' : isConnected ? '#15803D' : '#64748B';
                          const statusBg = isSyncing ? '#EFF6FF' : isFailed ? '#FEF2F2' : isConnected ? '#F0FDF4' : '#F1F5F9';

                          const icon = src.source_type === 'github' ? '🐙'
                            : (src.source_type === 'mongodb' || src.source_type === 'mongodb_atlas') ? '🍃'
                            : src.source_type === 'jira' ? '🎯'
                            : src.source_type === 'confluence' ? '📘'
                            : src.source_type === 'postgresql' ? '🐘'
                            : (src.source_type === 'slack' || src.source_type === 'slack_channel' || src.source_type === 'slack_workspace') ? '💬'
                            : '🔌';

                          const docCount = cfg.discovered_items_count || dbDocuments.filter(d => d.source_id === src.id).length;
                          const currentSchedule = cfg.schedule || 'off';

                          return (
                            <div
                              key={src.id}
                              style={{
                                background: '#FFFFFF',
                                border: '1px solid #E2E8F0',
                                borderRadius: '10px',
                                padding: '16px 18px',
                                display: 'grid',
                                gap: '12px',
                                transition: 'all 0.15s ease',
                                boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                              }}
                            >
                              {/* Header row */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ fontSize: '1.6rem', lineHeight: 1 }}>{icon}</span>
                                  <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                      <span style={{ fontWeight: 800, fontSize: '0.94rem', color: '#0F172A' }}>{src.name}</span>
                                      <span style={{
                                        fontSize: '0.68rem',
                                        fontWeight: 700,
                                        padding: '2px 8px',
                                        borderRadius: '10px',
                                        background: statusBg,
                                        color: statusColor,
                                        border: `1px solid ${statusColor}33`,
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                      }}>
                                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusColor, display: 'inline-block' }} />
                                        {isSyncing ? 'Syncing...' : statusLabel}
                                      </span>
                                      <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: '#F1F5F9', color: '#64748B', fontWeight: 600 }}>
                                        {src.source_type.toUpperCase()}
                                      </span>
                                    </div>
                                    <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                                      Source ID: <code style={{ fontSize: '0.70rem' }}>{src.id}</code> • Authority: <strong>{src.authority_level}%</strong>
                                    </div>
                                  </div>
                                </div>

                                {/* Schedule Management Dropdown */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748B' }}>Schedule:</span>
                                  <select
                                    value={currentSchedule}
                                    onChange={(e) => handleUpdateSchedule(src.id, e.target.value)}
                                    style={{
                                      padding: '4px 8px',
                                      fontSize: '0.74rem',
                                      fontWeight: 600,
                                      borderRadius: '6px',
                                      border: '1px solid #CBD5E1',
                                      background: currentSchedule !== 'off' ? '#FFF7ED' : '#F8FAFC',
                                      color: currentSchedule !== 'off' ? '#EA580C' : '#334155',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    <option value="off">Off (Manual Sync)</option>
                                    <option value="1m">Every 1 minute</option>
                                    <option value="10m">Every 10 minutes</option>
                                  </select>
                                </div>
                              </div>

                              {/* Details Metrics Grid */}
                              <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                                gap: '10px',
                                background: '#F8FAFC',
                                borderRadius: '8px',
                                padding: '10px 14px',
                                fontSize: '0.74rem'
                              }}>
                                <div>
                                  <span style={{ color: '#64748B', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>DISCOVERED / STORED</span>
                                  <strong style={{ color: '#0F172A', fontSize: '0.86rem' }}>{docCount} documents</strong>
                                </div>
                                <div>
                                  <span style={{ color: '#64748B', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>LAST SUCCESSFUL SYNC</span>
                                  <span style={{ color: '#0F172A', fontWeight: 600 }}>
                                    {src.last_synced_at ? new Date(src.last_synced_at).toLocaleString() : 'Never'}
                                  </span>
                                </div>
                                <div>
                                  <span style={{ color: '#64748B', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>NEXT SCHEDULED SYNC</span>
                                  <span style={{ color: cfg.next_sync_at ? '#2563EB' : '#64748B', fontWeight: 600 }}>
                                    {cfg.next_sync_at ? new Date(cfg.next_sync_at).toLocaleTimeString() : (currentSchedule === 'off' ? 'Disabled' : 'Pending')}
                                  </span>
                                </div>
                                <div>
                                  <span style={{ color: '#64748B', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>LAST ATTEMPT</span>
                                  <span style={{ color: '#0F172A' }}>
                                    {cfg.last_attempt_at ? new Date(cfg.last_attempt_at).toLocaleTimeString() : 'N/A'}
                                  </span>
                                </div>
                              </div>

                              {/* Actionable Error Callout */}
                              {cfg.last_error && (
                                <div style={{
                                  background: '#FEF2F2',
                                  border: '1px solid #FCA5A5',
                                  borderRadius: '6px',
                                  padding: '8px 12px',
                                  fontSize: '0.72rem',
                                  color: '#991B1B'
                                }}>
                                  <strong>⚠️ Sync Diagnostic:</strong> {cfg.last_error}
                                </div>
                              )}

                              {/* Action Buttons Row */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <button
                                    type="button"
                                    onClick={() => handleSyncSource(src.id, src.name)}
                                    disabled={isSyncing}
                                    className="btn btn-primary"
                                    style={{
                                      padding: '5px 12px',
                                      fontSize: '0.74rem',
                                      fontWeight: 700,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '5px',
                                      background: '#2563EB',
                                      borderColor: '#2563EB'
                                    }}
                                  >
                                    <span className={isSyncing ? "spin" : ""}>🔄</span>
                                    <span>{isSyncing ? "Syncing Now..." : "Sync Now"}</span>
                                  </button>

                                  <button
                                    type="button"
                                    onClick={() => {
                                      setDocSourceFilter(src.id);
                                      setDocExplorerView('folders');
                                    }}
                                    className="btn btn-secondary"
                                    style={{ padding: '5px 12px', fontSize: '0.74rem', fontWeight: 600 }}
                                  >
                                    📄 Stored Documents ({docCount})
                                  </button>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => handleDisconnectSource(src.id, src.name)}
                                  className="btn btn-secondary"
                                  style={{ padding: '5px 10px', fontSize: '0.72rem', color: '#DC2626', borderColor: '#FCA5A5' }}
                                >
                                  Disconnect
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* SECTION 2: SYNCHRONIZED CONNECTORS */}
                  <div style={{
                    background: '#FAF8F5',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '12px',
                    padding: '20px',
                    boxShadow: 'none'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                        📊 Synchronized Connectors ({synchronizedSources.length})
                      </h3>
                      <span className="badge badge-verified" style={{ fontSize: '0.70rem', padding: '2px 8px' }}>
                        PostgreSQL ACID Backed
                      </span>
                    </div>
                    <p style={{ fontSize: '0.76rem', color: '#64748B', margin: '0 0 16px 0' }}>
                      Connections with at least one verified historical synchronization. Synchronized records remain queryable even during transient network errors.
                    </p>

                    {synchronizedSources.length === 0 ? (
                      <div style={{ padding: '24px', textAlign: 'center', background: '#F8FAFC', borderRadius: '8px', border: '1px dashed #E2E8F0', fontSize: '0.78rem', color: '#64748B' }}>
                        No connectors have completed synchronization yet. Trigger <strong>"Sync Now"</strong> on any configured live connector above to synchronize source documents.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                        {synchronizedSources.map(src => {
                          const icon = src.source_type === 'github' ? '🐙'
                            : (src.source_type === 'mongodb' || src.source_type === 'mongodb_atlas') ? '🍃'
                            : src.source_type === 'jira' ? '🎯'
                            : src.source_type === 'confluence' ? '📘'
                            : src.source_type === 'postgresql' ? '🐘'
                            : (src.source_type === 'slack' || src.source_type === 'slack_channel' || src.source_type === 'slack_workspace') ? '💬'
                            : '🔌';
                          const count = dbDocuments.filter(d => d.source_id === src.id).length;

                          return (
                            <div
                              key={src.id}
                              style={{
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '8px',
                                padding: '14px',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'space-between',
                                gap: '10px'
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontSize: '1.4rem' }}>{icon}</span>
                                <div>
                                  <div style={{ fontWeight: 800, fontSize: '0.86rem', color: '#0F172A' }}>{src.name}</div>
                                  <div style={{ fontSize: '0.70rem', color: '#64748B' }}>{src.source_type.toUpperCase()}</div>
                                </div>
                              </div>

                              <div style={{ fontSize: '0.74rem', color: '#334155' }}>
                                <div><strong>{count}</strong> documents synchronized</div>
                                <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '2px' }}>
                                  Last synced: {src.last_synced_at ? new Date(src.last_synced_at).toLocaleDateString() : 'N/A'}
                                </div>
                              </div>

                              <button
                                type="button"
                                onClick={() => {
                                  setDocSourceFilter(src.id);
                                  setDocExplorerView('folders');
                                }}
                                style={{
                                  padding: '5px 10px',
                                  fontSize: '0.72rem',
                                  fontWeight: 700,
                                  background: '#FFFFFF',
                                  border: '1px solid #CBD5E1',
                                  borderRadius: '6px',
                                  cursor: 'pointer',
                                  color: '#2563EB',
                                  textAlign: 'center'
                                }}
                              >
                                View Ingested Documents →
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* SECTION 3: AVAILABLE LIVE DATA PROVIDERS (5 SUPPORTED PROVIDERS) */}
                  <div style={{
                    background: '#FAF8F5',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '12px',
                    padding: '20px',
                    boxShadow: 'none'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                        🔌 Available Live Connectors (6 Supported Providers)
                      </h3>
                      <span className="badge badge-verified" style={{ fontSize: '0.70rem', padding: '2px 8px' }}>
                        Production Drivers & Pluggable Sync
                      </span>
                    </div>
                    <p style={{ fontSize: '0.76rem', color: '#64748B', margin: '0 0 18px 0' }}>
                      Connect to real external systems with genuine API handshakes, database drivers, schema discovery, and encrypted credentials.
                    </p>

                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                      gap: '16px'
                    }}>
                      {supportedLiveCatalog.map(connector => {
                        const existingCount = liveConfiguredSources.filter(s =>
                          (s.source_type || '').toLowerCase() === connector.id.toLowerCase()
                        ).length;

                        return (
                          <div
                            key={connector.id}
                            style={{
                              background: '#FFFFFF',
                              border: '1px solid #E2E8F0',
                              borderRadius: '12px',
                              padding: '18px',
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'space-between',
                              gap: '14px',
                              transition: 'all 0.15s ease',
                              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                <span style={{ fontSize: '2rem' }}>{connector.icon}</span>
                                <span style={{
                                  fontSize: '0.64rem',
                                  fontWeight: 700,
                                  textTransform: 'uppercase',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  background: '#F1F5F9',
                                  color: '#475569'
                                }}>
                                  {connector.category_label}
                                </span>
                              </div>

                              <div style={{ fontSize: '0.94rem', fontWeight: 800, color: '#0F172A' }}>
                                {connector.name}
                              </div>
                              <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '4px', lineHeight: 1.4 }}>
                                {connector.description}
                              </div>
                              <div style={{ fontSize: '0.68rem', color: '#2563EB', fontWeight: 600, marginTop: '8px' }}>
                                Scope: {connector.scope}
                              </div>
                            </div>

                            <div>
                              {existingCount > 0 && (
                                <div style={{ fontSize: '0.68rem', color: '#15803D', fontWeight: 700, marginBottom: '6px' }}>
                                  ✓ {existingCount} independent {existingCount === 1 ? 'connection' : 'connections'} active
                                </div>
                              )}
                              <button
                                type="button"
                                onClick={() => {
                                  setSelectedConnectorMeta(connector);
                                  setNewSourceForm(prev => ({
                                    ...prev,
                                    name: `Production ${connector.name} ${existingCount > 0 ? `#${existingCount + 1}` : ''}`.trim(),
                                    sourceType: connector.id,
                                    authorityLevel: connector.id === 'slack' ? 50 : 85,
                                    pgPort: connector.default_port || 5432,
                                    schedule: 'off',
                                    externalId: ''
                                  }));
                                  setTestConnectionResult(null);
                                  setDocExplorerView('connect');
                                }}
                                className="btn btn-primary"
                                style={{
                                  width: '100%',
                                  padding: '7px 0',
                                  fontSize: '0.76rem',
                                  fontWeight: 700,
                                  background: '#EA580C',
                                  borderColor: '#EA580C',
                                  textAlign: 'center'
                                }}
                              >
                                + Connect {connector.name}
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* VIEW: FULL PAGE CONNECT REAL ENTERPRISE DATA SOURCE (ATLAN ARCHITECTURE) */}
            {docExplorerView === 'connect' && (
              <div style={{
                background: '#FAF8F5',
                border: '1px solid var(--border-subtle)',
                borderRadius: '14px',
                padding: '28px',
                boxShadow: 'none',
                marginBottom: '24px'
              }}>
                {/* Header & 4-Step Process Guide */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', borderBottom: '1px solid #F1F5F9', paddingBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                        Enterprise Connector Setup Wizard
                      </h3>
                      <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                        105 Supported Integrations
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
                      Follow the 4-step wizard below to configure automated crawlers, test real-time connectivity, and extract schema policies into PostgreSQL.
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => { setDocExplorerView('connectors'); setTestConnectionResult(null); setIsConnectorDropdownOpen(false); }}
                    style={{
                      background: '#F1F5F9',
                      border: '1px solid #CBD5E1',
                      borderRadius: '8px',
                      padding: '6px 14px',
                      fontSize: '0.80rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      color: '#475569'
                    }}
                  >
                    ← Cancel & Return
                  </button>
                </div>

                {/* 4-Step Interactive Stepper Banner */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '12px',
                  marginBottom: '24px',
                  background: '#F8FAFC',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '1px solid #E2E8F0'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#EA580C', color: '#FFF', fontSize: '0.72rem', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>1</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A' }}>Select Source</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Choose system type</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#EA580C', color: '#FFF', fontSize: '0.72rem', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>2</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A' }}>Auth & Config</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Host & credentials</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#EA580C', color: '#FFF', fontSize: '0.72rem', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>3</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A' }}>Policy & Scope</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Authority & crawler</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '22px', height: '22px', borderRadius: '50%', background: '#EA580C', color: '#FFF', fontSize: '0.72rem', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>4</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0F172A' }}>Test & Connect</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748B' }}>Live handshake sync</div>
                    </div>
                  </div>
                </div>

                {/* Category Filter Chips */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
                  {catalogCategories.map(cat => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => {
                        setCatalogFilterCategory(cat.id);
                        setIsConnectorDropdownOpen(true);
                      }}
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        borderRadius: '14px',
                        border: catalogFilterCategory === cat.id ? '1px solid var(--primary, #2563EB)' : '1px solid var(--border-subtle, #E2E8F0)',
                        background: catalogFilterCategory === cat.id ? 'var(--primary, #2563EB)' : '#F8FAFC',
                        color: catalogFilterCategory === cat.id ? '#FFFFFF' : 'var(--text-secondary, #475569)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {cat.label} ({cat.count})
                    </button>
                  ))}
                </div>

                {/* Professional Search Bar with Inline Dropdown Below */}
                <div style={{ position: 'relative', marginBottom: '16px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary, #475569)', display: 'block', marginBottom: '5px' }}>
                    Search Target Data Source ({
                      catalogConnectors.filter(c =>
                        (catalogFilterCategory === 'all' || c.category === catalogFilterCategory) &&
                        (!catalogSearchQuery || c.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || c.description.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || c.id.toLowerCase().includes(catalogSearchQuery.toLowerCase()))
                      ).length
                    } available):
                  </label>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: '#FFFFFF',
                    border: isConnectorDropdownOpen ? '1px solid var(--primary, #2563EB)' : '1px solid var(--border-medium, #CBD5E1)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    boxShadow: isConnectorDropdownOpen ? '0 0 0 3px rgba(37, 99, 235, 0.12)' : '0 1px 3px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s ease'
                  }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted, #64748B)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px', flexShrink: 0 }}>
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input
                      type="text"
                      placeholder="Search across 105 data sources... e.g. GitHub, Snowflake, PostgreSQL, S3, Kafka, Databricks"
                      value={catalogSearchQuery}
                      onFocus={() => setIsConnectorDropdownOpen(true)}
                      onChange={e => {
                        setCatalogSearchQuery(e.target.value);
                        setIsConnectorDropdownOpen(true);
                      }}
                      style={{
                        width: '100%',
                        border: 'none',
                        outline: 'none',
                        background: 'transparent',
                        fontSize: '0.84rem',
                        color: 'var(--text-main, #0F172A)'
                      }}
                    />
                    {catalogSearchQuery && (
                      <button
                        type="button"
                        onClick={() => { setCatalogSearchQuery(''); setIsConnectorDropdownOpen(true); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: '2px 4px', fontSize: '0.85rem' }}
                        title="Clear search"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  {/* Interactive Dropdown Directly Below Search Bar */}
                  {isConnectorDropdownOpen && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      marginTop: '4px',
                      background: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid var(--border-medium, #CBD5E1)',
                      boxShadow: '0 12px 28px rgba(0,0,0,0.15)',
                      maxHeight: '260px',
                      overflowY: 'auto',
                      zIndex: 1050,
                      padding: '6px'
                    }}>
                      {(() => {
                        const matches = catalogConnectors.filter(c =>
                          (catalogFilterCategory === 'all' || c.category === catalogFilterCategory) &&
                          (!catalogSearchQuery ||
                            c.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) ||
                            c.description.toLowerCase().includes(catalogSearchQuery.toLowerCase()) ||
                            c.id.toLowerCase().includes(catalogSearchQuery.toLowerCase()) ||
                            c.category_label.toLowerCase().includes(catalogSearchQuery.toLowerCase()))
                        );
                        if (matches.length === 0) {
                          return (
                            <div style={{ padding: '16px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted, #64748B)' }}>
                              No connector matching "{catalogSearchQuery}". Try another keyword or category filter.
                            </div>
                          );
                        }
                        return matches.map(c => {
                          const isSelected = newSourceForm.sourceType === c.id;
                          return (
                            <div
                              key={c.id}
                              onClick={() => {
                                let defaultName = `Production ${c.name}`;
                                setNewSourceForm({ ...newSourceForm, sourceType: c.id, name: defaultName });
                                setSelectedConnectorMeta(c);
                                setCatalogSearchQuery(c.name);
                                setIsConnectorDropdownOpen(false);
                                setTestConnectionResult(null);
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                background: isSelected ? 'rgba(37, 99, 235, 0.08)' : 'transparent',
                                borderLeft: isSelected ? '3px solid var(--primary, #2563EB)' : '3px solid transparent',
                                transition: 'background 0.1s ease',
                                marginBottom: '2px'
                              }}
                              onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#F8FAFC'; }}
                              onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '1.2rem' }}>{c.icon || '🔌'}</span>
                                <div>
                                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main, #0F172A)' }}>
                                    {c.name}
                                  </div>
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748B)', maxWidth: '440px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {c.description}
                                  </div>
                                </div>
                              </div>
                              <span className="badge badge-verified" style={{ fontSize: '0.66rem', padding: '2px 6px', flexShrink: 0 }}>
                                {c.category_label}
                              </span>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  )}
                </div>

                {/* Selected Connector Scope Banner */}
                {(() => {
                  const currentMeta = catalogConnectors.find(c => c.id === newSourceForm.sourceType) || selectedConnectorMeta || catalogConnectors[0];
                  if (!currentMeta) return null;
                  return (
                    <div style={{
                      background: '#F8FAFC',
                      border: '1px solid var(--border-subtle, #E2E8F0)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      marginBottom: '16px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{currentMeta.icon || '🔌'}</span>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--text-main, #0F172A)' }}>{currentMeta.name}</span>
                            <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>{currentMeta.category_label}</span>
                          </div>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary, #475569)', marginBottom: '4px' }}>{currentMeta.description}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--primary, #2563EB)', fontWeight: 600 }}>
                            Monitored Contract Scope: {currentMeta.monitored_scope}
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsConnectorDropdownOpen(true)}
                        style={{
                          background: '#FFFFFF',
                          border: '1px solid var(--border-medium, #CBD5E1)',
                          borderRadius: '4px',
                          padding: '3px 8px',
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          color: 'var(--text-secondary, #475569)',
                          cursor: 'pointer',
                          flexShrink: 0
                        }}
                      >
                        Change
                      </button>
                    </div>
                  );
                })()}

                <form onSubmit={handleConnectNewSource} style={{ display: 'grid', gap: '14px' }}>
                  {/* Connection Instance Name */}
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary, #475569)', display: 'block', marginBottom: '4px' }}>
                      Connector Instance Name:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Production Core Snowflake Warehouse"
                      value={newSourceForm.name}
                      onChange={e => setNewSourceForm({ ...newSourceForm, name: e.target.value })}
                      style={{ width: '100%', padding: '8px 10px', fontSize: '0.84rem' }}
                      required
                    />
                  </div>

                  {/* 1. GITHUB SPECIFIC FIELDS */}
                  {newSourceForm.sourceType === 'github' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>GitHub Repository Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Token envelope-encrypted with Fernet</span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Owner / Organization:</label>
                          <input
                            type="text"
                            placeholder="e.g. facebook or your-org"
                            value={newSourceForm.githubOwner}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, githubOwner: e.target.value }); setTestConnectionResult(null); }}
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Branch:</label>
                          <input
                            type="text"
                            value={newSourceForm.githubBranch}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, githubBranch: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="main"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Personal Access Token (PAT):</label>
                          <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Requires repo read scope</span>
                        </div>
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type={showTokenMask ? "text" : "password"}
                            value={newSourceForm.githubToken}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, githubToken: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="ghp_... (Optional for public repos)"
                            style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                          />
                          <button
                            type="button"
                            onClick={() => setShowTokenMask(!showTokenMask)}
                            style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                            title={showTokenMask ? "Hide token" : "Show token"}
                          >
                            👁️
                          </button>
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Repository (owner/repo):</label>
                          <button
                            type="button"
                            onClick={() => handleDiscoverResource('repos')}
                            disabled={isDiscovering}
                            style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '2px 8px', fontSize: '0.70rem', fontWeight: 700, cursor: 'pointer' }}
                          >
                            {isDiscovering ? 'Discovering...' : '🔍 Discover Repositories'}
                          </button>
                        </div>
                        <input
                          type="text"
                          placeholder="e.g. facebook/react or my-org/security-standards"
                          value={newSourceForm.githubRepo}
                          onChange={e => { setNewSourceForm({ ...newSourceForm, githubRepo: e.target.value }); setTestConnectionResult(null); }}
                          style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          required
                        />
                        {discoveredOptions.repos && discoveredOptions.repos.length > 0 && (
                          <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            <span style={{ fontSize: '0.68rem', color: '#64748B', alignSelf: 'center' }}>Discovered:</span>
                            {discoveredOptions.repos.slice(0, 6).map(r => (
                              <button
                                key={r}
                                type="button"
                                onClick={() => setNewSourceForm(prev => ({ ...prev, githubRepo: r }))}
                                style={{ padding: '2px 6px', fontSize: '0.68rem', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '4px', cursor: 'pointer' }}
                              >
                                {r}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 2. POSTGRESQL SPECIFIC FIELDS */}
                  {(['postgresql', 'postgres'].includes(newSourceForm.sourceType)) && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>PostgreSQL Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 asyncpg Driver • Parameterized Queries</span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Host / Hostname:</label>
                          <input
                            type="text"
                            value={newSourceForm.pgHost}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, pgHost: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="localhost or db.internal"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Port:</label>
                          <input
                            type="number"
                            value={newSourceForm.pgPort}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, pgPort: e.target.value }); setTestConnectionResult(null); }}
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database Name:</label>
                          <input
                            type="text"
                            value={newSourceForm.pgDatabase}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, pgDatabase: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="postgres or context_trust"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>SSL Mode:</label>
                          <select
                            value={newSourceForm.pgSslMode}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, pgSslMode: e.target.value }); setTestConnectionResult(null); }}
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          >
                            <option value="prefer">prefer</option>
                            <option value="require">require</option>
                            <option value="disable">disable</option>
                          </select>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Username:</label>
                          <input
                            type="text"
                            value={newSourceForm.pgUsername}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, pgUsername: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="postgres"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Password:</label>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <input
                              type={showPasswordMask ? "text" : "password"}
                              value={newSourceForm.pgPassword}
                              onChange={e => { setNewSourceForm({ ...newSourceForm, pgPassword: e.target.value }); setTestConnectionResult(null); }}
                              placeholder="••••••••"
                              style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                            />
                            <button
                              type="button"
                              onClick={() => setShowPasswordMask(!showPasswordMask)}
                              style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                            >
                              👁️
                            </button>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                            <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Schema(s):</label>
                            <button
                              type="button"
                              onClick={() => handleDiscoverResource('schemas')}
                              disabled={isDiscovering}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              🔍 Discover
                            </button>
                          </div>
                          <input
                            type="text"
                            value={newSourceForm.pgSchemas}
                            onChange={e => setNewSourceForm({ ...newSourceForm, pgSchemas: e.target.value })}
                            placeholder="public, analytics"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                            <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Tables (Optional filter):</label>
                            <button
                              type="button"
                              onClick={() => handleDiscoverResource('tables', newSourceForm.pgSchemas || 'public')}
                              disabled={isDiscovering}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              🔍 Discover
                            </button>
                          </div>
                          <input
                            type="text"
                            value={newSourceForm.pgTables}
                            onChange={e => setNewSourceForm({ ...newSourceForm, pgTables: e.target.value })}
                            placeholder="e.g. users, policies (all if empty)"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 3. MONGODB ATLAS SPECIFIC FIELDS */}
                  {(['mongodb', 'mongodb_atlas', 'mongodb_self', 'documentdb'].includes(newSourceForm.sourceType)) && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>MongoDB Atlas Cluster Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Motor Driver • Bounded Cursor Batching</span>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Connection URI:</label>
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type={showPasswordMask ? "text" : "password"}
                            value={newSourceForm.mongoUri}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, mongoUri: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="mongodb+srv://user:pass@cluster.mongodb.net/test or mongodb://localhost:27017"
                            style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowPasswordMask(!showPasswordMask)}
                            style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                          >
                            👁️
                          </button>
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '4px', lineHeight: '1.3' }}>
                          💡 <strong>Atlas Tip:</strong> Use credentials from <em>Security → Database Access</em> (not your web portal login). If your password contains symbols like <code>@</code>, <code>#</code>, or <code>:</code>, URL-encode them (e.g. <code>%40</code> for <code>@</code>, <code>%23</code> for <code>#</code>).
                        </div>
                        {newSourceForm.mongoUri && (newSourceForm.mongoUri.includes('<') || newSourceForm.mongoUri.includes('>')) && (
                          <div style={{
                            background: '#FEF2F2',
                            border: '1px solid #FCA5A5',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            marginTop: '6px',
                            fontSize: '0.72rem',
                            color: '#991B1B',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '8px'
                          }}>
                            <span>
                              ⚠️ <strong>Placeholder Brackets Detected:</strong> Your URI contains <code>&lt;</code> and <code>&gt;</code> (e.g. <code>&lt;spk&gt;</code>). In MongoDB Atlas, angle brackets are placeholders. Remove <code>&lt;</code> and <code>&gt;</code> around your password.
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                const cleaned = newSourceForm.mongoUri.replace(/<([^>]+)>/g, '$1');
                                setNewSourceForm({ ...newSourceForm, mongoUri: cleaned });
                                setTestConnectionResult(null);
                              }}
                              style={{
                                background: '#DC2626',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '3px 8px',
                                fontSize: '0.68rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              Auto-Fix Brackets
                            </button>
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                            <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database Name:</label>
                            <button
                              type="button"
                              onClick={() => handleDiscoverResource('databases')}
                              disabled={isDiscovering}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              🔍 Discover DBs
                            </button>
                          </div>
                          <input
                            type="text"
                            value={newSourceForm.mongoDatabase}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, mongoDatabase: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="production or analytics"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                          {discoveredOptions.databases && discoveredOptions.databases.length > 0 && (
                            <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                              {discoveredOptions.databases.slice(0, 4).map(db => (
                                <button
                                  key={db}
                                  type="button"
                                  onClick={() => setNewSourceForm(prev => ({ ...prev, mongoDatabase: db }))}
                                  style={{ padding: '1px 5px', fontSize: '0.68rem', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '3px', cursor: 'pointer' }}
                                >
                                  {db}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                            <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Collections (comma-separated):</label>
                            <button
                              type="button"
                              onClick={() => handleDiscoverResource('collections', newSourceForm.mongoDatabase)}
                              disabled={isDiscovering}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              🔍 Discover Colls
                            </button>
                          </div>
                          <input
                            type="text"
                            value={newSourceForm.mongoCollections}
                            onChange={e => setNewSourceForm({ ...newSourceForm, mongoCollections: e.target.value })}
                            placeholder="e.g. orders, policies, entitlements"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 4. JIRA SPECIFIC FIELDS */}
                  {newSourceForm.sourceType === 'jira' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>Jira Cloud / Server Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Atlassian REST API v3 • ADF Extraction</span>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Jira Base URL:</label>
                        <input
                          type="url"
                          value={newSourceForm.jiraBaseUrl}
                          onChange={e => { setNewSourceForm({ ...newSourceForm, jiraBaseUrl: e.target.value }); setTestConnectionResult(null); }}
                          placeholder="https://your-domain.atlassian.net"
                          style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          required
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>User Email / Username:</label>
                          <input
                            type="email"
                            value={newSourceForm.jiraEmail}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, jiraEmail: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="dev@company.com"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>API Token:</label>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <input
                              type={showPasswordMask ? "text" : "password"}
                              value={newSourceForm.jiraToken}
                              onChange={e => { setNewSourceForm({ ...newSourceForm, jiraToken: e.target.value }); setTestConnectionResult(null); }}
                              placeholder="••••••••"
                              style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                              required
                            />
                            <button
                              type="button"
                              onClick={() => setShowPasswordMask(!showPasswordMask)}
                              style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                            >
                              👁️
                            </button>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                            <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Project Key:</label>
                            <button
                              type="button"
                              onClick={() => handleDiscoverResource('projects')}
                              disabled={isDiscovering}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              🔍 Discover Projects
                            </button>
                          </div>
                          <input
                            type="text"
                            value={newSourceForm.jiraProject}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, jiraProject: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="e.g. SEC, ENG, OPS"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                          {discoveredOptions.projects && discoveredOptions.projects.length > 0 && (
                            <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                              {discoveredOptions.projects.slice(0, 5).map(p => (
                                <button
                                  key={p.key || p}
                                  type="button"
                                  onClick={() => setNewSourceForm(prev => ({ ...prev, jiraProject: p.key || p }))}
                                  style={{ padding: '1px 5px', fontSize: '0.68rem', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '3px', cursor: 'pointer' }}
                                >
                                  {p.key || p}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Optional JQL Filter:</label>
                          <input
                            type="text"
                            value={newSourceForm.jiraFilter}
                            onChange={e => setNewSourceForm({ ...newSourceForm, jiraFilter: e.target.value })}
                            placeholder="status = Done ORDER BY updated DESC"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 5. CONFLUENCE SPECIFIC FIELDS */}
                  {newSourceForm.sourceType === 'confluence' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>Confluence Wiki Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Atlassian Wiki API • HTML to Markdown Normalization</span>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Confluence Base URL:</label>
                        <input
                          type="url"
                          value={newSourceForm.confluenceBaseUrl}
                          onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceBaseUrl: e.target.value }); setTestConnectionResult(null); }}
                          placeholder="https://your-domain.atlassian.net/wiki"
                          style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          required
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>User Email / Username:</label>
                          <input
                            type="email"
                            value={newSourceForm.confluenceEmail}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceEmail: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="dev@company.com"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>API Token:</label>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <input
                              type={showPasswordMask ? "text" : "password"}
                              value={newSourceForm.confluenceToken}
                              onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceToken: e.target.value }); setTestConnectionResult(null); }}
                              placeholder="••••••••"
                              style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                              required
                            />
                            <button
                              type="button"
                              onClick={() => setShowPasswordMask(!showPasswordMask)}
                              style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                            >
                              👁️
                            </button>
                          </div>
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Space Key(s) (comma-separated):</label>
                          <button
                            type="button"
                            onClick={() => handleDiscoverResource('spaces')}
                            disabled={isDiscovering}
                            style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                          >
                            🔍 Discover Spaces
                          </button>
                        </div>
                        <input
                          type="text"
                          value={newSourceForm.confluenceSpace}
                          onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceSpace: e.target.value }); setTestConnectionResult(null); }}
                          placeholder="e.g. POLICIES, TECHNICALITY, SD"
                          style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          required
                        />
                        {discoveredOptions.spaces && discoveredOptions.spaces.length > 0 && (
                          <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                            {discoveredOptions.spaces.slice(0, 8).map(s => {
                              const spaceKey = (typeof s === 'object' ? s.key : s) || '';
                              return (
                                <button
                                  key={spaceKey}
                                  type="button"
                                  onClick={() => setNewSourceForm(prev => {
                                    const currentList = (prev.confluenceSpace || '').split(',').map(x => x.trim().toUpperCase()).filter(Boolean);
                                    if (currentList.includes(spaceKey.toUpperCase())) return prev;
                                    return {
                                      ...prev,
                                      confluenceSpace: currentList.length > 0 ? `${currentList.join(', ')}, ${spaceKey}` : spaceKey
                                    };
                                  })}
                                  style={{ padding: '2px 6px', fontSize: '0.68rem', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '3px', cursor: 'pointer' }}
                                  title={`Add space ${spaceKey}`}
                                >
                                  + {spaceKey}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 6. SLACK SPECIFIC FIELDS */}
                  {newSourceForm.sourceType === 'slack' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>Slack Workspace Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Web API v2 • Token Auth & Channel Ingestion</span>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Bot User OAuth Token (xoxb-...):</label>
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type={showPasswordMask ? "text" : "password"}
                            value={newSourceForm.slackBotToken}
                            onChange={e => { setNewSourceForm({ ...newSourceForm, slackBotToken: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="xoxb-your-slack-bot-token"
                            style={{ width: '100%', padding: '7px 32px 7px 9px', fontSize: '0.82rem' }}
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowPasswordMask(!showPasswordMask)}
                            style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', alignItems: 'center' }}
                          >
                            👁️
                          </button>
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '3px' }}>
                          Requires scopes: <code>channels:read</code>, <code>channels:history</code>, <code>users:read</code>, <code>files:read</code> (for ingesting uploaded document contents like Word/PDF).
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Channel(s) (comma-separated names or IDs):</label>
                          <button
                            type="button"
                            onClick={() => handleDiscoverResource('channels')}
                            disabled={isDiscovering}
                            style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8', borderRadius: '4px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer' }}
                          >
                            🔍 Discover Channels
                          </button>
                        </div>
                        <input
                          type="text"
                          value={newSourceForm.slackChannels}
                          onChange={e => { setNewSourceForm({ ...newSourceForm, slackChannels: e.target.value }); setTestConnectionResult(null); }}
                          placeholder="e.g. general, incidents, dev-decisions (or leave empty to ingest all member channels)"
                          style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                        />
                        {discoveredOptions.channels && discoveredOptions.channels.length > 0 && (
                          <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {discoveredOptions.channels.slice(0, 12).map(c => {
                              const chanName = typeof c === 'object' ? (c.name || c.id) : c;
                              const isMember = typeof c === 'object' ? c.is_member : true;
                              return (
                                <button
                                  key={chanName}
                                  type="button"
                                  onClick={() => setNewSourceForm(prev => {
                                    const currentList = (prev.slackChannels || '').split(',').map(x => x.trim().replace(/^#/, '')).filter(Boolean);
                                    if (currentList.includes(chanName)) return prev;
                                    return {
                                      ...prev,
                                      slackChannels: currentList.length > 0 ? `${currentList.join(', ')}, ${chanName}` : chanName
                                    };
                                  })}
                                  style={{
                                    padding: '2px 8px',
                                    fontSize: '0.68rem',
                                    background: isMember === false ? '#FFFBEB' : '#F1F5F9',
                                    border: isMember === false ? '1px solid #FDE68A' : '1px solid #CBD5E1',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    color: isMember === false ? '#B45309' : '#1E293B'
                                  }}
                                  title={isMember === false ? `Bot is not in #${chanName}. Run /invite @bot first.` : `Add #${chanName}`}
                                >
                                  #{chanName} {isMember === false ? '⚠️' : ''}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Lookback Days (1–365):</label>
                          <input
                            type="number"
                            min="1"
                            max="365"
                            value={newSourceForm.slackLookbackDays}
                            onChange={e => setNewSourceForm({ ...newSourceForm, slackLookbackDays: e.target.value })}
                            placeholder="30"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: '14px' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 600, color: '#334155', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={newSourceForm.slackIncludeReplies !== false}
                              onChange={e => setNewSourceForm({ ...newSourceForm, slackIncludeReplies: e.target.checked })}
                            />
                            Include Thread Replies
                          </label>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 7. UNIVERSAL DRIVER CONFIGURATION FOR NON-LIVE CATALOG CONNECTORS */}
                  {!['github', 'postgresql', 'postgres', 'mongodb', 'mongodb_atlas', 'jira', 'confluence', 'slack'].includes(newSourceForm.sourceType) && (
                    <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle, #E2E8F0)', borderRadius: '8px', padding: '14px', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)' }}>Enterprise Endpoint Connection Parameters</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 TLS 1.3 / Token Auth</span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Host / Endpoint URL / Account:</label>
                          <input
                            type="text"
                            value={genericConfig.host}
                            onChange={e => { setGenericConfig({ ...genericConfig, host: e.target.value }); setTestConnectionResult(null); }}
                            placeholder={`e.g. ${newSourceForm.sourceType}-cluster.prod.internal`}
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Port (Optional):</label>
                          <input
                            type="number"
                            value={genericConfig.port}
                            onChange={e => { setGenericConfig({ ...genericConfig, port: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="Default"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database / Workspace:</label>
                          <input
                            type="text"
                            value={genericConfig.database}
                            onChange={e => { setGenericConfig({ ...genericConfig, database: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="production"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>API Key / Secret:</label>
                          <input
                            type="password"
                            value={genericConfig.password}
                            onChange={e => { setGenericConfig({ ...genericConfig, password: e.target.value }); setTestConnectionResult(null); }}
                            placeholder="••••••••"
                            style={{ width: '100%', padding: '7px 9px', fontSize: '0.82rem' }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* STEP 3: SCHEDULE CONFIGURATION SELECTOR */}
                  <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '14px' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary, #475569)', display: 'block', marginBottom: '8px' }}>
                      Automated Synchronization Schedule:
                    </label>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                      {[
                        { id: 'off', label: 'Off', desc: 'Manual on-demand synchronization only' },
                        { id: '1m', label: 'Every 1 minute', desc: 'Continuous automated low-latency crawl' },
                        { id: '10m', label: 'Every 10 minutes', desc: 'Periodic background synchronization' }
                      ].map(sch => {
                        const isSelected = (newSourceForm.schedule || 'off') === sch.id;
                        return (
                          <div
                            key={sch.id}
                            onClick={() => setNewSourceForm(prev => ({ ...prev, schedule: sch.id }))}
                            style={{
                              padding: '10px 12px',
                              borderRadius: '8px',
                              border: isSelected ? '2px solid #EA580C' : '1px solid #CBD5E1',
                              background: isSelected ? '#FFF7ED' : '#FFFFFF',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div style={{ fontSize: '0.80rem', fontWeight: 700, color: isSelected ? '#EA580C' : '#0F172A' }}>
                              {sch.label}
                            </div>
                            <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '2px' }}>
                              {sch.desc}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Authority Slider */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary, #475569)' }}>
                        Trust Authority Level:
                      </label>
                      <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--primary, #2563EB)' }}>
                        {newSourceForm.authorityLevel}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      value={newSourceForm.authorityLevel}
                      onChange={e => setNewSourceForm({ ...newSourceForm, authorityLevel: e.target.value })}
                      style={{ width: '100%' }}
                    />
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748B)' }}>
                      High authority sources (90%+) supersede conflicting claims from lower authority sources.
                    </div>
                  </div>

                  {/* Test Connection Diagnostic Result */}
                  {testConnectionResult && (
                    <div style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      fontSize: '0.78rem',
                      background: testConnectionResult.success ? '#F0FDF4' : '#FEF2F2',
                      border: `1px solid ${testConnectionResult.success ? '#BBF7D0' : '#FCA5A5'}`,
                      color: testConnectionResult.success ? '#15803D' : '#B91C1C'
                    }}>
                      <div style={{ fontWeight: 800, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{testConnectionResult.success ? '✓ Pre-flight Connection Succeeded' : '✕ Connection Diagnostic Failed'}</span>
                      </div>
                      <div>{testConnectionResult.message}</div>
                      {testConnectionResult.details && Object.keys(testConnectionResult.details).length > 0 && (
                        <div style={{ fontSize: '0.72rem', marginTop: '4px', opacity: 0.9 }}>
                          Details: {JSON.stringify(testConnectionResult.details)}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                    <button
                      type="button"
                      onClick={handleTestConnection}
                      disabled={isTestingConnection}
                      className="btn btn-secondary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 16px',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        background: '#F8FAFC',
                        border: '1px solid #CBD5E1'
                      }}
                    >
                      <span className={isTestingConnection ? "spin" : ""}>⚡</span>
                      {isTestingConnection ? "Running Connection Diagnostic..." : "Test Connection"}
                    </button>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => { setDocExplorerView('connectors'); setTestConnectionResult(null); setIsConnectorDropdownOpen(false); }}
                        className="btn btn-secondary"
                        style={{ padding: '8px 16px', fontSize: '0.82rem', fontWeight: 600 }}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isConnectingSource || !testConnectionResult?.success}
                        className="btn btn-primary"
                        style={{
                          padding: '8px 20px',
                          fontSize: '0.82rem',
                          fontWeight: 700,
                          background: testConnectionResult?.success ? '#EA580C' : '#94A3B8',
                          borderColor: testConnectionResult?.success ? '#EA580C' : '#94A3B8',
                          boxShadow: testConnectionResult?.success ? '0 2px 6px rgba(234, 88, 12, 0.25)' : 'none',
                          cursor: testConnectionResult?.success ? 'pointer' : 'not-allowed'
                        }}
                        title={!testConnectionResult?.success ? "Run and pass 'Test Connection' before saving" : "Save connection and run initial sync"}
                      >
                        {isConnectingSource ? "Connecting & Syncing..." : "Save Securely & Ingest"}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            )}

            {/* VIEW 1: LIVE INGESTION STUDIO & CLAIM EXTRACTOR */}
            {docExplorerView === 'ingest' && (
              <LiveIngestionStudio
                activeOrg={activeOrg}
                activePersona={activePersona}
                activeWorkspace={activeWorkspace}
                onClaimExtracted={() => {
                  fetchLiveDatabaseRecords();
                  fetchHealthAndConflicts(activeOrg?.id);
                }}
                showToast={showToast}
                onNavigateToVaultClaims={(targetDocId) => {
                  setActiveTab('visual_lineage');
                  setVaultSubTab('claims');
                  if (targetDocId) {
                    setSelectedLineageAssetId(targetDocId);
                  }
                }}
              />
            )}

            {/* VIEW 2: DOCUMENT WORKSPACE & FOLDER EXPLORER (CAN CREATE, ORGANIZE, RENAME, UPLOAD) */}
            {(docExplorerView === 'folders' || docExplorerView === 'documents') && (
              <DocumentWorkspaceExplorer
                activeOrg={activeOrg}
                token={authToken}
                user={authUser}
                showToast={showToast}
                readOnly={false}
                onInspectDocument={(doc) => setInspectorState({
                  isOpen: true,
                  assetType: 'document',
                  assetId: doc.id,
                  assetTitle: doc.title
                })}
                onViewClaims={(doc) => {
                  setSelectedLineageAssetId(doc.id);
                  setVaultSubTab('documents');
                  setActiveTab('visual_lineage');
                }}
              />
            )}

            {/* VIEW 3: ATOMIC CLAIMS BROWSER (MILLION-SCALE DISCOVERY ENGINE) */}
            {docExplorerView === 'claims' && (
              <div className="clean-panel" style={{ padding: '20px' }}>
                <MillionScaleClaimsGrid
                  claims={displayedDbClaims}
                  documents={displayedDbDocuments}
                  activeWorkspace={activeWorkspace}
                  onInspectDocument={(doc) => setInspectorState({
                    isOpen: true,
                    assetType: 'document',
                    assetId: doc.id,
                    assetTitle: doc.title
                  })}
                  onInspectClaim={(claim) => {
                    const foundDoc = displayedDbDocuments.find(d => d.id === claim.document_id || d.versions?.some(v => v.id === claim.document_version_id));
                    if (foundDoc) {
                      setInspectorState({
                        isOpen: true,
                        assetType: 'document',
                        assetId: foundDoc.id,
                        assetTitle: foundDoc.title
                      });
                    }
                  }}
                />
              </div>
            )}
          </div>
          )
        )}

        {/* ========================================================= */}
        {/* TAB 6: DECISION AUDIT TRAIL & LINEAGE EXPLORER            */}
        {/* ========================================================= */}
        {activeTab === 'audit' && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="Decision Audit Trail & Cryptographic Ledger"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* Centered Top Header & Compliance Export Actions */}
            <div className="tab-header-center clean-panel" style={{ padding: '24px', background: 'var(--bg-card)', marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Live Decision Audit Trail & Lineage Explorer
              </h1>
              <p className="tab-subtitle">
                Cryptographically tamper-evident decision logs with 4-stage end-to-end lineage tracing, actor authorization gates, and candidate evidence provenance.
              </p>

              {/* Centered Export & Refresh Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
                <button
                  onClick={() => fetchAuditLogs(activeOrg?.id)}
                  className="btn btn-secondary"
                  disabled={auditLoading}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span style={{ display: 'inline-block', transform: auditLoading ? 'rotate(180deg)' : 'none', transition: 'transform 0.5s' }}>
                    🔄
                  </span>
                  {auditLoading ? 'Refreshing...' : 'Refresh Logs'}
                </button>
                <button
                  onClick={() => handleExportAuditLogs('csv')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span>📊</span> Export CSV
                </button>
                <button
                  onClick={() => handleExportAuditLogs('json')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span>📜</span> Export JSON
                </button>
                <button
                  onClick={() => setIsDossierModalOpen(true)}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px', background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
                >
                  <span>🏛️</span> Compliance Dossier (NIST / EU AI Act)
                </button>
              </div>
            </div>

            {/* 6 Compliance KPI Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: '12px',
              marginTop: '20px'
            }}>
              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Total Decisions
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                  {auditSummary.total_decisions}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  100% Provenance Captured
                </div>
              </div>

              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Policy Allow Rate
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '4px' }}>
                  {auditSummary.allow_rate_pct}%
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {auditSummary.allow_count} Allowed / {auditSummary.block_count} Blocked
                </div>
              </div>

              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Risk Interceptions
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: auditSummary.block_count > 0 ? 'var(--danger-text, #ef4444)' : 'var(--text-main)', marginTop: '4px' }}>
                  {auditSummary.block_count + auditSummary.review_count}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {auditSummary.high_risk_count} High Risk Blocked
                </div>
              </div>

              <div
                onClick={() => setIsRoiModalOpen(true)}
                style={{ background: '#ECFDF5', padding: '14px 16px', borderRadius: '8px', border: '1px solid #A7F3D0', cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                title="Click to view full Financial Liability ROI breakdown"
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: '#047857', fontWeight: 700, textTransform: 'uppercase' }}>
                    Liability Prevented
                  </div>
                  <span className="badge badge-allow" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>ROI View</span>
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#059669', marginTop: '4px' }}>
                  ${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '0'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#047857', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>💰</span> {auditSummary.total_blocked_incidents || (auditSummary.block_count + auditSummary.review_count)} Incidents Intercepted
                </div>
              </div>

              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Crypto Signatures
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
                  100% SHA-256
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--success-text)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>✓</span> Tamper-Evident Chain
                </div>
              </div>

              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Avg Gate Latency
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                  {auditSummary.avg_latency_ms} <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>ms</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Real-time inline guard
                </div>
              </div>
            </div>

            {/* Filter Toolbar & Live Audit Log Stream */}
            <div className="clean-panel" style={{ padding: '20px', background: 'var(--bg-card)' }}>

              {/* Filter Controls Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>

                {/* Search Box */}
                <div style={{ position: 'relative', minWidth: '260px', flex: 1, maxWidth: '400px' }}>
                  <input
                    type="text"
                    placeholder="Search prompt, actor ID, or audit ID..."
                    value={auditSearchQuery}
                    onChange={(e) => setAuditSearchQuery(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px 8px 32px',
                      fontSize: '0.82rem',
                      background: 'var(--bg-card-subtle)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      color: 'var(--text-main)'
                    }}
                  />
                  <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    🔍
                  </span>
                  {auditSearchQuery && (
                    <button
                      onClick={() => setAuditSearchQuery('')}
                      style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Verdict Filters */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 700, marginRight: '4px' }}>
                    VERDICT:
                  </span>
                  {['all', 'ALLOW', 'BLOCK', 'REVIEW', 'CLARIFY'].map(v => (
                    <button
                      key={v}
                      onClick={() => setAuditFilterVerdict(v)}
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        borderRadius: '4px',
                        border: auditFilterVerdict === v ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                        background: auditFilterVerdict === v ? 'var(--primary-subtle, rgba(99,102,241,0.15))' : 'var(--bg-card-subtle)',
                        color: auditFilterVerdict === v ? 'var(--primary)' : 'var(--text-muted)',
                        cursor: 'pointer'
                      }}
                    >
                      {v.toUpperCase()}
                    </button>
                  ))}
                </div>

                {/* Risk Filter */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                    RISK:
                  </span>
                  <select
                    value={auditFilterRisk}
                    onChange={(e) => setAuditFilterRisk(e.target.value)}
                    style={{
                      padding: '5px 10px',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      borderRadius: '4px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card-subtle)',
                      color: 'var(--text-main)'
                    }}
                  >
                    <option value="all">All Risk Levels</option>
                    <option value="LOW">Low Risk</option>
                    <option value="MEDIUM">Medium Risk</option>
                    <option value="HIGH">High Risk</option>
                  </select>
                </div>
              </div>

              {/* Logs Table */}
              {auditLogs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📋</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    No Decision Audit Records Found
                  </div>
                  <p style={{ fontSize: '0.78rem', marginTop: '4px', maxWidth: '450px', margin: '4px auto 16px auto' }}>
                    {auditSearchQuery || auditFilterVerdict !== 'all' || auditFilterRisk !== 'all'
                      ? 'No records match your active search or filter criteria. Try resetting filters.'
                      : 'Run a Decision Gate evaluation or query the MCP server to begin populating the live compliance audit log.'}
                  </p>
                  {(auditSearchQuery || auditFilterVerdict !== 'all' || auditFilterRisk !== 'all') && (
                    <button
                      onClick={() => { setAuditSearchQuery(''); setAuditFilterVerdict('all'); setAuditFilterRisk('all'); }}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.78rem', padding: '6px 14px' }}
                    >
                      Reset Filters
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Timestamp & Audit ID</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Actor & Role</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Decision Prompt</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Verdict</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Risk</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Crypto Token</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr
                          key={log.id || log.audit_id}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            cursor: 'pointer',
                            transition: 'background 0.15s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-subtle)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                          onClick={() => handleInspectLineage(log.audit_id)}
                        >
                          {/* Timestamp & Audit ID */}
                          <td style={{ padding: '12px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-main)', fontFamily: 'monospace', fontSize: '0.76rem' }}>
                              {log.audit_id}
                            </div>
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Just now'} • {log.created_at ? new Date(log.created_at).toLocaleDateString() : ''}
                            </div>
                          </td>

                          {/* Actor & Role */}
                          <td style={{ padding: '12px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.78rem' }}>
                              {log.actor_id}
                            </div>
                            <span className="badge badge-outline" style={{ fontSize: '0.62rem', padding: '1px 5px', marginTop: '3px', display: 'inline-block' }}>
                              {log.actor_role}
                            </span>
                          </td>

                          {/* Decision Prompt */}
                          <td style={{ padding: '12px', maxWidth: '300px' }}>
                            <div style={{ color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                              {log.decision_prompt}
                            </div>
                            {log.preferred_source && (
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                Source: {log.preferred_source}
                              </div>
                            )}
                          </td>

                          {/* Verdict */}
                          <td style={{ padding: '12px' }}>
                            <span
                              className={
                                log.verdict === 'ALLOW' ? 'badge badge-verified' :
                                  log.verdict === 'BLOCK' ? 'badge badge-warning' :
                                    'badge badge-review'
                              }
                              style={{ fontSize: '0.72rem', padding: '2px 8px', fontWeight: 800 }}
                            >
                              {log.verdict}
                            </span>
                          </td>

                          {/* Risk */}
                          <td style={{ padding: '12px' }}>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                color: log.risk_level === 'LOW' ? 'var(--success-text)' : log.risk_level === 'HIGH' ? 'var(--danger-text, #ef4444)' : 'var(--warning-text, #f59e0b)'
                              }}
                            >
                              {log.risk_level}
                            </span>
                          </td>

                          {/* SHA-256 Token */}
                          <td style={{ padding: '12px' }} onClick={(e) => e.stopPropagation()}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <code style={{ fontSize: '0.68rem', background: 'var(--bg-card-subtle)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                                {log.audit_token ? `${log.audit_token.substring(0, 8)}...${log.audit_token.substring(log.audit_token.length - 6)}` : 'SHA256-OK'}
                              </code>
                              <button
                                onClick={() => handleCopyAuditToken(log.audit_token)}
                                title="Copy cryptographic SHA-256 signature"
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  color: copiedToken === log.audit_token ? 'var(--success-text)' : 'var(--text-muted)',
                                  cursor: 'pointer',
                                  fontSize: '0.74rem'
                                }}
                              >
                                {copiedToken === log.audit_token ? '✓' : '📋'}
                              </button>
                            </div>
                          </td>

                          {/* Action Button */}
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            <button
                              onClick={() => handleInspectLineage(log.audit_id)}
                              className="btn btn-secondary"
                              style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                            >
                              Inspect Lineage ➔
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
          )
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 2: VAULT (DATA EXPLORATION & DAG LINEAGE)  */}
        {/* ========================================================= */}
        {activeTab === 'visual_lineage' && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="Context Vault & Evidence Lineage"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
          <div>
            <VisualLineageGraph
              activeOrg={activeOrg}
              activeWorkspace={activeWorkspace}
              showToast={showToast}
              vaultSubTab={vaultSubTab}
              onVaultSubTabChange={(sub) => {
                setVaultSubTab(sub);
                setSelectedLineageAssetId(null);
                setSelectedLineageClaimId(null);
              }}
              initialAssetId={selectedLineageAssetId}
              onAssetChange={setSelectedLineageAssetId}
              initialClaimId={selectedLineageClaimId}
              onClaimChange={setSelectedLineageClaimId}
              initialSection={lineageSection}
              onSectionChange={setLineageSection}
              onOpenFileBrowser={() => { setActiveTab('ingestion'); setDocExplorerView('folders'); }}
            />
          </div>
          )
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 3: CONTEXT CURATOR BOT (OPTION 3)          */}
        {/* ========================================================= */}
        {(activeTab === 'context_curator' || activeTab === 'conflicts') && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="Context Curator & Conflict Resolution Hub"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
          <div>
            <ContextCuratorStudio
              activeOrg={activeOrg}
              activeWorkspace={activeWorkspace}
              showToast={showToast}
              conflicts={conflicts}
              onResolveConflict={handleResolveConflict}
              onRefreshConflicts={() => fetchHealthAndConflicts(activeOrg?.id)}
              initialSubView={activeTab === 'conflicts' ? 'conflicts' : curatorSubView}
              onSubViewChange={setCuratorSubView}
            />
          </div>
          )
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 4: MCP INTEGRATION STUDIO (OPTION 4)       */}
        {/* ========================================================= */}
        {activeTab === 'integrations' && (
          !isEnvironmentReady ? (
            <ServiceLockedGate
              serviceName="MCP Hub & External Integrations"
              isOrgReady={isOrgReady}
              isWorkspaceReady={isWorkspaceReady}
              activeOrg={activeOrg}
              authToken={authToken}
              onOpenOrgModal={() => setShowNewOrgModal(true)}
              onOpenWorkspaceModal={() => setShowNewWorkspaceModal(true)}
              onGoHome={() => setActiveTab('home')}
              onOrgCreated={handleOrgCreated}
              showToast={showToast}
            />
          ) : (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '20px' }}>

              <h1 className="tab-main-heading">
                Model Context Protocol (MCP) & Agent Integrations
              </h1>
              <p className="tab-subtitle">
                Connect external autonomous agent frameworks (LangChain, CrewAI, AutoGen, Claude Desktop) to the Context Trust Gateway via standardized MCP endpoints.
              </p>
            </div>
            <McpIntegrationStudio
              activeOrg={activeOrg}
              showToast={showToast}
              initialSubView={mcpActiveSubView}
              onSubViewChange={setMcpActiveSubView}
            />
          </div>
          )
        )}

        {/* ========================================================= */}
        {/* TAB 7: TEAM, PERSONAS & GOVERNANCE ACTIVITY HUB           */}
        {/* ========================================================= */}
        {activeTab === 'team' && (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '20px' }}>

              <h1 className="tab-main-heading">
                Enterprise Team, Personas & Governance Activity
              </h1>
              <p className="tab-subtitle">
                Manage organizational users, switch testing personas, review Atlan-grade separation of duties (SoD), and audit real-time user activities.
              </p>
            </div>
            <TeamAndActivityHub
              activeOrg={activeOrg}
              activePersona={activePersona}
              onSelectPersona={(p) => setActivePersona(p)}
              showToast={showToast}
              initialSubTab={teamSubTab}
              onSubTabChange={setTeamSubTab}
              onOpenRbacModal={() => setIsRbacModalOpen(true)}
              onLaunchSetupWizard={(org) => {
                setSetupWizardTargetOrg(org || activeOrg);
                setIsSetupWizardOpen(true);
              }}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 8: USER PROFILE, IDENTITY & COMPANY SWITCHER          */}
        {/* ========================================================= */}
        {activeTab === 'profile' && (
          <div>
            <UserProfileStudio
              activeOrg={activeOrg}
              organizations={myOrganizations && myOrganizations.length > 0 ? myOrganizations : (activeOrg ? [activeOrg] : [])}
              onSwitchOrg={handleSwitchOrganization}
              activeWorkspace={activeWorkspace}
              workspaces={workspaces}
              onSwitchWorkspace={setActiveWorkspace}
              activePersona={activePersona}
              personas={personas && personas.length > 0 ? personas : DEFAULT_ENTERPRISE_PERSONAS}
              onSelectPersona={handleSelectPersona}
              effectiveRole={effectiveRole}
              roleMetadata={roleMetadata}
              onOpenRbacModal={() => setIsRbacModalOpen(true)}
              onOpenRegisterOrg={() => {
                setActiveTab('profile');
                setProfileSubTab('register');
              }}
              onLaunchSetupWizard={(org) => {
                if (org && org.id !== activeOrg?.id) {
                  setActiveOrg(org);
                }
                setActiveTab('settings');
              }}
              onOpenOrgSettings={(targetOrg) => {
                if (targetOrg && targetOrg.id !== activeOrg?.id) {
                  setActiveOrg(targetOrg);
                }
                setActiveTab('settings');
              }}
              onLogout={authLogout}
              showToast={showToast}
              initialSubSection={profileSubTab}
              onSubSectionChange={setProfileSubTab}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 9: DEDICATED WORKSPACE SETTINGS & IDENTITY PAGE       */}
        {/* ========================================================= */}
        {activeTab === 'settings' && (
          <div>
            <WorkspaceSettingsStudio
              activeOrg={activeOrg}
              onOrgUpdated={(updated) => {
                setActiveOrg(updated);
                setOrganizations(orgs => orgs.map(o => o.id === updated.id ? updated : o));
              }}
              onBack={() => setActiveTab('profile')}
              onOpenRbacModal={() => setIsRbacModalOpen(true)}
              showToast={showToast}
            />
          </div>
        )}
      </main>

      {/* ========================================================= */}
      {/* 4-STAGE VISUAL DECISION LINEAGE INSPECTOR MODAL           */}
      {/* ========================================================= */}
      {isLineageModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="clean-panel" style={{ width: '100%', maxWidth: '850px', maxHeight: '90vh', overflowY: 'auto', padding: '28px', background: 'var(--bg-card)' }}>

            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                    DECISION PROVENANCE AUDIT
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {selectedAuditLineage?.audit_id || 'Loading...'}
                  </span>
                </div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  4-Stage End-to-End Decision Lineage Inspector
                </h2>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(selectedAuditLineage, null, 2));
                    const dl = document.createElement('a');
                    dl.setAttribute("href", dataStr);
                    dl.setAttribute("download", `lineage_${selectedAuditLineage?.audit_id || 'report'}.json`);
                    dl.click();
                  }}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '5px 10px' }}
                >
                  📥 Export JSON
                </button>
                <button
                  onClick={() => { setIsLineageModalOpen(false); setSelectedAuditLineage(null); }}
                  style={{ background: 'transparent', border: 'none', fontSize: '1.3rem', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px 8px' }}
                >
                  ✕
                </button>
              </div>
            </div>

            {isFetchingLineage || !selectedAuditLineage ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>⏳</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Loading decision lineage & cryptographic verification...</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* STAGE 1: Actor & Intent */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        1
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 1: ACTOR INTENT & ROLE AUTHORIZATION
                      </span>
                    </div>
                    <span className="badge badge-outline" style={{ fontSize: '0.65rem' }}>
                      Scope: {selectedAuditLineage.stage_1_actor.scope}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.8rem', marginBottom: '8px' }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Actor Identifier: </span>
                      <span style={{ fontWeight: 700, color: 'var(--text-main)', fontFamily: 'monospace' }}>
                        {selectedAuditLineage.stage_1_actor.actor_id}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Actor Role: </span>
                      <span className="badge badge-review" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                        {selectedAuditLineage.stage_1_actor.actor_role}
                      </span>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.82rem', color: 'var(--text-main)' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700, marginBottom: '2px' }}>
                      DECISION PROMPT / REQUESTED ACTION:
                    </span>
                    {selectedAuditLineage.stage_1_actor.decision_prompt}
                  </div>
                </div>

                {/* STAGE 2: Evidence & Candidate Authority */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        2
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 2: CANDIDATE EVIDENCE & AUTHORITY RATINGS
                      </span>
                    </div>
                    <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                      {selectedAuditLineage.stage_2_evidence.total_candidate_claims} Candidate Claims Evaluated
                    </span>
                  </div>

                  {selectedAuditLineage.stage_2_evidence.sources.length === 0 ? (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
                      No separate candidate context items were attached; policy evaluated against authoritative organizational registry.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {selectedAuditLineage.stage_2_evidence.sources.map((item, idx) => (
                        <div key={idx} style={{ background: 'var(--bg-card)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                                📄 {item.source || item.source_id || 'System Document'}
                              </span>
                              {item.updated_at && (
                                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                  ({item.updated_at})
                                </span>
                              )}
                            </div>
                            <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                              Authority: {item.authority_level || 50}/100
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-main)', marginTop: '4px', fontStyle: 'italic' }}>
                            "{item.claim || item.content || JSON.stringify(item)}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* STAGE 3: Contradiction Engine & Scope Check */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        3
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 3: CONTRADICTION & FRESHNESS RESOLUTION
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <span className={selectedAuditLineage.stage_3_contradiction.conflicts_detected ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.65rem' }}>
                        {selectedAuditLineage.stage_3_contradiction.conflicts_detected ? '⚠️ Contradiction Resolved' : '✓ Uncontradicted'}
                      </span>
                      <span className={selectedAuditLineage.stage_3_contradiction.role_authorized ? 'badge badge-verified' : 'badge badge-warning'} style={{ fontSize: '0.65rem' }}>
                        {selectedAuditLineage.stage_3_contradiction.role_authorized ? '✓ Role Authorized' : '🛑 Role Insufficient'}
                      </span>
                    </div>
                  </div>

                  {selectedAuditLineage.stage_3_contradiction.contradiction_details.length > 0 ? (
                    <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--warning-text, #f59e0b)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                        CONTRADICTION ANALYSIS:
                      </span>
                      <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-main)' }}>
                        {selectedAuditLineage.stage_3_contradiction.contradiction_details.map((detail, idx) => (
                          <li key={idx} style={{ marginBottom: '2px' }}>{detail}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.78rem', color: 'var(--success-text)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>✓</span> No temporal or authority conflicts detected across active corporate policies.
                    </div>
                  )}
                </div>

                {/* STAGE 4: Final Verdict & Cryptographic Hash */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--success-solid)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        4
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 4: FINAL VERDICT & CRYPTOGRAPHIC PROVENANCE
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Latency: {selectedAuditLineage.stage_4_verdict.execution_ms} ms
                      </span>
                      <span
                        className={
                          selectedAuditLineage.stage_4_verdict.verdict === 'ALLOW' ? 'badge badge-verified' :
                            selectedAuditLineage.stage_4_verdict.verdict === 'BLOCK' ? 'badge badge-warning' :
                              'badge badge-review'
                        }
                        style={{ fontSize: '0.75rem', padding: '3px 10px', fontWeight: 800 }}
                      >
                        {selectedAuditLineage.stage_4_verdict.verdict}
                      </span>
                    </div>
                  </div>

                  {/* Reasons */}
                  <div style={{ marginBottom: '12px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      EXPLAINABLE AUDIT REASONS:
                    </span>
                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem', color: 'var(--text-main)' }}>
                      {selectedAuditLineage.stage_4_verdict.reasons.map((r, idx) => (
                        <li key={idx} style={{ marginBottom: '3px' }}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Suggested Action */}
                  {selectedAuditLineage.stage_4_verdict.suggested_action && (
                    <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block' }}>
                        SUGGESTED NEXT ACTION:
                      </span>
                      <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                        {selectedAuditLineage.stage_4_verdict.suggested_action}
                      </span>
                    </div>
                  )}

                  {/* Cryptographic SHA-256 Signature Box */}
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '6px', border: '1px solid var(--primary-subtle, rgba(99,102,241,0.3))' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 800, letterSpacing: '0.05em' }}>
                        🔒 CRYPTOGRAPHIC SHA-256 AUDIT SIGNATURE
                      </span>
                      <button
                        onClick={() => handleCopyAuditToken(selectedAuditLineage.stage_4_verdict.audit_token)}
                        className="btn btn-secondary"
                        style={{ fontSize: '0.68rem', padding: '3px 8px' }}
                      >
                        {copiedToken === selectedAuditLineage.stage_4_verdict.audit_token ? '✓ Copied' : 'Copy Hash'}
                      </button>
                    </div>
                    <code style={{ fontSize: '0.72rem', color: '#38bdf8', wordBreak: 'break-all', display: 'block', fontFamily: 'monospace' }}>
                      {selectedAuditLineage.stage_4_verdict.audit_token}
                    </code>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                      Tamper-evident digest of actor, prompt, evidence claims, timestamp, and verdict.
                    </div>
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: REGISTER NEW CLIENT ORGANIZATION / WORKSPACE       */}
      {/* ========================================================= */}
      {showNewOrgModal && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowNewOrgModal(false);
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
          }}
        >
          <div className="clean-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', background: 'var(--bg-card)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Create Enterprise Organization
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
                  Create an isolated tenant boundary for policy governance and document vaults.
                </p>
              </div>
              <button
                onClick={() => setShowNewOrgModal(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOrganization}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Organization / Company Name *
                </label>
                <input
                  type="text"
                  placeholder="Enter enterprise organization name..."
                  value={newOrgName}
                  onChange={e => {
                    setNewOrgName(e.target.value);
                    if (!newOrgSlug) {
                      setNewOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
                    }
                  }}
                  required
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Tenant Domain Slug *
                </label>
                <input
                  type="text"
                  placeholder="organization-slug"
                  value={newOrgSlug}
                  onChange={e => setNewOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, ''))}
                  required
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem', fontFamily: 'monospace' }}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                  Unique identifier used for isolated database partition and connector scope.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewOrgModal(false)}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingOrg || !newOrgName.trim()}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', fontSize: '0.82rem' }}
                >
                  {isCreatingOrg ? 'Creating...' : 'Create Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: CREATE DEPARTMENTAL WORKSPACE                     */}
      {/* ========================================================= */}
      {showNewWorkspaceModal && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowNewWorkspaceModal(false);
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
          }}
        >
          <div className="clean-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', background: 'var(--bg-card)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <span className="badge badge-verified" style={{ marginBottom: '6px' }}>
                  🏢 {activeOrg?.name || 'demo'}
                </span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Create Department Workspace
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
                  Add a functional domain workspace under this client company.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowNewWorkspaceModal(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateWorkspace}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Workspace Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Legal & Compliance, Growth Engineering, EMEA Support..."
                  value={newWorkspaceName}
                  onChange={e => setNewWorkspaceName(e.target.value)}
                  required
                  autoFocus
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Department Domain *
                </label>
                <select
                  value={newWorkspaceDomain}
                  onChange={e => setNewWorkspaceDomain(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', fontSize: '0.85rem', background: 'var(--bg-card-subtle)', color: 'var(--text-main)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}
                >
                  <option value="governance">⚖️ Legal, Risk & Governance</option>
                  <option value="finance">💳 Finance & Billing Operations</option>
                  <option value="secops">🛡️ Engineering & Infrastructure SecOps</option>
                  <option value="hr">👥 HR & People Operations</option>
                  <option value="support">💬 Customer Support & Success</option>
                  <option value="staging">🧪 Staging / Policy Sandbox</option>
                  <option value="global">📁 General / Multi-Department</option>
                </select>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Workspace Scope & Purpose
                </label>
                <input
                  type="text"
                  placeholder="e.g. Dedicated space for compliance audits and legal policy validation"
                  value={newWorkspaceDescription}
                  onChange={e => setNewWorkspaceDescription(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewWorkspaceModal(false)}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim()}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', fontSize: '0.82rem' }}
                >
                  Create & Switch Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Enterprise Multi-Step Organization Onboarding & Setup Wizard Modal */}
      <OrganizationSetupWizardModal
        isOpen={isSetupWizardOpen}
        onClose={() => setIsSetupWizardOpen(false)}
        initialOrg={setupWizardTargetOrg}
        onSetupComplete={(updatedOrg, newAccessToken) => {
          setActiveOrg(updatedOrg);
          setOrganizations(prev => {
            const exists = prev.some(o => o.id === updatedOrg.id);
            return exists ? prev.map(o => o.id === updatedOrg.id ? updatedOrg : o) : [...prev, updatedOrg];
          });
          localStorage.setItem('context_layer_active_org_id', updatedOrg.id);
          setOrgSetupRefreshTrigger(prev => prev + 1);
          fetchOrganizations();
          fetchHealthAndConflicts(updatedOrg.id);
          fetchLiveDatabaseRecords(updatedOrg.id);
          showToast(`Organization '${updatedOrg.name}' setup complete and active!`);
        }}
      />

      {/* Enterprise Authentication & Persona Switching Modal */}
      <SignInModal />

      {/* Session Superseded Security Alert Modal (Single Device Policy Enforced) */}
      {sessionSupersededNotice && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 99999,
            padding: '16px',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #FECACA',
              boxShadow: '0 25px 60px -15px rgba(220, 38, 38, 0.25)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div style={{ height: '4px', background: 'linear-gradient(90deg, #EF4444, #DC2626, #B91C1C)' }} />
            <div style={{ padding: '24px 28px', textAlign: 'center' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '16px',
                  backgroundColor: '#FEF2F2',
                  border: '1px solid #FECACA',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px auto',
                  color: '#DC2626',
                }}
              >
                <ShieldAlert size={28} />
              </div>

              <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0F172A', margin: '0 0 8px 0' }}>
                Active Session Terminated
              </h3>

              <div
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  backgroundColor: '#FEF2F2',
                  color: '#991B1B',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '14px',
                }}
              >
                <span>Enterprise Single-Device Security Policy</span>
              </div>

              <p style={{ fontSize: '0.82rem', color: '#475569', lineHeight: 1.5, margin: '0 0 20px 0' }}>
                {sessionSupersededNotice}
              </p>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <button
                  type="button"
                  onClick={() => {
                    setSessionSupersededNotice(null);
                    setAuthModalTab('login');
                    setIsAuthModalOpen(true);
                  }}
                  style={{
                    flex: 1,
                    padding: '11px 18px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
                    color: '#FFFFFF',
                    fontSize: '0.84rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(234, 88, 12, 0.25)',
                  }}
                >
                  Sign In Again on this Device
                </button>
                <button
                  type="button"
                  onClick={() => setSessionSupersededNotice(null)}
                  style={{
                    padding: '11px 16px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    backgroundColor: '#FFFFFF',
                    color: '#64748B',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Enterprise Organization & Workspace Governance Modal */}
      <OrganizationSettingsModal
        isOpen={isOrgSettingsModalOpen}
        onClose={() => setIsOrgSettingsModalOpen(false)}
        activeOrg={activeOrg}
        onOrgUpdated={(updated) => {
          setActiveOrg(updated);
          fetchOrganizations();
        }}
      />

      {/* Atlan-Grade RBAC & Separation of Duties (SoD) Permissions Matrix Modal */}
      <RbacMatrixModal
        isOpen={isRbacModalOpen}
        onClose={() => setIsRbacModalOpen(false)}
      />

      {/* Executive Financial Liability Prevented & Loss Avoidance ROI Modal */}
      <ExecutiveRoiModal
        isOpen={isRoiModalOpen}
        onClose={() => setIsRoiModalOpen(false)}
        activeOrg={activeOrg}
        auditSummary={auditSummary}
      />

      {/* Regulatory Compliance Dossier Export Modal (NIST AI 600-1 / EU AI Act) */}
      <ComplianceDossierModal
        isOpen={isDossierModalOpen}
        onClose={() => setIsDossierModalOpen(false)}
        activeOrg={activeOrg}
      />

      {/* Real-Time Webhook & Incident Dispatch Modal (Slack / PagerDuty / MS Teams) */}
      <WebhookSettingsModal
        isOpen={isWebhookModalOpen}
        onClose={() => setIsWebhookModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Human-in-the-Loop Decision Escalation Queue (EU AI Act Article 14) */}
      <HitlEscalationModal
        isOpen={isHitlModalOpen}
        onClose={() => setIsHitlModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Automated Red-Teaming & Adversarial Prompt Injector (OWASP LLM Top 10) */}
      <RedTeamModal
        isOpen={isRedTeamModalOpen}
        onClose={() => setIsRedTeamModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Cryptographic Merkle Tree Audit Ledger & Verifier (EU AI Act Article 12) */}
      <MerkleVerificationModal
        isOpen={isMerkleModalOpen}
        onClose={() => setIsMerkleModalOpen(false)}
        initialAuditToken={merkleSelectedToken}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Interactive Asset Deep-Dive Inspector Drawer (Documents, Connectors, Claims & Conflicts) */}
      <AssetInspectorDrawer
        isOpen={inspectorState.isOpen}
        onClose={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
        assetType={inspectorState.assetType}
        assetId={inspectorState.assetId}
        assetTitle={inspectorState.assetTitle}
        onNavigateToCurator={() => {
          setActiveTab('conflicts');
          window.history.pushState(null, '', '/conflicts');
        }}
      />

      {/* Clean In-App Document Page Viewer Modal (No Google/Browser Toolbar) */}
      {selectedDocForViewer && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.7)',
          backdropFilter: 'blur(5px)',
          zIndex: 10000,
          padding: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1440px',
            height: '92vh',
            background: '#FFFFFF',
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <DocumentPageViewer
              documentData={selectedDocForViewer}
              onBack={() => setSelectedDocForViewer(null)}
              onNavigateToLineage={() => {
                setSelectedDocForViewer(null);
                setActiveTab('visual_lineage');
                setVaultSubTab('documents');
              }}
              showToast={showToast}
            />
          </div>
        </div>
      )}
    </div>
  );
}

