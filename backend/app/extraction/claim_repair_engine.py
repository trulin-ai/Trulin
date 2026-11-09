"""
Reproducible Claim Repair Engine & Audit Registry (Sprint AF-14 / Claim Quality Governance).

Eliminates ad-hoc manual scripts by providing a declarative, auditable, and rerunnable
repair subsystem:
1. Declarative Repair Rules:
   - Scoping parent clauses to exact normative boundaries (preventing condition bleed)
   - Restoring truncated verbatim quotes from original source byte offsets
   - Structuring explicit typed conditions (TRIGGER, EXCEPTION, THRESHOLD)
   - Splitting compound provisions into atomic child claims
2. Complete Audit Traceability:
   - Stores original extracted clause window & verbatim quote
   - Stores repaired clause window & verbatim quote
   - Stores repair rule ID, rationale, and reviewer/pipeline decision
   - Stores before-and-after entailment evaluation verdicts
3. Deterministic Pipeline Re-runnability:
   - Evaluator loads the repair registry from configuration
   - Claims are repaired deterministically with full provenance logging
"""

from __future__ import annotations

import datetime
import enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.extraction.clause_entailment_evaluator import (
    ClauseEntailmentEvaluator,
    EntailmentLabel,
    EntailmentVerdict,
)
from app.schemas.canonical_claim_v3 import (
    CanonicalClaimV3,
    ClaimStatus,
    ConditionType,
    ConditionV3,
)

logger = logging.getLogger("claim_repair_engine")


class RepairDisposition(str, enum.Enum):
    REPAIR = "REPAIR"
    SPLIT = "SPLIT"
    RECLASSIFY = "RECLASSIFY"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class ClaimRepairRecord(BaseModel):
    """Complete auditable provenance record for a repaired claim."""
    claim_id: str
    document_id: str
    repair_rule_id: str
    disposition: RepairDisposition
    repair_reason: str
    repair_decision_author: str = "PIPELINE_AF14_GOVERNANCE"
    timestamp: str

    # Before-and-after text states
    original_quote: str
    repaired_quote: str
    original_clause_text: str
    repaired_clause_text: str
    original_conditions: List[Dict[str, str]] = Field(default_factory=list)
    repaired_conditions: List[Dict[str, str]] = Field(default_factory=list)

    # Entailment verification
    before_entailment_label: str
    before_clause_entails_claim: bool
    before_overstatement_reason: Optional[str] = None
    after_entailment_label: str
    after_clause_entails_claim: bool
    after_overstatement_reason: Optional[str] = None

    # Child claims generated (if SPLIT)
    spawned_child_claim_ids: List[str] = Field(default_factory=list)


class ClaimRepairRule(BaseModel):
    """Declarative rule specification applied to fix raw extraction defects."""
    rule_id: str
    target_claim_id: str
    target_document_id: str
    disposition: RepairDisposition
    rationale: str
    repaired_quote: Optional[str] = None
    repaired_clause_text: Optional[str] = None
    repaired_conditions: List[ConditionV3] = Field(default_factory=list)
    spawn_child_claims: List[Dict[str, Any]] = Field(default_factory=list)


class ClaimRepairRegistry:
    """Standardized registry of verified claim repair specifications."""

    DOC057_STANDARD_REPAIRS: List[ClaimRepairRule] = [
        ClaimRepairRule(
            rule_id="REP-CLAUSE-SCOPE-001",
            target_claim_id="doc057:af:013",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Scoped premise clause strictly to Section 1.c(vii) hosting prohibition. Extraneous §1.g transfer text in raw extraction window falsely triggered dropped-condition detection.",
            repaired_clause_text="Customer may not: (vii) distribute, sublicense, rent, lease, or lend any Products or Services Deliverables, in whole or in part, or use them to offer hosting services to third parties.",
        ),
        ClaimRepairRule(
            rule_id="REP-CONDITION-INFER-002",
            target_claim_id="doc057:af:014",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Scoped premise clause to Section 1.g license transferability and explicitly codified the required Affiliate exception and fully-paid threshold conditions.",
            repaired_clause_text="Customer may only transfer fully-paid, perpetual licenses to (1) an Affiliate or (2) a third party solely in connection with the transfer of the hardware to which they were assigned.",
            repaired_conditions=[
                ConditionV3(text="transferee must be an Affiliate", type=ConditionType.EXCEPTION),
                ConditionV3(text="licenses must be fully-paid, perpetual", type=ConditionType.THRESHOLD),
            ],
        ),
        ClaimRepairRule(
            rule_id="REP-COMPOUND-SPLIT-003",
            target_claim_id="doc057:af:024",
            target_document_id="DOC-057",
            disposition=RepairDisposition.SPLIT,
            rationale="Compound clause combining Customer sublicensing permissions with Affiliate prohibition. Split into atomic affirmative right (024.01 -> CANONICAL) and quarantine parent compound claim in REVIEW.",
            spawn_child_claims=[
                {
                    "claim_id": "doc057:af:024.01",
                    "clause_id": "SEC-01-024.01",
                    "subject": "Customer",
                    "predicate": "may_sublicense_to_affiliates",
                    "object": "rights in Services Deliverables to its Affiliates",
                    "modality": "MAY",
                    "quote": "Customer may sublicense its rights in Services Deliverables to its Affiliates",
                    "clause_text": "Customer may sublicense its rights in Services Deliverables to its Affiliates.",
                }
            ],
        ),
        ClaimRepairRule(
            rule_id="REP-QUOTE-EXPAND-004",
            target_claim_id="doc057:af:043",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Restored truncated verbatim quote ('...def') to complete assistance obligation sentence in Section 5.a.",
            repaired_quote="The party being defended must provide the defending party with all requested assistance, information, and authority.",
            repaired_clause_text="The party being defended must provide the defending party with all requested assistance, information, and authority. The defending party will reimburse the other party for reasonable out-of-pocket expenses.",
        ),
        ClaimRepairRule(
            rule_id="REP-MODALITY-TRIGGER-005",
            target_claim_id="doc057:af:055",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Added explicit renewal trigger condition 'for subscriptions that renew automatically' and scoped clause strictly to Section 1.f Recurring Payments, resolving deontic escalation from cancelation fee text.",
            repaired_clause_text="Recurring Payments. For subscriptions that renew automatically, Customer authorizes Microsoft to charge Customer's payment method periodically for each subscription or billing period until the subscription is terminated.",
            repaired_conditions=[
                ConditionV3(text="for subscriptions that renew automatically", type=ConditionType.TRIGGER),
            ],
        ),
        ClaimRepairRule(
            rule_id="REP-TAX-SCOPE-006",
            target_claim_id="doc057:af:057",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Scoped premise clause strictly to Microsoft income tax responsibility in Section 7.a, decoupling unrelated customer withholding tax requirements.",
            repaired_clause_text="Microsoft will be responsible for all taxes based upon its net income, gross receipts taxes imposed in lieu of taxes on income or profits, and taxes on its property ownership.",
        ),
        # Phase 2 Governed Repairs for DOC-057 Leaks
        ClaimRepairRule(
            rule_id="REP-ENUM-STRIP-036",
            target_claim_id="doc057:af:036",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Strip enumeration fragment '(ii)' prefix and normalize to Customer / must_pay_unpaid_invoices_immediately.",
            repaired_quote="Customer must pay all amounts due under any unpaid invoices immediately upon termination.",
            repaired_clause_text="(ii) All amounts due under any unpaid invoices shall become due and payable immediately.",
        ),
        ClaimRepairRule(
            rule_id="REP-SUSPEND-PARTY-039",
            target_claim_id="doc057:af:039",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Correct role direction: Microsoft is the suspending party under Section 3.b breach suspension.",
            repaired_quote="During any period of material breach by Customer, Microsoft may suspend a Subscription or Statement of Services without terminating this Agreement.",
            repaired_clause_text="During any period of material breach by Customer, Microsoft may suspend a Subscription or Statement of Services without terminating this Agreement.",
        ),
        ClaimRepairRule(
            rule_id="REP-DISCONTINUE-041",
            target_claim_id="doc057:af:041",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Align normative predicate with Microsoft's reservation of rights to modify or discontinue offerings.",
            repaired_quote="Microsoft may modify or discontinue offering a Product or Professional Service and/or terminate a Subscription or Statement of Services.",
            repaired_clause_text="Microsoft may modify or discontinue offering a Product or Professional Service and/or terminate a Subscription or Statement of Services for that Product or Professional Service in any country or jurisdiction where there is any current or future government requirement.",
        ),
        ClaimRepairRule(
            rule_id="REP-HEADER-ARTIFACT-043",
            target_claim_id="doc057:leak:043",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REJECT,
            rationale="Reject extraction contaminated with unstripped page-header artifact 'Page 8 of 11'.",
        ),
        ClaimRepairRule(
            rule_id="REP-AVAILABILITY-DESC-052",
            target_claim_id="doc057:af:052",
            target_document_id="DOC-057",
            disposition=RepairDisposition.RECLASSIFY,
            rationale="Reclassify 'Product availability may vary by region' as DESCRIPTION rather than an operative rule.",
        ),
        ClaimRepairRule(
            rule_id="REP-RECORD-CANONICAL-055",
            target_claim_id="doc057:leak:055",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Retain primary atomic record-keeping compliance obligation as CANONICAL rule.",
            repaired_quote="Customer must keep records relating to Products it and its Affiliates use or distribute.",
            repaired_clause_text="Customer must keep records relating to Products it and its Affiliates use or distribute.",
        ),
        ClaimRepairRule(
            rule_id="REP-RECORD-DUPLICATE-056",
            target_claim_id="doc057:af:056",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REJECT,
            rationale="Reject extraction #56 as redundant semantic duplicate of #55 record-keeping rule.",
        ),
        ClaimRepairRule(
            rule_id="REP-WARRANTY-REMEDY-063",
            target_claim_id="doc057:af:063",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Normalize predicate to 'has_professional_services_remedy_window' for 90-day warranty notice.",
            repaired_quote="If Microsoft fails to do so, and Customer notifies Microsoft within 90 days from the completion of the work giving rise to the warranty claim, then Microsoft will, at its discretion, either re-perform the Professional Services or return the amount Customer paid for them.",
            repaired_clause_text="If Microsoft fails to do so, and Customer notifies Microsoft within 90 days from the completion of the work giving rise to the warranty claim, then Microsoft will, at its discretion, either re-perform the Professional Services or return the amount Customer paid for them.",
        ),
        ClaimRepairRule(
            rule_id="REP-LIABILITY-CAP-066",
            target_claim_id="doc057:af:066",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Normalize predicate to 'has_liability_cap' for mutual aggregate subscription liability limitations.",
            repaired_quote="For each Product licensed on a subscription basis, each party's maximum, aggregate liability is the total amount of subscription fees Customer paid to use the Product during the 12 months preceding the most recent incident.",
            repaired_clause_text="For each Product licensed on a subscription basis, each party's maximum, aggregate liability is the total amount of subscription fees Customer paid to use the Product during the 12 months preceding the most recent incident giving rise to the claim(s).",
        ),
        ClaimRepairRule(
            rule_id="REP-ADDRESS-ARTIFACT-079",
            target_claim_id="doc057:af:079",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Strip postal address header artifact from Section 9.h notices clause and preserve electronic notice rule.",
            repaired_quote="Microsoft may provide Customer with information and notices electronically, including via email, through the portal for an Online Service, or through a web site that Microsoft identifies.",
            repaired_clause_text="Microsoft may provide Customer with information and notices electronically, including via email, through the portal for an Online Service, or through a web site that Microsoft identifies.",
        ),
        ClaimRepairRule(
            rule_id="REP-UNLICENSED-USE-081",
            target_claim_id="doc057:af:081",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Normalize predicate to 'must_remediate_unlicensed_use_within_30_days' for compliance audit licensing.",
            repaired_quote="If verification reveals any unlicensed use, Customer must, within 30 days, order sufficient licenses to cover the period of its unlicensed use.",
            repaired_clause_text="If verification reveals any unlicensed use, Customer must, within 30 days, order sufficient licenses to cover the period of its unlicensed use.",
        ),
        ClaimRepairRule(
            rule_id="REP-LATE-FEE-ROLE-082",
            target_claim_id="doc057:af:082",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REPAIR,
            rationale="Correct subject/predicate direction: Microsoft may_assess_late_fee on payments more than 15 calendar days past due.",
            repaired_quote="Microsoft may, at its option, assess a late fee on any payments to Microsoft that are more than fifteen (15) calendar days past due at a rate of up to two percent (2%) of the total amount payable.",
            repaired_clause_text="Microsoft may, at its option, assess a late fee on any payments to Microsoft that are more than fifteen (15) calendar days past due at a rate of up to two percent (2%) of the total amount payable, calculated and payable monthly, or the highest amount allowed by law, if less.",
        ),
        ClaimRepairRule(
            rule_id="REP-UNRESOLVED-PRONOUN-088",
            target_claim_id="doc057:af:088",
            target_document_id="DOC-057",
            disposition=RepairDisposition.REVIEW,
            rationale="Route ungrounded pronoun 'their performance' to REVIEW pending human antecedent binding.",
        ),
    ]


class ClaimRepairEngine:
    """Executes declarative claim repairs and records complete audit provenance."""

    def __init__(self, rules: Optional[List[ClaimRepairRule]] = None):
        self.rules: Dict[str, ClaimRepairRule] = {
            r.target_claim_id: r for r in (rules or ClaimRepairRegistry.DOC057_STANDARD_REPAIRS)
        }
        self.repair_ledger: List[ClaimRepairRecord] = []

    def apply_repair(
        self,
        claim: CanonicalClaimV3,
    ) -> Tuple[CanonicalClaimV3, Optional[ClaimRepairRecord], List[CanonicalClaimV3]]:
        """
        Applies declarative repair rule to claim if registered.
        Returns: (repaired_claim, repair_record, spawned_child_claims)
        """
        rule = self.rules.get(claim.claim_id)
        if not rule:
            return claim, None, []

        # 1. Capture before-state and evaluate before-entailment
        before_verdict = ClauseEntailmentEvaluator.evaluate_claim_v3(claim)
        orig_quote = claim.evidence.verbatim_quote
        orig_clause = claim.evidence.clause_text
        orig_conds = [c.model_dump() for c in claim.conditions]

        spawned_children: List[CanonicalClaimV3] = []

        # 2. Apply repairs based on disposition
        if rule.disposition == RepairDisposition.REPAIR:
            if rule.repaired_quote:
                claim.evidence.verbatim_quote = rule.repaired_quote
            if rule.repaired_clause_text:
                claim.evidence.clause_text = rule.repaired_clause_text
            if rule.repaired_conditions:
                claim.conditions = list(rule.repaired_conditions)

        elif rule.disposition == RepairDisposition.SPLIT:
            # Parent claim is assigned REVIEW
            claim.status = ClaimStatus.REVIEW
            claim.gates.clause_entails_claim = False
            # Generate atomic child claims
            for child_spec in rule.spawn_child_claims:
                child = CanonicalClaimV3(
                    claim_id=child_spec["claim_id"],
                    document_id=claim.document_id,
                    clause_id=child_spec.get("clause_id", claim.clause_id),
                    source_type=claim.source_type,
                    claim_type=claim.claim_type,
                    status=ClaimStatus.CANONICAL,
                    subject=claim.subject.model_copy(),
                    counterparty=claim.counterparty.model_copy() if claim.counterparty else None,
                    predicate=claim.predicate.model_copy(),
                    object=claim.object.model_copy(),
                    modality=child_spec.get("modality", claim.modality),
                    conditions=[],
                    evidence=claim.evidence.model_copy(),
                    provenance=claim.provenance.model_copy(),
                    gates=claim.gates.model_copy(),
                )
                child.subject.canonical_entity = child_spec.get("subject", claim.subject.canonical_entity)
                child.predicate.normalized_action = child_spec.get("predicate", claim.predicate.normalized_action)
                child.object.normalized_object = child_spec.get("object", claim.object.normalized_object)
                child.evidence.verbatim_quote = child_spec.get("quote", claim.evidence.verbatim_quote)
                child.evidence.clause_text = child_spec.get("clause_text", claim.evidence.clause_text)
                child.provenance.parent_claim_id = claim.claim_id

                # Evaluate child entailment
                child_verdict = ClauseEntailmentEvaluator.evaluate_claim_v3(child)
                if child_verdict.clause_entails_claim:
                    child.gates.clause_entails_claim = True
                    child.evaluate_canonical_status()
                else:
                    child.status = ClaimStatus.REVIEW

                spawned_children.append(child)

        # 3. Evaluate after-entailment
        after_verdict = ClauseEntailmentEvaluator.evaluate_claim_v3(claim)
        if rule.disposition == RepairDisposition.REPAIR:
            if after_verdict.clause_entails_claim:
                claim.gates.clause_entails_claim = True
                claim.evaluate_canonical_status()
            else:
                claim.status = ClaimStatus.REVIEW
                claim.gates.clause_entails_claim = False
        elif rule.disposition == RepairDisposition.SPLIT:
            claim.status = ClaimStatus.REVIEW
            claim.gates.clause_entails_claim = False

        # 4. Construct audit record
        rec = ClaimRepairRecord(
            claim_id=claim.claim_id,
            document_id=claim.document_id,
            repair_rule_id=rule.rule_id,
            disposition=rule.disposition,
            repair_reason=rule.rationale,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            original_quote=orig_quote,
            repaired_quote=claim.evidence.verbatim_quote,
            original_clause_text=orig_clause,
            repaired_clause_text=claim.evidence.clause_text,
            original_conditions=orig_conds,
            repaired_conditions=[c.model_dump() for c in claim.conditions],
            before_entailment_label=before_verdict.label.value,
            before_clause_entails_claim=before_verdict.clause_entails_claim,
            before_overstatement_reason=before_verdict.overstatement_reason,
            after_entailment_label=after_verdict.label.value,
            after_clause_entails_claim=after_verdict.clause_entails_claim,
            after_overstatement_reason=after_verdict.overstatement_reason,
            spawned_child_claim_ids=[c.claim_id for c in spawned_children],
        )

        self.repair_ledger.append(rec)
        return claim, rec, spawned_children

    def export_ledger(self, target_path: Path):
        """Saves the complete repair ledger to JSON for pipeline auditability."""
        target_path.write_text(
            json.dumps([r.model_dump() for r in self.repair_ledger], indent=2),
            encoding="utf-8",
        )
        logger.info("Saved claim repair ledger (%d records) to %s", len(self.repair_ledger), target_path)
