# Agent Constitution

**Multi-agent governance for teams that want more than orchestration.**
**Adversarial debate, epistemic honesty, retrospective calibration.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests: 157 passed](https://img.shields.io/badge/tests-157%20passed-brightgreen.svg)]()

```mermaid
flowchart LR
    A["🔍 Analyst<br/>scores idea<br/><b>35/40</b>"] -->|"score ≥ 32"| B["⚔️ Critic<br/>3 challenges"]
    B --> C["🛡️ Defender<br/>3 rebuttals"]
    C --> D["⚖️ Judge<br/>verdict + delta"]
    D --> E["📊 Governance<br/>Score 7.8/10"]
    E -.->|"30 days later"| F["🔄 Retro<br/>was judge right?<br/>credibility ±0.05"]

    style A fill:#2563eb,color:#fff,stroke:none
    style B fill:#dc2626,color:#fff,stroke:none
    style C fill:#2563eb,color:#fff,stroke:none
    style D fill:#7c3aed,color:#fff,stroke:none
    style E fill:#059669,color:#fff,stroke:none
    style F fill:#d97706,color:#fff,stroke:none
```

Agent Constitution helps agent teams do three things most frameworks leave to you:

- encode epistemic rules in markdown instead of hidden prompt strings
- force high-stakes outputs through structured adversarial review
- track whether past judgments were actually right

```
BEFORE                                    AFTER Agent Constitution
─────────────────────────────────────     ─────────────────────────────────────
Analyst: "Great opportunity!               Analyst: "Score: 35/40, confidence: 0.7"
         Score: 42/50"                     Score >= 32 → DEBATE TRIGGERED
Critic:  "I agree, looks promising."       Critic:  "Market size is [SPECULATION].
→ Ship it!                                          Competitor has 3x more runway."
→ 3 months later: competitor raised        Analyst: "Fair — revised to 28/50"
  $50M, market was 10x smaller             Judge:   "proceed_with_caution, delta: -7"
                                           30 days later: Retrospective confirms
                                             challenger was RIGHT. Credibility +0.05
```

> Other frameworks solve *how* agents communicate.
> Agent Constitution solves *whether agents are thinking honestly*.

---

## Quick Start

**One command. Zero config. No API key.**

```bash
pip install agent-constitution
ac debate "Should we build an AI code review tool?"
```

```
Agent Constitution  |  Adversarial Debate
Adapter: mock

1. Agents initialized
   analyst  | mock
   critic   | mock
   judge    | mock

2. Analyst evaluates: Should we build an AI code review tool?
   Score: 35/40
   Confidence: 75%

3. Score 35 >= 32 — debate triggered
   Challenges: 3 raised
   Defenses:   3 filed
   Verdict:    proceed_with_caution
   Delta:      -3
   Final:      35 -> 32

5. Audit trail (3 steps)
```

**Use real LLMs:**

```bash
# Anthropic API
export ANTHROPIC_API_KEY=sk-ant-...
ac debate "topic" --adapter anthropic

# Local models (free, private)
ollama serve
ac debate "topic" --adapter ollama --model llama3

# Claude CLI
ac debate "topic" --adapter claude --model sonnet
```

**What you get right away:**

- a zero-config debate demo with no API key
- strict schema validation for challenger, defender, and judge output
- a provisional governance score computed from recorded runs
- support for Mock, Anthropic, Ollama, and Claude CLI backends

---

## Three Core Mechanisms

### 1. Constitutional Governance

Every agent injects epistemic rules at the system-prompt level.
Speculation must be tagged `[SPECULATION]`. Bad news gets promoted. Confidence is always 0.0-1.0.

Each agent has its own `SOUL.md`:

```markdown
# Analyst — Nate

## Mission
Evaluate opportunities with calibrated, multi-dimensional assessments.

## Hard Constraints
- Inherits all rules from ../../CONSTITUTION.md
- Must tag any market size estimate above $10B as [SPECULATION] unless sourced
- Always present the bear case before the bull case
```

No more rules buried in Python strings. Edit a markdown file to change how an agent thinks.

### 2. Adversarial Debate

Controversial assessments (score >= 32/40) trigger structured debates.
A challenger raises three specific challenges. The defender rebuts each.
A judge renders a verdict with a score delta and full audit trail.

```python
from constitution import BaseAgent, Constitution, Debate

rules = Constitution.default()
analyst  = BaseAgent(role="analyst",  goal="Evaluate opportunities", constitution=rules)
critic   = BaseAgent(role="critic",   goal="Challenge assumptions",  constitution=rules)
judge    = BaseAgent(role="judge",    goal="Render fair verdicts",   constitution=rules)

debate = Debate(challenger=critic, defender=analyst, judge=judge)
result = debate.run(topic="Should we build an AI code review tool?")

result.verdict       # "proceed_with_caution"
result.score_delta   # -3
result.challenges    # ["Market is more competitive than assessed", ...]
result.audit_trail   # Full debate record
```

Every LLM response goes through **separate validation** before it's trusted.
The debate engine uses explicit schema validators (`_validate_challenges`, `_validate_defenses`, `_validate_verdict`) and rejects malformed debate output by default. If you want legacy fallback behavior, opt into `strict_validation=False`.

### 3. Retrospective Calibration

Periodic lookback verifies past predictions.
Did the risks materialize? Was the optimism justified?
Agents earn (or lose) credibility over time.

```python
from constitution import Retrospective

retro = Retrospective()
pred = retro.record_prediction("analyst", "Market will grow 3x", confidence=0.75)
# ... time passes ...
retro.verify(pred.id, outcome="correct")  # credibility +0.05
retro.get_credibility("analyst")          # 1.05
```

### 4. Lifecycle Hooks

Plug into any point in the governance pipeline without modifying core code.

```python
from constitution import BaseAgent, Debate, DebateHook, AgentHook

class AuditHook(DebateHook):
    """Log every debate step to an external system."""
    def post_verdict(self, result):
        send_to_datadog(result.audit_trail)
        return result

class CostApprovalHook(AgentHook):
    """Allow cost overruns instead of crashing."""
    def on_cost_limit(self, agent, cost_usd, total_cost):
        return "warn"  # "raise" (default) | "warn" | "allow"

# Hooks compose — pass multiple, they chain in order
debate = Debate(challenger, defender, judge, hooks=[AuditHook()])
agent = BaseAgent(role="analyst", goal="Evaluate", hooks=[CostApprovalHook()])
```

Available hook points:

| Hook | When | Can modify |
|------|------|-----------|
| `AgentHook.pre_call` | Before LLM call | Prompt |
| `AgentHook.post_call` | After LLM call | Response content |
| `AgentHook.on_cost_limit` | Cost would exceed limit | Raise / warn / allow |
| `DebateHook.pre_challenge` | Before challenger runs | Topic |
| `DebateHook.post_challenge` | After challenge validation | Challenges list |
| `DebateHook.pre_defense` | Before defender runs | Challenges |
| `DebateHook.post_defense` | After defense validation | Defenses list |
| `DebateHook.pre_verdict` | Before judge runs | Abort (raise) |
| `DebateHook.post_verdict` | After verdict | Full result |
| `DebateHook.on_validation_error` | Schema validation fails | Raise / fallback |

---

## Governance Score

Measure how well-governed your agent system is from recorded CLI runs:

```bash
ac score
```

```
Dimension                  Score   Weight
─────────────────────────  ─────   ──────
Epistemic Honesty          8/10    25%
Constitutional Compliance  7/10    25%
Debate Rigor               6/10    20%
Calibration Accuracy       7/10    15%
Audit Completeness         9/10    15%

Weighted Governance Score: 7.8/10
```

The governance score tracks five dimensions: epistemic honesty, constitutional compliance, debate rigor, calibration accuracy, and audit completeness. `ac debate` records governance data to `workspace/governance_history.json`, and `ac score` aggregates those real runs instead of printing placeholders. Until you verify retrospectives, the report stays explicitly **uncalibrated** and should be treated as a provisional operational snapshot rather than a final grade.

---

## Why Agent Constitution?

### Why Now: The Governance Gap

2026 is the year of **agent governance**. Singapore launched the [world's first Agentic AI Governance Framework](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf) at WEF 2026. Gartner predicts 40% of enterprise apps will feature AI agents by year-end. Everyone is writing governance *policy papers*. Nobody has shipped the *code*.

Agent Constitution is that code.

### Framework Comparison

| Dimension | CrewAI | LangGraph | AutoGen | **Agent Constitution** |
|-----------|--------|-----------|---------|----------------------|
| Agent coordination | Yes | Yes | Yes | Debate-scoped |
| **Adversarial debate** | - | - | Conversational | **Structured + schema-validated** |
| **Retrospective calibration** | - | - | - | **Yes** |
| **Human-readable SOUL.md** | - | - | - | **Yes** |
| Team governance | - | - | Limited | **Core feature** |
| Cost tracking | Via LiteLLM | Via callbacks | - | **Built-in** |

> Other frameworks solve *how* agents communicate. **We solve whether they're thinking honestly.**

---

## Personal Agent Mode

Not just for multi-agent teams. Works for individuals too.

```python
from constitution import BaseAgent, Constitution
from adapters import OllamaAdapter

personal = BaseAgent(
    role="personal_assistant",
    goal="Help me think clearly",
    constitution=Constitution.from_soul_md("my_soul.md"),
    adapter=OllamaAdapter(model="llama3")  # Free, local
)
```

Same constitutional governance. Epistemic honesty, self-challenge, calibrated confidence.

```bash
python examples/demo_personal.py
```

---

## Supported LLM Backends

| Adapter | Requires | Use case |
|---------|----------|----------|
| `MockAdapter` | Nothing | Testing, demos, CI |
| `AnthropicAPIAdapter` | `ANTHROPIC_API_KEY` | Production with API billing |
| `ClaudeCLIAdapter` | Claude Max subscription | Local dev with Claude CLI |
| `OllamaAdapter` | [Ollama](https://ollama.com) running locally | **Free**, private, any open model |

Add your own:

```python
from adapters import LLMAdapter, LLMResponse

class MyAdapter(LLMAdapter):
    def call(self, messages, system_prompt="", tools=None, max_tokens=4096) -> LLMResponse:
        ...
```

---

## Core Modules

| Module | What it does |
|--------|-------------|
| `constitution/debate.py` | Adversarial debate engine + schema validators |
| `constitution/retrospective.py` | Prediction tracking + credibility calibration |
| `constitution/governance_score.py` | 5-dimension governance scoring from recorded runs |
| `constitution/cost_guard.py` | Token budget enforcement with hard limits |
| `constitution/base_agent.py` | BaseAgent with constitution injection |
| `constitution/hooks.py` | AgentHook + DebateHook lifecycle system |
| `constitution/cli.py` | `ac` CLI entry point (`ac debate`, `ac score`) |
| `adapters/mock.py` | Debate-aware mock adapter (zero API key) |
| `adapters/anthropic_api.py` | Anthropic API adapter |
| `adapters/ollama.py` | Ollama local models adapter |
| `adapters/claude_cli.py` | Claude CLI adapter |

## Tech Stack

| Tech | Role |
|------|------|
| Python 3.11+ | Runtime |
| [Rich](https://github.com/Textualize/rich) | CLI formatting and tables |
| PyYAML | Constitution / SOUL.md loading |
| httpx | HTTP client for Ollama and API adapters |
| pytest | 138 tests, zero API keys required |
| ruff | Linting and formatting |

---

## Architecture

```
CONSTITUTION.md              Shared epistemic rules (injected to all agents)
examples/agents/
  analyst/SOUL.md            Analyst identity, values, constraints
  critic/SOUL.md             Critic persona, debate role
  judge/SOUL.md              Judge impartiality rules

adapters/
  mock.py                    Debate-aware mock (zero API key)
  anthropic_api.py           Anthropic API
  claude_cli.py              Claude CLI
  ollama.py                  Ollama local models

constitution/
  base_agent.py              BaseAgent with constitution injection
  constitution.py            Constitution loader (SOUL.md / YAML / default)
  debate.py                  Adversarial debate engine + schema validators
  signal.py + signal_pool.py Signal dedup, cross-reference, filtering
  cost_guard.py              Token budget monitoring (pre-check, not post-record)
  trace.py                   RunTrace audit trail
  retrospective.py           Prediction recording + credibility calibration
  governance_score.py        Five-dimension governance scoring
  cli.py                     `ac` CLI
```

### Design Principles

- **Generator/Validator separation**: Every LLM response is generated, then validated by a separate function. The debate engine uses `_validate_challenges()`, `_validate_defenses()`, and `_validate_verdict()` and raises `DebateValidationError` on malformed debate output by default.
- **Constitution as prompt injection**: Rules live in markdown files, not Python strings. `SOUL.md` files are human-readable and version-controllable.
- **Cost guard with hard limit**: Budget limits are enforced after each LLM call. When cumulative cost would exceed the hard limit, the guard raises `CostLimitExceeded` and halts further calls.

---

## Origin

Extracted from a personal intelligence system with 21 specialized agents that has been running daily for months. The constitutional governance, adversarial debate, and retrospective calibration mechanisms were battle-tested in production before being extracted into this framework.

## Research Foundation

Multi-agent debate improves factual reasoning and reduces hallucination ([Du et al., 2023](https://arxiv.org/abs/2305.14325)). Heterogeneous agents with dynamic debate mechanisms outperform homogeneous approaches ([FREE-MAD, 2025](https://arxiv.org/abs/2509.11035)).

Agent Constitution draws on these findings to build a practical, installable governance framework.

---

## Roadmap

**v1 (current)** — Multi-Agent Governance Harness
- Constitutional agent governance via `SOUL.md`
- Adversarial debate engine (challenger/defender/judge)
- Retrospective calibration with credibility tracking
- Personal agent mode
- 4 LLM backends: Mock, Anthropic, Claude CLI, Ollama
- `ac` CLI + Governance Score

**v1.5 — Runtime Governance**
- Per-turn token budgets (not just session-level hard limits)
- Permission gates on adapter calls (sub-agents get restricted scope)
- Auto-compaction with semantic retention for long-running sessions
- Consolidation engine: background learning extraction during idle time

**v2 — Agent Growth Engine**
- Skill auto-creation from experience (with adversarial review before promotion)
- Dream/consolidation cycle: session end → extract learnings → update SOUL.md
- Memory MCP server (recall/store/consolidate across sessions)

**v3 — Protocol Layer**
- Model Context Protocol integration (tools as MCP servers)
- Agent-to-agent protocol support for cross-framework collaboration
- Multi-platform gateway (Discord, Telegram, Slack)

> Why governance first? Because protocols solve *how* agents communicate.
> Agent Constitution solves *whether agents are thinking honestly*.
> The governance layer is what makes everything else trustworthy.

---

## License

Apache-2.0 — see [LICENSE](LICENSE)

Use it freely. Modify it freely. Build on it commercially. Contributions are welcome under the project's [CLA](CLA.md).
