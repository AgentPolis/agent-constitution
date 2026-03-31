"""
Tests for Retrospective and Prediction.
"""

from datetime import datetime, timedelta

import pytest

from constitution import Prediction, Retrospective


def _make_retro() -> Retrospective:
    return Retrospective()


class TestRetrospectiveRecordPrediction:
    def test_record_returns_prediction(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "Market will rise", 0.8)
        assert isinstance(pred, Prediction)

    def test_record_returns_prediction_with_unique_id(self):
        retro = _make_retro()
        p1 = retro.record_prediction("analyst", "claim 1", 0.7)
        p2 = retro.record_prediction("analyst", "claim 2", 0.8)
        assert p1.id != p2.id

    def test_record_id_is_non_empty_string(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "something", 0.9)
        assert isinstance(pred.id, str)
        assert len(pred.id) > 0

    def test_record_stores_in_predictions_list(self):
        retro = _make_retro()
        retro.record_prediction("analyst", "claim", 0.75)
        assert len(retro.predictions) == 1

    def test_record_sets_agent_credibility_to_1_0_if_new_agent(self):
        retro = _make_retro()
        retro.record_prediction("new_agent", "claim", 0.6)
        assert retro.get_credibility("new_agent") == 1.0

    def test_record_rejects_invalid_confidence(self):
        retro = _make_retro()
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            retro.record_prediction("analyst", "claim", 1.2)


class TestRetrospectiveVerify:
    def test_verify_returns_credibility_delta(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        delta = retro.verify(pred.id, "correct")
        assert isinstance(delta, float)

    def test_verify_correct_delta_is_positive(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        delta = retro.verify(pred.id, "correct")
        assert delta == pytest.approx(+0.05)

    def test_verify_incorrect_delta_is_negative(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        delta = retro.verify(pred.id, "incorrect")
        assert delta == pytest.approx(-0.10)

    def test_verify_partial_delta(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        delta = retro.verify(pred.id, "partial")
        assert delta == pytest.approx(+0.01)

    def test_verify_raises_for_unknown_prediction_id(self):
        retro = _make_retro()
        with pytest.raises(ValueError, match="not found"):
            retro.verify("nonexistent-id", "correct")

    def test_verify_raises_for_already_verified_prediction(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        retro.verify(pred.id, "correct")
        with pytest.raises(ValueError, match="already verified"):
            retro.verify(pred.id, "correct")

    def test_verify_rejects_invalid_outcome(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        with pytest.raises(ValueError, match="outcome must be one of"):
            retro.verify(pred.id, "unknown")

    def test_verify_updates_agent_credibility(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        retro.verify(pred.id, "correct")
        assert retro.get_credibility("analyst") == pytest.approx(1.05)

    def test_verify_updates_prediction_outcome(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        retro.verify(pred.id, "incorrect")
        assert pred.outcome == "incorrect"

    def test_verify_sets_verified_at(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        retro.verify(pred.id, "correct")
        assert pred.verified_at is not None
        assert isinstance(pred.verified_at, datetime)


class TestRetrospectiveGetPending:
    def test_get_pending_returns_past_verify_date(self):
        retro = _make_retro()
        # Manually create a prediction that's past due
        pred = retro.record_prediction("analyst", "old claim", 0.7, verify_after_days=1)
        # Backdate made_at to simulate past prediction
        pred.made_at = datetime.now() - timedelta(days=2)
        pending = retro.get_pending()
        assert pred in pending

    def test_get_pending_excludes_recent_predictions(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "recent claim", 0.7, verify_after_days=7)
        pending = retro.get_pending()
        assert pred not in pending

    def test_get_pending_excludes_already_verified(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "verified claim", 0.7, verify_after_days=1)
        pred.made_at = datetime.now() - timedelta(days=2)
        retro.verify(pred.id, "correct")
        pending = retro.get_pending()
        assert pred not in pending

    def test_get_pending_empty_returns_empty_list(self):
        retro = _make_retro()
        assert retro.get_pending() == []


class TestRetrospectiveGetCredibility:
    def test_get_credibility_returns_1_0_for_unknown_agent(self):
        retro = _make_retro()
        assert retro.get_credibility("unknown_agent") == 1.0

    def test_get_credibility_returns_current_score(self):
        retro = _make_retro()
        pred = retro.record_prediction("analyst", "claim", 0.8)
        retro.verify(pred.id, "incorrect")
        assert retro.get_credibility("analyst") == pytest.approx(0.90)


class TestRetrospectiveSummary:
    def test_summary_returns_dict(self):
        retro = _make_retro()
        result = retro.summary()
        assert isinstance(result, dict)

    def test_summary_has_total_predictions(self):
        retro = _make_retro()
        assert "total_predictions" in retro.summary()

    def test_summary_has_verified(self):
        retro = _make_retro()
        assert "verified" in retro.summary()

    def test_summary_has_correct(self):
        retro = _make_retro()
        assert "correct" in retro.summary()

    def test_summary_has_accuracy(self):
        retro = _make_retro()
        assert "accuracy" in retro.summary()

    def test_summary_counts_correctly(self):
        retro = _make_retro()
        p1 = retro.record_prediction("analyst", "claim 1", 0.8)
        p2 = retro.record_prediction("analyst", "claim 2", 0.7)
        retro.record_prediction("analyst", "claim 3", 0.6)
        retro.verify(p1.id, "correct")
        retro.verify(p2.id, "incorrect")
        summary = retro.summary()
        assert summary["total_predictions"] == 3
        assert summary["verified"] == 2
        assert summary["correct"] == 1
        assert summary["accuracy"] == pytest.approx(0.5)

    def test_summary_accuracy_zero_when_no_verified(self):
        retro = _make_retro()
        retro.record_prediction("analyst", "claim", 0.8)
        summary = retro.summary()
        assert summary["accuracy"] == 0.0

    def test_summary_empty_retro(self):
        retro = _make_retro()
        summary = retro.summary()
        assert summary["total_predictions"] == 0
        assert summary["verified"] == 0
        assert summary["correct"] == 0
        assert summary["accuracy"] == 0.0
