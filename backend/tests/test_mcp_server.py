import uuid
import pytest
import httpx
from sqlalchemy import delete
from app.main import app
from app.core.security import create_access_token
from app.db.database import AsyncSessionLocal
from app.db.enums import RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.user import User
from app.mcp.server import MCP_PROTOCOL_VERSION, MCP_TOOLS

ADMIN_MCP_HEADERS = {"Authorization": "Bearer trulin_mcp_claude_live_9a8b7c6d5e4f"}


@pytest.mark.anyio
async def test_mcp_manifest():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/mcp/manifest")
        assert res.status_code == 200
        data = res.json()
        assert data["schema_version"] == MCP_PROTOCOL_VERSION
        assert data["name"] == "context-trust-layer"
        assert "tools" in data["capabilities"]


@pytest.mark.anyio
async def test_mcp_tools_list():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/mcp/tools")
        assert res.status_code == 200
        data = res.json()
        assert "tools" in data
        assert len(data["tools"]) >= 4
        tool_names = [t["name"] for t in data["tools"]]
        assert "context_trust_get_trusted_context" in tool_names
        assert "context_trust_evaluate_decision" in tool_names
        assert "context_trust_search_claims" in tool_names
        assert "context_trust_check_conflicts" in tool_names


@pytest.mark.anyio
async def test_mcp_rest_invoke_evaluate_decision():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/mcp/invoke",
            headers=ADMIN_MCP_HEADERS,
            json={
                "tool": "context_trust_evaluate_decision",
                "arguments": {
                    "action_type": "customer_refund",
                    "actor_id": "88888888-8888-8888-8888-888888888888",
                    "actor_role": "billing_agent",
                    "parameters": {"amount": 5000, "customer_tier": "enterprise"}
                }
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["tool"] == "context_trust_evaluate_decision"
        assert "decision" in data["result"]
        assert data["result"]["execution_status"] == "Not executed by Trulin"


@pytest.mark.anyio
async def test_mcp_rest_invoke_search_claims():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/mcp/invoke",
            headers=ADMIN_MCP_HEADERS,
            json={
                "tool": "context_trust_search_claims",
                "arguments": {
                    "search_text": "refund",
                    "status": "all",
                    "limit": 5
                }
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "claims" in data["result"]


@pytest.mark.anyio
async def test_mcp_jsonrpc_initialize_and_tools():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 0. Unauthenticated JSON-RPC call must be rejected
        res_unauth = await client.post(
            "/v1/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 0}
        )
        assert res_unauth.status_code == 200
        assert res_unauth.json()["error"]["code"] == -32001

        # 1. Initialize
        res_init = await client.post(
            "/v1/mcp",
            headers=ADMIN_MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {},
                "id": 1
            }
        )
        assert res_init.status_code == 200
        data_init = res_init.json()
        assert data_init["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION

        # 2. tools/list
        res_list = await client.post(
            "/v1/mcp",
            headers=ADMIN_MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2
            }
        )
        assert res_list.status_code == 200
        data_list = res_list.json()
        assert len(data_list["result"]["tools"]) >= 4

        # 3. tools/call
        res_call = await client.post(
            "/v1/mcp",
            headers=ADMIN_MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "context_trust_check_conflicts",
                    "arguments": {
                        "claim_text": "Refund window is 90 days."
                    }
                },
                "id": 3
            }
        )
        assert res_call.status_code == 200
        data_call = res_call.json()
        assert data_call["result"]["isError"] is False
        assert len(data_call["result"]["content"]) > 0


@pytest.mark.anyio
async def test_mcp_ui_jwt_studio_access_and_protocol_audience_separation():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(Organization(id=org_id, name="UI Auth Org", slug=f"ui-org-{org_id.hex[:8]}"))
        await session.flush()
        session.add(User(
            id=user_id,
            organization_id=org_id,
            name="Studio Admin",
            email=f"studio-{user_id.hex[:8]}@trulin.test",
            role=UserRole.ADMIN,
            status=RecordStatus.ACTIVE,
        ))
        await session.commit()

    jwt_token = create_access_token(subject=str(user_id))
    ui_headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Studio / Control-plane endpoints accept valid Web User JWT
            res_tel = await client.get("/v1/mcp/telemetry?limit=10", headers=ui_headers)
            assert res_tel.status_code == 200

            res_tok = await client.get("/v1/mcp/tokens", headers=ui_headers)
            assert res_tok.status_code == 200

            res_inv = await client.post(
                "/v1/mcp/invoke",
                headers=ui_headers,
                json={"tool": "context_trust_evaluate_decision", "arguments": {"action_type": "refund", "actor_id": "ui-user"}},
            )
            assert res_inv.status_code == 200
            assert res_inv.json()["success"] is True

            # MCP protocol endpoint (/v1/mcp) MUST still reject Web User JWT (audience separation)
            res_rpc = await client.post(
                "/v1/mcp",
                headers=ui_headers,
                json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 99},
            )
            assert res_rpc.status_code == 200
            assert res_rpc.json()["error"]["code"] == -32001
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Organization).where(Organization.id == org_id))
            await session.commit()

