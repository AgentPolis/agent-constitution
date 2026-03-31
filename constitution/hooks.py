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

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_agent import BaseAgent
    from .debate import DebateResult, DebateValidationError

logger = logging.getLogger(__name__)


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
