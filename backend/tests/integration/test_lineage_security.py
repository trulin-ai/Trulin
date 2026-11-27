"""
Security, Scoping, Grounding & Bounded-Investigation Tests for /v1/lineage/*.

Covers:
1. Unauthenticated requests rejected with 401.
2. Cross-organization request rejected with 403; Org B cannot view Org A nodes/edges/blast-radius.
3. Same-organization, cross-workspace isolation (WS1 subtree vs sibling WS2).
4. Both-sides conflict validation: cross-workspace conflict (WS1 <-> WS2) is excluded from WS1.
5. Explicit claim_id decision grounding (inferred=False) vs legacy substring fallback (inferred=True).
6. Honest edge mutation endpoint returns 501 Not Implemented instead of false 200.
7. Bounded /v1/lineage/investigate contract (scope, summary, truncated, next_cursor, ranking_basis).
"""

import uuid
import pytest
import httpx
from sqlalchemy import delete

from app.main import app
from app.core.security import create_access_token
from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, UserRole
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.data_source import DataSource
from app.db.models.decision_evaluation import DecisionEvaluation
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.db.models.user import User


@pytest.mark.anyio
async def test_lineage_security_scoping_grounding_and_investigate_contract():
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    ws1_id = uuid.uuid4()
    ws1_child_id = uuid.uuid4()
    ws2_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        session.add_all([
            Organization(id=org_a_id, name="Lineage Org A", slug=f"lin-a-{org_a_id.hex[:8]}"),
            Organization(id=org_b_id, name="Lineage Org B", slug=f"lin-b-{org_b_id.hex[:8]}"),
        ])
        await session.flush()

        session.add_all([
            User(id=user_a_id, organization_id=org_a_id, name="Alice A", email=f"a-{user_a_id.hex[:8]}@t.test", role=UserRole.ADMIN, status=RecordStatus.ACTIVE),
            User(id=user_b_id, organization_id=org_b_id, name="Bob B", email=f"b-{user_b_id.hex[:8]}@t.test", role=UserRole.ADMIN, status=RecordStatus.ACTIVE),
        ])
        await session.flush()

        session.add_all([
            Folder(id=ws1_id, organization_id=org_a_id, name="WS1", depth=0),
            Folder(id=ws1_child_id, organization_id=org_a_id, parent_id=ws1_id, name="WS1 Child", depth=1),
            Folder(id=ws2_id, organization_id=org_a_id, name="WS2", depth=0),
        ])
        await session.flush()

        src_a = DataSource(id=uuid.uuid4(), organization_id=org_a_id, name="Confluence A", source_type="confluence", external_id=f"src-a-{org_a_id.hex[:6]}", status=RecordStatus.ACTIVE)
        src_b = DataSource(id=uuid.uuid4(), organization_id=org_b_id, name="Slack B", source_type="slack", external_id=f"src-b-{org_b_id.hex[:6]}", status=RecordStatus.ACTIVE)
        session.add_all([src_a, src_b])
        await session.flush()

        doc_ws1 = Document(id=uuid.uuid4(), organization_id=org_a_id, folder_id=ws1_id, source_id=src_a.id, title="WS1 Policy Doc", document_type="policy", content_hash="d1")
        doc_ws1c = Document(id=uuid.uuid4(), organization_id=org_a_id, folder_id=ws1_child_id, source_id=src_a.id, title="WS1 Child Doc", document_type="policy", content_hash="d1c")
        doc_ws2 = Document(id=uuid.uuid4(), organization_id=org_a_id, folder_id=ws2_id, source_id=src_a.id, title="WS2 Secret Doc", document_type="policy", content_hash="d2")
        doc_b = Document(id=uuid.uuid4(), organization_id=org_b_id, source_id=src_b.id, title="Org B Doc", document_type="policy", content_hash="db")
        session.add_all([doc_ws1, doc_ws1c, doc_ws2, doc_b])
        await session.flush()

        dv1 = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws1.id, version_number=1, content_hash="v1")
        dv1c = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws1c.id, version_number=1, content_hash="v1c")
        dv2 = DocumentVersion(id=uuid.uuid4(), document_id=doc_ws2.id, version_number=1, content_hash="v2")
        dvb = DocumentVersion(id=uuid.uuid4(), document_id=doc_b.id, version_number=1, content_hash="vb")
        session.add_all([dv1, dv1c, dv2, dvb])
        await session.flush()

        c_ws1 = Claim(id=uuid.uuid4(), organization_id=org_a_id, document_version_id=dv1.id, claim_text="WS1 refunds must be approved above $500.", subject="Refund", predicate="must_not_exceed", object="$500", claim_type="policy", status=ClaimStatus.VERIFIED)
        c_ws1c = Claim(id=uuid.uuid4(), organization_id=org_a_id, document_version_id=dv1c.id, claim_text="WS1 child refunds must be approved above $250.", subject="Refund", predicate="must_not_exceed", object="$250", claim_type="policy", status=ClaimStatus.VERIFIED)
        c_ws2 = Claim(id=uuid.uuid4(), organization_id=org_a_id, document_version_id=dv2.id, claim_text="WS2 executive refunds must be approved above $9000.", subject="Refund", predicate="must_not_exceed", object="$9000", claim_type="policy", status=ClaimStatus.VERIFIED)
        c_b = Claim(id=uuid.uuid4(), organization_id=org_b_id, document_version_id=dvb.id, claim_text="Org B expenses must be approved.", subject="Expense", predicate="requires", object="approval", claim_type="policy", status=ClaimStatus.VERIFIED)
        session.add_all([c_ws1, c_ws1c, c_ws2, c_b])
        await session.flush()

        session.add_all([
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws1.id, document_id=doc_ws1.id, text_span=c_ws1.claim_text, section="S1", page_number=1),
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws1c.id, document_id=doc_ws1c.id, text_span=c_ws1c.claim_text, section="S2", page_number=1),
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_ws2.id, document_id=doc_ws2.id, text_span=c_ws2.claim_text, section="S3", page_number=1),
            ClaimEvidence(id=uuid.uuid4(), claim_id=c_b.id, document_id=doc_b.id, text_span=c_b.claim_text, section="SB", page_number=1),
        ])

        cf_within = ClaimConflict(id=uuid.uuid4(), claim_a_id=c_ws1.id, claim_b_id=c_ws1c.id, conflict_type="contradiction", severity="high", confidence=0.95, resolution_status=ConflictStatus.DETECTED)
        cf_cross = ClaimConflict(id=uuid.uuid4(), claim_a_id=c_ws1.id, claim_b_id=c_ws2.id, conflict_type="contradiction", severity="high", confidence=0.95, resolution_status=ConflictStatus.DETECTED)
        session.add_all([cf_within, cf_cross])

        dec_explicit = DecisionEvaluation(
            id=uuid.uuid4(),
            audit_id=f"aud-exp-{org_a_id.hex[:6]}",
            organization_id=org_a_id,
            actor_id="agent-1",
            actor_role="support",
            decision_prompt="Refund $700",
            verdict="BLOCK",
            risk_level="HIGH",
            context_items=[{"claim": c_ws1.claim_text, "claim_id": str(c_ws1.id), "role": "supporting"}],
            audit_token="tok1",
        )
        dec_legacy = DecisionEvaluation(
            id=uuid.uuid4(),
            audit_id=f"aud-leg-{org_a_id.hex[:6]}",
            organization_id=org_a_id,
            actor_id="agent-2",
            actor_role="support",
            decision_prompt="Refund $300",
            verdict="ALLOW",
            risk_level="LOW",
            context_items=[{"claim": c_ws1c.claim_text}],
            audit_token="tok2",
        )
        session.add_all([dec_explicit, dec_legacy])
        await session.commit()

    headers_a = {"Authorization": f"Bearer {create_access_token(str(user_a_id))}"}
    headers_b = {"Authorization": f"Bearer {create_access_token(str(user_b_id))}"}

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unauthenticated -> 401
            assert (await client.get("/v1/lineage/graph")).status_code == 401
            assert (await client.get("/v1/lineage/investigate")).status_code == 401

            # 2. Cross-organization query -> 403
            res_cross_org = await client.get(f"/v1/lineage/investigate?organization_id={org_a_id}", headers=headers_b)
            assert res_cross_org.status_code == 403

            # Org B cannot access Org A's blast radius -> 404
            res_blast_b = await client.get(f"/v1/lineage/blast-radius/{c_ws1.id}", headers=headers_b)
            assert res_blast_b.status_code == 404

            # 3. Same-org, cross-workspace isolation + both-sides conflict check
            res_ws1 = await client.get(f"/v1/lineage/graph?workspace_id={ws1_id}", headers=headers_a)
            assert res_ws1.status_code == 200
            g_ws1 = res_ws1.json()
            node_ids = {n["id"] for n in g_ws1["nodes"]}
            assert f"doc_{doc_ws1.id}" in node_ids
            assert f"doc_{doc_ws1c.id}" in node_ids
            assert f"cl_{c_ws1.id}" in node_ids
            assert f"cl_{c_ws1c.id}" in node_ids
            assert f"cfl_{cf_within.id}" in node_ids
            # Sibling WS2 doc, claim, and cross-workspace conflict MUST NOT appear
            assert f"doc_{doc_ws2.id}" not in node_ids
            assert f"cl_{c_ws2.id}" not in node_ids
            assert f"cfl_{cf_cross.id}" not in node_ids
            # Org B nodes MUST NOT appear
            assert f"cl_{c_b.id}" not in node_ids

            # Blast radius for WS1 claim must exclude WS2 opposite claim
            res_blast_a = await client.get(f"/v1/lineage/blast-radius/{c_ws1.id}?workspace_id={ws1_id}", headers=headers_a)
            assert res_blast_a.status_code == 200
            opp_ids = {c["claim_id"] for c in res_blast_a.json()["conflicting_claims"]}
            assert str(c_ws1c.id) in opp_ids
            assert str(c_ws2.id) not in opp_ids

            # 4. Explicit decision_grounding vs labeled legacy inferred_grounding
            edges_by_target = {e["target"]: e for e in g_ws1["edges"] if str(e["target"]).startswith("dec_")}
            e_exp = edges_by_target.get(f"dec_{dec_explicit.id}")
            e_leg = edges_by_target.get(f"dec_{dec_legacy.id}")
            assert e_exp is not None and e_exp["type"] == "decision_grounding" and e_exp["inferred"] is False
            assert e_leg is not None and e_leg["type"] == "inferred_grounding" and e_leg["inferred"] is True

            # 5. Bounded /v1/lineage/investigate contract
            res_inv = await client.get(f"/v1/lineage/investigate?workspace_id={ws1_id}&mode=risk&limit=5", headers=headers_a)
            assert res_inv.status_code == 200
            inv = res_inv.json()
            assert inv["scope"]["organization_id"] == str(org_a_id)
            assert inv["scope"]["workspace_id"] == str(ws1_id)
            assert "snapshot_at" in inv["scope"]
            assert "node_counts" in inv["summary"]
            assert "risk_counts" in inv["summary"]
            assert "truncated" in inv
            assert "next_cursor" in inv
            assert inv["ranking_basis"] == "conflict_severity_and_trust"

            # 6. Honest edge mutation -> 501 Not Implemented
            res_mut = await client.post("/v1/lineage/edges/mutate", headers=headers_a, json={"added_edges": [], "severed_edge_ids": ["e1"]})
            assert res_mut.status_code == 501
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Folder).where(Folder.id == ws1_child_id))
            await session.execute(delete(Folder).where(Folder.organization_id == org_a_id))
            await session.execute(delete(Organization).where(Organization.id.in_([org_a_id, org_b_id])))
            await session.commit()
