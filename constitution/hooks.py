"""
Lifecycle hooks for agent calls and debates.

Override any method to hook into the governance pipeline.
All hooks are no-ops by default — only implement what you need.

Example:
    class AuditHook(DebateHook):
        def post_verdict(self, result):
            log_to_external(result.audit_trail)
            return result

    debate = Debate(challenger, defender, judge, hooks=[AuditHook()])
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .base_agent import BaseAgent
    from .debate import DebateResult, DebateValidationError

logger = logging.getLogger(__name__)


def _normalize_value(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_tokens(values: set[str] | tuple[str, ...] | list[str] | None) -> set[str]:
    if not values:
        return set()
    return {_normalize_value(value) for value in values}


def _extract_json_object(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _lookup_string(data: dict | None, *keys: str) -> str | None:
    if not data:
        return None
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _humanize_verdict(verdict: str) -> str:
    labels = {
        "proceed": "Proceed",
        "reject": "Reject",
        "proceed_with_caution": "Proceed With Caution",
        "reconsider": "Reconsider",
    }
    return labels.get(verdict, verdict.replace("_", " ").title())


@dataclass(frozen=True)
class TriggerContext:
    """Normalized context that a trigger policy can inspect."""

    prompt: str
    response_content: str
    score: int | None = None
    action_type: str | None = None
    decision_type: str | None = None
    environment: str | None = None
    matched_keywords: tuple[str, ...] = ()
    raw_data: dict | None = None

    @property
    def combined_text(self) -> str:
        return "\n".join(part for part in [self.prompt, self.response_content] if part)

    @classmethod
    def from_inputs(
        cls,
        *,
        prompt: str,
        response_content: str,
        score: int | None,
        keyword_pool: set[str] | None = None,
    ) -> TriggerContext:
        raw_data = _extract_json_object(response_content) or _extract_json_object(prompt)
        combined_text = f"{prompt}\n{response_content}".lower()
        matched_keywords = tuple(
            sorted(
                keyword
                for keyword in (keyword_pool or set())
                if keyword.lower().replace("_", " ") in combined_text
                or keyword.lower() in combined_text
            )
        )
        return cls(
            prompt=prompt,
            response_content=response_content,
            score=score,
            action_type=_lookup_string(raw_data, "action", "action_type", "actionType"),
            decision_type=_lookup_string(
                raw_data,
                "decision_type",
                "decisionType",
                "decision",
                "category",
                "kind",
            ),
            environment=_lookup_string(
                raw_data,
                "environment",
                "env",
                "target_environment",
                "targetEnvironment",
            ),
            matched_keywords=matched_keywords,
            raw_data=raw_data,
        )


@dataclass
class DecisionPolicy:
    """Declarative rules for auto-triggering debate in existing pipelines."""

    min_score: int | None = None
    action_types: set[str] = field(default_factory=set)
    decision_types: set[str] = field(default_factory=set)
    environments: set[str] = field(default_factory=set)
    critical_keywords: set[str] = field(default_factory=set)
    decision_keywords: set[str] = field(default_factory=set)
    match_mode: str = "any"

    def __post_init__(self) -> None:
        self.action_types = _normalize_tokens(self.action_types)
        self.decision_types = _normalize_tokens(self.decision_types)
        self.environments = _normalize_tokens(self.environments)
        self.critical_keywords = _normalize_tokens(self.critical_keywords)
        self.decision_keywords = _normalize_tokens(self.decision_keywords)
        if self.match_mode not in {"any", "all"}:
            raise ValueError("match_mode must be 'any' or 'all'")

    def keyword_pool(self) -> set[str]:
        return set(self.critical_keywords) | set(self.decision_keywords)

    def evaluate(self, context: TriggerContext) -> tuple[bool, list[str]]:
        checks: list[tuple[bool, str]] = []

        if self.min_score is not None:
            checks.append(
                (
                    context.score is not None and context.score >= self.min_score,
                    (
                        f"score {context.score} >= {self.min_score}"
                        if context.score is not None
                        else f"score unavailable for min_score {self.min_score}"
                    ),
                )
            )

        if self.action_types:
            normalized_action = (
                _normalize_value(context.action_type) if context.action_type else None
            )
            checks.append(
                (
                    normalized_action in self.action_types,
                    f"action_type matched: {context.action_type}"
                    if context.action_type
                    else "action_type unavailable",
                )
            )

        if self.decision_types:
            normalized_decision_type = (
                _normalize_value(context.decision_type) if context.decision_type else None
            )
            checks.append(
                (
                    normalized_decision_type in self.decision_types,
                    (
                        f"decision_type matched: {context.decision_type}"
                        if context.decision_type
                        else "decision_type unavailable"
                    ),
                )
            )

        if self.environments:
            normalized_environment = (
                _normalize_value(context.environment) if context.environment else None
            )
            checks.append(
                (
                    normalized_environment in self.environments,
                    (
                        f"environment matched: {context.environment}"
                        if context.environment
                        else "environment unavailable"
                    ),
                )
            )

        if self.critical_keywords:
            critical_matches = sorted(
                keyword for keyword in context.matched_keywords if keyword in self.critical_keywords
            )
            checks.append(
                (
                    bool(critical_matches),
                    (
                        "critical keywords matched: " + ", ".join(critical_matches)
                        if critical_matches
                        else "critical keywords unavailable"
                    ),
                )
            )

        if self.decision_keywords:
            decision_matches = sorted(
                keyword for keyword in context.matched_keywords if keyword in self.decision_keywords
            )
            checks.append(
                (
                    bool(decision_matches),
                    (
                        "decision keywords matched: " + ", ".join(decision_matches)
                        if decision_matches
                        else "decision keywords unavailable"
                    ),
                )
            )

        if not checks:
            return False, []

        matched_reasons = [reason for matched, reason in checks if matched]
        if self.match_mode == "all":
            return all(matched for matched, _ in checks), matched_reasons
        return any(matched for matched, _ in checks), matched_reasons

    @classmethod
    def high_stakes_default(cls) -> DecisionPolicy:
        """Reasonable starter policy for deploy / planning / architecture workflows."""
        return cls(
            min_score=70,
            action_types={"deploy", "launch", "migrate", "rollback", "approve"},
            environments={"production"},
            critical_keywords={"auth", "billing", "security", "customer data", "pricing"},
            decision_keywords={"should we", "recommend", "approve", "reject"},
            match_mode="any",
        )


class AgentHook:
    """Lifecycle hooks for BaseAgent.run() calls."""

    def pre_call(self, agent: BaseAgent, prompt: str) -> str:
        """Called before LLM call. Return modified prompt or raise to abort."""
        return prompt

    def post_call(self, agent: BaseAgent, response_content: str, cost_usd: float) -> str:
        """Called after LLM call and cost recording. Return modified content."""
        return response_content

    def on_cost_limit(self, agent: BaseAgent, cost_usd: float, total_cost: float) -> str:
        """Called when cost would exceed limit. Return 'raise', 'warn', or 'allow'."""
        return "raise"


class GovernanceGateHook(AgentHook):
    """Trigger structured debate after an agent response when a score crosses threshold.

    This is intended for embedding Agent Constitution inside an existing pipeline:

    - developer's agent produces a scored decision
    - hook extracts score from the response
    - if score crosses the threshold, challenger/defender/judge debate runs

    By default, the original response content is returned unchanged so the hook
    is safe to add without silently corrupting JSON output formats. Callers can
    provide a response_formatter or on_debate_complete sink if they want the
    verdict surfaced inline or sent elsewhere.
    """

    def __init__(
        self,
        challenger: BaseAgent,
        judge: BaseAgent,
        *,
        defender: BaseAgent | None = None,
        threshold: int | None = None,
        trigger_policy: DecisionPolicy | None = None,
        render_mode: str = "silent",
        score_extractor: Callable[[str], int | None] | None = None,
        topic_builder: Callable[[BaseAgent, str, int], str] | None = None,
        response_formatter: Callable[[str, DebateResult], str] | None = None,
        on_debate_complete: Callable[[DebateResult], None] | None = None,
        strict_validation: bool = True,
    ):
        self.challenger = challenger
        self.judge = judge
        self.defender = defender
        self.threshold = threshold
        self.trigger_policy = trigger_policy
        if render_mode not in {"silent", "summary", "full_transcript"}:
            raise ValueError("render_mode must be 'silent', 'summary', or 'full_transcript'")
        self.render_mode = render_mode
        self.score_extractor = score_extractor or self._default_score_extractor
        self.topic_builder = topic_builder or self._default_topic_builder
        self.response_formatter = response_formatter
        self.on_debate_complete = on_debate_complete
        self.strict_validation = strict_validation
        self.last_score: int | None = None
        self.last_result: DebateResult | None = None
        self.last_context: TriggerContext | None = None
        self.last_trigger_reasons: list[str] = []
        self._in_gate = False
        self._prompt_stack: list[str] = []

    @staticmethod
    def _default_score_extractor(response_content: str) -> int | None:
        import json

        try:
            data = json.loads(response_content)
        except (json.JSONDecodeError, TypeError):
            return None

        score = data.get("score") if isinstance(data, dict) else None
        return int(score) if isinstance(score, (int, float)) else None

    @staticmethod
    def _default_topic_builder(agent: BaseAgent, response_content: str, score: int) -> str:
        return response_content

    @staticmethod
    def chat_response_formatter(mode: str = "summary") -> Callable[[str, DebateResult], str]:
        """Return a user-facing formatter for chat surfaces."""
        if mode not in {"summary", "full_transcript"}:
            raise ValueError("chat formatter mode must be 'summary' or 'full_transcript'")

        def formatter(response_content: str, result: DebateResult) -> str:
            from .debate import SCORE_MAX, clamp_score, delta_severity, score_band

            data = _extract_json_object(response_content)
            summary = _lookup_string(data, "summary", "recommendation") or response_content
            confidence = data.get("confidence") if isinstance(data, dict) else None
            action = _lookup_string(data, "action", "action_type", "actionType")
            environment = _lookup_string(data, "environment", "env")
            initial_score = data.get("score") if isinstance(data, dict) else None
            adjusted_score = None
            if isinstance(initial_score, (int, float)):
                adjusted_score = clamp_score(int(initial_score) + result.score_delta)

            lines = [f"Recommendation: {summary}"]
            if action:
                lines.append(f"Action: {action}")
            if environment:
                lines.append(f"Environment: {environment}")
            if isinstance(confidence, (int, float)):
                lines.append(f"Confidence: {float(confidence):.0%}")
            if isinstance(initial_score, (int, float)):
                lines.append(
                    f"Assessment: {int(initial_score)}/{SCORE_MAX} ({score_band(int(initial_score)).title()})"
                )
            if adjusted_score is not None:
                lines.append(
                    f"Adjusted score: {adjusted_score}/{SCORE_MAX} ({score_band(adjusted_score).title()})"
                )

            lines.extend(
                [
                    "",
                    "Governance check triggered.",
                    f"Verdict: {_humanize_verdict(result.verdict)}",
                    f"Score delta: {result.score_delta:+d}",
                    f"Delta severity: {delta_severity(result.score_delta).title()}",
                    f"Why: {result.reasoning}",
                ]
            )

            if result.challenges:
                lines.append(f"Top concern: {result.challenges[0]}")
            if result.missing_context:
                lines.extend(["Missing context:", *[f"- {item}" for item in result.missing_context]])
            if result.next_actions:
                lines.extend(["Next step:", *[f"- {action}" for action in result.next_actions]])
            if result.upgrade_condition:
                lines.append(f"Upgrade condition: {result.upgrade_condition}")
            if result.downgrade_condition:
                lines.append(f"Downgrade condition: {result.downgrade_condition}")

            if mode == "full_transcript":
                lines.extend(
                    [
                        "",
                        "Challenges:",
                        *[f"- {challenge}" for challenge in result.challenges],
                        "",
                        "Defenses:",
                        *[f"- {defense}" for defense in result.defenses],
                    ]
                )

            return "\n".join(lines)

        return formatter

    def _governance_summary_payload(self, result: DebateResult) -> dict:
        from .debate import delta_severity

        payload = {
            "triggered": True,
            "trigger_reasons": list(self.last_trigger_reasons),
            "verdict": result.verdict,
            "score_delta": result.score_delta,
            "delta_severity": delta_severity(result.score_delta),
            "reasoning": result.reasoning,
            "missing_context": list(result.missing_context),
            "next_actions": list(result.next_actions),
            "upgrade_condition": result.upgrade_condition,
            "downgrade_condition": result.downgrade_condition,
        }
        if self.last_score is not None:
            payload["initial_score"] = self.last_score
            from .debate import clamp_score, score_band

            adjusted = clamp_score(self.last_score + result.score_delta)
            payload["adjusted_score"] = adjusted
            payload["initial_band"] = score_band(self.last_score)
            payload["adjusted_band"] = score_band(adjusted)
        return payload

    def _format_summary_text(self, response_content: str, result: DebateResult) -> str:
        trigger_reasons = ", ".join(self.last_trigger_reasons) or "policy gate"
        top_challenge = result.challenges[0] if result.challenges else "No challenge captured."
        return (
            f"{response_content}\n\n"
            "[Governance Check]\n"
            f"- verdict: {result.verdict}\n"
            f"- score_delta: {result.score_delta:+d}\n"
            f"- delta_severity: {self._governance_summary_payload(result).get('delta_severity', 'unknown')}\n"
            f"- trigger_reasons: {trigger_reasons}\n"
            f"- top_challenge: {top_challenge}\n"
            f"- missing_context: {' | '.join(result.missing_context)}\n"
            f"- next_actions: {' | '.join(result.next_actions)}\n"
            f"- upgrade_condition: {result.upgrade_condition}\n"
            f"- downgrade_condition: {result.downgrade_condition}\n"
        )

    def _format_full_transcript_text(self, response_content: str, result: DebateResult) -> str:
        trigger_reasons = ", ".join(self.last_trigger_reasons) or "policy gate"
        challenge_lines = "\n".join(
            f"  {idx}. {challenge}" for idx, challenge in enumerate(result.challenges, 1)
        )
        defense_lines = "\n".join(
            f"  {idx}. {defense}" for idx, defense in enumerate(result.defenses, 1)
        )
        return (
            f"{response_content}\n\n"
            "[Governance Check]\n"
            f"trigger_reasons: {trigger_reasons}\n"
            f"verdict: {result.verdict}\n"
            f"score_delta: {result.score_delta:+d}\n"
            f"delta_severity: {self._governance_summary_payload(result).get('delta_severity', 'unknown')}\n"
            f"reasoning: {result.reasoning}\n"
            f"missing_context: {' | '.join(result.missing_context)}\n"
            f"next_actions: {' | '.join(result.next_actions)}\n"
            f"upgrade_condition: {result.upgrade_condition}\n"
            f"downgrade_condition: {result.downgrade_condition}\n"
            "challenges:\n"
            f"{challenge_lines}\n"
            "defenses:\n"
            f"{defense_lines}\n"
        )

    def _render_builtin_response(self, response_content: str, result: DebateResult) -> str:
        if self.render_mode == "silent":
            return response_content

        raw_object = _extract_json_object(response_content)
        if raw_object is not None:
            payload = self._governance_summary_payload(result)
            if self.render_mode == "summary":
                payload["top_challenge"] = result.challenges[0] if result.challenges else None
            else:
                payload["challenges"] = list(result.challenges)
                payload["defenses"] = list(result.defenses)
                payload["audit_trail"] = list(result.audit_trail)
            enriched = dict(raw_object)
            enriched["governance"] = payload
            return json.dumps(enriched, ensure_ascii=False)

        if self.render_mode == "summary":
            return self._format_summary_text(response_content, result)
        return self._format_full_transcript_text(response_content, result)

    def pre_call(self, agent: BaseAgent, prompt: str) -> str:
        self._prompt_stack.append(prompt)
        return prompt

    def post_call(self, agent: BaseAgent, response_content: str, cost_usd: float) -> str:
        from .debate import Debate

        prompt = self._prompt_stack.pop() if self._prompt_stack else ""
        if self._in_gate:
            return response_content

        score = self.score_extractor(response_content)
        self.last_score = score
        self.last_result = None
        debate = Debate(
            challenger=self.challenger,
            defender=self.defender or agent,
            judge=self.judge,
            strict_validation=self.strict_validation,
        )
        threshold = self.threshold if self.threshold is not None else debate.SCORE_THRESHOLD
        context = TriggerContext.from_inputs(
            prompt=prompt,
            response_content=response_content,
            score=score,
            keyword_pool=self.trigger_policy.keyword_pool() if self.trigger_policy else None,
        )
        self.last_context = context
        self.last_trigger_reasons = []

        score_trigger = score is not None and score >= threshold
        if score_trigger:
            self.last_trigger_reasons.append(f"score {score} >= {threshold}")

        policy_trigger = False
        if self.trigger_policy is not None:
            policy_trigger, reasons = self.trigger_policy.evaluate(context)
            self.last_trigger_reasons.extend(reasons)

        if not score_trigger and not policy_trigger:
            return response_content

        topic_score = score if score is not None else threshold
        topic = self.topic_builder(agent, response_content, topic_score)
        self._in_gate = True
        try:
            result = debate.run(topic=topic, initial_score=topic_score)
        finally:
            self._in_gate = False
        self.last_result = result
        if self.on_debate_complete is not None:
            self.on_debate_complete(result)
        if self.response_formatter is not None:
            return self.response_formatter(response_content, result)
        return self._render_builtin_response(response_content, result)


class DebateHook:
    """Lifecycle hooks for the adversarial debate pipeline."""

    def pre_challenge(self, topic: str) -> str:
        """Called before challenger runs. Return modified topic or raise to abort."""
        return topic

    def post_challenge(self, challenges: list[str]) -> list[str]:
        """Called after challenge validation. Can modify, filter, or add challenges."""
        return challenges

    def pre_defense(self, challenges: list[str]) -> list[str]:
        """Called before defender runs. Return modified challenges."""
        return challenges

    def post_defense(self, defenses: list[str]) -> list[str]:
        """Called after defense validation. Can modify defenses."""
        return defenses

    def pre_verdict(self, challenges: list[str], defenses: list[str]) -> None:
        """Called before judge runs. Raise to abort."""
        pass

    def post_verdict(self, result: DebateResult) -> DebateResult:
        """Called after verdict. Can modify or log the final result."""
        return result

    def on_validation_error(self, stage: str, error: DebateValidationError) -> str:
        """Called when LLM output fails schema validation.

        Args:
            stage: 'challenge', 'defense', or 'verdict'
            error: The validation error

        Returns:
            'raise' — re-raise the error (default, strict)
            'fallback' — use fallback values
        """
        return "raise"


class CompositeAgentHook(AgentHook):
    """Chains multiple AgentHooks. Runs in order, each receiving the previous output."""

    def __init__(self, hooks: list[AgentHook]):
        self._hooks = hooks

    def pre_call(self, agent, prompt):
        for hook in self._hooks:
            prompt = hook.pre_call(agent, prompt)
        return prompt

    def post_call(self, agent, response_content, cost_usd):
        for hook in self._hooks:
            response_content = hook.post_call(agent, response_content, cost_usd)
        return response_content

    def on_cost_limit(self, agent, cost_usd, total_cost):
        for hook in self._hooks:
            action = hook.on_cost_limit(agent, cost_usd, total_cost)
            if action != "raise":
                return action
        return "raise"


class CompositeDebateHook(DebateHook):
    """Chains multiple DebateHooks. Runs in order."""

    def __init__(self, hooks: list[DebateHook]):
        self._hooks = hooks

    def pre_challenge(self, topic):
        for hook in self._hooks:
            topic = hook.pre_challenge(topic)
        return topic

    def post_challenge(self, challenges):
        for hook in self._hooks:
            challenges = hook.post_challenge(challenges)
        return challenges

    def pre_defense(self, challenges):
        for hook in self._hooks:
            challenges = hook.pre_defense(challenges)
        return challenges

    def post_defense(self, defenses):
        for hook in self._hooks:
            defenses = hook.post_defense(defenses)
        return defenses

    def pre_verdict(self, challenges, defenses):
        for hook in self._hooks:
            hook.pre_verdict(challenges, defenses)

    def post_verdict(self, result):
        for hook in self._hooks:
            result = hook.post_verdict(result)
        return result

    def on_validation_error(self, stage, error):
        for hook in self._hooks:
            action = hook.on_validation_error(stage, error)
            if action != "raise":
                return action
        return "raise"
