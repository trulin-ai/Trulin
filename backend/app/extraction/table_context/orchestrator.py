"""
TCUSE Orchestrator: Integrates Table Context Collector, Header Resolver,
Semantic Interpreter, Enrichment Engine, Consistency Validator, and Completeness Auditor.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.table_context.consistency_validator import (
    TableCompletenessAuditor,
    TableSemanticConsistencyValidator,
)
from app.extraction.table_context.context_collector import TableContextCollector
from app.extraction.table_context.enrichment_engine import TableContextEnrichmentEngine
from app.extraction.table_context.models import (
    AtomicTableFact,
    CanonicalTable,
    TableCompletenessReport,
    TableConsistencyReport,
    TableSemanticInterpretation,
)
from app.extraction.table_context.semantic_interpreter import TableSemanticInterpreter
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult

logger = logging.getLogger(__name__)


@dataclass
class TableContextExecutionResult:
    """Complete output of TCUSE execution across an evidence bundle."""
    tables: List[CanonicalTable] = field(default_factory=list)
    interpretations: List[TableSemanticInterpretation] = field(default_factory=list)
    atomic_facts: List[AtomicTableFact] = field(default_factory=list)
    claims: List[CandidateClaim] = field(default_factory=list)
    claims_by_unit_id: Dict[str, List[CandidateClaim]] = field(default_factory=dict)
    consistency_reports: List[TableConsistencyReport] = field(default_factory=list)
    completeness_reports: List[TableCompletenessReport] = field(default_factory=list)


class TableContextPipeline:
    """Single cohesive entry point for TCUSE inside Layer 5."""

    @classmethod
    def run(
        cls,
        evidence_result: ParsedEvidenceResult,
        envelope_id: uuid.UUID,
        asset_id: str,
        document_title: Optional[str] = None,
        use_cache: bool = True,
    ) -> TableContextExecutionResult:
        tables = TableContextCollector.collect_tables(
            evidence_result=evidence_result,
            document_title=document_title,
        )
        if not tables:
            return TableContextExecutionResult()

        result = TableContextExecutionResult(tables=tables)
        per_table_artifacts: List[Tuple[CanonicalTable, TableSemanticInterpretation, List[AtomicTableFact], List[CandidateClaim]]] = []

        for tbl in tables:
            interp = TableSemanticInterpreter.interpret(tbl, use_cache=use_cache)
            tbl.interpretation = interp
            facts, tbl_claims = TableContextEnrichmentEngine.enrich_and_generate_claims(
                table=tbl,
                interp=interp,
                envelope_id=envelope_id,
                asset_id=asset_id,
            )
            result.interpretations.append(interp)
            result.atomic_facts.extend(facts)
            result.claims.extend(tbl_claims)
            for c in tbl_claims:
                result.claims_by_unit_id.setdefault(c.unit_id, []).append(c)
            per_table_artifacts.append((tbl, interp, facts, tbl_claims))

        doc_tables_claims = [(t, clms) for t, _, _, clms in per_table_artifacts]
        for tbl, interp, facts, tbl_claims in per_table_artifacts:
            cons_rep = TableSemanticConsistencyValidator.validate_table_claims(
                table=tbl,
                interp=interp,
                atomic_facts=facts,
                claims=tbl_claims,
                all_document_tables_claims=doc_tables_claims,
            )
            comp_rep = TableCompletenessAuditor.audit(
                table=tbl,
                interp=interp,
                atomic_facts=facts,
                claims=tbl_claims,
            )
            result.consistency_reports.append(cons_rep)
            result.completeness_reports.append(comp_rep)

            if not cons_rep.passed:
                logger.warning(
                    "TCUSE consistency validator flagged table %s: %s",
                    tbl.table_id,
                    cons_rep.errors,
                )

        return result

