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

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402

from adapters import AnthropicAPIAdapter  # noqa: E402
from constitution import BaseAgent, Constitution, Debate, DebateValidationError  # noqa: E402
from constitution.debate import clamp_score, delta_severity  # noqa: E402
from constitution.scenarios import build_analyst_prompt  # noqa: E402

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

    topic = "Should we expand from mid-market to enterprise this year?"
    console.print(f"\n[bold]Topic:[/bold] {topic}")

    console.print("\n[yellow]Running analyst assessment...[/yellow]")
    assessment = analyst.run(build_analyst_prompt(topic))
    console.print(f"[dim]Analyst response:[/dim] {assessment[:300]}")

    import json
    try:
        data = json.loads(assessment)
        score = data.get("score", 78)
    except (json.JSONDecodeError, TypeError):
        score = 78

    console.print(f"\n[bold]Score:[/bold] {score}/100")

    debate = Debate(challenger=critic, defender=analyst, judge=judge)
    if debate.should_trigger(score):
        console.print(f"\n[yellow]⚔️  Score {score} ≥ 70 → Triggering debate...[/yellow]")
        try:
            result = debate.run(topic=topic, initial_score=score)
        except DebateValidationError as exc:
            console.print(f"\n[red]Debate rejected invalid model output:[/red] {exc}")
            sys.exit(2)

        console.print(f"\n[bold]Verdict:[/bold] [magenta]{result.verdict}[/magenta]")
        console.print(f"[bold]Score Delta:[/bold] {result.score_delta:+d}")
        console.print(f"[bold]Delta Severity:[/bold] {delta_severity(result.score_delta).title()}")
        console.print(f"[bold]Final Score:[/bold] {clamp_score(score + result.score_delta)}/100")

        total_cost = analyst.get_total_cost() + critic.get_total_cost() + judge.get_total_cost()
        console.print(f"\n[dim]Total API cost: ${total_cost:.4f}[/dim]")
    else:
        console.print(f"\n[dim]Score {score} < 70, debate not triggered.[/dim]")

    console.print(Panel.fit("[bold green]✓ API Demo Complete[/bold green]", border_style="green"))

if __name__ == "__main__":
    main()
