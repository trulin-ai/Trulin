"""
Table Semantic Consistency Validator & Completeness Auditor (Sections 13 & 14).

Independently validates generated table-derived claims across 12 semantic invariants,
computes 5 separate confidence scores, and enforces both cell-level and
relationship-level completeness audits.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.table_context.models import (
    AtomicTableFact,
    CanonicalTable,
    CellDisposition,
    TableCompletenessReport,
    TableConfidenceBreakdown,
    TableConsistencyReport,
    TableSemanticInterpretation,
    TableType,
)


class TableSemanticConsistencyValidator:
    """Independent post-generation semantic consistency validator for table claims."""

    @classmethod
    def validate_table_claims(
        cls,
        table: CanonicalTable,
        interp: TableSemanticInterpretation,
        atomic_facts: List[AtomicTableFact],
        claims: List[CandidateClaim],
        all_document_tables_claims: Optional[List[Tuple[CanonicalTable, List[CandidateClaim]]]] = None,
    ) -> TableConsistencyReport:
        """Runs all 12 consistency checks and produces separate confidence scores."""
        checks: Dict[str, bool] = {
            "subject_supported_by_row_and_header": True,
            "predicate_matches_table_meaning": True,
            "object_preserves_original_value": True,
            "units_and_currencies_preserved": True,
            "ranges_and_operators_preserved": True,
            "conditions_retained": True,
            "exceptions_and_footnotes_attached": True,
            "context_supports_interpretation": not table.context_bundle.has_inconsistency,
            "no_unsupported_assumptions": True,
            "distinct_contexts_produce_distinct_claims": True,
            "independently_understandable": True,
            "complete_evidence_set_supports_claim": True,
        }
        warnings: List[str] = []
        errors: List[str] = []

        if table.context_bundle.has_inconsistency:
            warnings.extend(table.context_bundle.inconsistency_reasons)

        row_map = {r.row_id: r for r in table.rows}
        hdr_by_name = {h.raw_header: h for h in table.header_hierarchy.columns}

        for claim in claims:
            tb = claim.table_binding
            if not tb:
                continue

            row = next((r for r in table.rows if r.row_index == tb.row_index), None)
            norm_cell = row.normalized_cells.get(tb.column_header) if row else None
            hdr_node = hdr_by_name.get(tb.column_header)

            # 1. Subject supported by row/header
            if not claim.subject or len(claim.subject.strip()) < 1:
                checks["subject_supported_by_row_and_header"] = False
                errors.append(f"Empty subject for row {tb.row_index}.")

            # 2. Predicate reflects table meaning when topic is known
            if interp.business_topic and not interp.is_ambiguous and interp.table_type not in (TableType.REVISION_HISTORY, TableType.METADATA_NAVIGATIONAL):
                topic_words = [w.lower() for w in re.findall(r"[a-z]{3,}", interp.business_topic)]
                if topic_words and claim.predicate in ("has_value", "has_days", "has_amount"):
                    checks["predicate_matches_table_meaning"] = False
                    errors.append(
                        f"Generic predicate '{claim.predicate}' fails to reflect table topic '{interp.business_topic}'."
                    )

            # 3. Object preserves original cell value
            raw_clean = re.sub(r"\s*(?:\*+|†|‡|\[\d+\]|\(\d+\)|[¹²³⁴⁵⁶⁷⁸⁹]+)\s*$", "", tb.cell_value).strip()
            if raw_clean and raw_clean.lower() not in str(claim.object or "").lower() and not (norm_cell and norm_cell.is_formula_unavailable):
                checks["object_preserves_original_value"] = False
                errors.append(f"Original cell value '{tb.cell_value}' lost in object '{claim.object}'.")

            # 4. Units & currencies preserved
            exp_unit = (norm_cell.unit if norm_cell else None) or (hdr_node.embedded_unit if hdr_node else None)
            if exp_unit and exp_unit not in str(claim.object or "").lower() and exp_unit != (claim.unit or "").lower():
                if not (exp_unit == "%" and "%" in str(claim.object or "")) and not (exp_unit.upper() in str(claim.object or "").upper()):
                    checks["units_and_currencies_preserved"] = False
                    warnings.append(f"Expected unit '{exp_unit}' missing for cell '{tb.cell_value}'.")

            # 5. Ranges & operators preserved
            if norm_cell and norm_cell.comparison_operator and norm_cell.comparison_operator not in ("~",):
                if not norm_cell.qualifiers and norm_cell.comparison_operator not in str(claim.object or ""):
                    checks["ranges_and_operators_preserved"] = False
                    warnings.append(f"Comparison operator '{norm_cell.comparison_operator}' not preserved.")

            # 6. Header conditions retained
            if hdr_node and hdr_node.inferred_conditions:
                if not claim.conditions:
                    checks["conditions_retained"] = False
                    errors.append(f"Header conditions {hdr_node.inferred_conditions} dropped.")

            # 7. Footnotes attached when markers present
            if norm_cell and norm_cell.footnote_markers:
                matched_any = any(mk in interp.footnote_qualifications for mk in norm_cell.footnote_markers)
                if matched_any and not (claim.conditions or claim.exceptions):
                    checks["exceptions_and_footnotes_attached"] = False
                    warnings.append(f"Footnote markers {norm_cell.footnote_markers} not attached to claim.")

            # 8. No unsupported semantic assumptions when context is missing
            if interp.is_ambiguous and not interp.business_topic and claim.predicate not in ("has_value",) and not claim.is_ambiguous:
                checks["no_unsupported_assumptions"] = False
                errors.append("Generated specific semantic claim without sufficient contextual evidence.")

            # 9. Independently understandable (not a bare cell value or raw markdown row)
            if len((claim.claim_text or "").split()) < 4 or claim.claim_text.strip().startswith("|"):
                checks["independently_understandable"] = False
                errors.append(f"Claim text '{claim.claim_text}' is not independently understandable.")

            # 10. Complete evidence set supports claim
            if not claim.evidence_refs or row and row.unit_id not in claim.evidence_refs:
                checks["complete_evidence_set_supports_claim"] = False
                errors.append("Claim missing complete contextual + cell evidence_refs.")

        # Cross-table identical-rows distinct-context check (#10)
        if all_document_tables_claims:
            my_rows = {tuple(sorted(r.cells.items())) for r in table.rows}
            my_preds = {c.predicate for c in claims}
            for other_tbl, other_claims in all_document_tables_claims:
                if other_tbl.table_id == table.table_id:
                    continue
                other_rows = {tuple(sorted(r.cells.items())) for r in other_tbl.rows}
                other_title = other_tbl.context_bundle.table_title.text if other_tbl.context_bundle.table_title else ""
                my_title = table.context_bundle.table_title.text if table.context_bundle.table_title else ""
                if my_rows == other_rows and my_title and other_title and my_title.lower() != other_title.lower():
                    other_preds = {c.predicate for c in other_claims}
                    if my_preds and my_preds == other_preds:
                        checks["distinct_contexts_produce_distinct_claims"] = False
                        errors.append(
                            f"Tables '{my_title}' and '{other_title}' have identical rows but produced identical predicates {my_preds}."
                        )

        ev_verif_score = 0.98 if checks["complete_evidence_set_supports_claim"] and checks["object_preserves_original_value"] else 0.50
        claim_gen_score = 0.95 if (checks["independently_understandable"] and checks["predicate_matches_table_meaning"]) else 0.60

        breakdown = TableConfidenceBreakdown(
            table_extraction=table.extraction_confidence,
            table_reconstruction=table.reconstruction_confidence,
            context_interpretation=interp.semantic_confidence,
            claim_generation=claim_gen_score,
            evidence_verification=ev_verif_score,
        )

        passed = all(
            checks[k] for k in (
                "subject_supported_by_row_and_header",
                "predicate_matches_table_meaning",
                "object_preserves_original_value",
                "conditions_retained",
                "no_unsupported_assumptions",
                "distinct_contexts_produce_distinct_claims",
                "independently_understandable",
                "complete_evidence_set_supports_claim",
            )
        )

        return TableConsistencyReport(
            table_id=table.table_id,
            passed=passed,
            checks=checks,
            warnings=warnings,
            errors=errors,
            confidence_breakdown=breakdown,
        )


class TableCompletenessAuditor:
    """Enforces Cell-Level and Semantic-Relationship-Level Completeness Audits (Section 14)."""

    @classmethod
    def audit(
        cls,
        table: CanonicalTable,
        interp: TableSemanticInterpretation,
        atomic_facts: List[AtomicTableFact],
        claims: List[CandidateClaim],
    ) -> TableCompletenessReport:
        cell_dispositions: Dict[str, str] = {}
        missing_cells: List[str] = []

        claims_by_cell: Dict[str, CandidateClaim] = {}
        for c in claims:
            cid = (c.locator or {}).get("cell_id")
            if cid:
                claims_by_cell[cid] = c

        facts_by_cell = {f"table_cell:{f.table_id}_row_{f.row_index}_col_{f.col_index}": f for f in atomic_facts}
        scope_set = set(table.header_hierarchy.scope_columns)

        # Header cells
        for hn in table.header_hierarchy.columns:
            hid = f"{table.table_id}_hdr_col_{hn.col_index}"
            cell_dispositions[hid] = CellDisposition.CONTEXTUAL_HEADER.value

        # Data cells
        total_cells = len(table.header_hierarchy.columns)
        for row in table.rows:
            for hn in table.header_hierarchy.columns:
                total_cells += 1
                cid = f"{table.table_id}_row_{row.row_index}_col_{hn.col_index}"
                norm_v = row.normalized_cells.get(hn.raw_header)

                if hn.raw_header in scope_set:
                    cell_dispositions[cid] = CellDisposition.CONDITION.value if len(scope_set) > 1 and hn.col_index > 0 else CellDisposition.SUPPORTING_INFORMATION.value
                elif cid in claims_by_cell:
                    clm = claims_by_cell[cid]
                    if clm.is_ambiguous:
                        cell_dispositions[cid] = CellDisposition.FLAGGED_FOR_REVIEW.value
                    elif interp.table_type in (TableType.REVISION_HISTORY, TableType.METADATA_NAVIGATIONAL):
                        cell_dispositions[cid] = CellDisposition.METADATA.value
                    else:
                        cell_dispositions[cid] = CellDisposition.CONTEXT_ENRICHED_CLAIM.value
                elif f"table_cell:{cid}" in facts_by_cell:
                    cell_dispositions[cid] = CellDisposition.ATOMIC_FACT.value
                elif norm_v and (norm_v.data_type == "empty" or not re.sub(r"[\s•●❖\-_|*✓✔✗✘\.]+", "", norm_v.raw_value)):
                    cell_dispositions[cid] = CellDisposition.NON_SEMANTIC.value
                else:
                    cell_dispositions[cid] = CellDisposition.EXTRACTION_FAILURE.value
                    missing_cells.append(cid)

        # Audit B: Semantic Relationship Completeness (10 required relationships)
        ctx = table.context_bundle
        rel_checks = {
            "title_to_purpose": (ctx.table_title is None) or bool(interp.table_purpose),
            "header_to_column": len(table.header_hierarchy.columns) == len(table.headers),
            "row_header_to_row": all(bool(r.row_id) for r in table.rows),
            "scope_to_rule": bool(table.header_hierarchy.scope_columns) and (len(table.headers) < 2 or bool(table.header_hierarchy.rule_columns)),
            "condition_to_value": all(
                bool(c.conditions) for c in claims
                if (c.locator or {}).get("col_header") in {h.raw_header for h in table.header_hierarchy.columns if h.inferred_conditions}
            ),
            "exception_to_row": (not interp.exceptions) or any(bool(c.exceptions) for c in claims) or is_non_rule(interp),
            "footnote_to_cell": (not ctx.footnotes) or any(bool(c.conditions or c.exceptions) for c in claims) or is_non_rule(interp),
            "formula_to_value": all(
                (c.table_binding and c.table_binding.formula is not None)
                for c in claims
                if (c.structured_values or {}).get("normalized_cell", {}).get("formula")
            ),
            "parent_to_child_header": (not table.header_hierarchy.has_grouped_headers) or any(h.parent_header is not None for h in table.header_hierarchy.columns),
            "table_context_to_claims": (not claims) or all(c.semantic_context is not None for c in claims),
        }

        return TableCompletenessReport(
            table_id=table.table_id,
            total_cells=total_cells,
            cell_dispositions=cell_dispositions,
            cell_completeness_passed=len(missing_cells) == 0,
            missing_cells=missing_cells,
            relationship_checks=rel_checks,
            relationship_completeness_passed=all(rel_checks.values()),
        )


def is_non_rule(interp: TableSemanticInterpretation) -> bool:
    return interp.table_type in (TableType.REVISION_HISTORY, TableType.METADATA_NAVIGATIONAL)

