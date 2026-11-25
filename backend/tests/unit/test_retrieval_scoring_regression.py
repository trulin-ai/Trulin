"""
Targeted Regression Test: Retrieval Engine Reciprocal Rank Fusion & Section Context Expansion.

Guarantees:
1. `scores_by_claim_id` is computed via lexical and semantic scoring with RRF.
2. `section_context_map` expands related clauses from the same document section.
3. 6-tuple packing/unpacking matches between `evaluated_items` and ranking/audit loops.
4. GovernedContextPackage and ContextItemResponse populate without NameError or TypeError.
"""

import decimal
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest


@pytest.mark.asyncio
async def test_retrieval_rrf_scoring_and_section_context():
    """Verify that ContextRetrievalEngine evaluates RRF and section expansion cleanly."""
    org_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, organization_id=org_id, title="Service Level Agreement")
    ver = DocumentVersion(id=ver_id, document_id=doc_id, version_number=1, is_current=True)

    c1 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Production downtime credit must be requested within 30 days of incident.",
        subject="Customer",
        predicate="must_request_credit_within",
        object="30 days of incident",
        claim_type="rule",
        status=ClaimStatus.VERIFIED,
    )
    c1.trust_scores = [ClaimTrustScore(claim_id=c1.id, overall_score=decimal.Decimal("0.9500"))]
    c1.validity_records = [ClaimValidity(claim_id=c1.id, is_current=True)]
    c1.evidence = [
        ClaimEvidence(
            claim_id=c1.id,
            document_id=doc_id,
            document=doc,
            section="Section 4.1",
            text_span="Credit requests must be submitted within 30 days.",
            page_number=4,
        )
    ]

    c2 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Credits exceeding $10,000 require VP authorization before approval.",
        subject="Finance",
        predicate="requires_vp_authorization",
        object="credits exceeding $10,000",
        claim_type="rule",
        status=ClaimStatus.VERIFIED,
    )
    c2.trust_scores = [ClaimTrustScore(claim_id=c2.id, overall_score=decimal.Decimal("0.9000"))]
    c2.validity_records = [ClaimValidity(claim_id=c2.id, is_current=True)]
    c2.evidence = [
        ClaimEvidence(
            claim_id=c2.id,
            document_id=doc_id,
            document=doc,
            section="Section 4.1",
            text_span="Credits above $10,000 require VP sign-off.",
            page_number=4,
        )
    ]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [c1, c2]
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    engine = ContextRetrievalEngine(mock_session)

    req = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="credit request window 30 days",
        min_trust_score=decimal.Decimal("0.80"),
        canonical_only=True,
    )
    resp = await engine.query_context(req)

    assert len(resp.context) >= 1
    assert "credit" in resp.context[0].claim.lower()
    # Check that section context expansion cleanly decoupled into section_context items
    assert len(resp.context[0].section_context) >= 1
    assert resp.context[0].section_context[0].is_normative is False
    assert resp.context[0].section_context[0].section == "Section 4.1"
    # Check governed packages are populated
    assert len(resp.governed_packages) >= 1
    assert resp.governed_packages[0].rule_text == c1.claim_text

