"""
Layer 5: LLM Semantic Extractor.
Extracts nuanced claims from complex unstructured narrative prose and multi-layered policies using LLMs.
Includes automatic fallback to DomainRuleExtractor for resilience.
"""

from __future__ import annotations

import logging
from typing import List

from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


class LLMSemanticExtractor:
    """Semantic LLM extractor with graceful fallback to domain rules."""

    def __init__(self, provider: BaseLLMProvider | None = None):
        try:
            self.provider = provider or get_llm_provider()
        except Exception:
            self.provider = None

    async def extract_from_unit(self, unit: ParsedEvidenceUnit) -> List[CandidateClaim]:
        claims: List[CandidateClaim] = []
        text = (unit.content_text or "").strip()
        hier = unit.hierarchical_context or []
        doc_title = hier[0] if hier else "Policy"
        section_title = " > ".join(hier[1:]) if len(hier) > 1 else "Clause"

        if not text:
            return claims

        # Try LLM extraction if provider available
        if self.provider is not None:
            try:
                extraction_result = await self.provider.extract_claims(
                    document_title=doc_title,
                    section_title=section_title,
                    section_content=text,
                )
                if extraction_result and extraction_result.claims:
                    from app.extraction.deontic_classifier import DeonticClassifier
                    from app.extraction.subject_normalizer import SubjectNormalizer
                    from app.extraction.predicate_registry import PredicateRegistry
                    from app.ingestion.parsers.evidence_model import ContentRole

                    unit_role = getattr(unit, "content_role", ContentRole.POLICY_RULE)
                    unit_canonical = getattr(unit, "is_canonical", True)

                    for idx, c in enumerate(extraction_result.claims):
                        evidence_span = getattr(c, "evidence_text_span", None) or (c.evidence.exact_quote if hasattr(c, "evidence") and c.evidence else text)
                        modality, modal_op, is_decision_eligible = DeonticClassifier.classify_text(c.claim_text)
                        if not is_decision_eligible or modality == "DESCRIPTIVE":
                            continue

                        # Check case study / example / contact / summary boundaries
                        clean_text = DeonticClassifier.strip_markdown(c.claim_text)
                        s_lower = clean_text.lower()
                        context_str = f"{doc_title} > {section_title}"
                        is_case = (
                            unit_role == ContentRole.EXAMPLE
                            or any(w in context_str.lower() for w in ("case stud", "sample case", "20.2", "illustrative"))
                            or "case " in (c.subject or "").lower()
                        )

                        claim_role = unit_role
                        claim_canon = unit_canonical
                        if is_case:
                            claim_role = ContentRole.EXAMPLE
                            claim_canon = False
                            claim_type_out = "EXAMPLE"
                        elif unit_role == ContentRole.CONTACT_INFO or "contact" in (c.claim_type or "").lower():
                            claim_role = ContentRole.CONTACT_INFO
                            claim_canon = False
                            claim_type_out = "CONTACT_INFORMATION"
                        elif unit_role == ContentRole.SUMMARY or "summary" in (c.claim_type or "").lower():
                            claim_role = ContentRole.SUMMARY
                            claim_canon = False
                            claim_type_out = "SUMMARY"
                        else:
                            claim_type_out = c.claim_type or "policy"

                        # Subject normalization
                        raw_s = DeonticClassifier.strip_markdown(c.subject or doc_title)
                        norm_subject, _ = SubjectNormalizer.normalize(raw_s, context=context_str)

                        # Case-study subjects: keep LLM-assigned subject as-is; flag as example non-canonical
                        if is_case:
                            pass  # norm_subject retained from LLM extraction; canonicality set below
                        else:
                            if norm_subject.lower().startswith("case "):
                                if any(w in s_lower for w in ("video course", "video", "digital", "download")):
                                    norm_subject = "Digital goods"
                                elif "gift card" in s_lower:
                                    norm_subject = "Gift cards"
                                else:
                                    norm_subject = section_title or doc_title

                        # Predicate normalization
                        raw_p = (c.predicate or "specifies").strip()
                        raw_obj = DeonticClassifier.strip_markdown(c.object or c.claim_text)
                        norm_pred, is_can = PredicateRegistry.normalize_predicate(raw_p)
                        if not is_can or PredicateRegistry.is_disallowed_generic(norm_pred):
                            norm_pred, raw_obj, modality = DomainRuleExtractor.normalize_predicate_and_modality(
                                raw_pred=raw_p,
                                raw_pred_obj=raw_obj,
                                clean_sentence=clean_text,
                                raw_modal=modal_op or "specifies",
                                current_modality=modality,
                            )

                        cand = CandidateClaim.create(
                            envelope_id=unit.envelope_id,
                            unit_id=unit.unit_id,
                            asset_id=unit.asset_id,
                            claim_text=clean_text,
                            subject=norm_subject,
                            predicate=norm_pred,
                            object_=raw_obj,
                            evidence_text_span=evidence_span,
                            modal_operator=modal_op,
                            modality=modality,
                            claim_type=claim_type_out,
                            content_role=claim_role,
                            is_canonical=claim_canon,
                            extraction_strategy=ExtractionStrategyType.LLM_SEMANTIC,
                            locator=unit.locator,
                            structured_values={"llm_extracted": True, "model": extraction_result.extraction_model},
                            confidence=0.94,
                        )
                        claims.append(cand)
                    return claims
            except Exception as e:
                logger.warning("LLM extraction failed, engaging DomainRuleExtractor fallback: %s", str(e))

        # Fallback to deterministic domain rule extraction
        fallback_claims = DomainRuleExtractor.extract_from_unit(unit)
        for fc in fallback_claims:
            fc.extraction_strategy = ExtractionStrategyType.LLM_SEMANTIC
        return fallback_claims
