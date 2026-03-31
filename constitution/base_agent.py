from __future__ import annotations

from typing import Optional

from adapters.base import LLMAdapter, LLMResponse
from adapters.mock import MockAdapter

from .constitution import Constitution
from .cost_guard import CostGuard, CostLimitExceeded
from .hooks import AgentHook, CompositeAgentHook
from .trace import RunTrace


class BaseAgent:
    def __init__(
        self,
        role: str,
        goal: str,
        persona: str = "",
        adapter: Optional[LLMAdapter] = None,
        constitution: Optional[Constitution] = None,
        max_iterations: int = 3,
        hooks: Optional[list[AgentHook]] = None,
    ):
        self.role = role
        self.goal = goal
        self.persona = persona
        self.adapter = adapter or MockAdapter()
        self.constitution = constitution or Constitution.default()
        self.max_iterations = max_iterations
        self._trace = RunTrace(agent_role=role)
        self._cost_guard = CostGuard()
        self._hook: AgentHook = CompositeAgentHook(hooks) if hooks else AgentHook()

    def _build_system_prompt(self) -> str:
        """Build system prompt: role + goal + persona + constitution injection."""
        parts = [
            f"You are {self.role}.",
            f"Goal: {self.goal}",
        ]
        if self.persona:
            parts.append(f"Persona: {self.persona}")
        parts.append(self.constitution.as_prompt())
        return "\n\n".join(parts)

    def run(self, prompt: str, tools: Optional[list[dict]] = None) -> str:
        """Execute agent with constitution-injected system prompt."""
        # --- pre_call hook ---
        prompt = self._hook.pre_call(self, prompt)

        system = self._build_system_prompt()
        messages = [{"role": "user", "content": prompt}]

        response: LLMResponse = self.adapter.call(
            messages=messages,
            system_prompt=system,
            tools=tools,
        )

        self._trace.record(
            prompt=prompt,
            response=response.content,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
            cost=response.cost_usd,
        )

        try:
            self._cost_guard.record(response.cost_usd)
        except CostLimitExceeded:
            action = self._hook.on_cost_limit(
                self, response.cost_usd, self._cost_guard.total_cost
            )
            if action == "raise":
                raise
            # "warn" or "allow" — continue without raising

        # --- post_call hook ---
        content = self._hook.post_call(self, response.content, response.cost_usd)

        return content

    def get_trace(self) -> RunTrace:
        return self._trace

    def get_total_cost(self) -> float:
        return self._cost_guard.total_cost
