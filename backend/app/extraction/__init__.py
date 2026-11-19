"""
Layer 5: Candidate Extraction & Source-Aware Verification Package.
"""

from app.extraction.models import (
    CandidateClaim,
    ClaimType,
    CompletenessLedgerRecord,
    ExtractionStrategyType,
    Layer5ExtractionResult,
)
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.prose_normative_classifier import ProseNormativeClassifier
from app.extraction.strategy_router import StrategyRouter
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.pipeline import Layer5ExtractionPipeline, global_extraction_pipeline

__all__ = [
    "CandidateClaim",
    "ClaimType",
    "CompletenessLedgerRecord",
    "ExtractionStrategyType",
    "Layer5ExtractionResult",
    "CandidateDiscoveryEngine",
    "ProseNormativeClassifier",
    "StrategyRouter",
    "CompletenessLedger",
    "Layer5ExtractionPipeline",
    "global_extraction_pipeline",
]
