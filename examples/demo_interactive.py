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
from constitution.debate import DebateResult
from constitution.hooks import DebateHook
from constitution.retrospective import Retrospective

console = Console()

# ---------------------------------------------------------------------------
# Live Debate Hook — shows each stage as it happens
# ---------------------------------------------------------------------------

class LiveDebateHook(DebateHook):
    """Print each debate stage live so the user sees the process unfold."""

    def pre_challenge(self, topic: str) -> str:
        console.print("\n  [bold yellow]▶ Challenger 正在分析弱點...[/bold yellow]")
        return topic

    def post_challenge(self, challenges: list[str]) -> list[str]:
        console.print(Panel(
            "\n".join(f"[red]{i}.[/red] {c}" for i, c in enumerate(challenges, 1)),
            title="[bold red]Challenger 質疑[/bold red]",
            border_style="red",
            padding=(1, 2),
        ))
        return challenges

    def pre_defense(self, challenges: list[str]) -> list[str]:
        console.print("  [bold yellow]▶ Defender 正在準備回擊...[/bold yellow]")
        return challenges

    def post_defense(self, defenses: list[str]) -> list[str]:
        console.print(Panel(
            "\n".join(f"[green]{i}.[/green] {d}" for i, d in enumerate(defenses, 1)),
            title="[bold green]Defender 辯護[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
        return defenses

    def pre_verdict(self, challenges, defenses):
        console.print("  [bold yellow]▶ Judge 正在權衡雙方論點...[/bold yellow]")

    def post_verdict(self, result: DebateResult) -> DebateResult:
        verdict_colors = {
            "proceed": "bold green",
            "reject": "bold red",
            "proceed_with_caution": "bold yellow",
            "reconsider": "bold magenta",
        }
        verdict_labels = {
            "proceed": "通過 — 可以執行",
            "reject": "駁回 — 不建議執行",
            "proceed_with_caution": "有條件通過 — 注意風險",
            "reconsider": "需要重新考慮",
        }
        color = verdict_colors.get(result.verdict, "bold white")
        label = verdict_labels.get(result.verdict, result.verdict)

        console.print(Panel(
            f"[{color}]{label}[/{color}]\n\n"
            f"[bold]Score 變化：[/bold]{result.score_delta:+d}\n\n"
            f"[bold]理由：[/bold]\n{result.reasoning}",
            title="[bold magenta]Judge 裁決[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        ))
        return result


# ---------------------------------------------------------------------------
# Presets — common decision scenarios users can pick
# ---------------------------------------------------------------------------

PRESETS = {
    "1": {
        "name": "技術決策",
        "topic": "Should we rewrite our monolith backend from Python to Rust for 10x performance?",
    },
    "2": {
        "name": "產品決策",
        "topic": "Should we pivot from B2B SaaS to open-source with a managed cloud offering?",
    },
    "3": {
        "name": "架構決策",
        "topic": "Should we migrate from REST API to GraphQL across all 12 microservices?",
    },
    "4": {
        "name": "人員決策",
        "topic": "Should we hire 5 junior developers instead of 2 senior developers to scale faster?",
    },
    "5": {
        "name": "投資決策",
        "topic": "Should we raise a $10M Series A now at 40x revenue multiple, or wait 6 months for better metrics?",
    },
}


def pick_topic() -> str:
    """Let user pick a preset or type their own."""
    console.print("\n[bold]選一個情境，或自己輸入：[/bold]\n")
    for key, preset in PRESETS.items():
        console.print(f"  [cyan]{key}[/cyan]. {preset['name']}")
        console.print(f"     [dim]{preset['topic'][:70]}...[/dim]")
    console.print("  [cyan]6[/cyan]. 自己輸入\n")

    choice = console.input("[bold]選擇 (1-6): [/bold]").strip()
    if choice in PRESETS:
        topic = PRESETS[choice]["topic"]
        console.print(f"\n  [dim]→ {topic}[/dim]")
        return topic
    else:
        topic = console.input("\n[bold]輸入你的決策問題：[/bold] ").strip()
        if not topic:
            topic = PRESETS["1"]["topic"]
            console.print(f"  [dim]→ 使用預設：{topic}[/dim]")
        return topic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Use MockAdapter (no API key)")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold blue]Agent Constitution — 互動辯論體驗[/bold blue]\n"
        "[dim]你的 AI agent 在做重大決策前，會先被挑戰。[/dim]",
        border_style="blue",
    ))

    # ── Adapter selection ──
    use_mock = args.mock
    if not use_mock:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[yellow]未偵測到 ANTHROPIC_API_KEY，使用 MockAdapter[/yellow]")
            use_mock = True

    if use_mock:
        from adapters import MockAdapter
        adapter = MockAdapter()
        console.print("[dim]Mode: MockAdapter (罐頭回應，但完整展示流程)[/dim]")
    else:
        from adapters import AnthropicAPIAdapter
        adapter = AnthropicAPIAdapter(model="claude-haiku-4-5-20251001", api_key=api_key)
        console.print("[dim]Mode: Anthropic API (claude-haiku-4-5，真實 LLM 辯論)[/dim]")

    # ── Pick topic ──
    topic = pick_topic()

    # ── Setup agents ──
    console.print("\n[bold cyan]建立 Agent 團隊[/bold cyan]")
    rules = Constitution.default()

    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate decisions with honest, calibrated assessments. Return JSON with score (0-40), dimensions (market_size, timing, moat, execution, revenue each 0-10), summary, confidence (0-1).",
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

    console.print("  [cyan]analyst[/cyan] — 評估決策可行性")
    console.print("  [red]critic[/red]  — 挑戰假設、找盲點")
    console.print("  [magenta]judge[/magenta]   — 公正裁決")

    # ── Step 1: Assessment ──
    console.print("\n[bold cyan]Step 1: Analyst 評估中...[/bold cyan]")
    assessment = analyst.run(
        f"Evaluate this decision on a 0-40 scale across 5 dimensions "
        f"(market_size, timing, moat, execution, revenue). Return JSON with "
        f"score, dimensions dict, summary, confidence (0-1). Decision: {topic}"
    )

    try:
        data = json.loads(assessment)
        score = data.get("score", 35)
        summary = data.get("summary", assessment[:200])
        confidence = data.get("confidence", 0.75)
        dimensions = data.get("dimensions", {})

        table = Table(title="Analyst 評估", box=box.ROUNDED)
        table.add_column("維度", style="cyan")
        table.add_column("分數", style="green", justify="center")
        table.add_column("", style="dim")
        for dim, val in dimensions.items():
            bar = "█" * val + "░" * (10 - val)
            table.add_row(dim.replace("_", " ").title(), f"{val}/10", bar)
        console.print(table)
        console.print(f"\n  [bold]總分：[/bold][yellow]{score}/40[/yellow]  "
                       f"[bold]信心：[/bold]{confidence:.0%}")
        console.print(f"  [bold]摘要：[/bold]{summary}")
    except (json.JSONDecodeError, TypeError):
        score = 35
        console.print(f"  [dim]{assessment[:300]}[/dim]")

    # ── Step 2: Trigger decision ──
    threshold = Debate.SCORE_THRESHOLD
    console.print("\n[bold cyan]Step 2: 是否觸發辯論？[/bold cyan]")
    console.print(f"  Score {score} {'≥' if score >= threshold else '<'} {threshold} (threshold)")

    if score < threshold:
        console.print("  [green]低風險，不需要辯論。直接通過。[/green]")
        return

    console.print("  [yellow]高分 = 高風險決策 → 觸發 Adversarial Debate[/yellow]")
    console.print("  [dim]（這就是 Agent Constitution 的核心：重大決策自動被挑戰）[/dim]")

    # ── Step 3: Debate ──
    console.print("\n[bold cyan]Step 3: 辯論開始[/bold cyan]")

    debate = Debate(
        challenger=critic,
        defender=analyst,
        judge=judge,
        hooks=[LiveDebateHook()],
    )
    result = debate.run(topic=topic, initial_score=score)
    final_score = score + result.score_delta

    # ── Step 4: Record to retrospective ──
    retro = Retrospective()
    pred = retro.record_prediction(
        agent_role="analyst",
        claim=f"Decision '{topic[:50]}...' scored {score}/40",
        confidence=confidence if 'confidence' in dir() else 0.75,
    )

    # ── Step 5: Summary ──
    console.print("\n[bold cyan]結果[/bold cyan]")

    summary_table = Table(box=box.ROUNDED, show_header=False)
    summary_table.add_column("", style="bold", width=12)
    summary_table.add_column("")
    summary_table.add_row("決策", topic[:80])
    summary_table.add_row("初始評分", f"{score}/40")
    summary_table.add_row("辯論調整", f"{result.score_delta:+d}")
    summary_table.add_row("最終評分", f"[bold]{final_score}/40[/bold]")
    summary_table.add_row("判決", result.verdict)
    summary_table.add_row("Prediction ID", pred.id[:8] + "...")
    console.print(summary_table)

    if not use_mock:
        total_cost = analyst.get_total_cost() + critic.get_total_cost() + judge.get_total_cost()
        console.print(f"\n  [dim]API 成本：${total_cost:.4f} (4 calls × haiku)[/dim]")

    console.print(Panel.fit(
        "[bold]為什麼這很重要？[/bold]\n\n"
        "沒有 Agent Constitution：agent 說 'score 35, go for it'，你就信了。\n"
        "有 Agent Constitution：每個高風險決策都會被質疑、辯護、裁決。\n"
        "全程有審計紀錄，任何人都能回溯「為什麼做了這個決定」。",
        border_style="blue",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
