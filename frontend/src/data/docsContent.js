export const DOCS_CATEGORIES = [
  {
    id: 'getting-started',
    label: 'Getting Started',
    articles: [
      {
        id: 'welcome',
        title: 'Welcome to Trulin',
        readTime: '3 min read',
        summary: 'How Trulin turns unstructured enterprise policies into evidence-grounded claims for human teams and AI agents.',
        deepLink: { label: 'Open Home Overview', tab: 'home' },
        sections: [
          {
            id: 'what-is-trulin',
            heading: 'What is Trulin?',
            body: [
              'Trulin is an Enterprise Context Trust & Decision Governance platform. Instead of letting AI assistants retrieve raw, conflicting, or unverified document chunks, Trulin extracts atomic policy claims, verifies them through a 9-gate certification pipeline, and tracks provenance back to the exact source document.',
              'Verified context is delivered through two distinct, governed paths: the AI Copilot for human decision-makers, and the Model Context Protocol (MCP) Hub for external autonomous agents.'
            ],
            callout: {
              type: 'info',
              title: 'Two Delivery Paths, One Governed Source',
              text: 'Both the AI Copilot and external MCP clients read from the same verified claim ledger—candidate, rejected, and conflicted claims are never silently mixed into operative answers.'
            }
          },
          {
            id: 'architecture-flow',
            heading: 'End-to-End Governance Flow',
            body: [
              '1. Ingest: Upload policies or connect enterprise sources in Documents.',
              '2. Certify: Automated extraction + 9-Gate validation + human Curator Triage promote valid rules to VERIFIED.',
              '3. Govern: Conflicts are flagged and isolated until resolved by a curator.',
              '4. Deliver: Serve Decision Briefs to humans in AI Copilot or scoped context & advisory verdicts via MCP.'
            ]
          }
        ]
      },
      {
        id: 'quickstart',
        title: '5-Minute Quickstart',
        readTime: '4 min read',
        summary: 'Go from a fresh workspace to your first verified policy answer and authenticated MCP query.',
        deepLink: { label: 'Go to Documents', tab: 'ingestion' },
        sections: [
          {
            id: 'step-1-upload',
            heading: '1. Upload a Policy Document',
            body: [
              'Navigate to Documents and upload a PDF, DOCX, or Markdown policy into your target workspace folder. Trulin parses sections, extracts candidate claims, and attaches exact text-span evidence.'
            ]
          },
          {
            id: 'step-2-curate',
            heading: '2. Certify Claims in Curator Triage',
            body: [
              'Open Curator Triage to review candidate claims. Claims passing all 9 deterministic gates appear in Ready for Batch Approval, while ambiguous or conflicting rules are held for safety review.'
            ]
          },
          {
            id: 'step-3-deliver',
            heading: '3. Query via AI Copilot or MCP',
            body: [
              'Test human-facing Decision Briefs in AI Copilot, or open MCP & Agent Hub → Credentials & Client Setup to issue an agent token and connect Claude Desktop, Cursor, or mcp_stdio.py.'
            ]
          }
        ]
      },
      {
        id: 'core-concepts',
        title: 'Core Concepts & Data Model',
        readTime: '4 min read',
        summary: 'Understand Organizations, Workspaces (Folder Subtrees), Claims, Evidence, and Conflicts.',
        deepLink: { label: 'Explore Knowledge Vault', tab: 'visual_lineage' },
        sections: [
          {
            id: 'org-workspace',
            heading: 'Organizations & Workspaces',
            body: [
              'Every organization is a strict tenant boundary. Within an organization, a workspace_id maps to a scoped Folder subtree (the target folder and its descendant folders).',
              'Tokens or sessions scoped to one workspace cannot read claims, conflicts, or lineage nodes belonging to sibling workspaces in the same organization.'
            ]
          },
          {
            id: 'claims-evidence',
            heading: 'Atomic Claims & Evidence',
            body: [
              'Each claim captures a structured subject, predicate, object, operative modal verb, and direct evidence span (document title, section, and page number).'
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'curation',
    label: 'Curation & Governance',
    articles: [
      {
        id: 'nine-gates',
        title: '9-Gate Claim Certification',
        readTime: '5 min read',
        summary: 'Deterministic quality and safety gates that every claim must pass before becoming agent-accessible.',
        deepLink: { label: 'Open Curator Triage', tab: 'context_curator' },
        sections: [
          {
            id: 'gate-overview',
            heading: 'Why 9 Gates?',
            body: [
              'Raw LLM extractions frequently capture page headers, postal addresses, compound multi-rule sentences, or descriptive prose without operative obligations. Trulin evaluates every claim deterministically across atomicity, subject validity, predicate normativity, deontic modality, and evidence span existence.'
            ],
            callout: {
              type: 'tip',
              title: 'Fail-Closed Default',
              text: 'Any claim failing a gate is marked REVIEW_REQUIRED and excluded from agent-accessible verified context until a curator resolves or edits it.'
            }
          }
        ]
      },
      {
        id: 'triage-workflow',
        title: 'Policy Rule Triage & Conflicts',
        readTime: '4 min read',
        summary: 'How curators batch-approve safe rules, inspect held items, and isolate policy contradictions.',
        deepLink: { label: 'Open Approvals Board', tab: 'context_curator' },
        sections: [
          {
            id: 'kanban-lanes',
            heading: 'Three Triage Lanes',
            body: [
              'Ready for Batch Approval: High-confidence claims passing all 9 gates.',
              'Held for Safety Review: Claims with missing conditions, unresolved pronouns, or active contradictions.',
              'Certified Rules: Operative rules actively served to AI Copilot and MCP.'
            ]
          },
          {
            id: 'conflict-isolation',
            heading: 'Both-Sides Conflict Verification',
            body: [
              'When two claims contradict (e.g., 30-day vs. 90-day refund window), Trulin records a ClaimConflict. MCP queries verify that both sides of a conflict belong to the caller’s authorized organization and workspace before surfacing it.'
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'copilot',
    label: 'AI Copilot',
    articles: [
      {
        id: 'decision-briefs',
        title: 'Decision Briefs & Depth Controls',
        readTime: '3 min read',
        summary: 'How Trulin structures human answers with Brief, Standard, and Detailed controls.',
        deepLink: { label: 'Open AI Copilot', tab: 'playground' },
        sections: [
          {
            id: 'brief-structure',
            heading: 'Anatomy of a Decision Brief',
            body: [
              'AI Copilot answers questions strictly from verified claims within the active workspace scope, preserving conditions, exceptions, conflicts, and clickable source citations.',
              'Use Brief for executive summaries, Standard for balanced operational guidance, and Detailed for full supporting evidence and conditions.'
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'mcp',
    label: 'MCP & External Agents',
    articles: [
      {
        id: 'mcp-architecture',
        title: 'MCP Architecture & Boundaries',
        readTime: '5 min read',
        summary: 'Distinguishing Context Delivery, Advisory Evaluation, and Sandbox Enforcement.',
        deepLink: { label: 'Open MCP & Agent Hub', tab: 'integrations', subView: 'overview' },
        sections: [
          {
            id: 'three-capabilities',
            heading: 'Three Distinct Capabilities',
            body: [
              '1. Context Delivery (Live DB): Retrieves verified, 9-gate-passed claims with real claim IDs, provenance, and explicit abstention when unsupported.',
              '2. Advisory Evaluation (Advisory Only): Evaluates a proposed action against policy and returns ALLOW, BLOCK, or REQUIRE_REVIEW with execution_status: "Not executed by Trulin".',
              '3. Execution Enforcement (Sandbox Only): Demonstrated via SandboxLedgerTool requiring a single-use, HMAC-signed permit token. Returning BLOCK does not prevent an external agent from calling a downstream tool directly unless that tool enforces Trulin permits.'
            ],
            callout: {
              type: 'warning',
              title: 'Security Boundary',
              text: '3rd-party proxies in the MCP Hub are simulated for guardrail verification. Real external mutations are not enabled.'
            }
          }
        ]
      },
      {
        id: 'mcp-auth',
        title: 'Authentication & Scoped Tokens',
        readTime: '4 min read',
        summary: 'How Bearer tokens, tool entitlements, and audience separation work across MCP endpoints.',
        deepLink: { label: 'Manage Agent Tokens', tab: 'integrations', subView: 'credentials' },
        sections: [
          {
            id: 'token-auth',
            heading: 'Token Authentication & Audience Separation',
            body: [
              'External MCP protocol endpoints (POST /v1/mcp, GET /v1/mcp/sse, POST /v1/mcp/messages) strictly require an active MCP Agent Token (trulin_mcp_*) via Authorization: Bearer <token> or X-MCP-Token.',
              'Organization and workspace scope are derived from the validated token—caller-supplied organization_id or workspace_id overrides in tool arguments are ignored.'
            ],
            code: {
              label: 'Authenticated JSON-RPC Request (cURL)',
              language: 'bash',
              snippet: `curl -X POST http://127.0.0.1:8000/v1/mcp \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer trulin_mcp_claude_live_9a8b7c6d5e4f" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "context_trust_get_trusted_context",
      "arguments": { "query": "refund approval limit" }
    },
    "id": 1
  }'`
            }
          },
          {
            id: 'token-lifecycle',
            heading: 'Current Token Lifecycle Note',
            body: [
              'Agent tokens are currently stored in-memory per backend worker process (with 4 pre-seeded development tokens). For multi-worker production deployments, persist tokens in a shared database or secret store.'
            ]
          }
        ]
      },
      {
        id: 'mcp-clients',
        title: 'Connecting Claude, Cursor & Stdio',
        readTime: '4 min read',
        summary: 'Step-by-step configuration for Claude Desktop, Cursor IDE, and backend/mcp_stdio.py.',
        deepLink: { label: 'Open Client Setup', tab: 'integrations', subView: 'credentials' },
        sections: [
          {
            id: 'stdio-bridge',
            heading: 'Using the Local Stdio Bridge (mcp_stdio.py)',
            body: [
              'Trulin ships a lightweight stdio-to-HTTP JSON-RPC bridge at backend/mcp_stdio.py. Set TRULIN_MCP_TOKEN and CONTEXT_LAYER_API_URL in your client environment.'
            ],
            code: {
              label: 'Claude Desktop / Cursor MCP Config',
              language: 'json',
              snippet: `{
  "mcpServers": {
    "trulin-context-trust": {
      "command": "python",
      "args": ["B:/Trulin/backend/mcp_stdio.py"],
      "env": {
        "CONTEXT_LAYER_API_URL": "http://127.0.0.1:8000/v1/mcp",
        "TRULIN_MCP_TOKEN": "trulin_mcp_claude_live_9a8b7c6d5e4f"
      }
    }
  }
}`
            }
          }
        ]
      },
      {
        id: 'mcp-reference',
        title: 'MCP Tools & Resources Reference',
        readTime: 'Reference',
        summary: 'Live parameter schemas and descriptions loaded directly from Trulin’s MCP server.',
        deepLink: { label: 'Open Tool Explorer', tab: 'integrations', subView: 'explorer' },
        renderLiveMcpSchema: true,
        sections: [
          {
            id: 'live-tools',
            heading: 'Registered MCP Tools',
            body: [
              'All tools below are registered on POST /v1/mcp and POST /v1/mcp/invoke and enforce token-derived organization and workspace isolation.'
            ]
          },
          {
            id: 'live-resources',
            heading: 'Read-Only Context Resources',
            body: [
              'Resources expose scoped snapshots of verified claims, active documents, and unresolved contradictions.'
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'security',
    label: 'Security & Audit',
    articles: [
      {
        id: 'audit-compliance',
        title: 'Audit Events & Telemetry',
        readTime: '3 min read',
        summary: 'How Trulin persists MCP audit events and distinguishes them from in-memory telemetry.',
        deepLink: { label: 'Open Audit Log', tab: 'audit' },
        sections: [
          {
            id: 'persisted-vs-memory',
            heading: 'Persisted Audit vs. In-Memory Telemetry',
            body: [
              'MCP tool invocations are persisted to PostgreSQL (user_activity_logs) as audit events intended to support compliance review.',
              'The Live Telemetry waterfall in MCP & Agent Hub reads from an in-memory ring buffer (300 events) for real-time inspection and resets on server restart. Raw bearer tokens and HMAC signing secrets are never logged.'
            ]
          }
        ]
      }
    ]
  }
];
