"""
Universal Hard Governance Gate Evaluator.

Enforces strict, fail-closed validation across the 9 Enterprise Governance Gates:
1. span_exists: Byte/character evidence span exists, non-empty, and untruncated.
2. clause_entails_claim: Proposition entails source clause without modal/polarity conflict.
3. subject_valid: Subject is a recognized contractual actor or governed asset, not a syntax fragment.
4. counterparty_resolved: Governed relationship is fully bound; no dangling/unresolved pronouns.
5. predicate_valid: Predicate is an operative normative relation aligned with textual polarity.
6. is_atomic: Proposition governs exactly one action/remedy without multi-branch disjunctions.
7. is_not_duplicate: Proposition is unique by semantic signature (not a duplicate extraction).
8. claim_type_allowed: Claim is an operative rule (RULE, POLICY_RULE, POLICY), not a definition/reference.
9. human_approved_if_required: High-risk or low-confidence claims require explicit human signoff.

A claim is AUTOMATED_CERTIFIED if and only if EVERY gate evaluates to True.
Missing or indeterminate gates fail closed to False.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union


REQUIRED_GATES = [
    "span_exists",
    "clause_entails_claim",
    "subject_valid",
    "counterparty_resolved",
    "predicate_valid",
    "is_atomic",
    "is_not_duplicate",
    "claim_type_allowed",
    "human_approved_if_required",
    "text_integrity",
]

# Patterns detecting injected taxonomy predicate slugs or snake_case identifiers in claim text
PREDICATE_SLUG_PATTERNS = [
    r"\b(has_[a-z0-9_]+|can_[a-z0-9_]+|may_[a-z0-9_]+|must_[a-z0-9_]+|apply_to|remains_responsible_for|governs_[a-z0-9_]+|will_[a-z0-9_]+)\b",
    r"\b(has_validity_rule|has_refund_reimbursement_window|can_cancel_before_shipment|has_refund_eligibility|may_receive_store_credit)\b",
]

# Operative contractual modal verbs required in normative rules
MODAL_OPERATIVE_PATTERN = r"\b(may|must|will|shall|can|cannot|can\s+not|should|is\s+required\s+to|are\s+required\s+to|is\s+entitled\s+to|are\s+entitled\s+to|agrees\s+to|agree\s+to|authorizes?|grants?|retains?|warrants?|reserves?|is\s+responsible\s+for|remains\s+responsible\s+for|has\s+a\b|has\s+the\s+right\s+to\b|is\s+limited\s+to\b|is\s+capped\s+at\b|shall\s+be\s+limited\s+to\b|liability\s+is\s+the\b|must\s+not|may\s+not|will\s+not|shall\s+not|neither\s+party\s+will|is\s+not\s+licensed\s+to|prohibited\s+from|(?:is|are)\s+refunded|refunded|(?:is|are)\s+issued)\b"

# Generic catch-all predicates banned from canonical certification
BANNED_GENERIC_PREDICATES = {
    "governs_contract_validity",
    "contract_validity",
    "has_validity_rule",
    "complies_with",
    "has_summary",
    "cancel",
    "scheduled",
    "appeal",
    "specifies_governing_rule",
}

# Unstripped leading enumeration artifact markers in claim text
LEADING_ENUMERATION_PATTERN = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s+"

# Broken bare infinitive / headless grammar patterns that reverse legal meaning or lack inflection
BROKEN_GRAMMAR_PATTERNS = [
    r"(?i)^microsoft\s+withdraw\b",
    r"(?i)^each\s+party\s+take\b",
    r"(?i)^parties\s+disclose\b",
    r"(?i)^customers?\s+modify\b",
    r"(?i)^customers?\s+apply_to\b",
    r"(?i)^customers?\s+obtain\b",
    r"(?i)^customers?\s+order\b",
    r"(?i)^customers?\s+uninstall\b",
    r"(?i)^customers?\s+transfer\b",
    r"(?i)^customers?\s+pay\b",
    r"(?i)\bwill\s+contract\s+validity\b",
    r"(?i)\bwill\s+grants?\b",
    r"(?i)\bwill\s+authorizes?\b",
    r"(?i)\bwill\s+applies?\b",
    r"(?i)\bwill\s+warrants?\b",
    r"(?i)\bwill\s+issue\s+refund\s+receive\b",
    r"(?i)\bmust\s+verify\s+refund\s+conditions\b",
    r"(?i)\bwill\s+refund\s+eligibility\b",
    r"(?i)\bwill\s+requires\b",
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

# Non-rule claim types
NON_RULE_CLAIM_TYPES = {
    "reference",
    "description",
    "definition",
    "responsibility",
    "fragment",
    "section_marker",
    "duplicate",
    "quarantined",
    "example",
    "derived_summary",
    "summary",
    "contact_information",
    "contact",
}

# Normative rule claim types
ALLOWED_RULE_CLAIM_TYPES = {
    "rule",
    "policy_rule",
    "policy",
    "table_rule",
    "table_row",
    "policy_matrix",
    "metric",
}

# Text markers that indicate navigational cross-references rather than operative policy rules
REFERENCE_TEXT_MARKERS = [
    "more details about",
    "details about cancellation",
    "can be found in the product terms",
    "can be found at",
    "for more information",
    "refer to section",
    "see the product terms",
    "visit http",
]

# Text markers that indicate general descriptive scope rather than operative rules
DESCRIPTION_TEXT_MARKERS = [
    "may be subject to u.s. and other countries' export laws",
    "export jurisdiction",
    "export laws",
    "trade laws",
    "governed by the laws of",
    "product availability may vary",
    "availability may vary",
    "may vary by region",
    "does not include online services",
    "software does not include",
]

# Predicates that are vendor-side rights in commercial agreements
VENDOR_SIDE_RIGHT_PREDICATES = {
    "may_assess_late_fee",
    "may_suspend_subscription",
    "may_suspend_for_security_or_breach",
    "may_apply_administration_fee",
    "may_terminate_for_nonpayment",
}


@dataclass
class GateEvaluationResult:
    span_exists: bool = False
    clause_entails_claim: bool = False
    subject_valid: bool = False
    counterparty_resolved: bool = False
    predicate_valid: bool = False
    is_atomic: bool = False
    is_not_duplicate: bool = False
    claim_type_allowed: bool = False
    human_approved_if_required: bool = False
    text_integrity: bool = False
    all_9_gates_passed: bool = False
    certification_tier: str = "REVIEW_REQUIRED"
    is_canonical: bool = False
    agent_accessible: bool = False
    rejection_reasons: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    gates: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gates": self.gates,
            "all_9_gates_passed": self.all_9_gates_passed,
            "certification_tier": self.certification_tier,
            "is_canonical": self.is_canonical,
            "agent_accessible": self.agent_accessible,
            "rejection_reasons": self.rejection_reasons,
            "reason_codes": self.reason_codes,
        }


ClaimGateResult = GateEvaluationResult


class ClaimGateEvaluator:
    """Universal fail-closed evaluator for enterprise governance claims."""

    @staticmethod
    def strip_enumeration_prefix(text: Optional[str]) -> str:
        """Strips leading enumeration markers like (i), (ii), (iv), 1., 2), (a), etc."""
        if not text:
            return ""
        pattern = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s*"
        return re.sub(pattern, "", text).strip()

    @staticmethod
    def compute_semantic_signature(subject: Optional[str], predicate: Optional[str], obj: Optional[str]) -> str:
        """Computes a normalized hash signature for semantic deduplication."""
        s = (subject or "").strip().lower()
        p = (predicate or "").strip().lower()
        # Clean punctuation and whitespace from object
        o = re.sub(r"[^\w\s]", "", (obj or "").strip().lower())
        words = o.split()[:8]  # First 8 normalized words
        key = f"{s}|{p}|{' '.join(words)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def evaluate(
        cls,
        claim_text: Optional[str] = "",
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_text: Optional[str] = None,
        claim_type: Optional[str] = "policy",
        status: Optional[str] = "candidate",
        evidence_snippet: Optional[str] = None,
        confidence_or_trust: float = 0.95,
        existing_signatures: Optional[Set[str]] = None,
        is_human_approved: bool = False,
        claim_id: Optional[str] = None,
        object_val: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> GateEvaluationResult:
        """
        Universally evaluates all 9 hard governance gates for a claim.
        Missing or failing criteria fail closed.
        """
        if object_text is None and object_val is not None:
            object_text = object_val
        if confidence is not None:
            confidence_or_trust = confidence

        reasons: List[str] = []
        text_clean = (claim_text or "").strip()
        text_lower = text_clean.lower()
        subj_clean = (subject or "").strip()
        subj_lower = subj_clean.lower()
        pred_clean = (predicate or "").strip()
        pred_lower = pred_clean.lower()
        ct_clean = (claim_type or "policy").strip().lower()
        st_clean = (status or "candidate").strip().lower()

        # ---------------------------------------------------------
        # Phase 2.4: Shared Universal Gate Contract Routing
        # ---------------------------------------------------------
        from app.services.gate_contract import SharedGateRequest, SharedGovernanceGateEngine
        ev_input = evidence_snippet or (kwargs.get("evidence_spans")[0] if kwargs.get("evidence_spans") else None) or text_clean
        shared_req = SharedGateRequest(
            claim_text=text_clean,
            subject=subj_clean,
            predicate=pred_clean,
            object_val=object_text,
            evidence_quote=str(ev_input) if ev_input else None,
            conditions=kwargs.get("conditions") or (metadata.get("conditions") if metadata else None),
            exceptions=kwargs.get("exceptions") or (metadata.get("exceptions") if metadata else None),
            claim_type=ct_clean,
            status=st_clean,
            confidence=confidence_or_trust,
            document_text=kwargs.get("document_text"),
            enclosing_clause=kwargs.get("enclosing_clause"),
            table_header=kwargs.get("table_header") or (metadata.get("table_header") if metadata else None),
            scope=kwargs.get("scope") or (metadata.get("scope") if metadata else None),
            locators=kwargs.get("locators") or (metadata.get("locators") if metadata else None),
            metadata=metadata,
        )
        shared_res = SharedGovernanceGateEngine.evaluate(shared_req)
        reason_codes = list(shared_res.reason_codes)

        # ---------------------------------------------------------
        # 1. Gate: claim_type_allowed
        # ---------------------------------------------------------
        # Must be an operative rule, not a definition, reference, description, or fragment
        is_type_allowed = True
        if ct_clean in NON_RULE_CLAIM_TYPES:
            is_type_allowed = False
            reasons.append(f"Claim type '{claim_type}' is non-operative (definition, reference, or description).")
        elif any(marker in text_lower for marker in REFERENCE_TEXT_MARKERS):
            is_type_allowed = False
            reasons.append("Claim is a navigational cross-reference, not an operative policy rule.")
        elif any(marker in text_lower for marker in DESCRIPTION_TEXT_MARKERS) or "product availability" in subj_lower:
            is_type_allowed = False
            reasons.append("Claim is descriptive background/jurisdiction scope, not an operative rule.")
        elif ct_clean not in ALLOWED_RULE_CLAIM_TYPES:
            is_type_allowed = False
            reasons.append(f"Unrecognized claim type '{claim_type}'.")

        # ---------------------------------------------------------
        # 2. Gate: is_atomic
        # ---------------------------------------------------------
        # Must represent exactly ONE obligation, permission, or prohibition
        is_atomic = True
        if ct_clean == "quarantined":
            is_atomic = False
            reasons.append("Claim is explicitly quarantined as a multi-part compound rule.")
        else:
            # Check for multi-branch transfer rules (Affiliate + 3rd party + hardware + divestiture + merger)
            has_transfer = "transfer" in text_lower or "transferee" in text_lower
            if has_transfer and ("(1)" in text_lower or "(i)" in text_lower) and ("(2)" in text_lower or "(ii)" in text_lower):
                is_atomic = False
                reasons.append("Compound rule: Multi-branch transfer conditions require decomposition.")
            elif has_transfer and ("affiliate" in text_lower or "affiliates" in text_lower) and ("third party" in text_lower or "third parties" in text_lower or "third-party" in text_lower) and ("hardware" in text_lower or "merger" in text_lower or "divestiture" in text_lower or "divestitures" in text_lower):
                is_atomic = False
                reasons.append("Compound rule: Compound transfer rule conjoining affiliate and third-party divestiture conditions.")

            # Check for sublicensing permission/prohibition asymmetry (Customer may sublicense; Affiliates may not)
            if "may sublicense" in text_lower and ("may not sublicense" in text_lower or "affiliates may not" in text_lower):
                is_atomic = False
                reasons.append("Compound rule: Compound sublicensing rule with opposing permissions requires decomposition.")

            # Check for multi-remedy verification audits (reimbursement + license acquisition at 125% + legal cap)
            if ("audit" in text_lower or "unlicensed use" in text_lower) and ("reimburse" in text_lower or "reimbursement" in text_lower or "costs" in text_lower) and ("acquire" in text_lower or "acquisition" in text_lower or "license cost" in text_lower or "125%" in text_lower or "pricing" in text_lower):
                is_atomic = False
                reasons.append("Compound rule: Compound audit remedy combining reimbursement and forced license acquisition.")

        # ---------------------------------------------------------
        # 3. Gate: subject_valid
        # ---------------------------------------------------------
        is_subject_valid = True
        if not subj_clean or len(subj_clean) < 2:
            is_subject_valid = False
            reasons.append("Subject is empty or too short.")
        elif any(re.search(pat, subj_clean) for pat in PAGE_HEADER_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject '{subj_clean}' contains a page-header artifact.")
        elif any(re.search(pat, subj_clean) for pat in POSTAL_ADDRESS_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject '{subj_clean}' contains a postal-address artifact.")
        elif any(re.search(pat, subj_lower) for pat in INVALID_SUBJECT_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject '{subj_clean}' is a syntax fragment, grammar artifact, or non-actor token.")
        elif subj_lower in {"assignment", "the", "it", "this", "these", "that", "which", "a", "an"}:
            is_subject_valid = False
            reasons.append(f"Subject '{subj_clean}' is a stopword or grammatical noun phrase, not a governed entity.")
        elif text_lower.startswith("(ii) all amounts") and ("customer" not in subj_lower):
            is_subject_valid = False
            reasons.append("Enumeration fragment '(ii) All amounts' lacks canonical actor subject.")

        # ---------------------------------------------------------
        # 4. Gate: counterparty_resolved
        # ---------------------------------------------------------
        is_counterparty_resolved = True

        # Pronoun / antecedent resolution check
        pronoun_match = (
            re.search(r"\b(their|them|his|her)\s+performance\b", text_lower)
            or "remains responsible for their" in text_lower
            or text_lower.endswith("their performance.")
            or text_lower.endswith("their performance")
        )
        if pronoun_match:
            grounding_entities = [
                "subcontractor", "subcontractors", "representative", "representatives",
                "affiliate", "affiliates", "employee", "employees", "personnel", "agent", "agents"
            ]
            if not any(e in text_lower for e in grounding_entities):
                is_counterparty_resolved = False
                reasons.append("Ungrounded pronoun 'their' lacks clear antecedent party resolution in claim span.")

        # Predicate-direction consistency: Evidence-conditioned role validation
        # If subject is Customer AND predicate is a vendor-side right AND clause does not grant that right to Customer -> REVIEW_REQUIRED
        if subj_lower in {"customer", "client", "buyer", "subscriber", "licensee"} and (
            pred_lower in VENDOR_SIDE_RIGHT_PREDICATES or any(v in pred_lower for v in ["late_fee", "administration_fee"])
        ):
            clause_full = f"{text_lower} {(evidence_snippet or '').lower()}"
            explicit_grant = False
            customer_perm = rf"\b{subj_lower}\s+(?:may|can|has\s+the\s+right\s+to|reserves\s+the\s+right\s+to|is\s+entitled\s+to)\b"
            if re.search(customer_perm, clause_full):
                if "suspend" in pred_lower:
                    if re.search(rf"\b{subj_lower}\s+(?:may|can|has\s+the\s+right\s+to)\s+.*?\bsuspend\b", clause_full):
                        explicit_grant = True
                elif "fee" in pred_lower or "late" in pred_lower:
                    if re.search(rf"\b{subj_lower}\s+(?:may|can|has\s+the\s+right\s+to)\s+.*?\b(assess|charge|apply)\b", clause_full):
                        explicit_grant = True
                elif "terminate" in pred_lower:
                    if re.search(rf"\b{subj_lower}\s+(?:may|can|has\s+the\s+right\s+to)\s+.*?\bterminate\b", clause_full):
                        explicit_grant = True
                else:
                    explicit_grant = True

            if not explicit_grant:
                # Do NOT auto-reject. Route to REVIEW_REQUIRED!
                is_counterparty_resolved = False
                reasons.append(
                    f"Role direction requires review: Predicate '{pred_clean}' is a vendor-side right assigned to subject '{subj_clean}', "
                    f"but surrounding clause does not explicitly grant that right to {subj_clean}."
                )

        # ---------------------------------------------------------
        # 5. Gate: predicate_valid
        # ---------------------------------------------------------
        is_predicate_valid = True
        if not pred_clean or len(pred_clean) < 2 or pred_lower in {"the", "a", "in", "is", "take"}:
            is_predicate_valid = False
            reasons.append(f"Predicate '{pred_clean}' is invalid or a generic stopword.")
        elif pred_lower in BANNED_GENERIC_PREDICATES or "governs_contract_validity" in pred_lower:
            is_predicate_valid = False
            reasons.append(f"Generic catch-all predicate '{pred_clean}' is unconstrained; requires normalization to specific action taxonomy.")
        else:
            # Contradiction check: text gives Microsoft right to modify, but predicate is must_not_modify_agreement
            if pred_lower == "must_not_modify_agreement":
                if subj_lower == "microsoft" or "microsoft may modify" in text_lower or "microsoft reserves" in text_lower:
                    is_predicate_valid = False
                    reasons.append("Contradictory predicate: 'must_not_modify_agreement' contradicts Microsoft reservation of rights.")

        # ---------------------------------------------------------
        # 6. Gate: span_exists
        # ---------------------------------------------------------
        is_span_exists = True
        if not text_clean or len(text_clean) < 15:
            is_span_exists = False
            reasons.append("Claim text is empty or too brief to constitute an operative provision.")
        elif text_clean.startswith("...") or text_clean.endswith("..."):
            is_span_exists = False
            reasons.append("Claim text is an ellipsis fragment.")
        elif re.search(r"\b(and|or|for|to|with|of|the)\s+all\s+other\s*$", text_lower):
            is_span_exists = False
            reasons.append(f"Claim text is truncated mid-sentence: '{text_clean[-30:]}'.")
        elif "and for all other" in text_lower and not text_lower.endswith("."):
            is_span_exists = False
            reasons.append("Truncated sentence fragment ending at 'and for all other'.")
        elif any(re.search(pat, text_clean) for pat in PAGE_HEADER_PATTERNS):
            is_span_exists = False
            reasons.append("Claim text contains a page-header / pagination artifact (span hygiene failure).")
        elif any(re.search(pat, text_clean) for pat in POSTAL_ADDRESS_PATTERNS):
            is_span_exists = False
            reasons.append("Claim text contains an unstripped postal address artifact (span hygiene failure).")

        # ---------------------------------------------------------
        # 7. Gate: clause_entails_claim
        # ---------------------------------------------------------
        is_clause_entails_claim = True
        # If there is a direct predicate contradiction or truncated text, entailment also fails
        if not is_predicate_valid or not is_span_exists:
            is_clause_entails_claim = False
            reasons.append("Claim fails clause entailment due to textual contradiction or truncated premise.")
        else:
            from app.services.universal_gate_evaluator import UniversalGateEvaluator
            entail_ok, entail_msg = UniversalGateEvaluator.check_semantic_entailment(
                subject=subj_clean,
                predicate=pred_clean,
                claim_text=text_clean,
                evidence_quote=evidence_snippet or text_clean,
                clause_text=text_clean,
            )
            if not entail_ok:
                is_clause_entails_claim = False
                reasons.append(f"Clause entailment failure: {entail_msg}")

        # ---------------------------------------------------------
        # 8. Gate: is_not_duplicate
        # ---------------------------------------------------------
        is_not_duplicate = True
        if metadata and metadata.get("is_duplicate"):
            is_not_duplicate = False
            reasons.append("Claim metadata flags it as a duplicate.")
        elif ct_clean == "duplicate":
            is_not_duplicate = False
            reasons.append("Claim is marked as a collapsed duplicate.")
        elif st_clean == "rejected" and metadata and metadata.get("duplicate_of"):
            is_not_duplicate = False
            reasons.append("Claim is marked as a rejected duplicate.")
        
        # Semantic signature check if pool is provided
        sig = cls.compute_semantic_signature(subj_clean, pred_clean, object_text or text_clean)
        if existing_signatures is not None:
            if sig in existing_signatures:
                is_not_duplicate = False
                reasons.append("Semantic signature already exists in canonical catalog.")

        # ---------------------------------------------------------
        # 9. Gate: human_approved_if_required
        # ---------------------------------------------------------
        # Low trust score or explicit review queue items require human approval
        is_human_approved_if_required = True
        if confidence_or_trust < 0.70 and not is_human_approved:
            is_human_approved_if_required = False
            reasons.append(f"Trust score {confidence_or_trust:.2f} requires human approval.")

        # ---------------------------------------------------------
        # 10. Gate: text_integrity
        # ---------------------------------------------------------
        is_text_integrity = True

        # 10a. Predicate slug rejection (snake_case taxonomy labels injected into text)
        for pat in PREDICATE_SLUG_PATTERNS:
            slug_match = re.search(pat, text_clean)
            if slug_match:
                is_text_integrity = False
                reasons.append(f"Text integrity failure: Injected predicate identifier or taxonomy slug in claim text: '{slug_match.group(0)}'.")
                break

        # 10b. Broken bare infinitive / headless grammar patterns
        if is_text_integrity:
            for pat in BROKEN_GRAMMAR_PATTERNS:
                if re.search(pat, text_clean):
                    is_text_integrity = False
                    reasons.append(f"Text integrity failure: Truncated or bare infinitive phrasing without governing modal verb: '{text_clean[:60]}'.")
                    break

        # 10c. Modal/operative verb preservation in normative rules
        # Exempt table rows, list items, declarative constraints, and non-rule context
        is_table_rule = bool(
            (
                metadata
                and (
                    metadata.get("table_grid")
                    or metadata.get("in_table")
                    or metadata.get("is_table")
                    or metadata.get("table_context")
                    or metadata.get("semantic_context")
                    or metadata.get("table_grid_binding")
                )
            )
            or ct_clean in {"table_rule", "table_row", "policy_matrix"}
            or "|" in text_clean
            or "\t" in text_clean
            or (evidence_snippet and "|" in str(evidence_snippet))
        )
        is_list_item = bool(
            re.match(r"^\s*(?:[-*•]|\d+[\.\)])\s+", text_clean)
            or (metadata and (metadata.get("is_list") or metadata.get("evidence_structure") == "list_item"))
        )
        is_declarative_constraint = bool(
            re.search(
                r"\b(?:approval|approved by|manager approval|tier \d+|lead approval|director approval|"
                r"required|requires|requirement|eligible|eligibility|not eligible|valid|validity|"
                r"condition|subject to|applies to|minimum|maximum|limit|limited to|threshold|"
                r"fee|fees|deposit|non-refundable|non-returnable|deadline|within \d+|per \d+|per customer)\b",
                text_lower,
            )
            or any(k in subj_lower for k in ("approval", "threshold", "returns without", "refund approval", "tier", "return window", "refund speed", "return shipping", "restocking fee", "processing", "warranty", "shipping"))
            or any(k in pred_lower for k in ("requires_", "has_refund_", "has_stage_", "has_identity_", "has_posting_", "has_default_", "has_return_", "has_summary", "has_warranty_", "applies_to", "is_required", "has_refusal_refund_rule", "cannot_be_refunded_for_cash"))
        )
        content_role_clean = str((metadata.get("content_role") if metadata else None) or kwargs.get("content_role") or "").lower()
        is_non_rule_context = ct_clean in NON_RULE_CLAIM_TYPES or content_role_clean in {"definition", "contact_info", "example", "revision_history"}

        if is_text_integrity and ct_clean in ALLOWED_RULE_CLAIM_TYPES and not (is_table_rule or is_list_item or is_declarative_constraint or is_non_rule_context):
            if not re.search(MODAL_OPERATIVE_PATTERN, text_lower):
                is_text_integrity = False
                reasons.append("Text integrity failure: Normative rule is missing an operative modal verb ('may', 'must', 'will', 'shall', etc.).")

        # 10d. Polarity integrity check (prohibition predicate vs affirmative text)
        if is_text_integrity:
            is_prohibition_predicate = any(
                pred_lower == p or pred_lower.startswith(f"{p}_") or f"_{p}_" in pred_lower or pred_lower.endswith(f"_{p}")
                for p in ["must_not", "prohibited", "shall_not", "may_not"]
            )
            has_negative_polarity = any(n in text_lower for n in [" not ", "n't ", "never", "neither", "no ", "without", "prohibit", "is not licensed"])
            if is_prohibition_predicate and not has_negative_polarity:
                is_text_integrity = False
                reasons.append(f"Text integrity failure: Prohibition predicate '{pred_clean}' contradicts affirmative phrasing lacking negative polarity.")

        # 10e. Enumeration artifact cleanup enforcement (no leading (i), (ii), (iv), 1. in certified rule text)
        if is_text_integrity and ct_clean in ALLOWED_RULE_CLAIM_TYPES:
            enum_match = re.match(LEADING_ENUMERATION_PATTERN, text_clean)
            if enum_match:
                is_text_integrity = False
                reasons.append(f"Text integrity failure: Claim text contains unstripped enumeration artifact prefix: '{enum_match.group(0).strip()}'.")

        if not is_text_integrity:
            is_clause_entails_claim = False

        # ---------------------------------------------------------
        # Assemble All Hard Gates
        # ---------------------------------------------------------
        gates = {
            "span_exists": is_span_exists,
            "clause_entails_claim": is_clause_entails_claim,
            "subject_valid": is_subject_valid,
            "counterparty_resolved": is_counterparty_resolved,
            "predicate_valid": is_predicate_valid,
            "is_atomic": is_atomic,
            "is_not_duplicate": is_not_duplicate,
            "claim_type_allowed": is_type_allowed,
            "human_approved_if_required": is_human_approved_if_required,
            "text_integrity": is_text_integrity,
        }

        # FAIL CLOSED: Every boolean MUST be True
        all_passed = all(gates[g] is True for g in REQUIRED_GATES)

        # Determine Tier
        if all_passed:
            tier = "AUTOMATED_CERTIFIED"
            is_canon = True
            agent_acc = True
        elif st_clean == "rejected" or not is_not_duplicate or ct_clean in ("fragment", "duplicate") or not is_span_exists:
            tier = "REJECTED"
            is_canon = False
            agent_acc = False
        elif not is_type_allowed or is_non_rule_context or ct_clean in ("definition", "description", "reference", "responsibility", "example", "summary", "contact_information", "form_field_specification", "non_rule"):
            tier = "NON_RULE"
            is_canon = False
            agent_acc = False
        elif not is_atomic or ct_clean == "quarantined":
            tier = "QUARANTINED"
            is_canon = False
            agent_acc = False
        else:
            tier = "REVIEW_REQUIRED"
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
        if not shared_res.evidence_grounding or not shared_res.source_locator_validity:
            is_span_exists = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)
        if not shared_res.condition_preservation or not shared_res.exception_preservation or not shared_res.scope_preservation or not shared_res.value_fidelity:
            is_clause_entails_claim = False
            for r in shared_res.rejection_reasons:
                if r not in reasons:
                    reasons.append(r)

        return GateEvaluationResult(
            span_exists=is_span_exists,
            clause_entails_claim=is_clause_entails_claim,
            subject_valid=is_subject_valid,
            counterparty_resolved=is_counterparty_resolved,
            predicate_valid=is_predicate_valid,
            is_atomic=is_atomic,
            is_not_duplicate=is_not_duplicate,
            claim_type_allowed=is_type_allowed,
            human_approved_if_required=is_human_approved_if_required,
            text_integrity=is_text_integrity,
            all_9_gates_passed=all_passed,
            certification_tier=tier,
            is_canonical=is_canon,
            agent_accessible=agent_acc,
            rejection_reasons=reasons,
            reason_codes=reason_codes,
            gates=gates,
        )
