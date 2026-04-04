#!/usr/bin/env python3
"""
Agent Constitution Demo: Adversarial Debate
Run: python examples/demo_debate.py           # interactive prompt
     python examples/demo_debate.py --auto    # default topic, no prompt
     python examples/demo_debate.py --topic "Should we build X?"
No API key required.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapters import MockAdapter
from constitution import BaseAgent, Constitution, Debate

console = Console()

DEFAULT_TOPIC = "Should we expand from mid-market to enterprise this year?"

def main():
    parser = argparse.ArgumentParser(description="Agent Constitution Debate Demo")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Use default topic without prompting",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Debate topic to evaluate without interactive prompting",
    )
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold blue]Agent Constitution[/bold blue]\n"
        "[dim]Adversarial Debate Demo -- No API key required[/dim]",
        border_style="blue"
    ))

    # Determine topic
    if args.topic:
        topic = args.topic.strip()
    elif args.auto:
        topic = DEFAULT_TOPIC
    else:
        topic = console.input("\n[bold]What topic should we debate?[/bold] ").strip()
        if not topic:
            topic = DEFAULT_TOPIC
            console.print("[dim]No input -- using default topic.[/dim]")

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
    console.print("  analyst -- MockAdapter")
    console.print("  critic -- MockAdapter")
    console.print("  judge -- MockAdapter")

    # 2. Initial assessment
    console.print("\n[bold]Step 2: Analyst evaluates the decision[/bold]")
    console.print(f"  [dim]Topic: {topic}[/dim]")
    assessment = analyst.run(f"Evaluate this opportunity: {topic}")

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

    debate = Debate(challenger=critic, defender=analyst, judge=judge)
    threshold = debate.SCORE_THRESHOLD

    # 3. Trigger debate
    console.print(
        f"\n[bold]Step 3: Debate trigger check[/bold]\n"
        f"  [dim]Rule: trigger structured debate only if score ≥ {threshold}/40[/dim]"
    )

    if not debate.should_trigger(score):
        console.print(f"  [dim]Score {score} < {threshold} — debate not triggered[/dim]")
        return

    console.print(f"  [yellow]⚔️  Score {score} ≥ {threshold} — debate triggered![/yellow]")

    result = debate.run(topic=topic, initial_score=score)

    # 4. Show debate results
    console.print("\n[bold]Step 4: Debate Results[/bold]")

    console.print("\n  [red]Challenges:[/red]")
    for i, challenge in enumerate(result.challenges, 1):
        console.print(f"    {i}. {challenge}")

    console.print("\n  [green]Defenses:[/green]")
    for i, defense in enumerate(result.defenses, 1):
        console.print(f"    {i}. {defense}")

    console.print(f"\n  [bold]Verdict:[/bold] [magenta]{result.verdict}[/magenta]")
    console.print(f"  [bold]Score Delta:[/bold] {result.score_delta:+d}")
    console.print(f"  [bold]Reasoning:[/bold] {result.reasoning[:200]}")

    final_score = score + result.score_delta
    console.print(f"\n  [bold]Final Score:[/bold] [yellow]{score}[/yellow] → [green]{final_score}[/green]")

    # 5. Audit trail
    console.print("\n[bold]Step 5: Debate Audit Trail[/bold]")
    console.print(
        "  [dim]Core debate uses 3 role steps (challenger, defender, judge). "
        "Extra hook audit events appear only when hooks mutate the pipeline.[/dim]"
    )
    console.print(f"  [dim]{len(result.audit_trail)} audit entries recorded[/dim]")
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
