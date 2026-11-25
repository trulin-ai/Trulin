import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    token: str
    agent_id: str
    role: str = "developer"
    allowed_tools: List[str] = Field(default_factory=lambda: ["*"])
    rate_limit_rpm: int = 60
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    status: str = "active"  # "active" | "revoked"
    organization_id: str = "11111111-1111-1111-1111-111111111111"
    workspace_id: Optional[str] = None


class CreateAgentTokenRequest(BaseModel):
    name: str
    agent_id: str
    role: str = "developer"
    allowed_tools: List[str] = Field(default_factory=lambda: ["*"])
    rate_limit_rpm: int = 60
    organization_id: str = "11111111-1111-1111-1111-111111111111"
    workspace_id: Optional[str] = None


class MCPTokenService:
    _instance = None
    _tokens: Dict[str, AgentToken] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPTokenService, cls).__new__(cls)
            cls._instance._init_seed_tokens()
        return cls._instance

    def _init_seed_tokens(self):
        seed_data = [
            ("Claude Desktop Global Assistant", "claude-desktop-01", "admin", ["*"], 120, "trulin_mcp_claude_live_9a8b7c6d5e4f"),
            ("SecOps Compliance Sentinel", "secops-sentinel", "secops", ["context_trust_get_trusted_context", "context_trust_evaluate_decision", "context_trust_intercept_tool_call"], 60, "trulin_mcp_secops_live_21f98a3b04c8"),
            ("Autonomous Billing Reconciler", "billing-reconciler", "finance", ["context_trust_get_trusted_context", "context_trust_evaluate_decision"], 45, "trulin_mcp_finance_gate_77ea418290bc"),
            ("Zendesk Support Copilot", "support-bot-primary", "support", ["context_trust_get_trusted_context", "context_trust_search_claims"], 90, "trulin_mcp_support_read_33cd1982b5fa"),
        ]

        now = datetime.now(timezone.utc)
        for name, agent_id, role, tools, rpm, tok_val in seed_data:
            t = AgentToken(
                id=str(uuid.uuid4()),
                name=name,
                token=tok_val,
                agent_id=agent_id,
                role=role,
                allowed_tools=tools,
                rate_limit_rpm=rpm,
                created_at=now,
                last_used_at=now,
                status="active"
            )
            self._tokens[t.id] = t

    def list_tokens(self, organization_id: Optional[str] = None) -> List[AgentToken]:
        tokens = list(self._tokens.values())
        if organization_id:
            tokens = [t for t in tokens if t.organization_id == organization_id]
        return sorted(tokens, key=lambda x: x.created_at, reverse=True)

    def create_token(self, req: CreateAgentTokenRequest) -> AgentToken:
        token_secret = f"trulin_mcp_{req.role}_{secrets.token_hex(12)}"
        token_obj = AgentToken(
            id=str(uuid.uuid4()),
            name=req.name,
            token=token_secret,
            agent_id=req.agent_id,
            role=req.role,
            allowed_tools=req.allowed_tools if req.allowed_tools else ["*"],
            rate_limit_rpm=req.rate_limit_rpm,
            created_at=datetime.now(timezone.utc),
            status="active",
            organization_id=req.organization_id,
            workspace_id=req.workspace_id,
        )
        self._tokens[token_obj.id] = token_obj
        return token_obj

    def revoke_token(self, token_id: str) -> bool:
        if token_id in self._tokens:
            self._tokens[token_id].status = "revoked"
            return True
        return False

    def resolve_token(self, token_str: str) -> Optional[AgentToken]:
        """Resolves an active token without checking tool-level entitlements."""
        if not token_str:
            return None
        for t in self._tokens.values():
            if t.token == token_str:
                if t.status != "active":
                    return None
                t.last_used_at = datetime.now(timezone.utc)
                return t
        return None

    def is_tool_allowed(self, token_obj: AgentToken, requested_tool: str) -> bool:
        return "*" in token_obj.allowed_tools or requested_tool in token_obj.allowed_tools

    def validate_token(self, token_str: str, requested_tool: str) -> Optional[AgentToken]:
        token_obj = self.resolve_token(token_str)
        if not token_obj:
            return None
        if self.is_tool_allowed(token_obj, requested_tool):
            return token_obj
        return None


mcp_token_service = MCPTokenService()
