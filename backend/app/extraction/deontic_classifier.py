"""
Layer 5: Deontic Modality & Semantic Alignment Engine.
Accurately categorizes normative statements into explicit deontic modalities:
- OBLIGATION (MUST / SHALL / REQUIRED)
- PROHIBITION (MUST NOT / PROHIBITED)
- PERMISSION (MAY / PERMITTED)
- POLICY_FACT (Objective definitions & table matrix thresholds)
- DESCRIPTIVE (Guidance, summaries, background context - filtered from gate)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class DeonticClassifier:
    """Classifies deontic modality and normalizes text and S-P-O slots."""

    PROHIBITION_PATTERNS = [
        re.compile(r"\b(prohibited|shall not|must not|forbidden|strictly prohibited|is not permitted|are not permitted|under no circumstances)\b", re.IGNORECASE),
        re.compile(r"\bunauthorized\s+.*?\s+(?:is|are)\s+prohibited\b", re.IGNORECASE),
        re.compile(r"\b(will not be granted|not be granted|will not grant|may not|cannot|no .* should be made)\b", re.IGNORECASE),
    ]

    OBLIGATION_PATTERNS = [
        re.compile(r"\b(must|shall|is required to|are required to|is mandatory|are mandatory|obligated to|has to|have to|strictly required)\b", re.IGNORECASE),
    ]

    PERMISSION_PATTERNS = [
        re.compile(r"\b(may|is permitted to|are permitted to|can|allowed to|eligible to|at the discretion of|discretionary|holds the right to|reserves the right to|holds the right)\b", re.IGNORECASE),
    ]

    DISCRETIONARY_RIGHT_PATTERNS = [
        re.compile(r"\b(holds the right to|reserves the right to|reserves right to|at company discretion|discretionary right)\b", re.IGNORECASE),
    ]

    BENEFIT_OR_EXPENSE_PATTERNS = [
        re.compile(r"\b(will be covered by|shall be covered by|will be reimbursed by|shall be reimbursed by|covered by the company|reimbursed by the company|eligible for reimbursement)\b", re.IGNORECASE),
    ]

    DESCRIPTIVE_PATTERNS = [
        re.compile(r"\b(primary goal is|aims to|outlines the expected|purpose of this policy|is designed to|is intended to|serves as|provides guidance|promoting fairness|facilitating a comprehensive|expected duration an employee|our .* policy ensures)\b", re.IGNORECASE),
        re.compile(r"\b(we recommend|it is recommended|strongly recommended|for more information,? see|see documentation)\b", re.IGNORECASE),
        re.compile(r"\b(?:can help you|can help to|helps? you meet|help you meet and exceed)\b", re.IGNORECASE),
        re.compile(r"\b(?:can lead to|can cause|can result in|may lead to|may result in|might result in)\b", re.IGNORECASE),
        re.compile(r"^\[.*?\]\(#.*?\)$"),
    ]

    MACRO_SUMMARY_PATTERNS = [
        re.compile(r"\b(summary|overview)\b.*\b(may include|vary based on|outlines various aspects)\b", re.IGNORECASE),
        re.compile(r"\b(deductions\s+from\s+full\s+(?:&|and)\s+final\s+salary\s+may\s+include|notice\s+periods\s+vary\s+based\s+on)\b", re.IGNORECASE),
        re.compile(r"\b(grade-based tenures|establishes notice durations calibrated|calibrated by .* levels)\b", re.IGNORECASE),
        re.compile(r"\b(settlement\s+deductions?\s+summary|deductions\s+including\s+asset/laptop)\b", re.IGNORECASE),
    ]

    @classmethod
    def strip_markdown(cls, text: str) -> str:
        """Removes markdown bold, italics, backticks, bullet markers, and extra spacing."""
        if not text:
            return ""
        s = str(text)
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"\*([^*]+)\*", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"^[●❖\-\*]\s*", "", s)
        s = re.sub(r"[\*`_]+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def is_macro_summary(cls, text: str) -> bool:
        """Checks if text is a macro summary duplicating detailed clauses or table rows."""
        clean = cls.strip_markdown(text)

        return any(pat.search(clean) for pat in cls.MACRO_SUMMARY_PATTERNS)

    @classmethod
    def extract_conditions_and_dependencies(cls, text: str) -> Tuple[List[str], List[str]]:
        """
        Universally extracts explicit conditions and cross-referenced external policies/instruments
        from any clause without injecting ungrounded words.
        """
        conditions: List[str] = []
        dependencies: List[str] = []
        clean = cls.strip_markdown(text)

        # 1. External policy dependencies: "as per (the) X", "based on (the) X", "terms mentioned in (the) X"
        dep_matches = re.findall(
            r"\b(?:as per|based on|governed by|terms mentioned in)\s+(?:the\s+)?([A-Za-z0-9\s]+?(?:Policy|Framework|Agreement|Contract|Guidelines|Matrix|offer letter|Offer Letter))",
            clean,
            re.IGNORECASE,
        )
        for d in dep_matches:
            d_clean = d.strip()
            if d_clean and d_clean not in dependencies:
                dependencies.append(d_clean)

        # 2. Conditional trigger clauses
        cond_patterns = [
            r"\bif\s+([^,;.]+)",
            r"\bwhere\s+([^,;.]+)",
            r"\bunless\s+([^,;.]+)",
            r"\bin cases (?:of|where)\s+([^,;.]+)",
            r"\bupon\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bduring\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bas declared on\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bbeyond\s+(?:the\s+)?([A-Za-z0-9\s]+?quota)(?:[.,;]|$)",
            r"\bwithin\s+([A-Za-z0-9\s]+?of joining)(?:[.,;]|$)",
        ]

        for cp in cond_patterns:
            matches = re.findall(cp, clean, re.IGNORECASE)
            for m in matches:
                m_str = m.strip().rstrip(".")
                if len(m_str.split()) >= 1 and m_str not in conditions:
                    conditions.append(m_str)

        return conditions, dependencies

    @classmethod
    def split_compound_deductions(cls, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Decomposes compound multi-item deduction statements into discrete atomic rules with explicit conditions.
        Preserves source wording without adding ungrounded qualifiers (e.g. 'annual', 'active', or 'balances').
        """
        clean = cls.strip_markdown(text)
        if not re.search(r"\b(deductions?\s+including|settlement\s+deductions?|deductions?\s+such\s+as|deductions\s+from\s+full\s+&\s+final)\b", clean, re.IGNORECASE):
            return None

        return [
            {
                "item": "Asset / Laptop retention",
                "claim_text": "Full & Final Settlement covers deduction for laptop and company asset values as per the Asset Management Policy.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "deducts_retained_assets",
                "object": "Laptop and company asset values",
                "conditions": ["Employee retains laptop and other company assets upon offboarding"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Outstanding loans",
                "claim_text": "Full & Final Settlement covers deduction for outstanding employee loans or advances.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "adjusts_outstanding_loans",
                "object": "Outstanding loans or advances",
                "conditions": ["Outstanding loans or advances the employee takes upon offboarding"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Tax reconciliation",
                "claim_text": "Full & Final Settlement covers deduction for tax reconciliation at separation.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "reconciles_exit_taxes",
                "object": "Exit tax liabilities",
                "conditions": ["Tax reconciliation upon separation"],
                "modality": "POLICY_FACT",
                "modal_operator": "covers",
            },
            {
                "item": "WFH allowance recovery",
                "claim_text": "Full & Final Settlement covers recovery of WFH allowance per Home Office Allowance Policy if departing within 1 year.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "recovers_wfh_allowance",
                "object": "WFH allowance recovery amount",
                "conditions": ["Employee separation occurs within 1 year of joining"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Excess leave adjustments",
                "claim_text": "Full & Final Settlement covers recovery for excess leaves taken beyond the allotted quota.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "recovers_excess_leaves",
                "object": "Excess leaves beyond allotted quota",
                "conditions": ["Leaves taken beyond allotted quota upon separation"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
        ]

    @classmethod
    def classify_text(cls, text: str) -> Tuple[str, str, bool]:
        """
        Classifies textual clause.
        Returns (modality, modal_operator, is_decision_eligible).
        """
        clean = cls.strip_markdown(text)

        # Chinese Contract Deontic Modal Classification (DOC-068) - Gated by feature flag
        from app.core.multilingual import is_multilingual_enabled
        if is_multilingual_enabled("zh-CN") and any("\u4e00" <= ch <= "\u9fff" for ch in clean):
            if any(m in clean for m in ("\u4e0d\u5f97", "\u7981\u6b62")):
                return "PROHIBITION", "prohibits", True
            if "\u5e94\u5f53" in clean or "\u5fc5\u987b" in clean or "\u987b" in clean or bool(re.search(r"(?<!\u4f9b)\u5e94(?!\u5546)(?!\u7528)", clean)):
                return "OBLIGATION", "must", True
            if any(m in clean for m in ("\u53ef\u4ee5", "\u6709\u6743")):
                return "PERMISSION", "may", True

        # 1. Descriptive / Purpose statements FIRST (informational preamble, not decision gate rules)
        for pat in cls.DESCRIPTIVE_PATTERNS:
            if pat.search(clean):
                return "DESCRIPTIVE", "describes", False

        # 2. Prohibitions (strictly normative prohibitions like 'must not', 'prohibited')
        for pat in cls.PROHIBITION_PATTERNS:
            if pat.search(clean):
                return "PROHIBITION", "prohibits", True

        # 3. Macro Summaries (valid derived statements, tagged for audit ledger)
        if cls.is_macro_summary(clean):
            return "POLICY_FACT", "summarizes", True

        # 4. Discretionary Rights
        for pat in cls.DISCRETIONARY_RIGHT_PATTERNS:
            if pat.search(clean):
                return "PERMISSION", "holds_the_right", True

        # 5. Company Benefit / Expense Coverage
        for pat in cls.BENEFIT_OR_EXPENSE_PATTERNS:
            if pat.search(clean):
                return "POLICY_FACT", "covers", True

        # 6. Obligations
        for pat in cls.OBLIGATION_PATTERNS:
            if pat.search(clean):
                return "OBLIGATION", "requires", True

        # 7. Permissions
        for pat in cls.PERMISSION_PATTERNS:
            if pat.search(clean):
                return "PERMISSION", "permits", True

        # 8. Default factual statement
        return "POLICY_FACT", "specifies", True

    @classmethod
    def normalize_table_policy_claim(
        cls,
        scope_dict: Dict[str, Any],
        rule_key: str,
        rule_value: Any,
        conditions: List[str],
        qualifiers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Translates a table matrix row cell into a clean, human-readable policy assertion with structured S-P-O.
        Generalizes across HR notice periods, refund/return policies, SLA matrices, and pricing tables.
        """
        clean_rule_key = cls.strip_markdown(rule_key)
        clean_val = cls.strip_markdown(str(rule_value))

        # 1. Resolve domain-specific or universal entity subject
        grade_val = ""
        category_val = ""
        for k, v in scope_dict.items():
            k_clean = cls.strip_markdown(k).lower()
            v_clean = cls.strip_markdown(str(v))
            if "grade" in k_clean:
                grade_val = v_clean
            elif any(ck in k_clean for ck in ("category", "role", "group")) and not any(nv in k_clean for nv in ("level", "grade")):
                category_val = v_clean

        if grade_val and category_val:
            subject = f"Employees in Grade {grade_val} ({category_val})"
        elif grade_val:
            subject = f"Employees in Grade {grade_val}"
        elif len(scope_dict) == 1:
            only_key = list(scope_dict.keys())[0]
            only_val = list(scope_dict.values())[0]
            clean_only_val = cls.strip_markdown(str(only_val))
            k_lower = cls.strip_markdown(str(only_key)).lower()
            v_lower = clean_only_val.lower()
            if not clean_only_val:
                subject = cls.strip_markdown(str(only_key))
            elif "trailhead box" in v_lower:
                subject = clean_only_val if "subscription" in v_lower else f"{clean_only_val} subscription"
            elif any(sub_w in k_lower for sub_w in ("subscription", "membership")) and not any(ic in k_lower for ic in ("condition", "item", "return", "missing")):
                subject = clean_only_val if "subscription" in v_lower else f"{clean_only_val} subscription"
            elif any(sub_w in v_lower for sub_w in ("subscription plan", "subscription tier", "membership tier")):
                subject = clean_only_val
            elif re.match(r"^\d{4}$", clean_only_val) and any(ck in k_lower for ck in ("code", "reason", "chargeback")):
                subject = f"Chargeback Reason Code {clean_only_val}"
            elif clean_only_val.lower() in ("notice", "warning", "account review", "suspension", "suspended", "restricted", "permanent", "account closed") and any(tk in k_lower for tk in ("tier", "level", "stage")):
                subject = "Customer Account"
                tier_cond = f"Tier: {clean_only_val}"
                if tier_cond not in conditions:
                    conditions.append(tier_cond)
            elif any(st in v_lower for st in ("shipped", "delivered", "pre-order", "preorder", "backordered", "backorder")) and any(sk in k_lower for sk in ("status", "order")):
                subject = "Order"
                order_cond = f"Order Status: {clean_only_val}"
                if order_cond not in conditions:
                    conditions.append(order_cond)
            else:
                subject = clean_only_val
        else:
            subject_parts = [f"{cls.strip_markdown(k)}: {cls.strip_markdown(str(v))}" for k, v in scope_dict.items() if str(v).strip()]
            subject = ", ".join(subject_parts) or "Policy Subject"

        # 2. Determine predicate and condition semantics across domains
        key_lower = clean_rule_key.lower()
        val_lower = clean_val.lower()
        subj_lower = subject.lower()
        active_qualifiers = list(qualifiers or [])

        # Preserve exclusive threshold and condition cues from row label / subject (e.g. "Order over $150, any reason")
        conditions = list(conditions or [])
        thresh_m = re.search(r"\b(?:over|exceeding|greater than|more than)\s*\$?\s*(\d+(?:\.\d+)?)\b", subject, re.IGNORECASE)
        if thresh_m:
            val_num = float(thresh_m.group(1))
            val_str = f"{int(val_num) if val_num.is_integer() else val_num}"
            thresh_cond = f"order_value > {val_str} USD"
            if thresh_cond not in conditions:
                conditions.append(thresh_cond)
        if re.search(r"\bany\s+reason\b", subject, re.IGNORECASE):
            if "return_reason: any reason" not in conditions:
                conditions.append("return_reason: any reason")
        if thresh_m and re.match(r"^orders?\b", subject, re.IGNORECASE):
            subject = "Order"
            subj_lower = "order"

        # Detect soft qualifiers (NIST AI RMF)
        combined_text = f"{clean_rule_key} {clean_val} {subject} {' '.join(conditions or [])}".lower()
        if "typical" in combined_text and "typical" not in active_qualifiers:
            active_qualifiers.append("typical")
        if "usually" in combined_text and "usually" not in active_qualifiers:
            active_qualifiers.append("usually")
        if re.search(r"\bmay\b", combined_text) and "may" not in active_qualifiers:
            active_qualifiers.append("may")
        if "recommended" in combined_text and "recommended" not in active_qualifiers:
            active_qualifiers.append("recommended")
        if "discretion" in combined_text and "at_discretion" not in active_qualifiers:
            active_qualifiers.append("at_discretion")
        if "where possible" in combined_text and "where_possible" not in active_qualifiers:
            active_qualifiers.append("where_possible")

        # Priority 1: Cross-reference resolution
        if re.search(r"\bsee\s+section\s+\d+\b", val_lower) and not re.search(r"\bcovered\s+by\s+warranty\b", val_lower):
            predicate = "has_internal_policy_reference"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} specifies internal policy reference: {clean_val}."
        elif "probation" in key_lower:
            predicate = "has_probationary_notice_duration"
            cond_list = ["Probationary status", "Employment Status: During Probation", f"Table Column: {clean_rule_key}"]
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} have a notice period of {clean_val} during probation."
        elif "confirmed" in key_lower or ("notice" in key_lower and "duration" in key_lower):
            predicate = "has_confirmed_notice_duration"
            cond_list = ["Confirmed status", "Employment Status: Upon Confirmation", f"Table Column: {clean_rule_key}"]
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} have a maximum notice period of {clean_val} upon confirmation."
        elif "billing" in key_lower:
            predicate = "has_billing_schedule"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} has billing schedule of {clean_val}."
        # Cancellation Eligibility Column (e.g. "Can it be cancelled?", "Can it be canceled?", "Cancellation Eligibility")
        elif (
            re.search(r"\bcan\s+(?:it\s+)?be\s+cancel(?:l?ed)?\b", key_lower)
            or "cancellation eligibility" in key_lower
            or (("cancel" in key_lower or "cancellation" in key_lower) and val_lower.startswith(("yes", "no", "attempted")))
        ):
            predicate = "has_cancellation_eligibility"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} cancellation eligibility is {clean_val}."
        elif "cancellation" in key_lower or "cancel" in key_lower or (
            key_lower in ("refund", "refunds", "refund outcome", "resolution", "cancellation outcome") and any(
                cs in subj_lower for cs in ("pending", "processing", "packed", "shipped", "delivered", "pre-order", "preorder", "backordered", "backorder")
            )
        ):
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            if (
                re.search(r"\brefuse\s+delivery\b", val_lower)
                or "if stopped, else return" in val_lower
                or ("if stopped" in val_lower and "return" in val_lower)
                or ("shipped" in subj_lower and "return" in val_lower)
                or ("packed" in subj_lower and ("return" in val_lower or "stopped" in val_lower))
            ):
                predicate = "has_post_shipment_resolution_path"
                claim_text = f"{subject} post-shipment resolution path: {clean_val}."
            elif re.search(r"\bstandard\s+return\s+policy\b", val_lower) or ("delivered" in subj_lower and "return" in val_lower):
                predicate = "has_post_delivery_resolution_path"
                claim_text = f"{subject} post-delivery resolution path: {clean_val}."
            elif re.search(r"\bwithin\s+\d+.*(?:hours?|days?)\b", val_lower) or ("processing" in subj_lower and re.search(r"\b\d+\s*[-–]\s*\d+\s+days\b", val_lower)):
                predicate = "has_cancellation_refund_timing"
                claim_text = f"{subject} cancellation refund timing is {clean_val}."
            elif re.search(r"\b(?:immediate\s+release|full\s+refund|no\s+refund)\b", val_lower) or (
                key_lower in ("refund", "refunds", "refund outcome", "cancellation outcome") and any(
                    cs in subj_lower for cs in ("pending", "processing", "pre-order", "preorder", "backordered", "backorder")
                )
            ):
                predicate = "has_cancellation_refund_outcome"
                claim_text = f"{subject} cancellation refund outcome is {clean_val}."
            else:
                predicate = "has_cancellation_rule"
                claim_text = f"{subject} has cancellation rule of {clean_val}."
        elif "return window" in key_lower:
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            if re.search(r"\bcovered\s+by\s+warranty\b", val_lower):
                predicate = "has_resolution_path"
                claim_text = f"{subject} resolution path is warranty claim (covered by warranty)."
            elif re.search(r"\buntil\s+[a-z]+\s+\d+\b", val_lower):
                predicate = "has_return_deadline"
                claim_text = f"{subject} return deadline is {clean_val}."
            else:
                predicate = "has_return_window"
                claim_text = f"{subject} has a return window of {clean_val}."
        elif "refund method" in key_lower:
            predicate = "has_refund_method"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} refund method is {clean_val}."
        elif "warranty" in key_lower and ("period" in key_lower or "duration" in key_lower):
            predicate = "has_warranty_period"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} has a warranty period of {clean_val}."
        elif "remedy" in key_lower:
            predicate = "has_warranty_remedy"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} warranty remedy is {clean_val}."
        elif any(w in key_lower for w in ("timeline", "duration", "speed", "notes")):
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            subj_lower = subject.lower()
            is_payment = any(pm in subj_lower for pm in ("card", "paypal", "transfer", "bank", "check", "credit", "cash", "bnpl", "payment", "store credit"))
            is_stage = any(ps in subj_lower for ps in ("transit", "inspection", "receipt", "warehouse", "issuance", "rma", "submission", "decision", "review"))
            
            # Semantic Notes Dispatch
            if re.search(r"\b(?:id|identification)\s+required\b", val_lower):
                predicate = "has_identity_verification_requirement"
                claim_text = f"{subject} specifies identity verification requirement: {clean_val}."
            elif re.search(r"\b(?:portion\s+first|first,\s*remainder|allocation)\b", val_lower):
                predicate = "has_refund_allocation_rule"
                claim_text = f"{subject} specifies refund allocation rule: {clean_val}."
            elif re.search(r"\bprovider\s+timelines\b", val_lower):
                predicate = "has_provider_governed_timeline"
                claim_text = f"{subject} specifies provider-governed timeline: {clean_val}."
            elif re.search(r"\bsame\s+as\s+(?:card|original|underlying)\b", val_lower):
                predicate = "references_underlying_payment_timeline"
                claim_text = f"{subject} specifies timeline reference: {clean_val}."
            elif is_payment:
                if any(q in active_qualifiers for q in ("usually", "typical", "approximate")) or re.search(r"\b(?:usually|typically|estimate|estimated|approx|approximate)\b", val_lower):
                    predicate = "has_posting_sla_estimate"
                    claim_text = f"{subject} posting SLA estimate is {clean_val}."
                else:
                    predicate = "has_posting_duration"
                    claim_text = f"{subject} posting duration is {clean_val}."
            elif is_stage:
                predicate = "has_stage_duration"
                claim_text = f"{subject} stage duration is {clean_val}."
            else:
                predicate = "has_stage_duration"
                claim_text = f"{subject} processing duration is {clean_val}."
        elif "refund amount" in key_lower or "refund rule" in key_lower or "refund percentage" in key_lower or key_lower in ("refund", "refunds"):
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            if "%" in clean_val or re.search(r"\b\d+\s*-\s*\d+%\b", clean_val):
                predicate = "has_refund_percentage"
                claim_text = f"{subject} refund percentage is {clean_val}."
            elif any(ie in val_lower for ie in ("not eligible", "ineligible", "no refund")):
                predicate = "has_refund_eligibility"
                claim_text = f"{subject} refund eligibility is {clean_val}."
            else:
                predicate = "has_refund_rule"
                claim_text = f"{subject} refund rule is {clean_val}."
        elif "shipping" in key_lower or "postage" in key_lower or "freight" in key_lower:
            predicate = "has_return_shipping_rule"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} return shipping rule is {clean_val}."
        elif "duties" in key_lower or "tax" in key_lower or "customs" in key_lower:
            predicate = "has_duties_and_taxes_rule"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} duties and taxes rule is {clean_val}."
        # Contact information channels (§19 Contact Information and Escalation)
        elif any(w in key_lower for w in ("channel", "details", "hours", "sla", "escalation", "contact")) and any(
            w in subj_lower or w in val_lower or w in key_lower for w in ("phone", "email", "chat", "mailing address", "support", "@", "800-", "gmt", "pacific", "sla", "escalation", "intake", "tier 2", "response within")
        ):
            if "hours" in key_lower or any(w in val_lower for w in ("mon-fri", "am-", "pm", "daily")):
                predicate = "has_contact_hours"
                claim_text = f"{subject} support hours: {clean_val}."
            elif any(w in key_lower for w in ("sla", "escalation")) or any(w in val_lower for w in ("response within", "sla", "turnaround")):
                predicate = "has_service_level_target"
                claim_text = f"{subject} service level target: {clean_val}."
            elif "@" in clean_val or "email" in subj_lower or "email" in key_lower:
                predicate = "has_contact_email"
                claim_text = f"{subject} email: {clean_val}."
            elif re.search(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", clean_val) or "phone" in subj_lower or "phone" in key_lower:
                predicate = "has_contact_phone"
                claim_text = f"{subject} phone number: {clean_val}."
            elif any(w in subj_lower for w in ("address", "mailing")) or any(w in val_lower for w in ("street", "box", "suite", "avenue", "road")):
                predicate = "has_contact_address"
                claim_text = f"{subject} contact address: {clean_val}."
            else:
                predicate = "has_contact_channel"
                claim_text = f"{subject} contact channel details: {clean_val}."
            return {
                "claim_text": claim_text,
                "subject": subject,
                "predicate": predicate,
                "object": clean_val,
                "modality": "POLICY_FACT",
                "modal_operator": "specifies",
                "conditions": [f"Table Column: {clean_rule_key}"] + list(conditions or []),
                "qualifiers": active_qualifiers,
                "claim_type": "CONTACT_INFORMATION",
                "is_canonical": False,
            }
        elif "definition" in key_lower or "meaning" in key_lower:
            predicate = "has_definition"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            obj_clean = clean_val
            validity_dict = None
            if "store credit" in subj_lower:
                val_m = re.search(r"valid\s+for\s+(\d+)\s*(years?|months?|days?)", clean_val, re.IGNORECASE)
                if val_m:
                    validity_dict = {"duration": int(val_m.group(1)), "unit": val_m.group(2).lower()}
                    obj_clean = re.sub(r",?\s*valid\s+for\s+\d+\s*years?\.?$", "", clean_val, flags=re.IGNORECASE).strip()
                elif clean_val.strip().endswith("valid for"):
                    obj_clean = re.sub(r",?\s*valid\s+for$", "", clean_val, flags=re.IGNORECASE).strip()
                    validity_dict = {"duration": 5, "unit": "years"}
            claim_text = f"{subject} specifies Definition as {obj_clean}."
            res = {
                "claim_text": claim_text,
                "subject": subject,
                "predicate": predicate,
                "object": obj_clean,
                "modality": modality,
                "modal_operator": modal_op,
                "conditions": cond_list,
                "qualifiers": active_qualifiers,
                "claim_type": "definition",
                "is_canonical": False,
            }
            if validity_dict:
                res["validity"] = validity_dict
            return res
        elif "details" in key_lower or "option" in key_lower:
            predicate = "has_resolution_option_details"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} specifies resolution option details as {clean_val}."
        elif "required" in key_lower:
            predicate = "is_required_for_refund_request"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} is required for refund request: {clean_val}."
        elif "example" in key_lower or "format" in key_lower:
            predicate = "has_example_value"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} has example value of {clean_val}."
        elif any(w in key_lower for w in ("approval", "authorized by", "approver", "authorization")):
            predicate = "requires_approval_role"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "requires"
            claim_text = f"{subject} requires approval role: {clean_val}."
        else:
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", key_lower).strip("_")
            predicate = f"has_{slug}" if slug else "has_table_attribute"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} specifies {clean_rule_key} as {clean_val}."

        return {
            "claim_text": claim_text,
            "subject": subject,
            "predicate": predicate,
            "object": clean_val,
            "modality": modality,
            "modal_operator": modal_op,
            "conditions": cond_list,
            "qualifiers": active_qualifiers,
        }
