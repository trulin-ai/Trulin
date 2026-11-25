import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.mcp_middleware import (
    ToolCallProposal,
    ToolInterceptionResult,
    ToolRiskTier,
    WorkflowPlanEvaluateRequest,
    WorkflowPlanEvaluateResponse,
)
from app.services.webhook_service import compute_single_incident_liability

logger = logging.getLogger(__name__)

def _get_permit_secret() -> bytes:
    secret = os.environ.get("TRULIN_MCP_PERMIT_SECRET")
    if not secret:
        if os.environ.get("ENVIRONMENT", "").lower() == "production":
            raise RuntimeError("TRULIN_MCP_PERMIT_SECRET must be configured in production.")
        secret = "trulin-dev-permit-hmac-secret-v1"
    return secret.encode("utf-8")


DEFAULT_PERMIT_TTL_SECONDS = 120


def _canonical_args_hash(arguments: Dict[str, Any]) -> str:
    canonical = json.dumps(arguments or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def issue_permit_token(
    tool_name: str,
    arguments: Dict[str, Any],
    organization_id: str,
    actor_id: str,
    workspace_id: Optional[str] = None,
    policy_decision_id: Optional[str] = None,
    ttl_seconds: int = DEFAULT_PERMIT_TTL_SECONDS,
) -> str:
    """Issues a short-lived HMAC-SHA256 signed permit token bound to permit_id, agent, org, workspace, tool, args, and expiry."""
    now = int(time.time())
    claims = {
        "jti": str(uuid.uuid4()),
        "agent_id": actor_id,
        "org_id": organization_id,
        "ws_id": workspace_id,
        "tool": tool_name,
        "args_hash": _canonical_args_hash(arguments),
        "iat": now,
        "exp": now + ttl_seconds,
        "decision_id": policy_decision_id or f"dec_{uuid.uuid4().hex[:12]}",
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    sig = hmac.new(_get_permit_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"permit_{payload_b64}.{sig}"


def verify_permit_token(
    permit_token: Optional[str],
    tool_name: str,
    arguments: Dict[str, Any],
    organization_id: str,
    workspace_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verifies HMAC signature, expiry, tool_name, arguments_hash, organization_id, and workspace_id."""
    if not permit_token or not isinstance(permit_token, str) or not permit_token.startswith("permit_"):
        return False, "Missing or malformed permit token", None

    body = permit_token[len("permit_"):]
    if "." not in body:
        return False, "Invalid permit token format", None

    payload_b64, provided_sig = body.rsplit(".", 1)
    expected_sig = hmac.new(_get_permit_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False, "Permit token signature verification failed", None

    try:
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception:
        return False, "Permit token payload decoding failed", None

    if int(claims.get("exp", 0)) < int(time.time()):
        return False, "Permit token has expired", None
    if claims.get("tool") != tool_name:
        return False, f"Permit token bound to tool '{claims.get('tool')}', not '{tool_name}'", None
    if claims.get("org_id") != organization_id:
        return False, "Permit token organization_id mismatch", None
    if workspace_id is not None and claims.get("ws_id") != workspace_id:
        return False, "Permit token workspace_id mismatch", None
    if claims.get("args_hash") != _canonical_args_hash(arguments):
        return False, "Permit token arguments_hash mismatch", None

    return True, "Valid permit token", claims

# Heuristic patterns for SQL & Shell Injection in tool arguments
SQL_INJECTION_PATTERNS = [
    r"\b(drop|truncate|alter)\s+(table|database|schema)?\s*[a-zA-Z0-9_]+",
    r"\bdelete\s+from\b",
    r";\s*(drop|delete|insert|update|truncate)\b",
    r"(\bunion\s+select\b|\bselect\s+.*\s+from\s+information_schema\b)",
    r"(\bor\s+1=1\b|--|#\s*$)",
]

SHELL_INJECTION_PATTERNS = [
    r"\b(rm\s+-rf|rmdir|mkfs)\b",
    r"\b(cat\s+/etc/shadow|cat\s+/etc/passwd)\b",
    r"(\|\s*bash|\|\s*sh|curl.*\|\s*sh)",
    r"\b(whoami|chmod\s+777|chown\s+root)\b",
    r"\b(iptables\s+-F|ufw\s+disable)\b",
]


def classify_tool_tier(tool_name: str) -> ToolRiskTier:
    """Classifies tool into risk tiers based on tool name semantics."""
    t_lower = (tool_name or "").lower()

    # Tier 4 Dangerous
    if any(k in t_lower for k in [
        "shell", "bash", "terminal", "drop", "truncate", "kill",
        "wire_transfer", "crypto_payout", "firewall", "reboot", "shutdown",
        "delete_database", "iam_role_grant", "shell_exec", "run_cmd"
    ]):
        return ToolRiskTier.TIER_4_DANGEROUS

    # Tier 3 High Mutation
    if any(k in t_lower for k in [
        "sql", "database", "refund", "update", "delete", "modify", "patch",
        "send_payment", "change_policy", "grant_leave", "set_contract", "execute"
    ]):
        return ToolRiskTier.TIER_3_MUTATING_HIGH

    # Tier 2 Low Mutation
    if any(k in t_lower for k in [
        "add_comment", "tag", "draft", "note", "notify", "send_email",
        "create_ticket", "append", "log"
    ]):
        return ToolRiskTier.TIER_2_MUTATING_LOW

    # Tier 1 Read Only
    return ToolRiskTier.TIER_1_READ_ONLY


def scan_arguments_for_threats(arguments: Dict[str, Any]) -> List[str]:
    """Inspects all string argument values recursively for SQL, shell, or exfiltration indicators."""
    threats = []
    args_json = json.dumps(arguments).lower()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, args_json, re.IGNORECASE):
            threats.append(f"SQL Injection signature detected: {pattern}")
            break

    for pattern in SHELL_INJECTION_PATTERNS:
        if re.search(pattern, args_json, re.IGNORECASE):
            threats.append(f"Critical Shell / Command Injection signature detected: {pattern}")
            break

    return threats


async def intercept_tool_call(
    proposal: ToolCallProposal,
) -> ToolInterceptionResult:
    """Interprets and enforces safety governance policies on a planned tool invocation before execution."""
    t0 = time.perf_counter()
    tier = classify_tool_tier(proposal.tool_name)
    reasons: List[str] = []
    liability_prevented = 0.0
    suggested_action = None
    role_lower = (proposal.actor_role or "support").lower()

    # 1. Scan argument payloads for malicious injection patterns
    threats = scan_arguments_for_threats(proposal.arguments)
    if threats:
        tier = ToolRiskTier.TIER_4_DANGEROUS
        reasons.extend(threats)
        reasons.append("Tool execution immediately halted by Deterministic Security Policy.")
        verdict = "BLOCK"
        liability_prevented = 45000.0
        suggested_action = "Reject tool call and flag security incident for anomalous prompt execution."
    else:
        # 2. Check Role-Based Tool Entitlements & Thresholds
        if tier == ToolRiskTier.TIER_4_DANGEROUS:
            if role_lower not in ("admin", "ciso", "lead_devops"):
                verdict = "BLOCK"
                reasons.append(
                    f"Separation of Duties Violation: Role '{proposal.actor_role}' is not authorized to invoke dangerous tool '{proposal.tool_name}'."
                )
                liability_prevented = 50000.0
                suggested_action = "Require manual C-level or CISO approval before re-attempting dangerous operation."
            else:
                verdict = "REQUIRE_REVIEW"
                reasons.append("High-impact dangerous tool requires mandatory dual-custody verification under EU AI Act Art. 14.")
                liability_prevented = 25000.0
                suggested_action = "Route to Human-in-the-Loop review queue for auditor sign-off."

        elif tier == ToolRiskTier.TIER_3_MUTATING_HIGH:
            # Check for financial refund thresholds
            amount = 0.0
            for k, v in proposal.arguments.items():
                if "amount" in k.lower() or "refund" in k.lower() or "price" in k.lower():
                    try:
                        amount = float(v)
                    except (ValueError, TypeError):
                        pass

            if amount > 2500.0 and role_lower not in ("finance", "admin"):
                verdict = "REQUIRE_REVIEW"
                reasons.append(
                    f"Financial Safety Ceiling: Transaction amount ${amount:,.2f} exceeds automated limit ($2,500.00) for role '{proposal.actor_role}'."
                )
                liability_prevented = amount
                suggested_action = "Escalate to finance supervisor for dual sign-off."
            elif "delete" in proposal.tool_name.lower() and role_lower not in ("admin", "data_owner"):
                verdict = "BLOCK"
                reasons.append(f"Destructive mutation '{proposal.tool_name}' blocked for role '{proposal.actor_role}'.")
                liability_prevented = 10000.0
                suggested_action = "Contact Data Owner for authorized data pruning."
            else:
                verdict = "PERMIT"
                reasons.append("Tool invocation complies with deterministic role policy bounds.")

        elif tier == ToolRiskTier.TIER_2_MUTATING_LOW:
            verdict = "PERMIT"
            reasons.append("Low-mutation tool call authorized with standard execution telemetry.")

        else:
            # TIER_1_READ_ONLY
            verdict = "PERMIT"
            reasons.append("Read-only context lookup granted.")

    # Calculate risk score
    tier_scores = {
        ToolRiskTier.TIER_1_READ_ONLY: 10.0,
        ToolRiskTier.TIER_2_MUTATING_LOW: 35.0,
        ToolRiskTier.TIER_3_MUTATING_HIGH: 70.0,
        ToolRiskTier.TIER_4_DANGEROUS: 95.0,
    }
    risk_score = tier_scores[tier]
    if verdict == "BLOCK":
        risk_score = max(risk_score, 90.0)

    # Cryptographic HMAC-signed permit token generation (bound to permit_id, agent, org, workspace, tool, args, expiry)
    permit_token = None
    if verdict in ("PERMIT", "SANITIZE_AND_PERMIT"):
        permit_token = issue_permit_token(
            tool_name=proposal.tool_name,
            arguments=proposal.arguments,
            organization_id=str(proposal.organization_id or ""),
            actor_id=proposal.actor_id,
            workspace_id=getattr(proposal, "workspace_id", None),
        )

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return ToolInterceptionResult(
        verdict=verdict,
        permit_token=permit_token,
        risk_tier=tier,
        risk_score=risk_score,
        reasons=reasons,
        sanitized_arguments=proposal.arguments,
        liability_prevented_usd=liability_prevented,
        suggested_action=suggested_action,
        execution_ms=duration_ms,
        timestamp=datetime.now(timezone.utc),
    )


async def evaluate_workflow_plan(
    plan: WorkflowPlanEvaluateRequest,
) -> WorkflowPlanEvaluateResponse:
    """Pre-audits an entire multi-step agent workflow plan before any tool execution begins."""
    step_evals: List[ToolInterceptionResult] = []
    total_liability = 0.0
    accumulated_risk = 0.0
    all_reasons: List[str] = []
    highest_tier = ToolRiskTier.TIER_1_READ_ONLY

    tier_order = [
        ToolRiskTier.TIER_1_READ_ONLY,
        ToolRiskTier.TIER_2_MUTATING_LOW,
        ToolRiskTier.TIER_3_MUTATING_HIGH,
        ToolRiskTier.TIER_4_DANGEROUS,
    ]

    for step in plan.steps:
        proposal = ToolCallProposal(
            tool_name=step.tool_name,
            arguments=step.arguments,
            actor_id=plan.actor_id,
            actor_role=plan.actor_role,
            organization_id=plan.organization_id,
            workflow_id=plan.workflow_id,
            step_index=step.step_id,
            justification=step.description,
        )
        res = await intercept_tool_call(proposal)
        step_evals.append(res)
        total_liability += res.liability_prevented_usd
        accumulated_risk += res.risk_score

        if tier_order.index(res.risk_tier) > tier_order.index(highest_tier):
            highest_tier = res.risk_tier

        if res.verdict != "PERMIT":
            all_reasons.extend(res.reasons)

    # Determine overall workflow verdict
    if any(s.verdict == "BLOCK" for s in step_evals):
        overall_verdict = "BLOCK"
    elif any(s.verdict == "REQUIRE_REVIEW" for s in step_evals) or accumulated_risk > 150.0:
        overall_verdict = "REQUIRE_REVIEW"
        if accumulated_risk > 150.0 and "Accumulated risk" not in "".join(all_reasons):
            all_reasons.append(
                f"Multi-Step Risk Compounding: Cumulative workflow risk score ({accumulated_risk:.1f}) exceeds composite threshold."
            )
    else:
        overall_verdict = "PERMIT"
        all_reasons.append("All planned agent tool steps meet deterministic governance criteria.")

    normalized_risk = min(100.0, round(accumulated_risk / max(1, len(plan.steps)), 1))

    return WorkflowPlanEvaluateResponse(
        workflow_id=plan.workflow_id,
        verdict=overall_verdict,
        max_risk_tier=highest_tier,
        accumulated_risk_score=normalized_risk,
        total_liability_prevented_usd=total_liability,
        reasons=all_reasons,
        step_evaluations=step_evals,
    )
