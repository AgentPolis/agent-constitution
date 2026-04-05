#!/usr/bin/env python3
"""
Agent Constitution: Interactive Debate Experience

The user proposes a decision. Agents evaluate, challenge, and judge — live.

Usage:
  ANTHROPIC_API_KEY=sk-ant-... python examples/demo_interactive.py
  python examples/demo_interactive.py --mock    # no API key, uses MockAdapter
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from constitution import BaseAgent, Constitution, Debate
from constitution.debate import DebateResult, SCORE_MAX, clamp_score, delta_severity, score_band
from constitution.hooks import DebateHook
from constitution.retrospective import Retrospective
from constitution.scenarios import build_analyst_prompt

console = Console()

# ---------------------------------------------------------------------------
# Live Debate Hook — shows each stage as it happens
# ---------------------------------------------------------------------------

class LiveDebateHook(DebateHook):
    """Print each debate stage live so the user sees the process unfold."""

    def pre_challenge(self, topic: str) -> str:
        console.print("\n  [bold yellow]▶ Challenger is analyzing weak points...[/bold yellow]")
        return topic

    def post_challenge(self, challenges: list[str]) -> list[str]:
        console.print(Panel(
            "\n".join(f"[red]{i}.[/red] {c}" for i, c in enumerate(challenges, 1)),
            title="[bold red]Challenger Critique[/bold red]",
            border_style="red",
            padding=(1, 2),
        ))
        return challenges

    def pre_defense(self, challenges: list[str]) -> list[str]:
        console.print("  [bold yellow]▶ Defender is preparing rebuttals...[/bold yellow]")
        return challenges

    def post_defense(self, defenses: list[str]) -> list[str]:
        console.print(Panel(
            "\n".join(f"[green]{i}.[/green] {d}" for i, d in enumerate(defenses, 1)),
            title="[bold green]Defender Rebuttal[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
        return defenses

    def pre_verdict(self, challenges, defenses):
        console.print("  [bold yellow]▶ Judge is weighing both sides...[/bold yellow]")

    def post_verdict(self, result: DebateResult) -> DebateResult:
        verdict_colors = {
            "proceed": "bold green",
            "reject": "bold red",
            "proceed_with_caution": "bold yellow",
            "reconsider": "bold magenta",
        }
        verdict_labels = {
            "proceed": "Proceed - evidence supports execution",
            "reject": "Reject - do not proceed",
            "proceed_with_caution": "Proceed with caution - risks remain",
            "reconsider": "Reconsider - needs another pass",
        }
        color = verdict_colors.get(result.verdict, "bold white")
        label = verdict_labels.get(result.verdict, result.verdict)

        console.print(Panel(
            f"[{color}]{label}[/{color}]\n\n"
            f"[bold]Score delta:[/bold] {result.score_delta:+d}\n\n"
            f"[bold]Delta severity:[/bold] {delta_severity(result.score_delta).title()}\n\n"
            f"[bold]Reasoning:[/bold]\n{result.reasoning}\n\n"
            f"[bold]Next actions:[/bold]\n- " + "\n- ".join(result.next_actions) + "\n\n"
            f"[bold]Upgrade condition:[/bold]\n{result.upgrade_condition}\n\n"
            f"[bold]Downgrade condition:[/bold]\n{result.downgrade_condition}",
            title="[bold magenta]Judge Verdict[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        ))
        return result


# ---------------------------------------------------------------------------
# Presets — common decision scenarios users can pick
# ---------------------------------------------------------------------------

PRESETS = {
    "1": {
        "name": "Pricing decision",
        "topic": "Should we launch usage-based pricing for enterprise API customers this quarter?",
    },
    "2": {
        "name": "Market expansion",
        "topic": "Should we expand from mid-market to enterprise before hiring a dedicated solutions engineering team?",
    },
    "3": {
        "name": "Platform decision",
        "topic": "Should we consolidate three internal tools into a single customer workflow platform this half?",
    },
    "4": {
        "name": "Organization design",
        "topic": "Should we reorganize product and engineering into vertical pods before the Q4 launch?",
    },
    "5": {
        "name": "Financing decision",
        "topic": "Should we raise a Series A now or extend runway six months and target stronger net revenue retention first?",
    },
}


def pick_topic() -> str:
    """Let user pick a preset or type their own."""
    console.print("\n[bold]Pick a scenario, or enter your own:[/bold]\n")
    for key, preset in PRESETS.items():
        console.print(f"  [cyan]{key}[/cyan]. {preset['name']}")
        console.print(f"     [dim]{preset['topic'][:70]}...[/dim]")
    console.print("  [cyan]6[/cyan]. Enter my own topic\n")

    choice = console.input("[bold]Choose (1-6): [/bold]").strip()
    if choice in PRESETS:
        topic = PRESETS[choice]["topic"]
        console.print(f"\n  [dim]→ {topic}[/dim]")
        return topic
    else:
        topic = console.input("\n[bold]Enter your decision question:[/bold] ").strip()
        if not topic:
            topic = PRESETS["1"]["topic"]
            console.print(f"  [dim]→ Using default: {topic}[/dim]")
        return topic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Use MockAdapter (no API key)")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold blue]Agent Constitution - Interactive Debate Experience[/bold blue]\n"
        "[dim]High-stakes decisions get challenged before they become commitments.[/dim]",
        border_style="blue",
    ))

    # Adapter selection
    use_mock = args.mock
    if not use_mock:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[yellow]ANTHROPIC_API_KEY not found. Falling back to MockAdapter.[/yellow]")
            use_mock = True

    if use_mock:
        from adapters import MockAdapter
        adapter = MockAdapter()
        console.print("[dim]Mode: MockAdapter (canned responses, full flow demo)[/dim]")
    else:
        from adapters import AnthropicAPIAdapter
        adapter = AnthropicAPIAdapter(model="claude-haiku-4-5-20251001", api_key=api_key)
        console.print("[dim]Mode: Anthropic API (claude-haiku-4-5, live LLM debate)[/dim]")

    # Pick topic
    topic = pick_topic()

    # Setup agents
    console.print("\n[bold cyan]Building the agent team[/bold cyan]")
    rules = Constitution.default()

    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate decisions with honest, calibrated assessments. Return JSON with a 0-100 score, 5 scenario-aware dimensions scored 0-20 each, summary, confidence (0-1), and scenario.",
        persona="Methodical and data-driven. Never overstates confidence. Tags uncertainty with [SPECULATION].",
        adapter=adapter,
        constitution=rules,
    )
    critic = BaseAgent(
        role="critic",
        goal="Challenge assumptions and surface blind spots in the proposed decision",
        persona="Sharp and contrarian by design. Finds the holes others miss. Raises exactly 3 challenges.",
        adapter=adapter,
        constitution=rules,
    )
    judge = BaseAgent(
        role="judge",
        goal="Evaluate debate arguments impartially and render a fair verdict",
        persona="Measured and impartial. Weights argument quality over role. Explains reasoning clearly.",
        adapter=adapter,
        constitution=rules,
    )

    console.print("  [cyan]analyst[/cyan] - frames the case for the decision")
    console.print("  [red]critic[/red]  - tests assumptions and surfaces downside risk")
    console.print("  [magenta]judge[/magenta]   - renders an impartial recommendation")

    # Step 1: Assessment
    console.print("\n[bold cyan]Step 1: Analyst is evaluating...[/bold cyan]")
    assessment = analyst.run(build_analyst_prompt(topic))

    try:
        data = json.loads(assessment)
        score = data.get("score", 78)
        summary = data.get("summary", assessment[:200])
        confidence = data.get("confidence", 0.75)
        dimensions = data.get("dimensions", {})

        table = Table(title="Analyst Assessment", box=box.ROUNDED)
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", style="green", justify="center")
        table.add_column("", style="dim")
        for dim, val in dimensions.items():
            filled = max(0, min(10, int(round(val / 2))))
            bar = "█" * filled + "░" * (10 - filled)
            table.add_row(dim.replace("_", " ").title(), f"{val}/20", bar)
        console.print(table)
        console.print(
            f"\n  [bold]Total score:[/bold] [yellow]{score}/{SCORE_MAX}[/yellow] "
            f"({score_band(score).title()})  [bold]Confidence:[/bold] {confidence:.0%}"
        )
        console.print(f"  [bold]Summary:[/bold] {summary}")
    except (json.JSONDecodeError, TypeError):
        score = 78
        console.print(f"  [dim]{assessment[:300]}[/dim]")

    # Step 2: Trigger decision
    threshold = Debate.SCORE_THRESHOLD
    console.print("\n[bold cyan]Step 2: Should debate trigger?[/bold cyan]")
    console.print(f"  Score {score} {'≥' if score >= threshold else '<'} {threshold} (threshold)")

    if score < threshold:
        console.print("  [green]Low risk. No debate needed. Proceeding directly.[/green]")
        return

    console.print("  [yellow]High score = material decision worth pressure-testing -> triggering adversarial debate[/yellow]")
    console.print("  [dim](This is the core idea: major decisions get challenged automatically.)[/dim]")

    # Step 3: Debate
    console.print("\n[bold cyan]Step 3: Debate begins[/bold cyan]")

    debate = Debate(
        challenger=critic,
        defender=analyst,
        judge=judge,
        hooks=[LiveDebateHook()],
    )
    result = debate.run(topic=topic, initial_score=score)
    final_score = clamp_score(score + result.score_delta)

    # Step 4: Record to retrospective
    retro = Retrospective()
    pred = retro.record_prediction(
        agent_role="analyst",
        claim=f"Decision '{topic[:50]}...' scored {score}/{SCORE_MAX}",
        confidence=confidence if 'confidence' in dir() else 0.75,
    )

    # Step 5: Summary
    console.print("\n[bold cyan]Results[/bold cyan]")

    summary_table = Table(box=box.ROUNDED, show_header=False)
    summary_table.add_column("", style="bold", width=12)
    summary_table.add_column("")
    summary_table.add_row("Decision", topic[:80])
    summary_table.add_row("Initial score", f"{score}/{SCORE_MAX}")
    summary_table.add_row("Debate delta", f"{result.score_delta:+d}")
    summary_table.add_row("Final score", f"[bold]{final_score}/{SCORE_MAX}[/bold]")
    summary_table.add_row("Verdict", result.verdict)
    summary_table.add_row("Prediction ID", pred.id[:8] + "...")
    console.print(summary_table)

    if not use_mock:
        total_cost = analyst.get_total_cost() + critic.get_total_cost() + judge.get_total_cost()
        console.print(f"\n  [dim]API cost: ${total_cost:.4f} (4 calls x haiku)[/dim]")

    console.print(Panel.fit(
        "[bold]Why this matters[/bold]\n\n"
        "Without Agent Constitution: a recommendation can move forward with little structured challenge.\n"
        "With Agent Constitution: high-stakes decisions get challenged, defended, and judged before they become commitments.\n"
        "The whole process leaves an audit trail, so teams can revisit why the decision was made.",
        border_style="blue",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
