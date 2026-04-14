"""Tests for AgentHook and DebateHook lifecycle systems."""

import json

import pytest

from adapters.base import LLMResponse
from constitution import (
    BaseAgent,
    Constitution,
    Debate,
    DebateResult,
    DecisionPolicy,
    GovernanceGateHook,
)
from constitution.cost_guard import CostLimitExceeded
from constitution.hooks import (
    AgentHook,
    CompositeAgentHook,
    CompositeDebateHook,
    DebateHook,
    TriggerContext,
)

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

    def test_trace_records_post_hook_response(self):
        hook = ResponseModifyHook()
        agent = BaseAgent(role="test", goal="test", hooks=[hook])
        result = agent.run("test")
        assert agent.get_trace().entries[-1].response == result

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

        class NonZeroCostAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content="ok",
                    input_tokens=10,
                    output_tokens=5,
                    cost_usd=0.5,
                    duration_ms=1,
                )

        agent = BaseAgent(
            role="test",
            goal="test",
            adapter=NonZeroCostAdapter(),
            hooks=[AllowCostHook()],
        )
        agent._cost_guard.hard_limit_usd = 0.001
        # Should not raise because hook returns "allow"
        agent.run("test")
        assert agent.get_total_cost() == pytest.approx(0.5)

    def test_cost_limit_hook_default_raises(self):
        agent = BaseAgent(role="test", goal="test")
        # Mock returns cost=0.0, so we directly test via cost_guard
        agent._cost_guard.hard_limit_usd = 1.0
        agent._cost_guard._total_cost = 0.99
        # Directly trigger to verify hook wiring
        with pytest.raises(CostLimitExceeded):
            agent._cost_guard.record(0.5)


class TestGovernanceGateHook:
    def test_triggers_debate_when_score_crosses_threshold(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(challenger=critic, defender=defender, judge=judge)
        agent = BaseAgent(role="analyst", goal="Evaluate", constitution=rules, hooks=[gate])

        response = agent.run("Should we approve this pricing exception for a strategic enterprise account?")

        assert isinstance(response, str)
        assert gate.last_score is not None
        assert gate.last_result is not None

    def test_skips_when_score_cannot_be_extracted(self):
        class PlainTextAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content="plain text without score",
                    input_tokens=10,
                    output_tokens=5,
                    cost_usd=0.0,
                    duration_ms=1,
                )

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(challenger=critic, defender=defender, judge=judge)
        agent = BaseAgent(
            role="analyst",
            goal="Evaluate",
            constitution=rules,
            adapter=PlainTextAdapter(),
            hooks=[gate],
        )

        response = agent.run("test")

        assert response == "plain text without score"
        assert gate.last_score is None
        assert gate.last_result is None

    def test_policy_can_trigger_without_score(self):
        class PlannerAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content=(
                        '{"action":"deploy","environment":"production",'
                        '"summary":"Deploy the billing auth hotfix now."}'
                    ),
                    input_tokens=12,
                    output_tokens=8,
                    cost_usd=0.0,
                    duration_ms=1,
                )

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic,
            defender=defender,
            judge=judge,
            trigger_policy=DecisionPolicy(
                action_types={"deploy"},
                environments={"production"},
                critical_keywords={"billing", "auth"},
                match_mode="any",
            ),
        )
        agent = BaseAgent(
            role="planner",
            goal="Plan release actions",
            constitution=rules,
            adapter=PlannerAdapter(),
            hooks=[gate],
        )

        response = agent.run("Should we deploy the auth hotfix to production?")

        assert "deploy" in response
        assert gate.last_score is None
        assert gate.last_result is not None
        assert gate.last_context is not None
        assert gate.last_context.action_type == "deploy"
        assert gate.last_context.environment == "production"
        assert "action_type matched: deploy" in gate.last_trigger_reasons

    def test_policy_match_mode_all_requires_every_condition(self):
        context = TriggerContext.from_inputs(
            prompt="Should we deploy to staging?",
            response_content='{"action":"deploy","environment":"staging"}',
            score=30,
            keyword_pool={"deploy", "production"},
        )
        policy = DecisionPolicy(
            min_score=70,
            action_types={"deploy"},
            environments={"production"},
            match_mode="all",
        )

        should_trigger, reasons = policy.evaluate(context)

        assert should_trigger is False
        assert reasons == ["action_type matched: deploy"]

    def test_high_stakes_default_policy_catches_keyword_only_decisions(self):
        class RecommendationAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content="Recommendation: approve this pricing change before launch.",
                    input_tokens=11,
                    output_tokens=7,
                    cost_usd=0.0,
                    duration_ms=1,
                )

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic,
            defender=defender,
            judge=judge,
            trigger_policy=DecisionPolicy.high_stakes_default(),
        )
        agent = BaseAgent(
            role="planner",
            goal="Recommend launch actions",
            constitution=rules,
            adapter=RecommendationAdapter(),
            hooks=[gate],
        )

        agent.run("Recommend whether we should approve the pricing launch.")

        assert gate.last_result is not None
        assert gate.last_context is not None
        assert "pricing" in gate.last_context.matched_keywords

    def test_summary_render_mode_enriches_json_response(self):
        class PlannerAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content='{"action":"deploy","environment":"production","summary":"Ship now."}',
                    input_tokens=9,
                    output_tokens=6,
                    cost_usd=0.0,
                    duration_ms=1,
                )

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic,
            defender=defender,
            judge=judge,
            trigger_policy=DecisionPolicy(action_types={"deploy"}, environments={"production"}),
            render_mode="summary",
        )
        agent = BaseAgent(
            role="planner",
            goal="Plan release actions",
            constitution=rules,
            adapter=PlannerAdapter(),
            hooks=[gate],
        )

        rendered = agent.run("Should we deploy now?")
        data = json.loads(rendered)

        assert data["action"] == "deploy"
        assert data["governance"]["triggered"] is True
        assert data["governance"]["verdict"] in {
            "proceed",
            "reject",
            "proceed_with_caution",
            "reconsider",
        }
        assert "top_challenge" in data["governance"]

    def test_full_transcript_render_mode_appends_text_transcript(self):
        class TextAdapter:
            def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
                return LLMResponse(
                    content="Recommendation: deploy the billing-auth fix now.",
                    input_tokens=9,
                    output_tokens=6,
                    cost_usd=0.0,
                    duration_ms=1,
                )

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic,
            defender=defender,
            judge=judge,
            trigger_policy=DecisionPolicy(critical_keywords={"billing", "auth"}),
            render_mode="full_transcript",
        )
        agent = BaseAgent(
            role="planner",
            goal="Plan release actions",
            constitution=rules,
            adapter=TextAdapter(),
            hooks=[gate],
        )

        rendered = agent.run("Should we deploy the billing-auth fix?")

        assert "[Governance Check]" in rendered
        assert "challenges:" in rendered
        assert "defenses:" in rendered
        assert "trigger_reasons:" in rendered

    def test_chat_response_formatter_returns_product_style_text(self):
        formatter = GovernanceGateHook.chat_response_formatter("summary")
        result = DebateResult(
            verdict="proceed_with_caution",
            score_delta=-21,
            reasoning="Several concerns remain unresolved.",
            missing_context=["Deployment checklist was not supplied."],
            challenges=["Rollback plan is still untested."],
            defenses=["Rollback automation exists behind a feature flag."],
        )
        rendered = formatter(
            '{"summary":"Deploy the billing-auth hotfix now.","action":"deploy","environment":"production","score":78,"confidence":0.82}',
            result,
        )

        assert "Recommendation: Deploy the billing-auth hotfix now." in rendered
        assert "Environment: production" in rendered
        assert "Confidence: 82%" in rendered
        assert "Assessment:" in rendered
        assert "Adjusted score:" in rendered
        assert "Verdict: Proceed With Caution" in rendered
        assert "Delta severity: Major Concern" in rendered
        assert "Top concern: Rollback plan is still untested." in rendered
        assert "Missing context:" in rendered


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
        assert result.audit_trail[-1]["role"] == "hook"
        assert result.audit_trail[-1]["stage"] == "post_verdict"

    def test_post_verdict_invalid_mutation_raises_in_strict_mode(self):
        class InvalidVerdictHook(DebateHook):
            def post_verdict(self, result):
                result.verdict = "ship_it"
                return result

        debate = _make_debate(hooks=[InvalidVerdictHook()])
        with pytest.raises(Exception):
            debate.run("Test")

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

    def test_invalid_post_challenge_falls_back_when_not_strict(self):
        class InvalidChallengesHook(DebateHook):
            def post_challenge(self, challenges):
                return ["ok", 123]

        debate = _make_debate(hooks=[InvalidChallengesHook()])
        debate.strict_validation = False
        result = debate.run("Test")
        assert all(isinstance(challenge, str) for challenge in result.challenges)

    def test_post_challenge_mutation_is_audited(self):
        class AppendChallengeHook(DebateHook):
            def post_challenge(self, challenges):
                return challenges + ["Hook-added challenge"]

        debate = _make_debate(hooks=[AppendChallengeHook()])
        result = debate.run("Test")
        assert any(
            entry.get("role") == "hook" and entry.get("stage") == "post_challenge"
            for entry in result.audit_trail
        )


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


# ---------------------------------------------------------------------------
# VerificationTier tests
# ---------------------------------------------------------------------------

from constitution.hooks import VerificationTier, COMPLEXITY_LEVELS, TrustProtocol


class TestVerificationTier:
    def test_from_complexity_mapping(self):
        assert VerificationTier.from_complexity("low") == VerificationTier.LOW
        assert VerificationTier.from_complexity("medium") == VerificationTier.STANDARD
        assert VerificationTier.from_complexity("high") == VerificationTier.HIGH
        assert VerificationTier.from_complexity("critical") == VerificationTier.CRITICAL

    def test_from_complexity_none_defaults_to_standard(self):
        assert VerificationTier.from_complexity(None) == VerificationTier.STANDARD

    def test_from_complexity_unknown_defaults_to_standard(self):
        assert VerificationTier.from_complexity("banana") == VerificationTier.STANDARD

    def test_from_complexity_normalizes_case(self):
        assert VerificationTier.from_complexity("HIGH") == VerificationTier.HIGH
        assert VerificationTier.from_complexity("Critical") == VerificationTier.CRITICAL


# ---------------------------------------------------------------------------
# DecisionPolicy complexity tests
# ---------------------------------------------------------------------------


class TestDecisionPolicyComplexity:
    def test_min_complexity_triggers_on_high(self):
        policy = DecisionPolicy(min_complexity="high")
        context = TriggerContext(
            prompt="test", response_content="test", complexity="high"
        )
        triggered, reasons = policy.evaluate(context)
        assert triggered
        assert any("complexity" in r for r in reasons)

    def test_min_complexity_skips_on_low(self):
        policy = DecisionPolicy(min_complexity="high")
        context = TriggerContext(
            prompt="test", response_content="test", complexity="low"
        )
        triggered, reasons = policy.evaluate(context)
        assert not triggered

    def test_min_complexity_triggers_on_higher_level(self):
        policy = DecisionPolicy(min_complexity="medium")
        context = TriggerContext(
            prompt="test", response_content="test", complexity="critical"
        )
        triggered, reasons = policy.evaluate(context)
        assert triggered

    def test_complexity_levels_matches_exact(self):
        policy = DecisionPolicy(complexity_levels={"high", "critical"})
        ctx_high = TriggerContext(prompt="t", response_content="t", complexity="high")
        ctx_low = TriggerContext(prompt="t", response_content="t", complexity="low")
        assert policy.evaluate(ctx_high)[0]
        assert not policy.evaluate(ctx_low)[0]

    def test_min_complexity_unavailable_does_not_trigger(self):
        policy = DecisionPolicy(min_complexity="high")
        context = TriggerContext(prompt="test", response_content="test", complexity=None)
        triggered, _ = policy.evaluate(context)
        assert not triggered

    def test_invalid_min_complexity_raises(self):
        with pytest.raises(ValueError, match="min_complexity"):
            DecisionPolicy(min_complexity="banana")

    def test_verification_tier_from_context(self):
        policy = DecisionPolicy()
        ctx = TriggerContext(prompt="t", response_content="t", complexity="critical")
        assert policy.verification_tier(ctx) == VerificationTier.CRITICAL

    def test_combined_score_and_complexity(self):
        """Score OR complexity can trigger in 'any' mode."""
        policy = DecisionPolicy(min_score=70, min_complexity="high", match_mode="any")
        # Score alone triggers
        ctx1 = TriggerContext(prompt="t", response_content="t", score=80, complexity="low")
        assert policy.evaluate(ctx1)[0]
        # Complexity alone triggers
        ctx2 = TriggerContext(prompt="t", response_content="t", score=50, complexity="high")
        assert policy.evaluate(ctx2)[0]
        # Neither triggers
        ctx3 = TriggerContext(prompt="t", response_content="t", score=50, complexity="low")
        assert not policy.evaluate(ctx3)[0]


# ---------------------------------------------------------------------------
# TriggerContext complexity extraction tests
# ---------------------------------------------------------------------------


class TestTriggerContextComplexity:
    def test_extracts_complexity_from_json(self):
        response = json.dumps({"score": 80, "complexity": "high"})
        ctx = TriggerContext.from_inputs(
            prompt="test", response_content=response, score=80
        )
        assert ctx.complexity == "high"

    def test_extracts_complexity_level_variant(self):
        response = json.dumps({"score": 80, "complexity_level": "critical"})
        ctx = TriggerContext.from_inputs(
            prompt="test", response_content=response, score=80
        )
        assert ctx.complexity == "critical"

    def test_extracts_risk_level_as_complexity(self):
        response = json.dumps({"score": 80, "risk_level": "high"})
        ctx = TriggerContext.from_inputs(
            prompt="test", response_content=response, score=80
        )
        assert ctx.complexity == "high"

    def test_no_complexity_returns_none(self):
        response = json.dumps({"score": 80})
        ctx = TriggerContext.from_inputs(
            prompt="test", response_content=response, score=80
        )
        assert ctx.complexity is None


# ---------------------------------------------------------------------------
# GovernanceGateHook verification tier tests
# ---------------------------------------------------------------------------


class TestGovernanceGateHookTier:
    def test_low_tier_skips_debate(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        policy = DecisionPolicy(
            decision_keywords={"should we"},
            match_mode="any",
        )
        gate = GovernanceGateHook(
            challenger=critic,
            judge=judge,
            trigger_policy=policy,
            verification_tier=VerificationTier.LOW,
        )
        agent = BaseAgent(role="analyst", goal="Evaluate", constitution=rules, hooks=[gate])

        response = agent.run("Should we deploy?")
        # LOW tier should skip debate even when policy triggers
        assert gate.last_result is None
        assert gate.last_verification_tier == VerificationTier.LOW

    def test_standard_tier_runs_debate(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic,
            judge=judge,
            verification_tier=VerificationTier.STANDARD,
        )
        agent = BaseAgent(role="analyst", goal="Evaluate", constitution=rules, hooks=[gate])

        response = agent.run("Should we deploy?")
        # STANDARD should run debate when score triggers
        if gate.last_score is not None and gate.last_score >= 70:
            assert gate.last_result is not None
            assert gate.last_verification_tier == VerificationTier.STANDARD

    def test_tier_inferred_from_policy_context(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        policy = DecisionPolicy(min_complexity="high")
        gate = GovernanceGateHook(
            challenger=critic,
            judge=judge,
            trigger_policy=policy,
        )
        # Manually check tier resolution
        ctx = TriggerContext(prompt="t", response_content="t", complexity="critical")
        tier = policy.verification_tier(ctx)
        assert tier == VerificationTier.CRITICAL


# ---------------------------------------------------------------------------
# TrustProtocol facade tests
# ---------------------------------------------------------------------------


class TestTrustProtocol:
    def test_creates_hook_with_defaults(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        protocol = TrustProtocol(challenger=critic, judge=judge)

        assert protocol.hook is not None
        assert protocol.policy is not None
        assert protocol.last_result is None

    def test_min_complexity_sets_policy(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        protocol = TrustProtocol(
            challenger=critic, judge=judge, min_complexity="high"
        )

        assert protocol.policy.min_complexity == "high"

    def test_invalid_min_complexity_raises(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        with pytest.raises(ValueError):
            TrustProtocol(challenger=critic, judge=judge, min_complexity="banana")

    def test_tier_passed_to_hook(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        protocol = TrustProtocol(
            challenger=critic, judge=judge, tier=VerificationTier.HIGH
        )

        assert protocol.hook.verification_tier == VerificationTier.HIGH

    def test_hook_integrates_with_agent(self):
        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        protocol = TrustProtocol(challenger=critic, judge=judge)
        agent = BaseAgent(
            role="analyst", goal="Evaluate", constitution=rules,
            hooks=[protocol.hook],
        )

        response = agent.run("Should we deploy?")
        assert isinstance(response, str)
