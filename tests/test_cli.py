"""
Tests for CLI helper functions.
No real API calls — uses MockAdapter and in-memory data.
"""

import json
from unittest.mock import patch

import pytest

from adapters import MockAdapter
from constitution import BaseAgent, DebateResult
from constitution.cli import (
    _analyst_response_is_valid,
    _append_governance_history,
    _build_adapter,
    _build_governance_record,
    _epistemic_honesty_score,
    _has_calibrated_confidence,
    _load_governance_history,
    _parse_json_object,
    _resolve_role_config,
    build_parser,
)

# ---------------------------------------------------------------------------
# _parse_json_object
# ---------------------------------------------------------------------------

class TestParseJsonObject:
    def test_valid_json_object(self):
        assert _parse_json_object('{"a": 1}') == {"a": 1}

    def test_json_array_returns_none(self):
        assert _parse_json_object("[1, 2]") is None

    def test_invalid_json_returns_none(self):
        assert _parse_json_object("not json") is None

    def test_none_input_returns_none(self):
        assert _parse_json_object(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_json_object("") is None


# ---------------------------------------------------------------------------
# _has_calibrated_confidence
# ---------------------------------------------------------------------------

class TestHasCalibratedConfidence:
    def test_valid_confidence(self):
        assert _has_calibrated_confidence('{"confidence": 0.75}') is True

    def test_confidence_zero(self):
        assert _has_calibrated_confidence('{"confidence": 0.0}') is True

    def test_confidence_one(self):
        assert _has_calibrated_confidence('{"confidence": 1.0}') is True

    def test_confidence_out_of_range(self):
        assert _has_calibrated_confidence('{"confidence": 1.5}') is False

    def test_confidence_negative(self):
        assert _has_calibrated_confidence('{"confidence": -0.1}') is False

    def test_no_confidence_field(self):
        assert _has_calibrated_confidence('{"score": 5}') is False

    def test_non_json(self):
        assert _has_calibrated_confidence("plain text") is False


# ---------------------------------------------------------------------------
# _epistemic_honesty_score
# ---------------------------------------------------------------------------

class TestEpistemicHonestyScore:
    def test_empty_responses(self):
        assert _epistemic_honesty_score([]) == 0.0

    def test_all_calibrated(self):
        responses = ['{"confidence": 0.5}', '{"confidence": 0.8}']
        assert _epistemic_honesty_score(responses) == 1.0

    def test_speculation_tag(self):
        responses = ["This is [SPECULATION] about the market"]
        assert _epistemic_honesty_score(responses) == 1.0

    def test_i_dont_know(self):
        responses = ["I don't know the exact figure"]
        assert _epistemic_honesty_score(responses) == 1.0

    def test_no_honesty_signals(self):
        responses = ["The market is huge", "Revenue will triple"]
        assert _epistemic_honesty_score(responses) == 0.0

    def test_mixed(self):
        responses = ['{"confidence": 0.5}', "Revenue will triple"]
        assert _epistemic_honesty_score(responses) == 0.5


# ---------------------------------------------------------------------------
# _analyst_response_is_valid
# ---------------------------------------------------------------------------

class TestAnalystResponseIsValid:
    def test_valid_response(self):
        raw = json.dumps({
            "score": 35,
            "summary": "Looks promising",
            "dimensions": {"market": 8, "team": 7},
            "confidence": 0.75,
        })
        assert _analyst_response_is_valid(raw) is True

    def test_missing_score(self):
        raw = json.dumps({
            "summary": "No score",
            "dimensions": {},
            "confidence": 0.5,
        })
        assert _analyst_response_is_valid(raw) is False

    def test_missing_confidence(self):
        raw = json.dumps({
            "score": 35,
            "summary": "No confidence",
            "dimensions": {},
        })
        assert _analyst_response_is_valid(raw) is False

    def test_non_json(self):
        assert _analyst_response_is_valid("just text") is False


# ---------------------------------------------------------------------------
# _build_adapter
# ---------------------------------------------------------------------------

class TestBuildAdapter:
    def test_mock_adapter(self):
        adapter = _build_adapter("mock", None)
        assert isinstance(adapter, MockAdapter)

    def test_unknown_adapter_exits(self):
        with pytest.raises(SystemExit):
            _build_adapter("nonexistent", None)


# ---------------------------------------------------------------------------
# _build_governance_record
# ---------------------------------------------------------------------------

def _make_agent(role: str, response_json: str) -> BaseAgent:
    adapter = MockAdapter(role_responses={role: response_json}, simulate_delay_ms=0)
    return BaseAgent(role=role, goal=f"Act as {role}", adapter=adapter)


CHALLENGER_RESPONSE = json.dumps({
    "challenges": ["Challenge A", "Challenge B", "Challenge C"],
    "severity": "medium",
})

DEFENDER_RESPONSE = json.dumps({
    "defenses": ["Defense A", "Defense B", "Defense C"],
    "confidence": 0.75,
})

JUDGE_RESPONSE = json.dumps({
    "verdict": "proceed_with_caution",
    "score_delta": -3,
    "reasoning": "Challenges are valid but manageable.",
    "confidence": 0.72,
})

ANALYST_RESPONSE = json.dumps({
    "score": 35,
    "summary": "Promising opportunity",
    "dimensions": {"market": 8, "team": 7, "timing": 7, "risk": 6, "upside": 7},
    "confidence": 0.75,
})


class TestBuildGovernanceRecord:
    def test_record_without_debate(self):
        analyst = _make_agent("analyst", ANALYST_RESPONSE)
        critic = _make_agent("critic", CHALLENGER_RESPONSE)
        judge = _make_agent("judge", JUDGE_RESPONSE)
        # Run analyst so it has a trace entry
        analyst.run("test")

        record = _build_governance_record(
            topic="test topic",
            score=25,
            debate_triggered=False,
            result=None,
            assessment=ANALYST_RESPONSE,
            analyst=analyst,
            critic=critic,
            judge=judge,
        )

        assert record["topic"] == "test topic"
        assert record["score"] == 25
        assert record["debate_triggered"] is False
        assert record["challenges_count"] == 0
        assert record["defenses_count"] == 0

    def test_record_with_debate_result(self):
        analyst = _make_agent("analyst", ANALYST_RESPONSE)
        critic = _make_agent("critic", CHALLENGER_RESPONSE)
        judge = _make_agent("judge", JUDGE_RESPONSE)

        # Run agents to create trace entries
        analyst.run("test")
        critic.run("test")
        judge.run("test")

        result = DebateResult(
            verdict="proceed_with_caution",
            score_delta=-3,
            reasoning="Valid concerns",
            challenges=["C1", "C2", "C3"],
            defenses=["D1", "D2", "D3"],
            audit_trail=[
                {"role": "challenger", "content": CHALLENGER_RESPONSE},
                {"role": "defender", "content": DEFENDER_RESPONSE},
                {"role": "judge", "content": JUDGE_RESPONSE},
            ],
        )

        record = _build_governance_record(
            topic="debate topic",
            score=35,
            debate_triggered=True,
            result=result,
            assessment=ANALYST_RESPONSE,
            analyst=analyst,
            critic=critic,
            judge=judge,
        )

        assert record["debate_triggered"] is True
        assert record["challenges_count"] == 3
        assert record["defenses_count"] == 3
        assert record["audit_trail_entries"] == 3
        assert record["debate_rigor"] > 0.0

    def test_record_with_short_audit_trail(self):
        """audit_trail < 3 entries should not crash (bounds check)."""
        analyst = _make_agent("analyst", ANALYST_RESPONSE)
        critic = _make_agent("critic", CHALLENGER_RESPONSE)
        judge = _make_agent("judge", JUDGE_RESPONSE)
        analyst.run("test")

        result = DebateResult(
            verdict="proceed_with_caution",
            score_delta=-1,
            reasoning="Partial",
            challenges=["C1"],
            defenses=["D1"],
            audit_trail=[
                {"role": "challenger", "content": CHALLENGER_RESPONSE},
            ],
        )

        record = _build_governance_record(
            topic="partial debate",
            score=35,
            debate_triggered=True,
            result=result,
            assessment=ANALYST_RESPONSE,
            analyst=analyst,
            critic=critic,
            judge=judge,
        )

        # Should return a valid record without crashing
        assert record["topic"] == "partial debate"
        assert record["debate_rigor"] == 0.0
        assert record["audit_completeness"] == 0.0


# ---------------------------------------------------------------------------
# _load_governance_history / _append_governance_history
# ---------------------------------------------------------------------------

class TestGovernanceHistory:
    def test_load_nonexistent_file(self, tmp_path):
        with patch("constitution.cli.GOVERNANCE_HISTORY_PATH", tmp_path / "missing.json"):
            assert _load_governance_history() == []

    def test_load_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with patch("constitution.cli.GOVERNANCE_HISTORY_PATH", bad_file):
            assert _load_governance_history() == []

    def test_load_non_list_json(self, tmp_path):
        obj_file = tmp_path / "obj.json"
        obj_file.write_text('{"key": "value"}')
        with patch("constitution.cli.GOVERNANCE_HISTORY_PATH", obj_file):
            assert _load_governance_history() == []

    def test_round_trip(self, tmp_path):
        hist_file = tmp_path / "history.json"
        with (
            patch("constitution.cli.GOVERNANCE_HISTORY_PATH", hist_file),
            patch("constitution.cli.WORKSPACE_DIR", tmp_path),
        ):
            _append_governance_history({"topic": "test", "score": 35})
            loaded = _load_governance_history()
            assert len(loaded) == 1
            assert loaded[0]["topic"] == "test"

            _append_governance_history({"topic": "second", "score": 28})
            loaded = _load_governance_history()
            assert len(loaded) == 2


# ---------------------------------------------------------------------------
# Edge cases for _build_adapter
# ---------------------------------------------------------------------------

class TestBuildAdapterEdgeCases:
    def test_mock_ignores_model(self):
        adapter = _build_adapter("mock", "some-model")
        assert isinstance(adapter, MockAdapter)

    def test_case_sensitive_adapter_name(self):
        with pytest.raises(SystemExit):
            _build_adapter("Mock", None)

    def test_empty_string_adapter(self):
        with pytest.raises(SystemExit):
            _build_adapter("", None)


# ---------------------------------------------------------------------------
# Role-specific CLI config
# ---------------------------------------------------------------------------

class TestRoleConfigResolution:
    def test_role_uses_shared_defaults_when_no_override(self):
        parser = build_parser()
        args = parser.parse_args([
            "debate",
            "topic",
            "--adapter", "claude",
            "--model", "sonnet",
        ])

        assert _resolve_role_config(args, "analyst") == ("claude", "sonnet")
        assert _resolve_role_config(args, "critic") == ("claude", "sonnet")
        assert _resolve_role_config(args, "judge") == ("claude", "sonnet")

    def test_role_specific_override_wins_over_shared_default(self):
        parser = build_parser()
        args = parser.parse_args([
            "debate",
            "topic",
            "--adapter", "claude",
            "--model", "sonnet",
            "--critic-model", "opus",
            "--judge-adapter", "anthropic",
            "--judge-model", "claude-opus-4-6",
        ])

        assert _resolve_role_config(args, "analyst") == ("claude", "sonnet")
        assert _resolve_role_config(args, "critic") == ("claude", "opus")
        assert _resolve_role_config(args, "judge") == ("anthropic", "claude-opus-4-6")

    def test_role_specific_adapter_can_be_set_without_shared_override(self):
        parser = build_parser()
        args = parser.parse_args([
            "debate",
            "topic",
            "--critic-adapter", "ollama",
            "--critic-model", "llama3",
        ])

        assert _resolve_role_config(args, "analyst") == ("mock", None)
        assert _resolve_role_config(args, "critic") == ("ollama", "llama3")
        assert _resolve_role_config(args, "judge") == ("mock", None)
