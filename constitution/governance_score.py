"""
Governance Score — quantifies how well a system follows constitutional governance.

The current weighted score uses five dimensions:

- epistemic_honesty: do responses surface uncertainty and calibrated confidence?
- constitutional_compliance: do responses satisfy required schemas / rules?
- debate_rigor: do high-stakes decisions receive structured adversarial review?
- calibration_accuracy: are past predictions later verified as correct?
- audit_completeness: is there enough trace data to inspect what happened?
"""

from dataclasses import dataclass

WEIGHTS = {
    "epistemic_honesty": 0.25,
    "constitutional_compliance": 0.25,
    "debate_rigor": 0.20,
    "calibration_accuracy": 0.15,
    "audit_completeness": 0.15,
}


@dataclass
class GovernanceReport:
    epistemic_honesty: float
    constitutional_compliance: float
    debate_rigor: float
    calibration_accuracy: float | None
    audit_completeness: float
    score: int
    badge: str
    label: str


def _resolve_dimension(
    explicit: float | None,
    alias: float | None,
    name: str,
) -> float | None:
    if explicit is not None and alias is not None and explicit != alias:
        raise ValueError(f"{name} received conflicting values: {explicit} vs {alias}")
    return explicit if explicit is not None else alias


def _validate_metric(name: str, value: float | None) -> None:
    if value is None:
        return
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def compute_governance_score(
    *,
    epistemic_honesty: float | None = None,
    constitutional_compliance: float | None = None,
    debate_rigor: float | None = None,
    calibration_accuracy: float | None = None,
    audit_completeness: float | None = None,
    # Backward-compatible aliases from the initial 3-dimension version.
    debate_coverage: float | None = None,
    constitution_compliance: float | None = None,
) -> GovernanceReport:
    """
    Compute governance score from weighted dimensions.

    Metrics must be 0.0-1.0. When calibration_accuracy is unavailable, the score
    is still computed against the full five-dimension weight table so the report
    remains provisional instead of inflating to a perfect score.
    """
    constitutional_compliance = _resolve_dimension(
        constitutional_compliance,
        constitution_compliance,
        "constitutional_compliance",
    )
    debate_rigor = _resolve_dimension(debate_rigor, debate_coverage, "debate_rigor")

    metrics = {
        "epistemic_honesty": 0.0 if epistemic_honesty is None else epistemic_honesty,
        "constitutional_compliance": (
            0.0 if constitutional_compliance is None else constitutional_compliance
        ),
        "debate_rigor": 0.0 if debate_rigor is None else debate_rigor,
        "calibration_accuracy": calibration_accuracy,
        "audit_completeness": 0.0 if audit_completeness is None else audit_completeness,
    }

    for name, value in metrics.items():
        _validate_metric(name, value)

    available_weight = 0.0
    weighted_total = 0.0
    for name, weight in WEIGHTS.items():
        value = metrics[name]
        if value is None:
            available_weight += weight
            continue
        weighted_total += value * weight
        available_weight += weight

    score = 0
    if available_weight > 0:
        score = max(0, min(100, int(round((weighted_total / available_weight) * 100))))

    if metrics["calibration_accuracy"] is None:
        badge, label = "uncalibrated", "Not yet calibrated"
    elif score >= 80:
        badge, label = "green", "Well-governed"
    elif score >= 60:
        badge, label = "yellow", "Partially governed"
    else:
        badge, label = "red", "Needs governance"

    return GovernanceReport(
        epistemic_honesty=metrics["epistemic_honesty"],
        constitutional_compliance=metrics["constitutional_compliance"],
        debate_rigor=metrics["debate_rigor"],
        calibration_accuracy=metrics["calibration_accuracy"],
        audit_completeness=metrics["audit_completeness"],
        score=score,
        badge=badge,
        label=label,
    )


def aggregate_governance_reports(reports: list[GovernanceReport]) -> GovernanceReport:
    """Average multiple governance reports into one aggregate report."""
    if not reports:
        return uncalibrated_report()

    calibration_values = [
        report.calibration_accuracy
        for report in reports
        if report.calibration_accuracy is not None
    ]

    return compute_governance_score(
        epistemic_honesty=(
            sum(report.epistemic_honesty for report in reports) / len(reports)
        ),
        constitutional_compliance=(
            sum(report.constitutional_compliance for report in reports) / len(reports)
        ),
        debate_rigor=(sum(report.debate_rigor for report in reports) / len(reports)),
        calibration_accuracy=(
            sum(calibration_values) / len(calibration_values)
            if calibration_values
            else None
        ),
        audit_completeness=(
            sum(report.audit_completeness for report in reports) / len(reports)
        ),
    )


def uncalibrated_report() -> GovernanceReport:
    """Return a placeholder report when no historical data exists."""
    return GovernanceReport(
        epistemic_honesty=0.0,
        constitutional_compliance=0.0,
        debate_rigor=0.0,
        calibration_accuracy=None,
        audit_completeness=0.0,
        score=0,
        badge="uncalibrated",
        label="Not yet calibrated",
    )
