#!/usr/bin/env python3
"""
Agent Constitution Demo: Real LLM via Anthropic API
Run: ANTHROPIC_API_KEY=sk-ant-... python examples/demo_api.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Check API key first
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: ANTHROPIC_API_KEY environment variable not set.")
    print("Usage: ANTHROPIC_API_KEY=sk-ant-... python examples/demo_api.py")
    print("\nTo run without an API key: python examples/demo_debate.py")
    sys.exit(1)

from rich.console import Console
from rich.panel import Panel

from adapters import AnthropicAPIAdapter
from constitution import BaseAgent, Constitution, Debate, DebateValidationError

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]🏛️ Agent Constitution[/bold blue]\n"
        "[dim]Adversarial Debate Demo — Real LLM (Anthropic API)[/dim]",
        border_style="blue"
    ))

    console.print("\n[bold]Initializing agents with Anthropic API...[/bold]")
    rules = Constitution.default()

    adapter = AnthropicAPIAdapter(model="claude-haiku-4-5-20251001", api_key=api_key)

    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate business opportunities with honest, calibrated assessments",
        persona="Methodical and data-driven. Never overstates confidence.",
        adapter=adapter,
        constitution=rules,
    )
    critic = BaseAgent(
        role="critic",
        goal="Challenge assumptions and surface blind spots",
        persona="Sharp and contrarian. Raises exactly 3 specific challenges.",
        adapter=adapter,
        constitution=rules,
    )
    judge = BaseAgent(
        role="judge",
        goal="Evaluate debate arguments impartially and render fair verdicts",
        persona="Measured and impartial. Weights argument quality over role.",
        adapter=adapter,
        constitution=rules,
    )

    topic = "Should we build an AI-powered code review tool for enterprise teams?"
    console.print(f"\n[bold]Topic:[/bold] {topic}")

    console.print("\n[yellow]Running analyst assessment...[/yellow]")
    assessment = analyst.run(
        f"Evaluate this opportunity on a 0-40 scale across 5 dimensions "
        f"(market_size, timing, moat, execution, revenue). Return JSON with "
        f"score, dimensions dict, summary, confidence (0-1). Topic: {topic}"
    )
    console.print(f"[dim]Analyst response:[/dim] {assessment[:300]}")

    import json
    try:
        data = json.loads(assessment)
        score = data.get("score", 35)
    except (json.JSONDecodeError, TypeError):
        score = 35

    console.print(f"\n[bold]Score:[/bold] {score}/40")

    debate = Debate(challenger=critic, defender=analyst, judge=judge)
    if debate.should_trigger(score):
        console.print(f"\n[yellow]⚔️  Score {score} ≥ 32 → Triggering debate...[/yellow]")
        try:
            result = debate.run(topic=topic, initial_score=score)
        except DebateValidationError as exc:
            console.print(f"\n[red]Debate rejected invalid model output:[/red] {exc}")
            sys.exit(2)

        console.print(f"\n[bold]Verdict:[/bold] [magenta]{result.verdict}[/magenta]")
        console.print(f"[bold]Score Delta:[/bold] {result.score_delta:+d}")
        console.print(f"[bold]Final Score:[/bold] {score + result.score_delta}/40")

        total_cost = analyst.get_total_cost() + critic.get_total_cost() + judge.get_total_cost()
        console.print(f"\n[dim]Total API cost: ${total_cost:.4f}[/dim]")
    else:
        console.print(f"\n[dim]Score {score} < 32, debate not triggered.[/dim]")

    console.print(Panel.fit("[bold green]✓ API Demo Complete[/bold green]", border_style="green"))

if __name__ == "__main__":
    main()
