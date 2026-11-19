import decimal
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document_version import DocumentVersion
from app.db.models.hitl_escalation import HitlEscalation
from app.schemas.claim import ClaimResponse
from app.services.claim_clustering_engine import ClaimClusteringEngine

router = APIRouter(prefix="/review", tags=["review"])


class ClaimReviewActionRequest(BaseModel):
    action: Literal["approve", "reject", "edit", "escalate"] = Field(
        ...,
        description="Review action: approve, reject, edit, or escalate",
    )
    edited_claim_text: Optional[str] = Field(default=None, description="Replacement claim text (for edit action)")
    edited_subject: Optional[str] = Field(default=None, description="Replacement normalized subject (for edit action)")
    edited_predicate: Optional[str] = Field(default=None, description="Replacement predicate (for edit action)")
    edited_object: Optional[str] = Field(default=None, description="Replacement object (for edit action)")
    reviewer_id: Optional[uuid.UUID] = Field(default=None, description="Identifier of human reviewer")
    reviewer_notes: Optional[str] = Field(default=None, description="Review justification / audit remarks")
    escalation_reason: Optional[str] = Field(default=None, description="Reason for escalation to HITL queue")


class BatchPatternActionRequest(BaseModel):
    action: Literal["approve", "reject", "hold", "escalate"] = Field(
        ...,
        description="Batch action: approve, reject, hold, or escalate",
    )
    selected_claim_ids: Optional[list[uuid.UUID]] = Field(
        default=None,
        description="Explicit subset of claim IDs to mutate. If omitted, applies to all claims in the cluster.",
    )
    reviewer_id: Optional[uuid.UUID] = Field(default=None, description="Identifier of human reviewer")
    reviewer_notes: Optional[str] = Field(default=None, description="Review justification / audit remarks")


class BatchRevertRequest(BaseModel):
    batch_id: str = Field(..., description="UUID of batch transaction to revert")


class ClaimReviewSummaryResponse(BaseModel):
    organization_id: str
    total_queued_for_review: int
    approved_claims_count: int
    rejected_claims_count: int
    superseded_claims_count: int
    review_throughput_rate: float


@router.get("/queue", response_model=list[ClaimResponse])
async def list_review_queue(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    document_id: Optional[uuid.UUID] = Query(None, description="Optional document filter"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns candidate claims queued for human triage and review
    (status == CANDIDATE, low confidence, or unnormalized/ambiguous).
    """
    conditions = [
        Claim.organization_id == organization_id,
        Claim.status == ClaimStatus.CANDIDATE,
    ]

    stmt = (
        select(Claim)
        .order_by(Claim.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(Claim.evidence),
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
        )
    )

    if document_id is not None:
        stmt = stmt.join(DocumentVersion, Claim.document_version_id == DocumentVersion.id).where(
            DocumentVersion.document_id == document_id,
            *conditions,
        )
    else:
        stmt = stmt.where(*conditions)

    result = await db.execute(stmt)
    claims = result.scalars().all()
    return [ClaimResponse.model_validate(c) for c in claims]


@router.get("/summary", response_model=ClaimReviewSummaryResponse)
async def get_review_summary(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
):
    """Returns real-time counts and metrics for the human review queue."""
    counts_stmt = (
        select(Claim.status, func.count(Claim.id))
        .where(Claim.organization_id == organization_id)
        .group_by(Claim.status)
    )
    res = await db.execute(counts_stmt)
    status_map = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in res.all()}

    queued = status_map.get("candidate", 0)
    approved = status_map.get("verified", 0) + status_map.get("active", 0)
    rejected = status_map.get("rejected", 0)
    superseded = status_map.get("superseded", 0)

    total_reviewed = approved + rejected
    total_all = queued + total_reviewed
    throughput = round(float(total_reviewed / total_all) if total_all > 0 else 0.0, 4)

    return ClaimReviewSummaryResponse(
        organization_id=str(organization_id),
        total_queued_for_review=queued,
        approved_claims_count=approved,
        rejected_claims_count=rejected,
        superseded_claims_count=superseded,
        review_throughput_rate=throughput,
    )


# ─── PATTERN APPROVAL BOARD (10-MINUTE EXTREME BATCH ADJUDICATION) ───────

@router.get("/patterns")
async def list_claim_patterns(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    document_id: Optional[uuid.UUID] = Query(None, description="Optional document filter"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Clusters candidate claims into ~30-45 high-leverage policy patterns for 10-minute batch review.
    Returns categorized patterns, representative quotes, confidence tiers, and triage burn-down summary.
    """
    return await ClaimClusteringEngine.cluster_candidate_claims(
        db=db,
        organization_id=organization_id,
        document_id=document_id,
    )


@router.get("/patterns/{pattern_id}/claims")
async def list_pattern_claims(
    pattern_id: str,
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    document_id: Optional[uuid.UUID] = Query(None, description="Optional document filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieves all individual claims within a cluster for outlier inspection and pre-selection checkboxes.
    """
    return await ClaimClusteringEngine.get_pattern_claims(
        db=db,
        pattern_id=pattern_id,
        organization_id=organization_id,
        document_id=document_id,
    )


@router.post("/patterns/{pattern_id}/action")
async def execute_pattern_batch_action(
    pattern_id: str,
    req: BatchPatternActionRequest,
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Executes a reversible batch triage action across all selected claims in a pattern.
    Applies canonical normalization, trust boost, validity records, and records a reversible transaction.
    """
    return await ClaimClusteringEngine.apply_batch_pattern_action(
        db=db,
        pattern_id=pattern_id,
        action=req.action,
        organization_id=organization_id,
        reviewer_id=req.reviewer_id,
        reviewer_notes=req.reviewer_notes,
        selected_claim_ids=req.selected_claim_ids,
    )


@router.post("/patterns/batch_revert")
async def revert_batch_action(
    req: BatchRevertRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Reverts a batch transaction, restoring claims to their candidate state.
    """
    return await ClaimClusteringEngine.revert_batch_transaction(
        db=db,
        batch_id=req.batch_id,
    )


# ─── INDIVIDUAL CLAIM TRIAGE ACTIONS ─────────────────────────────────────

@router.post("/{claim_id}/action", response_model=ClaimResponse)
async def execute_claim_review_action(
    claim_id: uuid.UUID,
    req: ClaimReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes an individual triage action (approve, reject, edit, escalate) on a queued candidate claim.
    """
    stmt = (
        select(Claim)
        .where(Claim.id == claim_id)
        .options(
            selectinload(Claim.evidence),
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
        )
    )
    claim = (await db.execute(stmt)).scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    now = datetime.now(timezone.utc)

    # 1. Action: APPROVE
    if req.action == "approve":
        claim.status = ClaimStatus.VERIFIED
        claim.updated_at = now

        for score in claim.trust_scores:
            score.human_score = decimal.Decimal("1.0")
            score.overall_score = decimal.Decimal(str(min(round(float(score.overall_score) + 0.15, 4), 1.0)))
            score.calculated_at = now

        for val in claim.validity_records:
            val.is_current = True
            val.validity_status = "verified"

    # 2. Action: REJECT
    elif req.action == "reject":
        claim.status = ClaimStatus.REJECTED
        claim.updated_at = now

        for val in claim.validity_records:
            val.is_current = False
            val.validity_status = "rejected"

    # 3. Action: EDIT
    elif req.action == "edit":
        if req.edited_claim_text:
            claim.claim_text = req.edited_claim_text
        if req.edited_subject:
            claim.subject = req.edited_subject[:255]
        if req.edited_predicate:
            claim.predicate = req.edited_predicate[:255]
        if req.edited_object:
            claim.object = req.edited_object

        claim.status = ClaimStatus.VERIFIED
        claim.updated_at = now

        for score in claim.trust_scores:
            score.human_score = decimal.Decimal("1.0")
            score.overall_score = decimal.Decimal(str(min(round(float(score.overall_score) + 0.20, 4), 1.0)))
            score.calculated_at = now

        for val in claim.validity_records:
            val.is_current = True
            val.validity_status = "verified"

    # 4. Action: ESCALATE
    elif req.action == "escalate":
        escalation = HitlEscalation(
            organization_id=claim.organization_id,
            audit_id=str(claim.id),
            actor_id=str(req.reviewer_id or "reviewer"),
            actor_role="Senior Compliance Reviewer",
            action_prompt=f"Review ambiguous claim: '{claim.claim_text}' (Subject: {claim.subject}, Predicate: {claim.predicate})",
            reasons=[req.escalation_reason or "Ambiguous claim subject, value, or predicate requires policy author escalation."],
            category="Claim Triage Escalation",
            liability_prevented_usd=500.0,
            status="PENDING_REVIEW",
        )
        db.add(escalation)

    await db.commit()
    await db.refresh(claim)
    return ClaimResponse.model_validate(claim)


@router.get("/certification/ae3/reconciliation")
async def get_ae3_reconciliation_report() -> dict[str, Any]:
    """Retrieve Sprint AE-3 Trust-Tiered Certification reconciliation report and quality gate scorecard."""
    import json
    from pathlib import Path
    report_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "research" / "certification_ae3" / "reconciliation_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AE-3 reconciliation report not found.")
    return json.loads(report_path.read_text(encoding="utf-8"))


@router.get("/certification/ae3/metrics")
async def get_ae3_dashboard_metrics() -> dict[str, Any]:
    """Retrieve real-time Sprint AE-3 continuous dashboard metrics."""
    import json
    from pathlib import Path
    report_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "research" / "certification_ae3" / "reconciliation_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AE-3 reconciliation report not found.")
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return data.get("dashboard_metrics", {})
