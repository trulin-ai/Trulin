import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CalibrationObservation(BaseModel):
    conflict_id: str
    impact_score: float
    predicted_blast: str  # "CRITICAL_BLAST", "HIGH_BLAST", "ROUTINE"
    downstream_workflows_count: int
    reviewer_decision: str  # "APPROVE", "REJECT", "ESCALATE", "DEFER"
    actual_escalated: bool
    rationale: Optional[str] = None


class BlastCalibrationReport(BaseModel):
    total_observations: int
    is_calibrated: bool = Field(..., description="True when >= 30 empirical observations have been recorded")
    sample_confidence: str
    false_critical_rate: float
    false_routine_rate: float
    empirical_escalation_correlation: float
    workflow_sensitivity_coefficient: float = 0.30  # Weight applied to downstream workflows
    predicted_critical_count: int
    actual_escalated_count: int
    calibration_status: str  # "CALIBRATED_PRODUCTION_READY" or "UNWEIGHTED_ASSUMPTIONS_PROVISIONAL"


class BlastRadiusCalibrator:
    """Telemetry and calibration tracker for blast radius scoring."""

    _observations: List[CalibrationObservation] = []

    @classmethod
    def record_observation(
        cls,
        conflict_id: str,
        impact_score: float,
        predicted_blast: str,
        downstream_workflows_count: int,
        reviewer_decision: str,
        actual_escalated: bool,
        rationale: Optional[str] = None,
    ) -> None:
        cls._observations.append(
            CalibrationObservation(
                conflict_id=str(conflict_id),
                impact_score=float(impact_score),
                predicted_blast=predicted_blast,
                downstream_workflows_count=int(downstream_workflows_count),
                reviewer_decision=reviewer_decision,
                actual_escalated=actual_escalated,
                rationale=rationale,
            )
        )

    @classmethod
    def get_calibration_report(cls) -> BlastCalibrationReport:
        n = len(cls._observations)
        if n == 0:
            return BlastCalibrationReport(
                total_observations=0,
                is_calibrated=False,
                sample_confidence="ZERO_OBSERVATIONS (Weights remain theoretical assumptions)",
                false_critical_rate=0.0,
                false_routine_rate=0.0,
                empirical_escalation_correlation=0.0,
                workflow_sensitivity_coefficient=0.30,
                predicted_critical_count=0,
                actual_escalated_count=0,
                calibration_status="UNWEIGHTED_ASSUMPTIONS_PROVISIONAL",
            )

        pred_critical = [o for o in cls._observations if o.predicted_blast in ("CRITICAL_BLAST", "HIGH_BLAST")]
        pred_routine = [o for o in cls._observations if o.predicted_blast == "ROUTINE"]
        actual_esc = [o for o in cls._observations if o.actual_escalated]

        # False-critical: predicted critical, but actual reviewer did not escalate
        false_crit_count = sum(1 for o in pred_critical if not o.actual_escalated)
        false_crit_rate = round(false_crit_count / max(1, len(pred_critical)), 4) if pred_critical else 0.0

        # False-routine: predicted routine, but actual reviewer escalated
        false_routine_count = sum(1 for o in pred_routine if o.actual_escalated)
        false_routine_rate = round(false_routine_count / max(1, len(pred_routine)), 4) if pred_routine else 0.0

        # Pearson correlation between impact score and actual escalation (0 or 1)
        scores = [o.impact_score for o in cls._observations]
        escalations = [1.0 if o.actual_escalated else 0.0 for o in cls._observations]
        mean_s = sum(scores) / n
        mean_e = sum(escalations) / n

        num = sum((scores[i] - mean_s) * (escalations[i] - mean_e) for i in range(n))
        den_s = sum((s - mean_s) ** 2 for s in scores)
        den_e = sum((e - mean_e) ** 2 for e in escalations)
        den = math.sqrt(den_s * den_e)

        corr = round(num / den, 4) if den > 1e-6 else 0.0

        is_calibrated = n >= 30
        status = "CALIBRATED_PRODUCTION_READY" if is_calibrated else "UNWEIGHTED_ASSUMPTIONS_PROVISIONAL"
        confidence = f"CALIBRATED_STATISTICAL_SAMPLE (N={n}>=30)" if is_calibrated else f"PROVISIONAL_OBSERVATIONS (N={n}<30; weights remain directional)"

        return BlastCalibrationReport(
            total_observations=n,
            is_calibrated=is_calibrated,
            sample_confidence=confidence,
            false_critical_rate=false_crit_rate,
            false_routine_rate=false_routine_rate,
            empirical_escalation_correlation=corr,
            workflow_sensitivity_coefficient=0.30,
            predicted_critical_count=len(pred_critical),
            actual_escalated_count=len(actual_esc),
            calibration_status=status,
        )

    @classmethod
    def reset(cls) -> None:
        cls._observations.clear()

