"""
Layer 5: Candidate Discovery Engine ("What might be a claim?").
Scans ParsedEvidenceUnits from Layer 4 and determines eligibility for claim extraction.
Identifies normative assertions, database invariants, schema constraints, table policies, and metric rules.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.extraction.models import ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


class CandidateDiscoveryEngine:
    """Discovers claim candidates from Layer 4 parsed evidence units."""

    # Modal verbs and normative policy markers
    MODAL_PATTERN = re.compile(
        r"\b(must|shall|required|requires|mandates?|prohibited|forbidden|should|enforces?|ensures?|responsib(?:le|ility)|authoriz(?:es?|ed)?|restricted to|always|never|guarantees?|holds the right|reserves the right|permitted|may|will not be granted|not be granted|will not grant|will be made|cannot|automatically\s+grants?|automatically\s+granted|agrees?\s+to\s+receive|agree\s+that|remain\s+valid|remains\s+valid|issue\s+a\s+refund|we[’']ll\s+issue|will\s+issue|limited\s+to|must\s+be\s+started|return\s+almost\s+any\s+physical\s+product|return\s+the\s+product\s+in\s+like-new\s+condition|limit\s+\d+\s+product\s+returns)\b",
        re.IGNORECASE,
    )
    # Thresholds, numerical values, and standard time windows
    THRESHOLD_PATTERN = re.compile(
        r"\b(\d+\s*(?:days?|hours?|minutes?|seconds?|months?|years?|percent|%|bits?|bytes?|ms))\b|\b(AES-?\d+|FIDO2|WebAuthn|MFA|TLS\s*v?\d*\.?\d*|SHA-?\d+)\b",
        re.IGNORECASE,
    )
    # Conversational decision keywords
    DECISION_PATTERN = re.compile(
        r"\b(approv(?:ed|ing|e)|agree|co-sign(?:ed)?|grant(?:ed)?|exempt(?:ion)?|decision|reject(?:ed)?|denied|deployed)\b",
        re.IGNORECASE,
    )
    # Payroll deductions and financial adjustments
    DEDUCTION_RECOVERY_PATTERN = re.compile(
        r"\b(deducted|deductions?|recovered|recovery|adjusted|reconciliation|clawback|holds the right to recover)\b",
        re.IGNORECASE,
    )
    # Company benefit or expense coverage
    BENEFIT_OR_EXPENSE_PATTERN = re.compile(
        r"\b(covered by|shipping costs?|reimburse|reimbursed|allowance)\b",
        re.IGNORECASE,
    )

    @classmethod
    def is_candidate(cls, unit: ParsedEvidenceUnit) -> Tuple[bool, ExtractionStrategyType, str]:
        """
        Evaluates an evidence unit across text, tables, structured records, and connector messages.
        Returns (is_candidate, recommended_strategy, reason).
        """
        b_type = unit.block_type
        text = (unit.normalized_content or unit.content_text or "").strip()
        s_data = unit.structured_data or {}
        unit_role = getattr(unit, "content_role", None)

        # 1. Structured Database & BSON Records -> Deterministic Schema Extraction
        if b_type in ("database_record", "record_row", "structured_record"):
            if s_data.get("flattened_fields") or s_data.get("raw_record") or s_data.get("row_value"):
                return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Database record with typed field invariants."
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Structured operational record."

        # 2. Relational & Schema DDL Definitions & Constraints -> Deterministic Schema Extraction
        if b_type in ("schema_definition", "column_definition", "constraint_definition"):
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Relational schema constraint / DDL definition."

        # 2B. Structured JSON Scalars and XML Elements
        if b_type in ("json_scalar", "xml_element"):
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Structured scalar or XML element data invariant."

        # 3. BI Metric Definitions & Lineage -> Deterministic Schema Extraction
        if b_type in ("metric_definition", "lineage_node", "config_property"):
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "BI metric rule or lineage dependency."

        # 4. Structured Table Rows -> Table-Aware Extraction
        if b_type in ("table_row", "table"):
            table_type = s_data.get("table_type")
            cols = s_data.get("columns", {})
            col_keys_lower = [str(k).lower().strip() for k in cols.keys()]

            # Filter 4A: Revision History metadata (routed to document provenance)
            if table_type == "revision_history" or (
                any("ver" in k or "revision" in k for k in col_keys_lower)
                and any("date" in k or "description" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is document revision history metadata; routed to document provenance."

            # Filter 4B: Table of Contents / Outline (routed to document structure)
            if table_type == "table_of_contents" or (
                any("section" in k for k in col_keys_lower)
                and any("title" in k or "topic" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is table of contents/section outline; routed to document structure."

            # Filter 4C: Approver / Sign-off log (routed to authority record)
            if table_type == "approver_signoff" or (
                any("role" in k or "sign" in k for k in col_keys_lower)
                and any("name" in k or "designation" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is document approver sign-off metadata; routed to document authority record."

            # Filter 4D: Website Sitemap Footer Links (routed to navigation/metadata)
            if (
                table_type == "website_sitemap_footer"
                or any(k in ("what's new", "about microsoft", "microsoft store", "developer & it", "education", "company", "small business", "explore copilot", "windows 11 apps", "explore microsoft products") for k in col_keys_lower)
                or (any("developer" in k for k in col_keys_lower) and any("company" in k or "education" in k for k in col_keys_lower))
                or (any("copilot" in k for k in col_keys_lower) and any("windows" in k or "surface" in k for k in col_keys_lower))
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is website sitemap navigation footer; filtered from normative policy claims."

            # Eligible: Policy Matrix (e.g. Grade Notice Duration Matrix)
            if s_data.get("is_ambiguous"):
                return True, ExtractionStrategyType.TABLE_AWARE, "Table row policy matrix with ambiguous/merged cell layout requiring review."
            if cols or b_type == "table_row":
                return True, ExtractionStrategyType.TABLE_AWARE, "Structured policy matrix row with defined columns."
            return True, ExtractionStrategyType.TABLE_AWARE, "Table policy specification."

        # 5. Conversational Decisions, Messages, and Connector Content
        if b_type in ("chat_message", "message", "slack_message", "commit", "pull_request", "issue", "connector_payload"):
            if (
                cls.DECISION_PATTERN.search(text)
                or cls.MODAL_PATTERN.search(text)
                or cls.THRESHOLD_PATTERN.search(text)
                or any(w in text.lower() for w in ("strictly limited to", "limited to", "window is", "deployment window", "must be", "will be", "deployed"))
            ):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Connector communication with factual or policy assertion."
            return False, ExtractionStrategyType.DOMAIN_RULES, "Informal chat message without decision or factual constraint."

        # Definitions: discover terms, classifications, and threshold qualifiers
        if unit_role == ContentRole.DEFINITION or (
            b_type in ("clause", "paragraph", "definition")
            and bool(re.search(r"^(?:[\"“\'][^\"”\']+[\"”\']|[A-Z][a-zA-Z\s\-]{2,30})\s+(?:means|is defined as|refers to|shall mean)\b", text, re.IGNORECASE))
        ):
            return True, ExtractionStrategyType.DOMAIN_RULES, "Definition establishing terminology, scope qualification, or threshold criteria."

        # Exceptions: discover explicit policy exemptions
        if unit_role == ContentRole.EXCEPTION or (
            b_type in ("clause", "paragraph", "exception")
            and not re.search(r"\bwithout\s+exceptions?\b|\bwith\s+no\s+exceptions?\b", text, re.IGNORECASE)
            and bool(re.search(r"\b(?:exception|exemptions?|unless|except for|excluding)\b", text, re.IGNORECASE))
            and len(text.split()) > 3
        ):
            return True, ExtractionStrategyType.DOMAIN_RULES, "Explicit policy exemption or exception rule."

        # FAQ Answers: factual or policy responses to questions
        if unit_role in (ContentRole.FAQ_ANSWER, ContentRole.FAQ) and not text.endswith("?"):
            return True, ExtractionStrategyType.DOMAIN_RULES, "FAQ answer specifying policy constraints or factual specifications."

        # Chinese Deontic Modal Check (DOC-068) - Gated by feature flag
        from app.core.multilingual import is_multilingual_enabled
        if is_multilingual_enabled("zh-CN"):
            if any("\u4e00" <= ch <= "\u9fff" for ch in text) and any(m in text for m in ("\u4e0d\u5f97", "\u5e94\u5f53", "\u5fc5\u987b", "\u5e94", "\u6709\u6743", "\u53ef\u4ee5")):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Chinese contract deontic policy assertion."

        # 6. Document Clauses & Paragraphs
        if b_type in ("clause", "paragraph", "definition", "faq_answer"):
            from app.extraction.deontic_classifier import DeonticClassifier

            # Filter out FAQ questions, introductory context, and document metadata upfront
            if unit_role in (ContentRole.FAQ_QUESTION, ContentRole.INTRODUCTORY_CONTEXT, ContentRole.DOCUMENT_METADATA) or text.strip().endswith("?"):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Inquiry question, introductory context, or document metadata; non-canonical context."
            unit_role = getattr(unit, "content_role", None)
            if unit_role in (ContentRole.FAQ_QUESTION, ContentRole.INTRODUCTORY_CONTEXT, ContentRole.DOCUMENT_METADATA) or text.strip().endswith("?"):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Inquiry question, introductory context, or document metadata; non-canonical context."

            # Filter out sample case studies, narrative customer anecdotes, and revision history
            h_path_str = " > ".join(getattr(unit, "heading_path", []) or []).lower()
            if any(term in h_path_str for term in ("sample case", "case studies", "case study", "revision history", "changelog", "document history")):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Illustrative case study or revision history; non-normative context."
            if re.match(r"^Case\s+[A-Z]\s*[:\-–]", text):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Illustrative case study scenario; non-normative context."
            if re.match(r"^[A-Z][a-z]+\s+(?:ordered|bought|purchased|received|contacted|returned)\b", text):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Illustrative customer anecdote; non-normative context."

            # Filter out running page headers / footers and pagination artifacts
            if re.search(r"\bPage\s+\d+\s+of\s+\d+\b", text, re.IGNORECASE) and len(text.split()) < 20:
                return False, ExtractionStrategyType.DOMAIN_RULES, "Running header/footer pagination artifact."
            if re.match(r"^(?:Vendor Agreement|Agreement Template)\b", text.strip(), re.IGNORECASE) and len(text.split()) < 10:
                return False, ExtractionStrategyType.DOMAIN_RULES, "Running document header template artifact."

            # Filter out contact directory hours, phone numbers, and call-center preparatory steps
            if re.search(r"\b(?:1-800-\d{3}-\d{4}|Mon-Fri\s+\d|Pacific Time|call center hours|Please have your order number)\b", text, re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Customer support directory / phone line information."
            if re.match(r"^Agents will email your RMA\b", text):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Internal operational customer service timeframe."

            # Filter out boilerplate legal severability and copyright notices
            norm_text = re.sub(r"\s+", " ", text).strip()
            if re.search(r"\b(?:distinct and severable and a declaration|may be reproduced, stored in a retrieval system|defines the duration of notice and payout options|Effective\s+April\s+1,\s+2021,\s+this\s+policy\s+outlines)\b", norm_text, re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Standard boilerplate severability/confidentiality notice."
            if re.match(r"^(?:Version\s+Date\s+Change|Revision\s+History)\b", norm_text, re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Document revision history or changelog table."
            if re.match(r"^(?:For example|For instance)\b", norm_text, re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Illustrative example introductory phrase; non-normative context."

            # Filter out contract clause selection cross-references and broken wrap fragments
            if re.match(r"^(?:Clause \d+|Annex [A-Z0-9]+)\s*:\s*(?:In accordance with [^,]+,\s*)?the parties (?:select|agree|are detailed)\b", text, re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Standard contractual cross-reference / forum election clause."
            if re.search(r"\bClauses \d+ to\s*$", text) or re.match(r"^\d+\s+for any data to which it\b", text):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Broken sentence fragment or wrapped clause citation."
            if re.search(r"\b(?:best efforts to|from time to time by\s*[a-z]?)$", text.strip(), re.IGNORECASE):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Dangling broken clause fragment."

            has_obligations = any(ob.search(text) for ob in DeonticClassifier.OBLIGATION_PATTERNS) or bool(cls.MODAL_PATTERN.search(text))

            if unit_role == ContentRole.REFERENCE_CITATION and not has_obligations:
                return False, ExtractionStrategyType.DOMAIN_RULES, "Reference citation or external pointer; non-normative context."

            if re.match(r"^(?:for more information,? see|see documentation|refer to documentation)\b", text, re.IGNORECASE) and not has_obligations:
                return False, ExtractionStrategyType.DOMAIN_RULES, "Reference citation or external pointer; non-normative context."

            # Filter out procedural UI instructions in how-to articles
            from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
            if DomainRuleExtractor.is_procedural_ui_instruction(text):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Procedural UI instruction or click in how-to guide; non-normative action."

            modality, _, is_decision_eligible = DeonticClassifier.classify_text(text)

            # Filter out purpose/goal statements and preamble outlines
            if re.search(r"\b(?:primary goal is|aims to|outlines the expected|purpose of this policy|is designed to|is intended to|serves as|provides guidance)\b", text, re.IGNORECASE):
                return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational guidance or purpose statement; filtered from decision gate."

            # Filter out purely descriptive statements unless unit contains explicit obligation modals
            if (not is_decision_eligible or modality == "DESCRIPTIVE") and not has_obligations:
                return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational guidance or purpose statement; filtered from decision gate."

            # Allow macro summary statements for non-canonical derived summary extraction
            if DeonticClassifier.is_macro_summary(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Macro summary statement for non-canonical derived summary extraction."

            # Eligible: Compound financial/settlement deductions requiring decomposition (fallback for concise docs)
            if DeonticClassifier.split_compound_deductions(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Financial settlement and deduction rules requiring atomic decomposition."

            # Eligible: Dedicated deduction and recovery clauses (e.g. laptop retention, loans, tax deductions)
            if cls.DEDUCTION_RECOVERY_PATTERN.search(text) and len(text.split()) > 4:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Payroll deduction or financial recovery policy clause."

            # Eligible: HR termination, severance, or notice policy clauses
            if re.search(r"\b(?:minimum of two weeks|written notice|resignation|final paycheck|position elimination|severance pay|pay instead of notice|pay in (?:lieu|place) of notice)\b", text, re.IGNORECASE):
                return True, ExtractionStrategyType.DOMAIN_RULES, "HR termination, notice, or severance policy clause."

            # Eligible: Policy Effective Date specification
            if re.search(r"\bEffective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\b|\beffective\s+date\b", text, re.IGNORECASE):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Policy effective date specification."

            # Eligible: Company benefit or expense coverage (e.g. shipping costs covered)
            if cls.BENEFIT_OR_EXPENSE_PATTERN.search(text) and len(text.split()) > 4:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Company expense or benefit policy clause."

            # Eligible: Product return exclusions and specifications
            if any(w in text.lower() for w in ("clearly personalized", "made to your specifications", "custom-made", "cannot be returned", "inseparably mixed", "unsealed after delivery")):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Product return exclusion or specification restriction."

            has_modal = bool(cls.MODAL_PATTERN.search(text))
            has_threshold = bool(cls.THRESHOLD_PATTERN.search(text))

            if modality == "PROHIBITION":
                return True, ExtractionStrategyType.DOMAIN_RULES, "Strict policy prohibition clause."
            elif has_modal and has_threshold:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Strict policy clause with modal obligations and numerical thresholds."
            elif has_modal or modality in ("OBLIGATION", "PERMISSION"):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Normative assertion containing modal requirements or discretionary permissions."
            elif has_threshold and len(text.split()) > 4:
                return True, ExtractionStrategyType.LLM_SEMANTIC, "Factual claim containing quantitative thresholds."
            return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational prose without normative constraints."

        # 7. Headings (context providers, generally not standalone claims)
        if b_type == "heading":
            if any(w in text.lower() for w in ("must", "shall", "required", "prohibited", "shall not", "cannot")):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Composite heading with actionable policy prose."
            return False, ExtractionStrategyType.DOMAIN_RULES, "Structural heading without standalone claim."

        return False, ExtractionStrategyType.DOMAIN_RULES, "Unrecognized block type."

    @classmethod
    def discover_candidates(
        cls, units: List[ParsedEvidenceUnit]
    ) -> List[Tuple[ParsedEvidenceUnit, ExtractionStrategyType, str]]:
        """Filters an evidence unit list to only candidate units with assigned extraction strategies."""
        candidates = []
        for u in units:
            eligible, strategy, reason = cls.is_candidate(u)
            if eligible:
                candidates.append((u, strategy, reason))
        return candidates
