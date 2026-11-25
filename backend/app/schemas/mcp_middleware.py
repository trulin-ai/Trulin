import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolRiskTier(str, Enum):
    TIER_1_READ_ONLY = "TIER_1_READ_ONLY"          # Search, get context, read docs (Safe)
    TIER_2_MUTATING_LOW = "TIER_2_MUTATING_LOW"      # Post note, append tag, draft message
    TIER_3_MUTATING_HIGH = "TIER_3_MUTATING_HIGH"    # SQL update, issue refund, change user status
    TIER_4_DANGEROUS = "TIER_4_DANGEROUS"            # Drop table, bash command, shell exec, wire transfer, firewall open


class ToolCallProposal(BaseModel):
    tool_name: str = Field(..., description="External tool or MCP function name, e.g. 'execute_sql', 'send_wire_refund'")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Payload arguments provided to the tool")
    actor_id: str = Field(default="autonomous-agent", description="Calling AI agent identifier")
    actor_role: str = Field(default="support", description="Role of the agent executing the tool")
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[str] = None
    workflow_id: Optional[str] = Field(default=None, description="Multi-step workflow correlation ID")
    step_index: Optional[int] = Field(default=1, description="Step number in multi-step plan")
    justification: Optional[str] = Field(default=None, description="Agent's stated rationale for invoking this tool")


class ToolInterceptionResult(BaseModel):
    verdict: str  # "PERMIT", "BLOCK", "REQUIRE_REVIEW", "SANITIZE_AND_PERMIT"
    permit_token: Optional[str] = Field(default=None, description="Cryptographic SHA-256 execution permit granted to tool")
    risk_tier: ToolRiskTier
    risk_score: float  # 0.0 to 100.0
    reasons: List[str] = Field(default_factory=list)
    sanitized_arguments: Optional[Dict[str, Any]] = None
    liability_prevented_usd: float = 0.0
    suggested_action: Optional[str] = None
    execution_ms: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


class WorkflowPlanStep(BaseModel):
    step_id: int
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class WorkflowPlanEvaluateRequest(BaseModel):
    workflow_id: str
    goal: str
    actor_id: str
    actor_role: str
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[str] = None
    steps: List[WorkflowPlanStep] = Field(..., min_length=1)


class WorkflowPlanEvaluateResponse(BaseModel):
    workflow_id: str
    verdict: str  # "PERMIT", "BLOCK", "REQUIRE_REVIEW"
    max_risk_tier: ToolRiskTier
    accumulated_risk_score: float
    total_liability_prevented_usd: float
    reasons: List[str]
    step_evaluations: List[ToolInterceptionResult]
