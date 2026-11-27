"""
Feedback Telemetry & Failure Taxonomy Service.

Enables rigorous diagnostic tracking of Copilot errors:
Instead of treating failures as generic "bad model responses", every issue
is classified into an actionable pipeline stage:
- PARSING: Document linearization or layout table error
- EXTRACTION: Meaning divergence (e.g. 'immediately upon receipt' became '30 days')
- REFERENCE_LABELS: Stale document version, wrong section tag
- RETRIEVAL: RRF search failed to surface the operative clause
- MISSING_CONTEXT: Legitimate policy gap (unanswerable topic)
- GENERATION: LLM hallucination or invented entity
- VERIFICATION: AnswerVerifier flagged ungrounded number or missing citation
- AUTHORIZATION: Scoped RBAC boundary violation
- UI_DISPLAY: Presentation or citation chip rendering issue
"""

import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FailureTaxonomyStage(str, enum.Enum):
    PARSING = "parsing"
    EXTRACTION = "extraction"
    REFERENCE_LABELS = "reference_labels"
    RETRIEVAL = "retrieval"
    MISSING_CONTEXT = "missing_context"
    GENERATION = "generation"
    VERIFICATION = "verification"
    AUTHORIZATION = "authorization"
    UI_DISPLAY = "ui_display"


class PilotVerdict(str, enum.Enum):
    PASS = "PASS"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    UNSAFE = "UNSAFE"


class PilotIssueCategory(str, enum.Enum):
    SCOPE_FAILURE = "SCOPE_FAILURE"
    MATERIAL_MUTATION = "MATERIAL_MUTATION"
    EVIDENCE_MAPPING_ERROR = "EVIDENCE_MAPPING_ERROR"
    MISSING_CONDITION = "MISSING_CONDITION"
    SILENT_CONFLICT = "SILENT_CONFLICT"
    DEPTH_QUALITY = "DEPTH_QUALITY"
    NAVIGATION_FAILURE = "NAVIGATION_FAILURE"
    OTHER = "OTHER"


class PilotChecklist(BaseModel):
    scope_identified: bool = True
    answers_inquiry: bool = True
    grounded_evidence: bool = True
    conditions_surfaced: bool = True
    conflicts_flagged: bool = True
    depth_appropriate: bool = True
    navigation_works: bool = True
    tone_and_safety: bool = True


class PilotFeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    reviewer_name: str = "pilot_reviewer"
    reviewer_role: str = "evaluator"
    verdict: PilotVerdict
    issue_category: PilotIssueCategory | None = None
    checklist: PilotChecklist | None = None
    notes: str | None = None
    latency_ms: float | None = None
    feature_flags: dict[str, Any] | None = None
    wording_outcome: dict[str, Any] | str | None = None
    question_type: str | None = None
    depth: str | None = None


class FeedbackSubmitRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str = Field(description="'thumbs_up', 'thumbs_down', or 'disputed'")
    failure_stage: FailureTaxonomyStage | None = None
    notes: str | None = None
    suggested_correction: str | None = None
    user_id: str | None = None
    user_role: str | None = None


# In-memory stores for telemetry & pilot feedback
_FEEDBACK_LOG: list[dict[str, Any]] = []
_PILOT_FEEDBACK_LOG: list[dict[str, Any]] = []


class FeedbackTelemetryService:
    """Service to record, categorize, and route Copilot failures and Pilot Evaluations."""

    @classmethod
    def record_feedback(cls, request_in: FeedbackSubmitRequest) -> dict[str, Any]:
        """Records a user/evaluator feedback event with failure taxonomy."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "message_id": request_in.message_id,
            "session_id": request_in.session_id,
            "user_id": request_in.user_id,
            "user_role": request_in.user_role or "evaluator",
            "rating": request_in.rating,
            "failure_stage": request_in.failure_stage.value if request_in.failure_stage else None,
            "notes": request_in.notes,
            "suggested_correction": request_in.suggested_correction,
            "status": "staged_for_steward" if request_in.rating != "thumbs_up" else "closed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _FEEDBACK_LOG.append(record)
        logger.info(
            "Copilot feedback recorded: %s (Rating: %s, Stage: %s)",
            record_id,
            request_in.rating,
            request_in.failure_stage,
        )
        return record

    @classmethod
    def record_pilot_feedback(cls, request_in: PilotFeedbackRequest) -> dict[str, Any]:
        """Records a formal reviewer pilot evaluation for an adaptive answer."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "message_id": request_in.message_id,
            "session_id": request_in.session_id,
            "reviewer_name": request_in.reviewer_name,
            "reviewer_role": request_in.reviewer_role,
            "verdict": request_in.verdict.value,
            "issue_category": request_in.issue_category.value if request_in.issue_category else None,
            "checklist": request_in.checklist.model_dump() if request_in.checklist else None,
            "notes": request_in.notes,
            "latency_ms": request_in.latency_ms,
            "feature_flags": request_in.feature_flags,
            "wording_outcome": request_in.wording_outcome,
            "question_type": request_in.question_type,
            "depth": request_in.depth,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Replace existing review for same message if present, else append
        existing_idx = next((i for i, r in enumerate(_PILOT_FEEDBACK_LOG) if r["message_id"] == request_in.message_id), None)
        if existing_idx is not None:
            _PILOT_FEEDBACK_LOG[existing_idx] = record
        else:
            _PILOT_FEEDBACK_LOG.append(record)

        logger.info(
            "Pilot evaluation recorded: msg=%s, verdict=%s, category=%s, reviewer=%s",
            request_in.message_id,
            request_in.verdict.value,
            request_in.issue_category.value if request_in.issue_category else "NONE",
            request_in.reviewer_name,
        )
        return record

    @classmethod
    def list_pilot_feedback(cls, session_id: str | None = None) -> list[dict[str, Any]]:
        """Returns recorded pilot evaluations, optionally filtered by session."""
        if session_id:
            return [r for r in _PILOT_FEEDBACK_LOG if r["session_id"] == session_id]
        return list(_PILOT_FEEDBACK_LOG)

    @classmethod
    def get_pilot_feedback_for_message(cls, message_id: str) -> dict[str, Any] | None:
        """Finds pilot evaluation for a specific message."""
        return next((r for r in _PILOT_FEEDBACK_LOG if r["message_id"] == message_id), None)

    @classmethod
    def get_pilot_summary(cls) -> dict[str, Any]:
        """Aggregates pilot evaluations into summary statistics for acceptance review."""
        total = len(_PILOT_FEEDBACK_LOG)
        verdict_counts = {v.value: 0 for v in PilotVerdict}
        issue_counts = {cat.value: 0 for cat in PilotIssueCategory}
        checklist_sums = {
            "scope_identified": 0,
            "answers_inquiry": 0,
            "grounded_evidence": 0,
            "conditions_surfaced": 0,
            "conflicts_flagged": 0,
            "depth_appropriate": 0,
            "navigation_works": 0,
            "tone_and_safety": 0,
        }
        total_latency = 0.0
        latency_samples = 0
        wording_success_count = 0
        wording_eval_count = 0

        for r in _PILOT_FEEDBACK_LOG:
            v = r.get("verdict")
            if v in verdict_counts:
                verdict_counts[v] += 1
            cat = r.get("issue_category")
            if cat in issue_counts:
                issue_counts[cat] += 1
            if r.get("latency_ms") is not None:
                total_latency += float(r["latency_ms"])
                latency_samples += 1
            
            w_out = r.get("wording_outcome")
            if isinstance(w_out, dict) and w_out.get("requested"):
                wording_eval_count += 1
                if w_out.get("applied"):
                    wording_success_count += 1

            chk = r.get("checklist") or {}
            for k in checklist_sums:
                if chk.get(k, True):
                    checklist_sums[k] += 1

        checklist_rates = {
            k: (checklist_sums[k] / total) if total > 0 else 1.0
            for k in checklist_sums
        }

        return {
            "total_evaluations": total,
            "verdict_distribution": verdict_counts,
            "pass_rate": (verdict_counts["PASS"] / total) if total > 0 else 1.0,
            "unsafe_count": verdict_counts["UNSAFE"],
            "issue_category_distribution": issue_counts,
            "checklist_compliance_rates": checklist_rates,
            "avg_latency_ms": round(total_latency / latency_samples, 2) if latency_samples > 0 else 0.0,
            "wording_success_rate": (wording_success_count / wording_eval_count) if wording_eval_count > 0 else 1.0,
        }

    @classmethod
    def clear_pilot_feedback(cls) -> None:
        """Clears pilot feedback log (for tests)."""
        _PILOT_FEEDBACK_LOG.clear()

    @classmethod
    def get_stage_distribution(cls) -> dict[str, Any]:
        """Returns aggregated telemetry on root causes of failures."""
        total = len(_FEEDBACK_LOG)
        stage_counts = {stage.value: 0 for stage in FailureTaxonomyStage}
        positive_count = 0
        negative_count = 0

        for r in _FEEDBACK_LOG:
            if r["rating"] == "thumbs_up":
                positive_count += 1
            else:
                negative_count += 1
            if r.get("failure_stage") and r["failure_stage"] in stage_counts:
                stage_counts[r["failure_stage"]] += 1

        return {
            "total_feedback_events": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "satisfaction_rate": (positive_count / total) if total > 0 else 1.0,
            "root_cause_distribution": stage_counts,
        }

    @classmethod
    def list_steward_review_queue(cls) -> list[dict[str, Any]]:
        """Returns all feedback events requiring Data Steward context remediation."""
        return [r for r in _FEEDBACK_LOG if r["status"] == "steward_review_required" or r["rating"] != "thumbs_up"]
