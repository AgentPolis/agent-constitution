#!/usr/bin/env python3
"""
Agent Constitution Demo: Signal Pipeline
Run: python examples/demo_signal.py
No API key required.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from constitution import Signal, SignalPool

console = Console()

def make_signal(tier, direction, title, source, confidence, hours_ago=0):
    return Signal(
        tier=tier,
        direction=direction,
        title=title,
        summary=f"Signal from {source}: {title}",
        source=source,
        confidence=confidence,
        timestamp=datetime.now() - timedelta(hours=hours_ago),
    )

def main():
    console.print(Panel.fit(
        "[bold blue]📡 Agent Constitution[/bold blue]\n"
        "[dim]Signal Pipeline Demo[/dim]",
        border_style="blue"
    ))

    # 1. Create signals from multiple sources
    console.print("\n[bold]Step 1: Ingesting signals from multiple sources[/bold]")

    signals = [
        make_signal("tier1", "bullish", "AI infrastructure demand surging", "rss_techcrunch", 0.85),
        make_signal("tier1", "bullish", "AI infrastructure demand surging", "kol_twitter", 0.78),  # same topic, different source
        make_signal("tier1", "bullish", "AI infrastructure demand surging", "institutional_gs", 0.91),  # 3rd source
        make_signal("tier2", "bearish", "Enterprise AI budget cuts Q1", "rss_bloomberg", 0.72),
        make_signal("tier2", "bearish", "Enterprise AI budget cuts Q1", "kol_twitter", 0.68),  # same topic
        make_signal("tier1", "neutral", "Model capabilities plateauing debate", "rss_techcrunch", 0.60),
        make_signal("tier2", "bullish", "New model release imminent", "rss_openai", 0.55),  # low confidence
        make_signal("tier1", "bullish", "AI infrastructure demand surging", "rss_techcrunch", 0.80, hours_ago=1),  # same source dup
    ]

    pool = SignalPool(dedup_window_hours=24)
    added = 0
    for s in signals:
        if pool.ingest(s):
            added += 1

    console.print(f"  Attempted: {len(signals)} signals")
    console.print(f"  Ingested (after dedup): [green]{added}[/green]")
    console.print(f"  Deduplicated (same source): [yellow]{len(signals) - added}[/yellow]")

    # 2. Cross-reference
    console.print("\n[bold]Step 2: Cross-referencing (signals confirmed by 2+ sources)[/bold]")
    xref = pool.cross_reference()

    table = Table(title=f"Cross-Referenced Signals ({len(xref)} total)", show_header=True)
    table.add_column("Direction", style="cyan", width=10)
    table.add_column("Title", style="white", width=45)
    table.add_column("Source", style="dim", width=20)
    table.add_column("Confidence", style="green", width=12)
    for s in xref:
        color = "green" if s.direction == "bullish" else "red" if s.direction == "bearish" else "yellow"
        table.add_row(f"[{color}]{s.direction}[/{color}]", s.title[:44], s.source, f"{s.confidence:.0%}")
    console.print(table)

    # 3. Actionable signals
    console.print("\n[bold]Step 3: Actionable signals (confidence ≥ 65%)[/bold]")
    actionable = pool.get_actionable(min_confidence=0.65)

    table2 = Table(title=f"Actionable Signals ({len(actionable)} total, sorted by confidence)", show_header=True)
    table2.add_column("Tier", style="cyan", width=8)
    table2.add_column("Direction", width=10)
    table2.add_column("Title", style="white", width=45)
    table2.add_column("Confidence", style="green", width=12)
    for s in actionable:
        color = "green" if s.direction == "bullish" else "red" if s.direction == "bearish" else "yellow"
        table2.add_row(s.tier, f"[{color}]{s.direction}[/{color}]", s.title[:44], f"{s.confidence:.0%}")
    console.print(table2)

    console.print(Panel.fit(
        f"[bold green]✓ Signal Pipeline Demo Complete[/bold green]\n"
        f"[dim]Ingested {added} unique signals → {len(xref)} cross-validated → {len(actionable)} actionable[/dim]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
