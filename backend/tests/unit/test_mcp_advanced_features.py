import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_MCP_HEADERS = {"Authorization": "Bearer trulin_mcp_claude_live_9a8b7c6d5e4f"}


@pytest.mark.asyncio
async def test_mcp_manifest_contains_full_primitives():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/mcp/manifest")
        assert res.status_code == 200
        data = res.json()
        assert "tools" in data["capabilities"]
        assert "resources" in data["capabilities"]
        assert "prompts" in data["capabilities"]
        assert "sampling" in data["capabilities"]
        assert "/v1/mcp/sse" in data["endpoints"]["sse"]


@pytest.mark.asyncio
async def test_mcp_resources_and_prompts_discovery():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Resources
        res_r = await client.get("/v1/mcp/resources")
        assert res_r.status_code == 200
        data_r = res_r.json()
        assert len(data_r["resources"]) >= 4
        uris = [r["uri"] for r in data_r["resources"]]
        assert "context://claims/verified" in uris
        assert "context://policies/active" in uris

        # Read active policies resource
        read_res = await client.get(
            "/v1/mcp/resources/read?uri=context://policies/active",
            headers=ADMIN_MCP_HEADERS,
        )
        assert read_res.status_code == 200
        assert "refund_window_days" in read_res.json()["text"]

        # Prompts
        res_p = await client.get("/v1/mcp/prompts")
        assert res_p.status_code == 200
        data_p = res_p.json()
        assert len(data_p["prompts"]) >= 3
        prompt_names = [p["name"] for p in data_p["prompts"]]
        assert "governed_financial_decision" in prompt_names

        # Hydrate prompt
        eval_p = await client.post(
            "/v1/mcp/prompts/governed_financial_decision",
            headers=ADMIN_MCP_HEADERS,
            json={"action_description": "Issue customer discount", "amount_usd": 450}
        )
        assert eval_p.status_code == 200
        assert "Governed Autonomous Financial Agent" in eval_p.json()["messages"][0]["content"]["text"]


@pytest.mark.asyncio
async def test_mcp_jsonrpc_resources_and_prompts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # JSON-RPC resources/list
        res_list = await client.post(
            "/v1/mcp",
            headers=ADMIN_MCP_HEADERS,
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 101},
        )
        assert res_list.status_code == 200
        assert "resources" in res_list.json()["result"]

        # JSON-RPC prompts/list
        prompt_list = await client.post(
            "/v1/mcp",
            headers=ADMIN_MCP_HEADERS,
            json={"jsonrpc": "2.0", "method": "prompts/list", "id": 102},
        )
        assert prompt_list.status_code == 200
        assert "prompts" in prompt_list.json()["result"]


@pytest.mark.asyncio
async def test_mcp_telemetry_and_tokens():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Telemetry stats & events
        res_t = await client.get("/v1/mcp/telemetry", headers=ADMIN_MCP_HEADERS)
        assert res_t.status_code == 200
        data_t = res_t.json()
        assert "stats" in data_t
        assert "events" in data_t
        assert data_t["stats"]["total_invocations"] >= 1

        # Tokens list
        res_tok = await client.get("/v1/mcp/tokens", headers=ADMIN_MCP_HEADERS)
        assert res_tok.status_code == 200
        tokens = res_tok.json()["tokens"]
        assert len(tokens) >= 1

        # Create token
        create_res = await client.post("/v1/mcp/tokens", headers=ADMIN_MCP_HEADERS, json={
            "name": "Integration Test Agent Token",
            "agent_id": "test-agent-99",
            "role": "secops",
            "allowed_tools": ["context_trust_get_trusted_context"],
            "rate_limit_rpm": 60
        })
        assert create_res.status_code == 200
        new_token = create_res.json()
        assert new_token["token"].startswith("trulin_mcp_secops_")

        # Revoke token
        rev_res = await client.delete(f"/v1/mcp/tokens/{new_token['id']}", headers=ADMIN_MCP_HEADERS)
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_mcp_proxies_execution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List proxy tools
        res_p = await client.get("/v1/mcp/proxies")
        assert res_p.status_code == 200
        proxies = res_p.json()["tools"]
        assert len(proxies) >= 4

        # Execute safe proxy query (SELECT)
        exec_safe = await client.post("/v1/mcp/proxies/execute", headers=ADMIN_MCP_HEADERS, json={
            "tool_id": "tool-postgres-query",
            "arguments": {"query": "SELECT user_id, email FROM users LIMIT 10;"},
            "actor_id": "dev-bot",
            "actor_role": "developer"
        })
        assert exec_safe.status_code == 200
        assert exec_safe.json()["guardrail_verdict"] == "PERMIT"
        assert exec_safe.json()["simulated_output"] is not None

        # Execute destructive SQL proxy query (DROP TABLE)
        exec_bad = await client.post("/v1/mcp/proxies/execute", headers=ADMIN_MCP_HEADERS, json={
            "tool_id": "tool-postgres-query",
            "arguments": {"query": "DROP TABLE accounts CASCADE;"},
            "actor_id": "dev-bot",
            "actor_role": "developer"
        })
        assert exec_bad.status_code == 200
        assert exec_bad.json()["guardrail_verdict"] == "BLOCK"
        assert exec_bad.json()["liability_prevented_usd"] > 0
