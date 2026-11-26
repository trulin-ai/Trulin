import decimal
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus
from app.db.models.agent import Agent
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.db.models.user_activity import UserActivityLog
from app.decision_engine.evaluator import DecisionEvaluator
from app.schemas.context import ContextQueryRequest
from app.schemas.decision import DecisionActor, DecisionContextItem, DecisionEvaluateRequest
from app.retrieval.engine import ContextRetrievalEngine
from app.services.claim_gate_evaluator import ClaimGateEvaluator


MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_NAME = "context-trust-layer"
MCP_SERVER_VERSION = "0.2.0"

# -------------------------------------------------------------
# MCP Resources Definitions (Read-only Context Data Streams)
# -------------------------------------------------------------
MCP_RESOURCES = [
    {
        "uri": "context://claims/verified",
        "name": "Verified Atomic Claims",
        "description": "Live stream of verified, high-trust enterprise policy statements and authority scores.",
        "mimeType": "application/json"
    },
    {
        "uri": "context://documents/active",
        "name": "Active Ingested Documents",
        "description": "Catalog of all synchronized enterprise sources (Slack, Notion, Confluence, G-Drive) and metadata.",
        "mimeType": "application/json"
    },
    {
        "uri": "context://contradictions/active",
        "name": "Active Policy Contradictions",
        "description": "Real-time ledger of cross-source policy disputes and contradiction alerts requiring data steward reconciliation.",
        "mimeType": "application/json"
    },
    {
        "uri": "context://audit/health",
        "name": "Context Decay & Health Audit",
        "description": "Tenant governance health, decay curve distribution, and trust index breakdown.",
        "mimeType": "application/json"
    },
    {
        "uri": "context://policies/active",
        "name": "Core Enterprise Governance Baseline",
        "description": "High-authority enterprise baseline standards for finance, SecOps, HR, and customer support.",
        "mimeType": "application/json"
    }
]

MCP_RESOURCE_TEMPLATES = [
    {
        "uriTemplate": "context://claims/{claim_id}",
        "name": "Specific Claim Lineage & Evidence",
        "description": "Fetches a single atomic claim along with its evidence chain, validity decay status, and trust score history.",
        "mimeType": "application/json"
    },
    {
        "uriTemplate": "context://documents/{document_id}",
        "name": "Document Claims Extracted",
        "description": "Fetches all atomic claims and extracted lineage for a specific source document ID.",
        "mimeType": "application/json"
    }
]

# -------------------------------------------------------------
# MCP Prompts Definitions (Pre-Engineered Governed System Prompts)
# -------------------------------------------------------------
MCP_PROMPTS = [
    {
        "name": "governed_financial_decision",
        "description": "Pre-execution financial decision prompt enforcing SOX approval thresholds, dispute limits, and role entitlements.",
        "arguments": [
            {
                "name": "action_description",
                "description": "The financial action or refund to evaluate (e.g. 'Issue $5,000 goodwill credit to account')",
                "required": True
            },
            {
                "name": "amount_usd",
                "description": "Dollar transaction amount",
                "required": False
            }
        ]
    },
    {
        "name": "sox_compliance_audit",
        "description": "Segregation-of-duties review prompt ensuring hotfixes, access grants, and ledger changes maintain four-eyes validation.",
        "arguments": [
            {
                "name": "system_name",
                "description": "Core service or ledger target name",
                "required": True
            }
        ]
    },
    {
        "name": "zero_trust_retrieval",
        "description": "Context grounding prompt requiring strict citation of high-trust verified claims with decay curve validation.",
        "arguments": [
            {
                "name": "inquiry",
                "description": "The enterprise topic or policy question",
                "required": True
            }
        ]
    },
    {
        "name": "secops_ingress_approval",
        "description": "Zero-trust network policy evaluation prompt checking production firewall rules against SecOps cryptographic key rotation rules.",
        "arguments": [
            {
                "name": "service_name",
                "description": "Target production service name",
                "required": True
            },
            {
                "name": "port",
                "description": "Target port or protocol",
                "required": True
            }
        ]
    }
]

# -------------------------------------------------------------
# MCP Tool Definitions (JSON Schema conforming to MCP Spec)
# -------------------------------------------------------------
MCP_TOOLS = [
    {
        "name": "context_trust_get_trusted_context",
        "description": "Retrieves evidence-backed, verified, and conflict-resolved context from the enterprise Context Trust Layer before an AI agent makes a decision or takes an action.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The natural language question, topic, or policy inquiry the agent needs trusted context for."
                },
                "organization_id": {
                    "type": "string",
                    "description": "The enterprise tenant organization ID (default: 11111111-1111-1111-1111-111111111111 for demo)."
                },
                "agent_id": {
                    "type": "string",
                    "description": "The unique identifier or name of the calling AI agent."
                },
                "min_trust_score": {
                    "type": "number",
                    "description": "Minimum acceptable trust threshold between 0.0 and 1.0 (default: 0.75).",
                    "default": 0.75
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of verified context items to return (default: 5).",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "context_trust_evaluate_decision",
        "description": "Evaluates an AI agent's proposed action against enterprise governance rules, authority hierarchy, and active policy contradictions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "The category or statement of the intended action (e.g., 'Determine whether customer is eligible for 45-day refund')."
                },
                "actor_id": {
                    "type": "string",
                    "description": "Identifier of the actor or agent proposing the action."
                },
                "actor_role": {
                    "type": "string",
                    "description": "Role of the actor (e.g., 'support', 'finance', 'developer', 'hr')."
                },
                "candidate_claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "source": {"type": "string"},
                            "updated_at": {"type": "string"},
                            "authority_level": {"type": "integer"},
                            "scope": {"type": "string"}
                        }
                    },
                    "description": "Optional list of candidate context items retrieved by the agent."
                },
                "required_scope": {
                    "type": "string",
                    "description": "Target scope or tier (e.g., 'Enterprise', 'US', 'General')."
                }
            },
            "required": ["action_type", "actor_id"]
        }
    },
    {
        "name": "context_trust_search_claims",
        "description": "Searches the atomic claim database for verified facts, policy boundaries, and authority levels within a specific department workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": "Keywords or predicate to search across enterprise claims."
                },
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                },
                "status": {
                    "type": "string",
                    "description": "Filter by claim status: 'verified', 'active', 'outdated', or 'all'.",
                    "default": "verified"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of claims to return (default: 10).",
                    "default": 10
                }
            },
            "required": ["search_text"]
        }
    },
    {
        "name": "context_trust_check_conflicts",
        "description": "Checks whether a proposed statement or extracted claim directly contradicts existing authoritative knowledge or superseded policies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_text": {
                    "type": "string",
                    "description": "The statement to check for contradictions against stored policies."
                },
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                }
            },
            "required": ["claim_text"]
        }
    },
    {
        "name": "context_trust_get_lineage",
        "description": "Retrieves the end-to-end DAG lineage and blast radius for a claim, document, or tenant context graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID."
                },
                "claim_id": {
                    "type": "string",
                    "description": "Optional specific claim ID to compute blast radius and downstream impacts."
                }
            }
        }
    },
    {
        "name": "context_trust_steward_audit",
        "description": "Runs an autonomous AI Data Steward audit scan detecting stale policies, active contradictions, and context health metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                }
            }
        }
    },
    {
        "name": "context_trust_intercept_tool_call",
        "description": "Pre-execution security middleware that evaluates external agent tool calls before invocation. Checks risk tier, SQL/shell injection, financial limits, and role entitlements. Returns PERMIT with cryptographic permit token or BLOCKS rogue execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The name of the tool the agent plans to invoke, e.g. 'execute_sql', 'send_payment'."
                },
                "arguments": {
                    "type": "object",
                    "description": "The planned arguments/payload passed to the tool."
                },
                "actor_id": {
                    "type": "string",
                    "description": "The agent executing the tool."
                },
                "actor_role": {
                    "type": "string",
                    "description": "Role of the agent (e.g. 'support', 'developer', 'finance', 'admin')."
                },
                "justification": {
                    "type": "string",
                    "description": "Optional explanation of why the agent is invoking this tool."
                }
            },
            "required": ["tool_name"]
        }
    }
]


DEFAULT_DEMO_ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _resolve_org_uuid(args: Dict[str, Any]) -> uuid.UUID:
    """Derives organization UUID from authenticated token context first, then arguments."""
    org_id_str = args.get("_auth_organization_id") or args.get("organization_id") or str(DEFAULT_DEMO_ORG_ID)
    try:
        return uuid.UUID(str(org_id_str))
    except Exception:
        return DEFAULT_DEMO_ORG_ID


def _resolve_workspace_uuid(args: Dict[str, Any]) -> Optional[uuid.UUID]:
    ws_id_str = args.get("_auth_workspace_id") or args.get("workspace_id")
    if not ws_id_str or str(ws_id_str).lower() == "all":
        return None
    try:
        return uuid.UUID(str(ws_id_str))
    except Exception:
        return None


async def _resolve_workspace_folder_ids(
    session: AsyncSession,
    org_id: uuid.UUID,
    ws_id: Optional[uuid.UUID],
) -> Optional[set[uuid.UUID]]:
    """
    In Trulin's current schema, workspace_id maps to a Folder subtree (folders.id
    plus any descendant folders within the same organization). Returns None when
    no workspace filter is active.
    """
    if ws_id is None:
        return None
    res = await session.execute(
        select(Folder.id, Folder.parent_id).where(Folder.organization_id == org_id)
    )
    rows = res.all()
    children_map: Dict[Optional[uuid.UUID], List[uuid.UUID]] = {}
    all_ids: set[uuid.UUID] = set()
    for fid, pid in rows:
        all_ids.add(fid)
        children_map.setdefault(pid, []).append(fid)

    if ws_id not in all_ids:
        return {ws_id}

    allowed: set[uuid.UUID] = set()
    queue = [ws_id]
    while queue:
        curr = queue.pop(0)
        if curr in allowed:
            continue
        allowed.add(curr)
        queue.extend(children_map.get(curr, []))
    return allowed


def _claim_in_scope(
    claim: Optional[Claim],
    org_id: uuid.UUID,
    allowed_folder_ids: Optional[set[uuid.UUID]],
) -> bool:
    if not claim or claim.organization_id != org_id:
        return False
    if allowed_folder_ids is None:
        return True
    for ev in (claim.evidence or []):
        if ev.document and ev.document.folder_id in allowed_folder_ids:
            return True
    return False


async def persist_mcp_audit_event(
    session: AsyncSession,
    organization_id: uuid.UUID,
    actor_id: str,
    actor_role: str,
    action_type: str,
    target_id: str,
    target_title: str,
    details: Dict[str, Any],
) -> None:
    """Persists an MCP audit event to user_activity_logs (intended to support compliance review)."""
    try:
        async with session.begin_nested():
            org_exists = await session.execute(select(Organization.id).where(Organization.id == organization_id))
            if not org_exists.scalar_one_or_none():
                return
            log_entry = UserActivityLog(
                organization_id=organization_id,
                user_id=None,
                user_name=actor_id[:255] if actor_id else "mcp-agent",
                user_role=actor_role[:50] if actor_role else "support",
                action_type=action_type[:100],
                target_type="mcp_tool",
                target_id=target_id[:255] if target_id else None,
                target_title=target_title[:500] if target_title else None,
                domain="MCP",
                details={
                    **details,
                    "audit_note": "Audit event intended to support compliance review",
                },
            )
            session.add(log_entry)
            await session.flush()
    except Exception:
        # Never crash MCP tool execution if audit persistence encounters a transient DB state
        pass


# -------------------------------------------------------------
# MCP Tool Execution Handlers
# -------------------------------------------------------------
async def handle_get_trusted_context(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id = _resolve_org_uuid(args)
    ws_id = _resolve_workspace_uuid(args)
    allowed_folder_ids = await _resolve_workspace_folder_ids(session, org_id, ws_id)

    agent_id_str = args.get("agent_id") or args.get("_auth_actor_id") or "88888888-8888-8888-8888-888888888888"
    try:
        agent_id = uuid.UUID(str(agent_id_str))
    except Exception:
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")

    query = args.get("query", "")
    min_score = float(args.get("min_trust_score", 0.75))
    max_results = int(args.get("max_results", 5))

    items = []
    # Query verified, 9-gate-passed atomic claims directly from the database for real claim IDs & provenance
    stmt = (
        select(Claim)
        .where(Claim.organization_id == org_id)
        .where(Claim.status == ClaimStatus.VERIFIED)
        .where(Claim.claim_type != "derived_summary")
        .options(
            selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            selectinload(Claim.trust_scores),
            selectinload(Claim.validity_records),
        )
    )
    if allowed_folder_ids is not None:
        stmt = stmt.where(
            Claim.evidence.any(ClaimEvidence.document.has(Document.folder_id.in_(allowed_folder_ids)))
        )

    words = [
        w.strip("?,.!\"'$;:")
        for w in query.lower().split()
        if len(w.strip("?,.!\"'$;:")) > 2 and w.strip("?,.!\"'$;:") not in {"the", "and", "for", "with", "from", "what", "are", "how", "can"}
    ]
    if words:
        conditions = []
        for w in words:
            conditions.append(Claim.claim_text.ilike(f"%{w}%"))
            conditions.append(Claim.subject.ilike(f"%{w}%"))
        stmt = stmt.where(or_(*conditions))

    res_claims = await session.execute(stmt.limit(max_results * 3))
    matched_claims = res_claims.scalars().all()

    matched_claim_ids = [c.id for c in matched_claims]
    conflicts_by_claim: Dict[uuid.UUID, List[Dict[str, Any]]] = {}
    if matched_claim_ids:
        cf_stmt = (
            select(ClaimConflict)
            .where(
                or_(
                    ClaimConflict.claim_a_id.in_(matched_claim_ids),
                    ClaimConflict.claim_b_id.in_(matched_claim_ids),
                )
            )
            .where(ClaimConflict.resolution_status != ConflictStatus.RESOLVED)
            .options(
                selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            )
        )
        cf_res = await session.execute(cf_stmt)
        for cf in cf_res.scalars().all():
            # Verify BOTH sides of every conflict belong to the authorized org & workspace
            if not (
                _claim_in_scope(cf.claim_a, org_id, allowed_folder_ids)
                and _claim_in_scope(cf.claim_b, org_id, allowed_folder_ids)
            ):
                continue
            cf_entry = {
                "conflict_id": str(cf.id),
                "conflict_type": str(cf.conflict_type),
                "severity": str(cf.severity),
                "claim_a_id": str(cf.claim_a_id),
                "claim_b_id": str(cf.claim_b_id),
                "claim_a_text": cf.claim_a.claim_text if cf.claim_a else None,
                "claim_b_text": cf.claim_b.claim_text if cf.claim_b else None,
            }
            conflicts_by_claim.setdefault(cf.claim_a_id, []).append(cf_entry)
            conflicts_by_claim.setdefault(cf.claim_b_id, []).append(cf_entry)

    for c in matched_claims:
        score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.94
        gate_res = ClaimGateEvaluator.evaluate(
            claim_id=str(c.id),
            subject=c.subject,
            predicate=c.predicate,
            object_val=c.object,
            claim_text=c.claim_text,
            claim_type=getattr(c, "claim_type", "policy"),
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
            metadata=getattr(c, "claim_metadata", {}) or {},
            confidence=score,
        )
        if not gate_res.all_9_gates_passed or not gate_res.agent_accessible:
            continue

        if score < min_score:
            continue

        doc_title = "Unknown Document"
        sec = "General"
        pg = 1
        if c.evidence:
            if c.evidence[0].document:
                doc_title = c.evidence[0].document.title
            sec = c.evidence[0].section or "General"
            pg = c.evidence[0].page_number or 1

        v_rec = c.validity_records[0] if c.validity_records else None
        items.append({
            "claim_id": str(c.id),
            "text": c.claim_text,
            "trust_score": score,
            "source": {
                "title": doc_title,
                "authority_level": 95,
                "section": sec,
                "page": pg,
            },
            "validity": {
                "is_current": v_rec.is_current if v_rec else True,
                "valid_from": v_rec.valid_from.isoformat() if v_rec and getattr(v_rec, "valid_from", None) else None,
                "valid_until": v_rec.valid_until.isoformat() if v_rec and getattr(v_rec, "valid_until", None) else None,
            },
            "evidence": [ev.text_span for ev in c.evidence] if c.evidence else [c.claim_text],
            "conflicts_detected": conflicts_by_claim.get(c.id, []),
        })
        if len(items) >= max_results:
            break

    # Explicit abstention when no verified claims match within authorized scope
    if len(items) == 0:
        return {
            "status": "success",
            "abstained": True,
            "query": query,
            "organization_id": str(org_id),
            "total_results": 0,
            "trusted_context": [],
            "summary": "No verified claims found matching query within authorized scope.",
        }

    return {
        "status": "success",
        "abstained": False,
        "query": query,
        "organization_id": str(org_id),
        "total_results": len(items),
        "trusted_context": items,
        "summary": f"Context Trust Layer returned {len(items)} verified claims matching trust threshold >= {min_score}.",
    }


async def handle_evaluate_decision(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    evaluator = DecisionEvaluator(session=session)
    
    actor_id_str = args.get("actor_id") or args.get("_auth_actor_id") or "ai-agent-default"
    actor_role = args.get("actor_role") or args.get("_auth_actor_role") or "support"
    action_type = args.get("action_type") or args.get("decision") or "Evaluate enterprise request"
    
    org_id = _resolve_org_uuid(args)

    context_items = []
    for c in args.get("candidate_claims", []):
        context_items.append(
            DecisionContextItem(
                claim=c.get("claim", ""),
                source=c.get("source", "Ssfa 01 01 Customer Refund & Disputes Policy"),
                updated_at=c.get("updated_at"),
                authority_level=c.get("authority_level", 50),
                scope=c.get("scope")
            )
        )

    # If no candidate context supplied, retrieve verified claims from database matching action_type
    if not context_items:
        action_tokens = [w.strip("?,.!\"'$;:") for w in action_type.lower().split() if len(w.strip("?,.!\"'$;:")) > 2 and w not in ["can", "for", "the", "with", "and", "under", "should", "does"]]
        retrieval_query = (
            select(Claim)
            .where(Claim.organization_id == org_id)
            .where(Claim.status == ClaimStatus.VERIFIED)
            .where(Claim.claim_type != "derived_summary")
            .options(
                selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(Claim.trust_scores)
            )
        )
        if action_tokens:
            token_conds = [Claim.claim_text.ilike(f"%{t}%") for t in action_tokens]
            retrieval_query = retrieval_query.where(or_(*token_conds))
        
        db_res = await session.execute(retrieval_query.limit(10))
        fetched_claims = db_res.scalars().all()
        
        # Score by relevance to query tokens
        def _score_candidate(clm):
            t_lower = clm.claim_text.lower()
            sc = sum(1 for t in action_tokens if t in t_lower)
            if any(num in t_lower for num in ["10,000", "2,500", "7,500", "$"]):
                sc += 3
            return sc

        sorted_fetched = sorted(fetched_claims, key=_score_candidate, reverse=True)

        for fc in sorted_fetched:
            gate_res = ClaimGateEvaluator.evaluate(
                claim_id=str(fc.id),
                subject=fc.subject,
                predicate=fc.predicate,
                object_val=fc.object,
                claim_text=fc.claim_text,
                claim_type=getattr(fc, "claim_type", "policy"),
                status=fc.status.value if hasattr(fc.status, "value") else str(fc.status),
                metadata=getattr(fc, "claim_metadata", {}) or {},
                confidence=float(fc.trust_scores[0].overall_score) if fc.trust_scores else 0.95,
            )
            if not gate_res.all_9_gates_passed or not gate_res.agent_accessible:
                continue

            doc_title = "Ssfa 01 01 Customer Refund & Disputes Policy"
            if fc.evidence and fc.evidence[0].document:
                doc_title = fc.evidence[0].document.title
            context_items.append(
                DecisionContextItem(
                    claim=fc.claim_text,
                    source=doc_title,
                    updated_at="2026-09-17",
                    authority_level=95,
                    scope="Enterprise",
                    claim_id=str(fc.id),
                    claim_version=str(fc.document_version_id) if fc.document_version_id else None,
                    role="supporting",
                )
            )
            if len(context_items) >= 5:
                break

    req = DecisionEvaluateRequest(
        decision=action_type,
        actor=DecisionActor(id=actor_id_str, role=actor_role),
        context=context_items,
        organization_id=org_id,
        required_scope=args.get("required_scope", "Enterprise")
    )

    res = await evaluator.evaluate(req, session=session)
    return {
        "status": "success",
        "decision": res.decision,
        "execution_status": "Not executed by Trulin",
        "validity": res.validity,
        "risk": res.risk,
        "reasons": res.reasons,
        "preferred_source": res.preferred_source,
        "audit_id": res.audit_id,
        "audit_token": res.audit_token,
        "execution_ms": res.execution_ms,
        "suggested_action": res.suggested_action
    }


async def handle_search_claims(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id = _resolve_org_uuid(args)
    ws_id = _resolve_workspace_uuid(args)
    allowed_folder_ids = await _resolve_workspace_folder_ids(session, org_id, ws_id)

    search_text = args.get("search_text", "").strip()
    status_filter = args.get("status", "verified")
    limit = int(args.get("limit", 10))

    query = select(Claim).where(Claim.organization_id == org_id)
    if allowed_folder_ids is not None:
        query = query.where(
            Claim.evidence.any(ClaimEvidence.document.has(Document.folder_id.in_(allowed_folder_ids)))
        )

    search_tokens = [w.strip("?,.!\"'$;:") for w in search_text.lower().split() if len(w.strip("?,.!\"'$;:")) > 2 and w not in ["the", "and", "for", "with", "from"]]

    if search_tokens:
        word_filters = []
        for w in search_tokens:
            word_filters.append(Claim.claim_text.ilike(f"%{w}%"))
            word_filters.append(Claim.subject.ilike(f"%{w}%"))
        query = query.where(or_(*word_filters))
    elif search_text:
        query = query.where(Claim.claim_text.ilike(f"%{search_text}%"))

    if status_filter != "all":
        try:
            status_enum = ClaimStatus(status_filter.lower())
            query = query.where(Claim.status == status_enum)
        except Exception:
            pass

    query = query.options(
        selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
        selectinload(Claim.trust_scores)
    )

    res = await session.execute(query)
    claims = res.scalars().all()

    # Rank claims by keyword match count & currency/number presence
    def _rank_match(c):
        txt = c.claim_text.lower()
        score = sum(1 for t in search_tokens if t in txt)
        if any(num in txt for num in ["10,000", "2,500", "7,500", "$"]):
            score += 2
        return score

    sorted_claims = sorted(claims, key=_rank_match, reverse=True)[:limit]

    items = []
    for c in sorted_claims:
        score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.94
        doc_title = "Ssfa 01 01 Customer Refund & Disputes Policy"
        section = "General"
        page = 1
        ev_quotes = []
        if c.evidence:
            if c.evidence[0].document:
                doc_title = c.evidence[0].document.title
            section = c.evidence[0].section or "General"
            page = c.evidence[0].page_number or 1
            ev_quotes = [ev.text_span for ev in c.evidence]

        gate_res = ClaimGateEvaluator.evaluate(
            claim_id=str(c.id),
            subject=c.subject,
            predicate=c.predicate,
            object_val=c.object,
            claim_text=c.claim_text,
            claim_type=getattr(c, "claim_type", "policy"),
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
            metadata=getattr(c, "claim_metadata", {}) or {},
            confidence=score,
        )

        items.append({
            "id": str(c.id),
            "text": c.claim_text,
            "document": doc_title,
            "section": section,
            "page": page,
            "subject": c.subject,
            "predicate": c.predicate,
            "object": c.object,
            "status": str(c.status),
            "claim_type": str(c.claim_type),
            "trust_score": score,
            "all_9_gates_passed": gate_res.all_9_gates_passed,
            "certification_tier": gate_res.certification_tier,
            "is_canonical": gate_res.is_canonical,
            "agent_accessible": gate_res.agent_accessible,
            "gates": gate_res.gates,
            "evidence": ev_quotes,
            "evidence_count": len(c.evidence) if c.evidence else 0
        })

    return {
        "status": "success",
        "search_text": search_text,
        "count": len(items),
        "claims": items
    }


async def handle_check_conflicts(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id = _resolve_org_uuid(args)
    ws_id = _resolve_workspace_uuid(args)
    allowed_folder_ids = await _resolve_workspace_folder_ids(session, org_id, ws_id)
    claim_text = args.get("claim_text", "").strip()

    ClaimA = aliased(Claim)
    ClaimB = aliased(Claim)
    stmt = (
        select(ClaimConflict)
        .join(ClaimA, ClaimConflict.claim_a_id == ClaimA.id)
        .join(ClaimB, ClaimConflict.claim_b_id == ClaimB.id)
        .where(ClaimA.organization_id == org_id, ClaimB.organization_id == org_id)
        .options(
            selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
        )
        .limit(50)
    )
    res = await session.execute(stmt)
    conflicts = res.scalars().all()

    tokens = [
        w.strip("?,.!\"'$;:")
        for w in claim_text.lower().split()
        if len(w.strip("?,.!\"'$;:")) > 2 and w.strip("?,.!\"'$;:") not in {"the", "and", "for", "with", "from"}
    ]

    results = []
    for cf in conflicts:
        # Verify BOTH sides of every conflict belong to authorized org & workspace
        if not (
            _claim_in_scope(cf.claim_a, org_id, allowed_folder_ids)
            and _claim_in_scope(cf.claim_b, org_id, allowed_folder_ids)
        ):
            continue
        text_a = (cf.claim_a.claim_text if cf.claim_a else "").lower()
        text_b = (cf.claim_b.claim_text if cf.claim_b else "").lower()
        if tokens and not any(t in text_a or t in text_b for t in tokens):
            continue
        status_val = str(cf.resolution_status.value if hasattr(cf.resolution_status, "value") else cf.resolution_status)
        results.append({
            "conflict_id": str(cf.id),
            "claim_1": cf.claim_a.claim_text if cf.claim_a else "Claim A",
            "claim_2": cf.claim_b.claim_text if cf.claim_b else "Claim B",
            "conflict_type": str(cf.conflict_type),
            "severity": str(cf.severity),
            "confidence": float(cf.confidence) if cf.confidence is not None else 1.0,
            "status": status_val,
        })
        if len(results) >= 10:
            break

    return {
        "status": "success",
        "organization_id": str(org_id),
        "claim_text": claim_text,
        "conflicts_found": len(results),
        "conflicts": results,
        "is_safe": len(results) == 0 or all(c["status"] == "resolved" for c in results),
    }


async def handle_get_lineage(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.lineage_service import LineageService
    org_id = _resolve_org_uuid(args)
    ws_id = _resolve_workspace_uuid(args)
    allowed_folder_ids = await _resolve_workspace_folder_ids(session, org_id, ws_id)

    claim_id_str = args.get("claim_id")
    service = LineageService(session)
    if claim_id_str:
        try:
            claim_id = uuid.UUID(claim_id_str)
            own_stmt = (
                select(Claim)
                .where(Claim.id == claim_id, Claim.organization_id == org_id)
                .options(selectinload(Claim.evidence).selectinload(ClaimEvidence.document))
            )
            own_res = await session.execute(own_stmt)
            root_claim = own_res.scalar_one_or_none()
            if not _claim_in_scope(root_claim, org_id, allowed_folder_ids):
                return {"error": "Claim not found in authorized organization/workspace."}

            blast = await service.get_blast_radius(claim_id)
            if "conflicting_claims" in blast and blast["conflicting_claims"]:
                opp_ids = [uuid.UUID(c["claim_id"]) for c in blast["conflicting_claims"] if c.get("claim_id")]
                if opp_ids:
                    opp_res = await session.execute(
                        select(Claim)
                        .where(Claim.id.in_(opp_ids))
                        .options(selectinload(Claim.evidence).selectinload(ClaimEvidence.document))
                    )
                    opp_map = {str(c.id): c for c in opp_res.scalars().all()}
                    blast["conflicting_claims"] = [
                        c for c in blast["conflicting_claims"]
                        if _claim_in_scope(opp_map.get(c.get("claim_id", "")), org_id, allowed_folder_ids)
                    ]
                    blast["connected_conflicts_count"] = len(blast["conflicting_claims"])
            return blast
        except Exception as e:
            return {"error": f"Invalid claim_id: {e}"}

    graph = await service.get_lineage_graph(org_id)
    if allowed_folder_ids is not None:
        doc_res = await session.execute(
            select(Document.id).where(Document.organization_id == org_id, Document.folder_id.in_(allowed_folder_ids))
        )
        allowed_doc_ids = {f"doc_{did}" for did in doc_res.scalars().all()}

        claim_res = await session.execute(
            select(Claim.id)
            .where(Claim.organization_id == org_id)
            .where(Claim.evidence.any(ClaimEvidence.document.has(Document.folder_id.in_(allowed_folder_ids))))
        )
        allowed_claim_uuids = set(claim_res.scalars().all())
        allowed_claim_node_ids = {f"claim_{cid}" for cid in allowed_claim_uuids}

        # Only include conflict nodes where BOTH sides are in allowed_claim_uuids
        cf_res = await session.execute(
            select(ClaimConflict.id, ClaimConflict.claim_a_id, ClaimConflict.claim_b_id)
            .where(
                ClaimConflict.claim_a_id.in_(allowed_claim_uuids),
                ClaimConflict.claim_b_id.in_(allowed_claim_uuids),
            )
        )
        allowed_conflict_node_ids = {f"conflict_{row[0]}" for row in cf_res.all()}

        kept_nodes = []
        kept_ids: set[str] = set()
        for n in graph.get("nodes", []):
            nid = n.get("id", "")
            ntype = n.get("type", "")
            if ntype == "document" and nid not in allowed_doc_ids:
                continue
            if ntype == "claim" and nid not in allowed_claim_node_ids:
                continue
            if ntype == "conflict" and nid not in allowed_conflict_node_ids:
                continue
            kept_nodes.append(n)
            kept_ids.add(nid)

        kept_edges = [
            e for e in graph.get("edges", [])
            if e.get("source") in kept_ids and e.get("target") in kept_ids
        ]
        graph["nodes"] = kept_nodes
        graph["edges"] = kept_edges
    return graph


async def handle_steward_audit(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.steward_agent import StewardAgentService
    org_id = _resolve_org_uuid(args)

    service = StewardAgentService(session)
    return await service.run_context_audit(org_id)


async def handle_intercept_tool_call(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.mcp_middleware_service import intercept_tool_call
    from app.schemas.mcp_middleware import ToolCallProposal
    org_id = _resolve_org_uuid(args)
    proposal = ToolCallProposal(
        tool_name=args.get("tool_name", ""),
        arguments=args.get("arguments", {}),
        actor_id=args.get("actor_id") or args.get("_auth_actor_id") or "mcp-agent",
        actor_role=args.get("actor_role") or args.get("_auth_actor_role") or "support",
        organization_id=org_id,
        workspace_id=args.get("_auth_workspace_id") or args.get("workspace_id"),
        justification=args.get("justification"),
    )
    result = await intercept_tool_call(proposal)
    return result.model_dump(mode="json")


# -------------------------------------------------------------
# Dispatcher for Tool Invocations
# -------------------------------------------------------------
TOOL_HANDLERS = {
    "context_trust_get_trusted_context": handle_get_trusted_context,
    "context_trust_evaluate_decision": handle_evaluate_decision,
    "context_trust_search_claims": handle_search_claims,
    "context_trust_check_conflicts": handle_check_conflicts,
    "context_trust_get_lineage": handle_get_lineage,
    "context_trust_steward_audit": handle_steward_audit,
    "context_trust_intercept_tool_call": handle_intercept_tool_call,
}


async def execute_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    session: AsyncSession,
    auth_org_id: Optional[str] = None,
    auth_workspace_id: Optional[str] = None,
    auth_actor_id: Optional[str] = None,
    auth_actor_role: Optional[str] = None,
) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(TOOL_HANDLERS.keys())}")

    scoped_args = dict(arguments or {})
    if auth_org_id:
        scoped_args["_auth_organization_id"] = auth_org_id
    if auth_workspace_id:
        scoped_args["_auth_workspace_id"] = auth_workspace_id
    if auth_actor_id:
        scoped_args["_auth_actor_id"] = auth_actor_id
    if auth_actor_role:
        scoped_args["_auth_actor_role"] = auth_actor_role

    result = await handler(session, scoped_args)
    org_uuid = _resolve_org_uuid(scoped_args)
    verdict = result.get("decision") or result.get("verdict") or "ALLOW"
    await persist_mcp_audit_event(
        session=session,
        organization_id=org_uuid,
        actor_id=auth_actor_id or scoped_args.get("actor_id", "mcp-agent"),
        actor_role=auth_actor_role or scoped_args.get("actor_role", "support"),
        action_type=f"mcp_tool:{tool_name}",
        target_id=tool_name,
        target_title=f"MCP Tool {tool_name} ({verdict})",
        details={"verdict": verdict, "tool_name": tool_name},
    )
    return result


# -------------------------------------------------------------
# MCP Resources Execution Handler
# -------------------------------------------------------------
async def execute_mcp_resource(
    uri: str,
    session: AsyncSession,
    auth_org_id: Optional[str] = None,
    auth_workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    org_id = DEFAULT_DEMO_ORG_ID
    if auth_org_id:
        try:
            org_id = uuid.UUID(str(auth_org_id))
        except Exception:
            org_id = DEFAULT_DEMO_ORG_ID

    ws_uuid = None
    if auth_workspace_id and str(auth_workspace_id).lower() != "all":
        try:
            ws_uuid = uuid.UUID(str(auth_workspace_id))
        except Exception:
            ws_uuid = None
    allowed_folder_ids = await _resolve_workspace_folder_ids(session, org_id, ws_uuid)

    if uri == "context://claims/verified":
        stmt = (
            select(Claim)
            .where(Claim.organization_id == org_id)
            .options(selectinload(Claim.evidence).selectinload(ClaimEvidence.document))
            .limit(50)
        )
        if allowed_folder_ids is not None:
            stmt = stmt.where(
                Claim.evidence.any(ClaimEvidence.document.has(Document.folder_id.in_(allowed_folder_ids)))
            )
        res = await session.execute(stmt)
        claims = res.scalars().all()
        certified_items = []
        for c in claims:
            gate_res = ClaimGateEvaluator.evaluate(
                claim_id=str(c.id),
                subject=c.subject,
                predicate=c.predicate,
                object_val=c.object,
                claim_text=c.claim_text,
                claim_type=getattr(c, "claim_type", "policy"),
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                metadata=getattr(c, "claim_metadata", {}) or {},
            )
            if gate_res.all_9_gates_passed and gate_res.agent_accessible:
                certified_items.append({
                    "id": str(c.id),
                    "claim_text": c.claim_text,
                    "status": str(c.status),
                    "tier": gate_res.certification_tier,
                    "all_9_gates_passed": True,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                })
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(certified_items, indent=2)
        }

    elif uri == "context://documents/active":
        stmt = select(Document).where(Document.organization_id == org_id).limit(20)
        if allowed_folder_ids is not None:
            stmt = stmt.where(Document.folder_id.in_(allowed_folder_ids))
        res = await session.execute(stmt)
        docs = res.scalars().all()
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps([
                {
                    "id": str(d.id),
                    "title": d.title,
                    "source_type": d.source_type,
                    "sync_status": str(d.sync_status) if hasattr(d, "sync_status") else "active"
                } for d in docs
            ], indent=2)
        }

    elif uri == "context://contradictions/active":
        ClaimA = aliased(Claim)
        ClaimB = aliased(Claim)
        stmt = (
            select(ClaimConflict)
            .join(ClaimA, ClaimConflict.claim_a_id == ClaimA.id)
            .join(ClaimB, ClaimConflict.claim_b_id == ClaimB.id)
            .where(
                ClaimA.organization_id == org_id,
                ClaimB.organization_id == org_id,
                ClaimConflict.resolution_status != ConflictStatus.RESOLVED,
            )
            .options(
                selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            )
            .limit(20)
        )
        res = await session.execute(stmt)
        conflicts = [
            cf for cf in res.scalars().all()
            if _claim_in_scope(cf.claim_a, org_id, allowed_folder_ids)
            and _claim_in_scope(cf.claim_b, org_id, allowed_folder_ids)
        ]
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps([
                {
                    "conflict_id": str(cf.id),
                    "conflict_type": str(cf.conflict_type),
                    "severity": str(cf.severity),
                    "status": str(cf.resolution_status)
                } for cf in conflicts
            ], indent=2)
        }

    elif uri == "context://audit/health":
        from app.services.steward_agent import StewardAgentService
        steward = StewardAgentService(session)
        audit_res = await steward.run_context_audit(org_id)
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(audit_res, indent=2)
        }

    elif uri == "context://policies/active":
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps({
                "governance_standard": "Context Trust Layer Zero-Trust Baseline v2.4",
                "finance": {
                    "refund_window_days": 30,
                    "goodwill_credit_max_tier1_usd": 500,
                    "sox_segregation_required": True
                },
                "secops": {
                    "token_expiry_minutes": 15,
                    "ingress_approval_role": "VP of Infrastructure",
                    "public_wifi_vpn_mandatory": True
                },
                "hr": {
                    "workstation_allowance_annual_usd": 1500,
                    "remote_security_compliance": "Enforced"
                }
            }, indent=2)
        }

    elif uri.startswith("context://claims/"):
        claim_id_str = uri.replace("context://claims/", "").strip()
        try:
            cid = uuid.UUID(claim_id_str)
            stmt = (
                select(Claim)
                .where(Claim.id == cid, Claim.organization_id == org_id)
                .options(selectinload(Claim.evidence).selectinload(ClaimEvidence.document))
            )
            res = await session.execute(stmt)
            claim = res.scalar_one_or_none()
            if claim and _claim_in_scope(claim, org_id, allowed_folder_ids):
                gate_res = ClaimGateEvaluator.evaluate(
                    claim_id=str(claim.id),
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object_val=claim.object,
                    claim_text=claim.claim_text,
                    claim_type=getattr(claim, "claim_type", "policy"),
                    status=claim.status.value if hasattr(claim.status, "value") else str(claim.status),
                    metadata=getattr(claim, "claim_metadata", {}) or {},
                )
                return {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps({
                        "id": str(claim.id),
                        "claim_text": claim.claim_text,
                        "subject": claim.subject,
                        "predicate": claim.predicate,
                        "object": claim.object,
                        "status": str(claim.status),
                        "all_9_gates_passed": gate_res.all_9_gates_passed,
                        "certification_tier": gate_res.certification_tier,
                        "is_canonical": gate_res.is_canonical,
                        "agent_accessible": gate_res.agent_accessible,
                        "gates": gate_res.gates,
                        "rejection_reasons": gate_res.rejection_reasons,
                        "created_at": claim.created_at.isoformat() if claim.created_at else None
                    }, indent=2)
                }
        except Exception:
            pass

    return {
        "uri": uri,
        "mimeType": "application/json",
        "text": json.dumps({"error": f"Resource URI '{uri}' not found or empty."}, indent=2)
    }


# -------------------------------------------------------------
# MCP Governed Prompts Execution Handler
# -------------------------------------------------------------
async def execute_mcp_prompt(prompt_name: str, arguments: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    if prompt_name == "governed_financial_decision":
        action = arguments.get("action_description", "Execute billing modification")
        amount = arguments.get("amount_usd", "unspecified")
        return {
            "description": f"Governed Financial Decision for: {action}",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": (
                            "You are a Governed Autonomous Financial Agent operating under Context Trust Layer policies.\n"
                            "RULES:\n"
                            "1. All refunds over $500 require Tier-2 Manager approval.\n"
                            "2. Verify that the customer contract has not expired before calculating proration.\n"
                            "3. Do NOT execute destructive ledger changes without verifying SOX compliance.\n"
                            f"Action Target: {action} (Amount: ${amount})"
                        )
                    }
                }
            ]
        }

    elif prompt_name == "sox_compliance_audit":
        system = arguments.get("system_name", "Core Billing Service")
        return {
            "description": f"SOX Segregation of Duties Audit for: {system}",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Execute a strict four-eyes verification audit on {system}.\n"
                            "Verify that no single engineer or agent holds simultaneous pull-request merge and production deployment permissions."
                        )
                    }
                }
            ]
        }

    elif prompt_name == "zero_trust_retrieval":
        inquiry = arguments.get("inquiry", "")
        return {
            "description": "Zero-Trust Context Grounding Prompt",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": (
                            "You are the Context Trust Layer Grounding Assistant.\n"
                            f"Answer inquiry: '{inquiry}' using strictly verified claims with Trust Score >= 0.75.\n"
                            "Cite specific source documents and highlight any active contradictions."
                        )
                    }
                }
            ]
        }

    elif prompt_name == "secops_ingress_approval":
        svc = arguments.get("service_name", "Ingress Gateway")
        port = arguments.get("port", "443")
        return {
            "description": f"SecOps Firewall Rule Evaluation: {svc}:{port}",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Evaluate firewall ingress exception proposal for service '{svc}' on port {port}.\n"
                            "Enforce mandatory mTLS 1.3 and block 0.0.0.0/0 SSH (port 22) ingress without VPN."
                        )
                    }
                }
            ]
        }

    raise ValueError(f"Prompt '{prompt_name}' not recognized in MCP Server catalog.")



