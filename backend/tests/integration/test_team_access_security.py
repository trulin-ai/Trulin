"""
Security, RBAC, Tenant Isolation & Lifecycle Tests for Team & Access (/v1/users*, /v1/auth/capabilities).
"""

import uuid
import pytest
import httpx
from sqlalchemy import delete, select

from app.main import app
from app.core.security import create_access_token
from app.db.database import AsyncSessionLocal
from app.db.enums import RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.models.user_activity import UserActivityLog


@pytest.mark.anyio
async def test_team_access_security_rbac_isolation_and_lifecycle():
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    admin_a_id = uuid.uuid4()
    viewer_a_id = uuid.uuid4()
    admin_b_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        session.add_all([
            Organization(id=org_a_id, name="Team Org A", slug=f"team-a-{org_a_id.hex[:8]}"),
            Organization(id=org_b_id, name="Team Org B", slug=f"team-b-{org_b_id.hex[:8]}"),
        ])
        await session.flush()

        session.add_all([
            User(
                id=admin_a_id,
                organization_id=org_a_id,
                name="Admin A",
                email=f"admin-a-{admin_a_id.hex[:8]}@t.test",
                role=UserRole.ADMIN,
                status=RecordStatus.ACTIVE,
                active_session_id="sess_admin_a",
            ),
            User(
                id=viewer_a_id,
                organization_id=org_a_id,
                name="Viewer A",
                email=f"viewer-a-{viewer_a_id.hex[:8]}@t.test",
                role=UserRole.VIEWER,
                status=RecordStatus.ACTIVE,
                active_session_id="sess_viewer_a",
            ),
            User(
                id=admin_b_id,
                organization_id=org_b_id,
                name="Admin B",
                email=f"admin-b-{admin_b_id.hex[:8]}@t.test",
                role=UserRole.ADMIN,
                status=RecordStatus.ACTIVE,
            ),
        ])
        await session.commit()

    token_admin_a = create_access_token(str(admin_a_id), {"org_id": str(org_a_id), "role": "admin", "session_id": "sess_admin_a"})
    token_viewer_a = create_access_token(str(viewer_a_id), {"org_id": str(org_a_id), "role": "viewer", "session_id": "sess_viewer_a"})
    headers_admin_a = {"Authorization": f"Bearer {token_admin_a}"}
    headers_viewer_a = {"Authorization": f"Bearer {token_viewer_a}"}

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unauthenticated requests -> 401
            assert (await client.get("/v1/users")).status_code == 401
            assert (await client.patch(f"/v1/users/{viewer_a_id}", json={"role": "admin"})).status_code == 401
            assert (await client.delete(f"/v1/users/{viewer_a_id}")).status_code == 401
            assert (await client.get("/v1/users/activity")).status_code == 401
            assert (await client.get("/v1/users/domains")).status_code == 401
            assert (await client.get("/v1/auth/capabilities")).status_code == 401

            # 2. Viewer RBAC enforcement -> 403
            r_v_patch = await client.patch(f"/v1/users/{viewer_a_id}", json={"role": "admin"}, headers=headers_viewer_a)
            assert r_v_patch.status_code == 403
            r_v_del = await client.delete(f"/v1/users/{viewer_a_id}", headers=headers_viewer_a)
            assert r_v_del.status_code == 403
            r_v_act = await client.get("/v1/users/activity", headers=headers_viewer_a)
            assert r_v_act.status_code == 403

            # 3. Capabilities endpoint returns canonical roles & server-computed flags
            r_cap = await client.get("/v1/auth/capabilities", headers=headers_admin_a)
            assert r_cap.status_code == 200
            cap_data = r_cap.json()
            assert cap_data["capabilities"]["can_change_roles"] is True
            assert "compliance_officer" in cap_data["roles"]
            assert "auditor" in cap_data["roles"]

            # 4. Cross-organization access denied -> 403
            assert (await client.get(f"/v1/users?organization_id={org_b_id}", headers=headers_admin_a)).status_code == 403
            assert (await client.patch(f"/v1/users/{admin_b_id}", json={"role": "viewer"}, headers=headers_admin_a)).status_code == 403
            assert (await client.get(f"/v1/users/activity?organization_id={org_b_id}", headers=headers_admin_a)).status_code == 403

            # 5. Admin changes viewer role -> 200 + audited
            r_role = await client.patch(
                f"/v1/users/{viewer_a_id}",
                json={"role": "reviewer", "reason": "Access review"},
                headers=headers_admin_a,
            )
            assert r_role.status_code == 200
            assert r_role.json()["role"] == "reviewer"

            # 6. Last active admin cannot be demoted or deactivated -> 400
            assert (await client.patch(f"/v1/users/{admin_a_id}", json={"role": "viewer"}, headers=headers_admin_a)).status_code == 400
            assert (await client.delete(f"/v1/users/{admin_a_id}", headers=headers_admin_a)).status_code == 400

            # 7. Deactivate viewer -> 204, token rejected (403), audit history retained
            r_deact = await client.delete(f"/v1/users/{viewer_a_id}?reason=Offboarding", headers=headers_admin_a)
            assert r_deact.status_code == 204
            assert (await client.get("/v1/users", headers=headers_viewer_a)).status_code == 403

            r_act = await client.get("/v1/users/activity", headers=headers_admin_a)
            assert r_act.status_code == 200
            actions = [a["action_type"] for a in r_act.json()["activities"]]
            assert "ROLE_UPDATED" in actions
            assert "MEMBER_DEACTIVATED" in actions

            # 8. Domains endpoint returns real org-scoped structure
            r_dom = await client.get("/v1/users/domains", headers=headers_admin_a)
            assert r_dom.status_code == 200
            assert r_dom.json()["organization_id"] == str(org_a_id)
            assert r_dom.json()["is_preview"] is False

        # Verify DB state: viewer is DEACTIVATED with active_session_id cleared, Admin B untouched
        async with AsyncSessionLocal() as session:
            v = (await session.execute(select(User).where(User.id == viewer_a_id))).scalar_one()
            assert v.status == RecordStatus.DEACTIVATED
            assert v.active_session_id is None
            b = (await session.execute(select(User).where(User.id == admin_b_id))).scalar_one()
            assert b.organization_id == org_b_id
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(UserActivityLog).where(UserActivityLog.organization_id.in_([org_a_id, org_b_id])))
            await session.execute(delete(User).where(User.organization_id.in_([org_a_id, org_b_id])))
            await session.execute(delete(Organization).where(Organization.id.in_([org_a_id, org_b_id])))
            await session.commit()
