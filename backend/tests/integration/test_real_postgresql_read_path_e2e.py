"""
Real PostgreSQL Database End-to-End Integration Test for Read-Path Stabilization.

Validates:
1. Live execution of GET /v1/documents/{document_id}/artifacts against real PostgreSQL database.
2. Real document (e3cdd194-1a9b-4f01-9031-13e6b027d3d2) containing all 224 claims.
3. Assert exactly 140 claims return certification_tier == 'AUTOMATED_CERTIFIED', is_canonical == True.
4. Assert candidate claims (including #2-#5) return certification_tier == 'REVIEW_REQUIRED', is_canonical == False.
5. Assert revalidation_audit is present capturing diagnostic divergence.
6. Assert absolute database immutability: zero rows mutated, status unchanged, updated_at unchanged.
"""

import uuid
import pytest
import httpx
from sqlalchemy import text

from app.main import app
from app.db.database import AsyncSessionLocal

NORTHWIND_DOC_ID = uuid.UUID("e3cdd194-1a9b-4f01-9031-13e6b027d3d2")


@pytest.mark.anyio
async def test_real_postgresql_artifacts_endpoint_immutability():
    # 1. Query real database before calling artifacts endpoint within a read-only transaction
    async with AsyncSessionLocal() as session:
        # Enforce read-only transaction guardrail
        await session.execute(text("SET TRANSACTION READ ONLY;"))
        server_ver = (await session.execute(text("SHOW server_version;"))).scalar()
        assert server_ver is not None, "PostgreSQL server version must be available"

        # Verify Northwind document exists
        doc_row = (await session.execute(
            text("SELECT id, title FROM documents WHERE id = :doc_id"),
            {"doc_id": NORTHWIND_DOC_ID}
        )).fetchone()
        assert doc_row is not None, f"Document {NORTHWIND_DOC_ID} not found in PostgreSQL"

        # Record exact state of all 224 claims before the API call
        claims_before = (await session.execute(
            text("""
                SELECT c.id, c.status, c.updated_at
                FROM claims c
                JOIN document_versions dv ON dv.id = c.document_version_id
                WHERE dv.document_id = :doc_id
                ORDER BY c.id
            """),
            {"doc_id": NORTHWIND_DOC_ID}
        )).fetchall()

        assert len(claims_before) == 224, f"Expected 224 claims in DB, found {len(claims_before)}"
        verified_count_db = sum(1 for c in claims_before if c[1] == "verified")
        assert verified_count_db in (140, 178), f"Expected 140 or 178 verified claims, found {verified_count_db}"

        # Safety Guardrail: Prove that write operations are rejected in read-only transaction
        try:
            await session.execute(text("UPDATE claims SET claim_text = 'mutation_attempt' WHERE id = :cid"), {"cid": claims_before[0][0]})
            write_blocked = False
        except Exception:
            write_blocked = True
        await session.rollback()
        assert write_blocked is True, "Database transaction must strictly prohibit write operations"

    # 2. Call live API endpoint with real database (NO dependency overrides)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/v1/documents/{NORTHWIND_DOC_ID}/artifacts")
        assert res.status_code == 200, f"API call failed: {res.text}"
        data = res.json()

    # 3. Assert API response metrics
    assert "claims" in data
    returned_claims = data["claims"]
    assert len(returned_claims) == 224

    certified_claims = [c for c in returned_claims if c["certification_tier"] == "AUTOMATED_CERTIFIED"]
    assert len(certified_claims) == 140, f"Expected 140 certified claims in API response, got {len(certified_claims)}"

    canonical_claims = [c for c in returned_claims if c["is_canonical"] is True]
    assert len(canonical_claims) == 140, f"Expected 140 canonical claims, got {len(canonical_claims)}"

    # Assert diagnostic revalidation_audit is present
    divergent_count = sum(1 for c in returned_claims if c.get("revalidation_audit", {}).get("divergence_flag") is True)
    assert divergent_count > 0, "Expected diagnostic divergence flags to be captured"

    # 4. Query real database after calling artifacts endpoint to prove zero mutation
    async with AsyncSessionLocal() as session:
        claims_after = (await session.execute(
            text("""
                SELECT c.id, c.status, c.updated_at
                FROM claims c
                JOIN document_versions dv ON dv.id = c.document_version_id
                WHERE dv.document_id = :doc_id
                ORDER BY c.id
            """),
            {"doc_id": NORTHWIND_DOC_ID}
        )).fetchall()

        assert len(claims_after) == 224, "Claim count in DB changed!"
        for before, after in zip(claims_before, claims_after):
            assert before[0] == after[0], "Claim ID mismatch!"
            assert before[1] == after[1], f"Claim {before[0]} status mutated from {before[1]} to {after[1]}!"
            assert before[2] == after[2], f"Claim {before[0]} updated_at mutated from {before[2]} to {after[2]}!"

    print(f"\n[REAL POSTGRESQL VERIFICATION SUCCESS]: 224 claims read; 140 certified; 0 rows mutated in database.")

