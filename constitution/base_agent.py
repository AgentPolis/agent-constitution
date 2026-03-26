from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters import LLMAdapter, LLMResponse, MockAdapter
from .constitution import Constitution
from .trace import RunTrace
from .cost_guard import CostGuard


class BaseAgent:
    def __init__(
        self,
        role: str,
        goal: str,
        persona: str = "",
        adapter: Optional[LLMAdapter] = None,
        constitution: Optional[Constitution] = None,
        max_iterations: int = 3,
    ):
        self.role = role
        self.goal = goal
        self.persona = persona
        self.adapter = adapter or MockAdapter()
        self.constitution = constitution or Constitution.default()
        self.max_iterations = max_iterations
        self._trace = RunTrace(agent_role=role)
        self._cost_guard = CostGuard()

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

    def run(self, prompt: str, tools: list[dict] = None) -> str:
        """Execute agent with constitution-injected system prompt."""
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
        self._cost_guard.record(response.cost_usd)

        return response.content

    def get_trace(self) -> RunTrace:
        return self._trace

    def get_total_cost(self) -> float:
        return self._cost_guard.total_cost
