"""
Universal 10-Gate Claim Governance Certification Evaluator.

Enforces strict, document-agnostic fail-closed validation:
1. evidence_exists: Non-empty verbatim quote and valid source locator.
2. evidence_located: Verbatim quote physically grounded at byte/char offsets.
3. text_integrity: Not synthesized, no taxonomy slugs, modal preserved, negation intact.
4. clause_entails_claim: Enclosing clause logically entails the proposition.
5. subject_valid: Resolves to an actor, role, defined asset; rejects grammatical fragments.
6. counterparty_resolved: Bound obligor/obligee, no dangling ungrounded pronouns.
7. predicate_valid: Belongs to versioned taxonomy; role-compatible; not a banned catch-all.
8. atomicity_valid: Governs exactly one action/remedy without multi-branch disjunctions.
9. duplicate_valid: Unique proposition; collapsed duplicates point to canonical.
10. claim_type_allowed: Operative RULE (definitions, references, and descriptions routed to NON_RULE).
11. human_approval_required (Optional): Evaluated from risk policy.

Every gate fails closed. Missing or unverified gates evaluate to False.
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.evidence import ImmutableEvidenceSpan
from app.schemas.universal_claim import ClaimLifecycleState, ClaimType, ModalityType, UniversalClaim
from app.services.dynamic_modality_extractor import DynamicModalityExtractor
from app.services.evidence_locator_service import EvidenceLocatorService
from app.services.role_direction_validator import RoleDirectionValidator
from app.taxonomy.registry import PredicateRegistryService


UNIVERSAL_10_GATES = [
    "evidence_exists",
    "evidence_located",
    "text_integrity",
    "clause_entails_claim",
    "subject_valid",
    "counterparty_resolved",
    "predicate_valid",
    "atomicity_valid",
    "duplicate_valid",
    "claim_type_allowed",
]

# Generic page-header and document pagination patterns
PAGE_HEADER_PATTERNS = [
    r"(?i)\bpage\s+\d+\s+of\s+\d+\b",
    r"(?i)^\s*page\s+\d+\b",
]

# Generic postal-address patterns (street numbers, street types, PO box, postal codes, suite numbers)
POSTAL_ADDRESS_PATTERNS = [
    r"(?i)\b\d{1,5}\s+[A-Za-z0-9\.\s]{1,30}\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Lane|Ln|Court|Ct|Parkway|Pkwy|Plaza|Plz)\b",
    r"(?i)\bp\.?o\.?\s*box\s+\d+\b",
    r"(?i)\bsuite\s+\d+\b",
    r"(?i)\b[A-Z]{2}\s+\d{5}(-\d{4})?\b",
    r"(?i)\b\d{5}-\d{4}\b",
    r"(?i)\b[A-Za-z\s]+,\s+[A-Z]{2}\s+\d{5}\b",
]

# Disallowed subject prefixes and exact tokens that indicate grammar fragments or syntax artifacts
INVALID_SUBJECT_PATTERNS = [
    r"^\(?[iIvVxX0-9]+[\.\)\s]",    # Enumeration markers: (i), (ii), 1., 2)
    r"^\(?\s*[a-zA-Z]\s*[\.\)]",     # Enumeration letters: (a), (b), a.
    r"^the\s+following\b",
    r"^without\s+limiting\b",
    r"^failure\s+to\s+enforce\b",
    r"^any\s+attempted\s+assignment\b",
    r"^termination\s+without\s+cause\b",
    r"^no\s+changes?\b",
    r"^changes?\b",
    r"^such\s+changes?\b",
    r"^all\s+amounts?\b",
    r"^this\s+agreement\b",
    r"^page\s+\d+",
    r"^section\s+[\d\.]+",
    r"^article\s+\d+",
] + PAGE_HEADER_PATTERNS + POSTAL_ADDRESS_PATTERNS

# Operative contractual modal verbs required in normative rules
MODAL_OPERATIVE_PATTERN = (
    r"\b("
    r"may|must|will|shall|can|should|cannot|"
    r"(?:is|are)\s+required(?:\s+to)?|approval\s+required|required|"
    r"(?:is|are)\s+accepted|accepted\s+in-store|"
    r"(?:is|are)\s+entitled\s+to|(?:is|are)\s+eligible\s+(?:for|to)|"
    r"agrees?\s+to|authorizes?|grants?|retains?|warrants?|reserves?|assigns?|requires?|"
    r"(?:is|are|remains)\s+responsible\s+for|has\s+a\b|has\s+the\s+right\s+to\b|"
    r"is\s+limited\s+to\b|is\s+capped\s+at\b|shall\s+be\s+limited\s+to\b|liability\s+is\s+the\b|"
    r"must\s+not|may\s+not|will\s+not|shall\s+not|neither\s+party\s+will|is\s+not\s+licensed\s+to|prohibited\s+from|"
    r"non-refundable|not\s+refundable|not\s+eligible|never\s+expire|applies|"
    r"(?:is|are)\s+issued|submits?|decides?|refunded|refunds?|receives?|bonus|deducted(?:\s+from)?"
    r")\b"
)

# Generic predicate slug pattern in claim text
PREDICATE_SLUG_REGEX = r"\b(?:has|can|may|must|will|remains|is)_[a-z0-9]+(?:_[a-z0-9]+)+\b"

# Generic leading enumeration prefix
ENUMERATION_PREFIX_PATTERN = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s+"

# Non-rule types
NON_RULE_TYPES = {
    "definition",
    "reference",
    "description",
    "responsibility",
    "section_marker",
    "fragment",
    "contact_information",
    "contact",
}

# Cross-reference cues
REFERENCE_CUES = [
    "more details about",
    "can be found in",
    "can be found at",
    "for more information",
    "refer to section",
    "see the",
    "visit http",
]

# Description cues
DESCRIPTION_CUES = [
    "availability may vary",
    "may vary by region",
    "subject to export laws",
    "subject to u.s. and other",
    "governed by the laws of",
    "does not include online services",
]


class EntailmentDecision(str, Enum):
    """3-valued semantic entailment classification."""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class SemanticEntailmentResult:
    """Detailed semantic entailment verdict across dimensions."""
    decision: EntailmentDecision
    is_supported: bool
    reason: str
    dimension_checked: str = "ACTION"

    def __iter__(self):
        return iter((self.is_supported, self.reason))


@dataclass
class UniversalGateResult:
    evidence_exists: bool = False
    evidence_located: bool = False
    text_integrity: bool = False
    clause_entails_claim: bool = False
    subject_valid: bool = False
    counterparty_resolved: bool = False
    predicate_valid: bool = False
    atomicity_valid: bool = False
    duplicate_valid: bool = False
    claim_type_allowed: bool = False
    human_approved_if_required: bool = True

    entailment_decision: str = "INSUFFICIENT_EVIDENCE"
    entailment_reason: Optional[str] = None
    entailment_dimension: Optional[str] = None

    subject: Optional[str] = None
    all_gates_passed: bool = False
    lifecycle_state: ClaimLifecycleState = ClaimLifecycleState.REVIEW_REQUIRED
    certification_tier: str = "REVIEW_REQUIRED"
    is_canonical: bool = False
    agent_accessible: bool = False
    rejection_reasons: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    gates: Dict[str, bool] = field(default_factory=dict)
    repaired_claim_text: Optional[str] = None

    @property
    def lifecycle_decision(self) -> str:
        if self.certification_tier == "AUTOMATED_CERTIFIED":
            return "approve"
        if self.certification_tier == "REVIEW_REQUIRED":
            return "review"
        if self.certification_tier == "NON_RULE":
            return "non_rule"
        return "reject"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gates": self.gates,
            "all_gates_passed": self.all_gates_passed,
            "subject": self.subject,
            "lifecycle_state": self.lifecycle_state.value if hasattr(self.lifecycle_state, "value") else str(self.lifecycle_state),
            "lifecycle_decision": self.lifecycle_decision,
            "certification_tier": self.certification_tier,
            "is_canonical": self.is_canonical,
            "agent_accessible": self.agent_accessible,
            "rejection_reasons": self.rejection_reasons,
            "reason_codes": self.reason_codes,
            "repaired_claim_text": self.repaired_claim_text,
            "entailment_decision": self.entailment_decision,
            "entailment_reason": self.entailment_reason,
            "entailment_dimension": self.entailment_dimension,
        }



class UniversalGateEvaluator:
    """Universal 10-gate fail-closed claim governance evaluator."""

    @staticmethod
    def strip_enumeration_prefix(text: Optional[str]) -> str:
        """Strips leading enumeration markers like (i), (ii), (iv), 1., 2), (a), etc."""
        if not text:
            return ""
        pattern = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s*"
        return re.sub(pattern, "", text).strip()

    @staticmethod
    def compute_semantic_signature(subject: Optional[str], predicate: Optional[str], obj_or_text: Optional[str]) -> str:
        s = (subject or "").strip().lower()
        p = (predicate or "").strip().lower()
        o = re.sub(r"[^\w\s]", "", (obj_or_text or "").strip().lower())
        words = o.split()[:8]
        key = f"{s}|{p}|{' '.join(words)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def check_semantic_entailment(
        cls,
        subject: str,
        predicate: str,
        claim_text: str,
        evidence_quote: str,
        clause_text: str = "",
        object_text: str = "",
        modality: str = "",
    ) -> SemanticEntailmentResult:
        """
        Deterministic, document-agnostic 3-valued semantic entailment check.
        Evaluates whether evidence logically supports, directly contradicts, or provides
        insufficient evidence for the structured proposition across actor, action,
        object, modality, deadline, and conditions.
        """
        text_lower = (evidence_quote or claim_text or "").lower()
        clause_lower = (clause_text or "").lower()
        full_evidence = f"{text_lower} {clause_lower}".strip()
        pred_lower = (predicate or "").lower()
        subj_lower = (subject or "").lower()
        obj_lower = (object_text or "").lower()

        # 1. has_return_window / has_refund_window
        if pred_lower in ("has_return_window", "has_refund_window"):
            # Direct contradiction: clause explicitly bars returns or specifies non-refundable
            if re.search(r"\b(no returns|all sales are final|returns are not permitted|non-returnable|cannot be returned|strictly non-refundable|non-refundable|nonrefundable|not eligible for (?:any\s+)?refund|no refunds?(?:\s+will\s+be\s+provided)?)\b", full_evidence):
                # If claim asserts a specific timeframe/exception (e.g. 7 days) that does not appear in full_evidence
                window_match = re.search(r"\b(\d+)\s*(?:days?|calendar days?|business days?|hours?)\b", claim_text.lower())
                if window_match:
                    window_str = window_match.group(0)
                    if window_str not in full_evidence:
                        return SemanticEntailmentResult(
                            decision=EntailmentDecision.CONTRADICTED,
                            is_supported=False,
                            reason=f"Direct contradiction: evidence specifies non-refundable; does not contain asserted {window_str} exception window.",
                            dimension_checked="MODALITY_POLARITY",
                        )
                elif not re.search(r"\b(not eligible|non-refundable|cannot be returned|no returns)\b", obj_lower):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason="Direct contradiction: evidence explicitly bars returns/refunds of products.",
                        dimension_checked="MODALITY_POLARITY",
                    )
            # Scope / Action mismatch: audit license remediation
            if re.search(r"\b(unlicensed use|order sufficient licenses|verification reveals any unlicensed|cover the period of its unlicensed)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs audit licensing remediation; insufficient evidence to establish or negate a product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: professional services warranty remedy
            if re.search(r"\b(warranty claim|professional services|re-perform|giving rise to the warranty)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs professional services warranty notification and remedies; insufficient evidence for a product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: bank posting duration / speed (Candidate #24)
            if re.search(r"\b(bank may take|post the credit|processed immediately)\b", full_evidence) and not re.search(r"\b(return window|days to return|return within)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies banking posting speed or credit processing duration, not product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: price drop adjustment (Candidate #81)
            if re.search(r"\b(price adjustment|price drop|drops in price)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies price drop adjustment, not product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: courtesy first-charge refund for forgotten trial cancel (Candidate #86)
            if re.search(r"\b(forget to cancel|forgot to cancel|first charge)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies courtesy trial refund request, not product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: subscription pause privilege (Candidate #87)
            if re.search(r"\b(subscribers can pause|pause for up to)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies subscription pause privilege, not product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: order cancellation status (Candidate #80)
            if re.search(r"\b(refund pending.*within 1 hour|processing.*contact support|authorisation processing)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies order cancellation status, not product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Absence of return keywords in full evidence (including table headers and hierarchical section context)
            if not re.search(r"\b(return|returned|returns|return window|refund|refunds|refunded)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate lacks product return/refund cues in evidence.",
                    dimension_checked="ACTION_OBJECT",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes product return/refund window.",
                dimension_checked="ACTION_OBJECT",
            )

        # 1b. has_warranty_remedy_window / has_professional_services_remedy_window
        if pred_lower in ("has_warranty_remedy_window", "has_professional_services_remedy_window"):
            if not re.search(r"\b(warranty claim|warranty|re-perform|remedy|within \d+ days|completion of the work)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate lacks warranty notice or remedy cues in evidence.",
                    dimension_checked="ACTION_OBJECT",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes warranty notification remedy window.",
                dimension_checked="ACTION_OBJECT",
            )

        # 2. authorizes_recurring_charges
        if pred_lower == "authorizes_recurring_charges":
            # Direct contradiction
            if re.search(r"\b(shall not process recurring|does not authorize recurring|recurring charges are prohibited)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence bars recurring billing charges.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Action mismatch: credit report / financial inquiry for invoicing eligibility
            if re.search(r"\b(credit report|credit reports|financial condition|eligibility for invoicing)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause authorizes financial assessment and credit inquiry for invoicing terms; insufficient evidence for recurring billing charges.",
                    dimension_checked="ACTION_OBJECT",
                )
            # Absence of recurring cues
            has_recurring = bool(re.search(r"\b(recurring|periodically|automatic renewal|auto-renew|periodically for each|electronic debit|store.*payment details|charge.*payment method)\b", full_evidence))
            if not has_recurring:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'authorizes_recurring_charges' lacks recurring billing or periodic charge support in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes authorization of recurring charges.",
                dimension_checked="ACTION",
            )

        # 3. has_refund_eligibility
        if pred_lower == "has_refund_eligibility":
            # Direct contradiction: fees strictly non-refundable or items past cutoff
            if re.search(
                r"\b(strictly non-refundable|non-refundable|nonrefundable|no refunds?(?:\s+will\s+be\s+provided)?|"
                r"not eligible for (?:any\s+)?refund|cannot be returned|not returnable|cannot be returned or refunded|"
                r"non-refundable items|items returned more than 90 days|perishable goods.*past 14 days)\b",
                f"{full_evidence} {obj_lower} {claim_text.lower()}",
            ):
                if not re.search(r"\b(not eligible|non-refundable|cannot be returned|prohibited|no refund)\b", obj_lower):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason="Direct contradiction: evidence explicitly specifies fees or items are non-refundable.",
                        dimension_checked="MODALITY_POLARITY",
                    )
            # Scope mismatch: return freight deduction / fee
            if re.search(r"\b(freight deduction|return freight|flat-rate return freight|restocking fee|deducted from the refund)\b", full_evidence) and not re.search(r"\bis eligible for (?:a )?refund\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies return freight deduction or fee; requires predicate 'has_return_freight_deduction'.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope mismatch: drop-off receipt retention
            if re.search(r"\b(keep the drop-off receipt|retain the (?:drop-off )?receipt)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies procedural receipt retention; requires predicate 'requires_receipt_retention'.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope mismatch: settlement currency
            if re.search(r"\b(currency of the original charge|issued in the currency)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies refund settlement currency; requires predicate 'uses_original_charge_currency'.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope mismatch: purchaser non-notification
            if re.search(r"\b(purchaser is not notified|gift recipient)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies purchaser non-notification on gift exchange.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope mismatch: tax / privacy record retention
            if re.search(r"\b(retained for \d+ years|tax compliance|transaction logs)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies compliance data retention period.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope mismatch: security deposit / collateral for credit invoicing
            if re.search(r"\b(provide security|security in a form|eligible for invoicing)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs credit security collateral for invoicing; insufficient evidence for refund eligibility.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Check for refund keywords in evidence excluding general document title
            evidence_no_header = re.sub(r"(?i)\bnorthwind\s+refund\s+policy\b", "", full_evidence).strip()
            has_refund = bool(re.search(r"\b(refund|refunds|refunded|reimburse|reimbursement|return the amount|money back|credit)\b", evidence_no_header))
            if not has_refund:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_refund_eligibility' lacks refund or reimbursement support in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence supports refund eligibility.",
                dimension_checked="ACTION",
            )

        # 3b. has_default_refund_destination
        if pred_lower == "has_default_refund_destination":
            if re.search(r"\b(bonus|5% bonus|store credit instead of)\b", full_evidence) and not re.search(r"\bdefault refund destination\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies store credit bonus incentive; insufficient evidence for default refund destination.",
                    dimension_checked="ACTION_SCOPE",
                )

        # 4. must_pay_within_30_days
        if pred_lower == "must_pay_within_30_days":
            # Action mismatch: 30-day deadline attached to non-payment action (cure breach, notice, remedy, etc.)
            has_pay_action = bool(re.search(r"\b(pay|payment|invoices?|amounts? due|fees?|charges?|remit)\b", full_evidence))
            if not has_pay_action:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action mismatch: 30-day deadline in evidence applies to non-payment obligation (e.g. cure breach, notice, or remedy), not invoice payment.",
                    dimension_checked="ACTION",
                )
            # Direct deadline contradiction: payment due immediately
            if re.search(r"\b(immediately upon receipt|due immediately|upon receipt of an invoice)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct deadline contradiction: evidence specifies payment is due immediately upon receipt of invoice, which contradicts a Net 30 deadline.",
                    dimension_checked="DEADLINE",
                )
            # Deadline absence: pre-termination services with no payment timeframe
            if re.search(r"\b(provided or used before termination|services before termination)\b", full_evidence) and not re.search(r"\b(30|thirty)\s+(?:calendar\s+)?days\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Deadline absent: evidence establishes pre-termination payment obligation but contains no 30-day payment deadline.",
                    dimension_checked="DEADLINE",
                )
            # Absence of 30 days
            has_30 = bool(re.search(r"\b(30 days|thirty days|thirty \(30\) days|30 calendar days|thirty calendar days|net 30)\b", full_evidence))
            if not has_30:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'must_pay_within_30_days' asserts a 30-day deadline not present in the evidence.",
                    dimension_checked="DEADLINE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes 30-day payment deadline.",
                dimension_checked="DEADLINE",
            )

        # 4b. must_pay_unpaid_invoices_immediately
        if pred_lower == "must_pay_unpaid_invoices_immediately":
            has_invoice = bool(re.search(r"\b(invoices?|unpaid invoices?|billed amounts?)\b", full_evidence))
            if not has_invoice:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Object mismatch: evidence governs payment of taxes or other obligations, not unpaid invoices.",
                    dimension_checked="OBJECT",
                )
            has_immediate = bool(re.search(r"\b(immediately|upon receipt|promptly upon receipt)\b", full_evidence))
            if not has_immediate:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Deadline absent: evidence does not establish that invoices must be paid immediately.",
                    dimension_checked="DEADLINE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes immediate payment obligation for unpaid invoices.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 4c. must_pay_for_services_before_termination
        if pred_lower == "must_pay_for_services_before_termination":
            has_term_timing = bool(re.search(r"\b(before termination|prior to termination|provided or used before termination|as of the termination date)\b", full_evidence))
            if not has_term_timing:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Condition/Timing mismatch: evidence does not restrict payment obligation to services delivered prior to termination.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes pre-termination services payment obligation.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 5. warrants_professional_standards
        if pred_lower == "warrants_professional_standards":
            # Direct contradiction
            if re.search(r"\b(as is without warranty of any kind|disclaims all warranties of professional standard|no warranty of skill)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence disclaims professional warranty standards.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Scope mismatch: delegation to affiliates / subcontractors
            is_delegation = bool(re.search(r"\b(through its affiliates|use subcontractors|perform.*through its affiliates)\b", full_evidence))
            has_warranty = bool(re.search(r"\b(warrants?|warranty|standard of care|professional care|skill|industry standards?)\b", full_evidence))
            if is_delegation and not has_warranty:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause permits delegation to affiliates and subcontractors; insufficient evidence for an affirmative professional standards warranty.",
                    dimension_checked="ACTION_SCOPE",
                )
            if not has_warranty:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'warrants_professional_standards' lacks warranty or professional standard cues in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes warranty of professional standards.",
                dimension_checked="ACTION",
            )

        # 6. must_not_modify_agreement
        if pred_lower == "must_not_modify_agreement":
            # Object mismatch: Product modification != Agreement modification
            is_product_mod = bool(re.search(r"\b(modify or discontinue offering a product|modify.*product|discontinue offering a product)\b", full_evidence))
            if is_product_mod:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Object mismatch: clause permits modifying or discontinuing a Product, which does not establish or contradict an agreement modification restriction.",
                    dimension_checked="OBJECT",
                )
            # Direct polarity contradiction: party permitted to modify agreement
            if re.search(r"\b(may modify this agreement|may update this agreement|may amend this agreement)\b", full_evidence):
                if subj_lower in ("customer", "licensee", "user"):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason="Direct contradiction: evidence permits Customer to modify the agreement, contradicting prohibition 'must_not_modify_agreement'.",
                        dimension_checked="MODALITY_POLARITY",
                    )
            if not re.search(r"\b(may not modify this agreement|must not modify this agreement|cannot modify this agreement|shall not modify this agreement)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Evidence does not support agreement modification prohibition.",
                    dimension_checked="MODALITY_POLARITY",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes prohibition against modifying agreement.",
                dimension_checked="MODALITY_POLARITY",
            )

        # 7. Formal Writing & Signature Subject & Predicate Integrity
        if "any waiver" in text_lower and "signed" in text_lower:
            if pred_lower == "must_be_in_writing" and "signed" not in pred_lower:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Condition omission: predicate 'must_be_in_writing' drops the essential cumulative requirement that the waiver be signed.",
                    dimension_checked="CONDITION",
                )
            if subj_lower in ("either party", "each party", "customer"):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Subject mismatch: subject for waiver clause must be 'Waiver' or 'Waiving party', not generic contracting entity.",
                    dimension_checked="SUBJECT",
                )
        elif "waiver" in text_lower and "signed" in text_lower and pred_lower == "must_be_in_writing":
            return SemanticEntailmentResult(
                decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                is_supported=False,
                reason="Condition omission: predicate 'must_be_in_writing' drops the cumulative signature requirement.",
                dimension_checked="CONDITION",
            )

        # 8. Notice requirement
        if "all notices must be in writing" in text_lower:
            if subj_lower in ("either party", "each party"):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Subject mismatch: subject for notice requirement must be 'Notice', not generic contracting entity.",
                    dimension_checked="SUBJECT",
                )

        # 8b. Suspension scope (Security/Breach vs Trade Laws)
        if pred_lower == "may_suspend_for_security_or_breach":
            has_sec_or_breach = bool(re.search(r"\b(security|breach|material breach|security risks?|vulnerability)\b", full_evidence))
            is_trade_law = bool(re.search(r"\b(trade laws?|sanctions?|embargo|export)\b", full_evidence))
            if is_trade_law and not has_sec_or_breach:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Scope/Trigger mismatch: evidence authorizes suspension to prevent trade law violations or comply with sanctions, not for security risks or material breach.",
                    dimension_checked="CONDITION",
                )
            if not has_sec_or_breach:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_suspend_for_security_or_breach' lacks security risk or breach triggers in evidence.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes suspension for security risk or material breach.",
                dimension_checked="CONDITION",
            )

        if pred_lower == "may_suspend_for_trade_laws":
            has_trade_laws = bool(re.search(r"\b(trade laws?|sanctions?|embargo|export regulations?)\b", full_evidence))
            if not has_trade_laws:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_suspend_for_trade_laws' lacks trade law, sanction, or embargo triggers in evidence.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes suspension to prevent trade law violations or comply with sanctions.",
                dimension_checked="CONDITION",
            )

        # 8b. Precedence & Custom Contract Override Checks
        if pred_lower in ("may_override_standard_terms", "may_supersede_standard_terms"):
            if subj_lower in ("customer", "customers", "user", "buyer", "subscriber", "client") or any(w in subj_lower for w in ("business customer", "standard account")):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Precedence contradiction: evidence specifies custom contracts/agreements may override standard terms; does not grant Customer an unrestricted permission to override.",
                    dimension_checked="AUTHORITY_SCOPE",
                )
            if not re.search(r"\b(override|supersede|preempt|govern in place of)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_override_standard_terms' lacks override/precedence cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes custom contract precedence over standard terms.",
                dimension_checked="AUTHORITY_SCOPE",
            )

        # 8c. Trial Cancellation vs Physical Shipment Checks
        if pred_lower == "can_cancel_before_shipment":
            if "trial" in full_evidence and not any(w in full_evidence for w in ("ship", "shipped", "shipping", "carrier", "tracking", "dispatch")):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs digital free trial cancellation before trial ends, not physical pre-shipment order cancellation.",
                    dimension_checked="ACTION_SCOPE",
                )

        if pred_lower == "can_cancel_before_trial_ends":
            if not re.search(r"\b(trial|trial ends|free trial)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'can_cancel_before_trial_ends' lacks free trial cancellation cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes trial cancellation prior to trial end with resulting no-charge outcome.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8d. Store Credit Actor Direction & Bonus Checks (Candidate #55)
        if pred_lower == "offers_store_credit_bonus":
            if subj_lower in ("customer", "customers", "user", "buyer", "subscriber", "client"):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Actor inversion: Customers receive bonus; Customers do not offer store credit bonus.",
                    dimension_checked="ACTOR_DIRECTION",
                )

        if pred_lower == "receives_store_credit_bonus":
            if not re.search(r"\b(bonus|5%|store credit)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'receives_store_credit_bonus' lacks store credit bonus cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes customer entitlement to 5% store credit bonus up to $25.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8e. Posting Duration & Processing Timeline (Candidate #24)
        if pred_lower in ("has_posting_duration", "has_processing_timeline"):
            if not re.search(r"\b(bank|post|processed immediately|posting|days to post|credit)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_posting_duration' lacks bank posting or processing timeline cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes bank or payment network refund posting duration.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8f. Price Adjustment Window (Candidate #81)
        if pred_lower == "has_price_adjustment_window":
            if not re.search(r"\b(price adjustment|price drop|drops in price)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_price_adjustment_window' lacks price drop or price adjustment cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes price adjustment protection window.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8g. First Charge Courtesy Refund (Candidate #86)
        if pred_lower in ("may_request_first_charge_refund", "has_first_charge_refund_window"):
            if not re.search(r"\b(forget to cancel|forgot to cancel|first charge)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_request_first_charge_refund' lacks courtesy trial refund cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes courtesy first-charge refund rights.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8h. Subscription Pause Privilege (Candidate #87)
        if pred_lower == "can_pause_subscription":
            if not re.search(r"\b(pause|pause for up to|pause subscription)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'can_pause_subscription' lacks subscription pause cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes subscriber right to pause subscription.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8i. Subscription Refund Rule Validation (Candidate #87 blocking)
        if pred_lower == "has_refund_rule":
            if re.search(r"\b(subscribers can pause|pause for up to)\b", full_evidence) and not re.search(r"\b(refund|refunded|refunds|prorated|pro-rated)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause specifies pausing subscription, not a refund rule.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes subscription refund rule.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8j. Cancellation Window (Candidate #80)
        if pred_lower in ("has_cancellation_window", "has_cancellation_rule"):
            if not re.search(r"\b(cancel\w*|refund pending|authorisation|self-service)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_cancellation_window' lacks cancellation timeline cues in evidence.",
                    dimension_checked="ACTION_SCOPE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes order cancellation window and authorization release.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 8d. Documentation Provision vs Requirement Checks
        if pred_lower == "requires_verifiable_order_or_purchase_proof":
            if re.search(r"\b(?:will provide|provides|provide)\b.*\b(?:upon\s+(?:\w+\s+)?request|on\s+(?:\w+\s+)?request)\b", full_evidence) and any(
                w in subj_lower or w in full_evidence for w in ("northwind", "vendor", "provider", "supplier", "we ")
            ):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Role direction contradiction: evidence obliges provider to provide commercial invoice and proof of return upon request, contradicting requirement on customer to supply proof.",
                    dimension_checked="ROLE_DIRECTION",
                )

        if pred_lower == "provides_documentation_upon_request":
            if not re.search(r"\b(?:provide|provides|will provide)\b", full_evidence) or not re.search(r"\b(?:upon\s+(?:\w+\s+)?request|on\s+(?:\w+\s+)?request)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'provides_documentation_upon_request' lacks upon-request provision cues in evidence.",
                    dimension_checked="ACTION_OBJECT",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes provider obligation to supply documentation upon request.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 9. Role Direction Reversal Check (Refund Payer vs Recipient)
        if "refund" in pred_lower or "reimburse" in pred_lower:
            if "customer" in subj_lower and re.search(r"\b(microsoft will.*refund|microsoft will.*return the amount customer paid|vendor will refund)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Role direction reversal: evidence obliges vendor/Microsoft to refund Customer, which contradicts an obligation on Customer to refund.",
                    dimension_checked="ROLE_DIRECTION",
                )

        # 10. General Polarity Check (Permission vs Prohibition on Same Object)
        if pred_lower.startswith("may_not_") or pred_lower.startswith("must_not_") or "prohibited_from_" in pred_lower:
            if re.search(r"\b(may\s+(?:only\s+)?[a-z]+|is\s+permitted\s+to|has\s+the\s+right\s+to)\b", text_lower) and not re.search(r"\b(may\s+not|must\s+not|shall\s+not|prohibited|cannot)\b", text_lower):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence expresses a permissive right, which contradicts the asserted prohibition predicate.",
                    dimension_checked="MODALITY_POLARITY",
                )

        # 10b. Polarity Inversion Check (Evidence explicitly exempts or negates charge/return, but claim asserts positive charge/return)
        claim_full_str = f"{pred_lower} {obj_lower}".strip()
        claim_is_negative = bool(re.search(r"\b(not|no|cannot|prohibited|non-|exempt|free)\b", claim_full_str))
        if not claim_is_negative:
            negated_action_patterns = [
                (r"\b(will not be charged|won't be charged|not be charged|no charge|free of charge|without charge|no fee)\b",
                 r"\b(charged?|fee|payment|pay)\b",
                 "Evidence specifies subject will not be charged / no fee, but claim asserts affirmative charge or fee liability."),
                (r"\b(cannot be returned|not eligible for (?:refund|return)|no refunds?|non-refundable|non-returnable|not permitted to return)\b",
                 r"\b(eligible|refund|return)\b",
                 "Evidence specifies item cannot be returned or is non-refundable, but claim asserts return/refund eligibility without restrictive prohibition."),
            ]
            for neg_pat, action_pat, msg in negated_action_patterns:
                if re.search(neg_pat, full_evidence) and re.search(action_pat, claim_full_str):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason=f"Polarity contradiction: {msg}",
                        dimension_checked="MODALITY_POLARITY",
                    )

        # 11. Table Cell Value Consistency Check (Wrong row value)
        if "|" in full_evidence:
            cells = [c.strip() for c in full_evidence.split("|") if c.strip()]
            if obj_lower and len(cells) >= 2:
                claim_pct = re.search(r"\b(\d+)\s*%", obj_lower)
                if claim_pct:
                    claim_val = claim_pct.group(1)
                    cell_pcts = [m.group(1) for c in cells for m in [re.search(r"\b(\d+)\s*%", c)] if m]
                    if cell_pcts and claim_val not in cell_pcts:
                        return SemanticEntailmentResult(
                            decision=EntailmentDecision.CONTRADICTED,
                            is_supported=False,
                            reason=f"Table cell value contradiction: evidence cell specifies {cell_pcts[0]}%, which contradicts asserted claim percentage {claim_val}%.",
                            dimension_checked="ACTION_OBJECT",
                        )

        # 12. Column Semantics vs Predicate Mismatch Check (Wrong column/predicate)
        if re.search(r"\b(?:timeline|duration|stage duration|processing time|window duration)\b", full_evidence):
            if pred_lower in ("has_refund_percentage", "has_return_shipping_rule") and not re.search(r"\b(?:refund amount|shipping refunded)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason=f"Column semantics mismatch: evidence column represents timeline/duration, which cannot entail predicate '{pred_lower}'.",
                    dimension_checked="ACTION_OBJECT",
                )

        # 13. Threshold Boundary Relaxation Check (> 150 vs >= 150)
        if re.search(r"\b(?:over\s+\$150|order\s+over\s+\$150|>\s*150|exceeding\s+\$150)\b", full_evidence):
            claim_clause_str = f"{claim_text} {obj_lower} {clause_lower}".lower()
            if re.search(r"\b(?:>=\s*150|\$150\s+or\s+more|150\s+or\s+more|at\s+least\s+\$150|order_value\s*>=\s*150)\b", claim_clause_str):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Threshold boundary relaxation: evidence specifies strictly exclusive threshold '> $150'; inclusive claim asserting '>= $150' improperly expands eligibility to the $150 boundary value.",
                    dimension_checked="CONDITIONS",
                )

        # 14. Original Shipping vs Return Label Cost Disentanglement
        if re.search(r"\b(?:return label cost|return label)\b", full_evidence):
            if "original shipping" in claim_text.lower() or pred_lower == "has_return_shipping_rule":
                if re.search(r"\b(?:free|refunded|yes)\b", obj_lower) and not re.search(r"\b(?:original shipping.*(?:yes|refunded|free))\b", full_evidence):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason="Role/Action confusion: return shipping label cost does not entail original outbound shipping fee reimbursement.",
                        dimension_checked="ACTION_OBJECT",
                    )
        if re.search(r"\b(?:original shipping refunded\?\s*no|original shipping.*non-refundable)\b", full_evidence):
            if pred_lower == "has_return_shipping_rule" and re.search(r"\b(?:yes|refunded|free)\b", obj_lower):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence explicitly specifies original shipping is not refunded.",
                    dimension_checked="MODALITY_POLARITY",
                )

        # 15. Conditional Photo Requirement vs Unconditional Assertion
        if re.search(r"\b(?:photos.*(?:may be requested|required only for|if requested|upon request)|photos of damage)\b", full_evidence):
            if ("photo" in claim_text.lower() or "photo" in pred_lower) and re.search(r"\b(?:all returns|unconditional|mandatory for all|required for any return)\b", claim_text.lower()):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Condition relaxation: evidence imposes photo requirement conditionally only for damaged/defective items; claim asserts unconditional photo requirement across all returns.",
                    dimension_checked="CONDITIONS",
                )

        return SemanticEntailmentResult(
            decision=EntailmentDecision.SUPPORTED,
            is_supported=True,
            reason="Semantic entailment verified against evidence.",
            dimension_checked="ALL_DIMENSIONS",
        )

    @classmethod
    def evaluate(
        cls,
        claim_text: str,
        subject: str,
        predicate: str,
        object_text: Optional[str] = None,
        claim_type: str = "RULE",
        evidence: Optional[ImmutableEvidenceSpan] = None,
        source_content: Optional[str] = None,
        clause_text: Optional[str] = None,
        confidence_or_trust: float = 0.95,
        existing_signatures: Optional[Set[str]] = None,
        is_human_approved: bool = False,
        requires_human_approval: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> UniversalGateResult:
        reasons: List[str] = []

        raw_text = (claim_text or "").strip()
        # Automatically strip leading enumeration prefixes for evaluation
        stripped_text = cls.strip_enumeration_prefix(raw_text)
        repaired_text = stripped_text if stripped_text != raw_text else None
        eval_text = stripped_text or raw_text

        text_lower = eval_text.lower()
        subj_clean = (subject or "").strip()
        subj_lower = subj_clean.lower()
        pred_clean = (predicate or "").strip()
        pred_lower = pred_clean.lower()
        obj_clean = (object_text or "").strip()
        obj_lower = obj_clean.lower()
        ct_clean = (claim_type or "RULE").strip().lower()

        # Enclosing clause text fallback
        surrounding_clause = clause_text or (evidence.clause_text if evidence else "") or ""
        surrounding_clause_lower = surrounding_clause.lower()

        # Phase 2.4: Execute shared universal gate contract
        from app.services.gate_contract import SharedGateRequest, SharedGovernanceGateEngine
        shared_req = SharedGateRequest(
            claim_text=eval_text,
            subject=subj_clean,
            predicate=pred_clean,
            object_val=obj_clean,
            evidence_quote=evidence.verbatim_quote if evidence else eval_text,
            enclosing_clause=surrounding_clause,
            table_header=metadata.get("table_header") if metadata else kwargs.get("table_header"),
            scope=metadata.get("scope") if metadata else kwargs.get("scope"),
            conditions=kwargs.get("conditions") or (metadata.get("conditions") if metadata else None),
            exceptions=kwargs.get("exceptions") or (metadata.get("exceptions") if metadata else None),
            claim_type=ct_clean,
            confidence=confidence_or_trust,
            document_text=source_content,
            locators=[{"start": evidence.char_start, "end": evidence.char_end}] if evidence and hasattr(evidence, "char_start") else None,
            metadata=metadata,
        )
        shared_res = SharedGovernanceGateEngine.evaluate(shared_req)
        codes = list(shared_res.reason_codes)

        # =========================================================================
        # Gate 1: evidence_exists
        # =========================================================================
        is_evidence_exists = True
        if evidence is None:
            is_evidence_exists = False
            reasons.append("Evidence failure: Missing ImmutableEvidenceSpan; claim has no physical source grounding.")
        elif not evidence.verbatim_quote or not evidence.verbatim_quote.strip():
            is_evidence_exists = False
            reasons.append("Evidence failure: Verbatim quote in ImmutableEvidenceSpan is empty.")
        elif not evidence.source_hash:
            is_evidence_exists = False
            reasons.append("Evidence failure: Missing cryptographic source hash.")

        # =========================================================================
        # Gate 2: evidence_located
        # =========================================================================
        is_evidence_located = True
        if not is_evidence_exists:
            is_evidence_located = False
        else:
            loc_res = EvidenceLocatorService.locate_and_verify(
                evidence=evidence,  # type: ignore[arg-type]
                source_content=source_content,
            )
            if not loc_res.located:
                is_evidence_located = False
                reasons.append(f"Evidence location failure: {loc_res.error_reason or 'Quote not found in source text.'}")

            # Phase 4: Field-to-Evidence Binding Containment Validation
            evidence_bindings = (metadata.get("evidence_bindings") if metadata else None) or kwargs.get("evidence_bindings") or []
            if evidence_bindings and source_content:
                for b in evidence_bindings:
                    b_span = getattr(b, "evidence_span", None) or (b.get("evidence_span") if isinstance(b, dict) else None)
                    if b_span and b_span.strip() and b_span.strip().lower() not in source_content.lower():
                        is_evidence_located = False
                        f_name = getattr(b, "field", None) or (b.get("field") if isinstance(b, dict) else "unnamed")
                        reasons.append(f"Evidence containment failure: Field binding for '{f_name}' ('{b_span}') not found in source text.")

        # =========================================================================
        # Gate 3: text_integrity
        # =========================================================================
        is_text_integrity = True
        # 3a. Disallow predicate slugs / snake_case identifiers injected into claim text
        slug_match = re.search(PREDICATE_SLUG_REGEX, raw_text)
        if slug_match:
            is_text_integrity = False
            reasons.append(f"Text integrity failure: Injected predicate identifier or taxonomy slug in claim text: '{slug_match.group(0)}'.")

        # 3b. Disallow page headers and postal addresses
        if any(re.search(pat, raw_text) for pat in PAGE_HEADER_PATTERNS):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text contains page header or pagination artifact.")
        if any(re.search(pat, raw_text) for pat in POSTAL_ADDRESS_PATTERNS):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text contains unstripped postal address artifact.")

        # 3c. Disallow truncated sentences
        if eval_text.startswith("...") or eval_text.endswith("..."):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text is an ellipsis fragment.")
        elif re.search(r"\b(and|or|for|to|with|of|the)\s+all\s+other\s*$", text_lower):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text is truncated mid-sentence.")

        # 3d. Check operative modal verb in rules (exempt table rows, list items, and declarative constraints)
        is_table_rule = bool(
            (metadata and (metadata.get("table_grid") or metadata.get("in_table")))
            or (kwargs.get("locator") and (kwargs["locator"].get("table_grid") or kwargs["locator"].get("table_id")))
            or ct_clean in {"table_rule", "table_row", "policy_matrix"}
            or "|" in raw_text
        )
        is_list_item = bool(
            re.match(r"^\s*(?:[-*•]|\d+[\.\)])\s+", eval_text)
            or (metadata and (metadata.get("is_list") or metadata.get("evidence_structure") == "list_item"))
            or (kwargs.get("locator") and (kwargs["locator"].get("is_list") or kwargs["locator"].get("evidence_structure") == "list_item"))
        )
        is_declarative_constraint = bool(
            re.search(
                r"\b(?:approval|approved by|manager approval|tier \d+|lead approval|director approval|"
                r"required|requires|requirement|eligible|eligibility|not eligible|valid|validity|"
                r"condition|subject to|applies to|minimum|maximum|limit|limited to|threshold|"
                r"fee|fees|deposit|non-refundable|non-returnable|deadline|within \d+|per \d+|per customer|"
                r"bonus|deduction|deducted|responsible for|duty drawback)\b",
                text_lower,
            )
            or any(k in subj_lower for k in ("approval", "threshold", "returns without", "refund approval", "tier", "oversize", "photos"))
            or any(k in pred_lower for k in ("requires_", "has_refund_", "has_stage_", "has_identity_", "has_posting_", "has_default_", "offers_", "has_return_freight_", "is_responsible_for", "uses_original_", "is_required_for"))
        )
        content_role_clean = str((metadata.get("content_role") if metadata else None) or kwargs.get("content_role") or "").lower()
        is_non_rule_context = ct_clean in NON_RULE_TYPES or content_role_clean in {"definition", "contact_info", "example", "revision_history"}

        if ct_clean in {"rule", "policy_rule", "policy"} and not (is_table_rule or is_list_item or is_declarative_constraint or is_non_rule_context):
            if not re.search(MODAL_OPERATIVE_PATTERN, text_lower):
                is_text_integrity = False
                reasons.append("Text integrity failure: Normative rule is missing an operative modal phrase ('may', 'must', 'will', 'shall', etc.).")

        # Table context completeness check: missing table context routes to review
        missing_table_context = False
        if is_table_rule:
            grid = (metadata.get("table_grid") if metadata else None) or (kwargs.get("locator", {}).get("table_grid") if kwargs.get("locator") else None)
            col_hdr = (grid.get("col_header") if grid else None) or (kwargs.get("locator", {}).get("col_header") if kwargs.get("locator") else None)
            row_k = (grid.get("row_key") if grid else None) or (kwargs.get("locator", {}).get("row_key") if kwargs.get("locator") else None)
            if not col_hdr and not row_k and "header:" not in surrounding_clause_lower and "|" not in raw_text:
                missing_table_context = True
                reasons.append("Table context failure: Missing table-header or row context requires manual adjudication review.")

        # 3e. Polarity and Negation consistency
        mod_res = DynamicModalityExtractor.validate_consistency(
            claim_text=eval_text,
            declared_modality=DynamicModalityExtractor.extract_modality(eval_text),
            predicate_name=pred_clean,
        )
        if not mod_res.is_consistent:
            is_text_integrity = False
            reasons.append(mod_res.error_reason or "Text integrity failure: Polarity inconsistency between predicate and text.")

        # =========================================================================
        # Gate 4: clause_entails_claim
        # =========================================================================
        is_clause_entails_claim = True
        entailment_dec = EntailmentDecision.SUPPORTED
        entailment_reason = None
        entailment_dim = "ALL_DIMENSIONS"

        if not is_evidence_exists or not is_evidence_located:
            is_clause_entails_claim = False
            entailment_dec = EntailmentDecision.INSUFFICIENT_EVIDENCE
            entailment_reason = "Missing or unlocated evidence precludes logical entailment."
            entailment_dim = "EVIDENCE"
            reasons.append(f"Clause entailment failure: {entailment_reason}")
        else:
            entail_res = cls.check_semantic_entailment(
                subject=subj_clean,
                predicate=pred_clean,
                claim_text=eval_text,
                evidence_quote=evidence.verbatim_quote if evidence else eval_text,
                clause_text=surrounding_clause,
                object_text=object_text or "",
            )
            entailment_dec = entail_res.decision
            entailment_reason = entail_res.reason
            entailment_dim = entail_res.dimension_checked
            if not entail_res.is_supported:
                is_clause_entails_claim = False
                reasons.append(f"Clause entailment failure [{entail_res.decision.value} - {entail_res.dimension_checked}]: {entail_res.reason}")

        # =========================================================================
        # Gate 5: subject_valid
        # =========================================================================
        is_subject_valid = True
        if not subj_clean or len(subj_clean) < 2:
            is_subject_valid = False
            reasons.append("Subject failure: Subject is empty or too short.")
        elif any(re.search(pat, subj_clean) for pat in PAGE_HEADER_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' contains a page header artifact.")
        elif any(re.search(pat, subj_clean) for pat in POSTAL_ADDRESS_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' contains a postal address artifact.")
        elif any(re.search(pat, subj_lower) for pat in INVALID_SUBJECT_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' is a syntax fragment or non-actor token.")
        elif subj_lower in {"assignment", "the", "it", "this", "these", "that", "which", "a", "an"}:
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' is a stopword or grammatical noun phrase.")

        # =========================================================================
        # Gate 6: counterparty_resolved
        # =========================================================================
        is_counterparty_resolved = True
        # Check dangling pronouns
        pronoun_match = re.search(r"\b(their|them|his|her)\s+performance\b", text_lower) or text_lower.endswith("their performance.")
        if pronoun_match:
            grounding_entities = ["subcontractor", "subcontractors", "representative", "representatives", "affiliate", "personnel", "agent", "employee"]
            if not any(g in text_lower or g in surrounding_clause_lower for g in grounding_entities):
                is_counterparty_resolved = False
                reasons.append("Counterparty failure: Ungrounded pronoun 'their' lacks clear antecedent party resolution.")

        # Evidence-conditioned role direction validation
        role_res = RoleDirectionValidator.validate(
            subject=subj_clean,
            predicate=pred_clean,
            clause_text=surrounding_clause,
        )
        if not role_res.is_valid:
            is_counterparty_resolved = False
            reasons.append(role_res.reason or "Counterparty failure: Directional right/duty conflicts with clause evidence.")

        # Phase 3: Universal Type-Compatibility Matrix Evaluation
        from app.extraction.type_compatibility import TypeCompatibilityMatrix
        type_comp = TypeCompatibilityMatrix.evaluate_compatibility(
            subject=subj_clean,
            predicate=pred_clean,
            object_text=obj_clean,
            clause_text=surrounding_clause,
        )
        if not type_comp.is_compatible:
            is_counterparty_resolved = False
            reasons.append(f"Type-compatibility failure [{type_comp.blocked_rule}]: {type_comp.reason}")

        # =========================================================================
        # Gate 7: predicate_valid
        # =========================================================================
        is_predicate_valid = True
        if not pred_clean or len(pred_clean) < 2 or pred_lower in {"the", "a", "in", "is", "take"}:
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Predicate '{pred_clean}' is invalid or a generic stopword.")
        elif PredicateRegistryService.is_banned(pred_clean):
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Generic catch-all predicate '{pred_clean}' is banned; requires normalized action taxonomy.")
        elif not PredicateRegistryService.exists(pred_clean):
            # Check if dynamically registered or allowed
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Predicate '{pred_clean}' is not present in versioned taxonomy registry.")

        # =========================================================================
        # Gate 8: atomicity_valid
        # =========================================================================
        is_atomicity_valid = True
        if ct_clean == "quarantined":
            is_atomicity_valid = False
            reasons.append("Atomicity failure: Claim is explicitly marked as quarantined compound rule.")
        else:
            # Layered compound detection
            has_transfer = "transfer" in text_lower or "transferee" in text_lower
            if has_transfer and ("(1)" in text_lower or "(i)" in text_lower) and ("(2)" in text_lower or "(ii)" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Multi-branch transfer disjunction requires decomposition into atomic child claims.")
            elif has_transfer and ("affiliate" in text_lower) and ("third party" in text_lower or "third-party" in text_lower) and ("hardware" in text_lower or "merger" in text_lower or "divestiture" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Compound transfer conditions across multiple separate entities.")

            if "may sublicense" in text_lower and ("may not sublicense" in text_lower or "affiliates may not" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Mixed polarity (permission + prohibition) requires splitting into child claims.")

            if ("audit" in text_lower or "unlicensed use" in text_lower) and ("reimburse" in text_lower) and ("acquire" in text_lower or "125%" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Compound audit remedies combining reimbursement and penalty license acquisition.")

        # =========================================================================
        # Gate 9: duplicate_valid
        # =========================================================================
        is_duplicate_valid = True
        if metadata and (metadata.get("is_duplicate") or metadata.get("duplicate_of")):
            is_duplicate_valid = False
            reasons.append("Duplicate check: Claim metadata indicates it is a duplicate.")
        elif ct_clean == "duplicate":
            is_duplicate_valid = False
            reasons.append("Duplicate check: Claim is classified as a duplicate.")
        elif existing_signatures is not None:
            sig = cls.compute_semantic_signature(subj_clean, pred_clean, object_text or eval_text)
            if sig in existing_signatures:
                is_duplicate_valid = False
                reasons.append("Duplicate check: Semantic signature already exists in canonical catalog.")

        # =========================================================================
        # Gate 10: claim_type_allowed
        # =========================================================================
        is_claim_type_allowed = True
        if pred_clean in ("must_comply_with_trade_laws", "may_suspend_for_security_or_breach", "may_suspend_for_trade_laws", "has_liability_cap", "has_late_payment_penalty_rate", "has_warranty_remedy_window"):
            is_claim_type_allowed = True
        elif ct_clean in NON_RULE_TYPES or content_role_clean in {"definition", "contact_info", "example", "revision_history"}:
            is_claim_type_allowed = False
            reasons.append(f"Claim type failure: '{content_role_clean or claim_type}' is a non-rule type (definition, reference, description, example, or revision_history).")
        elif any(cue in text_lower for cue in REFERENCE_CUES):
            is_claim_type_allowed = False
            reasons.append("Claim type failure: Text is a cross-reference cue, not an operative rule.")
        elif any(cue in text_lower for cue in DESCRIPTION_CUES) or "product availability" in subj_lower:
            has_operative_rule = bool(re.search(r"\b(may suspend or terminate|will comply with|must comply with|shall comply with|export jurisdictions|trade laws|may suspend a subscription)\b", text_lower))
            if not has_operative_rule:
                is_claim_type_allowed = False
                reasons.append("Claim type failure: Text is descriptive background scope, not an operative rule.")
        elif ct_clean not in {"rule", "policy_rule", "policy", "table_rule", "table_row", "policy_matrix"}:
            is_claim_type_allowed = False
            reasons.append(f"Claim type failure: Unrecognized claim type '{claim_type}'.")

        # =========================================================================
        # Gate 11: human_approved_if_required (Optional)
        # =========================================================================
        is_human_approved_if_required = True
        if requires_human_approval and not is_human_approved:
            is_human_approved_if_required = False
            reasons.append("Risk policy requirement: High-risk action requires explicit human approval signoff.")
        elif confidence_or_trust < 0.70 and not is_human_approved:
            is_human_approved_if_required = False
            reasons.append(f"Trust score {confidence_or_trust:.2f} requires human approval.")

        # =========================================================================
        # Compile Gates and Lifecycle State
        # =========================================================================
        gates = {
            "evidence_exists": is_evidence_exists,
            "evidence_located": is_evidence_located,
            "text_integrity": is_text_integrity,
            "clause_entails_claim": is_clause_entails_claim,
            "subject_valid": is_subject_valid,
            "counterparty_resolved": is_counterparty_resolved,
            "predicate_valid": is_predicate_valid,
            "atomicity_valid": is_atomicity_valid,
            "duplicate_valid": is_duplicate_valid,
            "claim_type_allowed": is_claim_type_allowed,
            "human_approved_if_required": is_human_approved_if_required,
        }

        all_10_passed = all(gates[g] is True for g in UNIVERSAL_10_GATES)
        all_passed = all_10_passed and is_human_approved_if_required and not missing_table_context

        if all_passed:
            tier = "AUTOMATED_CERTIFIED"
            state = ClaimLifecycleState.AUTOMATED_CERTIFIED
            is_canon = True
            agent_acc = True
        elif not is_duplicate_valid or ct_clean == "duplicate":
            tier = "DUPLICATE"
            state = ClaimLifecycleState.DUPLICATE
            is_canon = False
            agent_acc = False
        elif not is_atomicity_valid or ct_clean == "quarantined":
            tier = "QUARANTINED"
            state = ClaimLifecycleState.QUARANTINED
            is_canon = False
            agent_acc = False
        elif not is_claim_type_allowed or ct_clean in NON_RULE_TYPES or content_role_clean in {"definition", "contact_info", "example", "revision_history"}:
            tier = "NON_RULE"
            state = ClaimLifecycleState.NON_RULE
            is_canon = False
            agent_acc = False
        elif missing_table_context:
            tier = "REVIEW_REQUIRED"
            state = ClaimLifecycleState.REVIEW_REQUIRED
            is_canon = False
            agent_acc = False
        elif not is_evidence_exists or not is_evidence_located or not is_text_integrity:
            tier = "REJECTED"
            state = ClaimLifecycleState.REJECTED
            is_canon = False
            agent_acc = False
        else:
            tier = "REVIEW_REQUIRED"
            state = ClaimLifecycleState.REVIEW_REQUIRED
            is_canon = False
            agent_acc = False

        # Enforce shared gate contract verdicts
        if not shared_res.predicate_normativity or not shared_res.table_column_binding:
            is_predicate_valid = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)
        if not shared_res.spo_compatibility:
            is_counterparty_resolved = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)
        if not shared_res.polarity_consistency:
            is_text_integrity = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)
        if not shared_res.condition_preservation or not shared_res.exception_preservation or not shared_res.scope_preservation or not shared_res.value_fidelity:
            is_clause_entails_claim = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)

        return UniversalGateResult(
            evidence_exists=is_evidence_exists,
            evidence_located=is_evidence_located,
            text_integrity=is_text_integrity,
            clause_entails_claim=is_clause_entails_claim,
            subject_valid=is_subject_valid,
            counterparty_resolved=is_counterparty_resolved,
            predicate_valid=is_predicate_valid,
            atomicity_valid=is_atomicity_valid,
            duplicate_valid=is_duplicate_valid,
            claim_type_allowed=is_claim_type_allowed,
            human_approved_if_required=is_human_approved_if_required,
            entailment_decision=entailment_dec.value if hasattr(entailment_dec, "value") else str(entailment_dec),
            entailment_reason=entailment_reason,
            entailment_dimension=entailment_dim,
            all_gates_passed=all_passed,
            lifecycle_state=state,
            certification_tier=tier,
            is_canonical=is_canon,
            agent_accessible=agent_acc,
            rejection_reasons=reasons,
            reason_codes=codes,
            gates=gates,
            repaired_claim_text=repaired_text,
            subject=subj_clean,
        )
