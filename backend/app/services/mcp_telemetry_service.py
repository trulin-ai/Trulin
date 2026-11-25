import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPTelemetryEvent(BaseModel):
    """Audit event record intended to support compliance review (not proof of regulatory compliance)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    organization_id: Optional[str] = None
    tool_name: str
    client_type: str = "Claude Desktop"  # "Claude Desktop", "Cursor IDE", "LangChain", "Ollama", "REST Client"
    actor_id: str = "mcp-agent"
    actor_role: str = "support"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    verdict: str = "ALLOW"  # "ALLOW", "BLOCK", "REVIEW", "SUCCESS", "ERROR"
    trust_score: float = 0.90
    latency_ms: float = 42.0
    error: Optional[str] = None
    response_summary: Optional[str] = None


class MCPTelemetryStats(BaseModel):
    total_invocations: int
    allowed_count: int
    blocked_count: int
    review_count: int
    avg_latency_ms: float
    avg_trust_score: float
    active_connections: int


class MCPTelemetryService:
    _instance = None
    _events: List[MCPTelemetryEvent] = []
    _max_events = 300

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPTelemetryService, cls).__new__(cls)
            cls._instance._init_seed_events()
        return cls._instance

    def _init_seed_events(self):
        # Pre-seed realistic telemetry events for immediate UI showcase
        sample_tools = [
            ("context_trust_get_trusted_context", "Claude Desktop", "billing-agent-01", "finance", {"query": "What is enterprise refund window?"}, "ALLOW", 0.94, 28.4, "Retrieved 4 verified claims"),
            ("context_trust_evaluate_decision", "Cursor IDE", "cursor-developer", "developer", {"action_type": "Execute hotfix bypass"}, "REVIEW", 0.68, 45.1, "Requires Senior SecOps review"),
            ("context_trust_intercept_tool_call", "LangChain Agent", "support-lead", "support", {"tool_name": "execute_sql", "query": "DROP TABLE refunds;--"}, "BLOCK", 0.12, 18.2, "Destructive SQL injection detected"),
            ("context_trust_search_claims", "Ollama Local Gateway", "qwen3-assistant", "developer", {"search_text": "Wi-Fi VPN security"}, "ALLOW", 0.96, 15.6, "Matched 3 active baseline policies"),
            ("context_trust_check_conflicts", "Claude Desktop", "policy-curator", "admin", {"claim_text": "Unlimited 90-day refund for all tiers"}, "REVIEW", 0.55, 38.9, "Contradicts 30-day handbook policy"),
            ("context_trust_get_lineage", "Cursor IDE", "cursor-developer", "developer", {"claim_id": "c-4412"}, "ALLOW", 0.92, 22.0, "DAG depth 3, blast radius low"),
            ("context_trust_intercept_tool_call", "Autonomous Billing Agent", "billing-bot-02", "support", {"tool_name": "process_refund", "amount": 15000.0}, "BLOCK", 0.40, 24.5, "Amount exceeds support role threshold $500"),
            ("context_trust_get_trusted_context", "Claude Desktop", "hr-copilot", "hr", {"query": "Remote work workstation stipend"}, "ALLOW", 0.95, 31.2, "Retrieved HR equipment policy"),
        ]

        now = datetime.now(timezone.utc)
        for i, (tool, client, actor, role, args, verdict, score, latency, summary) in enumerate(sample_tools):
            self._events.append(
                MCPTelemetryEvent(
                    id=str(uuid.uuid4()),
                    timestamp=now,
                    tool_name=tool,
                    client_type=client,
                    actor_id=actor,
                    actor_role=role,
                    arguments=args,
                    verdict=verdict,
                    trust_score=score,
                    latency_ms=latency,
                    response_summary=summary,
                )
            )

    def record_event(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_type: str = "Claude Desktop",
        actor_id: str = "mcp-agent",
        actor_role: str = "support",
        verdict: str = "ALLOW",
        trust_score: float = 0.90,
        latency_ms: float = 30.0,
        error: Optional[str] = None,
        response_summary: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> MCPTelemetryEvent:
        event = MCPTelemetryEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            organization_id=organization_id,
            tool_name=tool_name,
            client_type=client_type,
            actor_id=actor_id,
            actor_role=actor_role,
            arguments=arguments,
            verdict=verdict,
            trust_score=trust_score,
            latency_ms=latency_ms,
            error=error,
            response_summary=response_summary,
        )
        self._events.insert(0, event)
        if len(self._events) > self._max_events:
            self._events.pop()
        return event

    def get_events(
        self,
        limit: int = 100,
        tool_filter: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[MCPTelemetryEvent]:
        events = self._events
        if organization_id:
            events = [e for e in events if e.organization_id == organization_id]
        if tool_filter and tool_filter != "all":
            events = [e for e in events if e.tool_name == tool_filter or e.client_type.lower() == tool_filter.lower()]
        return events[:limit]

    def get_stats(self, organization_id: Optional[str] = None) -> MCPTelemetryStats:
        events = self._events
        if organization_id:
            events = [e for e in events if e.organization_id == organization_id]
        if not events:
            return MCPTelemetryStats(
                total_invocations=0,
                allowed_count=0,
                blocked_count=0,
                review_count=0,
                avg_latency_ms=0.0,
                avg_trust_score=0.0,
                active_connections=0 if organization_id else 3,
            )

        allowed = sum(1 for e in events if e.verdict in ("ALLOW", "PERMIT", "SUCCESS"))
        blocked = sum(1 for e in events if e.verdict in ("BLOCK", "ERROR"))
        review = sum(1 for e in events if e.verdict in ("REVIEW", "REQUIRE_REVIEW"))
        avg_lat = sum(e.latency_ms for e in events) / len(events)
        avg_trust = sum(e.trust_score for e in events) / len(events)

        return MCPTelemetryStats(
            total_invocations=len(events),
            allowed_count=allowed,
            blocked_count=blocked,
            review_count=review,
            avg_latency_ms=round(avg_lat, 1),
            avg_trust_score=round(avg_trust, 2),
            active_connections=len(set(e.client_type for e in events[:20])),
        )

    def clear(self):
        self._events.clear()


mcp_telemetry_service = MCPTelemetryService()
