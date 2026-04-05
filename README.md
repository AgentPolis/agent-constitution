# Agent Constitution

**Governance harness for decisions that should be judged against real documents, not just a one-line prompt.**
**Works with single-agent and multi-agent workflows. Adds document-aware review, structured challenge, auditability, and governance scoring.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

```mermaid
flowchart LR
    A["🔍 Analyst<br/>scores idea<br/><b>72/100</b>"] -->|"score ≥ 70"| B["⚔️ Critic<br/>3 challenges"]
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

Agent Constitution is a governance layer you can place around an existing assistant, planner, reviewer, or agent pipeline.

It is meant for moments where the main problem is not producing an answer, but deciding whether that answer should drive action.

The important part is that the judgment can be grounded in attached documents.

Release checklists, rollback runbooks, deploy briefs, pricing memos, ownership maps, and similar files are not treated as decoration. They are treated as evidence that should change the recommendation.

That usually shows up in questions like:

- should we ship this change now
- is this recommendation strong enough to act on
- what should we do first
- what risks are still unresolved
- when should confidence be treated as provisional

The idea behind the project is straightforward:

AI systems are getting better at generating output, but judgment is still where a lot of value lives.

If a decision matters, it often helps to make the review process more explicit. Agent Constitution does that by helping systems:

- encode epistemic rules in markdown instead of burying them in prompt strings
- treat attached documents as evidence instead of ignoring them after retrieval
- route high-stakes outputs through structured challenge and judgment
- preserve audit history so important decisions can be revisited later

This is not only for multi-agent systems. You can use it to harden:

- a single assistant that needs review before acting
- a planner or deploy bot that should trigger governance only on high-stakes outputs
- a multi-agent workflow that needs explicit arbitration instead of free-form consensus

In practice, the goal is simple: make important AI decisions easier to challenge, easier to inspect, and easier to revisit later.

## When It Helps

Agent Constitution is a good fit when:

- a recommendation may lead to a real action, not just a draft
- confidence should be challenged before a decision is accepted
- you want a visible review step instead of implicit trust in one answer
- audit history matters because the decision may need to be revisited later

Common examples include deploys, pricing exceptions, architecture changes, compliance-sensitive choices, and memory or policy updates that are hard to unwind.

Concrete examples:

- deploy review using a release checklist, rollback runbook, and deploy brief
- pricing exception review using a finance memo, precedent guardrails, and account context
- organization change review using an ownership map, launch timeline, and dependency notes
- launch-readiness review for a README, proposal, or rollout plan framed as a decision

The key practical pattern is simple:

- ask a decision question
- attach the files a reviewer would actually want
- let the system say what the current judgment is and what evidence is still missing

What this looks like in a product surface:

```text
Before governance
Assistant:
  Recommendation: Approve the billing-auth hotfix rollout now.

After Agent Constitution summary gate
Assistant:
  Recommendation: Approve the billing-auth hotfix rollout now.
  Confidence: 82%
  Assessment: 72/100 (Promising)
  Adjusted score: 51/100 (Caution)

  Governance check triggered.
  Verdict: Proceed With Caution
  Score delta: -21
  Delta severity: Major Concern
  Why: Several concerns remain unresolved before the next gate.
  Top concern: Canary monitoring is still missing a billing-transaction-specific abort gate.
```

That example is based on a recorded live-model run, not a fabricated mock transcript. If you want to replay it locally without an API key, run:

```bash
python examples/demo_replay.py
```

```
BEFORE                                    AFTER Agent Constitution
─────────────────────────────────────     ─────────────────────────────────────
Planner: "Approve the pricing exception."  Planner: "Approve the pricing exception."
Confidence: 0.86                           Confidence: 0.86
Decision ships with no challenge           Governance check triggered
                                           Critic:  "Margin erosion and precedent risk"
                                           Defender:"Strategic account, capped term"
                                           Judge:   "proceed_with_caution, delta: -21"
                                           Key issue: finance approval path is missing
```

> Other frameworks usually focus on how components communicate.
> Agent Constitution focuses on how important decisions get challenged, judged, and audited.

## What Is Adjacent — And What Is Different

Agent Constitution sits near several existing categories, but it is trying to solve a slightly different problem:

- **Agent orchestration frameworks** solve how agents, tools, and workflows run together
- **Prompt / role systems** shape behavior through instructions, personas, and local rules
- **Guardrail / evaluation systems** check whether outputs violate rules or meet quality bars
- **Debate / self-critique methods** improve reasoning by adding challenge or adversarial review

Agent Constitution borrows from all of these, but its center of gravity is different.

It treats **high-stakes decisions as governed events**.

So the primary unit is not just:

- a message
- a prompt
- a workflow step
- or a final output

The primary unit is a **decision that may need challenge, arbitration, and audit history**.

That is the main distinction. The goal is not simply:

- better generation
- better collaboration
- better filtering

The goal is to create a more explicit process for producing better judgment when the decision matters.

That difference also matters when people compare "agent governance" projects:

| | Microsoft Agent Governance Toolkit | Agent Constitution |
|---|---|---|
| Focus | Runtime security and policy enforcement | Decision quality and judgment quality |
| When it runs | Around agent actions and tool execution | Around high-stakes recommendations and decisions |
| Core question | `Should this action be allowed?` | `Is this recommendation sound enough to act on?` |
| Mechanism | Policy engine, runtime interception, permission checks | Structured review, challenger/defender/judge flow, audit trail |
| Cost profile | Always-on runtime enforcement | Selective extra model calls when a decision merits challenge |

They are complementary, not substitutes.

## Quick Start

There are three good ways to try the project, depending on what you want to verify.

**1. Fastest public demo from a repo clone**

```bash
git clone https://github.com/AgentPolis/agent-constitution.git
cd agent-constitution
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python examples/demo_replay.py
```

This replays a recorded live-model deploy review with real supporting files, so it shows the intended product surface without requiring an API key.

**2. Best zero-key proof that attached documents change the judgment**

```bash
ac debate "Should we deploy the billing-auth hotfix to production tonight?" \
  --context-file examples/context/deploy/release-checklist.md \
  --context-file examples/context/deploy/rollback-runbook.md \
  --context-file examples/context/deploy/deploy-brief.md
```

Expected shape of the result:

```text
2. Analyst evaluates: Should we deploy the billing-auth hotfix to production tonight?
   Context files:
     - examples/context/deploy/release-checklist.md
     - examples/context/deploy/rollback-runbook.md
     - examples/context/deploy/deploy-brief.md
   Score: 79/100 (Promising)

3. Score 79 >= 70 — debate triggered
   Verdict: proceed
   Delta:   +8
   Final:   79 -> 87
```

**3. Package smoke test after install**

```bash
python3.11 -m pip install agent-constitution
ac debate "Should we deploy the billing-auth hotfix to production tonight?"
```

`agent-constitution` requires Python 3.11+.

That path is still useful, but without attached files it should be read as a first-pass judgment rather than a fully grounded deploy decision.

## Public Demo vs Internal Mock

For public-facing demos, this repo now prefers a recorded live-model replay over a generic mock transcript.

- `python examples/demo_replay.py` replays a real deploy review captured from a live Claude run.
- `ac debate "..." --context-file ...` with no API key uses the mock adapter, but still lets you verify that attached files change the recommendation.
- `ac debate "..."` with no files is still a useful smoke test for CI and local installation.
- `ac debate "..." --adapter anthropic|claude|ollama` runs the real judgment path.

That split is intentional:

- the replay demo shows what a real model can surface when it actually reads context files
- the mock path is still useful for deterministic testing, trigger checks, and hook validation

If you only want one public demo to point people at, use `python examples/demo_replay.py`.

There is also a real self-dogfooding example in [docs/case-studies/readme-launch-review.md](docs/case-studies/readme-launch-review.md), where Agent Constitution reviews its own README before launch.

## Scenario-Aware Scoring

`ac debate` is no longer one generic score template.

The initial analyst pass now changes rubric based on the decision type:

- `deploy`: `impact / readiness / rollback / blast_radius / evidence`
- `pricing`: `upside / precedent_risk / reversibility / evidence / strategic_fit`
- `org_design`: `clarity / disruption / timing / reversibility / execution_risk`
- `generic`: `impact / readiness / risk / evidence / reversibility`

Current score bands:

- `0-34`: Weak
- `35-49`: Borderline
- `50-69`: Caution
- `70-84`: Promising
- `85-100`: Strong

Current judge deltas are discrete:

- `+8`: strengthens case
- `0`: no material change
- `-13`: notable concern
- `-21`: major concern
- `-34`: stop-ship concern

That makes the output easier to read as a decision, not just a score.

## What Users Can Actually Do Today

The package is meant to be runnable, not just demoed.

For anything real, do not ask it to judge a one-line prompt in a vacuum.

The practical pattern is:

1. ask a decision question
2. attach background or supporting documents
3. let the system tell you what is still missing before you act

If you do not provide context, the output should be treated as a first-pass judgment, not final approval.

## How To Ask

You do not have to type `ac debate` in a product surface if the host already wires Agent Constitution in.

But the request still needs to be explicit enough that the system can identify:

- the decision being reviewed
- the downside if it is wrong
- the background or files that should be considered

These are good natural-language requests:

- `Use Agent Constitution to judge whether the billing-auth hotfix should go to production tonight.`
- `Run a challenger / defender / judge review on whether this README is ready for public launch.`
- `Assess this pricing exception, and tell me what context is missing before we approve it.`
- `Do a deploy decision review for this hotfix. Background is in the release checklist, rollback runbook, and deploy brief.`

These are weak requests:

- `Can we ship this?`
- `What do you think?`
- `Is this okay?`
- `Can you look at that thing from earlier?`

Weak requests can still be answered, but they should not be treated as fully grounded governance judgments.

You can install it and try these directly:

```bash
ac debate "Should we deploy the billing-auth hotfix to production tonight?"
ac debate "Should we approve this pricing exception for a strategic enterprise account?"
ac debate "Should we reorganize product and engineering into vertical pods before the Q4 launch?"
ac debate "Should we publish this README as-is for public launch?"
```

And for a real decision, attach the files a reviewer would actually want:

```bash
ac debate "Should we deploy the billing-auth hotfix to production tonight?" \
  --context-file examples/context/deploy/release-checklist.md \
  --context-file examples/context/deploy/rollback-runbook.md \
  --context-file examples/context/deploy/deploy-brief.md
```

There are sample deploy context files in:

```text
examples/context/deploy/
```

The last example is important: you can use Agent Constitution to review a README, launch plan, or proposal as long as you frame it as a decision.

What the package returns today:

- an initial analyst score with scenario-aware dimensions
- a trigger decision based on score threshold
- judgments that change when you attach materially different supporting files
- challenger / defender / judge outputs when debate triggers
- a concrete next-step package: `missing_context`, `next_actions`, `upgrade_condition`, `downgrade_condition`
- an audit trail that can be recorded and revisited later
- a per-run markdown debate record under `workspace/debates/`

By default, those `workspace/` artifacts are created relative to the current working directory where you run `ac`.

What the mock path is good for:

- verifying trigger behavior
- validating product surfaces
- testing hooks and audit flows
- checking whether scenario rubrics feel sensible
- proving that attached documents affect the result instead of being ignored

What it is not yet:

- a claim of full calibration across all decision types
- proof that any real model backend will match mock behavior out of the box
- a replacement for domain-specific evidence gathering

In other words, it can tell you:

- what the current recommendation is
- what context is missing
- what evidence would upgrade the decision
- what evidence would downgrade it

That is the key boundary: without background and files, it can still give you a first-pass judgment, but it should not pretend the decision is fully grounded.

It cannot honestly tell you:

- that a deploy is safe if you never gave it the deployment prep material
- that a pricing exception is acceptable if finance context was never attached
- that a reorg is wise if the launch timeline and ownership map are missing

If you want fixed prompts and a repeatable smoke test:

- golden prompts: [docs/golden-examples.md](docs/golden-examples.md)
- decision packet template: [docs/decision-packet-template.md](docs/decision-packet-template.md)
- distribution check: `python scripts/check_scenario_distribution.py`

Each `ac debate ...` run also writes a human-readable debate record like:

```text
workspace/debates/20260405T113600Z-should-we-deploy-the-billing-auth-hotfix.md
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

# Mixed-model debate from the CLI
ac debate "topic" --adapter claude --model sonnet --critic-model opus --judge-model opus
```

**What you get right away:**

- a zero-config replay demo based on a captured live-model run
- a zero-config debate smoke test with no API key
- strict schema validation for challenger, defender, and judge output
- a provisional governance score computed from recorded runs
- support for Mock, Anthropic, Ollama, and Claude CLI backends

Short answers to the obvious questions:

- `Can I use this with a single agent?` Yes. A single assistant can still be wrapped with trigger rules, challenger/judge review, and audit history.
- `Do I need premium models everywhere?` No. Use stronger models where arbitration quality matters most, usually the critic and judge.
- `When does this add value over a single stronger model?` When the decision itself benefits from an explicit review process, not only a higher-quality answer.

What this is and is not:

- `This is not a claim that debate always beats the strongest single model.` The point is to add challenge, arbitration, and auditability where a raw answer is not enough.
- `This is not for every prompt.` The intended use case is high-stakes or hard-to-reverse decisions such as deploys, auth changes, billing logic, pricing, compliance, and major architecture calls.
- `This is not fully calibrated governance out of the box.` Today the package records governance history and computes a provisional score from real runs; retrospective verification and credibility adjustment exist as library primitives and are still early-stage operationally.
- `This is not free in token cost.` Structured review adds extra model calls, so it should be triggered selectively where decision quality and auditability are worth the overhead.

## Developer Setup

If you are working from a local clone instead of the published package:

```bash
git clone https://github.com/AgentPolis/agent-constitution.git
cd agent-constitution
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest --tb=short -v
```

`tests/conftest.py` also makes local imports work when pytest is launched from the
parent workspace, but editable install remains the recommended development path.

## Model Strategy

Agent Constitution does **not** require Sonnet- or Opus-class models to function, but model quality has a direct effect on debate quality.

- For onboarding, CI, and structure checks, `MockAdapter` is enough
- For lightweight product demos or internal prototyping, a smaller real model can be acceptable
- For high-stakes review, use a stronger reasoning model for at least the critic and judge roles
- For launch, security, compliance, pricing, architecture, or memory-conflict decisions, Sonnet / Opus class models or their equivalent are strongly recommended

Current role-model behavior:

- CLI path: `ac debate ... --adapter ... --model ...` still gives you a fast shared default, but now also supports `--analyst-*`, `--critic-*`, and `--judge-*` overrides
- Library path: you can give each `BaseAgent(...)` its **own adapter and model**, so heterogeneous debate is also supported programmatically
- Product choice today: same-model debates remain the easy path; mixed-model debates are also supported when you want a stronger critic or judge

Example: heterogeneous role setup

```python
from adapters import AnthropicAPIAdapter
from constitution import BaseAgent, Constitution, Debate

rules = Constitution.default()

analyst = BaseAgent(
    role="analyst",
    goal="Produce the initial opportunity assessment",
    adapter=AnthropicAPIAdapter(model="claude-sonnet-4-5"),
    constitution=rules,
)
critic = BaseAgent(
    role="critic",
    goal="Pressure-test the assessment and surface hidden risks",
    adapter=AnthropicAPIAdapter(model="claude-opus-4-1"),
    constitution=rules,
)
judge = BaseAgent(
    role="judge",
    goal="Render the most reliable final verdict",
    adapter=AnthropicAPIAdapter(model="claude-opus-4-1"),
    constitution=rules,
)

debate = Debate(challenger=critic, defender=analyst, judge=judge)
```

Equivalent CLI pattern:

```bash
ac debate "Should we ship this pricing change?" \
  --adapter claude \
  --model sonnet \
  --critic-model opus \
  --judge-model opus
```

Three practical rules of thumb:

- Developer: start with one shared model to simplify ops, then split judge / critic onto stronger models when accuracy matters more than cost
- Product manager: if the debate outcome changes user-visible recommendations, budget for a stronger judge before you budget for a fancier analyst
- Agent designer: the critic and judge usually benefit most from stronger reasoning; the analyst can often be cheaper if its output is challengeable and schema-validated

One caution: a stronger model does not replace good role design. If the personas, constitutions, and trigger policy are weak, using Opus everywhere mostly makes the process more expensive, not more reliable.

## How Debate Triggers

`ac debate "topic"` does **not** skip straight to the challenger/defender/judge round.
It runs in two stages:

1. the analyst produces an initial scored assessment
2. the debate engine checks whether that score crosses the trigger threshold

By default, structured debate triggers only when the initial analyst score is **70/100 or higher**.

- If score `>= 70`, the critic, defender, and judge run
- If score `< 70`, the CLI exits after the initial assessment and records that debate was not triggered

Quick ways to see it:

```bash
# Full CLI path: assessment first, then auto-trigger if threshold is met
ac debate "Should we expand from mid-market to enterprise this year?"

# Standalone mock demo with explicit topic input
python examples/demo_debate.py --topic "Should we expand from mid-market to enterprise this year?"
```

If you want to force a debate programmatically, call `Debate.run(...)` directly after your own scoring step. The library-level trigger check is `Debate.should_trigger(score)`.

## Integration Patterns

In practice, Agent Constitution is often most useful as a **library gate inside an existing agent pipeline**, not only as a standalone CLI.

Common trigger patterns:

1. Score-gated library call

```python
result = my_agent.run("Should we deploy to production?")
score = extract_score(result)

debate = Debate(challenger=critic, defender=my_agent, judge=judge)
if debate.should_trigger(score):
    verdict = debate.run(topic=result, initial_score=score)
```

2. Hook-based governance gate

```python
from constitution import BaseAgent, Constitution, DecisionPolicy, GovernanceGateHook

policy = DecisionPolicy(
    action_types={"deploy", "launch", "migrate"},
    environments={"production"},
    critical_keywords={"auth", "billing", "security"},
    match_mode="any",
)

gate = GovernanceGateHook(
    challenger=critic,
    defender=defender,
    judge=judge,
    trigger_policy=policy,
    render_mode="summary",  # "silent" | "summary" | "full_transcript"
    response_formatter=GovernanceGateHook.chat_response_formatter("summary"),
)

agent = BaseAgent(
    role="planner",
    goal="Produce deployment recommendations",
    constitution=Constitution.default(),
    hooks=[gate],
)

response = agent.run("Should we deploy version 1.8.2 to production?")
if gate.last_result is not None:
    print(gate.last_result.verdict)
    print(gate.last_trigger_reasons)
```

3. External workflow trigger

Use your own rules to decide when a debate is mandatory, or let the built-in policy gate infer common high-stakes signals from planner output. This is the path that best fits external systems such as PM planners, deploy bots, PR reviewers, or memory pipelines that are not "Agent Constitution agents" themselves.

`GovernanceGateHook` is deliberately a review layer over planner output and recommendation text. It is not a runtime permission system or an execution sandbox.

Auto-trigger opportunities usually show up around:

- production deploys
- auth / billing / security-sensitive PRs
- large architectural changes
- expensive or irreversible business decisions
- planner output with `action`, `environment`, or `decision_type` fields

If your upstream system is not debate-aware, pass a dedicated `defender=` agent into `GovernanceGateHook(...)` so the gate can challenge the decision without requiring the original planner to emit debate-shaped JSON.

User-facing render modes:

- `silent`: keep the original response unchanged, but still populate `gate.last_result`
- `summary`: append or inject a compact governance verdict for chat surfaces
- `full_transcript`: attach challenges, defenses, and audit trail for audit-heavy views

For chat products, pair `render_mode="summary"` with `GovernanceGateHook.chat_response_formatter("summary")` so the user sees a polished assistant reply instead of raw JSON enrichment.

If you want the most guided end-user experience, start with `python examples/demo_interactive.py --mock`, then try `python examples/demo_governance_gate.py`, `python examples/demo_user_experience.py`, and `python examples/demo_chat_surface.py` to see what each render mode looks like in practice.

---

## Four Core Mechanisms

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

Rules live in version-controlled markdown instead of inline strings. Edit a markdown file to change how an agent thinks.

### 2. Adversarial Debate

High-scoring assessments (score >= 70/100) trigger structured debates so strong recommendations are challenged before action.
A challenger raises three specific challenges. The defender rebuts each.
A judge renders a verdict with a score delta and full audit trail.

```python
from constitution import BaseAgent, Constitution, Debate

rules = Constitution.default()
analyst  = BaseAgent(role="analyst",  goal="Evaluate opportunities", constitution=rules)
critic   = BaseAgent(role="critic",   goal="Challenge assumptions",  constitution=rules)
judge    = BaseAgent(role="judge",    goal="Render fair verdicts",   constitution=rules)

debate = Debate(challenger=critic, defender=analyst, judge=judge)
result = debate.run(topic="Should we expand from mid-market to enterprise this year?")

result.verdict       # "proceed_with_caution"
result.score_delta   # -21
result.challenges    # ["Market is more competitive than assessed", ...]
result.audit_trail   # Full debate record
```

Debate-stage LLM responses go through **separate validation** before they're trusted.
The debate engine uses explicit schema validators (`_validate_challenges`, `_validate_defenses`, `_validate_verdict`) and rejects malformed challenger, defender, and judge output by default. If you want legacy fallback behavior, opt into `strict_validation=False`.

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

# Built-in gate for existing agent pipelines
from constitution import DecisionPolicy, GovernanceGateHook

# Hooks compose — pass multiple, they chain in order
debate = Debate(challenger, defender, judge, hooks=[AuditHook()])
agent = BaseAgent(role="analyst", goal="Evaluate", hooks=[CostApprovalHook()])
policy = DecisionPolicy.high_stakes_default()
gate = GovernanceGateHook(
    challenger=critic,
    defender=defender,
    judge=judge,
    trigger_policy=policy,
    render_mode="summary",
)
```

Available hook points:

| Hook | When | Can modify |
|------|------|-----------|
| `AgentHook.pre_call` | Before LLM call | Prompt |
| `AgentHook.post_call` | After LLM call | Response content |
| `AgentHook.on_cost_limit` | Cost would exceed limit | Raise / warn / allow |
| `DebateHook.pre_challenge` | Before challenger runs | Topic |
| `DebateHook.post_challenge` | After challenge validation | Challenges list, revalidated before use |
| `DebateHook.pre_defense` | Before defender runs | Challenges |
| `DebateHook.post_defense` | After defense validation | Defenses list, revalidated before use |
| `DebateHook.pre_verdict` | Before judge runs | Abort (raise) |
| `DebateHook.post_verdict` | After verdict | Full result, revalidated before return |
| `DebateHook.on_validation_error` | Schema validation fails | Raise / fallback |

Hooks are best for logging, policy gates, and controlled transformations. In strict mode, any hook mutation that breaks the validated debate schema is rejected. `DecisionPolicy` lets a gate trigger from score, action type, environment, or critical keywords instead of relying on a single hard-coded score path.

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
Calibration Accuracy       N/A     15%
Audit Completeness         9/10    15%

Provisional Governance Score: 6.3/10
```

The governance score tracks five dimensions: epistemic honesty, constitutional compliance, debate rigor, calibration accuracy, and audit completeness. `ac debate` records governance data to `workspace/governance_history.json`, and `ac score` aggregates those real runs instead of printing placeholders. Until you verify retrospectives, the report stays explicitly **uncalibrated** and should be treated as a provisional operational snapshot rather than a final grade.

---

## Why Agent Constitution?

### Why Now: The Governance Gap

2026 is the year of **agent governance**. Singapore launched the [world's first Agentic AI Governance Framework](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf) at WEF 2026. Gartner predicts 40% of enterprise apps will feature AI agents by year-end. There is growing attention on governance, but most public discussion still sits at the framework or policy layer.

Agent Constitution is one attempt to turn that discussion into installable code: explicit constitutional rules, policy-based triggering, structured adversarial review, and auditable outputs. It is not the only way to approach this problem, but it is a concrete starting point.

### Where It Sits in the Ecosystem

Agent Constitution is not a replacement for orchestration frameworks. It is a governance layer that can work alongside them.

| Dimension | CrewAI | LangGraph | AutoGen | Agent Constitution |
|-----------|--------|-----------|---------|----------------------|
| Agent coordination | Yes | Yes | Yes | Debate-scoped only |
| Adversarial debate | Not built-in | Not built-in | Via GroupChat | Structured + schema-validated |
| Retrospective verification | Not built-in | Not built-in | Not built-in | Library primitives |
| Human-readable rules (SOUL.md) | Not built-in | Not built-in | Not built-in | Yes |
| Team governance | Not built-in | Not built-in | Limited | Core focus |
| Cost tracking | Via LiteLLM | Via callbacks | Via token tracking | Built-in + hooks |

These frameworks solve *how* agents coordinate. Agent Constitution focuses on a different question: *how decisions get challenged, judged, and audited*. They are complementary rather than competing.

---

## Personal Decision Review

The same governance ideas can wrap a single personal agent too.

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
| `constitution/retrospective.py` | Early library primitive for prediction tracking and credibility adjustment |
| `constitution/governance_score.py` | 5-dimension governance scoring from recorded runs |
| `constitution/cost_guard.py` | Token cost accounting with hard-limit enforcement after each call |
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
| pytest | 215 tests, zero API keys required |
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
  signal.py + signal_pool.py Early signal primitives for dedup and pooling
  cost_guard.py              Token cost accounting and hard-limit enforcement
  trace.py                   RunTrace audit trail
  retrospective.py           Early prediction recording primitive
  governance_score.py        Five-dimension governance scoring
  cli.py                     `ac` CLI
```

### Design Principles

- **Generator/Validator separation**: Debate-stage LLM responses are generated, then validated by a separate function. The debate engine uses `_validate_challenges()`, `_validate_defenses()`, and `_validate_verdict()` and raises `DebateValidationError` on malformed debate output by default.
- **Constitution as prompt injection**: Rules live in markdown files, not Python strings. `SOUL.md` files are human-readable and version-controllable.
- **Cost guard with hard limit**: Cost is accounted for after each completed call. If cumulative cost would cross the hard limit, the guard raises `CostLimitExceeded` immediately after that call unless a hook explicitly allows the over-limit result.

---

## Origin

Agent Constitution emerged from sustained experimentation with real decision workflows, review gates, and agent-mediated judgment loops.

It reflects a point of view shaped by implementation and repeated testing: for certain classes of decisions, improving model capability alone may not be enough. The decision itself can benefit from explicit challenge, arbitration, and auditability.

This repository does not present itself as a finalized standard for agent governance. It is a concrete, working proposal for how governance can be added to machine-made decisions without rebuilding an entire system from scratch.

We hope it serves both as a usable toolkit and as an invitation:

- to evaluate these ideas in real workflows
- to challenge the assumptions behind them
- to contribute stronger evidence, counterexamples, and better patterns

## Research Foundation

Multi-agent debate improves factual reasoning and reduces hallucination ([Du et al., 2023](https://arxiv.org/abs/2305.14325)). Heterogeneous agents with dynamic debate mechanisms outperform homogeneous approaches ([FREE-MAD, 2025](https://arxiv.org/abs/2509.11035)).

Agent Constitution draws on these findings and adapts them into a practical, installable governance workflow. The research is still evolving, and so is this project.

---

## Roadmap

These are exploratory directions, not shipped features.

**Current scope** — Governance harness
- Constitutional agent governance via `SOUL.md`
- Adversarial debate engine (challenger/defender/judge)
- Early retrospective primitives for prediction tracking and credibility adjustment
- Personal agent mode
- 4 LLM backends: Mock, Anthropic, Claude CLI, Ollama
- `ac` CLI + Governance Score

**Near-term extensions**
- Per-turn token budgets (not just session-level hard limits)
- Permission gates on adapter calls (sub-agents get restricted scope)
- Auto-compaction with semantic retention for long-running sessions
- Consolidation engine: background learning extraction during idle time

**Longer-term experiments**
- Skill auto-creation from experience (with adversarial review before promotion)
- Dream/consolidation cycle: session end → extract learnings → update SOUL.md
- Memory MCP server (recall/store/consolidate across sessions)

- Model Context Protocol integration (tools as MCP servers)
- Cross-framework collaboration patterns
- Multi-platform gateway (Discord, Telegram, Slack)

> Why start with governance? Because protocols solve *how* agents communicate.
> Agent Constitution focuses on a complementary question: *how decisions get challenged, judged, and audited*.
> We believe this layer is worth getting right early.

---

## License

Apache-2.0 — see [LICENSE](LICENSE)

Use it freely. Modify it freely. Build on it commercially. Contributions are welcome under the project's [CLA](CLA.md).
