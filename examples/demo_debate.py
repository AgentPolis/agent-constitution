#!/usr/bin/env python3
"""
Agent Constitution Demo: Adversarial Debate
Run: python examples/demo_debate.py
No API key required.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from constitution import BaseAgent, Constitution, Debate
from adapters import MockAdapter

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]🏛️ Agent Constitution[/bold blue]\n"
        "[dim]Adversarial Debate Demo — No API key required[/dim]",
        border_style="blue"
    ))

    # 1. Setup
    console.print("\n[bold]Step 1: Initializing agents with Constitutional rules[/bold]")
    rules = Constitution.default()

    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate business opportunities with honest, calibrated assessments",
        persona="Methodical and data-driven. Never overstates confidence.",
        adapter=MockAdapter(),
        constitution=rules,
    )
    critic = BaseAgent(
        role="critic",
        goal="Challenge assumptions and surface blind spots",
        persona="Sharp and contrarian by design. Raises exactly 3 challenges.",
        adapter=MockAdapter(),
        constitution=rules,
    )
    judge = BaseAgent(
        role="judge",
        goal="Evaluate debate arguments impartially and render fair verdicts",
        persona="Measured and impartial. Weights argument quality over role.",
        adapter=MockAdapter(),
        constitution=rules,
    )
    console.print("  ✓ analyst (Nate) — MockAdapter")
    console.print("  ✓ critic (Eve) — MockAdapter")
    console.print("  ✓ judge (Solomon) — MockAdapter")

    # 2. Initial assessment
    console.print("\n[bold]Step 2: Analyst evaluates opportunity[/bold]")
    topic = "Should we build an AI-powered code review tool for enterprise teams?"
    assessment = analyst.run(f"Evaluate this opportunity: {topic}")

    import json
    try:
        data = json.loads(assessment)
        score = data.get("score", 35)
        summary = data.get("summary", assessment[:100])
        confidence = data.get("confidence", 0.75)

        table = Table(title="Assessment Scores", show_header=True)
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", style="green")
        for dim, val in data.get("dimensions", {}).items():
            table.add_row(dim.replace("_", " ").title(), f"{val}/10")
        console.print(table)

        console.print(f"\n  [bold]Total Score:[/bold] [yellow]{score}/40[/yellow]")
        console.print(f"  [bold]Summary:[/bold] {summary}")
        console.print(f"  [bold]Confidence:[/bold] {confidence:.0%}")
    except (json.JSONDecodeError, TypeError):
        score = 35
        console.print(f"  Assessment: {assessment[:200]}")

    # 3. Trigger debate
    console.print(f"\n[bold]Step 3: Score {score} ≥ 32 → Triggering Adversarial Debate[/bold]")
    debate = Debate(challenger=critic, defender=analyst, judge=judge)

    if not debate.should_trigger(score):
        console.print("  [dim]Score below threshold, debate not triggered[/dim]")
        return

    console.print("  [yellow]⚔️  Debate triggered![/yellow]")

    result = debate.run(topic=topic, initial_score=score)

    # 4. Show debate results
    console.print("\n[bold]Step 4: Debate Results[/bold]")

    console.print("\n  [red]Challenges (Eve):[/red]")
    for i, challenge in enumerate(result.challenges, 1):
        console.print(f"    {i}. {challenge}")

    console.print("\n  [green]Defenses (Nate):[/green]")
    for i, defense in enumerate(result.defenses, 1):
        console.print(f"    {i}. {defense}")

    console.print(f"\n  [bold]Verdict (Solomon):[/bold] [magenta]{result.verdict}[/magenta]")
    console.print(f"  [bold]Score Delta:[/bold] {result.score_delta:+d}")
    console.print(f"  [bold]Reasoning:[/bold] {result.reasoning[:200]}")

    final_score = score + result.score_delta
    console.print(f"\n  [bold]Final Score:[/bold] [yellow]{score}[/yellow] → [green]{final_score}[/green]")

    # 5. Audit trail
    console.print(f"\n[bold]Step 5: RunTrace Audit Trail[/bold]")
    console.print(f"  [dim]{len(result.audit_trail)} debate steps recorded[/dim]")
    for entry in result.audit_trail:
        role = entry.get("role", "?")
        content = entry.get("content", "")[:80]
        console.print(f"  [{role}] {content}...")

    console.print(Panel.fit(
        f"[bold green]✓ Demo Complete[/bold green]\n"
        f"Debate verdict: [magenta]{result.verdict}[/magenta] | "
        f"Final score: [yellow]{final_score}/40[/yellow]\n"
        f"[dim]No API key used. Run examples/demo_api.py to use real LLMs.[/dim]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
