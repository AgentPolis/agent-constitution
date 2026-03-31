"""
Tests for the Debate engine and DebateResult.
All tests use MockAdapter — no real API calls.
"""

import json

import pytest

from adapters import MockAdapter
from constitution import BaseAgent, Debate, DebateResult, DebateValidationError


def _make_agent(role: str, response_json: str) -> BaseAgent:
    """Create a BaseAgent with a MockAdapter returning a fixed JSON response."""
    adapter = MockAdapter(role_responses={role: response_json}, simulate_delay_ms=0)
    return BaseAgent(role=role, goal=f"Act as {role}", adapter=adapter)


# Fixed responses for deterministic tests
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


def _make_debate() -> Debate:
    challenger = _make_agent("challenger", CHALLENGER_RESPONSE)
    defender = _make_agent("defender", DEFENDER_RESPONSE)
    judge = _make_agent("judge", JUDGE_RESPONSE)
    return Debate(challenger=challenger, defender=defender, judge=judge)


class TestDebateShouldTrigger:
    def test_should_trigger_at_threshold(self):
        debate = _make_debate()
        assert debate.should_trigger(32) is True

    def test_should_trigger_above_threshold(self):
        debate = _make_debate()
        assert debate.should_trigger(40) is True

    def test_should_not_trigger_below_threshold(self):
        debate = _make_debate()
        assert debate.should_trigger(31) is False

    def test_should_not_trigger_at_zero(self):
        debate = _make_debate()
        assert debate.should_trigger(0) is False


class TestDebateRun:
    def test_run_returns_debate_result(self):
        debate = _make_debate()
        result = debate.run("Is this a good investment?")
        assert isinstance(result, DebateResult)

    def test_result_has_verdict(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert hasattr(result, "verdict")
        assert result.verdict is not None

    def test_result_has_score_delta(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert hasattr(result, "score_delta")
        assert isinstance(result.score_delta, int)

    def test_result_has_challenges(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert hasattr(result, "challenges")
        assert isinstance(result.challenges, list)

    def test_result_has_defenses(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert hasattr(result, "defenses")
        assert isinstance(result.defenses, list)

    def test_result_has_audit_trail(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert hasattr(result, "audit_trail")
        assert isinstance(result.audit_trail, list)

    def test_audit_trail_has_three_entries(self):
        debate = _make_debate()
        result = debate.run("some topic")
        assert len(result.audit_trail) == 3

    def test_audit_trail_roles(self):
        debate = _make_debate()
        result = debate.run("some topic")
        roles = [entry["role"] for entry in result.audit_trail]
        assert roles == ["challenger", "defender", "judge"]

    def test_score_delta_clamped_max(self):
        # Judge tries to return +10, should be clamped to +5
        judge_response = json.dumps({
            "verdict": "proceed",
            "score_delta": 10,
            "reasoning": "Very strong.",
            "confidence": 0.9,
        })
        challenger = _make_agent("challenger", CHALLENGER_RESPONSE)
        defender = _make_agent("defender", DEFENDER_RESPONSE)
        judge = _make_agent("judge", judge_response)
        debate = Debate(challenger=challenger, defender=defender, judge=judge)
        result = debate.run("some topic")
        assert result.score_delta <= 5

    def test_score_delta_clamped_min(self):
        # Judge tries to return -20, should be clamped to -10
        judge_response = json.dumps({
            "verdict": "reject",
            "score_delta": -20,
            "reasoning": "Very weak.",
            "confidence": 0.9,
        })
        challenger = _make_agent("challenger", CHALLENGER_RESPONSE)
        defender = _make_agent("defender", DEFENDER_RESPONSE)
        judge = _make_agent("judge", judge_response)
        debate = Debate(challenger=challenger, defender=defender, judge=judge)
        result = debate.run("some topic")
        assert result.score_delta >= -10

    def test_verdict_is_valid(self):
        valid_verdicts = {"proceed", "reject", "proceed_with_caution", "reconsider"}
        debate = _make_debate()
        result = debate.run("some topic")
        assert result.verdict in valid_verdicts

    def test_debate_raises_on_invalid_json_by_default(self):
        adapter = MockAdapter(
            role_responses={"judge": "not json at all"},
            simulate_delay_ms=0,
        )
        challenger = _make_agent("challenger", CHALLENGER_RESPONSE)
        defender = _make_agent("defender", DEFENDER_RESPONSE)
        judge = BaseAgent(role="judge", goal="Judge", adapter=adapter)
        debate = Debate(challenger=challenger, defender=defender, judge=judge)
        with pytest.raises(DebateValidationError):
            debate.run("some topic")

    def test_debate_can_opt_into_fallback_mode(self):
        adapter = MockAdapter(
            role_responses={"judge": "not json at all"},
            simulate_delay_ms=0,
        )
        challenger = _make_agent("challenger", CHALLENGER_RESPONSE)
        defender = _make_agent("defender", DEFENDER_RESPONSE)
        judge = BaseAgent(role="judge", goal="Judge", adapter=adapter)
        debate = Debate(
            challenger=challenger,
            defender=defender,
            judge=judge,
            strict_validation=False,
        )
        result = debate.run("some topic")
        assert isinstance(result, DebateResult)
        assert result.verdict == "proceed_with_caution"
        assert result.score_delta == -3
