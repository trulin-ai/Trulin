"""
Layer 5: Candidate Extraction & Source-Aware Verification Pipeline.
Orchestrates Layer 4 Evidence -> Candidate Discovery -> Strategy Routing -> Plugin Verification -> Completeness Ledger.
"""

from __future__ import annotations

import logging
from typing import Any, List

from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.models import CandidateClaim, Layer5ExtractionResult, UnitOutcome
from app.extraction.plugins import VerificationPluginManager
from app.extraction.strategy_router import StrategyRouter
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult

logger = logging.getLogger(__name__)


class Layer5ExtractionPipeline:
    """End-to-end orchestrator for Layer 5."""

    def __init__(
        self,
        strategy_router: StrategyRouter | None = None,
        plugin_manager: VerificationPluginManager | None = None,
    ):
        self.router = strategy_router or StrategyRouter()
        self.plugin_manager = plugin_manager or VerificationPluginManager()

    async def process_envelope(
        self,
        envelope: CanonicalSourceEnvelope,
        evidence_result: ParsedEvidenceResult,
    ) -> Layer5ExtractionResult:
        """Processes an evidence result through Layer 5 extraction and verification."""
        ledger = CompletenessLedger(envelope.envelope_id, envelope.asset_id)
        all_candidates: List[CandidateClaim] = []

        # Run TCUSE across full evidence stream when tables are present
        tcuse_claims_by_unit: dict[str, List[CandidateClaim]] = {}
        table_context_summary: dict[str, Any] = {}
        if any(u.block_type == "table_row" for u in evidence_result.units):
            try:
                from app.extraction.table_context import TableContextPipeline
                tcuse_res = TableContextPipeline.run(
                    evidence_result=evidence_result,
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                )
                tcuse_claims_by_unit = tcuse_res.claims_by_unit_id
                table_context_summary = {
                    "tables_count": len(tcuse_res.tables),
                    "interpretations": [it.model_dump() for it in tcuse_res.interpretations],
                    "atomic_facts_count": len(tcuse_res.atomic_facts),
                    "consistency_reports": [cr.model_dump() for cr in tcuse_res.consistency_reports],
                    "completeness_reports": [cmp.model_dump() for cmp in tcuse_res.completeness_reports],
                }
            except Exception as tc_err:
                logger.warning("TCUSE table enrichment note: %s", tc_err)

        total_units = len(evidence_result.units)
        candidates_found = 0
        claims_extracted_count = 0
        claims_verified_count = 0
        claims_rejected_count = 0

        for unit in evidence_result.units:
            is_eligible, strategy, reason = CandidateDiscoveryEngine.is_candidate(unit)

            if not is_eligible and not (unit.block_type == "table_row" and unit.unit_id in tcuse_claims_by_unit):
                ledger.record_entry(
                    unit_id=unit.unit_id,
                    block_type=unit.block_type,
                    candidate_status="skipped",
                    outcome=UnitOutcome.SKIPPED_WITH_REASON,
                    extractor_used="none",
                    failure_reason=reason,
                )
                continue

            candidates_found += 1

            # 2. Extract Claims using TCUSE (for context-enriched tables) or selected strategy
            try:
                if unit.block_type == "table_row" and unit.unit_id in tcuse_claims_by_unit:
                    extracted_claims = tcuse_claims_by_unit[unit.unit_id]
                else:
                    extracted_claims = await self.router.extract(unit, strategy)
            except Exception as e:
                logger.error("Extraction failed for unit %s: %s", unit.unit_id, str(e))
                ledger.record_entry(
                    unit_id=unit.unit_id,
                    block_type=unit.block_type,
                    candidate_status="failed",
                    outcome=UnitOutcome.FAILED_RETRYABLE,
                    extractor_used=strategy.value,
                    failure_reason=str(e),
                )
                continue

            claims_extracted_count += len(extracted_claims)
            unit_verified_all = True
            unit_failure_reason = None

            # 3. Source-Aware Plugin Verification
            for claim in extracted_claims:
                is_valid, plugin_name, v_reason, details = self.plugin_manager.verify_candidate(
                    candidate=claim,
                    unit=unit,
                    raw_payload=envelope.raw_payload,
                )

                claim.verification_plugin = plugin_name
                claim.verification_details = details

                if is_valid:
                    claim.status = "verified"
                    claims_verified_count += 1
                else:
                    claim.status = "rejected"
                    claim.confidence = round(claim.confidence * 0.5, 2)
                    claims_rejected_count += 1
                    unit_verified_all = False
                    unit_failure_reason = v_reason

                all_candidates.append(claim)

            # Record in Completeness Ledger with 6 explicit states
            if not extracted_claims:
                outcome = UnitOutcome.PROCESSED_NO_CLAIMS
                status_str = "no_claims"
            elif any(getattr(c, "is_ambiguous", False) for c in extracted_claims):
                outcome = UnitOutcome.NEEDS_REVIEW
                status_str = "needs_review"
                unit_failure_reason = "Ambiguous cell or layout structure flagged for review"
            elif unit_verified_all:
                outcome = UnitOutcome.PROCESSED_WITH_CLAIMS
                status_str = "verified"
            else:
                outcome = UnitOutcome.PROCESSED_WITH_CLAIMS
                status_str = "extracted"

            ledger.record_entry(
                unit_id=unit.unit_id,
                block_type=unit.block_type,
                candidate_status=status_str,
                outcome=outcome,
                extractor_used=strategy.value,
                verification_plugin=extracted_claims[0].verification_plugin if extracted_claims else None,
                verification_passed=unit_verified_all and bool(extracted_claims),
                claims_count=len(extracted_claims),
                failure_reason=unit_failure_reason,
            )

        summary = ledger.get_summary()

        return Layer5ExtractionResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            total_evidence_units_received=total_units,
            candidates_discovered=candidates_found,
            claims_extracted=claims_extracted_count,
            claims_verified=claims_verified_count,
            claims_rejected=claims_rejected_count,
            completeness_score=summary["completeness_score"],
            candidates=all_candidates,
            ledger_summary=summary,
            table_context_summary=table_context_summary,
        )


# Global singleton instance
global_extraction_pipeline = Layer5ExtractionPipeline()
