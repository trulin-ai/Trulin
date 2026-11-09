"""
Regression & Unit Tests for the Selective NLP Extraction Pipeline (Layers 3–7).
Tests NLPManager, multi-level evidence units, cascaded NER, canonical sentence framing,
DeBERTa NLI integration, and condition preservation gate.
"""

import pytest
from app.core.nlp_manager import NLPManager
from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer
from app.extraction.clause_entailment_evaluator import ClauseEntailmentEvaluator, EntailmentLabel
from app.extraction.models import CandidateClaim
from app.extraction.subject_normalizer import SubjectNormalizer
from app.validation_gate.evaluators import CompletenessEvaluator


class TestSelectiveNLPComponents:
    """Test individual selective NLP components."""

    def test_nlp_manager_sentence_spans(self):
        text = "Employees are eligible for 24 days leave. Requests must be submitted 7 days prior. The HR department manages records."
        spans = NLPManager.get_sentence_spans(text)
        assert len(spans) == 3
        # Verify first sentence
        s0, start0, end0 = spans[0]
        assert "eligible for 24 days leave" in s0
        assert text[start0:end0] == s0
        # Verify second sentence
        s1, start1, end1 = spans[1]
        assert "Requests must be submitted" in s1
        assert text[start1:end1] == s1

    def test_subject_normalizer_cascaded_entity_extraction(self):
        sample = "Refunds exceeding $10,000 must be approved within 30 days."
        entities = SubjectNormalizer.resolve_entity_cascaded(sample)
        assert "entities" in entities
        labels = {e["label"] for e in entities["entities"]}
        # Verify Tier 1 regex extracted MONEY and DURATION
        assert "MONEY" in labels
        assert "DURATION" in labels
        texts = [e["text"] for e in entities["entities"]]
        assert any("$10,000" in t for t in texts)
        assert any("30 days" in t for t in texts)

    def test_canonical_sentence_synthesis(self):
        sentence = ClaimQualityNormalizer.synthesize_canonical_sentence(
            subject="Employee",
            modality="ENTITLEMENT",
            predicate="eligible_for",
            object_val="24 days of annual leave",
            conditions=["completed at least 12 months of continuous service"],
            exceptions=["during probation period"],
        )
        assert "Employee is entitled to eligible for 24 days of annual leave" in sentence or "Employee is entitled to" in sentence
        assert "provided that completed at least 12 months" in sentence
        assert "except where during probation period" in sentence

    def test_clause_entailment_evaluator_preserves_entailment(self):
        premise = "Employees who have completed at least 12 months of continuous service are eligible for 24 days of annual leave."
        verdict = ClauseEntailmentEvaluator.evaluate(
            premise_clause=premise,
            subject="Employees",
            modality="ENTITLEMENT",
            predicate="eligible_for_annual_leave",
            object_text="24 days of annual leave",
            conditions=["completed at least 12 months of continuous service"],
        )
        assert verdict.clause_entails_claim is True
        assert verdict.label == EntailmentLabel.ENTAILMENT

    def test_condition_preservation_gate_catches_dropped_condition(self):
        """If evidence contains restrictive condition and claim omitted it, completeness must flag it."""
        cand = CandidateClaim.create_for_test(
            claim_text="Employees are entitled to 24 days of annual leave.",
            subject="Employees",
            predicate="eligible_for",
            object_="24 days of annual leave",
            evidence_span="Employees who have completed at least 12 months of continuous service are eligible for 24 days of annual leave.",
            conditions=[],  # Dropped!
        )
        res = CompletenessEvaluator.evaluate(cand)
        assert res.passed is False
        assert "Condition preservation" in res.reason
        assert "prior service qualification" in res.reason

    def test_condition_preservation_gate_passes_when_condition_retained(self):
        """When condition is present in structured conditions, gate passes."""
        cand = CandidateClaim.create_for_test(
            claim_text="Employees are entitled to 24 days of annual leave.",
            subject="Employees",
            predicate="eligible_for",
            object_="24 days of annual leave",
            evidence_span="Employees who have completed at least 12 months of continuous service are eligible for 24 days of annual leave.",
            conditions=[{"field": "continuous_service", "operator": ">=", "value": 12, "unit": "months"}],
        )
        res = CompletenessEvaluator.evaluate(cand)
        assert res.passed is True
