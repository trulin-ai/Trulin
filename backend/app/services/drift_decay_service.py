import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.document import Document
from app.db.models.human_review import HumanReview
from app.db.models.user_activity import UserActivityLog
from app.schemas.drift import (
    AttestationPolicyConfig,
    AttestationRecord,
    ClaimDecayItem,
    ClaimRemediateRequest,
    ClaimRemediateResponse,
    DriftAnalysisResponse,
)

logger = logging.getLogger(__name__)

# Resilient in-memory fallback store for demo & offline mode
_IN_MEMORY_DRIFT_CLAIMS: Dict[str, Dict[str, Any]] = {}


def _calculate_decay(age_days: int, initial_trust: float) -> Tuple[float, float, str, str]:
    """Computes decayed trust, decay percentage, drift category, and recommended governance action.

    Note: Freshness factor is an advisory time-based signal. It does NOT automatically mutate or invalidate
    a claim's legal certification_status.
    """
    if age_days <= 30:
        factor = 1.00
        category = "ACTIVE_FRESH"
        action = "None: Knowledge is current and authoritative."
    elif age_days <= 90:
        factor = 0.92
        category = "AGING_WARNING"
        action = "Monitor: Policy approaches 90-day review horizon."
    elif age_days <= 180:
        factor = 0.75
        category = "STALE_TEMPORAL"
        action = "Re-Attest: Request Data Owner verification to renew freshness."
    else:
        factor = 0.50
        category = "SEVERELY_DECAYED"
        action = "Urgent: Retire or replace expired policy claim."

    current_trust = round(initial_trust * factor, 2)
    decay_pct = round((1.0 - factor) * 100.0, 1)
    return current_trust, decay_pct, category, action


def _seed_drift_claims_if_empty(org_id: uuid.UUID):
    org_key = str(org_id)
    existing = [c for c in _IN_MEMORY_DRIFT_CLAIMS.values() if c["organization_id"] == org_key]
    if not existing:
        now = datetime.now(timezone.utc)
        items = [
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555551"),
                "organization_id": org_key,
                "claim_text": "Refund processing window is strictly limited to 30 calendar days from delivery.",
                "document_title": "Customer Returns & Refund Policy 2026",
                "created_at": now - timedelta(days=15),
                "initial_trust": 0.95,
                "status": "VERIFIED",
                "certification_status": "CERTIFIED",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555552"),
                "organization_id": org_key,
                "claim_text": "Remote work internet stipends are disbursed automatically on the first pay cycle of employment.",
                "document_title": "Employee Handbook (Global Remote Guidelines)",
                "created_at": now - timedelta(days=48),
                "initial_trust": 0.90,
                "status": "VERIFIED",
                "certification_status": "CERTIFIED",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555553"),
                "organization_id": org_key,
                "claim_text": "Purchase orders under $5,000 do not require dual-custody approval or C-level signature.",
                "document_title": "Procurement & Vendor Payment SOP v1.2",
                "created_at": now - timedelta(days=125),
                "initial_trust": 0.88,
                "status": "VERIFIED",
                "certification_status": "CERTIFIED",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555554"),
                "organization_id": org_key,
                "claim_text": "Production firewall port 8080 may remain open for external staging ingress without CISO change approval.",
                "document_title": "Legacy Cloud Infrastructure Runbook 2024",
                "created_at": now - timedelta(days=220),
                "initial_trust": 0.85,
                "status": "VERIFIED",
                "certification_status": "CERTIFIED",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
                "organization_id": org_key,
                "claim_text": "Data subject access requests (DSAR) must be fulfilled within 45 days under standard processing.",
                "document_title": "Privacy & GDPR Compliance Standard",
                "created_at": now - timedelta(days=98),
                "initial_trust": 0.92,
                "status": "VERIFIED",
                "certification_status": "CERTIFIED",
            },
        ]
        for it in items:
            _IN_MEMORY_DRIFT_CLAIMS[str(it["claim_id"])] = it


async def analyze_context_drift(
    organization_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> DriftAnalysisResponse:
    """Calculates temporal decay, stale claims, and context freshness index.

    Guarantees architectural separation:
    - freshness_score: time-based decay signal computed continuously by the system.
    - certification_status: formal legal/trust standing controlled exclusively by validation workflows.
    Even when a claim is SEVERELY_DECAYED, its certification status is preserved unless formally retired.
    """
    now = datetime.now(timezone.utc)
    decay_items: List[ClaimDecayItem] = []

    db_claims = []
    if session:
        try:
            stmt = (
                select(Claim)
                .where(Claim.organization_id == organization_id)
                .options(
                    selectinload(Claim.trust_scores),
                    selectinload(Claim.evidence),
                )
            )
            res = await session.execute(stmt)
            db_claims = res.scalars().all()
        except Exception as e:
            logger.debug(f"DB load failed for drift analysis, using fallback: {e}")

    if db_claims:
        for c in db_claims:
            created = c.created_at or now
            age_days = max(0, (now - created).days)
            init_trust = 0.90
            if c.trust_scores:
                init_trust = float(getattr(c.trust_scores[0], "overall_score", None) or getattr(c.trust_scores[0], "confidence_score", None) or 0.90)

            cur_trust, dec_pct, cat, rec_act = _calculate_decay(age_days, init_trust)
            fresh_score = round(cur_trust / max(0.01, init_trust), 2)
            doc_title = "Internal Knowledge Base"
            if c.evidence and len(c.evidence) > 0 and c.evidence[0].document:
                doc_title = c.evidence[0].document.title

            cert_status = (c.status.value if hasattr(c.status, "value") else str(c.status or "candidate")).upper()

            decay_items.append(
                ClaimDecayItem(
                    claim_id=c.id,
                    claim_text=c.claim_text,
                    document_title=doc_title,
                    created_at=created,
                    age_days=age_days,
                    initial_trust=init_trust,
                    current_decayed_trust=cur_trust,
                    freshness_score=fresh_score,
                    certification_status=cert_status,
                    decay_pct=dec_pct,
                    drift_category=cat,
                    recommended_action=rec_act,
                )
            )
    else:
        _seed_drift_claims_if_empty(organization_id)
        org_key = str(organization_id)
        raw_items = [c for c in _IN_MEMORY_DRIFT_CLAIMS.values() if c["organization_id"] == org_key]

        for r in raw_items:
            age_days = max(0, (now - r["created_at"]).days)
            cur_trust, dec_pct, cat, rec_act = _calculate_decay(age_days, r["initial_trust"])
            fresh_score = round(cur_trust / max(0.01, r["initial_trust"]), 2)

            # Check Attestation Expiry Horizon (> 90 days) & Source Revision Invalidation
            att_rec = r.get("attestation_record")
            if att_rec:
                att_exp = att_rec.get("expires_at") if isinstance(att_rec.get("expires_at"), datetime) else None
                if att_exp and att_exp < now:
                    cat = "EXPIRED_ATTESTATION_RE_EVALUATION"
                    rec_act = "Re-evaluate: 90-day attestation review horizon expired. Re-attest against active source version."
                    fresh_score = min(fresh_score, 0.60)
            if r.get("source_revised_after_attestation"):
                cat = "SOURCE_REVISION_RE_EVALUATION_REQUIRED"
                rec_act = "Re-evaluate: Source document revised since last attestation. Attestation invalidated."
                fresh_score = min(fresh_score, 0.55)

            decay_items.append(
                ClaimDecayItem(
                    claim_id=r["claim_id"],
                    claim_text=r["claim_text"],
                    document_title=r["document_title"],
                    created_at=r["created_at"],
                    age_days=age_days,
                    initial_trust=r["initial_trust"],
                    current_decayed_trust=cur_trust,
                    freshness_score=fresh_score,
                    certification_status=r.get("certification_status", "CERTIFIED"),
                    decay_pct=dec_pct,
                    drift_category=cat,
                    recommended_action=rec_act,
                )
            )

    total_claims = len(decay_items)
    fresh_count = sum(1 for d in decay_items if d.drift_category == "ACTIVE_FRESH")
    decayed_count = total_claims - fresh_count
    avg_age = int(sum(d.age_days for d in decay_items) / max(1, total_claims))

    freshness_index = round(
        (sum(d.current_decayed_trust for d in decay_items) / max(1, sum(d.initial_trust for d in decay_items))) * 100.0,
        1,
    ) if decay_items else 100.0

    radar = {
        "<30d (Fresh)": sum(1 for d in decay_items if d.age_days <= 30),
        "30-90d (Aging)": sum(1 for d in decay_items if 30 < d.age_days <= 90),
        "90-180d (Stale)": sum(1 for d in decay_items if 90 < d.age_days <= 180),
        ">180d (Severely Decayed)": sum(1 for d in decay_items if d.age_days > 180),
    }

    stale_docs = len({d.document_title for d in decay_items if d.age_days > 90})

    return DriftAnalysisResponse(
        organization_id=organization_id,
        analyzed_at=now,
        total_claims=total_claims,
        fresh_claims_count=fresh_count,
        decayed_claims_count=decayed_count,
        stale_documents_count=stale_docs,
        average_age_days=avg_age,
        freshness_index_pct=freshness_index,
        decay_radar=radar,
        decayed_claims=sorted(decay_items, key=lambda x: x.age_days, reverse=True),
    )


def _normalize_version_str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).lower().lstrip("v").strip()
    parts = s.split(".")
    while len(parts) > 1 and parts[-1] == "0":
        parts.pop()
    return "v" + ".".join(parts)


async def remediate_claim_decay(
    req: ClaimRemediateRequest,
    session: Optional[AsyncSession] = None,
) -> ClaimRemediateResponse:
    """Remediates a decayed claim via explicit Data Owner Re-Attestation or Retirement.

    Re-Attestation Semantics:
    Creates a versioned governance attestation event recording:
    - attestation_id: unique event identifier
    - attester_id: acting data owner or auditor
    - attestation_decision: 'ATTESTED_VALID' or 'RETIRED_SUPERSEDED'
    - attestation_reason: documented justification
    - source_version: source document/policy version verified
    - expires_at: 90-day review horizon for subsequent re-attestation
    """
    now = datetime.now(timezone.utc)
    cid_str = str(req.claim_id)
    attestation_id = uuid.uuid4()
    attester_id = req.attester_id or uuid.UUID("22222222-2222-2222-2222-222222222222")

    action_clean = req.action.upper()
    if action_clean not in ("RE_ATTEST", "RETIRE"):
        action_clean = "RE_ATTEST"

    source_ver = req.source_version or "v1.0"
    evidence_ver = f"ev_{source_ver}"

    # Source Version & Access Validation: Attestation must reference the active governing source version
    if action_clean == "RE_ATTEST" and req.source_version:
        if session:
            stmt = select(Claim).where(Claim.id == req.claim_id).options(selectinload(Claim.document_version))
            res = await session.execute(stmt)
            claim_db = res.scalar_one_or_none()
            if claim_db and claim_db.document_version:
                expected_ver = str(claim_db.document_version.version_number)
                norm_req_ver = _normalize_version_str(req.source_version)
                norm_exp_ver = _normalize_version_str(expected_ver)
                if norm_req_ver != norm_exp_ver:
                    return ClaimRemediateResponse(
                        claim_id=req.claim_id,
                        action_taken="RE_ATTEST_REJECTED",
                        new_status="REQUIRES_RE_EVALUATION",
                        freshness_score=0.50,
                        certification_status=(claim_db.status.value if hasattr(claim_db.status, "value") else str(claim_db.status)).upper(),
                        new_trust_score=0.75,
                        message=f"Source version mismatch: Attestation specifies '{req.source_version}', but active policy document version is 'v{expected_ver}'. Attestation must review the active source.",
                        timestamp=now,
                        attestation_record=None,
                    )
        elif cid_str in _IN_MEMORY_DRIFT_CLAIMS:
            expected_ver = _IN_MEMORY_DRIFT_CLAIMS[cid_str].get("source_version", "v1.0")
            norm_req_ver = _normalize_version_str(req.source_version)
            norm_exp_ver = _normalize_version_str(expected_ver)
            if norm_req_ver != norm_exp_ver:
                return ClaimRemediateResponse(
                    claim_id=req.claim_id,
                    action_taken="RE_ATTEST_REJECTED",
                    new_status="REQUIRES_RE_EVALUATION",
                    freshness_score=0.50,
                    certification_status=_IN_MEMORY_DRIFT_CLAIMS[cid_str].get("certification_status", "CERTIFIED"),
                    new_trust_score=0.75,
                    message=f"Source version mismatch: Attestation specifies '{req.source_version}', but active policy document version is '{expected_ver}'. Attestation must review the active source.",
                    timestamp=now,
                    attestation_record=None,
                )

    domain_pack = req.domain_pack or "regulatory_policy"
    domain_defaults = {
        "financial_controls": {"horizon": 30, "mandatory": True, "grace": 7},
        "safety_compliance": {"horizon": 60, "mandatory": True, "grace": 14},
        "regulatory_policy": {"horizon": 90, "mandatory": True, "grace": 15},
        "hr_travel_expense": {"horizon": 90, "mandatory": True, "grace": 30},
        "engineering_docs": {"horizon": 120, "mandatory": False, "grace": 30},
        "general_faq": {"horizon": 180, "mandatory": False, "grace": 45},
    }
    pack_info = domain_defaults.get(domain_pack, {"horizon": 90, "mandatory": True, "grace": 15})
    horizon_days = req.review_horizon_days or pack_info["horizon"]
    grace_days = pack_info["grace"]
    is_mandatory = pack_info["mandatory"]

    policy_cfg = AttestationPolicyConfig(
        source_authority="governing_body",
        domain_pack=domain_pack,
        review_horizon_days=horizon_days,
        mandatory_reattestation=is_mandatory,
        grace_period_days=grace_days,
    )

    if action_clean == "RE_ATTEST":
        # Freshness reset only; certification standing maintained without illegal status mutation
        new_status = "ACTIVE"
        cert_status = "CERTIFIED"
        freshness_score = 1.00
        new_trust = 0.95
        decision = "ATTESTED_VALID"
        reason = req.reason or req.notes or "Data Owner re-attestation: verified current policy against active operations."
        expires_at = now + timedelta(days=horizon_days)
        msg = f"Claim successfully re-attested by Data Owner {attester_id} under policy '{domain_pack}'. Freshness window extended to {expires_at.date()} ({horizon_days}d horizon)."
    else:
        new_status = "SUPERSEDED"
        cert_status = "SUPERSEDED"
        freshness_score = 0.00
        new_trust = 0.00
        decision = "RETIRED_SUPERSEDED"
        reason = req.reason or req.notes or "Policy retired by compliance officer: superseded by new standard."
        expires_at = now
        msg = "Claim retired and marked SUPERSEDED: safely excluded from future autonomous agent RAG retrieval."

    attestation_record = AttestationRecord(
        attestation_id=attestation_id,
        claim_id=req.claim_id,
        attester_id=attester_id,
        attestation_decision=decision,
        attestation_reason=reason,
        source_version=source_ver,
        evidence_version=evidence_ver,
        attested_at=now,
        expires_at=expires_at,
        policy_config=policy_cfg,
    )

    # In-memory store update
    if cid_str in _IN_MEMORY_DRIFT_CLAIMS:
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["created_at"] = now if action_clean == "RE_ATTEST" else _IN_MEMORY_DRIFT_CLAIMS[cid_str]["created_at"]
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["status"] = new_status
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["certification_status"] = cert_status
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["initial_trust"] = new_trust
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["attestation_record"] = attestation_record.model_dump()
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["source_version"] = source_ver

    # DB persistence
    if session:
        try:
            stmt = select(Claim).where(Claim.id == req.claim_id)
            res = await session.execute(stmt)
            claim = res.scalar_one_or_none()
            if claim:
                if action_clean == "RETIRE":
                    claim.status = ClaimStatus.SUPERSEDED
                # Log immutable human review / attestation audit record
                org_id = claim.organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
                review_record = HumanReview(
                    id=attestation_id,
                    organization_id=org_id,
                    reviewer_id=attester_id,
                    target_type="claim_attestation",
                    target_id=req.claim_id,
                    decision=ReviewDecision.APPROVE if action_clean == "RE_ATTEST" else ReviewDecision.REJECT,
                    reason=f"[{decision}] {reason} (Expires: {expires_at.date()})",
                    previous_score=None,
                    new_score=None,
                    created_at=now,
                )
                session.add(review_record)

                activity_log = UserActivityLog(
                    organization_id=org_id,
                    user_id=attester_id,
                    user_name="Data Owner Attester",
                    user_role="data_owner",
                    action_type="CLAIM_RE_ATTESTED" if action_clean == "RE_ATTEST" else "CLAIM_RETIRED",
                    target_type="claim",
                    target_id=str(req.claim_id),
                    target_title=claim.claim_text[:60],
                    domain="Policy Lifecycle",
                    details={
                        "attestation_id": str(attestation_id),
                        "decision": decision,
                        "source_version": source_ver,
                        "expires_at": expires_at.isoformat(),
                        "reason": reason,
                    },
                    timestamp=now,
                )
                session.add(activity_log)
                await session.commit()
        except Exception as e:
            logger.warning(f"DB update/audit logging failed during claim remediation: {e}")

    return ClaimRemediateResponse(
        claim_id=req.claim_id,
        action_taken=action_clean,
        new_status=new_status,
        freshness_score=freshness_score,
        certification_status=cert_status,
        new_trust_score=new_trust,
        message=msg,
        timestamp=now,
        attestation_record=attestation_record,
    )
