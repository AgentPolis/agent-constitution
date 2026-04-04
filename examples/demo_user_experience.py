#!/usr/bin/env python3
"""
Agent Constitution: User-Facing Governance Rendering Demo

Shows what an end user would see in a chat surface after a governance gate
triggers in silent, summary, and full transcript modes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.base import LLMResponse
from constitution import BaseAgent, Constitution, DecisionPolicy, GovernanceGateHook


class PlannerAdapter:
    def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
        return LLMResponse(
            content='{"action":"deploy","environment":"production","summary":"Approve the billing-auth hotfix rollout now.","confidence":0.82}',
            input_tokens=24,
            output_tokens=14,
            cost_usd=0.0,
            duration_ms=4,
        )


def build_gate(render_mode: str) -> GovernanceGateHook:
    rules = Constitution.default()
    critic = BaseAgent(role="critic", goal="Challenge risky decisions", constitution=rules)
    defender = BaseAgent(
        role="defender",
        goal="Defend the planner's recommendation against concrete challenges",
        constitution=rules,
    )
    judge = BaseAgent(role="judge", goal="Render fair governance verdicts", constitution=rules)
    return GovernanceGateHook(
        challenger=critic,
        defender=defender,
        judge=judge,
        trigger_policy=DecisionPolicy(
            action_types={"deploy"},
            environments={"production"},
            critical_keywords={"billing", "auth"},
            match_mode="any",
        ),
        render_mode=render_mode,
    )


def main() -> None:
    rules = Constitution.default()
    prompt = "Should we approve the billing-auth hotfix rollout to production now?"

    for render_mode in ["silent", "summary", "full_transcript"]:
        gate = build_gate(render_mode)
        planner = BaseAgent(
            role="planner",
            goal="Produce operational release recommendations",
            adapter=PlannerAdapter(),
            constitution=rules,
            hooks=[gate],
        )
        rendered = planner.run(prompt)

        print("=" * 80)
        print(f"Render mode: {render_mode}")
        print("-" * 80)
        print(rendered)
        print()


if __name__ == "__main__":
    main()
