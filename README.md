# 🏛️ Agent Constitution

**Production-grade multi-agent governance framework
with adversarial debate, epistemic honesty, and retrospective calibration.**

> Most multi-agent frameworks focus on making agents talk.
> This one focuses on making agents **think honestly**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/your-org/agent-constitution/ci.yml?label=tests)](https://github.com/your-org/agent-constitution/actions)

---

## The Problem

Multi-agent systems suffer from confirmation bias.
Agents reinforce each other's hallucinations. Nobody says "I don't know."
There's no mechanism to check if past judgments were right.

**Agent Constitution solves this with three mechanisms:**

## Three Core Mechanisms

### 1. 🏛️ Constitutional Governance

Every agent injects epistemic rules at the system-prompt level. Speculation must be tagged. Bad news gets promoted. Confidence is always 0.0–1.0.

Each agent has its own `SOUL.md` — a human-readable markdown file defining identity, values, and hard limits. No more rules buried in Python strings.

```markdown
# Analyst — Nate

## Mission
Evaluate opportunities with calibrated, multi-dimensional assessments.

## Hard Constraints
- Inherits all rules from ../../CONSTITUTION.md
- Must tag any market size estimate above $10B as [SPECULATION] unless sourced
- Always present the bear case before the bull case
```

### 2. ⚔️ Adversarial Debate

Controversial assessments (score ≥ 32/40) trigger structured debates.
A challenger raises three specific challenges. The defender rebuts each.
A judge renders a verdict with a score delta and audit trail.

```python
debate = Debate(challenger=critic, defender=analyst, judge=judge)
result = debate.run(topic="Should we build an AI code review tool?")

print(result.verdict)        # "proceed_with_caution"
print(result.score_delta)    # -3
print(result.audit_trail)    # Full debate record
```

### 3. 🔄 Retrospective Calibration

Periodic lookback verifies past predictions.
Did the risks materialize? Was the optimism justified?
Agents earn (or lose) credibility over time.

```python
retro = Retrospective()
pred = retro.record_prediction("analyst", "Market will grow 3x", confidence=0.75)
# ... time passes ...
retro.verify(pred.id, outcome="correct")  # credibility +0.05
retro.get_credibility("analyst")          # 1.05
```

---

## Quick Start

**Zero config. No API key needed.**

```bash
git clone https://github.com/your-org/agent-constitution
cd agent-constitution
pip install -e .
python examples/demo_debate.py
```

```
🏛️ Agent Constitution
Adversarial Debate Demo — No API key required

Step 1: Initializing agents with Constitutional rules
  ✓ analyst (Nate) — MockAdapter
  ✓ critic (Eve) — MockAdapter
  ✓ judge (Solomon) — MockAdapter

Step 2: Analyst evaluates opportunity
  Total Score: 35/40
  Confidence: 75%

Step 3: Score 35 ≥ 32 → Triggering Adversarial Debate
  ⚔️  Debate triggered!

Step 4: Debate Results
  Verdict: proceed_with_caution
  Score Delta: -3
  Final Score: 35 → 32
```

## Use Real LLMs

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python examples/demo_api.py
```

Or in code:

```python
from constitution import BaseAgent, Constitution, Debate
from adapters import AnthropicAPIAdapter

rules = Constitution.default()

analyst = BaseAgent(
    role="analyst",
    goal="Evaluate business opportunities",
    constitution=rules,
    adapter=AnthropicAPIAdapter(model="claude-haiku-4-5-20251001")
)

critic = BaseAgent(
    role="critic",
    goal="Challenge assumptions and identify risks",
    constitution=rules,
    adapter=AnthropicAPIAdapter(model="claude-haiku-4-5-20251001")
)

debate = Debate(challenger=critic, defender=analyst, judge=...)
result = debate.run(topic="Should we build an AI code review tool?")
print(result.verdict)      # "proceed_with_caution"
print(result.score_delta)  # -3
```

---

## Architecture

```
adapters/          LLM backends (MockAdapter, AnthropicAPI, ClaudeAPI)
constitution/
  base_agent.py    BaseAgent with constitution injection
  constitution.py  Constitution loader (SOUL.md / YAML / default)
  debate.py        Adversarial debate engine
  signal.py        Signal schema
  signal_pool.py   Signal dedup, cross-reference, actionable filtering
  cost_guard.py    Token budget monitoring
  trace.py         RunTrace audit trail
  retrospective.py Prediction recording + calibration
examples/
  demo_debate.py   Zero-config debate demo
  demo_signal.py   Signal pipeline demo
  demo_api.py      Real LLM demo
```

Each agent reads from `SOUL.md`, not Python code:

```
CONSTITUTION.md           ← Shared epistemic rules (injected to all agents)
examples/agents/
  analyst/SOUL.md         ← Analyst identity, values, constraints
  critic/SOUL.md          ← Critic persona, debate role
  judge/SOUL.md           ← Judge impartiality rules
```

---

## Why Not CrewAI / MetaGPT / LangGraph?

| Dimension | CrewAI | MetaGPT | LangGraph | Agent Constitution |
|-----------|--------|---------|-----------|-------------------|
| Agent coordination | ✅ | ✅ | ✅ | ✅ |
| Role definitions | ✅ | ✅ | ✅ | ✅ |
| **Epistemic honesty** | ❌ | ❌ | ❌ | ✅ |
| **Adversarial debate** | ❌ | ❌ | ❌ | ✅ |
| **Retrospective calibration** | ❌ | ❌ | ❌ | ✅ |
| **Human-readable SOUL.md** | ❌ | ❌ | ❌ | ✅ |
| Cost tracking | ❌ | ❌ | ❌ | ✅ |
| MockAdapter (no API key) | ❌ | ❌ | ❌ | ✅ |

> These frameworks solve *how* agents communicate.
> Agent Constitution solves *whether agents are thinking honestly*.

---

## Supported LLM Backends

| Adapter | Requires | Use case |
|---------|----------|----------|
| `MockAdapter` | Nothing | Testing, demos, CI |
| `AnthropicAPIAdapter` | `ANTHROPIC_API_KEY` | Production with API billing |
| `ClaudeCLIAdapter` | Claude Max subscription | Local dev with Claude CLI |

Add your own by subclassing `LLMAdapter`:

```python
from adapters import LLMAdapter, LLMResponse

class MyAdapter(LLMAdapter):
    def call(self, messages, system_prompt="", tools=None, max_tokens=4096) -> LLMResponse:
        # Your implementation
        ...
```

---

## Roadmap

**v1 (current)** — Governance layer
- Constitutional agent governance via `SOUL.md`
- Adversarial debate engine (challenger/defender/judge)
- Retrospective calibration
- Multiple LLM backends

**v2 — MCP Integration**
- Agents connect to external tools via Model Context Protocol
- Replace hardcoded tool lists with dynamic MCP server discovery

**v3 — A2A Support**
- Standard agent-to-agent communication via Agent-to-Agent Protocol
- Cross-framework collaboration

> Why governance first? Because MCP/A2A solve *how* agents communicate.
> Agent Constitution solves *whether agents are thinking honestly*.
> Nobody else is doing the second part.

---

## License

MIT — see [LICENSE](LICENSE)
