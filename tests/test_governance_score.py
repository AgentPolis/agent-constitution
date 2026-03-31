import pytest

from constitution.governance_score import (
    GovernanceReport,
    aggregate_governance_reports,
    compute_governance_score,
    uncalibrated_report,
)


class TestComputeGovernanceScore:
    def test_perfect_score(self):
        r = compute_governance_score(
            epistemic_honesty=1.0,
            constitutional_compliance=1.0,
            debate_rigor=1.0,
            calibration_accuracy=1.0,
            audit_completeness=1.0,
        )
        assert r.score == 100
        assert r.badge == "green"
        assert r.label == "Well-governed"

    def test_zero_score(self):
        r = compute_governance_score(
            epistemic_honesty=0.0,
            constitutional_compliance=0.0,
            debate_rigor=0.0,
            calibration_accuracy=0.0,
            audit_completeness=0.0,
        )
        assert r.score == 0
        assert r.badge == "red"

    def test_weighted_formula_uses_five_dimensions(self):
        r = compute_governance_score(
            epistemic_honesty=1.0,
            constitutional_compliance=0.0,
            debate_rigor=0.0,
            calibration_accuracy=0.0,
            audit_completeness=0.0,
        )
        assert r.score == 25

    def test_backward_compatible_aliases_still_work(self):
        r = compute_governance_score(
            debate_coverage=0.8,
            constitution_compliance=0.7,
            calibration_accuracy=0.9,
        )
        assert r.debate_rigor == 0.8
        assert r.constitutional_compliance == 0.7
        assert r.calibration_accuracy == 0.9

    def test_uncalibrated_when_accuracy_missing(self):
        r = compute_governance_score(
            epistemic_honesty=0.9,
            constitutional_compliance=0.9,
            debate_rigor=0.8,
            audit_completeness=0.9,
        )
        assert r.badge == "uncalibrated"
        assert r.label == "Not yet calibrated"
        assert r.score > 0
        assert r.score < 100

    def test_returns_governance_report(self):
        r = compute_governance_score(
            epistemic_honesty=0.7,
            constitutional_compliance=0.8,
            debate_rigor=0.9,
            calibration_accuracy=0.6,
            audit_completeness=0.95,
        )
        assert isinstance(r, GovernanceReport)
        assert r.epistemic_honesty == 0.7
        assert r.constitutional_compliance == 0.8
        assert r.debate_rigor == 0.9
        assert r.audit_completeness == 0.95

    def test_input_validation_negative(self):
        with pytest.raises(ValueError):
            compute_governance_score(epistemic_honesty=-0.1)

    def test_input_validation_over_one(self):
        with pytest.raises(ValueError):
            compute_governance_score(audit_completeness=1.5)


class TestAggregateGovernanceReports:
    def test_aggregate_averages_reports(self):
        first = compute_governance_score(
            epistemic_honesty=1.0,
            constitutional_compliance=0.8,
            debate_rigor=0.6,
            calibration_accuracy=0.5,
            audit_completeness=0.9,
        )
        second = compute_governance_score(
            epistemic_honesty=0.5,
            constitutional_compliance=0.6,
            debate_rigor=0.4,
            calibration_accuracy=0.7,
            audit_completeness=0.8,
        )
        aggregated = aggregate_governance_reports([first, second])
        assert aggregated.epistemic_honesty == pytest.approx(0.75)
        assert aggregated.calibration_accuracy == pytest.approx(0.6)

    def test_empty_aggregate_returns_uncalibrated(self):
        aggregated = aggregate_governance_reports([])
        assert aggregated.badge == "uncalibrated"


class TestUncalibratedReport:
    def test_returns_uncalibrated_badge(self):
        r = uncalibrated_report()
        assert r.badge == "uncalibrated"
        assert r.label == "Not yet calibrated"
        assert r.score == 0
        assert r.calibration_accuracy is None
