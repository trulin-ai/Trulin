import React, { useState, useEffect } from 'react';
import {
  Compass,
  Terminal,
  KeyRound,
  Activity,
  ShieldAlert,
  BookOpen,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Database
} from 'lucide-react';

const normalizeMcpSubView = (view) => {
  if (!view || view === 'overview') return 'overview';
  if (view === 'tester' || view === 'resources' || view === 'middleware' || view === 'explorer') return 'explorer';
  if (view === 'tokens' || view === 'configs' || view === 'sdks' || view === 'credentials') return 'credentials';
  if (view === 'telemetry') return 'telemetry';
  if (view === 'proxies' || view === 'sandbox') return 'sandbox';
  return 'overview';
};

export default function McpIntegrationStudio({
  activeOrg,
  showToast,
  initialSubView = 'overview',
  onSubViewChange,
  onOpenDocs
}) {
  const [activeSubView, setActiveSubView] = useState(() => normalizeMcpSubView(initialSubView));
  const [explorerMode, setExplorerMode] = useState(() => {
    if (initialSubView === 'resources') return 'resources';
    if (initialSubView === 'middleware') return 'interception';
    return 'tools';
  });
  
  // Interactive Tester State
  const [selectedTool, setSelectedTool] = useState('context_trust_steward_audit');
  const [toolQuery, setToolQuery] = useState('What is the maximum allowed automated refund policy?');
  const [minTrustScore, setMinTrustScore] = useState(0.75);
  const [maxResults, setMaxResults] = useState(5);
  const [actionType, setActionType] = useState('Process automated refund claim');
  const [actorId, setActorId] = useState('billing-agent-01');
  const [actorRole, setActorRole] = useState('support');
  const [searchText, setSearchText] = useState('refund');
  const [claimText, setClaimText] = useState('Refund window is strictly limited to 30 days.');
  const [invoking, setInvoking] = useState(false);
  const [invocationResult, setInvocationResult] = useState({
    success: true,
    tool: "context_trust_steward_audit",
    result: {
      health_score: 94.8,
      grade: "A",
      claims_verified: 147,
      pending_conflicts: 0,
      status: "healthy"
    }
  });
  
  // Configs State
  const [activeSnippet, setActiveSnippet] = useState('claude');
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Live Telemetry State
  const [telemetryEvents, setTelemetryEvents] = useState([]);
  const [telemetryStats, setTelemetryStats] = useState({
    total_invocations: 10,
    allowed_count: 6,
    blocked_count: 2,
    review_count: 2,
    avg_latency_ms: 127,
    avg_trust_score: 0.92,
    active_connections: 4
  });
  const [telemetryFilter, setTelemetryFilter] = useState('all');
  const [autoRefreshTelemetry, setAutoRefreshTelemetry] = useState(true);

  // Agent Tokens (RBAC) State
  const [agentTokens, setAgentTokens] = useState([]);
  const [showCreateTokenModal, setShowCreateTokenModal] = useState(false);
  const [newTokenName, setNewTokenName] = useState('');
  const [newTokenAgentId, setNewTokenAgentId] = useState('');
  const [newTokenRole, setNewTokenRole] = useState('developer');
  const [newTokenTools, setNewTokenTools] = useState(['*']);
  const [newTokenRpm, setNewTokenRpm] = useState(60);
  const [isCreatingToken, setIsCreatingToken] = useState(false);
  const [copiedTokenId, setCopiedTokenId] = useState(null);

  // Resources & Prompts State
  const [mcpResources, setMcpResources] = useState([]);
  const [mcpPrompts, setMcpPrompts] = useState([]);
  const [selectedResourceUri, setSelectedResourceUri] = useState('context://policies/active');
  const [resourceContent, setResourceContent] = useState(null);
  const [isLoadingResource, setIsLoadingResource] = useState(false);
  const [selectedPromptName, setSelectedPromptName] = useState('governed_financial_decision');
  const [promptArgs, setPromptArgs] = useState('{\n  "action": "Issue $1,200 credit",\n  "account_tier": "enterprise"\n}');
  const [hydratedPrompt, setHydratedPrompt] = useState(null);
  const [isHydratingPrompt, setIsHydratingPrompt] = useState(false);

  // 3rd-Party Proxy Tools State
  const [proxyTools, setProxyTools] = useState([]);
  const [selectedProxyTool, setSelectedProxyTool] = useState(null);
  const [proxyToolArgs, setProxyToolArgs] = useState('{\n  "query": "SELECT user_id FROM accounts LIMIT 20"\n}');
  const [proxyActorRole, setProxyActorRole] = useState('developer');
  const [isExecutingProxy, setIsExecutingProxy] = useState(false);
  const [proxyResult, setProxyResult] = useState({
    tool: "execute_sql_query",
    policy_checks: "ready",
    interceptor: "active",
    waiting_execution: true
  });

  // Tool Interception Middleware State
  const [interceptToolName, setInterceptToolName] = useState('execute_sql');
  const [interceptRole, setInterceptRole] = useState('developer');
  const [interceptArgs, setInterceptArgs] = useState('{\n  "query": "SELECT * FROM users WHERE status = \'active\'"\n}');
  const [interceptResult, setInterceptResult] = useState(null);
  const [isIntercepting, setIsIntercepting] = useState(false);

  useEffect(() => {
    if (initialSubView) {
      setActiveSubView(normalizeMcpSubView(initialSubView));
      if (initialSubView === 'resources') setExplorerMode('resources');
      else if (initialSubView === 'middleware') setExplorerMode('interception');
      else if (initialSubView === 'tester') setExplorerMode('tools');
    }
  }, [initialSubView]);

  const handleSelectSubView = (subView) => {
    setActiveSubView(subView);
    if (onSubViewChange) onSubViewChange(subView);
  };

  const getStudioAuthHeaders = (extra = {}) => {
    const jwt = localStorage.getItem('ctl_token');
    return jwt ? { Authorization: `Bearer ${jwt}`, ...extra } : { ...extra };
  };

  // Fetch telemetry
  const fetchTelemetry = async () => {
    try {
      let url = '/v1/mcp/telemetry?limit=50';
      if (telemetryFilter !== 'all') {
        url += `&filter=${encodeURIComponent(telemetryFilter)}`;
      }
      const res = await fetch(url, { headers: getStudioAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setTelemetryEvents(data.events || []);
        if (data.stats) setTelemetryStats(data.stats);
      }
    } catch (e) {
      console.error("Failed to load MCP telemetry", e);
    }
  };

  // Fetch Tokens
  const fetchTokens = async () => {
    try {
      const res = await fetch('/v1/mcp/tokens', { headers: getStudioAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setAgentTokens(data.tokens || []);
      }
    } catch (e) {
      console.error("Failed to load agent tokens", e);
    }
  };

  // Fetch Resources & Prompts
  const fetchResourcesAndPrompts = async () => {
    try {
      const [resR, resP] = await Promise.all([
        fetch('/v1/mcp/resources'),
        fetch('/v1/mcp/prompts')
      ]);
      if (resR.ok) {
        const dataR = await resR.json();
        setMcpResources(dataR.resources || []);
      }
      if (resP.ok) {
        const dataP = await resP.json();
        setMcpPrompts(dataP.prompts || []);
      }
    } catch (e) {
      console.error("Failed to load resources/prompts", e);
    }
  };

  // Fetch Proxy Tools
  const fetchProxyTools = async () => {
    try {
      const res = await fetch('/v1/mcp/proxies');
      if (res.ok) {
        const data = await res.json();
        setProxyTools(data.tools || []);
        if (data.tools && data.tools.length > 0 && !selectedProxyTool) {
          setSelectedProxyTool(data.tools[0]);
          setProxyToolArgs(JSON.stringify(data.tools[0].sample_args || {}, null, 2));
          setProxyActorRole(data.tools[0].default_role || 'developer');
        }
      }
    } catch (e) {
      console.error("Failed to load proxy tools", e);
    }
  };

  useEffect(() => {
    if (activeSubView === 'telemetry') {
      fetchTelemetry();
    } else if (activeSubView === 'credentials') {
      fetchTokens();
    } else if (activeSubView === 'explorer' && explorerMode === 'resources') {
      fetchResourcesAndPrompts();
    } else if (activeSubView === 'sandbox') {
      fetchProxyTools();
    }
  }, [activeSubView, explorerMode, telemetryFilter]);

  // Auto-refresh telemetry interval
  useEffect(() => {
    let interval = null;
    if (activeSubView === 'telemetry' && autoRefreshTelemetry) {
      interval = setInterval(fetchTelemetry, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeSubView, autoRefreshTelemetry, telemetryFilter]);

  const toolsList = [
    {
      id: 'context_trust_get_trusted_context',
      num: '01',
      name: 'get_trusted_context',
      category: 'RAG RETRIEVAL',
      desc: 'Retrieve evidence-backed context before an agent acts.'
    },
    {
      id: 'context_trust_evaluate_decision',
      num: '02',
      name: 'evaluate_decision',
      category: 'DECISION GATE',
      desc: 'Evaluate actions against policy and authority.'
    },
    {
      id: 'context_trust_search_claims',
      num: '03',
      name: 'search_claims',
      category: 'KNOWLEDGE GRAPH',
      desc: 'Search atomic claims with predicate matching.'
    },
    {
      id: 'context_trust_check_conflicts',
      num: '04',
      name: 'check_conflicts',
      category: 'CONFLICT ANALYSIS',
      desc: 'Detect contradictions across enterprise policies.'
    },
    {
      id: 'context_trust_get_lineage',
      num: '05',
      name: 'get_lineage',
      category: 'PROVENANCE',
      desc: 'Trace source lineage and downstream impact.'
    },
    {
      id: 'context_trust_steward_audit',
      num: '06',
      name: 'steward_audit',
      category: 'CONTEXT CURATOR',
      desc: 'Scan stale policies and trust gaps.'
    },
    {
      id: 'context_trust_intercept_tool_call',
      num: '07',
      name: 'intercept_tool_call',
      category: 'TOOL GUARDRAIL',
      desc: 'Inspect arguments before execution.'
    }
  ];

  const handleExecuteMcp = async () => {
    setInvoking(true);
    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    let args = { organization_id: orgId };

    if (selectedTool === 'context_trust_get_trusted_context') {
      args = { ...args, query: toolQuery, min_trust_score: Number(minTrustScore), max_results: Number(maxResults) };
    } else if (selectedTool === 'context_trust_evaluate_decision') {
      args = { ...args, action_type: actionType, actor_id: actorId, actor_role: actorRole };
    } else if (selectedTool === 'context_trust_search_claims') {
      args = { ...args, search_text: searchText, status: 'all', limit: 5 };
    } else if (selectedTool === 'context_trust_check_conflicts') {
      args = { ...args, claim_text: claimText };
    } else if (selectedTool === 'context_trust_intercept_tool_call') {
      args = { ...args, tool_name: 'execute_sql', arguments: { query: 'SELECT * FROM users;' }, actor_id: actorId, actor_role: actorRole };
    }

    try {
      const res = await fetch('/v1/mcp/invoke', {
        method: 'POST',
        headers: getStudioAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          tool: selectedTool,
          arguments: args,
          client_type: 'MCP Studio',
          actor_id: actorId,
          actor_role: actorRole
        })
      });

      if (res.ok) {
        const data = await res.json();
        setInvocationResult(data);
        showToast?.(`MCP tool '${selectedTool}' executed (${data.latency_ms || 35}ms)!`);
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast?.(errData.detail || `MCP request failed (${res.status})`, "error");
      }
    } catch (e) {
      showToast?.(`MCP error: ${e.message}`, "error");
    } finally {
      setInvoking(false);
    }
  };

  const handleReadResource = async (uri) => {
    setIsLoadingResource(true);
    setSelectedResourceUri(uri);
    try {
      const res = await fetch(`/v1/mcp/resources/read?uri=${encodeURIComponent(uri)}`, {
        headers: getStudioAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setResourceContent(data);
        showToast?.(`Read resource: ${uri}`);
      }
    } catch (e) {
      showToast?.(`Failed to read resource: ${e.message}`, "error");
    } finally {
      setIsLoadingResource(false);
    }
  };

  const handleHydratePrompt = async () => {
    setIsHydratingPrompt(true);
    try {
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(promptArgs);
      } catch (err) {
        showToast?.("Invalid JSON arguments", "error");
        setIsHydratingPrompt(false);
        return;
      }

      const res = await fetch(`/v1/mcp/prompts/${selectedPromptName}`, {
        method: 'POST',
        headers: getStudioAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(parsedArgs)
      });
      if (res.ok) {
        const data = await res.json();
        setHydratedPrompt(data);
        showToast?.(`Hydrated prompt: ${selectedPromptName}`);
      }
    } catch (e) {
      showToast?.(`Prompt error: ${e.message}`, "error");
    } finally {
      setIsHydratingPrompt(false);
    }
  };

  const handleCreateToken = async (e) => {
    e.preventDefault();
    if (!newTokenName || !newTokenAgentId) return;
    setIsCreatingToken(true);
    try {
      const res = await fetch('/v1/mcp/tokens', {
        method: 'POST',
        headers: getStudioAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          name: newTokenName,
          agent_id: newTokenAgentId,
          role: newTokenRole,
          allowed_tools: newTokenTools,
          rate_limit_rpm: Number(newTokenRpm),
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111'
        })
      });
      if (res.ok) {
        const created = await res.json();
        setAgentTokens(prev => [created, ...prev]);
        setShowCreateTokenModal(false);
        setNewTokenName('');
        setNewTokenAgentId('');
        showToast?.("API Token created!");
      }
    } catch (e) {
      showToast?.(`Failed to create token: ${e.message}`, "error");
    } finally {
      setIsCreatingToken(false);
    }
  };

  const handleRevokeToken = async (tokenId) => {
    try {
      const res = await fetch(`/v1/mcp/tokens/${tokenId}`, {
        method: 'DELETE',
        headers: getStudioAuthHeaders(),
      });
      if (res.ok) {
        setAgentTokens(prev => prev.map(t => t.id === tokenId ? { ...t, status: 'revoked' } : t));
        showToast?.("Token revoked");
      }
    } catch (e) {
      showToast?.(`Failed to revoke token: ${e.message}`, "error");
    }
  };

  const handleExecuteProxyTool = async () => {
    if (!selectedProxyTool) return;
    setIsExecutingProxy(true);
    try {
      let parsedArgs = JSON.parse(proxyToolArgs);
      const res = await fetch('/v1/mcp/proxies/execute', {
        method: 'POST',
        headers: getStudioAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          tool_id: selectedProxyTool.id,
          arguments: parsedArgs,
          actor_id: 'autonomous-proxy-agent',
          actor_role: proxyActorRole
        })
      });
      if (res.ok) {
        const data = await res.json();
        setProxyResult(data);
        showToast?.(`Proxy tool evaluated: ${data.guardrail_verdict}`);
      }
    } catch (e) {
      showToast?.(`Proxy error: ${e.message}`, "error");
    } finally {
      setIsExecutingProxy(false);
    }
  };

  const getClientConfigCode = () => {
    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    if (activeSnippet === 'claude') {
      return JSON.stringify({
        mcpServers: {
          "context-trust-layer": {
            command: "python",
            args: ["-m", "app.mcp.client_stdio"],
            env: {
              CONTEXT_LAYER_API_URL: "http://127.0.0.1:8000/v1/mcp",
              CONTEXT_LAYER_ORG_ID: orgId
            }
          }
        }
      }, null, 2);
    } else if (activeSnippet === 'cursor') {
      return JSON.stringify({
        mcpServers: {
          "context-trust-layer": {
            url: "http://127.0.0.1:8000/v1/mcp",
            headers: { "X-Organization-Id": orgId }
          }
        }
      }, null, 2);
    } else if (activeSnippet === 'sse') {
      return JSON.stringify({
        mcpServers: {
          "context-trust-layer-sse": {
            url: "http://127.0.0.1:8000/v1/mcp/sse",
            transport: "sse",
            headers: {
              "X-Organization-Id": orgId,
              "Authorization": "Bearer trulin_mcp_secops_live_9a8b7c"
            }
          }
        }
      }, null, 2);
    }
    return `curl -X POST http://127.0.0.1:8000/v1/mcp \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer trulin_mcp_claude_live_9a8b7c6d5e4f" \\
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_trusted_context", "arguments": {"query": "refund policy", "organization_id": "${orgId}"}}, "id": 1}'`;
  };

  const subViewsList = [
    { id: 'overview', kicker: 'START', title: 'Overview & Quickstart', icon: <Compass size={15} /> },
    { id: 'explorer', kicker: 'EXPLORE', title: 'Tool & Resource Explorer', icon: <Terminal size={15} /> },
    { id: 'credentials', kicker: 'CONNECT', title: 'Credentials & Client Setup', icon: <KeyRound size={15} /> },
    { id: 'telemetry', kicker: 'MONITOR', title: 'Telemetry & Audit', icon: <Activity size={15} /> },
    { id: 'sandbox', kicker: 'SANDBOX', title: 'Sandbox & Proxies', icon: <ShieldAlert size={15} />, badge: 'Simulated' },
  ];

  const currentWorkspaceInfo = subViewsList.find(s => s.id === activeSubView) || subViewsList[0];

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 2. SUB-NAVIGATION STRIP (5 Clean Enterprise Tabs) */}
      <div className="mcp-subnav-strip" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        {subViewsList.map((tab) => {
          const isActive = activeSubView === tab.id;
          return (
            <div
              key={tab.id}
              className={`mcp-subnav-tab ${isActive ? 'active' : 'inactive'}`}
              onClick={() => handleSelectSubView(tab.id)}
              style={{ flex: '1 1 170px' }}
            >
              <div className="mcp-tab-icon-badge" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: isActive ? '#EA580C' : '#64748B' }}>
                {tab.icon}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.6rem', fontWeight: 800, color: isActive ? '#EA580C' : '#94A3B8', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                    {tab.kicker}
                  </span>
                  {tab.badge && (
                    <span style={{ fontSize: '0.58rem', fontWeight: 700, color: '#9A3412', background: '#FFEDD5', padding: '1px 5px', borderRadius: '4px' }}>
                      {tab.badge}
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '0.77rem', fontWeight: isActive ? 700 : 600, color: isActive ? '#0F172A' : '#475569', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {tab.title}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. WORKSPACE TITLE HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginTop: '2px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div style={{ fontSize: '0.66rem', fontWeight: 800, color: '#EA580C', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            MCP & AGENT HUB
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ color: '#EA580C', display: 'inline-flex', alignItems: 'center' }}>{currentWorkspaceInfo.icon}</span>
            <span>{currentWorkspaceInfo.title}</span>
          </h2>
        </div>

        {onOpenDocs && (
          <button
            type="button"
            onClick={() => onOpenDocs('mcp-architecture')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #E2E8F0',
              background: '#FFFFFF',
              color: '#334155',
              fontSize: '0.76rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <BookOpen size={14} color="#EA580C" />
            <span>MCP Docs & Reference</span>
          </button>
        )}
      </div>

      {/* 4. WORKSPACE CONTENT AREAS */}

      {/* ------------------------------------------------------------- */}
      {/* OVERVIEW & QUICKSTART                                         */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'overview' && (
        <div className="mcp-view-animated" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* 3-Step Quickstart Strip */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#EA580C', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '6px' }}>
              3-Step Integration Quickstart
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F172A', margin: '0 0 14px 0' }}>
              Connect external agents to Trulin’s governed policy context
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
              {[
                {
                  step: '01',
                  title: 'Issue a Scoped Agent Token',
                  desc: 'Create a bearer token bound to your organization, workspace subtree, and allowed MCP tools.',
                  action: 'Open Credentials',
                  target: 'credentials'
                },
                {
                  step: '02',
                  title: 'Connect Client or Stdio Bridge',
                  desc: 'Paste the ready-to-use config for Claude Desktop, Cursor, or backend/mcp_stdio.py.',
                  action: 'View Client Snippets',
                  target: 'credentials'
                },
                {
                  step: '03',
                  title: 'Verify Retrieval & Policy Gate',
                  desc: 'Test verified claim retrieval, advisory evaluation, and pre-execution interception.',
                  action: 'Open Tool Explorer',
                  target: 'explorer'
                }
              ].map((card) => (
                <div key={card.step} style={{ border: '1px solid #E2E8F0', borderRadius: '12px', padding: '16px', background: '#F8FAFC', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#EA580C', marginBottom: '4px' }}>STEP {card.step}</div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>{card.title}</div>
                    <div style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.5 }}>{card.desc}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleSelectSubView(card.target)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      alignSelf: 'flex-start',
                      padding: '6px 10px',
                      borderRadius: '7px',
                      border: '1px solid #CBD5E1',
                      background: '#FFFFFF',
                      color: '#0F172A',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    <span>{card.action}</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* 3 Honest Capability Boundary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
            <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.88rem', color: '#0F172A' }}>
                  <Database size={16} color="#2563EB" />
                  <span>Context Delivery</span>
                </div>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#166534', background: '#DCFCE7', padding: '2px 8px', borderRadius: '999px' }}>Live DB</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.55, margin: 0 }}>
                Queries PostgreSQL for <code>VERIFIED</code>, 9-gate-passed claims scoped to the token’s organization and workspace folder subtree, with explicit abstention on unsupported queries.
              </p>
            </div>

            <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.88rem', color: '#0F172A' }}>
                  <ShieldCheck size={16} color="#EA580C" />
                  <span>Advisory Evaluation</span>
                </div>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#1D4ED8', background: '#DBEAFE', padding: '2px 8px', borderRadius: '999px' }}>Advisory Only</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.55, margin: 0 }}>
                Evaluates proposed agent actions and returns <code>ALLOW</code>, <code>BLOCK</code>, or <code>REQUIRE_REVIEW</code> with supported reasons and explicit <code>execution_status: "Not executed by Trulin"</code>.
              </p>
            </div>

            <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.88rem', color: '#0F172A' }}>
                  <CheckCircle2 size={16} color="#9A3412" />
                  <span>Sandbox Enforcement</span>
                </div>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#9A3412', background: '#FFEDD5', padding: '2px 8px', borderRadius: '999px' }}>Simulated</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.55, margin: 0 }}>
                Demonstrates single-use, HMAC-signed permit verification via the local sandbox gateway. Real external tool mutations (Stripe, Postgres, Slack) remain disabled.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* EXPLORER MODE SWITCHER (Tools | Resources & Prompts | Guardrail) */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'explorer' && (
        <div style={{ display: 'flex', gap: '6px', background: '#F1F5F9', padding: '4px', borderRadius: '10px', alignSelf: 'flex-start' }}>
          {[
            { id: 'tools', label: 'MCP Tools (7)' },
            { id: 'resources', label: 'Resources & Prompts' },
            { id: 'interception', label: 'Interception Guardrail' }
          ].map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setExplorerMode(m.id)}
              style={{
                padding: '6px 14px',
                borderRadius: '7px',
                border: 'none',
                background: explorerMode === m.id ? '#FFFFFF' : 'transparent',
                color: explorerMode === m.id ? '#0F172A' : '#64748B',
                fontWeight: explorerMode === m.id ? 700 : 600,
                fontSize: '0.76rem',
                cursor: 'pointer',
                boxShadow: explorerMode === m.id ? '0 1px 2px rgba(15,23,42,0.06)' : 'none'
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 01: TOOL TESTER WORKSPACE                                     */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'explorer' && explorerMode === 'tools' && (
        <div className="mcp-view-animated" style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.25fr) minmax(400px, 1fr)', gap: '20px' }}>
          {/* Left Panel: Select an Endpoint */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#FED7AA', color: '#C2410C', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 800 }}>
                  01
                </span>
                <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>Select an endpoint</strong>
              </div>
              <span style={{ fontSize: '0.7rem', color: '#94A3B8', fontWeight: 600 }}>7 available</span>
            </div>

            {/* Endpoints 2-Col Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {toolsList.map((t) => {
                const isSelected = selectedTool === t.id;
                return (
                  <div
                    key={t.id}
                    className={`mcp-endpoint-card ${isSelected ? 'active-endpoint' : ''}`}
                    onClick={() => setSelectedTool(t.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, opacity: 0.6 }}>{t.num}</span>
                      <strong style={{ fontSize: '0.8rem', letterSpacing: '-0.01em' }}>{t.name}</strong>
                    </div>
                    <span className="mcp-card-category" style={{ fontSize: '0.62rem', fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#F97316' }}>
                      {t.category}
                    </span>
                    <span className="mcp-card-desc" style={{ fontSize: '0.68rem', lineHeight: 1.3, marginTop: '2px', color: '#64748B' }}>
                      {t.desc}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Bottom Select / Action Bar */}
            <div style={{ marginTop: 'auto', paddingTop: '14px', borderTop: '1px solid #F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase' }}>SELECTED ENDPOINT</span>
                <code style={{ fontSize: '0.78rem', color: '#0F172A', fontWeight: 700 }}>{selectedTool}</code>
              </div>
              <button
                type="button"
                className="btn-mcp-orange"
                onClick={handleExecuteMcp}
                disabled={invoking}
                style={{ padding: '10px 22px', fontSize: '0.82rem' }}
              >
                {invoking ? "Running..." : "Run endpoint"}
              </button>
            </div>
          </div>

          {/* Right Panel: Dark Terminal Response */}
          <div className="mcp-dark-terminal">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #27272A', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.9rem', color: '#F97316' }}>&gt;_</span>
                <strong style={{ fontSize: '0.8rem', color: '#FFFFFF' }}>Gateway response</strong>
                <span style={{ fontSize: '0.68rem', color: '#10B981', fontWeight: 600, background: 'rgba(16,185,129,0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                  JSON / 200 OK
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(invocationResult, null, 2));
                  showToast?.("Response copied!");
                }}
                style={{ background: '#27272A', border: '1px solid #3F3F46', color: '#A1A1AA', borderRadius: '6px', padding: '3px 8px', fontSize: '0.68rem', cursor: 'pointer' }}
              >
                Copy
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', maxHeight: '380px', fontFamily: 'monospace', fontSize: '0.78rem', lineHeight: 1.5, color: '#FCD34D' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(invocationResult?.result || invocationResult, null, 2)}
              </pre>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #27272A', paddingTop: '8px', fontSize: '0.68rem', color: '#71717A' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
                <span>Gateway connected</span>
              </div>
              <span>45 ms</span>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 02: LIVE TELEMETRY WORKSPACE                                  */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'telemetry' && (
        <div className="mcp-view-animated" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '0.73rem' }}>
            <span style={{ background: '#DCFCE7', color: '#166534', padding: '3px 9px', borderRadius: '999px', fontWeight: 700 }}>
              Persisted Audit: user_activity_logs (PostgreSQL)
            </span>
            <span style={{ background: '#F1F5F9', color: '#475569', padding: '3px 9px', borderRadius: '999px', fontWeight: 600 }}>
              Live Stream: In-Memory Ring Buffer (300 events)
            </span>
          </div>
          {/* 4 KPI Cards with top stripes */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
            <div className="mcp-kpi-card stripe-orange">
              <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Total transactions</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px' }}>
                <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0F172A' }}>{telemetryStats.total_invocations}</span>
                <span style={{ fontSize: '0.68rem', color: '#16A34A', background: '#F0FDF4', padding: '1px 6px', borderRadius: '10px', fontWeight: 700 }}>+12%</span>
              </div>
            </div>
            <div className="mcp-kpi-card stripe-green">
              <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Allowed</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px' }}>
                <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0F172A' }}>{telemetryStats.allowed_count}</span>
                <span style={{ fontSize: '0.68rem', color: '#16A34A', background: '#F0FDF4', padding: '1px 6px', borderRadius: '10px', fontWeight: 700 }}>60%</span>
              </div>
            </div>
            <div className="mcp-kpi-card stripe-red">
              <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Blocked</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px' }}>
                <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0F172A' }}>{telemetryStats.blocked_count}</span>
                <span style={{ fontSize: '0.68rem', color: '#DC2626', background: '#FEF2F2', padding: '1px 6px', borderRadius: '10px', fontWeight: 700 }}>20%</span>
              </div>
            </div>
            <div className="mcp-kpi-card stripe-blue">
              <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Average latency</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px' }}>
                <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0F172A' }}>{telemetryStats.avg_latency_ms} ms</span>
                <span style={{ fontSize: '0.68rem', color: '#16A34A', background: '#F0FDF4', padding: '1px 6px', borderRadius: '10px', fontWeight: 700 }}>-6%</span>
              </div>
            </div>
          </div>

          {/* Table Card */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid #F1F5F9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', animation: 'liveDotPulse 1.2s infinite' }} />
                <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>Transaction stream</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <select
                  value={telemetryFilter}
                  onChange={e => setTelemetryFilter(e.target.value)}
                  style={{ padding: '5px 10px', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '0.74rem' }}
                >
                  <option value="all">All tools & clients</option>
                  <option value="Claude Desktop">Claude Desktop</option>
                  <option value="Cursor IDE">Cursor IDE</option>
                  <option value="LangChain">LangChain</option>
                  <option value="Ollama">Ollama Local</option>
                </select>
                <button
                  type="button"
                  onClick={fetchTelemetry}
                  style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '5px 10px', borderRadius: '6px', fontSize: '0.74rem', cursor: 'pointer', fontWeight: 600 }}
                >
                  Refresh
                </button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '110px 180px 140px 100px 90px 1fr 70px', padding: '10px 18px', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', fontSize: '0.7rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              <span>TIME</span>
              <span>TOOL</span>
              <span>CALLER</span>
              <span>ROLE</span>
              <span>VERDICT</span>
              <span>DETAILS</span>
              <span>LATENCY</span>
            </div>

            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {telemetryEvents.map((evt) => (
                <div
                  key={evt.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '110px 180px 140px 100px 90px 1fr 70px',
                    padding: '12px 18px',
                    borderBottom: '1px solid #F1F5F9',
                    fontSize: '0.76rem',
                    alignItems: 'center'
                  }}
                >
                  <span style={{ color: '#64748B', fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                  <strong style={{ color: '#0F172A' }}>{evt.tool_name}</strong>
                  <span style={{ color: '#64748B' }}>{evt.client_type}</span>
                  <span>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#F1F5F9', fontSize: '0.68rem', fontWeight: 600, color: '#334155' }}>
                      {evt.actor_role}
                    </span>
                  </span>
                  <span>
                    <span className={`badge ${evt.verdict === 'ALLOW' || evt.verdict === 'PERMIT' ? 'badge-allow' : evt.verdict === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.64rem' }}>
                      {evt.verdict}
                    </span>
                  </span>
                  <span style={{ color: '#475569', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {evt.response_summary || JSON.stringify(evt.arguments)}
                  </span>
                  <span style={{ color: '#64748B', fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    {evt.latency_ms} ms
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 03: AGENT TOKENS WORKSPACE                                    */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'credentials' && (
        <div className="mcp-view-animated" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.66rem', fontWeight: 800, color: '#EA580C', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                IDENTITY AND ACCESS
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '2px 0 0 0', color: '#0F172A' }}>
                Agent credentials
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.76rem', color: '#64748B' }}>
                Scoped credentials with explicit tool grants and rate limits.
              </p>
            </div>
            <button
              type="button"
              className="btn-mcp-orange"
              onClick={() => setShowCreateTokenModal(true)}
              style={{ padding: '10px 18px', fontSize: '0.8rem' }}
            >
              Create API token
            </button>
          </div>

          {/* Tokens 4-Col Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {agentTokens.map((t, idx) => (
              <div
                key={t.id}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: '#94A3B8', fontWeight: 700 }}>0{idx + 1}</span>
                    <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>{t.name}</strong>
                  </div>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 6px', textTransform: 'uppercase' }}>
                    {t.status}
                  </span>
                </div>

                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '6px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem', fontFamily: 'monospace' }}>
                  <span style={{ color: '#475569' }}>trulin_mcp_••••••••••••</span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(t.token);
                      setCopiedTokenId(t.id);
                      showToast?.("Token copied!");
                      setTimeout(() => setCopiedTokenId(null), 2000);
                    }}
                    style={{ background: 'transparent', border: 'none', color: '#F97316', fontWeight: 700, cursor: 'pointer', fontSize: '0.7rem' }}
                  >
                    {copiedTokenId === t.id ? "Copied" : "Copy"}
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.7rem', color: '#64748B' }}>
                  <div>AGENT ID: <strong style={{ color: '#0F172A' }}>{t.agent_id}</strong></div>
                  <div>ROLE: <strong style={{ color: '#0F172A' }}>{t.role}</strong></div>
                  <div>RATE LIMIT: <strong style={{ color: '#0F172A' }}>{t.rate_limit_rpm} req/min</strong></div>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    ALLOWED TOOLS: <strong style={{ color: '#0F172A' }}>{t.allowed_tools.join(', ')}</strong>
                  </div>
                </div>

                <div style={{ marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid #F1F5F9' }}>
                  <button
                    type="button"
                    onClick={() => handleRevokeToken(t.id)}
                    style={{ background: 'transparent', border: 'none', color: '#DC2626', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                  >
                    Revoke access
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Modal */}
          {showCreateTokenModal && (
            <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
              <div style={{ background: '#FFFFFF', borderRadius: '14px', width: '460px', padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>Issue Agent API Token</h3>
                <div>
                  <label style={{ fontSize: '0.74rem', fontWeight: 600, color: '#64748B' }}>Token Label</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Autonomous Financial Reconciler"
                    value={newTokenName}
                    onChange={e => setNewTokenName(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', fontSize: '0.82rem', marginTop: '4px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.74rem', fontWeight: 600, color: '#64748B' }}>Agent ID</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. billing-agent-02"
                    value={newTokenAgentId}
                    onChange={e => setNewTokenAgentId(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', fontSize: '0.82rem', marginTop: '4px' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '0.74rem', fontWeight: 600, color: '#64748B' }}>Role</label>
                    <select
                      className="input-field"
                      value={newTokenRole}
                      onChange={e => setNewTokenRole(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', fontSize: '0.82rem', marginTop: '4px' }}
                    >
                      <option value="developer">Developer</option>
                      <option value="secops">SecOps</option>
                      <option value="finance">Finance</option>
                      <option value="support">Support</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '0.74rem', fontWeight: 600, color: '#64748B' }}>Rate Limit (RPM)</label>
                    <input
                      type="number"
                      className="input-field"
                      value={newTokenRpm}
                      onChange={e => setNewTokenRpm(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', fontSize: '0.82rem', marginTop: '4px' }}
                    />
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowCreateTokenModal(false)}>Cancel</button>
                  <button type="button" className="btn-mcp-orange" onClick={handleCreateToken} disabled={isCreatingToken} style={{ padding: '8px 16px' }}>
                    {isCreatingToken ? "Generating..." : "Generate Token"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 04: RESOURCES & PROMPTS WORKSPACE                             */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'explorer' && explorerMode === 'resources' && (
        <div className="mcp-view-animated" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Left: A MCP Resources */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#FED7AA', color: '#C2410C', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 800 }}>A</span>
                <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>MCP resources</strong>
              </div>
              <code style={{ fontSize: '0.7rem', color: '#94A3B8' }}>context://</code>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {mcpResources.map((res) => {
                const isSelected = selectedResourceUri === res.uri;
                return (
                  <div
                    key={res.uri}
                    onClick={() => setSelectedResourceUri(res.uri)}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '8px',
                      border: `1.5px solid ${isSelected ? '#F97316' : '#E2E8F0'}`,
                      background: isSelected ? '#FFF7ED' : '#F8FAFC',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <strong style={{ fontSize: '0.82rem', color: '#0F172A' }}>{res.name}</strong>
                      <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Read-only verified context with authority metadata.</span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReadResource(res.uri);
                      }}
                      style={{ background: 'transparent', border: 'none', color: '#64748B', fontSize: '0.68rem', cursor: 'pointer' }}
                    >
                      Read URI
                    </button>
                  </div>
                );
              })}
            </div>

            {resourceContent && (
              <div style={{ background: '#18181B', color: '#FCD34D', padding: '12px', borderRadius: '8px', maxHeight: '180px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.72rem' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{resourceContent.text}</pre>
              </div>
            )}
          </div>

          {/* Right: B Governed Prompts */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#FED7AA', color: '#C2410C', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 800 }}>B</span>
                <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>Governed prompts</strong>
              </div>
              <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>4 templates</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {mcpPrompts.map((p) => {
                const isSelected = selectedPromptName === p.name;
                return (
                  <div
                    key={p.name}
                    onClick={() => setSelectedPromptName(p.name)}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: `1.5px solid ${isSelected ? '#F97316' : '#E2E8F0'}`,
                      background: isSelected ? '#FFF7ED' : '#F8FAFC',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '2px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <strong style={{ fontSize: '0.82rem', color: '#0F172A' }}>{p.name}</strong>
                    <span style={{ fontSize: '0.68rem', color: '#64748B' }}>Policy-aware prompt with audit controls.</span>
                  </div>
                );
              })}
            </div>

            <div>
              <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 600 }}>Input arguments</span>
              <textarea
                className="input-field"
                rows={3}
                value={promptArgs}
                onChange={e => setPromptArgs(e.target.value)}
                style={{ width: '100%', padding: '8px', fontSize: '0.76rem', fontFamily: 'monospace', marginTop: '4px' }}
              />
              <button
                type="button"
                className="btn-mcp-orange"
                onClick={handleHydratePrompt}
                disabled={isHydratingPrompt}
                style={{ width: '100%', padding: '10px', fontSize: '0.82rem', marginTop: '10px' }}
              >
                {isHydratingPrompt ? "Hydrating..." : "Hydrate prompt"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 05: THIRD-PARTY PROXIES WORKSPACE                             */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'sandbox' && (
        <div className="mcp-view-animated" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ background: '#FFF7ED', border: '1px solid #FED7AA', borderRadius: '10px', padding: '10px 14px', fontSize: '0.78rem', color: '#9A3412', fontWeight: 600 }}>
            Simulated Sandbox: 3rd-party proxy tools (PostgreSQL, Stripe, GitHub, Slack) return simulated responses after policy interception. Real external mutations are disabled.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
          {/* Left Panel: 01 External tools */}
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#FED7AA', color: '#C2410C', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 800 }}>01</span>
                <strong style={{ fontSize: '0.84rem', color: '#0F172A' }}>External tools</strong>
              </div>
              <span style={{ fontSize: '0.66rem', color: '#16A34A', background: '#F0FDF4', padding: '2px 8px', borderRadius: '6px', fontWeight: 700 }}>
                INTERCEPTION ACTIVE
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {proxyTools.map((pt) => {
                const isSelected = selectedProxyTool?.id === pt.id;
                return (
                  <div
                    key={pt.id}
                    onClick={() => {
                      setSelectedProxyTool(pt);
                      setProxyToolArgs(JSON.stringify(pt.sample_args || {}, null, 2));
                      setProxyActorRole(pt.default_role || 'developer');
                    }}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: `1.5px solid ${isSelected ? '#F97316' : '#E2E8F0'}`,
                      background: isSelected ? '#FFF7ED' : '#F8FAFC',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '1.1rem' }}>{pt.icon}</span>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <strong style={{ fontSize: '0.78rem', color: '#0F172A' }}>{pt.name}</strong>
                        <span style={{ fontSize: '0.64rem', color: '#64748B' }}>{pt.provider}</span>
                      </div>
                    </div>
                    <span style={{ fontSize: '0.58rem', fontWeight: 800, padding: '1px 5px', borderRadius: '4px', background: pt.risk_level === 'CRITICAL' ? '#FEF2F2' : '#FFFBEB', color: pt.risk_level === 'CRITICAL' ? '#DC2626' : '#D97706' }}>
                      {pt.risk_level}
                    </span>
                  </div>
                );
              })}
            </div>

            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 600, color: '#64748B' }}>Actor role</label>
              <select
                className="input-field"
                value={proxyActorRole}
                onChange={e => setProxyActorRole(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.8rem', marginTop: '3px' }}
              >
                <option value="developer">Developer</option>
                <option value="finance">Finance</option>
                <option value="support">Support</option>
                <option value="secops">SecOps</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 600, color: '#64748B' }}>Tool payload</label>
              <textarea
                className="input-field"
                rows={3}
                value={proxyToolArgs}
                onChange={e => setProxyToolArgs(e.target.value)}
                style={{ width: '100%', padding: '8px', fontSize: '0.76rem', fontFamily: 'monospace', marginTop: '3px' }}
              />
            </div>

            <button
              type="button"
              className="btn-mcp-orange"
              onClick={handleExecuteProxyTool}
              disabled={isExecutingProxy}
              style={{ width: '100%', padding: '10px', fontSize: '0.82rem', marginTop: '6px' }}
            >
              {isExecutingProxy ? "Evaluating..." : "Execute through proxy"}
            </button>
          </div>

          {/* Right Panel: Dark Guardrail Ledger */}
          <div className="mcp-dark-terminal">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #27272A', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.9rem', color: '#F97316' }}>&gt;_</span>
                <strong style={{ fontSize: '0.8rem', color: '#FFFFFF' }}>Guardrail ledger</strong>
                <span style={{ fontSize: '0.68rem', color: '#10B981', background: 'rgba(16,185,129,0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                  JSON / 200 OK
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(proxyResult, null, 2));
                  showToast?.("Ledger copied!");
                }}
                style={{ background: '#27272A', border: '1px solid #3F3F46', color: '#A1A1AA', borderRadius: '6px', padding: '3px 8px', fontSize: '0.68rem', cursor: 'pointer' }}
              >
                Copy
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', maxHeight: '380px', fontFamily: 'monospace', fontSize: '0.78rem', lineHeight: 1.5, color: '#FCD34D' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(proxyResult, null, 2)}
              </pre>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #27272A', paddingTop: '8px', fontSize: '0.68rem', color: '#71717A' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
                <span>Gateway connected</span>
              </div>
              <span>450 ms</span>
            </div>
          </div>
        </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 06: INTERCEPTION GUARDRAIL WORKSPACE                          */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'explorer' && explorerMode === 'interception' && (
        <div className="mcp-view-animated" style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '20px' }}>
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#0F172A' }}>
              Pre-Execution Tool Guardrail Simulator
            </h3>
            <div>
              <label style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748B' }}>Proposed Tool Name</label>
              <input
                type="text"
                className="input-field"
                value={interceptToolName}
                onChange={e => setInterceptToolName(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.8rem', marginTop: '3px' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748B' }}>Agent Entitled Role</label>
              <select
                className="input-field"
                value={interceptRole}
                onChange={e => setInterceptRole(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.8rem', marginTop: '3px' }}
              >
                <option value="developer">Developer</option>
                <option value="support">Support Agent</option>
                <option value="finance">Finance Lead</option>
                <option value="secops">SecOps Engineer</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748B' }}>Tool Arguments (JSON)</label>
              <textarea
                className="input-field"
                rows={4}
                value={interceptArgs}
                onChange={e => setInterceptArgs(e.target.value)}
                style={{ width: '100%', padding: '8px', fontSize: '0.76rem', fontFamily: 'monospace', marginTop: '3px' }}
              />
            </div>
            <button
              type="button"
              className="btn-mcp-orange"
              onClick={async () => {
                setIsIntercepting(true);
                try {
                  const res = await fetch('/v1/mcp/intercept-tool', {
                    method: 'POST',
                    headers: getStudioAuthHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({
                      tool_name: interceptToolName,
                      arguments: JSON.parse(interceptArgs),
                      actor_id: 'test-agent',
                      actor_role: interceptRole
                    })
                  });
                  if (res.ok) {
                    const data = await res.json();
                    setInterceptResult(data);
                    showToast?.(`Audit verdict: ${data.verdict}`);
                  }
                } catch (e) {
                  showToast?.(`Audit failed: ${e.message}`, "error");
                } finally {
                  setIsIntercepting(false);
                }
              }}
              disabled={isIntercepting}
              style={{ width: '100%', padding: '10px', fontSize: '0.82rem' }}
            >
              {isIntercepting ? "Auditing Payload..." : "Audit Tool Proposal"}
            </button>
          </div>

          <div style={{ background: '#18181B', border: '1px solid #27272A', borderRadius: '14px', padding: '20px', color: '#F8FAFC' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #27272A', paddingBottom: '10px', marginBottom: '12px' }}>
              <strong style={{ fontSize: '0.84rem', color: '#93C5FD' }}>Guardrail Verdict</strong>
              {interceptResult && (
                <span className={`badge ${interceptResult.verdict === 'PERMIT' ? 'badge-allow' : 'badge-block'}`} style={{ fontSize: '0.64rem' }}>
                  {interceptResult.verdict}
                </span>
              )}
            </div>

            {interceptResult ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '0.76rem' }}>
                  Risk Tier: <strong style={{ color: '#F97316' }}>{interceptResult.risk_tier}</strong> • Score: <strong>{interceptResult.risk_score}/100</strong>
                </div>
                {interceptResult.permit_token && (
                  <div style={{ fontSize: '0.7rem', color: '#86EFAC', fontFamily: 'monospace' }}>
                    Permit Token: {interceptResult.permit_token}
                  </div>
                )}
                {interceptResult.reasons?.map((r, i) => (
                  <div key={i} style={{ fontSize: '0.72rem', color: '#CBD5E1' }}>• {r}</div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '180px', color: '#71717A' }}>
                <span>Run tool audit to see pre-execution security checks.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 07: CONFIGS & SDKS WORKSPACE (Included under Credentials tab) */}
      {/* ------------------------------------------------------------- */}
      {activeSubView === 'credentials' && (
        <div className="mcp-view-animated" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', background: '#F1F3F5', padding: '3px', borderRadius: '8px', gap: '3px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setActiveSnippet('claude')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: activeSnippet === 'claude' ? '#FFFFFF' : 'transparent', fontWeight: 600, fontSize: '0.76rem', cursor: 'pointer' }}
              >
                Claude Desktop (stdio)
              </button>
              <button
                onClick={() => setActiveSnippet('cursor')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: activeSnippet === 'cursor' ? '#FFFFFF' : 'transparent', fontWeight: 600, fontSize: '0.76rem', cursor: 'pointer' }}
              >
                Cursor IDE (HTTP)
              </button>
              <button
                onClick={() => setActiveSnippet('sse')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: activeSnippet === 'sse' ? '#FFFFFF' : 'transparent', fontWeight: 600, fontSize: '0.76rem', cursor: 'pointer' }}
              >
                Server-Sent Events (SSE)
              </button>
            </div>

            <button
              type="button"
              className="btn-mcp-orange"
              onClick={() => {
                navigator.clipboard.writeText(getClientConfigCode());
                setCopiedSnippet(true);
                showToast?.("Configuration snippet copied!");
                setTimeout(() => setCopiedSnippet(false), 2000);
              }}
              style={{ padding: '6px 14px', fontSize: '0.76rem' }}
            >
              {copiedSnippet ? "✓ Copied!" : "Copy Configuration"}
            </button>
          </div>

          <div style={{ background: '#18181B', border: '1px solid #27272A', borderRadius: '12px', padding: '20px', color: '#FCD34D', fontFamily: 'monospace', fontSize: '0.78rem', lineHeight: 1.5, maxHeight: '450px', overflowY: 'auto' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{getClientConfigCode()}</pre>
          </div>
        </div>
      )}

    </div>
  );
}
