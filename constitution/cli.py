#!/usr/bin/env python3
"""
ac - Agent Constitution CLI

Usage:
    ac debate "Should we build X?"                         # MockAdapter (no API key)
    ac debate "Should we build X?" --adapter anthropic     # Anthropic API
    ac debate "topic" --adapter ollama --model llama3      # Ollama local
    ac debate "topic" --adapter claude --model sonnet      # Claude CLI
    ac debate "topic" --critic-model opus --judge-model opus  # stronger critic/judge
    ac score                                               # Show Governance Score from recorded runs
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
WORKSPACE_DIR = Path("workspace")
GOVERNANCE_HISTORY_PATH = WORKSPACE_DIR / "governance_history.json"
DEBATES_DIR = WORKSPACE_DIR / "debates"
ADAPTER_CHOICES = ("mock", "anthropic", "ollama", "claude")


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


def _slugify_topic(topic: str, *, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    slug = slug[:limit].strip("-")
    return slug or "debate"


def _read_context_files(paths: list[str] | None, *, max_chars_per_file: int = 6000) -> tuple[list[dict], list[str]]:
    loaded: list[dict] = []
    errors: list[str] = []
    for raw_path in paths or []:
        path = Path(raw_path)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        truncated = False
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file]
            truncated = True
        loaded.append({"path": str(path), "content": content, "truncated": truncated})
    return loaded, errors


def _build_supporting_context(context_files: list[dict]) -> str:
    if not context_files:
        return ""
    sections = ["Supporting context:"]
    for item in context_files:
        header = f"[File: {item['path']}]"
        if item.get("truncated"):
            header += " (truncated)"
        sections.extend(["", header, item["content"]])
    return "\n".join(sections)


def _write_debate_artifact(
    *,
    topic: str,
    score: int,
    assessment: str,
    result,
    context_files: list[dict] | None = None,
) -> Path:
    from constitution.debate import SCORE_MAX, clamp_score, delta_severity, score_band

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    artifact_path = DEBATES_DIR / f"{timestamp}-{_slugify_topic(topic)}.md"
    DEBATES_DIR.mkdir(parents=True, exist_ok=True)

    assessment_data = _parse_json_object(assessment) or {}
    summary = assessment_data.get("summary", "")
    confidence = assessment_data.get("confidence")
    scenario = assessment_data.get("scenario", "unknown")
    dimensions = assessment_data.get("dimensions", {})

    lines = [
        f"# Debate Record: {topic}",
        "",
        f"- Generated: {timestamp}",
        f"- Scenario: {scenario}",
        f"- Initial score: {score}/{SCORE_MAX} ({score_band(score).title()})",
    ]

    if isinstance(confidence, (int, float)):
        lines.append(f"- Confidence: {float(confidence):.0%}")
    lines.extend(["", "## Context", ""])
    if context_files:
        for item in context_files:
            suffix = " (truncated)" if item.get("truncated") else ""
            lines.append(f"- {item['path']}{suffix}")
    else:
        lines.append("- No supporting context files were supplied. Treat this as a first-pass judgment.")
    lines.append("")
    lines.append("## Analyst Assessment")
    if summary:
        lines.extend(["", summary])
    if dimensions:
        lines.extend(["", "### Dimensions", ""])
        for dim, value in dimensions.items():
            lines.append(f"- {dim}: {value}/20")

    if result is None:
        lines.extend(["", "## Debate Trigger", "", "- Debate not triggered"])
    else:
        final_score = clamp_score(score + result.score_delta)
        lines.extend(
            [
                "",
                "## Debate Result",
                "",
                f"- Verdict: {result.verdict}",
                f"- Score delta: {result.score_delta:+d}",
                f"- Delta severity: {delta_severity(result.score_delta)}",
                f"- Final score: {final_score}/{SCORE_MAX} ({score_band(final_score).title()})",
                "",
                "### Reasoning",
                "",
                result.reasoning,
                "",
                "### Missing Context",
                "",
            ]
        )
        for missing in result.missing_context:
            lines.append(f"- {missing}")
        lines.extend(
            [
                "",
                "### Next Actions",
                "",
            ]
        )
        for action in result.next_actions:
            lines.append(f"- {action}")
        lines.extend(
            [
                "",
                "### Upgrade Condition",
                "",
                result.upgrade_condition,
                "",
                "### Downgrade Condition",
                "",
                result.downgrade_condition,
                "",
                "### Challenges",
                "",
            ]
        )
        for challenge in result.challenges:
            lines.append(f"- {challenge}")
        lines.extend(["", "### Defenses", ""])
        for defense in result.defenses:
            lines.append(f"- {defense}")

    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifact_path


def _strip_code_fence(raw: str | None) -> str | None:
    """Strip markdown code fences (```json ... ```) from LLM responses."""
    if not isinstance(raw, str):
        return None
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else raw


def _parse_json_object(raw: str | None) -> dict | None:
    stripped = _strip_code_fence(raw)
    if not isinstance(stripped, str):
        return None
    try:
        data = json.loads(stripped)
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


def _parse_analyst_assessment(raw: str) -> dict:
    data = _parse_json_object(raw)
    if data is None:
        raise ValueError("Analyst must return a JSON object.")
    if not isinstance(data.get("score"), (int, float)):
        raise ValueError("Analyst response must include numeric `score`.")
    if not isinstance(data.get("summary"), str):
        raise ValueError("Analyst response must include string `summary`.")
    if not isinstance(data.get("dimensions"), dict):
        raise ValueError("Analyst response must include object `dimensions`.")
    if not _has_calibrated_confidence(raw):
        raise ValueError("Analyst response must include calibrated `confidence` between 0 and 1.")
    return data


def _find_audit_entry_content(audit_trail: list[dict], role: str) -> str | None:
    for entry in audit_trail:
        if entry.get("role") == role and isinstance(entry.get("content"), str):
            return entry["content"]
    return None


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
    from constitution.debate import (
        VALID_VERDICTS,
        _validate_challenges,
        _validate_defenses,
        _validate_verdict,
    )

    raw_responses = [assessment]
    constitutional_checks = [1.0 if _analyst_response_is_valid(assessment) else 0.0]
    audit_checks = [1.0 if len(analyst.get_trace().entries) >= 1 else 0.0]
    debate_checks = [1.0 if debate_triggered else 0.0]

    calibration_accuracy = None
    challenges_count = 0
    defenses_count = 0
    audit_trail_entries = 0

    if result is not None:
        raw_responses.extend(entry.get("content", "") for entry in result.audit_trail)
        audit_trail_entries = len(result.audit_trail)
        challenges_count = len(result.challenges)
        defenses_count = len(result.defenses)

        if len(result.audit_trail) < 3:
            return {
                "topic": topic,
                "score": score,
                "debate_triggered": debate_triggered,
                "epistemic_honesty": _epistemic_honesty_score(raw_responses),
                "constitutional_compliance": sum(constitutional_checks) / len(constitutional_checks),
                "debate_rigor": 0.0,
                "calibration_accuracy": calibration_accuracy,
                "audit_completeness": 0.0,
                "responses_analyzed": len(raw_responses),
                "audit_trail_entries": audit_trail_entries,
                "challenges_count": challenges_count,
                "defenses_count": defenses_count,
            }

        challenger_raw = _find_audit_entry_content(result.audit_trail, "challenger")
        defender_raw = _find_audit_entry_content(result.audit_trail, "defender")
        judge_raw = _find_audit_entry_content(result.audit_trail, "judge")

        if not all((challenger_raw, defender_raw, judge_raw)):
            return {
                "topic": topic,
                "score": score,
                "debate_triggered": debate_triggered,
                "epistemic_honesty": _epistemic_honesty_score(raw_responses),
                "constitutional_compliance": sum(constitutional_checks) / len(constitutional_checks),
                "debate_rigor": 0.0,
                "calibration_accuracy": calibration_accuracy,
                "audit_completeness": 0.0,
                "responses_analyzed": len(raw_responses),
                "audit_trail_entries": audit_trail_entries,
                "challenges_count": challenges_count,
                "defenses_count": defenses_count,
            }

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
            1.0 if audit_trail_entries >= 3 else 0.0,
            1.0 if len(critic.get_trace().entries) >= 1 and len(judge.get_trace().entries) >= 1 else 0.0,
            1.0 if {"challenger", "defender", "judge"}.issubset(
                {entry.get("role") for entry in result.audit_trail}
            ) else 0.0,
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


def _resolve_role_config(args: argparse.Namespace, role: str) -> tuple[str, str | None]:
    adapter_name = getattr(args, f"{role}_adapter", None) or args.adapter
    model_name = getattr(args, f"{role}_model", None) or args.model
    return adapter_name, model_name


def _format_adapter_label(adapter_name: str, model_name: str | None) -> str:
    if model_name:
        return f"{adapter_name} ({model_name})"
    return adapter_name


def cmd_debate(args: argparse.Namespace) -> None:
    """Run a structured adversarial debate on the given topic."""
    from constitution import BaseAgent, Constitution, Debate, DebateValidationError
    from constitution.debate import SCORE_MAX, clamp_score, delta_severity, score_band
    from constitution.scenarios import build_analyst_prompt

    analyst_adapter_name, analyst_model = _resolve_role_config(args, "analyst")
    critic_adapter_name, critic_model = _resolve_role_config(args, "critic")
    judge_adapter_name, judge_model = _resolve_role_config(args, "judge")

    analyst_adapter = _build_adapter(analyst_adapter_name, analyst_model)
    critic_adapter = _build_adapter(critic_adapter_name, critic_model)
    judge_adapter = _build_adapter(judge_adapter_name, judge_model)

    console.print(Panel.fit(
        "[bold blue]Agent Constitution[/bold blue]  |  Adversarial Debate\n"
        f"[dim]Analyst: {_format_adapter_label(analyst_adapter_name, analyst_model)}[/dim]\n"
        f"[dim]Critic:  {_format_adapter_label(critic_adapter_name, critic_model)}[/dim]\n"
        f"[dim]Judge:   {_format_adapter_label(judge_adapter_name, judge_model)}[/dim]",
        border_style="blue",
    ))

    # --- agents ---
    rules = Constitution.default()

    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate business opportunities with honest, calibrated assessments",
        persona="Methodical and data-driven. Never overstates confidence.",
        adapter=analyst_adapter,
        constitution=rules,
    )
    critic = BaseAgent(
        role="critic",
        goal="Challenge assumptions and surface blind spots",
        persona="Sharp and contrarian by design. Raises exactly 3 challenges.",
        adapter=critic_adapter,
        constitution=rules,
    )
    judge = BaseAgent(
        role="judge",
        goal="Evaluate debate arguments impartially and render fair verdicts",
        persona="Measured and impartial. Weights argument quality over role.",
        adapter=judge_adapter,
        constitution=rules,
    )

    console.print("\n[bold]1. Agents initialized[/bold]")
    console.print(f"   analyst  | {_format_adapter_label(analyst_adapter_name, analyst_model)}")
    console.print(f"   critic   | {_format_adapter_label(critic_adapter_name, critic_model)}")
    console.print(f"   judge    | {_format_adapter_label(judge_adapter_name, judge_model)}")

    # --- initial assessment ---
    topic = args.topic
    console.print(f"\n[bold]2. Analyst evaluates:[/bold] {topic}")
    context_files, context_errors = _read_context_files(args.context_file)
    for error in context_errors:
        console.print(f"[yellow]Context file warning:[/yellow] {error}")
    if context_files:
        console.print("   [bold]Context files:[/bold]")
        for item in context_files:
            suffix = " (truncated)" if item.get("truncated") else ""
            console.print(f"     - {item['path']}{suffix}")
    else:
        console.print(
            "   [yellow]No supporting context files supplied.[/yellow] "
            "Treat this as a first-pass judgment, not a final approval."
        )
    supporting_context = _build_supporting_context(context_files)

    analyst_prompt = build_analyst_prompt(topic)
    if supporting_context:
        analyst_prompt = f"{analyst_prompt}\n\n{supporting_context}"
    assessment = analyst.run(analyst_prompt)

    try:
        data = _parse_analyst_assessment(assessment)
    except ValueError as exc:
        console.print(
            Panel.fit(
                f"[bold red]Assessment rejected[/bold red]\n[dim]{exc}[/dim]",
                border_style="red",
            )
        )
        sys.exit(2)

    score = int(data["score"])
    summary = data["summary"]
    confidence = data["confidence"]
    dims = data.get("dimensions", {})
    if dims:
        table = Table(title="Assessment Scores", show_header=True)
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", style="green")
        for dim, val in dims.items():
            table.add_row(dim.replace("_", " ").title(), f"{val}/20")
        console.print(table)

    console.print(
        f"   [bold]Score:[/bold] [yellow]{score}/{SCORE_MAX}[/yellow] "
        f"({score_band(score).title()})"
    )
    console.print(f"   [bold]Summary:[/bold] {summary}")
    console.print(f"   [bold]Confidence:[/bold] {confidence:.0%}")

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
        artifact_path = _write_debate_artifact(
            topic=topic,
            score=score,
            assessment=assessment,
            result=None,
            context_files=context_files,
        )
        console.print(f"[dim]Saved debate record: {artifact_path}[/dim]")
        return

    console.print(f"\n[bold]3. Score {score} >= {debate.SCORE_THRESHOLD} — debate triggered[/bold]")
    try:
        debate_topic = topic if not supporting_context else f"{topic}\n\n{supporting_context}"
        result = debate.run(topic=debate_topic, initial_score=score)
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
    console.print(f"   [bold]Severity:[/bold] {delta_severity(result.score_delta).title()}")
    console.print(f"   [bold]Reason:[/bold]   {result.reasoning[:200]}")
    if result.missing_context:
        console.print("   [bold]Missing Context:[/bold]")
        for item in result.missing_context:
            console.print(f"     - {item}")
    if result.next_actions:
        console.print("   [bold]Next Actions:[/bold]")
        for action in result.next_actions:
            console.print(f"     - {action}")
    if result.upgrade_condition:
        console.print(f"   [bold]Upgrade:[/bold]  {result.upgrade_condition}")
    if result.downgrade_condition:
        console.print(f"   [bold]Downgrade:[/bold] {result.downgrade_condition}")

    final_score = clamp_score(score + result.score_delta)
    console.print(
        f"\n   [bold]Final Score:[/bold] [yellow]{score}[/yellow] -> "
        f"[green]{final_score}/{SCORE_MAX}[/green] ({score_band(final_score).title()})"
    )

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
    artifact_path = _write_debate_artifact(
        topic=topic,
        score=score,
        assessment=assessment,
        result=result,
        context_files=context_files,
    )
    console.print(f"[dim]Saved debate record: {artifact_path}[/dim]")

    console.print(Panel.fit(
        f"[bold green]Done[/bold green]  "
        f"verdict=[magenta]{result.verdict}[/magenta]  "
        f"score=[yellow]{final_score}/{SCORE_MAX}[/yellow]",
        border_style="green",
    ))


def cmd_score(args: argparse.Namespace) -> None:
    """Display the current Governance Score from recorded runs."""
    from constitution import (
        aggregate_governance_reports,
        compute_governance_score,
        uncalibrated_report,
    )

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
        help="Assess a topic, then trigger debate automatically if score >= 70/100",
        description=(
            "Run an analyst assessment first. If the initial score is 70/100 or higher, "
            "Agent Constitution automatically triggers the challenger / defender / judge round."
        ),
    )
    debate_parser.add_argument(
        "topic",
        help="The topic or question to assess; structured debate runs only if the score crosses threshold",
    )
    debate_parser.add_argument(
        "--context-file",
        action="append",
        default=[],
        help="Attach a background file or decision document. Repeat for multiple files.",
    )
    debate_parser.add_argument(
        "--adapter",
        choices=ADAPTER_CHOICES,
        default="mock",
        help="Default LLM adapter for all debate roles unless a role-specific override is provided",
    )
    debate_parser.add_argument(
        "--model",
        default=None,
        help="Default model for all debate roles unless a role-specific override is provided",
    )
    for role in ("analyst", "critic", "judge"):
        debate_parser.add_argument(
            f"--{role}-adapter",
            choices=ADAPTER_CHOICES,
            default=None,
            help=f"Override adapter for the {role} role",
        )
        debate_parser.add_argument(
            f"--{role}-model",
            default=None,
            help=f"Override model for the {role} role",
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
