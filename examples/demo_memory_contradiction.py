#!/usr/bin/env python3
"""
POC: Memory Contradiction Resolution via Adversarial Debate

SuperMemory resolves contradictions silently (black-box).
We debate them openly — with full audit trail.

Run:  python examples/demo_memory_contradiction.py
No API key required.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapters.base import LLMAdapter, LLMResponse
from constitution import BaseAgent, Constitution, Debate
from constitution.retrospective import Retrospective

console = Console()


# ---------------------------------------------------------------------------
# Memory Store — simple in-memory store with contradiction detection
# ---------------------------------------------------------------------------

@dataclass
class Memory:
    id: int
    agent_role: str
    topic: str
    claim: str
    confidence: float
    timestamp: str  # ISO format
    status: str = "active"  # active, superseded, debated


class MemoryStore:
    def __init__(self):
        self.memories: list[Memory] = []
        self._next_id = 1

    def add(self, agent_role: str, topic: str, claim: str,
            confidence: float, timestamp: str) -> Memory:
        mem = Memory(
            id=self._next_id,
            agent_role=agent_role,
            topic=topic,
            claim=claim,
            confidence=confidence,
            timestamp=timestamp,
        )
        self._next_id += 1
        self.memories.append(mem)
        return mem

    def find_contradictions(self) -> list[tuple[Memory, Memory]]:
        """Find memories on the same topic from different agents/times."""
        by_topic: dict[str, list[Memory]] = {}
        for m in self.memories:
            if m.status == "active":
                by_topic.setdefault(m.topic, []).append(m)
        contradictions = []
        for topic, mems in by_topic.items():
            if len(mems) >= 2:
                # pair oldest with newest
                sorted_mems = sorted(mems, key=lambda m: m.timestamp)
                contradictions.append((sorted_mems[0], sorted_mems[-1]))
        return contradictions


# ---------------------------------------------------------------------------
# Memory-aware MockAdapter — understands contradiction debate prompts
# ---------------------------------------------------------------------------

class MemoryDebateMockAdapter(LLMAdapter):
    """MockAdapter specialized for memory contradiction debates."""

    def __init__(self, side: str = "neutral"):
        """side: 'old' (defends old memory), 'new' (defends new memory), 'neutral' (judge)"""
        self.side = side

    def call(self, messages, system_prompt="", tools=None, max_tokens=4096):
        user_text = " ".join(
            msg.get("content", "") for msg in messages if msg.get("role") == "user"
        ).lower()

        if "generate" in user_text and "challenges" in user_text:
            content = self._challenger_response(messages)
        elif "provide a defense" in user_text or "defend" in user_text:
            content = self._defender_response(messages)
        elif "verdict" in user_text and "evaluate" in user_text:
            content = self._judge_response(messages)
        else:
            content = json.dumps({"response": "Memory noted."})

        return LLMResponse(
            content=content,
            input_tokens=200,
            output_tokens=150,
            cost_usd=0.0,
            duration_ms=50,
        )

    def _challenger_response(self, messages) -> str:
        return json.dumps({
            "challenges": [
                "新記憶來自一週前的資料，但舊記憶是基於三個月的持續觀察。"
                "單次觀察的時間跨度不足以推翻長期趨勢。",
                "兩條記憶的資料來源可信度不同——舊記憶引用了一手數據，"
                "新記憶引用的是二手報導，存在資訊衰減風險。",
                "如果直接覆蓋舊記憶，會丟失歷史脈絡。應該保留兩條記憶"
                "並標注時間線，而非簡單地以新替舊。",
            ],
            "severity": "high",
        })

    def _defender_response(self, messages) -> str:
        return json.dumps({
            "defenses": [
                "時間跨度短不代表不準確。新記憶雖然只有一週的觀察，"
                "但它捕捉到了一個 regime change——市場結構已經改變，"
                "舊的長期趨勢不再適用。",
                "資料來源的差異已被考慮。新記憶的二手報導交叉驗證了"
                "三個獨立來源，信號一致性高於舊記憶的單一一手來源。",
                "同意不應簡單覆蓋。建議：將舊記憶標記為 'superseded'，"
                "新記憶標記為 'active'，保留完整歷史鏈——"
                "這正是我們比 SuperMemory 更透明的地方。",
            ],
            "confidence": 0.78,
        })

    def _judge_response(self, messages) -> str:
        return json.dumps({
            "verdict": "proceed_with_caution",
            "score_delta": -2,
            "reasoning": (
                "新記憶的證據較新且經過交叉驗證，但舊記憶的長期觀察仍有參考價值。"
                "判決：採納新記憶為 active，舊記憶降級為 superseded 但不刪除。"
                "兩條記憶均保留在審計紀錄中，任何人都可以回溯這次判決的完整辯論過程。"
                "這就是公開辯論 vs. 黑盒靜默覆蓋的核心差異。"
            ),
            "confidence": 0.82,
        })


# ---------------------------------------------------------------------------
# Main: 模擬記憶矛盾 → 觸發辯論 → 公開解決
# ---------------------------------------------------------------------------

def main():
    console.print(Panel.fit(
        "[bold blue]Agent Constitution — Memory Contradiction POC[/bold blue]\n"
        "[dim]SuperMemory resolves silently. We debate openly.[/dim]",
        border_style="blue",
    ))

    # ── Step 1: 建立記憶庫，灌入矛盾的記憶 ──
    console.print("\n[bold cyan]Step 1: 建立記憶庫[/bold cyan]")
    store = MemoryStore()

    m1 = store.add(
        agent_role="analyst",
        topic="enterprise_ai_adoption_rate",
        claim="企業 AI 採用率持續線性成長，預計 2026 Q3 達到 45%。基於過去 3 個月的穩定上升趨勢。",
        confidence=0.85,
        timestamp="2026-01-15T10:00:00",
    )
    m2 = store.add(
        agent_role="signal_monitor",
        topic="enterprise_ai_adoption_rate",
        claim="企業 AI 採用率在 2026 Q1 出現拐點，因監管收緊導致成長放緩至 28%，預計 Q3 僅達 32%。",
        confidence=0.72,
        timestamp="2026-03-22T14:30:00",
    )

    table = Table(title="Memory Store", box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Agent", style="cyan")
    table.add_column("時間", style="green")
    table.add_column("信心", style="yellow")
    table.add_column("內容")
    table.add_row(str(m1.id), m1.agent_role, m1.timestamp[:10], f"{m1.confidence:.0%}", m1.claim[:50] + "...")
    table.add_row(str(m2.id), m2.agent_role, m2.timestamp[:10], f"{m2.confidence:.0%}", m2.claim[:50] + "...")
    console.print(table)

    # ── Step 2: 偵測矛盾 ──
    console.print("\n[bold cyan]Step 2: 偵測矛盾[/bold cyan]")
    contradictions = store.find_contradictions()
    if not contradictions:
        console.print("  沒有發現矛盾。")
        return

    old_mem, new_mem = contradictions[0]
    console.print(f"  [red]矛盾發現！[/red] Topic: [bold]{old_mem.topic}[/bold]")
    console.print(f"  舊記憶 (#{old_mem.id}, {old_mem.agent_role}): {old_mem.claim[:60]}...")
    console.print(f"  新記憶 (#{new_mem.id}, {new_mem.agent_role}): {new_mem.claim[:60]}...")

    # ── Step 3: 觸發公開辯論 ──
    console.print("\n[bold cyan]Step 3: 觸發 Adversarial Debate[/bold cyan]")
    console.print("  [yellow]SuperMemory 會在這裡靜默覆蓋舊記憶。我們不會。[/yellow]")

    rules = Constitution.default()

    # Challenger: 質疑新記憶，捍衛舊記憶
    challenger = BaseAgent(
        role="memory_challenger",
        goal="Challenge the new memory and defend the established knowledge",
        persona="Skeptical of recency bias. Defends long-term observations.",
        adapter=MemoryDebateMockAdapter(side="old"),
        constitution=rules,
    )
    # Defender: 捍衛新記憶
    defender = BaseAgent(
        role="memory_defender",
        goal="Defend the new memory with evidence and reasoning",
        persona="Evidence-driven. Argues for updating beliefs when data supports it.",
        adapter=MemoryDebateMockAdapter(side="new"),
        constitution=rules,
    )
    # Judge: 公正裁決
    judge = BaseAgent(
        role="memory_judge",
        goal="Evaluate which memory should be retained and how",
        persona="Impartial. Weighs evidence quality, recency, and source reliability.",
        adapter=MemoryDebateMockAdapter(side="neutral"),
        constitution=rules,
    )

    console.print("  memory_challenger — 捍衛舊記憶")
    console.print("  memory_defender — 捍衛新記憶")
    console.print("  memory_judge — 公正裁決")

    debate_topic = (
        f"Memory Contradiction on '{old_mem.topic}':\n"
        f"  OLD ({old_mem.timestamp[:10]}, {old_mem.agent_role}, confidence={old_mem.confidence}): "
        f"{old_mem.claim}\n"
        f"  NEW ({new_mem.timestamp[:10]}, {new_mem.agent_role}, confidence={new_mem.confidence}): "
        f"{new_mem.claim}\n"
        f"Which memory should be the active belief? Should the old one be deleted or preserved as history?"
    )

    # ── Step 4: 逐步展示完整對話 ──
    console.print("\n[bold cyan]Step 4: 辯論過程——逐步對話記錄[/bold cyan]")

    # --- Round 1: System → Challenger ---
    console.print(Panel(
        f"[dim]Topic:[/dim] {debate_topic}\n\n"
        "[dim]Generate exactly 3 specific challenges to this assessment.[/dim]",
        title="[bold yellow]Round 1 — System → Challenger (memory_challenger)[/bold yellow]",
        subtitle="[dim]prompt sent to challenger agent[/dim]",
        border_style="yellow",
    ))

    debate = Debate(challenger=challenger, defender=defender, judge=judge)
    result = debate.run(topic=debate_topic, initial_score=35)

    console.print(Panel(
        "\n".join(f"[red]{i}.[/red] {c}" for i, c in enumerate(result.challenges, 1)),
        title="[bold red]Round 1 — Challenger Response[/bold red]",
        subtitle="[dim]memory_challenger 質疑新記憶，捍衛舊記憶[/dim]",
        border_style="red",
    ))

    # --- Round 2: System → Defender ---
    challenges_text = "\n".join(f"  {i}. {c}" for i, c in enumerate(result.challenges, 1))
    console.print(Panel(
        f"[dim]Topic:[/dim] {debate_topic}\n\n"
        f"[dim]Challenges raised:[/dim]\n{challenges_text}\n\n"
        "[dim]Provide a defense for each challenge.[/dim]",
        title="[bold yellow]Round 2 — System → Defender (memory_defender)[/bold yellow]",
        subtitle="[dim]prompt sent to defender agent, includes challenger's output[/dim]",
        border_style="yellow",
    ))

    console.print(Panel(
        "\n".join(f"[green]{i}.[/green] {d}" for i, d in enumerate(result.defenses, 1)),
        title="[bold green]Round 2 — Defender Response[/bold green]",
        subtitle="[dim]memory_defender 捍衛新記憶，逐條回擊[/dim]",
        border_style="green",
    ))

    # --- Round 3: System → Judge ---
    console.print(Panel(
        f"[dim]Topic:[/dim] {debate_topic}\n\n"
        f"[dim]Challenges:[/dim] (3 items from challenger)\n"
        f"[dim]Defenses:[/dim] (3 items from defender)\n\n"
        f"[dim]Evaluate the debate and return verdict.[/dim]",
        title="[bold yellow]Round 3 — System → Judge (memory_judge)[/bold yellow]",
        subtitle="[dim]prompt sent to judge, includes both sides[/dim]",
        border_style="yellow",
    ))

    console.print(Panel(
        f"[bold]Verdict:[/bold] [magenta]{result.verdict}[/magenta]\n"
        f"[bold]Score Delta:[/bold] {result.score_delta:+d}\n"
        f"[bold]Reasoning:[/bold]\n{result.reasoning}",
        title="[bold magenta]Round 3 — Judge Verdict[/bold magenta]",
        subtitle="[dim]memory_judge 綜合雙方論點做出裁決[/dim]",
        border_style="magenta",
    ))

    # ── Step 5: 執行裁決 + 更新 credibility ──
    console.print("\n[bold cyan]Step 5: 執行裁決[/bold cyan]")

    # Update memory status based on verdict
    old_mem.status = "superseded"
    new_mem.status = "active"

    console.print(f"  記憶 #{old_mem.id} → [dim]superseded[/dim]（保留歷史，不刪除）")
    console.print(f"  記憶 #{new_mem.id} → [green]active[/green]（當前有效信念）")

    # Update credibility scores
    retro = Retrospective()
    p_old = retro.record_prediction(old_mem.agent_role, old_mem.claim, old_mem.confidence)
    p_new = retro.record_prediction(new_mem.agent_role, new_mem.claim, new_mem.confidence)

    retro.verify(p_old.id, "incorrect")
    retro.verify(p_new.id, "correct")

    console.print("\n  Credibility 更新：")
    for role, score in retro.agent_credibility.items():
        color = "green" if score >= 1.0 else "red"
        console.print(f"    {role}: [{color}]{score:.2f}[/{color}]")

    # ── Step 6: 審計紀錄 ──
    console.print("\n[bold cyan]Step 6: 審計紀錄（vs SuperMemory 黑盒）[/bold cyan]")

    audit_table = Table(title="Debate Audit Trail — 完整可回溯", box=box.ROUNDED)
    audit_table.add_column("階段", style="cyan", width=8)
    audit_table.add_column("角色", style="yellow", width=12)
    audit_table.add_column("內容（解碼後）", ratio=1)

    stage_names = ["質疑", "辯護", "裁決"]
    for i, entry in enumerate(result.audit_trail):
        role = entry.get("role", "?")
        raw = entry.get("content", "")
        # Decode JSON to show readable content
        try:
            data = json.loads(raw)
            if "challenges" in data:
                decoded = "\n".join(f"  {j+1}. {c}" for j, c in enumerate(data["challenges"]))
            elif "defenses" in data:
                decoded = "\n".join(f"  {j+1}. {d}" for j, d in enumerate(data["defenses"]))
            elif "verdict" in data:
                decoded = f"  Verdict: {data['verdict']}\n  Delta: {data.get('score_delta', 0):+d}\n  {data.get('reasoning', '')[:120]}"
            else:
                decoded = raw[:120]
        except (json.JSONDecodeError, TypeError):
            decoded = raw[:120]
        stage = stage_names[i] if i < len(stage_names) else f"Step {i+1}"
        audit_table.add_row(stage, role, decoded)
    console.print(audit_table)

    # ── Summary ──
    console.print(Panel.fit(
        "[bold green]POC Complete[/bold green]\n\n"
        "[bold]SuperMemory 做法：[/bold] 靜默覆蓋，沒有理由，沒有紀錄\n"
        "[bold]我們的做法：[/bold]\n"
        "  1. 偵測矛盾\n"
        "  2. 公開辯論（質疑 → 辯護 → 裁決）\n"
        "  3. 保留完整歷史 + 審計紀錄\n"
        "  4. 更新 agent 可信度分數\n"
        "  5. 任何人都能回溯每一次記憶變更的「為什麼」\n\n"
        "[dim]No API key used. All agents use MockAdapter.[/dim]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
