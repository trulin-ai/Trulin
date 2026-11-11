"""
Layer 6: Enterprise Claim Store & Persistence.
Persists verified claims, cryptographic evidence, trust scores, and validity lineage into PostgreSQL.
"""

from __future__ import annotations

import decimal
import hashlib
import logging
import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, RecordStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.extraction.models import CandidateClaim
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.validation_gate.models import CandidateGateEvaluation, ClaimLifecycleDecision

logger = logging.getLogger(__name__)


def _generate_deterministic_claim_uuid(doc_version_id: uuid.UUID, candidate: CandidateClaim) -> uuid.UUID:
    """Generates a reproducible UUID from document version and candidate claim identity to enable idempotent upserts."""
    seed = f"{doc_version_id}:{(candidate.subject or '').strip().lower()}:{(candidate.predicate or '').strip().lower()}:{(candidate.object or '').strip().lower()}:{(candidate.claim_text or '').strip().lower()}"
    return uuid.uuid5(uuid.NAMESPACE_URL, seed)


class EnterpriseClaimStore:
    """Manages transactional persistence of claims into PostgreSQL."""

    @classmethod
    async def persist_evaluations(
        cls,
        evaluations: List[CandidateGateEvaluation],
        candidates_map: dict[str, CandidateClaim],
        envelope: CanonicalSourceEnvelope,
        session: Optional[AsyncSession] = None,
        document_version_id: Optional[uuid.UUID] = None,
    ) -> List[uuid.UUID]:
        """
        Persists a batch of gate-evaluated claims into PostgreSQL.
        Returns the list of persisted claim UUIDs.
        """
        if session is not None:
            return await cls._persist_with_session(
                evaluations, candidates_map, envelope, session, document_version_id=document_version_id
            )

        async with AsyncSessionLocal() as new_session:
            async with new_session.begin():
                persisted_ids = await cls._persist_with_session(
                    evaluations, candidates_map, envelope, new_session, document_version_id=document_version_id
                )
            return persisted_ids

    @classmethod
    async def _persist_with_session(
        cls,
        evaluations: List[CandidateGateEvaluation],
        candidates_map: dict[str, CandidateClaim],
        envelope: CanonicalSourceEnvelope,
        session: AsyncSession,
        document_version_id: Optional[uuid.UUID] = None,
    ) -> List[uuid.UUID]:
        persisted_ids: List[uuid.UUID] = []

        document = None
        doc_version = None

        # If document_version_id is explicitly supplied, look it up first
        if document_version_id:
            doc_version = await session.get(DocumentVersion, document_version_id)
            if doc_version:
                document = await session.get(Document, doc_version.document_id)

        # 1. Ensure Canonical Document and DocumentVersion exist if not resolved
        if not document:
            doc_stmt = select(Document).where(
                Document.organization_id == envelope.organization_id,
                Document.source_id == envelope.source_id,
                Document.external_id == envelope.asset_id,
            )
            doc_res = await session.execute(doc_stmt)
            document = doc_res.scalar_one_or_none()

        if not document:
            title = envelope.asset_id.split("/")[-1].split("#")[0] or "Untitled Document"
            document = Document(
                organization_id=envelope.organization_id,
                source_id=envelope.source_id,
                external_id=envelope.asset_id,
                title=title,
                document_type=envelope.native_format,
                domain="Enterprise",
                content_uri=envelope.asset_id,
                content_hash=envelope.content_hash,
                status=RecordStatus.ACTIVE,
            )
            session.add(document)
            await session.flush()

        # Find or create DocumentVersion
        if not doc_version:
            ver_stmt = select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.is_current.is_(True),
            )
            ver_res = await session.execute(ver_stmt)
            doc_version = ver_res.scalar_one_or_none()

        if not doc_version:
            doc_version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_uri=envelope.asset_id,
                content_hash=envelope.content_hash,
                is_current=True,
            )
            session.add(doc_version)
            await session.flush()

        # 2. Persist Claims and Supporting Records
        # Ensure idempotency for this document version by removing previous claim extractions
        await session.execute(
            delete(Claim).where(Claim.document_version_id == doc_version.id)
        )
        await session.flush()

        for eval_record in evaluations:
            candidate = candidates_map.get(eval_record.candidate_id)
            if not candidate:
                continue

            claim_uuid = _generate_deterministic_claim_uuid(doc_version.id, candidate)
            eval_record.persisted_claim_id = claim_uuid

            # Map Lifecycle Decision to DB ClaimStatus
            if eval_record.lifecycle_decision == ClaimLifecycleDecision.APPROVE:
                db_status = ClaimStatus.VERIFIED
            elif eval_record.lifecycle_decision == ClaimLifecycleDecision.REVIEW:
                db_status = ClaimStatus.CANDIDATE
            else:
                db_status = ClaimStatus.REJECTED

            # Check if claim exists
            claim_stmt = select(Claim).where(Claim.id == claim_uuid)
            existing_claim = (await session.execute(claim_stmt)).scalar_one_or_none()

            if existing_claim:
                existing_claim.claim_text = candidate.claim_text
                existing_claim.subject = (candidate.subject or "")[:255]
                existing_claim.predicate = (candidate.predicate or "")[:255]
                existing_claim.object = candidate.object
                existing_claim.claim_type = (candidate.claim_type or "policy")[:50]
                existing_claim.status = db_status
                claim = existing_claim
            else:
                claim = Claim(
                    id=claim_uuid,
                    organization_id=envelope.organization_id,
                    document_version_id=doc_version.id,
                    claim_text=candidate.claim_text,
                    subject=(candidate.subject or "")[:255],
                    predicate=(candidate.predicate or "")[:255],
                    object=candidate.object,
                    claim_type=(candidate.claim_type or "policy")[:50],
                    extraction_method=candidate.extraction_strategy.value[:50],
                    extraction_model="TrulinUniversalLayer5",
                    status=db_status,
                )
                session.add(claim)
                await session.flush()

            # 3. Create Evidence Record with exact spatial and section locators
            loc = candidate.locator or {}
            raw_page = loc.get("page_number") or loc.get("page")
            sec_heading = loc.get("section_heading") or loc.get("section")
            start_off = loc.get("start_offset") or loc.get("char_start")
            end_off = loc.get("end_offset") or loc.get("char_end")

            evidence = ClaimEvidence(
                claim_id=claim.id,
                document_id=document.id,
                evidence_type=(candidate.verification_plugin or "source_evidence")[:50],
                page_number=int(raw_page) if (raw_page is not None and str(raw_page).isdigit() and int(raw_page) > 0) else None,
                section=(str(sec_heading)[:500] if sec_heading else None),
                start_offset=int(start_off) if (start_off is not None and isinstance(start_off, int)) else None,
                end_offset=int(end_off) if (end_off is not None and isinstance(end_off, int)) else None,
                text_span=candidate.evidence_text_span,
                evidence_hash=candidate.content_hash,
            )
            session.add(evidence)

            # 4. Upsert ClaimTrustScore
            score_stmt = select(ClaimTrustScore).where(ClaimTrustScore.claim_id == claim.id)
            existing_score = (await session.execute(score_stmt)).scalar_one_or_none()
            
            src_score = decimal.Decimal(str(round(eval_record.authority.score, 4)))
            fresh_score = decimal.Decimal(str(round(eval_record.time.score, 4)))
            ev_score = decimal.Decimal(str(round(eval_record.source_match.score, 4)))
            mean_score = decimal.Decimal(str(round(eval_record.meaning.score, 4)))
            auth_score = decimal.Decimal(str(round(eval_record.authority.score, 4)))
            hum_score = decimal.Decimal("1.0") if eval_record.lifecycle_decision == ClaimLifecycleDecision.APPROVE else decimal.Decimal("0.5")
            tot_score = decimal.Decimal(str(round(eval_record.composite_trust_score, 4)))

            if existing_score:
                existing_score.source_score = src_score
                existing_score.freshness_score = fresh_score
                existing_score.evidence_score = ev_score
                existing_score.consistency_score = mean_score
                existing_score.authority_score = auth_score
                existing_score.human_score = hum_score
                existing_score.overall_score = tot_score
            else:
                ts = ClaimTrustScore(
                    claim_id=claim.id,
                    source_score=src_score,
                    freshness_score=fresh_score,
                    evidence_score=ev_score,
                    consistency_score=mean_score,
                    authority_score=auth_score,
                    human_score=hum_score,
                    overall_score=tot_score,
                )
                session.add(ts)

            # 5. Upsert ClaimValidity
            val_stmt = select(ClaimValidity).where(ClaimValidity.claim_id == claim.id)
            existing_val = (await session.execute(val_stmt)).scalar_one_or_none()
            is_curr = eval_record.time.status == "current"

            if existing_val:
                existing_val.is_current = is_curr
                existing_val.version = envelope.source_version
            else:
                cv = ClaimValidity(
                    claim_id=claim.id,
                    version=envelope.source_version[:50] if envelope.source_version else "v1.0",
                    is_current=is_curr,
                )
                session.add(cv)

            persisted_ids.append(claim.id)

        await session.flush()
        return persisted_ids
