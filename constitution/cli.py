#!/usr/bin/env python3
"""
ac - Agent Constitution CLI

Usage:
    ac debate "Should we build X?"                         # MockAdapter (no API key)
    ac debate "Should we build X?" --adapter anthropic     # Anthropic API
    ac debate "topic" --adapter ollama --model llama3      # Ollama local
    ac debate "topic" --adapter claude --model sonnet      # Claude CLI
    ac score                                               # Show Governance Score from recorded runs
"""
import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
WORKSPACE_DIR = Path("workspace")
GOVERNANCE_HISTORY_PATH = WORKSPACE_DIR / "governance_history.json"


def _load_governance_history() -> list[dict]:
    if not GOVERNANCE_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(GOVERNANCE_HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _append_governance_history(record: dict) -> None:
    history = _load_governance_history()
    history.append(record)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    GOVERNANCE_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_json_object(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _has_calibrated_confidence(raw: str) -> bool:
    data = _parse_json_object(raw)
    confidence = None if data is None else data.get("confidence")
    return isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0


def _epistemic_honesty_score(raw_responses: list[str]) -> float:
    if not raw_responses:
        return 0.0

    honest_count = 0
    for raw in raw_responses:
        lowered = raw.lower()
        if _has_calibrated_confidence(raw):
            honest_count += 1
            continue
        if "[speculation]" in lowered or "i don't know" in lowered or "unable to verify" in lowered:
            honest_count += 1
    return honest_count / len(raw_responses)


def _analyst_response_is_valid(raw: str) -> bool:
    data = _parse_json_object(raw)
    if data is None:
        return False
    return (
        isinstance(data.get("score"), (int, float))
        and isinstance(data.get("summary"), str)
        and isinstance(data.get("dimensions"), dict)
        and _has_calibrated_confidence(raw)
    )


def _build_governance_record(
    *,
    topic: str,
    score: int,
    debate_triggered: bool,
    assessment: str,
    result,
    analyst,
    critic,
    judge,
) -> dict:
    from constitution.debate import VALID_VERDICTS, _validate_challenges, _validate_defenses, _validate_verdict

    raw_responses = [assessment]
    constitutional_checks = [1.0 if _analyst_response_is_valid(assessment) else 0.0]
    audit_checks = [1.0 if len(analyst.get_trace().entries) >= 1 else 0.0]
    debate_checks = [1.0 if debate_triggered else 1.0]

    calibration_accuracy = None
    challenges_count = 0
    defenses_count = 0
    audit_trail_entries = 0

    if result is not None:
        raw_responses.extend(entry.get("content", "") for entry in result.audit_trail)
        audit_trail_entries = len(result.audit_trail)
        challenges_count = len(result.challenges)
        defenses_count = len(result.defenses)

        challenger_raw = result.audit_trail[0]["content"]
        defender_raw = result.audit_trail[1]["content"]
        judge_raw = result.audit_trail[2]["content"]

        try:
            _validate_challenges(challenger_raw)
            challenger_valid = True
        except ValueError:
            challenger_valid = False

        try:
            _validate_defenses(defender_raw)
            defender_valid = True
        except ValueError:
            defender_valid = False

        try:
            _validate_verdict(judge_raw)
            judge_valid = True
        except ValueError:
            judge_valid = False

        constitutional_checks.extend([
            1.0 if challenger_valid and _has_calibrated_confidence(challenger_raw) else 0.0,
            1.0 if defender_valid and _has_calibrated_confidence(defender_raw) else 0.0,
            1.0 if judge_valid and _has_calibrated_confidence(judge_raw) else 0.0,
        ])

        debate_checks = [
            1.0 if debate_triggered else 0.0,
            1.0 if challenges_count == 3 else 0.0,
            1.0 if defenses_count == challenges_count and defenses_count > 0 else 0.0,
            1.0 if result.verdict in VALID_VERDICTS else 0.0,
        ]

        audit_checks.extend([
            1.0 if audit_trail_entries == 3 else 0.0,
            1.0 if len(critic.get_trace().entries) >= 1 and len(judge.get_trace().entries) >= 1 else 0.0,
            1.0 if {entry.get("role") for entry in result.audit_trail} == {"challenger", "defender", "judge"} else 0.0,
        ])

    return {
        "topic": topic,
        "score": score,
        "debate_triggered": debate_triggered,
        "epistemic_honesty": _epistemic_honesty_score(raw_responses),
        "constitutional_compliance": sum(constitutional_checks) / len(constitutional_checks),
        "debate_rigor": sum(debate_checks) / len(debate_checks),
        "calibration_accuracy": calibration_accuracy,
        "audit_completeness": sum(audit_checks) / len(audit_checks),
        "responses_analyzed": len(raw_responses),
        "audit_trail_entries": audit_trail_entries,
        "challenges_count": challenges_count,
        "defenses_count": defenses_count,
    }


def _build_adapter(adapter_name: str, model: str | None):
    """Construct the appropriate LLMAdapter from CLI flags."""
    if adapter_name == "mock":
        from adapters.mock import MockAdapter
        return MockAdapter()

    if adapter_name == "anthropic":
        from adapters.anthropic_api import AnthropicAPIAdapter
        kwargs = {}
        if model:
            kwargs["model"] = model
        return AnthropicAPIAdapter(**kwargs)

    if adapter_name == "ollama":
        from adapters.ollama import OllamaAdapter
        kwargs = {}
        if model:
            kwargs["model"] = model
        return OllamaAdapter(**kwargs)

    if adapter_name == "claude":
        from adapters.claude_cli import ClaudeCLIAdapter
        kwargs = {}
        if model:
            kwargs["model"] = model
        return ClaudeCLIAdapter(**kwargs)

    console.print(f"[red]Unknown adapter:[/red] {adapter_name}")
    console.print("[dim]Available: mock, anthropic, ollama, claude[/dim]")
    sys.exit(1)


def cmd_debate(args: argparse.Namespace) -> None:
    """Run a structured adversarial debate on the given topic."""
    from constitution import BaseAgent, Constitution, Debate, DebateValidationError

    adapter = _build_adapter(args.adapter, args.model)
    adapter_label = args.adapter
    if args.model:
        adapter_label += f" ({args.model})"

    console.print(Panel.fit(
        "[bold blue]Agent Constitution[/bold blue]  |  Adversarial Debate\n"
        f"[dim]Adapter: {adapter_label}[/dim]",
        border_style="blue",
    ))

    # --- agents ---
    rules = Constitution.default()

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
        persona="Sharp and contrarian by design. Raises exactly 3 challenges.",
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

    console.print("\n[bold]1. Agents initialized[/bold]")
    console.print(f"   analyst  | {adapter_label}")
    console.print(f"   critic   | {adapter_label}")
    console.print(f"   judge    | {adapter_label}")

    # --- initial assessment ---
    topic = args.topic
    console.print(f"\n[bold]2. Analyst evaluates:[/bold] {topic}")

    assessment = analyst.run(f"Evaluate this opportunity: {topic}")

    try:
        data = json.loads(assessment)
        score = data.get("score", 35)
        summary = data.get("summary", assessment[:120])
        confidence = data.get("confidence", 0.75)

        dims = data.get("dimensions", {})
        if dims:
            table = Table(title="Assessment Scores", show_header=True)
            table.add_column("Dimension", style="cyan")
            table.add_column("Score", style="green")
            for dim, val in dims.items():
                table.add_row(dim.replace("_", " ").title(), f"{val}/10")
            console.print(table)

        console.print(f"   [bold]Score:[/bold] [yellow]{score}/40[/yellow]")
        console.print(f"   [bold]Summary:[/bold] {summary}")
        console.print(f"   [bold]Confidence:[/bold] {confidence:.0%}")
    except (json.JSONDecodeError, TypeError):
        score = 35
        console.print(f"   {assessment[:200]}")

    # --- debate ---
    debate = Debate(challenger=critic, defender=analyst, judge=judge)

    if not debate.should_trigger(score):
        console.print(f"\n[dim]Score {score} < {debate.SCORE_THRESHOLD} — debate not triggered.[/dim]")
        _append_governance_history(
            _build_governance_record(
                topic=topic,
                score=score,
                debate_triggered=False,
                assessment=assessment,
                result=None,
                analyst=analyst,
                critic=critic,
                judge=judge,
            )
        )
        return

    console.print(f"\n[bold]3. Score {score} >= {debate.SCORE_THRESHOLD} — debate triggered[/bold]")
    try:
        result = debate.run(topic=topic, initial_score=score)
    except DebateValidationError as exc:
        console.print(
            Panel.fit(
                f"[bold red]Debate rejected[/bold red]\n[dim]{exc}[/dim]",
                border_style="red",
            )
        )
        sys.exit(2)

    # --- results ---
    console.print("\n[bold]4. Debate results[/bold]")

    console.print("\n   [red]Challenges:[/red]")
    for i, c in enumerate(result.challenges, 1):
        console.print(f"   {i}. {c}")

    console.print("\n   [green]Defenses:[/green]")
    for i, d in enumerate(result.defenses, 1):
        console.print(f"   {i}. {d}")

    console.print(f"\n   [bold]Verdict:[/bold]  [magenta]{result.verdict}[/magenta]")
    console.print(f"   [bold]Delta:[/bold]    {result.score_delta:+d}")
    console.print(f"   [bold]Reason:[/bold]   {result.reasoning[:200]}")

    final_score = score + result.score_delta
    console.print(f"\n   [bold]Final Score:[/bold] [yellow]{score}[/yellow] -> [green]{final_score}/40[/green]")

    # --- audit ---
    console.print(f"\n[bold]5. Audit trail[/bold] ({len(result.audit_trail)} steps)")
    for entry in result.audit_trail:
        role = entry.get("role", "?")
        content = entry.get("content", "")[:80]
        console.print(f"   [{role}] {content}...")

    _append_governance_history(
        _build_governance_record(
            topic=topic,
            score=score,
            debate_triggered=True,
            assessment=assessment,
            result=result,
            analyst=analyst,
            critic=critic,
            judge=judge,
        )
    )

    console.print(Panel.fit(
        f"[bold green]Done[/bold green]  "
        f"verdict=[magenta]{result.verdict}[/magenta]  "
        f"score=[yellow]{final_score}/40[/yellow]",
        border_style="green",
    ))


def cmd_score(args: argparse.Namespace) -> None:
    """Display the current Governance Score from recorded runs."""
    from constitution import aggregate_governance_reports, compute_governance_score, uncalibrated_report

    console.print(Panel.fit(
        "[bold blue]Agent Constitution[/bold blue]  |  Governance Score",
        border_style="blue",
    ))

    table = Table(show_header=True)
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", style="green")
    table.add_column("Weight", style="dim")

    history = _load_governance_history()
    if not history:
        report = uncalibrated_report()
        console.print(table)
        console.print(
            "[dim]No recorded debate runs yet. Run `ac debate \"topic\"` first to build governance history.[/dim]"
        )
        console.print(f"\n[bold]Status:[/bold] [yellow]{report.label}[/yellow]")
        return

    reports = [
        compute_governance_score(
            epistemic_honesty=entry.get("epistemic_honesty", 0.0),
            constitutional_compliance=entry.get("constitutional_compliance", 0.0),
            debate_rigor=entry.get("debate_rigor", 0.0),
            calibration_accuracy=entry.get("calibration_accuracy"),
            audit_completeness=entry.get("audit_completeness", 0.0),
        )
        for entry in history
    ]
    report = aggregate_governance_reports(reports)

    dimensions = [
        ("Epistemic Honesty", report.epistemic_honesty, 0.25),
        ("Constitutional Compliance", report.constitutional_compliance, 0.25),
        ("Debate Rigor", report.debate_rigor, 0.20),
        ("Calibration Accuracy", report.calibration_accuracy, 0.15),
        ("Audit Completeness", report.audit_completeness, 0.15),
    ]

    for name, metric, weight in dimensions:
        rendered = "N/A" if metric is None else f"{metric * 10:.1f}/10"
        table.add_row(name, rendered, f"{weight:.0%}")

    console.print(table)
    score_label = "Weighted Governance Score"
    score_style = "green"
    if report.badge == "uncalibrated":
        score_label = "Provisional Governance Score"
        score_style = "yellow"

    console.print(
        f"\n[bold]{score_label}:[/bold] [{score_style}]{report.score / 10:.1f}/10[/{score_style}]"
    )
    console.print(
        f"[dim]{len(history)} recorded run(s) analyzed. Current label: {report.label}.[/dim]"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ac",
        description="Agent Constitution CLI - multi-agent governance framework",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- debate ---
    debate_parser = subparsers.add_parser(
        "debate",
        help="Run an adversarial debate on a topic",
    )
    debate_parser.add_argument(
        "topic",
        help="The topic or question to debate",
    )
    debate_parser.add_argument(
        "--adapter",
        choices=["mock", "anthropic", "ollama", "claude"],
        default="mock",
        help="LLM adapter to use (default: mock)",
    )
    debate_parser.add_argument(
        "--model",
        default=None,
        help="Model name to pass to the adapter",
    )

    # --- score ---
    subparsers.add_parser(
        "score",
        help="Show the current Governance Score",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "debate": cmd_debate,
        "score": cmd_score,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
