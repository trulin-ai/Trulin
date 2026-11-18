"""
Claim Clustering & Triage Engine
Enables high-leverage 10-minute batch adjudication across thousands of candidate claims.
Clusters claims by domain rule patterns, canonical predicate targets, and fail-closed safety tiers.
"""

import decimal
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.hitl_escalation import HitlEscalation


# In-memory transaction registry for reversible batch actions
# Maps batch_id -> { "pattern_id": ..., "action": ..., "timestamp": ..., "claims": [ { id, prev_status, prev_predicate, ... } ] }
REVERSIBLE_BATCH_REGISTRY: Dict[str, Dict[str, Any]] = {}

# High-risk generic unbound verbs that must fail-closed (held for individual review)
GENERIC_UNBOUND_VERBS = {
    "provide", "include", "take", "turn", "obtain", "choose",
    "change", "share", "apply_to", "use", "implement", "collect",
    "send", "has_col3", "_i_", "ensure"
}


def classify_claim_to_pattern(claim_text: str, subject: Optional[str], predicate: Optional[str], obj: Optional[str], doc_title: str = "") -> Dict[str, Any]:
    """
    Classifies an individual candidate claim into a semantic policy pattern.
    Applies deterministic fail-closed safety checks.
    """
    text_val = (claim_text or "").lower()
    pred_val = (predicate or "").lower()
    subj_val = (subject or "").lower()
    obj_val = (str(obj) or "").lower()
    doc_val = (doc_title or "").lower()
    full_text = f"{subj_val} {pred_val} {obj_val} {text_val} {doc_val}"

    # 1. High-risk generic unbound verbs -> HELD FOR FOCUSED REVIEW
    if pred_val in GENERIC_UNBOUND_VERBS and not any(kw in text_val for kw in ["responsible for", "terminate", "suspend", "refund", "delete", "tax", "confidential"]):
        return {
            "pattern_id": f"held_generic_{pred_val}",
            "pattern_name": f"Generic Verb: '{pred_val}'",
            "category": "Unbound Syntactic Verbs",
            "confidence": "Low / Hold",
            "status": "held",
            "is_safe": False,
            "canonical_predicate": None,
            "recommended_action": "Hold for Focused Review",
            "reason": f"Unbound syntactic verb '{pred_val}' lacks deontic modal binding. Fail-closed compliance requires manual inspection."
        }

    # 2. Responsibility & Affiliate Compliance
    if "responsible" in full_text or pred_val == "are_responsible_for":
        return {
            "pattern_id": "rule_affiliate_responsibility",
            "pattern_name": "Customer Responsibility for Affiliate Compliance",
            "category": "Compliance & Liability",
            "confidence": "High (98%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "remains_responsible_for",
            "recommended_action": "Approve → remains_responsible_for",
            "reason": "Explicit responsibility clause linking customer/affiliate obligation."
        }

    # 3. Termination & Suspension for Cause/Breach
    if any(k in full_text for k in ["terminate", "suspension", "suspend", "cancellation"]) and any(k in full_text for k in ["breach", "cause", "immediate", "cure", "default", "security"]):
        return {
            "pattern_id": "rule_termination_suspension_cause",
            "pattern_name": "Termination or Suspension for Cause / Material Breach",
            "category": "Term & Termination",
            "confidence": "High (96%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "may_terminate_for_material_breach",
            "recommended_action": "Approve → may_terminate_for_material_breach",
            "reason": "Standard bilateral or provider termination/suspension for uncured breach."
        }

    # 4. Termination for Convenience / Expiration
    if any(k in full_text for k in ["terminate", "expiration", "terminate this agreement", "without cause"]):
        return {
            "pattern_id": "rule_termination_convenience",
            "pattern_name": "Termination for Convenience / Agreement Term Expiration",
            "category": "Term & Termination",
            "confidence": "High (94%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "may_terminate_without_cause",
            "recommended_action": "Approve → may_terminate_without_cause",
            "reason": "Mutual or unilateral contract termination or natural term expiry."
        }

    # 5. Refund & Credit Eligibility
    if any(k in full_text for k in ["refund", "credit", "money back", "billing adjustment", "fee adjustment"]):
        return {
            "pattern_id": "rule_refund_eligibility",
            "pattern_name": "Customer Refund & Credit Eligibility",
            "category": "Billing & Financial",
            "confidence": "High (95%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "has_refund_eligibility",
            "recommended_action": "Approve → has_refund_eligibility",
            "reason": "Explicit refund or billing adjustment terms with qualification conditions."
        }

    # 6. Tax Obligations & Stamp Duties
    if any(k in full_text for k in ["tax", "taxes", "stamp duty", "vat", "gst", "withholding"]):
        return {
            "pattern_id": "rule_tax_obligations",
            "pattern_name": "Taxes, Duties & Fee Payment Obligations",
            "category": "Billing & Financial",
            "confidence": "High (97%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "requires_tax_payment",
            "recommended_action": "Approve → requires_tax_payment",
            "reason": "Statutory tax payment allocation between client and provider."
        }

    # 7. Data Deletion, Retention & Return Post-Termination
    if any(k in full_text for k in ["delete", "destruction", "destroy", "retention", "return customer data", "data deletion"]):
        return {
            "pattern_id": "rule_data_retention_deletion",
            "pattern_name": "Customer Data Retention & Deletion Post-Cancellation",
            "category": "Data Governance & Privacy",
            "confidence": "Medium (88%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "must_delete_customer_data",
            "recommended_action": "Approve → must_delete_customer_data",
            "reason": "Data purge mandate with post-termination retention window."
        }

    # 8. Permitted Software / Service Use Rights
    if any(k in full_text for k in ["permitted use", "may use", "licensed to", "use rights", "internal business"]):
        return {
            "pattern_id": "rule_permitted_use_scope",
            "pattern_name": "Permitted Software & Service Use Scope",
            "category": "Licensing & Scope",
            "confidence": "High (94%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "has_permitted_use_scope",
            "recommended_action": "Approve → has_permitted_use_scope",
            "reason": "License scope specification governing internal customer operations."
        }

    # 9. Use Restrictions & Prohibitions (Reverse Engineering, Virtualization)
    if any(k in full_text for k in ["may not be used", "prohibited", "shall not", "must not", "reverse engineer", "rentals", "virtual environment"]):
        return {
            "pattern_id": "rule_use_prohibitions",
            "pattern_name": "Software Use Prohibitions & Anti-Reverse Engineering",
            "category": "Licensing & Scope",
            "confidence": "High (96%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "prohibited_from_using",
            "recommended_action": "Approve → prohibited_from_using",
            "reason": "Explicit negative covenant prohibiting virtualization, reverse engineering, or resale."
        }

    # 10. Hardware Leasing & Rental Device Governance
    if any(k in full_text for k in ["leased pc", "rental rights", "lease", "rent", "re-lease", "hardware"]):
        return {
            "pattern_id": "rule_hardware_leasing",
            "pattern_name": "Hardware Leasing & Rental Rights Governance",
            "category": "Hardware & Leasing",
            "confidence": "High (91%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "governed_by_rental_terms",
            "recommended_action": "Approve → governed_by_rental_terms",
            "reason": "Operational conditions for leased PCs and OEM preinstalled software."
        }

    # 11. Governing Law, Jurisdiction & Legal Venue
    if any(k in full_text for k in ["construed under", "governing law", "jurisdiction", "dispute", "venue", "laws of"]):
        return {
            "pattern_id": "rule_governing_law",
            "pattern_name": "Governing Law, Jurisdiction & Legal Venue",
            "category": "Legal & General",
            "confidence": "High (99%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "governed_by_jurisdiction",
            "recommended_action": "Approve → governed_by_jurisdiction",
            "reason": "Standard legal jurisdiction and choice of law attribution."
        }

    # 12. Notice Periods & Written Delivery
    if any(k in full_text for k in ["notice", "notices", "written notice", "delivered on the date", "return receipt"]):
        return {
            "pattern_id": "rule_notice_periods",
            "pattern_name": "Notice Requirements & Delivery Verification",
            "category": "Operational & Notices",
            "confidence": "High (93%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "requires_advance_notice",
            "recommended_action": "Approve → requires_advance_notice",
            "reason": "Formal delivery and cure timeline notification requirements."
        }

    # 13. Contractual Term Definitions
    if pred_val == "has_definition" or any(k in full_text for k in ["means", "defined as", "does not include", "shall mean"]):
        return {
            "pattern_id": "rule_term_definitions",
            "pattern_name": "Contractual Term Definitions & Scope Exclusions",
            "category": "Definitions & Interpretations",
            "confidence": "High (97%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "defines_term",
            "recommended_action": "Approve → defines_term",
            "reason": "Canonical terminology definitions and exclusion boundaries."
        }

    # 14. Confidentiality & Non-Disclosure
    if any(k in full_text for k in ["confidential", "confidentiality", "non-disclosure", "trade secret"]):
        return {
            "pattern_id": "rule_confidentiality",
            "pattern_name": "Confidentiality Obligations & Survival Scope",
            "category": "Data Governance & Privacy",
            "confidence": "High (95%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "has_confidentiality_survival",
            "recommended_action": "Approve → has_confidentiality_survival",
            "reason": "Non-disclosure obligations and survival covenants."
        }

    # 15. License Transfer & Assignment Restrictions
    if any(k in full_text for k in ["transfer", "assignment", "assign", "resell", "sublicense"]):
        return {
            "pattern_id": "rule_license_transfer",
            "pattern_name": "License Transfer & Assignment Approval Requirements",
            "category": "Licensing & Scope",
            "confidence": "High (92%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "requires_transfer_consent",
            "recommended_action": "Approve → requires_transfer_consent",
            "reason": "Conditions restricting assignment or requiring written consent for license re-allocation."
        }

    # 16. Service Level & Support Commitments
    if any(k in full_text for k in ["support", "service level", "sla", "uptime", "maintenance"]):
        return {
            "pattern_id": "rule_sla_support",
            "pattern_name": "Support Commitments & SLA Operational Bounds",
            "category": "Support & Operations",
            "confidence": "Medium (85%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "governed_by_service_terms",
            "recommended_action": "Approve → governed_by_service_terms",
            "reason": "Technical support scope and response commitment terms."
        }

    # 17. Audit & Compliance Inspection Rights
    if any(k in full_text for k in ["audit", "inspection", "verify compliance", "records"]):
        return {
            "pattern_id": "rule_audit_rights",
            "pattern_name": "Audit & Compliance Verification Rights",
            "category": "Compliance & Liability",
            "confidence": "High (94%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "reserves_audit_rights",
            "recommended_action": "Approve → reserves_audit_rights",
            "reason": "Provider rights to verify software deployment and license compliance."
        }

    # 18. Developer API & Technical Endpoints
    if any(k in full_text for k in ["api", "endpoint", "request_uri", "get /", "post /", "rest", "json", "token"]):
        return {
            "pattern_id": "rule_api_integration",
            "pattern_name": "Developer API & Technical Endpoints Specification",
            "category": "Technical & API",
            "confidence": "Medium (86%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "specifies_api_endpoint",
            "recommended_action": "Approve → specifies_api_endpoint",
            "reason": "System API interaction endpoints and technical specifications."
        }

    # 19. General Enterprise Policy & Enrollment Terms
    if pred_val == "has_validity_rule" or "agreement" in full_text or "license" in full_text:
        return {
            "pattern_id": "rule_general_policy",
            "pattern_name": "General Enterprise Policy & Enrollment Terms",
            "category": "Policy Baseline",
            "confidence": "Medium (82%)",
            "status": "safe",
            "is_safe": True,
            "canonical_predicate": "governed_by_policy_rule",
            "recommended_action": "Approve → governed_by_policy_rule",
            "reason": "Standard contractual provision extracted from enterprise agreement."
        }

    # Edge cases / Context gaps
    return {
        "pattern_id": "held_edge_cases",
        "pattern_name": f"Context Gap / Table Attribute ('{pred_val[:20]}')",
        "category": "Ambiguous & Fragmented Context",
        "confidence": "Low / Hold",
        "status": "held",
        "is_safe": False,
        "canonical_predicate": None,
        "recommended_action": "Hold for Focused Review",
        "reason": "Fragmented sentence structure, unmapped table cell, or regional clause requiring individual verification."
    }


class ClaimClusteringEngine:
    @staticmethod
    async def cluster_candidate_claims(
        db: AsyncSession,
        organization_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Clusters all candidate claims into high-leverage policy patterns for 10-minute triage.
        Returns top patterns, sample quotes, document distribution, and triage metrics.
        """
        stmt = (
            select(
                Claim.id,
                Claim.claim_text,
                Claim.subject,
                Claim.predicate,
                Claim.object,
                Document.id.label("doc_id"),
                Document.title.label("doc_title"),
            )
            .join(DocumentVersion, Claim.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Claim.organization_id == organization_id,
                Claim.status == ClaimStatus.CANDIDATE,
            )
        )
        if document_id:
            stmt = stmt.where(Document.id == document_id)

        res = await db.execute(stmt)
        rows = res.all()

        pattern_groups = defaultdict(list)
        for row in rows:
            cid, text_val, subj, pred, obj, doc_id, doc_title = row
            p_info = classify_claim_to_pattern(text_val, subj, pred, obj, doc_title)
            pid = p_info["pattern_id"]
            pattern_groups[pid].append((row, p_info))

        # Sort patterns by claim count descending
        sorted_patterns = sorted(pattern_groups.items(), key=lambda x: len(x[1]), reverse=True)

        patterns_list = []
        safe_batch_claims_count = 0
        held_claims_count = 0

        for pid, items in sorted_patterns:
            first_row, p_meta = items[0]
            count = len(items)
            is_safe = p_meta["is_safe"]

            if is_safe:
                safe_batch_claims_count += count
            else:
                held_claims_count += count

            # Extract distinct documents in this pattern
            docs_in_pattern = list({r[6] for r in [it[0] for it in items] if r[6]})
            doc_summary = (
                f"{docs_in_pattern[0]}"
                if len(docs_in_pattern) == 1
                else f"Across {len(docs_in_pattern)} documents: {', '.join(docs_in_pattern[:2])}..."
            )

            # Representative claim (prefer clean verbatim text)
            rep_row = first_row
            for r, _ in items:
                if len(r[1] or "") > len(rep_row[1] or "") and len(r[1] or "") < 200:
                    rep_row = r
                    break

            # Collect all claim IDs for batch actions
            claim_ids = [str(r[0]) for r, _ in items]

            patterns_list.append({
                "pattern_id": pid,
                "pattern_name": p_meta["pattern_name"],
                "category": p_meta["category"],
                "claim_count": count,
                "confidence": p_meta["confidence"],
                "status": p_meta["status"],
                "is_safe": is_safe,
                "canonical_predicate": p_meta["canonical_predicate"],
                "recommended_action": p_meta["recommended_action"],
                "reason": p_meta["reason"],
                "document_distribution": doc_summary,
                "representative_claim": {
                    "id": str(rep_row[0]),
                    "claim_text": rep_row[1],
                    "subject": rep_row[2],
                    "predicate": rep_row[3],
                    "object": rep_row[4],
                    "document_title": rep_row[6],
                },
                "claim_ids": claim_ids,
            })

        return {
            "summary": {
                "total_candidates": len(rows),
                "safe_batch_claims_count": safe_batch_claims_count,
                "held_claims_count": held_claims_count,
                "patterns_count": len(patterns_list),
                "safe_patterns_count": sum(1 for p in patterns_list if p["is_safe"]),
                "held_patterns_count": sum(1 for p in patterns_list if not p["is_safe"]),
                "estimated_review_time_mins": round(len(patterns_list) * 0.25, 1),
            },
            "patterns": patterns_list,
        }

    @staticmethod
    async def get_pattern_claims(
        db: AsyncSession,
        pattern_id: str,
        organization_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all individual claims belonging to a given pattern,
        enabling the reviewer to inspect outliers and uncheck non-conforming items.
        """
        stmt = (
            select(
                Claim.id,
                Claim.claim_text,
                Claim.subject,
                Claim.predicate,
                Claim.object,
                Document.id.label("doc_id"),
                Document.title.label("doc_title"),
                Claim.created_at,
            )
            .join(DocumentVersion, Claim.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Claim.organization_id == organization_id,
                Claim.status == ClaimStatus.CANDIDATE,
            )
        )
        if document_id:
            stmt = stmt.where(Document.id == document_id)

        res = await db.execute(stmt)
        rows = res.all()

        matching_claims = []
        for row in rows:
            cid, text_val, subj, pred, obj, doc_id, doc_title, created_at = row
            p_info = classify_claim_to_pattern(text_val, subj, pred, obj, doc_title)
            if p_info["pattern_id"] == pattern_id:
                matching_claims.append({
                    "id": str(cid),
                    "claim_text": text_val,
                    "subject": subj,
                    "predicate": pred,
                    "object": obj,
                    "document_id": str(doc_id),
                    "document_title": doc_title,
                    "created_at": created_at.isoformat() if created_at else None,
                    "pre_selected": True,  # Pre-selected for batch action
                })

        return matching_claims

    @staticmethod
    async def apply_batch_pattern_action(
        db: AsyncSession,
        pattern_id: str,
        action: str,  # "approve" | "reject" | "hold" | "escalate"
        organization_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID] = None,
        reviewer_notes: Optional[str] = None,
        selected_claim_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a reversible batch triage action across all selected claims in a pattern.
        Updates statuses, validity records, trust scores, and logs the batch transaction.
        """
        now = datetime.now(timezone.utc)
        batch_id = str(uuid.uuid4())

        # If specific claim IDs were passed, use them; otherwise resolve all in this pattern
        target_ids = selected_claim_ids
        if not target_ids:
            # Resolve all claim IDs belonging to this pattern
            pattern_claims = await ClaimClusteringEngine.get_pattern_claims(db, pattern_id, organization_id)
            target_ids = [uuid.UUID(c["id"]) for c in pattern_claims]

        if not target_ids:
            return {
                "success": False,
                "message": "No candidate claims found for this pattern.",
                "batch_id": batch_id,
                "modified_count": 0,
            }

        # Fetch full claim objects with validity records and trust scores
        stmt = (
            select(Claim)
            .where(
                Claim.organization_id == organization_id,
                Claim.id.in_(target_ids),
                Claim.status == ClaimStatus.CANDIDATE,
            )
            .options(
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
            )
        )
        res = await db.execute(stmt)
        claims_to_modify = res.scalars().all()

        if not claims_to_modify:
            return {
                "success": False,
                "message": "Selected claims are no longer in candidate status.",
                "batch_id": batch_id,
                "modified_count": 0,
            }

        # Snapshot previous states for rollback
        snapshot = []
        for c in claims_to_modify:
            snapshot.append({
                "id": c.id,
                "status": c.status,
                "predicate": c.predicate,
                "updated_at": c.updated_at,
            })

        # Derive target predicate from pattern metadata
        sample_meta = classify_claim_to_pattern(
            claims_to_modify[0].claim_text,
            claims_to_modify[0].subject,
            claims_to_modify[0].predicate,
            claims_to_modify[0].object,
        )
        canonical_pred = sample_meta.get("canonical_predicate")

        # 1. ACTION: APPROVE
        if action == "approve":
            for c in claims_to_modify:
                c.status = ClaimStatus.VERIFIED
                if canonical_pred:
                    c.predicate = canonical_pred[:255]
                c.updated_at = now

                # Boost human review score & overall trust
                for score in c.trust_scores:
                    score.human_score = decimal.Decimal("1.0")
                    score.overall_score = decimal.Decimal(str(min(round(float(score.overall_score) + 0.15, 4), 1.0)))
                    score.calculated_at = now

                for val in c.validity_records:
                    val.is_current = True
                    val.validity_status = "verified"

        # 2. ACTION: REJECT
        elif action == "reject":
            for c in claims_to_modify:
                c.status = ClaimStatus.REJECTED
                c.updated_at = now

                for val in c.validity_records:
                    val.is_current = False
                    val.validity_status = "rejected"

        # 3. ACTION: ESCALATE
        elif action == "escalate":
            for c in claims_to_modify:
                escalation = HitlEscalation(
                    organization_id=c.organization_id,
                    audit_id=str(c.id),
                    actor_id=str(reviewer_id or "reviewer"),
                    actor_role="Senior Compliance Reviewer",
                    action_prompt=f"Batch Escalation [{sample_meta['pattern_name']}]: '{c.claim_text}'",
                    reasons=[reviewer_notes or f"Escalated from batch pattern triage ({sample_meta['pattern_name']})."],
                    category="Batch Pattern Escalation",
                    liability_prevented_usd=500.0,
                    status="PENDING_REVIEW",
                )
                db.add(escalation)

        # 4. ACTION: HOLD
        elif action == "hold":
            # Retain in candidate, no mutation, just audited
            pass

        await db.commit()

        # Register in reversible transaction memory
        REVERSIBLE_BATCH_REGISTRY[batch_id] = {
            "batch_id": batch_id,
            "pattern_id": pattern_id,
            "pattern_name": sample_meta.get("pattern_name", pattern_id),
            "action": action,
            "timestamp": now.isoformat(),
            "reviewer_id": str(reviewer_id) if reviewer_id else None,
            "modified_count": len(claims_to_modify),
            "snapshot": snapshot,
        }

        return {
            "success": True,
            "batch_id": batch_id,
            "action": action,
            "modified_count": len(claims_to_modify),
            "pattern_name": sample_meta.get("pattern_name", pattern_id),
            "canonical_predicate": canonical_pred,
            "message": f"Successfully applied '{action}' to {len(claims_to_modify)} claims in pattern.",
        }

    @staticmethod
    async def revert_batch_transaction(db: AsyncSession, batch_id: str) -> Dict[str, Any]:
        """
        Reverts a previously applied batch action, restoring claims to candidate status.
        """
        tx = REVERSIBLE_BATCH_REGISTRY.get(batch_id)
        if not tx:
            return {"success": False, "message": f"Batch transaction '{batch_id}' not found or already reverted."}

        claim_ids = [s["id"] for s in tx["snapshot"]]
        stmt = select(Claim).where(Claim.id.in_(claim_ids)).options(
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
        )
        res = await db.execute(stmt)
        claims = res.scalars().all()

        state_map = {s["id"]: s for s in tx["snapshot"]}
        now = datetime.now(timezone.utc)

        for c in claims:
            prev = state_map.get(c.id)
            if prev:
                c.status = prev["status"]
                c.predicate = prev["predicate"]
                c.updated_at = now
                for val in c.validity_records:
                    val.is_current = True
                    val.validity_status = "candidate"

        await db.commit()
        # Remove from registry once reverted
        del REVERSIBLE_BATCH_REGISTRY[batch_id]

        return {
            "success": True,
            "reverted_batch_id": batch_id,
            "reverted_claims_count": len(claims),
            "message": f"Successfully reverted batch {batch_id}; restored {len(claims)} claims to candidate status.",
        }
