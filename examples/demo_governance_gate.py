#!/usr/bin/env python3
"""
Agent Constitution: Embedded Governance Gate Demo

This demo shows how to auto-trigger debate inside an existing planner or deploy
workflow, even when the upstream agent is not "an Agent Constitution agent".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.base import LLMResponse
from constitution import BaseAgent, Constitution, DecisionPolicy, GovernanceGateHook


class DeploymentPlannerAdapter:
    """Pretend this came from another planning system."""

    def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
        plan = {
            "action": "deploy",
            "environment": "production",
            "decision_type": "release",
            "summary": "Approve the billing-auth hotfix rollout to production before the European morning peak.",
            "confidence": 0.82,
        }
        return LLMResponse(
            content=json.dumps(plan),
            input_tokens=42,
            output_tokens=27,
            cost_usd=0.0,
            duration_ms=5,
        )


def main() -> None:
    rules = Constitution.default()

    critic = BaseAgent(role="critic", goal="Challenge risky decisions", constitution=rules)
    defender = BaseAgent(
        role="defender",
        goal="Defend the upstream planner's proposal against specific challenges",
        constitution=rules,
    )
    judge = BaseAgent(role="judge", goal="Render fair governance verdicts", constitution=rules)

    policy = DecisionPolicy(
        action_types={"deploy"},
        environments={"production"},
        critical_keywords={"auth", "billing"},
        match_mode="any",
    )
    gate = GovernanceGateHook(
        challenger=critic,
        defender=defender,
        judge=judge,
        trigger_policy=policy,
    )
    planner = BaseAgent(
        role="planner",
        goal="Produce operational release recommendations",
        adapter=DeploymentPlannerAdapter(),
        constitution=rules,
        hooks=[gate],
    )

    response = planner.run("Should we approve the billing-auth hotfix rollout to production now?")

    print("Planner output:")
    print(response)
    print()
    print("Trigger reasons:")
    for reason in gate.last_trigger_reasons:
        print(f"- {reason}")
    print()

    if gate.last_result is None:
        print("Debate did not trigger.")
        return

    print("Debate verdict:")
    print(f"- verdict: {gate.last_result.verdict}")
    print(f"- score_delta: {gate.last_result.score_delta}")
    print(f"- reasoning: {gate.last_result.reasoning}")


if __name__ == "__main__":
    main()
