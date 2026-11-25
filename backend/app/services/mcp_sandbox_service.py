"""
Harmless local sandbox tool with an observable execution counter and atomic
single-use permit consumption to demonstrate the boundary between advisory
evaluation and non-bypassable gateway enforcement.

Enforcement boundary note:
- Enforcement holds ONLY when the downstream tool refuses execution without a
  valid, unconsumed, HMAC-signed Trulin permit token bound to (permit_id,
  agent_id, organization_id, workspace_id, tool_name, arguments_hash, exp).
- If the underlying tool is exposed directly without permit verification, the
  Trulin integration is advisory/optional rather than mandatory enforcement.
"""

import threading
from typing import Any, Dict, List, Optional, Set
from app.services.mcp_middleware_service import verify_permit_token
from app.services.mcp_telemetry_service import mcp_telemetry_service


class SandboxLedgerTool:
    """In-process harmless sandbox tool with an observable execution counter and atomic replay protection."""

    tool_name: str = "sandbox_ledger_write"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.execution_counter: int = 0
        self.last_payload: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, Any]] = []
        self._consumed_permits: Set[str] = set()

    def reset(self) -> None:
        with self._lock:
            self.execution_counter = 0
            self.last_payload = None
            self.history.clear()
            self._consumed_permits.clear()

    def execute_with_gateway(
        self,
        permit_token: Optional[str],
        arguments: Dict[str, Any],
        organization_id: str,
        workspace_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes the sandbox action ONLY if a valid, unconsumed Trulin permit_token is presented."""
        target_tool = tool_name or self.tool_name
        is_valid, reason, claims = verify_permit_token(
            permit_token=permit_token,
            tool_name=target_tool,
            arguments=arguments,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        if not is_valid or not claims:
            mcp_telemetry_service.record_event(
                tool_name=target_tool,
                arguments={"redacted": True},
                client_type="Sandbox Gateway",
                actor_id="unknown",
                actor_role="unknown",
                verdict="BLOCK",
                trust_score=0.0,
                latency_ms=1.0,
                error=reason,
                response_summary=f"Sandbox execution rejected: {reason}",
                organization_id=organization_id,
            )
            return {
                "executed": False,
                "execution_counter": self.execution_counter,
                "reason": reason,
            }

        permit_id = claims.get("jti", "")
        with self._lock:
            if permit_id in self._consumed_permits:
                mcp_telemetry_service.record_event(
                    tool_name=target_tool,
                    arguments={"permit_id": permit_id},
                    client_type="Sandbox Gateway",
                    actor_id=claims.get("agent_id", "unknown"),
                    actor_role="agent",
                    verdict="BLOCK",
                    trust_score=0.0,
                    latency_ms=1.0,
                    error="Permit token already consumed (replay blocked)",
                    response_summary=f"Sandbox replay blocked for permit {permit_id}",
                    organization_id=organization_id,
                )
                return {
                    "executed": False,
                    "execution_counter": self.execution_counter,
                    "reason": "Permit token already consumed (replay blocked)",
                }

            self._consumed_permits.add(permit_id)
            self.execution_counter += 1
            self.last_payload = {
                "permit_id": permit_id,
                "tool_name": target_tool,
                "organization_id": organization_id,
                "workspace_id": workspace_id,
                "arguments": arguments,
            }
            self.history.append(self.last_payload)
            counter_snapshot = self.execution_counter

        return {
            "executed": True,
            "execution_counter": counter_snapshot,
            "permit_id": permit_id,
            "reason": "Executed under verified Trulin permit",
            "payload": self.last_payload,
        }
