"""
Layer 5: Extraction Strategy Router.
Routes eligible candidate evidence units to the optimal extractor:
1. DeterministicSchemaExtractor (Structured BSON/SQL/JSON invariants)
2. DomainRuleExtractor (Enterprise compliance regex, grammar & decisions)
3. LLMSemanticExtractor (Narrative prose & multi-sentence clauses)
"""

from __future__ import annotations

import logging
from typing import List

from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.extractors.llm_extractor import LLMSemanticExtractor
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit

logger = logging.getLogger(__name__)


class StrategyRouter:
    """Routes candidates to their specialized extractor."""

    def __init__(self, llm_extractor: LLMSemanticExtractor | None = None):
        self.llm_extractor = llm_extractor or LLMSemanticExtractor()

    async def extract(
        self,
        unit: ParsedEvidenceUnit,
        strategy: ExtractionStrategyType,
    ) -> List[CandidateClaim]:
        """Invokes the selected extractor for a candidate evidence unit."""
        if unit.block_type != "table_row":
            from app.extraction.prose_normative_classifier import ProseNormativeClassifier
            unit.content_role = ProseNormativeClassifier.classify_unit(
                unit.content_text,
                default_role=unit.content_role,
            )

        if strategy in (ExtractionStrategyType.DETERMINISTIC_SCHEMA, ExtractionStrategyType.TABLE_AWARE):
            return DeterministicSchemaExtractor.extract_from_unit(unit)

        elif strategy == ExtractionStrategyType.DOMAIN_RULES:
            return DomainRuleExtractor.extract_from_unit(unit)

        elif strategy == ExtractionStrategyType.LLM_SEMANTIC:
            return await self.llm_extractor.extract_from_unit(unit)

        # Fallback
        return DomainRuleExtractor.extract_from_unit(unit)
