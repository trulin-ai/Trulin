import React, { useState, useMemo } from 'react';
import {
  Database,
  ArrowLeft,
  ArrowUpRight,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Check,
  Settings,
  Eye,
  EyeOff,
  Headphones,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import ConnectorIcon from './ConnectorIcon';

/**
 * Clean 4-stage Enterprise Data Source Setup Wizard
 * Stage 1: Select Source
 * Stage 2: Connect & Configure
 * Stage 3: Processing & Governance
 * Stage 4: Validate & Activate
 */
export default function ConnectDataSourceWizard({
  initialStep = 1,
  catalogConnectors = [],
  supportedLiveCatalog = [],
  newSourceForm,
  setNewSourceForm,
  genericConfig,
  setGenericConfig,
  selectedConnectorMeta,
  setSelectedConnectorMeta,
  showTokenMask,
  setShowTokenMask,
  showPasswordMask,
  setShowPasswordMask,
  discoveredOptions,
  isDiscovering,
  handleDiscoverResource,
  isTestingConnection,
  testConnectionResult,
  setTestConnectionResult,
  handleTestConnection,
  isConnectingSource,
  handleConnectNewSource,
  onCancel,
  showToast
}) {
  const [wizardStep, setWizardStep] = useState(initialStep);
  const [stage1Search, setStage1Search] = useState('');
  const [stage1Category, setStage1Category] = useState('all');
  const [stage1Sort, setStage1Sort] = useState('featured'); // 'featured' | 'name_asc' | 'category'
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [sidebarSearch, setSidebarSearch] = useState('');
  const [paramsExpanded, setParamsExpanded] = useState(true);
  const [showDiscoveryDetails, setShowDiscoveryDetails] = useState(false);
  const [hasRunDiscovery, setHasRunDiscovery] = useState(false);

  // Step 3: Processing & Governance UI states
  const [autoContentDetection, setAutoContentDetection] = useState(true);
  const [evidenceClaimExtraction, setEvidenceClaimExtraction] = useState(true);
  const [extractionMode, setExtractionMode] = useState('Automatic');
  const [conflictHandling, setConflictHandling] = useState('Flag for review');
  const [policyEvaluation, setPolicyEvaluation] = useState(true);

  const liveIds = useMemo(
    () => new Set(supportedLiveCatalog.map(c => c.id)),
    [supportedLiveCatalog]
  );

  // Merge live metadata with full catalog so all connectors have rich descriptions & scopes
  const allConnectors = useMemo(() => {
    const liveMap = new Map(supportedLiveCatalog.map(c => [c.id, c]));
    return catalogConnectors.map(c => {
      const live = liveMap.get(c.id);
      return {
        ...c,
        isLiveSupported: liveIds.has(c.id),
        monitored_scope: c.monitored_scope || live?.scope || 'Enterprise schema & policy documents'
      };
    });
  }, [catalogConnectors, supportedLiveCatalog, liveIds]);

  const categories = useMemo(() => {
    const map = new Map();
    allConnectors.forEach(c => {
      const key = c.category || 'other';
      const label = c.category_label || key;
      if (!map.has(key)) map.set(key, { id: key, label, count: 0 });
      map.get(key).count += 1;
    });
    return [{ id: 'all', label: 'All Categories', count: allConnectors.length }, ...Array.from(map.values())];
  }, [allConnectors]);

  const stage1Filtered = useMemo(() => {
    const q = stage1Search.trim().toLowerCase();
    return allConnectors
      .filter(c => {
        if (stage1Category !== 'all' && c.category !== stage1Category) return false;
        if (!q) return true;
        return (
          (c.name || '').toLowerCase().includes(q) ||
          (c.category_label || '').toLowerCase().includes(q) ||
          (c.description || '').toLowerCase().includes(q) ||
          (c.id || '').toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        if (stage1Sort === 'name_asc') return (a.name || '').localeCompare(b.name || '');
        if (stage1Sort === 'category') return (a.category_label || '').localeCompare(b.category_label || '');
        // featured: live supported first, then alphabetical
        if (a.isLiveSupported !== b.isLiveSupported) return a.isLiveSupported ? -1 : 1;
        return (a.name || '').localeCompare(b.name || '');
      });
  }, [allConnectors, stage1Search, stage1Category, stage1Sort]);

  const sidebarFiltered = useMemo(() => {
    const q = sidebarSearch.trim().toLowerCase();
    return allConnectors
      .filter(c => {
        if (!q) return true;
        return (
          (c.name || '').toLowerCase().includes(q) ||
          (c.category_label || '').toLowerCase().includes(q) ||
          (c.id || '').toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        if (a.isLiveSupported !== b.isLiveSupported) return a.isLiveSupported ? -1 : 1;
        return (a.name || '').localeCompare(b.name || '');
      });
  }, [allConnectors, sidebarSearch]);

  const currentMeta = useMemo(() => {
    return (
      allConnectors.find(c => c.id === newSourceForm.sourceType) ||
      selectedConnectorMeta ||
      allConnectors[0] || {
        id: 'github',
        name: 'GitHub',
        icon: '🐙',
        category_label: 'Code repository',
        description: 'Version control and collaboration platform for software development and policy-as-code.',
        monitored_scope: 'GitHub repository markdown policies, OpenAPI specifications, security docs & CI/CD standards.'
      }
    );
  }, [allConnectors, newSourceForm.sourceType, selectedConnectorMeta]);

  const handleSelectConnector = (connector, advanceToStep2 = true) => {
    setSelectedConnectorMeta(connector);
    setNewSourceForm(prev => ({
      ...prev,
      sourceType: connector.id,
      name: `Production ${connector.name}`,
      authorityLevel: connector.id === 'slack' ? 50 : 85,
      pgPort: connector.default_port || prev.pgPort || 5432,
      externalId: ''
    }));
    setTestConnectionResult(null);
    setHasRunDiscovery(false);
    if (advanceToStep2) setWizardStep(2);
  };

  const getPrimaryDiscoverTarget = (sourceType) => {
    if (sourceType === 'github') return { target: 'repos', parent: null };
    if (sourceType === 'postgresql' || sourceType === 'postgres') return { target: 'schemas', parent: null };
    if (sourceType === 'mongodb' || sourceType === 'mongodb_atlas') return { target: 'databases', parent: null };
    if (sourceType === 'jira') return { target: 'projects', parent: null };
    if (sourceType === 'confluence') return { target: 'spaces', parent: null };
    return { target: 'repos', parent: null };
  };

  const discoveredItemsList = useMemo(() => {
    const st = newSourceForm.sourceType;
    if (st === 'github') return discoveredOptions.repos || [];
    if (st === 'postgresql' || st === 'postgres') return discoveredOptions.schemas || [];
    if (st === 'mongodb' || st === 'mongodb_atlas') return discoveredOptions.databases || [];
    if (st === 'jira') return discoveredOptions.projects || [];
    if (st === 'confluence') return discoveredOptions.spaces || [];
    return [];
  }, [newSourceForm.sourceType, discoveredOptions]);

  const handleStep4Discover = async () => {
    const { target, parent } = getPrimaryDiscoverTarget(newSourceForm.sourceType);
    await handleDiscoverResource(target, parent);
    setHasRunDiscovery(true);
  };

  const scheduleSummaryLabel =
    newSourceForm.schedule === '10m'
      ? 'Sync every 10 minutes'
      : newSourceForm.schedule === '1m'
      ? 'Sync every 1 minute'
      : newSourceForm.schedule === '1h'
      ? 'Sync hourly'
      : 'Manual sync';

  const stepperItems = [
    {
      num: 1,
      title: 'Select Source',
      subtitle: wizardStep > 1 ? 'Completed' : 'Choose system type'
    },
    {
      num: 2,
      title: wizardStep >= 3 ? 'Connect & Configure' : 'Auth & Config',
      subtitle: wizardStep > 2 ? 'Completed' : wizardStep === 2 ? 'Provide credentials' : 'Provide credentials'
    },
    {
      num: 3,
      title: wizardStep >= 3 ? 'Processing & Governance' : 'Policy & Scope',
      subtitle: wizardStep > 3 ? 'Completed' : wizardStep === 3 ? 'Active' : 'Set access and scope'
    },
    {
      num: 4,
      title: wizardStep >= 3 ? 'Validate & Activate' : 'Test & Connect',
      subtitle: wizardStep === 4 ? 'Active' : wizardStep === 3 ? 'Upcoming' : 'Verify and activate'
    }
  ];

  const inputStyle = {
    width: '100%',
    padding: '8px 11px',
    fontSize: '0.80rem',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    background: '#FFFFFF',
    color: '#0F172A',
    outline: 'none',
    boxSizing: 'border-box'
  };

  const labelStyle = {
    fontSize: '0.73rem',
    fontWeight: 700,
    color: '#1E293B',
    display: 'block',
    marginBottom: '5px'
  };

  const ToggleSwitch = ({ enabled, onToggle }) => (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={enabled}
      style={{
        width: '38px',
        height: '20px',
        borderRadius: '9999px',
        border: 'none',
        background: enabled ? '#F97316' : '#CBD5E1',
        position: 'relative',
        cursor: 'pointer',
        transition: 'background 0.15s ease',
        flexShrink: 0,
        padding: 0
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: '2px',
          left: enabled ? '20px' : '2px',
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          background: '#FFFFFF',
          transition: 'left 0.15s ease',
          boxShadow: '0 1px 2px rgba(0,0,0,0.2)'
        }}
      />
    </button>
  );

  // Reusable Left Sidebar for Stages 2, 3, and 4
  const renderSupportedSidebar = () => (
    <div
      style={{
        width: '250px',
        flexShrink: 0,
        background: '#FAF8F5',
        border: '1px solid #E2E8F0',
        borderRadius: '12px',
        padding: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        alignSelf: 'stretch'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '0.84rem', fontWeight: 800, color: '#0F172A' }}>
          Supported Connectors
        </span>
        <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#EA580C' }}>
          {allConnectors.length}
        </span>
      </div>

      <div style={{ position: 'relative' }}>
        <Search
          size={13}
          color="#94A3B8"
          style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
        />
        <input
          type="text"
          placeholder="Search connectors..."
          value={sidebarSearch}
          onChange={e => setSidebarSearch(e.target.value)}
          style={{
            width: '100%',
            padding: '7px 10px 7px 30px',
            fontSize: '0.75rem',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            background: '#FFFFFF',
            color: '#0F172A',
            outline: 'none',
            boxSizing: 'border-box'
          }}
        />
      </div>

      <div
        style={{
          flex: 1,
          maxHeight: '380px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          paddingRight: '2px'
        }}
      >
        {sidebarFiltered.map(c => {
          const isActive = c.id === currentMeta.id;
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => handleSelectConnector(c, false)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '8px 10px',
                borderRadius: '8px',
                border: isActive ? '1px solid #FDBA74' : '1px solid transparent',
                background: isActive ? '#FFF7ED' : 'transparent',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.12s ease'
              }}
              onMouseEnter={e => {
                if (!isActive) e.currentTarget.style.background = '#F8FAFC';
              }}
              onMouseLeave={e => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                <ConnectorIcon connector={c} size={30} />
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      color: '#0F172A',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                  >
                    {c.name}
                  </div>
                  <div
                    style={{
                      fontSize: '0.68rem',
                      color: '#64748B',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                  >
                    {c.category_label}
                  </div>
                </div>
              </div>
              <ChevronRight size={14} color={isActive ? '#EA580C' : '#94A3B8'} style={{ flexShrink: 0 }} />
            </button>
          );
        })}
      </div>

      {/* Bottom Support Box */}
      <div
        style={{
          marginTop: 'auto',
          background: '#FFF7ED',
          border: '1px solid #FFEDD5',
          borderRadius: '8px',
          padding: '10px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}
      >
        <Headphones size={16} color="#2563EB" style={{ flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: '0.73rem', fontWeight: 700, color: '#0F172A' }}>
            Need a custom connector?
          </div>
          <button
            type="button"
            onClick={() => showToast?.('Custom connector request noted — our integrations team will reach out.')}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              fontSize: '0.69rem',
              color: '#64748B',
              cursor: 'pointer',
              textAlign: 'left'
            }}
          >
            Contact our support team
          </button>
        </div>
      </div>
    </div>
  );

  // Reusable Provider Header inside Right Main Panel (Stages 2, 3, 4)
  const renderProviderHeader = (rightAction = null) => (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: '12px',
        paddingBottom: '14px',
        borderBottom: '1px solid #F1F5F9',
        marginBottom: '16px',
        flexWrap: 'wrap'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', flex: 1, minWidth: '240px' }}>
        <ConnectorIcon connector={currentMeta} size={44} />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <h4 style={{ margin: 0, fontSize: '1.08rem', fontWeight: 800, color: '#0F172A' }}>
              {currentMeta.name}
            </h4>
            <span
              style={{
                fontSize: '0.67rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '9999px',
                background: '#FFF7ED',
                color: '#EA580C',
                border: '1px solid #FFEDD5'
              }}
            >
              {currentMeta.category_label}
            </span>
          </div>
          <p style={{ margin: '4px 0 6px 0', fontSize: '0.75rem', color: '#475569', lineHeight: 1.4 }}>
            {currentMeta.description}
          </p>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              fontSize: '0.71rem',
              fontWeight: 600,
              color: '#EA580C'
            }}
          >
            <ExternalLink size={11} />
            <span>Monitored Contract Scope: {currentMeta.monitored_scope}</span>
          </div>
        </div>
      </div>
      {rightAction}
    </div>
  );

  return (
    <div
      style={{
        background: '#FAF8F5',
        border: '1px solid #E2E8F0',
        borderRadius: '14px',
        padding: '20px 24px',
        marginBottom: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}
    >
      {/* 1. TOP TITLE BAR */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '10px',
              background: '#FEF3C7',
              border: '1px solid #FDE68A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <Database size={20} color="#D97706" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.22rem', fontWeight: 800, color: '#0F172A' }}>
              Connect Enterprise Data Source
            </h3>
            <p style={{ margin: '2px 0 0 0', fontSize: '0.77rem', color: '#64748B' }}>
              Configure automated schema extraction, governance rules, and continuous synchronization.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onCancel}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 16px',
            borderRadius: '9999px',
            border: '1px solid #FDBA74',
            background: '#FFF7ED',
            color: '#EA580C',
            fontSize: '0.76rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <ArrowLeft size={13} />
          <span>Back to Live Connectors</span>
        </button>
      </div>

      {/* 2. 4-STEP HORIZONTAL STEPPER */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          padding: '6px 12px',
          position: 'relative'
        }}
      >
        {stepperItems.map((step, idx) => {
          const isCompleted = wizardStep > step.num;
          const isActive = wizardStep === step.num;
          const lineFilled = wizardStep > step.num;

          return (
            <React.Fragment key={step.num}>
              <div
                onClick={() => {
                  if (isCompleted) setWizardStep(step.num);
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  minWidth: '120px',
                  cursor: isCompleted ? 'pointer' : 'default',
                  zIndex: 1
                }}
              >
                <div
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: isCompleted || isActive ? '#F97316' : '#CBD5E1',
                    color: '#FFFFFF',
                    fontSize: '0.74rem',
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '6px',
                    boxShadow: isActive ? '0 0 0 3px rgba(249, 115, 22, 0.18)' : 'none'
                  }}
                >
                  {isCompleted ? <Check size={13} strokeWidth={3} /> : step.num}
                </div>
                <div
                  style={{
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    color: isActive && wizardStep >= 3 ? '#EA580C' : '#0F172A'
                  }}
                >
                  {step.title}
                </div>
                <div
                  style={{
                    fontSize: '0.67rem',
                    color: isActive && wizardStep >= 3 ? '#EA580C' : '#64748B',
                    marginTop: '1px'
                  }}
                >
                  {step.subtitle}
                </div>
              </div>

              {idx < stepperItems.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: '2px',
                    background: lineFilled ? '#F97316' : '#E2E8F0',
                    marginTop: '12px',
                    marginLeft: '-12px',
                    marginRight: '-12px'
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* ========================================================= */}
      {/* STAGE 1: SELECT SOURCE (CATALOG GRID)                     */}
      {/* ========================================================= */}
      {wizardStep === 1 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Search / Filter / Sort Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: '1 1 280px' }}>
              <Search
                size={14}
                color="#94A3B8"
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                placeholder="Search connectors..."
                value={stage1Search}
                onChange={e => setStage1Search(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 34px',
                  fontSize: '0.80rem',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  background: '#FFFFFF',
                  color: '#0F172A',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={() => setShowFilterMenu(prev => !prev)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  fontSize: '0.76rem',
                  fontWeight: 600,
                  border: stage1Category !== 'all' ? '1px solid #F97316' : '1px solid #E2E8F0',
                  borderRadius: '8px',
                  background: stage1Category !== 'all' ? '#FFF7ED' : '#FFFFFF',
                  color: stage1Category !== 'all' ? '#EA580C' : '#0F172A',
                  cursor: 'pointer'
                }}
              >
                <Filter size={13} />
                <span>{stage1Category === 'all' ? 'Filter' : categories.find(c => c.id === stage1Category)?.label}</span>
              </button>

              {showFilterMenu && (
                <div
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 'calc(100% + 4px)',
                    background: '#FFFFFF',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 8px 20px rgba(0,0,0,0.08)',
                    zIndex: 50,
                    minWidth: '210px',
                    maxHeight: '260px',
                    overflowY: 'auto',
                    padding: '4px'
                  }}
                >
                  {categories.map(cat => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => {
                        setStage1Category(cat.id);
                        setShowFilterMenu(false);
                      }}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        width: '100%',
                        padding: '6px 10px',
                        fontSize: '0.74rem',
                        fontWeight: stage1Category === cat.id ? 700 : 500,
                        background: stage1Category === cat.id ? '#FFF7ED' : 'transparent',
                        color: stage1Category === cat.id ? '#EA580C' : '#0F172A',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        textAlign: 'left'
                      }}
                    >
                      <span>{cat.label}</span>
                      <span style={{ color: '#94A3B8' }}>{cat.count}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <select
              value={stage1Sort}
              onChange={e => setStage1Sort(e.target.value)}
              style={{
                padding: '8px 12px',
                fontSize: '0.76rem',
                fontWeight: 600,
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                background: '#FFFFFF',
                color: '#0F172A',
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="featured">Sort by: Recommended</option>
              <option value="name_asc">Sort by: Name (A-Z)</option>
              <option value="category">Sort by: Category</option>
            </select>
          </div>

          {/* 5-Column Connector Cards Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, minmax(0, 1fr))',
              gap: '14px'
            }}
          >
            {stage1Filtered.map(connector => (
              <div
                key={connector.id}
                style={{
                  background: '#FAF8F5',
                  border: '1px solid #E2E8F0',
                  borderRadius: '10px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = '#CBD5E1';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(15,23,42,0.05)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = '#E2E8F0';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                    <ConnectorIcon connector={connector} size={36} />
                    <ArrowUpRight size={14} color="#64748B" />
                  </div>
                  <div style={{ fontSize: '0.90rem', fontWeight: 700, color: '#0F172A' }}>
                    {connector.name}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                    {connector.category_label}
                  </div>
                </div>

                <div style={{ paddingTop: '8px', borderTop: '1px solid #E2E8F0' }}>
                  <button
                    type="button"
                    onClick={() => handleSelectConnector(connector, true)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '6px',
                      border: '1px solid #F97316',
                      background: '#F97316',
                      color: '#FFFFFF',
                      cursor: 'pointer'
                    }}
                  >
                    Connect
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom Custom Connector Banner */}
          <div
            style={{
              background: '#FFF7ED',
              border: '1px solid #FFEDD5',
              borderRadius: '8px',
              padding: '12px 16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#0F172A' }}>
              Need a custom connector?
            </span>
            <button
              type="button"
              onClick={() => showToast?.('Custom connector request noted — our integrations team will reach out.')}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                fontSize: '0.76rem',
                fontWeight: 600,
                color: '#EA580C',
                cursor: 'pointer'
              }}
            >
              Contact our support team →
            </button>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STAGES 2, 3, 4: TWO-COLUMN WIZARD WORKBENCH               */}
      {/* ========================================================= */}
      {wizardStep >= 2 && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '18px', flexWrap: 'wrap' }}>
          {renderSupportedSidebar()}

          {/* RIGHT MAIN PANEL */}
          <div
            style={{
              flex: '1 1 560px',
              minWidth: 0,
              background: '#FAF8F5',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '20px 22px',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* STAGE 2: CONNECT & CONFIGURE */}
            {wizardStep === 2 && (
              <>
                {renderProviderHeader()}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {/* Card 1: Connector Instance Details */}
                  <div
                    style={{
                      border: '1px solid #E2E8F0',
                      borderRadius: '10px',
                      padding: '14px 16px',
                      background: '#FFFFFF'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '10px' }}>
                      <Settings size={14} color="#2563EB" />
                      <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0F172A' }}>
                        Connector Instance Details
                      </span>
                    </div>
                    <label style={labelStyle}>
                      Connector Instance Name <span style={{ color: '#EF4444' }}>*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Production GitHub"
                      value={newSourceForm.name}
                      onChange={e => setNewSourceForm({ ...newSourceForm, name: e.target.value })}
                      style={inputStyle}
                    />
                  </div>

                  {/* Card 2: Provider-Specific Connection Parameters */}
                  <div
                    style={{
                      border: '1px solid #E2E8F0',
                      borderRadius: '10px',
                      padding: '14px 16px',
                      background: '#FFFFFF'
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setParamsExpanded(prev => !prev)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '7px',
                        width: '100%',
                        background: 'none',
                        border: 'none',
                        padding: 0,
                        cursor: 'pointer',
                        marginBottom: paramsExpanded ? '12px' : 0,
                        textAlign: 'left'
                      }}
                    >
                      {paramsExpanded ? <ChevronUp size={15} color="#2563EB" /> : <ChevronDown size={15} color="#2563EB" />}
                      <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0F172A' }}>
                        {currentMeta.name} Connection Parameters
                      </span>
                    </button>

                    {paramsExpanded && (
                      <div style={{ display: 'grid', gap: '12px' }}>
                        {/* GITHUB */}
                        {newSourceForm.sourceType === 'github' && (
                          <>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>
                                  Owner / Organization <span style={{ color: '#EF4444' }}>*</span>
                                </label>
                                <input
                                  type="text"
                                  placeholder="e.g. facebook or your-org"
                                  value={newSourceForm.githubOwner}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, githubOwner: e.target.value }); setTestConnectionResult(null); }}
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>
                                  Branch <span style={{ color: '#EF4444' }}>*</span>
                                </label>
                                <input
                                  type="text"
                                  placeholder="main"
                                  value={newSourceForm.githubBranch}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, githubBranch: e.target.value }); setTestConnectionResult(null); }}
                                  style={inputStyle}
                                />
                              </div>
                            </div>

                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                                <label style={{ ...labelStyle, marginBottom: 0 }}>Personal Access Token (PAT)</label>
                                <span style={{ fontSize: '0.68rem', color: '#EA580C', fontWeight: 600 }}>Requires repo read scope</span>
                              </div>
                              <div style={{ position: 'relative' }}>
                                <input
                                  type={showTokenMask ? 'text' : 'password'}
                                  placeholder="ghp_... (Optional for public repos)"
                                  value={newSourceForm.githubToken}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, githubToken: e.target.value }); setTestConnectionResult(null); }}
                                  style={{ ...inputStyle, paddingRight: '34px' }}
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowTokenMask(!showTokenMask)}
                                  style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                >
                                  {showTokenMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                </button>
                              </div>
                            </div>

                            <div>
                              <label style={labelStyle}>
                                Target Repository (owner/repo) <span style={{ color: '#EF4444' }}>*</span>
                              </label>
                              <input
                                type="text"
                                placeholder="e.g. facebook/react or your-org/security-standards"
                                value={newSourceForm.githubRepo}
                                onChange={e => { setNewSourceForm({ ...newSourceForm, githubRepo: e.target.value }); setTestConnectionResult(null); }}
                                style={inputStyle}
                              />
                            </div>
                          </>
                        )}

                        {/* POSTGRESQL */}
                        {['postgresql', 'postgres'].includes(newSourceForm.sourceType) && (
                          <>
                            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Host / Hostname <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgHost}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, pgHost: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="localhost or db.internal"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Port <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="number"
                                  value={newSourceForm.pgPort}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, pgPort: e.target.value }); setTestConnectionResult(null); }}
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Database Name <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgDatabase}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, pgDatabase: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="postgres"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>SSL Mode</label>
                                <select
                                  value={newSourceForm.pgSslMode}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, pgSslMode: e.target.value }); setTestConnectionResult(null); }}
                                  style={inputStyle}
                                >
                                  <option value="prefer">prefer</option>
                                  <option value="require">require</option>
                                  <option value="disable">disable</option>
                                </select>
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Username <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgUsername}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, pgUsername: e.target.value }); setTestConnectionResult(null); }}
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Password</label>
                                <div style={{ position: 'relative' }}>
                                  <input
                                    type={showPasswordMask ? 'text' : 'password'}
                                    value={newSourceForm.pgPassword}
                                    onChange={e => { setNewSourceForm({ ...newSourceForm, pgPassword: e.target.value }); setTestConnectionResult(null); }}
                                    placeholder="••••••••"
                                    style={{ ...inputStyle, paddingRight: '34px' }}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowPasswordMask(!showPasswordMask)}
                                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                  >
                                    {showPasswordMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                  </button>
                                </div>
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Target Schema(s)</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgSchemas}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgSchemas: e.target.value })}
                                  placeholder="public, analytics"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Tables (Optional filter)</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgTables}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgTables: e.target.value })}
                                  placeholder="e.g. users, policies"
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                          </>
                        )}

                        {/* MONGODB ATLAS */}
                        {['mongodb', 'mongodb_atlas', 'mongodb_self', 'documentdb'].includes(newSourceForm.sourceType) && (
                          <>
                            <div>
                              <label style={labelStyle}>Connection URI <span style={{ color: '#EF4444' }}>*</span></label>
                              <div style={{ position: 'relative' }}>
                                <input
                                  type={showPasswordMask ? 'text' : 'password'}
                                  value={newSourceForm.mongoUri}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, mongoUri: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="mongodb+srv://user:pass@cluster.mongodb.net/test"
                                  style={{ ...inputStyle, paddingRight: '34px' }}
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowPasswordMask(!showPasswordMask)}
                                  style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                >
                                  {showPasswordMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                </button>
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Database Name <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={newSourceForm.mongoDatabase}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, mongoDatabase: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="production"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Target Collections (comma-separated)</label>
                                <input
                                  type="text"
                                  value={newSourceForm.mongoCollections}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, mongoCollections: e.target.value })}
                                  placeholder="policies, controls"
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                          </>
                        )}

                        {/* JIRA */}
                        {newSourceForm.sourceType === 'jira' && (
                          <>
                            <div>
                              <label style={labelStyle}>Jira Site URL <span style={{ color: '#EF4444' }}>*</span></label>
                              <input
                                type="text"
                                value={newSourceForm.jiraBaseUrl}
                                onChange={e => { setNewSourceForm({ ...newSourceForm, jiraBaseUrl: e.target.value }); setTestConnectionResult(null); }}
                                placeholder="https://your-org.atlassian.net"
                                style={inputStyle}
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Atlassian Email <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="email"
                                  value={newSourceForm.jiraEmail}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, jiraEmail: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="user@company.com"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>API Token <span style={{ color: '#EF4444' }}>*</span></label>
                                <div style={{ position: 'relative' }}>
                                  <input
                                    type={showTokenMask ? 'text' : 'password'}
                                    value={newSourceForm.jiraToken}
                                    onChange={e => { setNewSourceForm({ ...newSourceForm, jiraToken: e.target.value }); setTestConnectionResult(null); }}
                                    placeholder="ATATT..."
                                    style={{ ...inputStyle, paddingRight: '34px' }}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowTokenMask(!showTokenMask)}
                                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                  >
                                    {showTokenMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                  </button>
                                </div>
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Project Key <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={newSourceForm.jiraProject}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, jiraProject: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="e.g. SEC or ENG"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>JQL Filter (Optional)</label>
                                <input
                                  type="text"
                                  value={newSourceForm.jiraFilter}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, jiraFilter: e.target.value })}
                                  placeholder="status != Done"
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                          </>
                        )}

                        {/* CONFLUENCE */}
                        {newSourceForm.sourceType === 'confluence' && (
                          <>
                            <div>
                              <label style={labelStyle}>Confluence Base URL <span style={{ color: '#EF4444' }}>*</span></label>
                              <input
                                type="text"
                                value={newSourceForm.confluenceBaseUrl}
                                onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceBaseUrl: e.target.value }); setTestConnectionResult(null); }}
                                placeholder="https://your-org.atlassian.net/wiki"
                                style={inputStyle}
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Atlassian Email <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="email"
                                  value={newSourceForm.confluenceEmail}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceEmail: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="user@company.com"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>API Token <span style={{ color: '#EF4444' }}>*</span></label>
                                <div style={{ position: 'relative' }}>
                                  <input
                                    type={showTokenMask ? 'text' : 'password'}
                                    value={newSourceForm.confluenceToken}
                                    onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceToken: e.target.value }); setTestConnectionResult(null); }}
                                    placeholder="ATATT..."
                                    style={{ ...inputStyle, paddingRight: '34px' }}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowTokenMask(!showTokenMask)}
                                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                  >
                                    {showTokenMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                  </button>
                                </div>
                              </div>
                            </div>
                            <div>
                              <label style={labelStyle}>Space Keys (comma-separated) <span style={{ color: '#EF4444' }}>*</span></label>
                              <input
                                type="text"
                                value={newSourceForm.confluenceSpace}
                                onChange={e => { setNewSourceForm({ ...newSourceForm, confluenceSpace: e.target.value }); setTestConnectionResult(null); }}
                                placeholder="e.g. HR, SEC, LEGAL"
                                style={inputStyle}
                              />
                            </div>
                          </>
                        )}

                        {/* SLACK */}
                        {newSourceForm.sourceType === 'slack' && (
                          <>
                            <div>
                              <label style={labelStyle}>Slack Bot Token <span style={{ color: '#EF4444' }}>*</span></label>
                              <div style={{ position: 'relative' }}>
                                <input
                                  type={showTokenMask ? 'text' : 'password'}
                                  value={newSourceForm.slackBotToken}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, slackBotToken: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="xoxb-..."
                                  style={{ ...inputStyle, paddingRight: '34px' }}
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowTokenMask(!showTokenMask)}
                                  style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                >
                                  {showTokenMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                </button>
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Channel IDs or Names</label>
                                <input
                                  type="text"
                                  value={newSourceForm.slackChannels}
                                  onChange={e => { setNewSourceForm({ ...newSourceForm, slackChannels: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="#security-policies, #hr-updates"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Lookback Days</label>
                                <input
                                  type="number"
                                  value={newSourceForm.slackLookbackDays}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, slackLookbackDays: e.target.value })}
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                          </>
                        )}

                        {/* GENERIC CONNECTORS (Salesforce, Snowflake, Kafka, etc.) */}
                        {!['github', 'postgresql', 'postgres', 'mongodb', 'mongodb_atlas', 'mongodb_self', 'documentdb', 'jira', 'confluence', 'slack'].includes(newSourceForm.sourceType) && (
                          <>
                            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Endpoint / Host / Bootstrap Server <span style={{ color: '#EF4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={genericConfig.host}
                                  onChange={e => { setGenericConfig({ ...genericConfig, host: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder={`e.g. ${newSourceForm.sourceType}-cluster.prod.internal`}
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>Port</label>
                                <input
                                  type="text"
                                  value={genericConfig.port}
                                  onChange={e => { setGenericConfig({ ...genericConfig, port: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="443"
                                  style={inputStyle}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              <div>
                                <label style={labelStyle}>Database / Workspace / Org</label>
                                <input
                                  type="text"
                                  value={genericConfig.database}
                                  onChange={e => { setGenericConfig({ ...genericConfig, database: e.target.value }); setTestConnectionResult(null); }}
                                  placeholder="production"
                                  style={inputStyle}
                                />
                              </div>
                              <div>
                                <label style={labelStyle}>API Key / Secret</label>
                                <div style={{ position: 'relative' }}>
                                  <input
                                    type={showPasswordMask ? 'text' : 'password'}
                                    value={genericConfig.password}
                                    onChange={e => { setGenericConfig({ ...genericConfig, password: e.target.value }); setTestConnectionResult(null); }}
                                    placeholder="••••••••"
                                    style={{ ...inputStyle, paddingRight: '34px' }}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowPasswordMask(!showPasswordMask)}
                                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}
                                  >
                                    {showPasswordMask ? <Eye size={14} /> : <EyeOff size={14} />}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Stage 2 Footer */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px' }}>
                    <button
                      type="button"
                      onClick={() => setWizardStep(1)}
                      style={{
                        padding: '7px 18px',
                        borderRadius: '9999px',
                        border: '1px solid #FDBA74',
                        background: '#FFFFFF',
                        color: '#EA580C',
                        fontSize: '0.76rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (!newSourceForm.name.trim()) {
                          showToast?.('Please enter a Connector Instance Name', 'error');
                          return;
                        }
                        setWizardStep(3);
                      }}
                      style={{
                        padding: '8px 20px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: '#F97316',
                        color: '#FFFFFF',
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      Continue to Processing & Governance →
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* STAGE 3: PROCESSING & GOVERNANCE */}
            {wizardStep === 3 && (
              <>
                {renderProviderHeader()}

                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.94rem', fontWeight: 800, color: '#0F172A' }}>
                    Processing & Governance
                  </h4>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.74rem', color: '#64748B' }}>
                    Configure how Trulin processes, evaluates and synchronizes connected data.
                  </p>
                </div>

                {/* 1. Data Processing */}
                <div style={{ paddingBottom: '16px', marginBottom: '16px', borderBottom: '1px solid #F1F5F9' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#0F172A', marginBottom: '10px' }}>
                    1. Data Processing
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                      <div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>Automatic Content Detection</div>
                        <div style={{ fontSize: '0.67rem', color: '#64748B' }}>Identify content types automatically.</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 600 }}>
                          {autoContentDetection ? 'Enabled' : 'Disabled'}
                        </span>
                        <ToggleSwitch enabled={autoContentDetection} onToggle={() => setAutoContentDetection(p => !p)} />
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                      <div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>Evidence & Claim Extraction</div>
                        <div style={{ fontSize: '0.67rem', color: '#64748B' }}>Extract claims and supporting evidence.</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 600 }}>
                          {evidenceClaimExtraction ? 'Enabled' : 'Disabled'}
                        </span>
                        <ToggleSwitch enabled={evidenceClaimExtraction} onToggle={() => setEvidenceClaimExtraction(p => !p)} />
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>Extraction Mode</div>
                      <select
                        value={extractionMode}
                        onChange={e => setExtractionMode(e.target.value)}
                        style={{ ...inputStyle, padding: '6px 10px', fontSize: '0.76rem' }}
                      >
                        <option value="Automatic">Automatic</option>
                        <option value="Strict Normative">Strict Normative</option>
                        <option value="Full Document">Full Document</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* 2. Trust & Governance */}
                <div style={{ paddingBottom: '16px', marginBottom: '16px', borderBottom: '1px solid #F1F5F9' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#0F172A', marginBottom: '10px' }}>
                    2. Trust & Governance
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>Trust Authority Threshold</span>
                        <span style={{ fontSize: '0.76rem', fontWeight: 800, color: '#EA580C' }}>{newSourceForm.authorityLevel}%</span>
                      </div>
                      <div style={{ fontSize: '0.67rem', color: '#64748B', marginBottom: '6px' }}>
                        Minimum authority for trusted evidence.
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="100"
                        value={newSourceForm.authorityLevel}
                        onChange={e => setNewSourceForm({ ...newSourceForm, authorityLevel: e.target.value })}
                        style={{ width: '100%', accentColor: '#F97316', cursor: 'pointer' }}
                      />
                    </div>

                    <div>
                      <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>Conflicting Claim Handling</div>
                      <select
                        value={conflictHandling}
                        onChange={e => setConflictHandling(e.target.value)}
                        style={{ ...inputStyle, padding: '6px 10px', fontSize: '0.76rem' }}
                      >
                        <option value="Flag for review">Flag for review</option>
                        <option value="Supersede by authority">Supersede by authority</option>
                        <option value="Quarantine both">Quarantine both</option>
                      </select>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                      <div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>Policy Evaluation</div>
                        <div style={{ fontSize: '0.67rem', color: '#64748B' }}>Apply governance policies automatically.</div>
                      </div>
                      <ToggleSwitch enabled={policyEvaluation} onToggle={() => setPolicyEvaluation(p => !p)} />
                    </div>
                  </div>
                </div>

                {/* 3. Synchronization */}
                <div style={{ paddingBottom: '18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
                    <div>
                      <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#0F172A' }}>3. Synchronization</div>
                      <div style={{ fontSize: '0.69rem', color: '#64748B', marginTop: '2px' }}>
                        Choose how often connected data is synchronized.
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(120px, 1fr))', gap: '10px', flex: '1 1 360px' }}>
                      {[
                        { id: 'off', label: 'Manual' },
                        { id: '10m', label: 'Every 10 minutes' },
                        { id: '1m', label: 'Every 1 minute' }
                      ].map(opt => {
                        const isSelected = (newSourceForm.schedule || 'off') === opt.id;
                        return (
                          <button
                            key={opt.id}
                            type="button"
                            onClick={() => setNewSourceForm(prev => ({ ...prev, schedule: opt.id }))}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              padding: '9px 12px',
                              borderRadius: '8px',
                              border: isSelected ? '1.5px solid #F97316' : '1px solid #E2E8F0',
                              background: isSelected ? '#FFF7ED' : '#FFFFFF',
                              color: isSelected ? '#EA580C' : '#0F172A',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            <span
                              style={{
                                width: '14px',
                                height: '14px',
                                borderRadius: '50%',
                                border: isSelected ? '4px solid #F97316' : '1.5px solid #CBD5E1',
                                background: '#FFFFFF',
                                boxSizing: 'border-box',
                                flexShrink: 0
                              }}
                            />
                            <span>{opt.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Stage 3 Footer */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    style={{
                      padding: '7px 18px',
                      borderRadius: '9999px',
                      border: '1px solid #FDBA74',
                      background: '#FFFFFF',
                      color: '#EA580C',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(4)}
                    style={{
                      padding: '8px 20px',
                      borderRadius: '9999px',
                      border: 'none',
                      background: '#F97316',
                      color: '#FFFFFF',
                      fontSize: '0.76rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Continue to Validate & Activate →
                  </button>
                </div>
              </>
            )}

            {/* STAGE 4: VALIDATE & ACTIVATE */}
            {wizardStep === 4 && (
              <>
                {renderProviderHeader()}

                <div style={{ marginBottom: '14px' }}>
                  <h4 style={{ margin: 0, fontSize: '0.94rem', fontWeight: 800, color: '#0F172A' }}>
                    Validate & Activate
                  </h4>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.74rem', color: '#64748B' }}>
                    Verify the connection, discover available data and activate the connector.
                  </p>
                </div>

                {/* Row 1: Test Connection */}
                <div style={{ padding: '14px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{ fontSize: '0.80rem', fontWeight: 800, color: '#0F172A' }}>1. Test Connection</span>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: testConnectionResult
                              ? testConnectionResult.success
                                ? '#DCFCE7'
                                : '#FEE2E2'
                              : '#FEF3C7',
                            color: testConnectionResult
                              ? testConnectionResult.success
                                ? '#15803D'
                                : '#B91C1C'
                              : '#B45309'
                          }}
                        >
                          {testConnectionResult
                            ? testConnectionResult.success
                              ? 'Connected'
                              : 'Failed'
                            : 'Not Tested'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '3px' }}>
                        Validate credentials, authentication and access permissions.
                        <br />
                        Run a connection test to unlock data discovery.
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleTestConnection}
                      disabled={isTestingConnection}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 18px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: '#F97316',
                        color: '#FFFFFF',
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        cursor: isTestingConnection ? 'wait' : 'pointer',
                        minWidth: '145px',
                        justifyContent: 'center'
                      }}
                    >
                      {isTestingConnection && <RefreshCw size={12} className="spin" />}
                      <span>{isTestingConnection ? 'Testing...' : 'Test Connection'}</span>
                    </button>
                  </div>

                  {testConnectionResult && (
                    <div
                      style={{
                        marginTop: '10px',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        fontSize: '0.74rem',
                        background: testConnectionResult.success ? '#F0FDF4' : '#FEF2F2',
                        border: `1px solid ${testConnectionResult.success ? '#BBF7D0' : '#FCA5A5'}`,
                        color: testConnectionResult.success ? '#15803D' : '#B91C1C'
                      }}
                    >
                      <strong>{testConnectionResult.success ? '✓ ' : '✕ '}</strong>
                      {testConnectionResult.message}
                    </div>
                  )}
                </div>

                {/* Row 2: Discover Data */}
                <div style={{ padding: '14px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{ fontSize: '0.80rem', fontWeight: 800, color: '#0F172A' }}>2. Discover Data</span>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: hasRunDiscovery ? '#DCFCE7' : '#F1F5F9',
                            color: hasRunDiscovery ? '#15803D' : '#64748B'
                          }}
                        >
                          {hasRunDiscovery ? 'Discovered' : 'Pending'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '3px' }}>
                        Available after a successful connection test.
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleStep4Discover}
                      disabled={!testConnectionResult?.success || isDiscovering}
                      style={{
                        padding: '8px 18px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: testConnectionResult?.success ? '#F97316' : '#E2E8F0',
                        color: testConnectionResult?.success ? '#FFFFFF' : '#64748B',
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        cursor: testConnectionResult?.success ? 'pointer' : 'not-allowed',
                        minWidth: '145px'
                      }}
                    >
                      {isDiscovering ? 'Discovering...' : 'Discover Data'}
                    </button>
                  </div>

                  {/* Discovery Metrics Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '12px' }}>
                    <div>
                      <div style={{ fontSize: '0.69rem', color: '#64748B' }}>Total resources</div>
                      <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                        {hasRunDiscovery ? discoveredItemsList.length : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.69rem', color: '#64748B' }}>Supported resources</div>
                      <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                        {hasRunDiscovery ? discoveredItemsList.length : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.69rem', color: '#64748B' }}>Unsupported resources</div>
                      <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                        {hasRunDiscovery ? 0 : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.69rem', color: '#64748B' }}>Detected data types</div>
                      <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                        {hasRunDiscovery ? currentMeta.category_label : '—'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Row 3: Review Ingestion */}
                <div style={{ padding: '14px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{ fontSize: '0.80rem', fontWeight: 800, color: '#0F172A' }}>3. Review Ingestion</span>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: testConnectionResult?.success ? '#DCFCE7' : '#F1F5F9',
                            color: testConnectionResult?.success ? '#15803D' : '#64748B'
                          }}
                        >
                          {testConnectionResult?.success ? 'Ready' : 'Pending'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '3px' }}>
                        After discovery, review resources, supported formats, exclusions and permission warnings.
                      </div>
                      <div style={{ fontSize: '0.71rem', color: '#1E293B', fontWeight: 700, marginTop: '6px' }}>
                        Processing settings from Step 3
                      </div>
                      <div style={{ fontSize: '0.70rem', color: '#2563EB', marginTop: '1px' }}>
                        {autoContentDetection ? 'Automatic detection' : 'Manual detection'}
                        {evidenceClaimExtraction ? ' & extraction' : ''} · {extractionMode} mode · Trust ≥ {newSourceForm.authorityLevel}% · Policy evaluation {policyEvaluation ? 'on' : 'off'} · {scheduleSummaryLabel}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setShowDiscoveryDetails(p => !p)}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: '#F1F5F9',
                        color: '#475569',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        minWidth: '145px'
                      }}
                    >
                      View discovery details {showDiscoveryDetails ? '▴' : '▾'}
                    </button>
                  </div>

                  {showDiscoveryDetails && (
                    <div
                      style={{
                        marginTop: '10px',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        background: '#F8FAFC',
                        border: '1px solid #E2E8F0',
                        fontSize: '0.72rem',
                        color: '#334155'
                      }}
                    >
                      {discoveredItemsList.length > 0 ? (
                        <div>
                          <strong>Discovered items:</strong> {discoveredItemsList.slice(0, 10).join(', ')}
                          {discoveredItemsList.length > 10 ? ` (+${discoveredItemsList.length - 10} more)` : ''}
                        </div>
                      ) : (
                        <div>
                          Instance: <strong>{newSourceForm.name}</strong> · Provider: <strong>{currentMeta.name}</strong> · Conflict Policy: <strong>{conflictHandling}</strong>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Row 4: Activate Connector */}
                <div style={{ padding: '14px 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{ fontSize: '0.80rem', fontWeight: 800, color: '#0F172A' }}>4. Activate Connector</span>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: testConnectionResult?.success ? '#DCFCE7' : '#F1F5F9',
                            color: testConnectionResult?.success ? '#15803D' : '#64748B'
                          }}
                        >
                          {testConnectionResult?.success ? 'Ready' : 'Pending'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '3px' }}>
                        Save configuration and start processing discovered data.
                      </div>
                      <div style={{ fontSize: '0.70rem', color: '#64748B', marginTop: '2px' }}>
                        {currentMeta.name} · {autoContentDetection ? 'Automatic processing' : 'Manual processing'} ·{' '}
                        {testConnectionResult?.success ? 'Validated & ready to activate' : 'Activation pending validation and review'}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleConnectNewSource}
                      disabled={isConnectingSource || !testConnectionResult?.success}
                      style={{
                        padding: '8px 18px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: testConnectionResult?.success ? '#F97316' : '#FFEDD5',
                        color: testConnectionResult?.success ? '#FFFFFF' : '#9A3412',
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        cursor: testConnectionResult?.success ? 'pointer' : 'not-allowed',
                        minWidth: '145px'
                      }}
                    >
                      {isConnectingSource ? 'Activating...' : 'Save & Activate'}
                    </button>
                  </div>
                </div>

                {/* Stage 4 Footer */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', flexWrap: 'wrap', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    style={{
                      padding: '7px 18px',
                      borderRadius: '9999px',
                      border: '1px solid #FDBA74',
                      background: '#FFFFFF',
                      color: '#EA580C',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Back
                  </button>
                  <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                    Complete connection testing, discovery and review before activation.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
