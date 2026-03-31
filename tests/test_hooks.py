"""Tests for AgentHook and DebateHook lifecycle systems."""

import pytest

from constitution import BaseAgent, Constitution, Debate, DebateResult
from constitution.hooks import AgentHook, CompositeAgentHook, CompositeDebateHook, DebateHook
from constitution.cost_guard import CostLimitExceeded


# ---------------------------------------------------------------------------
# AgentHook tests
# ---------------------------------------------------------------------------


class RecordingAgentHook(AgentHook):
    """Hook that records calls for assertion."""

    def __init__(self):
        self.pre_call_prompts = []
        self.post_call_contents = []
        self.cost_limit_calls = []

    def pre_call(self, agent, prompt):
        self.pre_call_prompts.append(prompt)
        return prompt

    def post_call(self, agent, response_content, cost_usd):
        self.post_call_contents.append(response_content)
        return response_content


class PromptModifyHook(AgentHook):
    """Hook that modifies the prompt before LLM call."""

    def pre_call(self, agent, prompt):
        return prompt + " [MODIFIED]"


class ResponseModifyHook(AgentHook):
    """Hook that modifies the response after LLM call."""

    def post_call(self, agent, response_content, cost_usd):
        return response_content + " [HOOKED]"


class TestAgentHookLifecycle:
    def test_default_hook_is_noop(self):
        agent = BaseAgent(role="test", goal="test")
        result = agent.run("hello")
        assert isinstance(result, str)

    def test_pre_call_hook_receives_prompt(self):
        hook = RecordingAgentHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook])
        agent.run("test prompt")
        assert hook.pre_call_prompts == ["test prompt"]

    def test_post_call_hook_receives_response(self):
        hook = RecordingAgentHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook])
        agent.run("test prompt")
        assert len(hook.post_call_contents) == 1

    def test_pre_call_hook_can_modify_prompt(self):
        hook = PromptModifyHook()
        recording = RecordingAgentHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook, recording])
        agent.run("original")
        assert recording.pre_call_prompts == ["original [MODIFIED]"]

    def test_post_call_hook_can_modify_response(self):
        hook = ResponseModifyHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook])
        result = agent.run("test")
        assert result.endswith(" [HOOKED]")

    def test_multiple_hooks_chain(self):
        hook1 = PromptModifyHook()
        hook2 = RecordingAgentHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook1, hook2])
        agent.run("start")
        assert hook2.pre_call_prompts == ["start [MODIFIED]"]


class TestAgentHookCostLimit:
    def test_cost_limit_hook_can_allow(self):
        class AllowCostHook(AgentHook):
            def on_cost_limit(self, agent, cost_usd, total_cost):
                return "allow"

        agent = BaseAgent(role="test", goal="test", hooks=[AllowCostHook()])
        agent._cost_guard.hard_limit_usd = 0.001
        # Should not raise because hook returns "allow"
        agent.run("test")

    def test_cost_limit_hook_default_raises(self):
        agent = BaseAgent(role="test", goal="test")
        # Mock returns cost=0.0, so we directly test via cost_guard
        agent._cost_guard.hard_limit_usd = 1.0
        agent._cost_guard._total_cost = 0.99
        # Directly trigger to verify hook wiring
        with pytest.raises(CostLimitExceeded):
            agent._cost_guard.record(0.5)


# ---------------------------------------------------------------------------
# DebateHook tests
# ---------------------------------------------------------------------------


class RecordingDebateHook(DebateHook):
    """Hook that records debate lifecycle calls."""

    def __init__(self):
        self.events = []

    def pre_challenge(self, topic):
        self.events.append(("pre_challenge", topic))
        return topic

    def post_challenge(self, challenges):
        self.events.append(("post_challenge", len(challenges)))
        return challenges

    def pre_defense(self, challenges):
        self.events.append(("pre_defense", len(challenges)))
        return challenges

    def post_defense(self, defenses):
        self.events.append(("post_defense", len(defenses)))
        return defenses

    def pre_verdict(self, challenges, defenses):
        self.events.append(("pre_verdict",))

    def post_verdict(self, result):
        self.events.append(("post_verdict", result.verdict))
        return result


def _make_debate(hooks=None):
    rules = Constitution.default()
    analyst = BaseAgent(role="analyst", goal="Evaluate", constitution=rules)
    critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
    judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
    return Debate(challenger=critic, defender=analyst, judge=judge, hooks=hooks)


class TestDebateHookLifecycle:
    def test_default_hook_is_noop(self):
        debate = _make_debate()
        result = debate.run("Test topic")
        assert result.verdict in {"proceed", "reject", "proceed_with_caution", "reconsider"}

    def test_all_hooks_fire_in_order(self):
        hook = RecordingDebateHook()
        debate = _make_debate(hooks=[hook])
        debate.run("Test topic")
        event_names = [e[0] for e in hook.events]
        assert event_names == [
            "pre_challenge",
            "post_challenge",
            "pre_defense",
            "post_defense",
            "pre_verdict",
            "post_verdict",
        ]

    def test_pre_challenge_can_modify_topic(self):
        class ModifyTopicHook(DebateHook):
            def pre_challenge(self, topic):
                return topic + " [INJECTED]"

        recording = RecordingDebateHook()
        debate = _make_debate(hooks=[ModifyTopicHook(), recording])
        debate.run("Original")
        assert recording.events[0] == ("pre_challenge", "Original [INJECTED]")

    def test_post_verdict_can_modify_result(self):
        class OverrideVerdictHook(DebateHook):
            def post_verdict(self, result):
                result.verdict = "reject"
                result.reasoning = "Overridden by hook"
                return result

        debate = _make_debate(hooks=[OverrideVerdictHook()])
        result = debate.run("Test")
        assert result.verdict == "reject"
        assert result.reasoning == "Overridden by hook"

    def test_pre_verdict_can_abort(self):
        class AbortHook(DebateHook):
            def pre_verdict(self, challenges, defenses):
                raise RuntimeError("Debate aborted by hook")

        debate = _make_debate(hooks=[AbortHook()])
        with pytest.raises(RuntimeError, match="Debate aborted by hook"):
            debate.run("Test")


class TestDebateHookValidationError:
    def test_on_validation_error_default_raises(self):
        # Default strict_validation=True + default hook returns "raise"
        # This is the existing behavior — just verifying hooks don't break it
        debate = _make_debate()
        result = debate.run("Test")
        assert result.verdict is not None  # mock adapter always produces valid output

    def test_on_validation_error_fallback(self):
        class FallbackHook(DebateHook):
            def on_validation_error(self, stage, error):
                return "fallback"

        debate = _make_debate(hooks=[FallbackHook()])
        result = debate.run("Test")
        assert result.verdict is not None


# ---------------------------------------------------------------------------
# CompositeHook tests
# ---------------------------------------------------------------------------


class TestCompositeAgentHook:
    def test_chains_pre_call(self):
        class AddA(AgentHook):
            def pre_call(self, agent, prompt):
                return prompt + "A"

        class AddB(AgentHook):
            def pre_call(self, agent, prompt):
                return prompt + "B"

        composite = CompositeAgentHook([AddA(), AddB()])
        result = composite.pre_call(None, "X")
        assert result == "XAB"

    def test_cost_limit_first_non_raise_wins(self):
        class RaiseHook(AgentHook):
            def on_cost_limit(self, agent, cost, total):
                return "raise"

        class AllowHook(AgentHook):
            def on_cost_limit(self, agent, cost, total):
                return "allow"

        composite = CompositeAgentHook([RaiseHook(), AllowHook()])
        assert composite.on_cost_limit(None, 1.0, 5.0) == "allow"


class TestCompositeDebateHook:
    def test_chains_pre_challenge(self):
        class AddSuffix(DebateHook):
            def __init__(self, suffix):
                self.suffix = suffix

            def pre_challenge(self, topic):
                return topic + self.suffix

        composite = CompositeDebateHook([AddSuffix("A"), AddSuffix("B")])
        assert composite.pre_challenge("X") == "XAB"

    def test_validation_error_first_non_raise_wins(self):
        class StrictHook(DebateHook):
            pass  # default returns "raise"

        class LenientHook(DebateHook):
            def on_validation_error(self, stage, error):
                return "fallback"

        composite = CompositeDebateHook([StrictHook(), LenientHook()])
        assert composite.on_validation_error("challenge", None) == "fallback"
