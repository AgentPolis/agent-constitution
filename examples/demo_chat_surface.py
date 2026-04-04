#!/usr/bin/env python3
"""
Agent Constitution: Chat Surface Before/After Demo

Shows what a user would see in a chat product before governance, with a compact
summary gate, and with a full transcript gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from adapters.base import LLMResponse
from constitution import BaseAgent, Constitution, DecisionPolicy, GovernanceGateHook

console = Console()


class PlannerAdapter:
    def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
        return LLMResponse(
            content=json.dumps(
                {
                    "action": "deploy",
                    "environment": "production",
                    "summary": "Approve the billing-auth hotfix rollout now.",
                    "confidence": 0.82,
                }
            ),
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
    response_formatter = (
        None
        if render_mode == "silent"
        else GovernanceGateHook.chat_response_formatter(
            "summary" if render_mode == "summary" else "full_transcript"
        )
    )
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
        response_formatter=response_formatter,
    )


def render_chat(turn_title: str, prompt: str, reply: str) -> None:
    console.print(
        Panel(
            prompt,
            title=f"{turn_title} · User",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(
        Panel(
            Syntax(reply, "json", word_wrap=True) if reply.strip().startswith("{") else reply,
            title=f"{turn_title} · Assistant",
            border_style="green",
            padding=(1, 2),
        )
    )


def main() -> None:
    rules = Constitution.default()
    prompt = "Should we approve the billing-auth hotfix rollout to production now?"

    plain_planner = BaseAgent(
        role="planner",
        goal="Produce operational release recommendations",
        adapter=PlannerAdapter(),
        constitution=rules,
    )
    plain_reply = plain_planner.run(prompt)
    render_chat("Before Governance", prompt, plain_reply)

    for label, render_mode in [
        ("With Summary Gate", "summary"),
        ("With Full Transcript Gate", "full_transcript"),
    ]:
        gate = build_gate(render_mode)
        planner = BaseAgent(
            role="planner",
            goal="Produce operational release recommendations",
            adapter=PlannerAdapter(),
            constitution=rules,
            hooks=[gate],
        )
        reply = planner.run(prompt)
        render_chat(label, prompt, reply)


if __name__ == "__main__":
    main()
