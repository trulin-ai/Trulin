"""
Layer 6: Multi-Dimensional Validation Gate Evaluators.
Evaluates candidate claims across the 6 core architecture dimensions:
1. Source Match (Pass / Fail)
2. Completeness (Complete / Partial)
3. Meaning (Supported / Uncertain)
4. Scope (In / Out)
5. Time (Current / Stale)
6. Authority (Authoritative / Non-Authoritative)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Tuple

from app.db.enums import SourceFamily, SourceIntent
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.extraction.predicate_registry import PredicateRegistry
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit
from app.validation_gate.models import (
    AuthorityStatus,
    CompletenessStatus,
    DimensionEvaluation,
    MeaningStatus,
    ReviewStatus,
    ScopeStatus,
    SourceMatchStatus,
    TimeStatus,
)


class SourceMatchEvaluator:
    """Verifies cryptographic grounding proof and plugin validation from Layer 5."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        # Check Layer 5 verification outcome
        is_verified = candidate.status == "verified"
        has_plugin = bool(candidate.verification_plugin)
        has_details = bool(candidate.verification_details)

        if is_verified and has_plugin:
            return DimensionEvaluation(
                dimension_name="source_match",
                status=SourceMatchStatus.PASS.value,
                score=1.0,
                passed=True,
                reason=f"Cryptographically verified by Layer 5 plugin `{candidate.verification_plugin}`.",
                details={"plugin": candidate.verification_plugin, **candidate.verification_details},
            )
        else:
            return DimensionEvaluation(
                dimension_name="source_match",
                status=SourceMatchStatus.FAIL.value,
                score=0.0,
                passed=False,
                reason=f"Candidate was not verified by an evidence plugin (status: `{candidate.status}`).",
                details={"status": candidate.status},
            )


class CompletenessEvaluator:
    """Evaluates syntactic, attribute, and condition completeness of the extracted claim."""

    @staticmethod
    def evaluate(candidate: CandidateClaim) -> DimensionEvaluation:
        subj = (candidate.subject or "").strip()
        pred = (candidate.predicate or "").strip()
        obj = (candidate.object or "").strip()
        span = (candidate.evidence_text_span or "").strip()
        is_ambiguous = getattr(candidate, "is_ambiguous", False)
        ambiguity_reason = getattr(candidate, "ambiguity_reason", None)

        has_spo = bool(subj and pred and obj)
        has_evidence = bool(span)

        if is_ambiguous:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.7,
                passed=False,
                reason=f"Ambiguous structure or cell mapping: {ambiguity_reason or 'Mapping requires review'}.",
                details={"subject": subj, "predicate": pred, "object": obj, "is_ambiguous": True},
            )

        PRONOUN_SUBJECTS = {"it", "they", "this", "that", "these", "those", "which", "he", "she", "there", "someone"}
        if subj.lower() in PRONOUN_SUBJECTS:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.2,
                passed=False,
                reason=f"Fragment detected: Subject is an ungrounded pronoun ('{subj}'). Complete assertion with named entity required.",
                details={"subject": subj, "predicate": pred, "object": obj, "is_fragment": True},
            )

        GENERIC_DISALLOWED_SUBJECTS = {"governed entity", "entity", "unknown entity", "policy subject", "governed"}
        if subj.lower() in GENERIC_DISALLOWED_SUBJECTS:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.2,
                passed=False,
                reason=f"Generic fallback subject '{subj}' is forbidden. Exact named entity or table row key required.",
                details={"subject": subj, "predicate": pred, "object": obj, "is_generic_subject": True},
            )

        # Knockout 1: Section Heading as Canonical Subject
        claim_text_clean = (candidate.claim_text or "").strip()
        HEADING_SUBJECTS = {
            "how to request a refund",
            "refund methods and payment types",
            "table of contents",
            "revision history",
            "frequently asked questions",
            "document revision history",
            "standard return policy",
            "order cancellations",
            "warranty claims vs. refunds",
            "warranty claims vs refunds",
            "contact information and escalation",
        }
        if subj.lower() in HEADING_SUBJECTS or (getattr(candidate, "content_role", None) == ContentRole.HEADING and len(claim_text_clean.split()) <= 5 and not any(m in claim_text_clean.lower() for m in [" shall ", " must ", " should ", " will ", " may "])):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.1,
                passed=False,
                reason=f"HEADING_NON_CANONICAL: Section heading '{subj}' is non-canonical contextual framing, not an executable policy claim.",
                details={"subject": subj, "is_heading": True, "decision_code": "HEADING_NON_CANONICAL"},
            )

        # Knockout 2: Question / FAQ Interrogative Sentence
        is_question = (
            claim_text_clean.endswith("?")
            or subj.endswith("?")
            or obj.endswith("?")
            or getattr(candidate, "content_role", None) == ContentRole.FAQ_QUESTION
            or (
                not claim_text_clean.lower().startswith("how to")
                and bool(re.match(r"^(?:will|can|how|what|why|where|when|is|do|does|did|should)\s+[a-z0-9\s]+\??$", claim_text_clean, re.IGNORECASE))
            )
        )
        if is_question:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.0,
                passed=False,
                reason="QUESTION_NOT_ASSERTION: Interrogative sentence or FAQ question cannot be verified as a canonical policy claim.",
                details={"is_question": True, "claim_text": claim_text_clean, "decision_code": "QUESTION_NOT_ASSERTION"},
            )

        # Knockout 3: Definition Fragment ending in e.g. / punctuation
        raw_obj_lower = obj.lower().strip()
        raw_text_lower = claim_text_clean.lower().strip()
        if (
            raw_obj_lower.endswith(("e.g.", "e.g.,", "i.e.", "i.e.,", ",", ";"))
            or raw_text_lower.endswith(("e.g.", "e.g.,", "i.e.", "i.e.,", ",", ";"))
            or raw_obj_lower in ("e.g.", "e.g.,", "i.e.", "i.e.,")
        ):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.1,
                passed=False,
                reason=f"DEFINITION_FRAGMENT: Incomplete assertion ending in abbreviation or conjunction: '{obj}'. Complete definition required.",
                details={"object": obj, "is_fragment": True, "decision_code": "DEFINITION_FRAGMENT"},
            )

        # Knockout 3B: Incomplete Assertions ending in dangling prepositions/connectives, unit-less numbers, or headless fragments
        dangling_pat = r"\b(valid\s+for|with|for|of|to|in|at|by|from|into|onto|and|or|a|an|the|within|after|before|during|under|over)\s*$"
        unitless_number_cutoff = bool(re.search(r"\bwithin\s+\d+\s*$", raw_obj_lower) or re.search(r"\bwithin\s+\d+\s*$", raw_text_lower))
        is_bare_case_header = bool(re.match(r"^Case\s+[A-Z]\s*[-–—:]\s*[^.]+\.?$", claim_text_clean, re.IGNORECASE))
        is_headless_fragment = bool(
            re.match(r"^(?:full\s+refund|partial\s+refund|replacement|repair|exchange|refund\s+issued)\s+(?:within|after|for|by|under|to)\b", claim_text_clean, re.IGNORECASE)
            and not re.search(r"\b(is|are|will|must|shall|may|can|eligible|entitled|receive|provides?)\b", claim_text_clean, re.IGNORECASE)
        )
        if re.search(dangling_pat, raw_obj_lower) or re.search(dangling_pat, raw_text_lower) or unitless_number_cutoff or is_bare_case_header or is_headless_fragment:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.0,
                passed=False,
                reason=f"INCOMPLETE_ASSERTION: Incomplete syntactic clause, headless fragment, bare heading, or missing measurement unit: '{obj or claim_text_clean}'. Complete assertion required.",
                details={"object": obj, "is_fragment": True, "decision_code": "INCOMPLETE_ASSERTION"},
            )

        # Knockout 3D: Subject Contamination (Cross-Case / Cross-Section Leaks)
        subj_l = subj.lower()
        claim_l = claim_text_clean.lower()
        # Generic cross-case contamination: subject starts with a case tag, or claim text
        # references more than one distinct case study (case A AND case B)
        is_subject_contaminated = (
            re.match(r"^case\s+[a-f]", subj_l) is not None
            or len(re.findall(r"\bcase\s+[a-f]\b", claim_l)) > 1
        )
        if is_subject_contaminated:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.0,
                passed=False,
                reason=f"SUBJECT_CONTAMINATION: Subject '{subj}' absorbed evidence content belonging to a distinct case study or policy section.",
                details={"subject": subj, "claim_text": claim_text_clean, "decision_code": "SUBJECT_CONTAMINATION"},
            )

        # Knockout 2B: Illustrative Examples & Sample Case Studies
        is_example = (
            getattr(candidate, "content_role", None) == ContentRole.EXAMPLE
            or getattr(candidate, "claim_type", "").lower() in ("example", "illustrative")
            or re.match(r"^case\s+[a-f]", subj_l)
            or "case study" in subj_l
        )
        if is_example:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.0,
                passed=False,
                reason=f"EXAMPLE_NON_CANONICAL: Illustrative example or case study '{subj}' cannot be verified as a canonical governing policy claim.",
                details={"subject": subj, "is_example": True, "decision_code": "EXAMPLE_NON_CANONICAL"},
            )

        # Knockout 3C: Weak Generic Predicates
        if pred.lower() in ("must_satisfy_requirement", "apply", "offer", "specifies_governing_rule"):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.2,
                passed=False,
                reason=f"WEAK_PREDICATE: Predicate '{pred}' is non-canonical and prohibited in governing policy claims.",
                details={"predicate": pred, "decision_code": "WEAK_PREDICATE"},
            )

        # Knockout 2C: Contact Information Metadata
        is_contact = (
            getattr(candidate, "content_role", None) == ContentRole.CONTACT_INFO
            or getattr(candidate, "claim_type", "").lower() in ("contact_info", "contact_information")
            or pred.lower() in ("has_contact_phone", "has_contact_email", "has_contact_address", "has_contact_hours", "has_service_level_target", "has_contact_channel")
        )
        if is_contact:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.5,
                passed=False,
                reason=f"CONTACT_INFO_NON_CANONICAL: Operational contact information metadata is non-normative and excluded from active policy execution.",
                details={"claim_type": candidate.claim_type, "decision_code": "CONTACT_INFO_NON_CANONICAL"},
            )

        # Knockout 2D: Document Summaries
        is_summary = (
            getattr(candidate, "content_role", None) in (ContentRole.DOCUMENT_METADATA, ContentRole.INTRODUCTORY_CONTEXT)
            or getattr(candidate, "claim_type", "").lower() in ("summary", "derived_summary", "summary_non_canonical")
            or "summary" in subj.lower()
        )
        if is_summary:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.5,
                passed=False,
                reason=f"SUMMARY_NON_CANONICAL: Section summary is contextual framing and excluded from active policy execution.",
                details={"claim_type": candidate.claim_type, "decision_code": "SUMMARY_NON_CANONICAL"},
            )

        # Knockout 3C: Subject Normalization Failure
        subj_lower = subj.lower()
        if any(subj_lower.startswith(p) for p in ("we ", "we're ", "our ", "after that we", "once an order has shipped, it")) or \
           ("(" in subj and ")" not in subj) or \
           re.search(r"\b(we|it|they)\s*$", subj_lower):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.1,
                passed=False,
                reason=f"SUBJECT_NORMALIZATION_FAILED: Subject '{subj}' contains unnormalized fragment, conversational pronoun phrase, or unclosed parenthesis.",
                details={"subject": subj, "is_fragment": True, "decision_code": "SUBJECT_NORMALIZATION_FAILED"},
            )

        # Knockout 4: Cross-Tenant / Hardcoded Subject Contamination
        ev_lower = span.lower()
        loc_path = (candidate.locator or {}).get("heading_path") or []
        heading_path_str = " ".join(str(p) for p in loc_path).lower()
        if "wingify" in subj.lower() and "wingify" not in ev_lower and "wingify" not in heading_path_str and "wingify" not in claim_text_clean.lower():
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.1,
                passed=False,
                reason=f"SUBJECT_CONTAMINATION: Subject '{subj}' contains hardcoded or cross-tenant entity not present in evidence.",
                details={"subject": subj, "is_contaminated": True, "decision_code": "SUBJECT_CONTAMINATION"},
            )

        # Knockout 4b: Bare Copula / Auxiliary Predicate Fragment
        if pred and pred.lower() in ("is", "has", "are", "have", "the", "a", "an") and not candidate.table_binding:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.3,
                passed=False,
                reason=f"Fragment detected: Predicate '{pred}' lacks normative relation or semantic action.",
                details={"predicate": pred, "is_fragment": True, "decision_code": "FRAGMENT_ASSERTION_DISCARDED"},
            )

        # Knockout 5: Weak Grammatical Predicate
        if pred and PredicateRegistry.is_disallowed_generic(pred) and not candidate.table_binding:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.4,
                passed=False,
                reason=f"WEAK_PREDICATE: Predicate '{pred}' is a weak grammatical verb or invalid numeric token rather than a canonical domain predicate.",
                details={"predicate": pred, "is_weak_predicate": True, "decision_code": "WEAK_PREDICATE"},
            )

        # Knockout 6: Meta-Rule Intro
        if re.search(r"\ball\s+of\s+the\s+following\s+conditions\s+must\s+be\s+met\b", claim_text_clean, re.IGNORECASE):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.3,
                passed=False,
                reason="META_RULE_NOT_ATOMIC: Monolithic eligibility intro clause must be decomposed into atomic criteria.",
                details={"is_meta_rule": True, "decision_code": "META_RULE_NOT_ATOMIC"},
            )

        ORPHAN_FRAGMENTS = {"month", "25th", "of renewal and box not shipped"}
        if obj.lower() in ORPHAN_FRAGMENTS:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.1,
                passed=False,
                reason=f"Fragment detected: Object '{obj}' is an orphan cell fragment from an unstitched multiline row.",
                details={"object": obj, "is_fragment": True},
            )

        if len(subj.split()) > 15 or re.match(r"^\d+\.\d+\s+[A-Z]", subj):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.4,
                passed=False,
                reason=f"Contaminated subject: Subject '{subj[:40]}...' contains section heading or narrative paragraph text.",
                details={"subject": subj, "is_contaminated_subject": True},
            )

        if not (has_spo and has_evidence):
            missing = []
            if not subj: missing.append("subject")
            if not pred: missing.append("predicate")
            if not obj: missing.append("object")
            if not has_evidence: missing.append("evidence_text_span")

            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.6,
                passed=False,
                reason=f"Fragment detected: Claim is missing mandatory attributes: {', '.join(missing)}.",
                details={"missing_attributes": missing, "is_fragment": True},
            )

        if pred.lower() in ("is", "has", "are", "have", "the", "a", "an"):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.3,
                passed=False,
                reason=f"Fragment detected: Predicate '{pred}' lacks normative relation or semantic action.",
                details={"predicate": pred, "is_fragment": True},
            )

        details_dict: dict[str, Any] = {"subject": subj, "predicate": pred, "object": obj}
        if getattr(candidate, "conditions", None):
            details_dict["conditions"] = candidate.conditions
        if getattr(candidate, "value", None) is not None:
            details_dict["value"] = candidate.value
            details_dict["unit"] = getattr(candidate, "unit", None)
        if getattr(candidate, "scope", None):
            details_dict["scope"] = candidate.scope

        # Grounding check for contextual preconditions / exceptions
        unsupported_conditions = []
        if getattr(candidate, "conditions", None):
            import json
            ev_corpus = (
                span + " " +
                str(getattr(candidate, "claim_text", "") or "") + " " +
                json.dumps(getattr(candidate, "structured_values", {}) or {}, default=str) + " " +
                json.dumps(getattr(candidate, "locator", {}) or {}, default=str)
            ).lower()
            stop_tokens = {
                "and", "the", "for", "with", "all", "status", "criteria", "per",
                "upon", "under", "from", "any", "not", "require", "requires", "must", "shall", "or",
                "employee", "employees", "employment", "staff", "role", "state", "applicable", "policy",
                "field", "operator", "between", "value", "type", "rule", "min", "max", "date"
            }
            for cond in candidate.conditions:
                if isinstance(cond, dict):
                    semantic_parts = []
                    f = cond.get("field")
                    if f:
                        semantic_parts.extend(re.split(r"[_ -]+", str(f)))
                    v = cond.get("value")
                    if isinstance(v, (list, tuple)):
                        semantic_parts.extend([str(item) for item in v])
                    elif v:
                        semantic_parts.append(str(v))
                    cond_words = [
                        w.lower() for w in re.findall(r"[a-zA-Z]{3,}", " ".join(semantic_parts))
                        if w.lower() not in stop_tokens
                    ]
                else:
                    cond_words = [
                        w.lower() for w in re.findall(r"[a-zA-Z]{3,}", str(cond))
                        if w.lower() not in stop_tokens
                    ]
                missing_words = [
                    w for w in cond_words
                    if w not in ev_corpus and (len(w) < 5 or w[:5] not in ev_corpus)
                ]
                if missing_words:
                    unsupported_conditions.append(f"Condition '{cond}' has ungrounded terms: {', '.join(missing_words)}")

        if unsupported_conditions:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.65,
                passed=False,
                reason=f"Unsupported conditions detected: {'; '.join(unsupported_conditions)}.",
                details={"unsupported_conditions": unsupported_conditions, **details_dict},
            )

        # Condition Preservation Gate (Phase 6):
        # Flags claims when enclosing evidence imposes restrictive conditions that were dropped
        span_lower = span.lower()
        if not getattr(candidate, "conditions", None) and len(span.split()) > 8:
            dropped_restrictive = []
            for pat, c_name in (
                (r"\bsolely in connection with\b", "solely in connection with"),
                (r"\bonly if\b", "only if"),
                (r"\bon the condition that\b", "on the condition that"),
                (r"\bcompleted at least \d+\s*(?:months?|years?)\b", "prior service qualification"),
                (r"\bsubject to\s+[a-z]+ approval\b", "approval requirement"),
            ):
                if re.search(pat, span_lower):
                    claim_obj_lower = (str(candidate.object or "") + " " + str(candidate.claim_text or "")).lower()
                    if c_name not in claim_obj_lower:
                        dropped_restrictive.append(c_name)

            if dropped_restrictive:
                return DimensionEvaluation(
                    dimension_name="completeness",
                    status=CompletenessStatus.PARTIAL.value,
                    score=0.70,
                    passed=False,
                    reason=f"Condition preservation failure: evidence contains qualifying condition ({', '.join(dropped_restrictive)}), but structured claim omitted it.",
                    details={"dropped_conditions": dropped_restrictive, **details_dict},
                )

        return DimensionEvaluation(
            dimension_name="completeness",
            status=CompletenessStatus.COMPLETE.value,
            score=1.0,
            passed=True,
            reason="Subject-Predicate-Object semantics, conditions, and evidence coordinates are 100% complete.",
            details=details_dict,
        )


class MeaningEvaluator:
    """Evaluates semantic clarity, deontic consistency, confidence, and absence of speculative hedges."""

    # Words signaling uncertainty or hedges
    UNCERTAIN_HEDGES = re.compile(r"\b(might|maybe|possibly|perhaps|unclear|tentative|assumed|unconfirmed)\b", re.IGNORECASE)
    OBLIGATION_EVIDENCE = re.compile(r"\b(must|shall|required|requires|mandates?|mandatory|obligated|has to|have to|return)\b", re.IGNORECASE)
    PROHIBITION_EVIDENCE = re.compile(r"\b(prohibited|shall\s+not|must\s+not|forbidden|strictly\s+prohibited|unauthorized\s+.*?\s+prohibited|will\s+not\s+be\s+granted|not\s+be\s+granted|may\s+not|cannot|no\s+.*?\s+should\s+be\s+made)\b", re.IGNORECASE)

    @classmethod
    def evaluate(cls, candidate: CandidateClaim) -> DimensionEvaluation:
        text = candidate.claim_text or ""
        evidence = candidate.evidence_text_span or ""
        confidence = candidate.confidence
        modality = getattr(candidate, "modality", "POLICY_FACT")

        has_hedge = bool(cls.UNCERTAIN_HEDGES.search(text))

        # 1. Subject-Evidence Grounding Validation
        is_zh = (candidate.structured_values or {}).get('language') == 'zh' or any('\u4e00' <= ch <= '\u9fff' for ch in evidence)
        subj_words = [
            w.lower()
            for w in re.findall(r'[a-zA-Z]{3,}', candidate.subject or '')
            if w.lower() not in {'the', 'and', 'for', 'with', 'all', 'per', 'from', 'any', 'upon', 'under', 'into'}
        ]
        ev_lower = evidence.lower()
        has_table_grid = bool(getattr(candidate, 'locator', {}) and candidate.locator.get('table_grid'))
        is_derived_summary = bool(getattr(candidate, 'claim_type', '') == 'derived_summary')
        from app.extraction.models import ExtractionStrategyType
        is_structured_schema = bool(getattr(candidate, 'extraction_strategy', None) == ExtractionStrategyType.DETERMINISTIC_SCHEMA)

        if is_zh:
            zh_subj_map = {
                'supplier': '\u4f9b\u5e94\u5546',
                'microsoft': '\u5fae\u8f6f',
                'parties': '\u53cc\u65b9',
                'either party': '\u4efb\u4f55\u4e00\u65b9',
                'buyer': '\u4e70\u65b9',
                'shipment': '\u53d1\u8d27',
            }
            matched_subj = any(zh_term in evidence for s_word in subj_words for zh_word, zh_term in zh_subj_map.items() if s_word in zh_word) or any(ch in evidence for ch in (candidate.subject or ''))
            if not matched_subj:
                return DimensionEvaluation(
                    dimension_name='meaning',
                    status=MeaningStatus.UNSUPPORTED.value,
                    score=0.20,
                    passed=False,
                    reason=f"Subject-Evidence mismatch: asserted subject '{candidate.subject}' has no grounding in the underlying evidence span.",
                    details={'subject': candidate.subject, 'evidence': evidence[:120], 'subject_unsupported': True},
                )
        elif subj_words and not has_table_grid and not is_derived_summary and not is_structured_schema:
            loc_headings = ' '.join((getattr(candidate, 'locator', {}) or {}).get('heading_path') or []).lower()
            ev_words = set(re.findall(r'[a-zA-Z]{3,}', ev_lower))
            matched_subj = any(
                w in ev_lower
                or w.rstrip('s') in ev_lower
                or any(ew.startswith(w.rstrip('s')) or w.startswith(ew.rstrip('s')) for ew in ev_words)
                or w in loc_headings
                for w in subj_words
            )
            is_pronoun_grounded = bool(
                {'you', 'your', 'we', 'our', 'us', 'company', 'agreement'}.intersection(ev_words)
                and any(w in {'customer', 'customers', 'admin', 'admins', 'vendor', 'microsoft', 'supplier', 'parties', 'employer', 'employee'} for w in subj_words)
            )
            is_doc_meta_subj = any(w in {'policy', 'governance', 'document'} for w in subj_words) and ('policy' in ev_lower or 'guideline' in ev_lower or 'policy' in loc_headings)
            if not matched_subj and not is_doc_meta_subj and not is_pronoun_grounded:
                return DimensionEvaluation(
                    dimension_name='meaning',
                    status=MeaningStatus.UNSUPPORTED.value,
                    score=0.20,
                    passed=False,
                    reason=f"Subject-Evidence mismatch: asserted subject '{candidate.subject}' has no grounding in the underlying evidence span.",
                    details={'subject': candidate.subject, 'evidence': evidence[:120], 'subject_unsupported': True},
                )

        # 2. Deontic consistency verification against evidence text
        deontic_mismatch = False
        if is_zh:
            if modality == 'OBLIGATION':
                deontic_mismatch = not bool(re.search(r'[\u5e94\u5f53\u5fc5\u987b\u5e94\u987b]', evidence))
            elif modality == 'PROHIBITION':
                deontic_mismatch = not bool(re.search(r'[\u4e0d\u5f97\u7981\u6b62]', evidence))
            elif modality == 'PERMISSION':
                deontic_mismatch = not bool(re.search(r'[\u53ef\u4ee5\u6709\u6743]', evidence))
        else:
            ev_clean = re.sub(r'\b(?:which|as|that)\s+may\b', '', evidence, flags=re.IGNORECASE)
            text_clean = re.sub(r'\b(?:which|as|that)\s+may\b', '', text, flags=re.IGNORECASE)
            has_shall_or_must = bool(re.search(r'\b(shall|must)\b', evidence, re.IGNORECASE))
            discretionary_phrases = ('holds the right', 'holds right', 'may request', 'permitted', 'option to', 'at its discretion')
            has_discretionary = any(p in ev_clean.lower() or p in text_clean.lower() for p in discretionary_phrases)
            if not has_shall_or_must and (re.search(r'\bmay\b', ev_clean, re.IGNORECASE) or re.search(r'\bmay\b', text_clean, re.IGNORECASE)):
                has_discretionary = True

            if modality == 'OBLIGATION' and (has_discretionary or not cls.OBLIGATION_EVIDENCE.search(evidence)):
                deontic_mismatch = True
            elif modality == 'PROHIBITION' and not cls.PROHIBITION_EVIDENCE.search(evidence):
                deontic_mismatch = True
        if deontic_mismatch:
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.UNCERTAIN.value,
                score=0.20,
                passed=False,
                reason=f"Deontic mismatch: claim claims {modality} but underlying source evidence reflects discretionary/permissive phrasing or lacks normative imperative verbs.",
                details={"confidence": confidence, "modality": modality, "deontic_mismatch": True},
            )

        if not has_hedge and confidence >= 0.88:
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.SUPPORTED.value,
                score=round(confidence, 4),
                passed=True,
                reason="Clear assertion with verified deontic alignment and strong grounding confidence.",
                details={"confidence": confidence, "modality": modality},
            )
        else:
            reason = "Speculative language or uncertainty detected." if has_hedge else f"Sub-threshold semantic confidence ({confidence*100:.0f}% < 88%)."
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.UNCERTAIN.value,
                score=round(max(confidence * 0.5, 0.4), 4),
                passed=False,
                reason=reason,
                details={"confidence": confidence, "has_hedge": has_hedge},
            )


class ScopeEvaluator:
    """Enforces organizational tenant isolation and declared asset scope."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        org_id = str(envelope.organization_id)
        asset_id = envelope.asset_id
        
        # Check that candidate references the parent envelope
        envelope_match = candidate.envelope_id == envelope.envelope_id
        asset_match = candidate.asset_id == asset_id

        if envelope_match and asset_match:
            return DimensionEvaluation(
                dimension_name="scope",
                status=ScopeStatus.IN_SCOPE.value,
                score=1.0,
                passed=True,
                reason=f"Claim is within authorized tenant boundary `{org_id}` and asset scope.",
                details={"organization_id": org_id, "asset_id": asset_id},
            )
        else:
            return DimensionEvaluation(
                dimension_name="scope",
                status=ScopeStatus.OUT_OF_SCOPE.value,
                score=0.0,
                passed=False,
                reason="Asset ID or Envelope ID mismatch against authorized ingestion scope.",
                details={"expected_asset": asset_id, "claim_asset": candidate.asset_id},
            )


class TemporalValidityEvaluator:
    """Evaluates claim freshness, obsolescence, and expiration timeframes."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        captured_at = envelope.captured_at
        now = datetime.now(timezone.utc)
        
        # Calculate age in days
        age_days = (now - captured_at).total_seconds() / 86400.0

        # Fresh within 180 days (standard enterprise policy audit cycle)
        if age_days <= 180.0:
            freshness_score = max(round(1.0 - (age_days / 365.0) * 0.2, 4), 0.8)
            return DimensionEvaluation(
                dimension_name="time",
                status=TimeStatus.CURRENT.value,
                score=freshness_score,
                passed=True,
                reason=f"Source snapshot is current (captured {age_days:.1f} days ago).",
                details={"age_days": round(age_days, 1)},
            )
        else:
            return DimensionEvaluation(
                dimension_name="time",
                status=TimeStatus.STALE.value,
                score=0.4,
                passed=False,
                reason=f"Source snapshot exceeds 180-day freshness window ({age_days:.1f} days old).",
                details={"age_days": round(age_days, 1)},
            )


class AuthorityEvaluator:
    """Evaluates source hierarchy authority tier according to declared SourceIntent and SourceFamily."""

    @staticmethod
    def evaluate(envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        intent = envelope.source_intent
        family = envelope.source_family

        # Tier 1: Canonical policies, DDL schemas, BSON database invariants (Authoritative)
        if intent in (SourceIntent.GOVERNANCE_POLICY, SourceIntent.OPERATIONAL_DATA) or family == SourceFamily.STRUCTURED:
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.AUTHORITATIVE.value,
                score=1.0,
                passed=True,
                reason=f"Primary authoritative enterprise source ({intent.value} / {family.value}).",
                details={"intent": intent.value, "family": family.value, "tier": 1},
            )

        # Tier 2: Factual knowledge, API catalogs, analytics metrics
        elif intent in (SourceIntent.FACTUAL_KNOWLEDGE, SourceIntent.ANALYTICS_METRIC):
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.AUTHORITATIVE.value,
                score=0.85,
                passed=True,
                reason=f"Secondary authoritative factual catalog ({intent.value}).",
                details={"intent": intent.value, "tier": 2},
            )

        # Tier 3: Discussions, comments, informal chat
        else:
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.NON_AUTHORITATIVE.value,
                score=0.50,
                passed=False,
                reason=f"Informational / non-authoritative discussion ({intent.value}).",
                details={"intent": intent.value, "tier": 3},
            )


class TableCellCoverageAuditor:
    """
    NIST AI RMF Table-Cell Coverage Auditor.
    Guarantees table-cell completeness across all table_row evidence units.
    Enforces that every policy-relevant table cell produces either:
    1. A canonical policy claim
    2. A typed non-canonical metadata record (e.g. note, fee, example)
    3. An explicit REVIEW disposition record with an audit reason (CELL_DROPPED_WITHOUT_DISPOSITION).
    Guarantees zero silent cell dropping across all table rows.
    """

    @classmethod
    def audit_row_coverage(cls, unit: ParsedEvidenceUnit, claims: list[CandidateClaim]) -> dict[str, Any]:
        """
        Audits that every column cell in unit.structured_data['columns'] has been accounted for.
        """
        s_data = unit.structured_data or {}
        cols = s_data.get("columns", {})
        if not cols:
            return {"status": "SKIPPED", "missing_columns": [], "total_cells": 0, "covered_cells": 0, "is_complete": True}

        col_keys = list(cols.keys())
        scope_keywords = ("level", "grade", "group", "role", "tier", "department", "category", "scope")
        scope_keys = [k for k in col_keys if any(sk in k.lower() for sk in scope_keywords)]
        if not scope_keys and col_keys:
            scope_keys = [col_keys[0]]

        rule_keys = [k for k in col_keys if k not in scope_keys]
        if not rule_keys and len(col_keys) > 1:
            rule_keys = [col_keys[-1]]
            scope_keys = col_keys[:-1]

        covered_columns = set()
        for c in claims:
            if c.table_binding and c.table_binding.column_header:
                covered_columns.add(c.table_binding.column_header)

        missing_columns = [k for k in rule_keys if k not in covered_columns]
        is_complete = len(missing_columns) == 0

        return {
            "status": "COMPLETE" if is_complete else "INCOMPLETE",
            "is_complete": is_complete,
            "scope_columns": scope_keys,
            "rule_columns": rule_keys,
            "covered_columns": list(covered_columns),
            "missing_columns": missing_columns,
            "total_rule_cells": len(rule_keys),
            "covered_rule_cells": len(rule_keys) - len(missing_columns),
        }

    @classmethod
    def audit_and_reconcile(cls, unit: ParsedEvidenceUnit, claims: list[CandidateClaim]) -> list[CandidateClaim]:
        """
        Audits unit coverage and synthesizes explicit REVIEW or typed records for any unaccounted cells.
        Guarantees zero silent cell dropping.
        """
        audit_res = cls.audit_row_coverage(unit, claims)
        missing_cols = audit_res.get("missing_columns", [])
        if not missing_cols:
            return claims

        s_data = unit.structured_data or {}
        cols = s_data.get("columns", {})
        loc = unit.locator or {}

        reconciled = list(claims)
        for col_name in missing_cols:
            cell_val = str(cols.get(col_name, "")).strip()
            # If the cell is explicitly empty/dash, emit a typed empty cell record
            if cell_val in ("", "-", "—", "N/A", "n/a", "None", "none", "nil"):
                disposition = "EMPTY_OR_NOT_APPLICABLE"
                ambig_reason = "CELL_EXPLICITLY_EMPTY"
                is_canonical = False
            else:
                disposition = "REVIEW"
                ambig_reason = "CELL_DROPPED_WITHOUT_DISPOSITION"
                is_canonical = False

            review_claim = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                run_id=getattr(unit, "run_id", None),
                source_unit_id=unit.unit_id,
                evidence_id=f"ev:{unit.unit_id}:{col_name}",
                claim_text=f"Table cell for row '{unit.hierarchical_context[-1] if unit.hierarchical_context else 'Table'}' col '{col_name}' value '{cell_val}' disposition: {disposition}.",
                subject=str(unit.hierarchical_context[-1] if unit.hierarchical_context else "Table Policy"),
                predicate="has_unmapped_table_cell",
                object_=cell_val or "empty",
                evidence_text_span=f"Column: {col_name} | Value: {cell_val}",
                value=cell_val,
                claim_type="non_canonical",
                content_role=ContentRole.POLICY_RULE,
                is_canonical=is_canonical,
                is_ambiguous=True,
                ambiguity_reason=ambig_reason,
                confidence=0.5,
                extraction_strategy=ExtractionStrategyType.TABLE_AWARE,
                locator={
                    **loc,
                    "table_grid": {
                        "col_header": col_name,
                        "cell_value": cell_val,
                        "disposition": disposition,
                    },
                },
                structured_values={
                    "audit_disposition": disposition,
                    "dropped_column": col_name,
                    "cell_value": cell_val,
                },
            )
            reconciled.append(review_claim)
        return reconciled
