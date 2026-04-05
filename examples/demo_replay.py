#!/usr/bin/env python3
"""
Replay a recorded live-model Agent Constitution debate without requiring an API key.

Run:
  python examples/demo_replay.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


def load_case() -> dict:
    case_path = Path(__file__).parent / "replay_data" / "billing_auth_claude_live.json"
    return json.loads(case_path.read_text(encoding="utf-8"))


def render_before_after(case: dict) -> None:
    before = case["before"]
    after = case["after"]

    before_lines = [
        f"Recommendation: {before['recommendation']}",
        f"Confidence: {before['confidence']}",
        f"Assessment: {before['assessment']}",
    ]
    after_lines = [
        f"Verdict: {after['verdict']}",
        f"Adjusted score: {after['final_score']}/100 ({after['final_band']})",
        f"Score delta: {after['score_delta']}",
        f"Delta severity: {after['delta_severity']}",
        f"Top concern: {after['top_concern']}",
    ]

    console.print(
        Panel(
            "\n".join(before_lines),
            title="Before Governance",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(
        Panel(
            "\n".join(after_lines),
            title="Recorded Live LLM Result",
            border_style="green",
            padding=(1, 2),
        )
    )


def render_dimensions(case: dict) -> None:
    table = Table(title="Scenario-Aware Dimensions")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", style="green")
    for key, value in case["after"]["dimensions"].items():
        table.add_row(key.replace("_", " ").title(), value)
    console.print(table)


def render_lists(case: dict) -> None:
    after = case["after"]

    console.print("[bold]Critic surfaced:[/bold]")
    for item in after["critic_points"]:
        console.print(f"- {item}")

    console.print("\n[bold]Defender replied:[/bold]")
    for item in after["defender_points"]:
        console.print(f"- {item}")

    console.print("\n[bold]Blockers before rollout:[/bold]")
    for item in after["blockers"]:
        console.print(f"- {item}")

    console.print("\n[bold]Upgrade condition:[/bold]")
    console.print(after["upgrade_condition"])
    console.print("\n[bold]Downgrade condition:[/bold]")
    console.print(after["downgrade_condition"])


def main() -> None:
    case = load_case()
    source = case["source"]

    console.print(
        Panel.fit(
            f"[bold blue]{case['title']}[/bold blue]\n"
            f"[dim]{case['subtitle']}[/dim]\n"
            f"[dim]Source: {source['adapter']} / {source['model']} ({source['mode']})[/dim]",
            border_style="blue",
        )
    )

    console.print("[bold]Prompt[/bold]")
    console.print(case["prompt"])
    console.print("\n[bold]Context files[/bold]")
    for path in case["context_files"]:
        console.print(f"- {path}")
    console.print()

    render_before_after(case)
    console.print()
    render_dimensions(case)
    console.print()
    console.print(f"[bold]Why the score moved[/bold]\n{case['after']['why']}\n")
    render_lists(case)


if __name__ == "__main__":
    main()
