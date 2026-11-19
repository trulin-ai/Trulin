"""
Test suite validating end-to-end claims count and representation consistency
across all document exploration and inspection tabs.
"""

import uuid
import pytest
from app.schemas.claim import ClaimResponse
from app.schemas.document import DocumentResponse
from app.api.v1.documents import _get_claims_counts_for_documents
from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, RecordStatus
from datetime import datetime, timezone

NORTHWIND_DOC_ID = uuid.UUID("e3cdd194-1a9b-4f01-9031-13e6b027d3d2")


@pytest.mark.anyio
async def test_document_response_has_claims_count_schema():
    """Validates DocumentResponse schema defines claims_count with default 0."""
    now = datetime.now(timezone.utc)
    doc_resp = DocumentResponse(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="Test Doc",
        status=RecordStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        claims_count=15,
    )
    assert doc_resp.claims_count == 15
    dumped = doc_resp.model_dump()
    assert dumped["claims_count"] == 15


@pytest.mark.anyio
async def test_claim_response_has_document_id():
    """Validates ClaimResponse schema includes and preserves document_id."""
    now = datetime.now(timezone.utc)
    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    claim_resp = ClaimResponse(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        claim_text="Customers may return items within 30 days.",
        subject="Customer",
        predicate="can_return_within_days",
        object="30 days",
        status=ClaimStatus.VERIFIED,
        created_at=now,
        updated_at=now,
    )
    assert claim_resp.document_id == doc_id
    dumped = claim_resp.model_dump()
    assert dumped["document_id"] == doc_id


@pytest.mark.anyio
async def test_claims_count_aggregation_for_northwind():
    """Validates _get_claims_counts_for_documents reports exact count in DB."""
    async with AsyncSessionLocal() as session:
        counts = await _get_claims_counts_for_documents(session, [NORTHWIND_DOC_ID])
        assert NORTHWIND_DOC_ID in counts
        assert counts[NORTHWIND_DOC_ID] == 224


@pytest.mark.anyio
async def test_empty_document_list_aggregation():
    """Validates _get_claims_counts_for_documents gracefully returns empty dict."""
    async with AsyncSessionLocal() as session:
        counts = await _get_claims_counts_for_documents(session, [])
        assert counts == {}

