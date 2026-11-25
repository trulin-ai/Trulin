"""
End-to-End MCP Client Verification Suite.

Covers all 3 distinct capability layers against real PostgreSQL + live FastAPI MCP endpoints:
1. Context Delivery (JSON-RPC 2.0 & REST):
   - Authenticated Org A client retrieves only Org A's verified, 9-gate-passed claims with real claim_ids & provenance.
   - Candidate and rejected claims are excluded.
   - Conflicts are scoped by organization_id and claim_text.
   - Unsupported queries return explicit abstention (abstained=True, total_results=0).
   - Org B token cannot retrieve Org A's claims or conflicts (tenant isolation).
   - Missing/revoked/unauthorized tokens are rejected (-32001 / -32003 / 401 / 403).
2. Advisory Evaluation:
   - Disallowed action returns verdict + supported policy reasons + explicit execution_status="Not executed by Trulin".
3. Sandbox Enforcement Proof:
   - Allowed request -> HMAC permit issued -> SandboxLedgerTool execution_counter increments 0 -> 1.
   - Blocked request -> BLOCK verdict, no permit -> execution_counter remains 1.
   - Tampered / missing / wrong-org / wrong-args permit -> rejected -> execution_counter remains 1.
"""

import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import time
import uuid
import pytest
import httpx
from sqlalchemy import delete

from app.main import app
from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.services.mcp_middleware_service import issue_permit_token
from app.services.mcp_sandbox_service import SandboxLedgerTool
from app.services.mcp_telemetry_service import mcp_telemetry_service
from app.services.mcp_token_service import CreateAgentTokenRequest, mcp_token_service


async def _seed_org_corpus(
    session,
    org_id: uuid.UUID,
    org_name: str,
    doc_title: str,
    verified_text: str,
    candidate_text: str,
    rejected_text: str,
    conflict_counter_text: str,
):
    org = Organization(id=org_id, name=org_name, slug=f"slug-{org_id.hex[:8]}")
    session.add(org)
    await session.flush()

    source = DataSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        name=f"{org_name} Source",
        source_type="manual_upload",
        external_id=f"ext-{org_id.hex[:8]}",
        status=RecordStatus.ACTIVE,
    )
    session.add(source)
    await session.flush()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=source.id,
        title=doc_title,
        document_type="policy",
        content_hash=f"doc-hash-{org_id.hex[:12]}",
    )
    session.add(doc)
    await session.flush()

    dv = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc.id,
        version_number=1,
        content_hash=f"hash-{org_id.hex[:12]}",
    )
    session.add(dv)
    await session.flush()

    c_verified = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=dv.id,
        claim_text=verified_text,
        subject="Refund Policy",
        predicate="requires",
        object="Tier-2 manager approval above $500",
        claim_type="policy",
        status=ClaimStatus.VERIFIED,
    )
    c_candidate = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=dv.id,
        claim_text=candidate_text,
        subject="Refund Policy",
        predicate="allows",
        object="unverified draft refund",
        claim_type="policy",
        status=ClaimStatus.CANDIDATE,
    )
    c_rejected = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=dv.id,
        claim_text=rejected_text,
        subject="Refund Policy",
        predicate="allows",
        object="rejected refund rule",
        claim_type="policy",
        status=ClaimStatus.REJECTED,
    )
    c_conflict_other = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=dv.id,
        claim_text=conflict_counter_text,
        subject="Refund Policy",
        predicate="allows",
        object="90-day exception",
        claim_type="policy",
        status=ClaimStatus.VERIFIED,
    )
    session.add_all([c_verified, c_candidate, c_rejected, c_conflict_other])
    await session.flush()

    ev = ClaimEvidence(
        id=uuid.uuid4(),
        claim_id=c_verified.id,
        document_id=doc.id,
        text_span=verified_text,
        section="Section 2.1",
        page_number=3,
    )
    session.add(ev)

    conflict = ClaimConflict(
        id=uuid.uuid4(),
        claim_a_id=c_verified.id,
        claim_b_id=c_conflict_other.id,
        conflict_type="contradiction",
        severity="high",
        confidence=0.92,
        resolution_status=ConflictStatus.DETECTED,
    )
    session.add(conflict)
    await session.flush()

    return {
        "org_id": org_id,
        "verified_claim_id": c_verified.id,
        "candidate_claim_id": c_candidate.id,
        "rejected_claim_id": c_rejected.id,
        "conflict_id": conflict.id,
        "doc_title": doc_title,
    }


@pytest.mark.anyio
async def test_mcp_e2e_context_advisory_and_sandbox_enforcement():
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        org_a = await _seed_org_corpus(
            session,
            org_id=org_a_id,
            org_name="Org Alpha E2E",
            doc_title="Alpha Refund Governance Policy",
            verified_text="Alpha refunds exceeding $500 require Tier-2 manager approval within 30 days.",
            candidate_text="Alpha candidate draft: refunds up to $9999 without approval.",
            rejected_text="Alpha rejected rule: never issue refunds.",
            conflict_counter_text="Alpha legacy addendum allows 90-day refund window.",
        )
        await _seed_org_corpus(
            session,
            org_id=org_b_id,
            org_name="Org Beta E2E",
            doc_title="Beta Expense Policy",
            verified_text="Beta travel expenses require VP approval above $1,000.",
            candidate_text="Beta candidate draft expense rule.",
            rejected_text="Beta rejected expense rule.",
            conflict_counter_text="Beta conflicting travel rule.",
        )
        await session.commit()

    # Issue scoped MCP tokens for Org A and Org B
    tok_a = mcp_token_service.create_token(
        CreateAgentTokenRequest(
            name="Org A E2E Agent",
            agent_id="agent-alpha-01",
            role="support",
            allowed_tools=[
                "context_trust_get_trusted_context",
                "context_trust_check_conflicts",
                "context_trust_evaluate_decision",
                "context_trust_intercept_tool_call",
            ],
            organization_id=str(org_a_id),
        )
    )
    tok_a_restricted = mcp_token_service.create_token(
        CreateAgentTokenRequest(
            name="Org A ReadOnly Agent",
            agent_id="agent-alpha-ro",
            role="support",
            allowed_tools=["context_trust_get_trusted_context"],
            organization_id=str(org_a_id),
        )
    )
    tok_b = mcp_token_service.create_token(
        CreateAgentTokenRequest(
            name="Org B E2E Agent",
            agent_id="agent-beta-01",
            role="support",
            allowed_tools=["*"],
            organization_id=str(org_b_id),
        )
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # -----------------------------------------------------------------
            # 1. Authentication & Tool Entitlement Enforcement
            # -----------------------------------------------------------------
            unauth_rpc = await client.post(
                "/v1/mcp",
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_trusted_context", "arguments": {"query": "refund"}}, "id": 1},
            )
            assert unauth_rpc.json()["error"]["code"] == -32001

            forbidden_rpc = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_a_restricted.token}"},
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_evaluate_decision", "arguments": {"action_type": "refund", "actor_id": "a1"}}, "id": 2},
            )
            assert forbidden_rpc.json()["error"]["code"] == -32003

            # -----------------------------------------------------------------
            # 2. Real Context Retrieval (Org A) via JSON-RPC 2.0
            # -----------------------------------------------------------------
            ctx_res = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_a.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "context_trust_get_trusted_context",
                        "arguments": {
                            "query": "Alpha refunds approval",
                            # Attempt to spoof Org B in arguments — must be ignored in favor of token's org_a_id
                            "organization_id": str(org_b_id),
                        },
                    },
                    "id": 3,
                },
            )
            assert ctx_res.status_code == 200
            ctx_payload = json.loads(ctx_res.json()["result"]["content"][0]["text"])
            assert ctx_payload["organization_id"] == str(org_a_id)
            assert ctx_payload["abstained"] is False
            assert ctx_payload["total_results"] >= 1
            returned_ids = {item["claim_id"] for item in ctx_payload["trusted_context"]}
            returned_texts = " ".join(item["text"] for item in ctx_payload["trusted_context"])
            assert str(org_a["verified_claim_id"]) in returned_ids
            assert str(org_a["candidate_claim_id"]) not in returned_ids
            assert str(org_a["rejected_claim_id"]) not in returned_ids
            assert "candidate draft" not in returned_texts
            assert "rejected rule" not in returned_texts
            assert ctx_payload["trusted_context"][0]["source"]["title"] == org_a["doc_title"]
            assert len(ctx_payload["trusted_context"][0]["conflicts_detected"]) >= 1

            # Unsupported query -> explicit abstention
            empty_res = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_a.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "context_trust_get_trusted_context",
                        "arguments": {"query": "quantum_teleportation_protocol_xyz"},
                    },
                    "id": 4,
                },
            )
            empty_payload = json.loads(empty_res.json()["result"]["content"][0]["text"])
            assert empty_payload["abstained"] is True
            assert empty_payload["total_results"] == 0
            assert empty_payload["trusted_context"] == []

            # Multi-tenant isolation: Org B token querying Org A's rule -> abstained
            cross_tenant_res = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_b.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "context_trust_get_trusted_context",
                        "arguments": {"query": "Alpha refunds", "organization_id": str(org_a_id)},
                    },
                    "id": 5,
                },
            )
            cross_payload = json.loads(cross_tenant_res.json()["result"]["content"][0]["text"])
            assert cross_payload["organization_id"] == str(org_b_id)
            assert cross_payload["abstained"] is True
            assert cross_payload["total_results"] == 0
            assert str(org_a["verified_claim_id"]) not in {
                item["claim_id"] for item in cross_payload["trusted_context"]
            }

            # Scoped conflict check: Org B cannot see Org A's conflicts
            cf_b_res = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_b.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "context_trust_check_conflicts",
                        "arguments": {"claim_text": "Alpha refunds 90-day"},
                    },
                    "id": 6,
                },
            )
            cf_b_payload = json.loads(cf_b_res.json()["result"]["content"][0]["text"])
            assert cf_b_payload["conflicts_found"] == 0

            # -----------------------------------------------------------------
            # 3. Advisory Evaluation (Explicitly Not Executed)
            # -----------------------------------------------------------------
            adv_res = await client.post(
                "/v1/mcp",
                headers={"Authorization": f"Bearer {tok_a.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "context_trust_evaluate_decision",
                        "arguments": {
                            "action_type": "Issue $5000 customer refund without manager approval",
                            "actor_id": "agent-alpha-01",
                            "actor_role": "support",
                        },
                    },
                    "id": 7,
                },
            )
            adv_payload = json.loads(adv_res.json()["result"]["content"][0]["text"])
            assert adv_payload["execution_status"] == "Not executed by Trulin"
            assert adv_payload["decision"] in ("BLOCK", "REQUIRE_REVIEW", "ALLOW")
            assert isinstance(adv_payload["reasons"], list)

            # -----------------------------------------------------------------
            # 4. Harmless Sandbox Tool Enforcement Proof
            # -----------------------------------------------------------------
            sandbox = SandboxLedgerTool()
            assert sandbox.execution_counter == 0

            # 4a. Allowed request -> PERMIT + HMAC permit_token -> counter increments to 1
            allowed_args = {"entry": "dry_run_check", "amount": 50}
            permit_res = await client.post(
                "/v1/mcp/intercept-tool",
                headers={"Authorization": f"Bearer {tok_a.token}"},
                json={
                    "tool_name": sandbox.tool_name,
                    "arguments": allowed_args,
                    "actor_id": "agent-alpha-01",
                    "actor_role": "support",
                },
            )
            assert permit_res.status_code == 200
            permit_data = permit_res.json()
            assert permit_data["verdict"] == "PERMIT"
            assert permit_data["permit_token"] is not None

            exec_ok = sandbox.execute_with_gateway(
                permit_token=permit_data["permit_token"],
                arguments=allowed_args,
                organization_id=str(org_a_id),
            )
            assert exec_ok["executed"] is True
            assert sandbox.execution_counter == 1

            # 4b. Blocked request (SQL injection) -> BLOCK, no permit -> counter stays 1
            blocked_args = {"entry": "DROP TABLE audit_logs;--"}
            block_res = await client.post(
                "/v1/mcp/intercept-tool",
                headers={"Authorization": f"Bearer {tok_a.token}"},
                json={
                    "tool_name": sandbox.tool_name,
                    "arguments": blocked_args,
                    "actor_id": "agent-alpha-01",
                    "actor_role": "support",
                },
            )
            assert block_res.status_code == 200
            block_data = block_res.json()
            assert block_data["verdict"] == "BLOCK"
            assert block_data["permit_token"] is None

            exec_blocked = sandbox.execute_with_gateway(
                permit_token=block_data["permit_token"],
                arguments=blocked_args,
                organization_id=str(org_a_id),
            )
            assert exec_blocked["executed"] is False
            assert sandbox.execution_counter == 1

            # 4c. Tampered / wrong-org / wrong-args permit -> rejected -> counter stays 1
            exec_tampered = sandbox.execute_with_gateway(
                permit_token=permit_data["permit_token"] + "tamper",
                arguments=allowed_args,
                organization_id=str(org_a_id),
            )
            assert exec_tampered["executed"] is False
            assert sandbox.execution_counter == 1

            exec_wrong_org = sandbox.execute_with_gateway(
                permit_token=permit_data["permit_token"],
                arguments=allowed_args,
                organization_id=str(org_b_id),
            )
            assert exec_wrong_org["executed"] is False
            assert sandbox.execution_counter == 1

            exec_wrong_args = sandbox.execute_with_gateway(
                permit_token=permit_data["permit_token"],
                arguments={"entry": "dry_run_check", "amount": 99999},
                organization_id=str(org_a_id),
            )
            assert exec_wrong_args["executed"] is False
            assert sandbox.execution_counter == 1

    finally:
        mcp_token_service.revoke_token(tok_a.id)
        mcp_token_service.revoke_token(tok_a_restricted.id)
        mcp_token_service.revoke_token(tok_b.id)
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Organization).where(Organization.id.in_([org_a_id, org_b_id])))
            await session.commit()


@pytest.mark.anyio
async def test_mcp_workspace_isolation_replay_auth_matrix_and_stdio_process(monkeypatch):
    """
    Verifies:
    1. Same-org, cross-workspace isolation (nested folder subtree WS1 vs sibling WS2),
       including BOTH sides of conflicts and lineage graph/blast-radius filtering.
    2. Permit replay, concurrent atomic consumption, expiry, wrong tool/workspace, and production secret guard.
    3. Complete endpoint authentication & admin RBAC negative matrix + no raw token logging.
    4. Real separate-process mcp_stdio.py client session against live uvicorn over stdin/stdout JSON-RPC.
    """
    org_id = uuid.uuid4()
    ws1_id = uuid.uuid4()
    ws1_child_id = uuid.uuid4()
    ws2_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        org = Organization(id=org_id, name="SameOrg MultiWS", slug=f"slug-ws-{org_id.hex[:8]}")
        session.add(org)
        await session.flush()

        f_ws1 = Folder(id=ws1_id, organization_id=org_id, name="WS1 Root", depth=0)
        f_ws1_child = Folder(id=ws1_child_id, organization_id=org_id, parent_id=ws1_id, name="WS1 Child", depth=1)
        f_ws2 = Folder(id=ws2_id, organization_id=org_id, name="WS2 Sibling", depth=0)
        session.add_all([f_ws1, f_ws1_child, f_ws2])
        await session.flush()

        src = DataSource(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="WS Test Source",
            source_type="manual_upload",
            external_id=f"ext-ws-{org_id.hex[:8]}",
            status=RecordStatus.ACTIVE,
        )
        session.add(src)
        await session.flush()

        doc_ws1 = Document(id=uuid.uuid4(), organization_id=org_id, folder_id=ws1_id, source_id=src.id, title="WS1 Policy", document_type="policy", content_hash="h-ws1")
        doc_ws1_child = Document(id=uuid.uuid4(), organization_id=org_id, folder_id=ws1_child_id, source_id=src.id, title="WS1 Child Policy", document_type="policy", content_hash="h-ws1c")
        doc_ws2 = Document(id=uuid.uuid4(), organization_id=org_id, folder_id=ws2_id, source_id=src.id, title="WS2 Secret Policy", document_type="policy", content_hash="h-ws2")
        session.add_all([doc_ws1, doc_ws1_child, doc_ws2])
        await session.flush()

        dv1 = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws1.id, version_number=1, content_hash="dv-ws1")
        dv1c = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws1_child.id, version_number=1, content_hash="dv-ws1c")
        dv2 = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws2.id, version_number=1, content_hash="dv-ws2")
        session.add_all([dv1, dv1c, dv2])
        await session.flush()

        c_ws1 = Claim(id=uuid.uuid4(), organization_id=org_id, document_version_id=dv1.id, claim_text="WS1 travel expenses must not exceed $300 per day.", subject="Travel expenses", predicate="must_not_exceed", object="$300 per day", claim_type="policy", status=ClaimStatus.VERIFIED)
        c_ws1c = Claim(id=uuid.uuid4(), organization_id=org_id, document_version_id=dv1c.id, claim_text="WS1 child addendum travel expenses must not exceed $450 per day.", subject="Travel expenses", predicate="must_not_exceed", object="$450 per day", claim_type="policy", status=ClaimStatus.VERIFIED)
        c_ws2 = Claim(id=uuid.uuid4(), organization_id=org_id, document_version_id=dv2.id, claim_text="WS2 executive travel expenses must not exceed $9000 per day.", subject="Travel expenses", predicate="must_not_exceed", object="$9000 per day", claim_type="policy", status=ClaimStatus.VERIFIED)
        session.add_all([c_ws1, c_ws1c, c_ws2])
        await session.flush()

        session.add_all([
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws1.id, document_id=doc_ws1.id, text_span=c_ws1.claim_text, section="S1", page_number=1),
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws1c.id, document_id=doc_ws1_child.id, text_span=c_ws1c.claim_text, section="S2", page_number=1),
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws2.id, document_id=doc_ws2.id, text_span=c_ws2.claim_text, section="S3", page_number=1),
        ])

        # Within-WS1 conflict (both sides in WS1 subtree) + Cross-workspace conflict (WS1 <-> WS2)
        cf_within = ClaimConflict(id=uuid.uuid4(), claim_a_id=c_ws1.id, claim_b_id=c_ws1c.id, conflict_type="contradiction", severity="medium", confidence=0.90, resolution_status=ConflictStatus.DETECTED)
        cf_cross = ClaimConflict(id=uuid.uuid4(), claim_a_id=c_ws1.id, claim_b_id=c_ws2.id, conflict_type="contradiction", severity="high", confidence=0.95, resolution_status=ConflictStatus.DETECTED)
        session.add_all([cf_within, cf_cross])
        await session.commit()

    tok_ws1 = mcp_token_service.create_token(
        CreateAgentTokenRequest(
            name="WS1 Scoped Support",
            agent_id="agent-ws1",
            role="support",
            allowed_tools=["*"],
            organization_id=str(org_id),
            workspace_id=str(ws1_id),
        )
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers_ws1 = {"Authorization": f"Bearer {tok_ws1.token}"}

            # 1. Same-org, cross-workspace isolation (WS1 + descendant WS1_child included; WS2 excluded)
            ctx_ws1 = await client.post(
                "/v1/mcp",
                headers=headers_ws1,
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_trusted_context", "arguments": {"query": "travel expenses", "workspace_id": str(ws2_id)}}, "id": 10},
            )
            ctx_data = json.loads(ctx_ws1.json()["result"]["content"][0]["text"])
            returned_ids = {i["claim_id"] for i in ctx_data["trusted_context"]}
            assert str(c_ws1.id) in returned_ids
            assert str(c_ws1c.id) in returned_ids
            assert str(c_ws2.id) not in returned_ids

            # Both-sides conflict check: cross-workspace conflict (c_ws1 <-> c_ws2) MUST NOT leak c_ws2
            cf_res = await client.post(
                "/v1/mcp",
                headers=headers_ws1,
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_check_conflicts", "arguments": {"claim_text": "travel expenses"}}, "id": 11},
            )
            cf_data = json.loads(cf_res.json()["result"]["content"][0]["text"])
            assert cf_data["conflicts_found"] == 1
            assert cf_data["conflicts"][0]["conflict_id"] == str(cf_within.id)

            # Lineage blast radius & graph must filter out WS2 nodes/conflicts
            lin_blast = await client.post(
                "/v1/mcp",
                headers=headers_ws1,
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_lineage", "arguments": {"claim_id": str(c_ws1.id)}}, "id": 12},
            )
            blast_data = json.loads(lin_blast.json()["result"]["content"][0]["text"])
            opp_ids = {c["claim_id"] for c in blast_data.get("conflicting_claims", [])}
            assert str(c_ws1c.id) in opp_ids
            assert str(c_ws2.id) not in opp_ids

            lin_graph = await client.post(
                "/v1/mcp",
                headers=headers_ws1,
                json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_lineage", "arguments": {}}, "id": 13},
            )
            graph_data = json.loads(lin_graph.json()["result"]["content"][0]["text"])
            node_ids = {n["id"] for n in graph_data.get("nodes", [])}
            assert f"claim_{c_ws2.id}" not in node_ids
            assert f"doc_{doc_ws2.id}" not in node_ids
            assert f"conflict_{cf_cross.id}" not in node_ids

            # 2. Complete Endpoint Auth & Admin RBAC Matrix Negative Tests
            for method, path, body in [
                ("GET", "/v1/mcp/sse", None),
                ("POST", "/v1/mcp/prompts/governed_financial_decision", {"action_description": "test"}),
                ("GET", "/v1/mcp/telemetry", None),
                ("DELETE", "/v1/mcp/telemetry", None),
                ("GET", "/v1/mcp/tokens", None),
                ("POST", "/v1/mcp/tokens", {"name": "x", "agent_id": "x"}),
                ("DELETE", "/v1/mcp/tokens/fake-id", None),
                ("POST", "/v1/mcp/proxies", {"id": "p1", "name": "p1", "provider": "x", "description": "x", "icon": "shield", "category": "test"}),
                ("POST", "/v1/mcp/workflow/evaluate", {"workflow_id": "w1", "goal": "g", "actor_id": "a1", "actor_role": "support", "steps": [{"step_id": 1, "tool_name": "get_ticket", "arguments": {}}]}),
            ]:
                r = await client.request(method, path, json=body)
                assert r.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {r.status_code}"

            for method, path, body in [
                ("GET", "/v1/mcp/tokens", None),
                ("POST", "/v1/mcp/tokens", {"name": "x", "agent_id": "x"}),
                ("DELETE", "/v1/mcp/tokens/fake-id", None),
                ("DELETE", "/v1/mcp/telemetry", None),
                ("POST", "/v1/mcp/proxies", {"id": "p1", "name": "p1", "provider": "x", "description": "x", "icon": "shield", "category": "test"}),
            ]:
                r = await client.request(method, path, headers=headers_ws1, json=body)
                assert r.status_code == 403, f"Expected 403 for non-admin {method} {path}, got {r.status_code}"

            # 3. Permit Replay, Concurrency, Expiry, Wrong-Tool/Workspace, and Production Secret Guard
            sandbox = SandboxLedgerTool()
            args_ok = {"entry": "ledger_item_1", "amount": 10}
            permit_res = await client.post(
                "/v1/mcp/intercept-tool",
                headers=headers_ws1,
                json={"tool_name": sandbox.tool_name, "arguments": args_ok, "actor_id": "agent-ws1", "actor_role": "support"},
            )
            permit_tok = permit_res.json()["permit_token"]

            # First use -> increments to 1
            r1 = sandbox.execute_with_gateway(permit_tok, args_ok, str(org_id), workspace_id=str(ws1_id))
            assert r1["executed"] is True and sandbox.execution_counter == 1

            # Second use (replay) -> rejected, counter stays 1
            r2 = sandbox.execute_with_gateway(permit_tok, args_ok, str(org_id), workspace_id=str(ws1_id))
            assert r2["executed"] is False and "replay" in r2["reason"].lower() and sandbox.execution_counter == 1

            # Concurrent duplicate use of a fresh permit -> exactly 1 succeeds
            fresh_tok = issue_permit_token(sandbox.tool_name, args_ok, str(org_id), "agent-ws1", workspace_id=str(ws1_id))
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futs = [
                    pool.submit(sandbox.execute_with_gateway, fresh_tok, args_ok, str(org_id), str(ws1_id))
                    for _ in range(4)
                ]
                results = [f.result() for f in futs]
            assert sum(1 for r in results if r["executed"]) == 1
            assert sandbox.execution_counter == 2

            # Expired, wrong-tool, and wrong-workspace permits -> rejected
            expired_tok = issue_permit_token(sandbox.tool_name, args_ok, str(org_id), "agent-ws1", workspace_id=str(ws1_id), ttl_seconds=-5)
            assert sandbox.execute_with_gateway(expired_tok, args_ok, str(org_id), str(ws1_id))["executed"] is False
            valid_tok2 = issue_permit_token(sandbox.tool_name, args_ok, str(org_id), "agent-ws1", workspace_id=str(ws1_id))
            assert sandbox.execute_with_gateway(valid_tok2, args_ok, str(org_id), str(ws1_id), tool_name="other_tool")["executed"] is False
            assert sandbox.execute_with_gateway(valid_tok2, args_ok, str(org_id), str(ws2_id))["executed"] is False
            assert sandbox.execution_counter == 2

            # Production secret guard
            monkeypatch.setenv("ENVIRONMENT", "production")
            monkeypatch.delenv("TRULIN_MCP_PERMIT_SECRET", raising=False)
            with pytest.raises(RuntimeError):
                issue_permit_token(sandbox.tool_name, args_ok, str(org_id), "agent-ws1")
            monkeypatch.delenv("ENVIRONMENT", raising=False)

            # Verify telemetry recorded denials without raw tokens
            tel_events = mcp_telemetry_service.get_events(limit=30)
            serialized = json.dumps([e.model_dump(mode="json") for e in tel_events])
            assert tok_ws1.token not in serialized
            assert permit_tok not in serialized

        # 4. Real Separate-Process MCP Client (uvicorn + mcp_stdio.py subprocess over stdin/stdout)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env = os.environ.copy()
        env["CONTEXT_LAYER_API_URL"] = f"http://127.0.0.1:{port}/v1/mcp"
        # Separate uvicorn process uses its own in-memory MCPTokenService (seeded tokens only)
        env["TRULIN_MCP_TOKEN"] = "trulin_mcp_claude_live_9a8b7c6d5e4f"

        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        try:
            # Wait for server readiness
            deadline = time.time() + 15
            ready = False
            while time.time() < deadline:
                try:
                    if httpx.get(f"http://127.0.0.1:{port}/v1/mcp/manifest", timeout=1.0).status_code == 200:
                        ready = True
                        break
                except Exception:
                    time.sleep(0.25)
            assert ready, "Separate uvicorn process failed to start"

            stdio_script = os.path.join(backend_dir, "mcp_stdio.py")
            rpc_requests = [
                {"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
                {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
                {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_trusted_context", "arguments": {"query": "travel cap"}}, "id": 3},
                {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_evaluate_decision", "arguments": {"action_type": "Approve $5000 travel", "actor_id": "agent-ws1"}}, "id": 4},
                {"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "context://claims/verified"}, "id": 5},
            ]
            stdin_payload = "\n".join(json.dumps(r) for r in rpc_requests) + "\n"
            stdio_proc = subprocess.run(
                [sys.executable, stdio_script],
                input=stdin_payload,
                text=True,
                capture_output=True,
                cwd=backend_dir,
                env=env,
                timeout=20,
            )
            assert stdio_proc.returncode == 0
            stdout_lines = [ln for ln in stdio_proc.stdout.splitlines() if ln.strip()]
            assert len(stdout_lines) == 5, f"Expected 5 clean JSON-RPC lines, got {len(stdout_lines)}: {stdio_proc.stdout}"
            responses = [json.loads(ln) for ln in stdout_lines]
            assert responses[0]["result"]["serverInfo"]["name"] == "context-trust-layer"
            assert len(responses[1]["result"]["tools"]) >= 7
            ctx_stdio = json.loads(responses[2]["result"]["content"][0]["text"])
            assert ctx_stdio["status"] == "success"
            assert "abstained" in ctx_stdio
            adv_stdio = json.loads(responses[3]["result"]["content"][0]["text"])
            assert adv_stdio["execution_status"] == "Not executed by Trulin"
            res_stdio = json.loads(responses[4]["result"]["contents"][0]["text"])
            assert isinstance(res_stdio, list)
        finally:
            server_proc.terminate()
            server_proc.wait(timeout=5)
    finally:
        mcp_token_service.revoke_token(tok_ws1.id)
        async with AsyncSessionLocal() as session:
            # Clean up folders before org cascade (folders self-FK has RESTRICT)
            await session.execute(delete(Folder).where(Folder.id == ws1_child_id))
            await session.execute(delete(Folder).where(Folder.organization_id == org_id))
            await session.execute(delete(Organization).where(Organization.id == org_id))
            await session.commit()
