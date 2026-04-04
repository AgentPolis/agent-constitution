#!/usr/bin/env python3
"""
Agent Constitution Demo: Personal Agent
Run: python examples/demo_personal.py
No API key required.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapters import MockAdapter
from constitution import BaseAgent, Constitution

console = Console()

# --- Mock responses tailored to the personal agent demo ---

PERSONAL_RESPONSES = {
    "selfreviewer": (
        "Self-review findings:\n"
        "1. FAIR — The response correctly separated observed execution issues from forward-looking speculation.\n"
        "2. CONCERN — Confidence 0.78 may be too high given we do not know how the current managers would absorb the transition load. Recommend lowering to 0.64.\n"
        "3. CONCERN — The claim that a reorganization would clarify ownership before launch is plausible, but still speculative without evidence from the last two delivery cycles.\n"
        "4. GOOD — Proactive recall of prior context was relevant and not overstated.\n"
        "Governance compliance: 3/4 checks passed. Score: 82/100"
    ),
    "personal": (
        "[verified] You said roadmap ownership is currently split across two PMs and launch-readiness reviews have slipped twice in the last quarter. "
        "[verified] You also said the onboarding rebuild is already on the Q4 critical path. "
        "[speculation] Reorganizing before launch could improve accountability, but it may also slow execution for 4-6 weeks while reporting lines and rituals reset. "
        "[speculation] A narrower move, such as assigning a single launch owner without a full reorg, may capture most of the clarity with less disruption. "
        "Confidence: 0.78"
    ),
    "recall": (
        "Recalling prior context: last week you said the biggest issue was unclear launch ownership between product, engineering, and customer success. "
        "[verified] That context supports the case for clearer operating boundaries before the Q4 release. "
        "[speculation] Instead of a full team reorg, a temporary launch pod with one directly responsible owner may deliver most of the benefit with lower disruption. "
        "Confidence: 0.72"
    ),
    "default": (
        '{"status": "ok", "response": "Task completed.", "confidence": 0.70}'
    ),
}


def compute_governance_score(review_text: str) -> int:
    """Extract or estimate a governance score from self-review text."""
    # Look for an explicit score in the review
    import re
    match = re.search(r"Score:\s*(\d+)/100", review_text)
    if match:
        return int(match.group(1))
    # Fallback heuristic
    score = 70
    if "GOOD" in review_text:
        score += 10
    if "CONCERN" in review_text:
        score -= 5
    return min(100, max(0, score))


def main():
    console.print(Panel.fit(
        "[bold blue]🧠 Personal Decision Review[/bold blue]\n"
        "[dim]Decision review for individual operators - No API key required[/dim]",
        border_style="blue"
    ))

    # --- Step 1: Load SOUL.md and create the personal agent ---
    console.print("\n[bold]Step 1: Loading SOUL.md and constitutional rules[/bold]")

    soul_path = Path(__file__).parent / "agents" / "personal" / "SOUL.md"
    if not soul_path.exists():
        console.print(f"[red]SOUL.md not found at {soul_path}[/red]")
        sys.exit(1)
    base_constitution = Constitution.default()
    soul_constitution = Constitution.from_soul_md(soul_path)
    merged = base_constitution.merge(soul_constitution)

    agent = BaseAgent(
        role="personal",
        goal="Help the user think clearly about technical decisions",
        persona="Thoughtful and direct. Tags every claim as [verified] or [speculation].",
        adapter=MockAdapter(role_responses=PERSONAL_RESPONSES, simulate_delay_ms=30),
        constitution=merged,
    )
    console.print(f"  ✓ Loaded SOUL.md from [cyan]{soul_path.name}[/cyan]")
    console.print(f"  ✓ Merged constitution: {len(merged.text)} chars")
    console.print("  ✓ Personal agent ready (MockAdapter — zero config)")

    # --- Step 2: Agent answers a question with epistemic honesty ---
    console.print("\n[bold]Step 2: 📝 Your agent responds...[/bold]")

    question = "Should I reorganize the product team before the Q4 launch?"
    console.print(f"  [dim]User:[/dim] {question}\n")

    answer = agent.run(question)

    console.print(Panel(
        answer,
        title="[bold green]Agent Response[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    # --- Step 3: Agent remembers context (simulated prior interaction) ---
    console.print("\n[bold]Step 3: 📝 Proactive recall from prior context[/bold]")

    recall_agent = BaseAgent(
        role="recall",
        goal="Incorporate prior context to give better answers",
        persona="Remembers past conversations. Surfaces relevant history.",
        adapter=MockAdapter(role_responses=PERSONAL_RESPONSES, simulate_delay_ms=30),
        constitution=merged,
    )

    followup = "What would you specifically recommend given what you know about my situation?"
    console.print(f"  [dim]User:[/dim] {followup}\n")

    recall_answer = recall_agent.run(followup)

    console.print(Panel(
        recall_answer,
        title="[bold yellow]Agent Response (with recall)[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))

    # --- Step 4: Adversarial self-review ---
    console.print("\n[bold]Step 4: 🔍 Self-check (adversarial review)...[/bold]")

    reviewer = BaseAgent(
        role="selfreviewer",
        goal="Audit the agent's own response for constitutional compliance",
        persona="Internal auditor. Checks epistemic honesty, calibration, and recall accuracy.",
        adapter=MockAdapter(role_responses=PERSONAL_RESPONSES, simulate_delay_ms=30),
        constitution=merged,
    )

    review_prompt = (
        f"Review this agent response for constitutional compliance:\n\n"
        f"ORIGINAL QUESTION: {question}\n"
        f"AGENT RESPONSE: {answer}\n\n"
        f"Check: (1) Are [verified]/[speculation] tags accurate? "
        f"(2) Is confidence well-calibrated? "
        f"(3) Are there unsupported claims? "
        f"(4) Was prior context used appropriately?"
    )

    review = reviewer.run(review_prompt)

    console.print(Panel(
        review,
        title="[bold red]Adversarial Self-Review[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))

    # --- Step 5: Governance score ---
    score = compute_governance_score(review)
    console.print(f"\n[bold]Step 5: 📊 Governance Score: {score}/100[/bold]")

    score_table = Table(show_header=True, title="Governance Breakdown")
    score_table.add_column("Check", style="cyan")
    score_table.add_column("Status", style="bold")
    score_table.add_row("Epistemic tags present", "[green]PASS[/green]")
    score_table.add_row("Confidence calibrated", "[yellow]ADJUSTED[/yellow] (0.78 → 0.64)")
    score_table.add_row("No fabricated claims", "[green]PASS[/green]")
    score_table.add_row("Speculation clearly marked", "[yellow]NEEDS WORK[/yellow]")
    console.print(score_table)

    # --- Wrap up ---
    total_cost = agent.get_total_cost() + recall_agent.get_total_cost() + reviewer.get_total_cost()
    trace_count = (
        len(agent.get_trace().entries)
        + len(recall_agent.get_trace().entries)
        + len(reviewer.get_trace().entries)
    )

    console.print(Panel.fit(
        f"[bold green]✓ Demo Complete[/bold green]\n"
        f"Governance Score: [yellow]{score}/100[/yellow] | "
        f"Trace entries: {trace_count} | "
        f"Cost: ${total_cost:.4f}\n\n"
        f"[bold]Agent Constitution can also support individual decision review.[/bold]\n"
        f"[dim]No API key used. Run examples/demo_api.py to use real LLMs.[/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
