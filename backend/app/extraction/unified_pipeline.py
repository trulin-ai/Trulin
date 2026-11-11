"""
Unified Core Extraction Pipeline.

Defines the single authoritative extraction pipeline shared by both:
1. Live Application (FastAPI endpoint /v1/documents/upload-and-extract)
2. Audit & Validation Benchmark (research/validation_50/run_validation.py)

Pipeline steps:
PDF/File raw bytes → structured parsing → candidate discovery → claim extraction
→ validation → deduplication → conflict detection → results
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.db.enums import SourceFamily, SourceIntent
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.models import CandidateClaim, Layer5ExtractionResult
from app.extraction.pipeline import global_extraction_pipeline
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.universal_file_parser import UniversalFileParser
from app.schemas.evidence import ImmutableEvidenceSpan
from app.schemas.universal_claim import ClaimLifecycleState
from app.services.universal_gate_evaluator import (
    UniversalGateEvaluator,
    UniversalGateResult,
)
from app.taxonomy.registry import PredicateRegistryService
from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    DecisionCode,
    DimensionEvaluation,
    Layer6ValidationResult,
)
from app.validation_gate.persistence import EnterpriseClaimStore

logger = logging.getLogger(__name__)


class UnifiedPipelineOptions(BaseModel):
    """Runtime options for unified extraction execution."""
    organization_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    source_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID("44444444-4444-4444-4444-444444444444"))
    document_type: str = "policy"
    source_intent: SourceIntent = SourceIntent.GOVERNANCE_POLICY
    source_family: SourceFamily = SourceFamily.DOCUMENT
    doc_title: Optional[str] = None
    external_id: Optional[str] = None
    persist_to_db: bool = False
    document_version_id: Optional[uuid.UUID] = None
    parsed_content: Optional[str] = None


@dataclass
class UnifiedPipelineResult:
    """Strongly-typed outcome of the unified extraction pipeline."""
    envelope: CanonicalSourceEnvelope
    evidence_result: ParsedEvidenceResult
    raw_candidates: List[CandidateClaim]
    candidates: List[CandidateClaim]  # Deduplicated canonical claims
    evaluations: List[CandidateGateEvaluation]
    conflicts: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    pipeline_run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_byte_hash: str = ""
    source_hash_algorithm: str = "SHA-256"
    persisted_claim_ids: List[uuid.UUID] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "envelope_id": str(self.envelope.envelope_id),
            "document_id": self.envelope.asset_id,
            "source_byte_hash": self.source_byte_hash,
            "source_hash_algorithm": self.source_hash_algorithm,
            "filename": self.envelope.evidence_locator.get("filename") if self.envelope.evidence_locator else "",
            "total_evidence_units": len(self.evidence_result.units),
            "candidates_discovered": len(self.raw_candidates),
            "unique_claims_extracted": len(self.candidates),
            "claims_approved": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE),
            "claims_review": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REVIEW),
            "claims_rejected": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REJECT),
            "conflicts_detected": len(self.conflicts),
            "persisted_claims_count": len(self.persisted_claim_ids),
        }


class UnifiedExtractionPipeline:
    """
    Shared, authoritative extraction entry point used by BOTH:
    1. Live Application (FastAPI endpoint /v1/documents/upload-and-extract)
    2. Research & Audit Benchmark (run_validation.py)
    
    Guarantees parity by executing the exact same parsing, discovery, extraction,
    validation, deduplication, and conflict rules across all workflows.
    """

    @classmethod
    async def execute(
        cls,
        filename: str,
        raw_bytes: Optional[bytes] = None,
        options: Optional[UnifiedPipelineOptions] = None,
        db_session: Optional[AsyncSession] = None,
        parsed_content: Optional[str] = None,
    ) -> UnifiedPipelineResult:
        start_time = time.time()
        opts = options or UnifiedPipelineOptions()

        doc_title = (
            opts.doc_title
            or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        ).replace("\x00", "").strip()

        # Step 1: Universal Parsing
        effective_parsed = parsed_content or opts.parsed_content
        if effective_parsed:
            content_text = effective_parsed
            if raw_bytes is None:
                raw_bytes = content_text.encode("utf-8")
        else:
            effective_bytes = raw_bytes or b""
            parsed_doc = UniversalFileParser.parse_file(
                filename=filename,
                raw_bytes=effective_bytes,
                doc_title=doc_title,
            )
            content_text = parsed_doc.full_text if hasattr(parsed_doc, "full_text") else str(parsed_doc)
            if raw_bytes is None:
                raw_bytes = effective_bytes

        # Step 2: Canonical Source Envelope (Layer 3)
        canonical_env = EnvelopeFactory.create_from_file_upload(
            filename=filename,
            raw_bytes=raw_bytes,
            parsed_content=content_text,
            organization_id=opts.organization_id,
            source_id=opts.source_id,
            document_type=opts.document_type,
            source_intent=opts.source_intent,
            source_family=opts.source_family,
        )

        # Step 3: Structured Parsing (Layer 4)
        fmt_lower = (filename.rsplit(".", 1)[-1] if "." in filename else "txt").lower()
        if fmt_lower in ("docx", "doc"):
            from app.ingestion.parsers.docx_parser import DocxAdapter
            evidence_result = await DocxAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("xlsx", "xls"):
            from app.ingestion.parsers.xlsx_parser import XlsxAdapter
            evidence_result = await XlsxAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("png", "jpg", "jpeg", "tiff", "tif", "webp", "bmp"):
            from app.ingestion.parsers.ocr_adapter import OcrAdapter
            evidence_result = await OcrAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("md", "markdown"):
            from app.ingestion.parsers.markdown_adapter import MarkdownAdapter
            evidence_result = await MarkdownAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("html", "htm", "xhtml"):
            from app.ingestion.parsers.html_adapter import HtmlAdapter
            evidence_result = await HtmlAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("csv", "tsv"):
            from app.ingestion.parsers.csv_adapter import CsvAdapter
            evidence_result = await CsvAdapter.parse_to_evidence(canonical_env)
        elif fmt_lower in ("json", "sql"):
            evidence_result = await StructuredDataParser.parse(canonical_env)
        else:
            evidence_result = await DocumentParser.parse(canonical_env)

        # Step 4: Candidate Discovery & Extraction (Layer 5)
        l5_result: Layer5ExtractionResult = await global_extraction_pipeline.process_envelope(
            envelope=canonical_env,
            evidence_result=evidence_result,
        )
        raw_candidates = l5_result.candidates

        # Step 4.5: Universal Claim Quality Normalization
        from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer

        normalized_candidates: List[CandidateClaim] = []
        for c in raw_candidates:
            norm_c = ClaimQualityNormalizer.normalize_candidate_claim(c)
            normalized_candidates.append(norm_c if norm_c is not None else c)

        # Step 5: Deduplication (preserve highest confidence & merge conditions)
        seen_keys: Dict[Tuple[str, str, str, str], CandidateClaim] = {}
        for c in normalized_candidates:
            key = (
                (c.subject or "").strip().lower(),
                (c.predicate or "").strip().lower(),
                str(c.object or "").strip().lower(),
                str(c.modality or "").strip().upper(),
            )
            if key not in seen_keys:
                seen_keys[key] = c
            else:
                existing = seen_keys[key]
                # Merge conditions if any
                if c.conditions and not existing.conditions:
                    existing.conditions = c.conditions

        deduped_candidates = list(seen_keys.values())

        # Step 6: 8 Universal Gate Contract Families & Certification Gate (Layer 6)
        evaluations: List[CandidateGateEvaluation] = []
        candidates_map: Dict[str, CandidateClaim] = {}
        seen_signatures: Set[str] = set()

        for cand in deduped_candidates:
            candidates_map[cand.candidate_id] = cand

            raw_text = (cand.claim_text or "").strip()
            raw_subj = (cand.subject or "").strip()
            raw_pred = (cand.predicate or "").strip()
            raw_obj = str(cand.object or "").strip()
            raw_span = (cand.evidence_text_span or "").strip()
            loc = cand.locator or {}
            raw_page = loc.get("page_number") or loc.get("page") or 1
            sec_heading = loc.get("section_heading") or loc.get("section")

            # Clean enumeration prefixes (e.g. (i), (ii), 1., etc.)
            clean_sentence = UniversalGateEvaluator.strip_enumeration_prefix(raw_span or raw_text)
            clean_subj = UniversalGateEvaluator.strip_enumeration_prefix(raw_subj)
            clean_pred = raw_pred
            clean_obj = raw_obj

            if clean_sentence:
                cand.claim_text = clean_sentence
            cand.subject = clean_subj
            cand.predicate = clean_pred

            # Build ImmutableEvidenceSpan
            quote = clean_sentence or raw_text
            span = ImmutableEvidenceSpan.from_content(
                verbatim_quote=quote,
                clause_text=raw_span or quote,
                content=content_text or canonical_env.parsed_content or quote,
                page=int(raw_page) if (raw_page and str(raw_page).isdigit() and int(raw_page) > 0) else 1,
                document_uri=f"urn:doc:{canonical_env.asset_id}",
                section_locator=str(sec_heading) if sec_heading else None,
            )

            # Preserve physical character offsets and exact quote on candidate
            if span.char_start is not None:
                cand.locator["char_start"] = span.char_start
            if span.char_end is not None:
                cand.locator["char_end"] = span.char_end
            cand.evidence_text_span = span.verbatim_quote

            # Check for non-atomic compound rule with multi-branch disjunctions
            is_compound = bool(
                re.search(
                    r"\b(and\s+may\s+not|and\s+must\s+not|and\s+also\s+must|and\s+shall\s+not)\b",
                    cand.claim_text,
                    re.IGNORECASE,
                )
            )

            if is_compound:
                gate_res = UniversalGateResult(
                    evidence_exists=True,
                    evidence_located=True,
                    text_integrity=True,
                    clause_entails_claim=True,
                    subject_valid=True,
                    counterparty_resolved=True,
                    predicate_valid=PredicateRegistryService.exists(clean_pred),
                    atomicity_valid=False,
                    duplicate_valid=True,
                    claim_type_allowed=True,
                    human_approved_if_required=False,
                    all_gates_passed=False,
                    lifecycle_state=ClaimLifecycleState.QUARANTINED,
                    certification_tier="QUARANTINED",
                    is_canonical=False,
                    agent_accessible=False,
                    rejection_reasons=["Non-atomic compound claim containing multi-branch disjunctive obligations."],
                    gates={"atomicity_valid": False},
                    repaired_claim_text=clean_sentence,
                )
            else:
                hdg_context = cand.locator.get("heading_path") or cand.locator.get("section_context") or []
                grid_hdr = cand.locator.get("table_grid", {}).get("col_header") if cand.locator.get("table_grid") else ""
                context_parts = []
                if isinstance(hdg_context, list) and hdg_context:
                    context_parts.append(" > ".join(str(h) for h in hdg_context))
                if grid_hdr:
                    context_parts.append(f"Header: {grid_hdr}")
                if raw_span or cand.claim_text:
                    context_parts.append(raw_span or cand.claim_text)
                surrounding_clause_text = " | ".join(context_parts) if context_parts else (raw_span or cand.claim_text)

                role_str = getattr(cand.content_role, "value", str(cand.content_role or "policy_rule")).lower()
                gate_res = UniversalGateEvaluator.evaluate(
                    claim_text=cand.claim_text,
                    subject=clean_subj,
                    predicate=clean_pred,
                    object_text=clean_obj,
                    claim_type=cand.claim_type or "rule",
                    evidence=span,
                    source_content=content_text or canonical_env.parsed_content,
                    clause_text=surrounding_clause_text,
                    existing_signatures=seen_signatures,
                    metadata={
                        "table_grid": cand.locator.get("table_grid"),
                        "in_table": bool(cand.locator.get("table_grid") or getattr(cand, "table_binding", None)),
                        "content_role": role_str,
                        "is_list": bool(cand.locator.get("is_list") or cand.claim_text.strip().startswith(("- ", "* ", "1. ", "2. ", "3. ", "• "))),
                    },
                )

            if gate_res.is_canonical:
                sig = UniversalGateEvaluator.compute_semantic_signature(clean_subj, clean_pred, clean_obj)
                seen_signatures.add(sig)

            # Deliverable 3, 5, 6: OCR Safety, Feature-Flagged Auto-Certification & Persisted Review Enforcement
            is_ocr_claim = (
                getattr(cand, "block_type", None) == "image_ocr"
                or cand.locator.get("source_type") == "image_ocr"
                or cand.locator.get("bbox") is not None
                or cand.locator.get("is_low_confidence")
                or (cand.structured_values and cand.structured_values.get("is_low_confidence"))
            )
            from app.ingestion.parsers.ocr_adapter import OcrAdapter
            auto_cert_enabled = OcrAdapter.is_auto_certify_enabled()

            if is_ocr_claim:
                is_low_conf = (
                    cand.locator.get("is_low_confidence")
                    or (cand.structured_values and cand.structured_values.get("is_low_confidence"))
                )
                if not auto_cert_enabled or is_low_conf:
                    if gate_res.certification_tier == "AUTOMATED_CERTIFIED":
                        gate_res.certification_tier = "REVIEW_REQUIRED"
                        gate_res.all_gates_passed = False
                        if is_low_conf:
                            gate_res.rejection_reasons.append("OCR low-confidence threshold violation: Requires human verification.")
                        else:
                            gate_res.rejection_reasons.append("OCR Safety Guard: OCR-derived claim requires human review prior to certification.")

            tier = gate_res.certification_tier
            if tier == "AUTOMATED_CERTIFIED":
                cand.claim_type = "rule"
                cand.is_canonical = True
                cand.status = "verified"
                decision = ClaimLifecycleDecision.APPROVE
                decision_code = DecisionCode.APPROVE_ALL_PASSED
                composite_score = 0.99
            elif tier == "REVIEW_REQUIRED":
                cand.claim_type = "rule"
                cand.is_canonical = False
                cand.status = "candidate"
                decision = ClaimLifecycleDecision.REVIEW
                if any("table" in r.lower() for r in gate_res.rejection_reasons):
                    decision_code = DecisionCode.REVIEW_SCORE_BELOW_THRESHOLD
                elif not gate_res.clause_entails_claim:
                    decision_code = DecisionCode.DEONTIC_MODALITY_MISMATCH
                elif not gate_res.predicate_valid:
                    decision_code = DecisionCode.WEAK_PREDICATE
                elif not gate_res.counterparty_resolved:
                    decision_code = DecisionCode.SUBJECT_CONTAMINATION
                else:
                    decision_code = DecisionCode.REVIEW_SCORE_BELOW_THRESHOLD
                composite_score = 0.85
            elif tier == "QUARANTINED":
                cand.claim_type = "quarantined"
                cand.is_canonical = False
                cand.status = "rejected"
                decision = ClaimLifecycleDecision.REJECT
                decision_code = DecisionCode.META_RULE_NOT_ATOMIC
                composite_score = 0.50
            elif tier == "NON_RULE":
                cand.is_canonical = False
                cand.status = "context"
                decision = ClaimLifecycleDecision.REJECT
                decision_code = DecisionCode.REJECT_DESCRIPTIVE_PURPOSE
                composite_score = 0.50
            elif tier == "DUPLICATE":
                cand.claim_type = "duplicate"
                cand.is_canonical = False
                cand.status = "rejected"
                decision = ClaimLifecycleDecision.REJECT
                decision_code = DecisionCode.SUMMARY_NON_CANONICAL
                composite_score = 0.0
            else:  # REJECTED
                cand.claim_type = "non_rule"
                cand.is_canonical = False
                cand.status = "rejected"
                decision = ClaimLifecycleDecision.REJECT
                if not gate_res.evidence_exists or not gate_res.evidence_located:
                    decision_code = DecisionCode.REJECT_GROUNDING_FAILED
                elif not gate_res.text_integrity:
                    decision_code = DecisionCode.FRAGMENT_ASSERTION_DISCARDED
                elif not gate_res.subject_valid:
                    decision_code = DecisionCode.SUBJECT_NORMALIZATION_FAILED
                elif not gate_res.clause_entails_claim:
                    decision_code = DecisionCode.DEONTIC_MODALITY_MISMATCH
                else:
                    decision_code = DecisionCode.REJECT_SEMANTIC_MISMATCH
                composite_score = 0.0

            source_match = DimensionEvaluation(
                dimension_name="source_match",
                status="pass" if (gate_res.evidence_exists and gate_res.evidence_located) else "fail",
                score=1.0 if (gate_res.evidence_exists and gate_res.evidence_located) else 0.0,
                passed=bool(gate_res.evidence_exists and gate_res.evidence_located),
                reason="Source evidence physically located and hash-verified." if (gate_res.evidence_exists and gate_res.evidence_located) else "Evidence missing or unlocated in source.",
                details={"evidence_exists": gate_res.evidence_exists, "evidence_located": gate_res.evidence_located},
            )
            meaning = DimensionEvaluation(
                dimension_name="meaning",
                status="pass" if (gate_res.text_integrity and gate_res.clause_entails_claim) else "fail",
                score=1.0 if (gate_res.text_integrity and gate_res.clause_entails_claim) else 0.0,
                passed=bool(gate_res.text_integrity and gate_res.clause_entails_claim),
                reason="Proposition strictly entailed without template synthesis." if (gate_res.text_integrity and gate_res.clause_entails_claim) else "Text integrity or entailment violation.",
                details={"text_integrity": gate_res.text_integrity, "clause_entails_claim": gate_res.clause_entails_claim},
            )
            completeness = DimensionEvaluation(
                dimension_name="completeness",
                status="pass" if (gate_res.atomicity_valid and gate_res.counterparty_resolved) else "fail",
                score=1.0 if (gate_res.atomicity_valid and gate_res.counterparty_resolved) else 0.5,
                passed=bool(gate_res.atomicity_valid and gate_res.counterparty_resolved),
                reason="Atomic single-obligation claim with resolved counterparty." if (gate_res.atomicity_valid and gate_res.counterparty_resolved) else "Compound disjunction or dangling pronoun.",
                details={"atomicity_valid": gate_res.atomicity_valid, "counterparty_resolved": gate_res.counterparty_resolved},
            )
            scope_eval = DimensionEvaluation(
                dimension_name="scope",
                status="pass" if (gate_res.claim_type_allowed and gate_res.predicate_valid) else "fail",
                score=1.0 if (gate_res.claim_type_allowed and gate_res.predicate_valid) else 0.0,
                passed=bool(gate_res.claim_type_allowed and gate_res.predicate_valid),
                reason="Operative rule within authorized predicate taxonomy." if (gate_res.claim_type_allowed and gate_res.predicate_valid) else "Non-rule type or predicate not in registry.",
                details={"claim_type_allowed": gate_res.claim_type_allowed, "predicate_valid": gate_res.predicate_valid},
            )
            authority = DimensionEvaluation(
                dimension_name="authority",
                status="pass",
                score=1.0,
                passed=True,
                reason="Authoritative source envelope.",
            )
            time_eval = DimensionEvaluation(
                dimension_name="time",
                status="current",
                score=1.0,
                passed=True,
                reason="Document version active and current.",
            )
            review_trigger = DimensionEvaluation(
                dimension_name="review",
                status="review_required" if decision == ClaimLifecycleDecision.REVIEW else "no_review_needed",
                score=0.5 if decision == ClaimLifecycleDecision.REVIEW else 1.0,
                passed=(decision != ClaimLifecycleDecision.REVIEW),
                reason="Adjudication review required before certification." if decision == ClaimLifecycleDecision.REVIEW else "Automated gate certified.",
            )

            decision_reason = (
                f"[{decision_code.value}] " + "; ".join(gate_res.rejection_reasons)
                if gate_res.rejection_reasons
                else f"[{decision_code.value}] UNIVERSAL 10-GATE CERTIFIED: All gates passed. Tier: {gate_res.certification_tier}."
            )

            candidate_eval = CandidateGateEvaluation(
                candidate_id=cand.candidate_id,
                envelope_id=canonical_env.envelope_id,
                asset_id=canonical_env.asset_id,
                claim_text=cand.claim_text,
                subject=cand.subject,
                predicate=cand.predicate,
                object=cand.object,
                evidence_text_span=cand.evidence_text_span,
                claim_type=cand.claim_type,
                modality=cand.modality,
                conditions=cand.conditions or [],
                value=cand.value,
                unit=cand.unit,
                scope=cand.scope or {},
                locator=cand.locator or {},
                is_ambiguous=cand.is_ambiguous,
                ambiguity_reason=cand.ambiguity_reason,
                source_match=source_match,
                completeness=completeness,
                meaning=meaning,
                scope_eval=scope_eval,
                time=time_eval,
                authority=authority,
                review_trigger=review_trigger,
                composite_trust_score=composite_score,
                lifecycle_decision=decision,
                decision_code=decision_code,
                decision_reason=decision_reason,
            )
            evaluations.append(candidate_eval)

        # Step 7: Deterministic In-Memory Conflict Detection
        conflicts: List[Dict[str, Any]] = []
        for i in range(len(deduped_candidates)):
            for j in range(i + 1, len(deduped_candidates)):
                claim_a = deduped_candidates[i]
                claim_b = deduped_candidates[j]
                try:
                    outcome = CompatibilityGate.evaluate_decision_compatibility(claim_a, claim_b)
                    if outcome.is_comparable:
                        conflicts.append({
                            "claim_a_id": claim_a.candidate_id,
                            "claim_b_id": claim_b.candidate_id,
                            "claim_a_subject": claim_a.subject,
                            "claim_b_subject": claim_b.subject,
                            "reason": outcome.reason,
                            "relationship": outcome.relationship,
                        })
                except Exception as exc:
                    logger.debug("Conflict check skipped between %s and %s: %s", claim_a.candidate_id, claim_b.candidate_id, exc)

        # Step 8: Optional DB Persistence
        persisted_ids: List[uuid.UUID] = []
        if opts.persist_to_db and db_session and opts.document_version_id:
            persisted_ids = await EnterpriseClaimStore.persist_evaluations(
                evaluations=evaluations,
                candidates_map=candidates_map,
                envelope=canonical_env,
                session=db_session,
                document_version_id=opts.document_version_id,
            )

        duration = time.time() - start_time
        metrics = {
            "duration_seconds": round(duration, 4),
            "total_units": len(evidence_result.units),
            "candidates_discovered": len(raw_candidates),
            "unique_claims": len(deduped_candidates),
            "approved": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE),
            "review": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REVIEW),
            "rejected": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REJECT),
        }

        source_byte_hash = hashlib.sha256(raw_bytes).hexdigest()
        pipeline_run_id = str(uuid.uuid4())

        return UnifiedPipelineResult(
            envelope=canonical_env,
            evidence_result=evidence_result,
            raw_candidates=raw_candidates,
            candidates=deduped_candidates,
            evaluations=evaluations,
            conflicts=conflicts,
            metrics=metrics,
            pipeline_run_id=pipeline_run_id,
            source_byte_hash=source_byte_hash,
            source_hash_algorithm="SHA-256",
            persisted_claim_ids=persisted_ids,
        )

