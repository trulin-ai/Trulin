"""
Integration test for Read-Path Certification Stabilization.

Verifies end-to-end API execution:
1. Calls GET /v1/documents/{document_id}/artifacts via ASGI AsyncClient.
2. Asserts persisted verified claim returns certification_tier == 'AUTOMATED_CERTIFIED' and is_canonical == True.
3. Asserts persisted candidate claim returns certification_tier == 'REVIEW_REQUIRED' and is_canonical == False.
4. Asserts revalidation_audit captures diagnostic live evaluation without mutating returned tier.
5. Asserts zero database mutations occurred during the read operation.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.main import app
from app.db.database import get_db
from app.db.enums import ClaimStatus


class MockTrustScore:
    overall_score = 0.95


class MockValidity:
    validity_status = "valid"


class MockEvidence:
    section = "Section 8. Refund Methods"
    text_span = "| Apple Pay / Google Pay | Underlying card | Same as card |"
    exact_quote = "| Apple Pay / Google Pay | Underlying card | Same as card |"


def make_mock_claim(claim_id, doc_ver_id, status, text, subj, pred, obj):
    c = MagicMock()
    c.id = claim_id
    c.document_version_id = doc_ver_id
    c.status = status
    c.claim_text = text
    c.subject = subj
    c.predicate = pred
    c.object = obj
    c.claim_type = "policy"
    c.claim_metadata = {}
    c.trust_scores = [MockTrustScore()]
    c.validity_records = [MockValidity()]
    c.evidence = [MockEvidence()]
    c.created_at = None
    return c


@pytest.mark.anyio
async def test_get_artifacts_read_path_stabilization_e2e():
    doc_id = uuid.uuid4()
    doc_ver_id = uuid.uuid4()
    org_id = uuid.uuid4()

    # Create mock document
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.organization_id = org_id
    mock_doc.title = "Northwind Policy"
    mock_doc.document_type = "policy"
    mock_doc.source_id = None
    mock_doc.external_id = "DOC-NW-01"
    mock_doc.content_hash = "hash_doc_123"
    mock_doc.content_uri = "Policy Content"
    mock_doc.created_at = None
    mock_doc.updated_at = None

    mock_version = MagicMock()
    mock_version.id = doc_ver_id
    mock_version.version_number = 1
    mock_version.content_uri = "Policy Content"
    mock_doc.versions = [mock_version]

    # Claim 1: Persisted VERIFIED claim
    verified_claim_id = uuid.uuid4()
    claim_verified = make_mock_claim(
        claim_id=verified_claim_id,
        doc_ver_id=doc_ver_id,
        status=ClaimStatus.VERIFIED,
        text="Refunds to Apple Pay post to underlying card.",
        subj="Apple Pay",
        pred="references_underlying_timeline",
        obj="Underlying card"
    )

    # Claim 2: Persisted CANDIDATE claim
    candidate_claim_id = uuid.uuid4()
    claim_candidate = make_mock_claim(
        claim_id=candidate_claim_id,
        doc_ver_id=doc_ver_id,
        status=ClaimStatus.CANDIDATE,
        text="Standard return window is 30 days.",
        subj="Return window",
        pred="has_return_window",
        obj="30 days"
    )

    claims_list = [claim_verified, claim_candidate]

    # Record initial database statuses before API call
    status_before_verified = claim_verified.status
    status_before_candidate = claim_candidate.status

    # Mock DB session execution
    mock_db = AsyncMock()

    # First execute: select Document
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_doc

    # Second execute: select Claims
    claims_result = MagicMock()
    claims_result.scalars.return_value.all.return_value = claims_list

    # Third execute: select Conflicts
    conflicts_result = MagicMock()
    conflicts_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [doc_result, claims_result, conflicts_result]

    # Execute GET /v1/documents/{id}/artifacts via ASGI AsyncClient with dependency override
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/v1/documents/{doc_id}/artifacts")
            assert res.status_code == 200, f"Artifacts endpoint failed: {res.text}"
            data = res.json()
    finally:
        app.dependency_overrides.clear()

    # 1. Assert Response Structure
    assert "claims" in data
    returned_claims = data["claims"]
    assert len(returned_claims) == 2

    # 2. Assert Verified Claim Properties
    c_ver = next(c for c in returned_claims if c["id"] == str(verified_claim_id))
    assert c_ver["status"] == "verified"
    assert c_ver["certification_tier"] == "AUTOMATED_CERTIFIED"
    assert c_ver["is_canonical"] is True
    assert c_ver["agent_accessible"] is True
    assert c_ver["all_9_gates_passed"] is True
    assert "revalidation_audit" in c_ver
    assert c_ver["revalidation_audit"]["persisted_tier"] == "AUTOMATED_CERTIFIED"

    # 3. Assert Candidate Claim Properties
    c_cand = next(c for c in returned_claims if c["id"] == str(candidate_claim_id))
    assert c_cand["status"] == "candidate"
    assert c_cand["certification_tier"] == "REVIEW_REQUIRED"
    assert c_cand["is_canonical"] is False
    assert c_cand["agent_accessible"] is False
    assert c_cand["all_9_gates_passed"] is False
    assert "revalidation_audit" in c_cand
    assert c_cand["revalidation_audit"]["persisted_tier"] == "REVIEW_REQUIRED"

    # 4. Assert Invariant: Revalidation Audit captures divergence without mutating returned tier
    assert "divergence_flag" in c_ver["revalidation_audit"]
    assert "live_tier" in c_ver["revalidation_audit"]

    # 5. Assert Zero Database Mutation
    assert claim_verified.status == status_before_verified
    assert claim_candidate.status == status_before_candidate
    assert mock_db.commit.call_count == 0, "Read endpoint must NEVER call db.commit()"
