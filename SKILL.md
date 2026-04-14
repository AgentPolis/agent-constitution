# Agent Constitution Skill

A trust protocol for AI agents. Use this project when you want a governance harness around a machine-made decision, not just a stronger raw answer. Works with a single agent or an entire multi-agent pipeline.

## When To Use

- A decision needs an initial assessment plus explicit counterarguments
- You want a single-agent or multi-agent system to become reviewable, challengeable, and auditable
- You want challenger / defender / judge roles with an audit trail
- You want a scored governance-oriented workflow rather than free-form multi-agent chat
- You want a zero-API-key local demo with the mock adapter before switching to real models

## When Not To Use

- You only need a raw answer with no review, challenge, or audit step
- You want open-ended agent collaboration without a scored trigger
- You need a general orchestration framework more than a governance / debate layer
- You want unconstrained brainstorming where every idea should flow through without a gate

## Core Trigger Rule

`ac debate "topic"` is a two-stage flow:

1. The analyst produces an initial scored assessment
2. Debate triggers only if the initial score is `>= 70/100`

This means `ac debate` may end after the initial assessment if the score is below threshold.

Important implication:

- `ac debate` is an **assessment-first** command
- It does **not** guarantee a full challenger / defender / judge round
- If you need to force a debate after your own scoring logic, use the library API instead of assuming the CLI will bypass the threshold

Current score bands:

- `0-34` weak
- `35-49` borderline
- `50-69` caution
- `70-84` promising
- `85-100` strong

Current judge deltas are discrete:

- `+8` strengthens case
- `0` no material change
- `-13` notable concern
- `-21` major concern
- `-34` stop-ship concern

Library-level check:

```python
from constitution import Debate

debate = Debate(challenger=critic, defender=analyst, judge=judge)
if debate.should_trigger(score):
    result = debate.run(topic=topic, initial_score=score)
```

## Recommended Operating Paths

Use the path that matches the goal:

- Fastest human trial: `python examples/demo_debate.py --topic "..."`
- Best public-facing no-key demo: `python examples/demo_replay.py`
- Fastest CLI workflow: `ac debate "topic"`
- Real decision workflow: `ac debate "topic" --context-file path/to/doc.md --context-file path/to/another.md`
- Real-model CLI workflow: `ac debate "topic" --adapter ...`
- Programmatic control over scoring and triggering: `Debate.should_trigger(score)` + `Debate.run(...)`
- Embedded pipeline gate: `GovernanceGateHook(challenger=..., judge=..., trigger_policy=...)`
- External planner / deploy gate demo: `python examples/demo_governance_gate.py`
- Chat-style before/after demo: `python examples/demo_chat_surface.py`

## Fastest Paths

Zero-config CLI:

```bash
pip install agent-constitution
ac debate "Should we build an AI code review tool?"
```

Decision with supporting documents:

```bash
ac debate "Should we deploy the billing-auth hotfix to production tonight?" \
  --context-file docs/release-checklist.md \
  --context-file docs/rollback-runbook.md \
  --context-file docs/incident-summary.md
```

There are sample deploy context files in `examples/context/deploy/` if you want a deterministic local smoke test.

Zero-config demo:

```bash
python examples/demo_debate.py --topic "Should we build an AI code review tool?"
```

Recorded real-model replay demo:

```bash
python examples/demo_replay.py
```

Real-model adapters:

```bash
ac debate "topic" --adapter anthropic
ac debate "topic" --adapter ollama --model llama3
ac debate "topic" --adapter claude --model sonnet
ac debate "topic" --adapter claude --model sonnet --critic-model opus --judge-model opus
```

## Model Expectations

Do not assume the project automatically picks a stronger model for the critic or judge.

Current behavior:

- CLI mode supports one shared adapter/model plus optional per-role overrides such as `--critic-model ...` or `--judge-adapter ...`
- Library mode lets you assign different adapters or models per role
- Mixed-model debate is therefore supported, but it is still a caller decision, not an automatic policy

Recommended mental model:

- `MockAdapter`: structure, CI, onboarding, screenshots, deterministic demos
- Smaller real model: low-risk internal prototyping
- Stronger model for critic and judge: launch, security, compliance, pricing, architecture, memory contradiction, or other high-downside decisions

If you only upgrade one role, upgrade the judge first or the critic + judge pair first. A premium analyst with a weak judge still leaves the most important arbitration step underpowered.

For high-stakes use, treat Sonnet / Opus class models, or equivalent reasoning-tier models from another provider, as the practical default rather than the formal minimum.

Built-in governance gate for existing agents:

```python
from constitution import DecisionPolicy, GovernanceGateHook

policy = DecisionPolicy.high_stakes_default()
gate = GovernanceGateHook(
    challenger=critic,
    defender=defender,
    judge=judge,
    trigger_policy=policy,
    render_mode="summary",
    response_formatter=GovernanceGateHook.chat_response_formatter("summary"),
)
agent = BaseAgent(role="analyst", goal="Evaluate", hooks=[gate])
response = agent.run("Should we deploy to production?")
if gate.last_result is not None:
    print(gate.last_result.verdict)
    print(gate.last_trigger_reasons)
```

Use a dedicated `defender=` when the upstream planner is not itself debate-aware. That is the common case for external systems.
Use `render_mode="silent"` for machine-first pipelines, `render_mode="summary"` for normal chat surfaces, and `render_mode="full_transcript"` only when the user truly needs the full debate in-view.
Use `GovernanceGateHook.chat_response_formatter("summary")` when the output should read like a polished assistant reply instead of raw JSON.

## Expected Output Shape

When debate triggers successfully, expect:

1. initial analyst assessment
2. trigger decision
3. validated `challenges`
4. validated `defenses`
5. validated `verdict` with `score_delta`
6. explicit `missing_context`, `next_actions`, `upgrade_condition`, and `downgrade_condition`
7. audit trail

Do not treat the project as a single-string verdict generator. The governance value is in the full structured path, not just the final label.

For user-facing integrations, the hook can render three different experiences:

- `silent`: original answer only
- `summary`: original answer plus compact governance verdict
- `full_transcript`: original answer plus challenges, defenses, and audit trail

## Important Behavior

- Strict schema validation is on by default
- Hooks are for logging, policy gates, and controlled transformations
- In strict mode, hook mutations that break validated debate structure are rejected
- Audit trail normally contains 3 core role steps
- Additional audit entries may appear when hooks mutate the pipeline
- `ac score` may be provisional / uncalibrated until retrospective verification exists
- MockAdapter is for structure, onboarding, and CI; it is not evidence of real-model quality
- CLI demos may look good with one shared model, but production users often want stronger critic / judge roles than analyst roles
- `DecisionPolicy` can trigger debate from score, action type, environment, decision type, critical keywords, or complexity level
- `VerificationTier` controls debate depth: LOW (skip), STANDARD (single round), HIGH (full + context), CRITICAL (multi-round)
- Every debate produces a hash-chained `GovernanceChain` — tamper-evident, portable, offline-verifiable via `GovernanceChain.verify_artifact()`
- `TrustProtocol` is a one-line facade wrapping policy + tier + hook
- If policy triggers without an explicit score, the gate seeds debate with the threshold score unless you provide your own scorer

## Hook Boundaries

Hooks are best for:

- logging
- approval gates
- external audit sinks
- carefully controlled post-processing

Hooks are not a license to silently change the meaning of the debate.

Current safety model:

- schema-breaking hook mutations are rejected in strict mode
- hook-induced debate mutations may create additional audit entries
- no-hook runs still produce the normal 3 core role steps

## How To Frame Tasks Well

Good tasks have:

- a real decision or recommendation surface
- meaningful downside if the initial answer is wrong
- enough specificity that the analyst can score it
- supporting context or files when the decision depends on operational details

Examples:

- "Should we deploy the billing-auth hotfix to production tonight?"
- "Should we approve this pricing exception for a strategic enterprise account?"
- "Should we reorganize product and engineering into vertical pods before the Q4 launch?"
- "Assess this acquisition idea, then challenge it if the score is high enough"
- "Run a challenger / defender / judge review on this product strategy"

Weak tasks:

- "Brainstorm some ideas"
- "Give me general thoughts"
- "Chat about this topic"

## Good User Framing

Prefer prompts like:

- "Debate whether we should launch X"
- "Assess this idea, then challenge it if the score is strong enough"
- "Run a challenger / defender / judge review on this proposal"
- "Use Agent Constitution to judge whether this hotfix should go to production tonight"
- "Do a deploy decision review. Background is in the release checklist and rollback runbook."
- "Assess this pricing exception and tell me what context is missing before approval"

Avoid framing it as generic brainstorming. This project is strongest when the task is a judgment call with meaningful downside risk.

Natural-language triggering is fine, but it should still include:

- the decision question
- the risk or action surface
- background docs when the choice depends on operational detail

Weak natural-language triggers:

- "Can we ship this?"
- "Is this okay?"
- "Help me judge that thing from earlier"

Strong natural-language triggers:

- "Use Agent Constitution to judge whether the billing-auth hotfix should go to production tonight"
- "Run a challenger / defender / judge review on whether this README is ready for public launch"
- "Assess this pricing exception and tell me what is still missing before approval"

## What Users Can Actually Do Today

Users can do more than watch a demo:

- Install the package and run `ac debate "Should we deploy the billing-auth hotfix to production tonight?"`
- Attach real files to a decision: `ac debate "Should we deploy the billing-auth hotfix to production tonight?" --context-file docs/release-checklist.md --context-file docs/rollback-runbook.md`
- Ask for a pricing decision review: `ac debate "Should we approve this pricing exception for a strategic enterprise account?"`
- Ask for an org/design review: `ac debate "Should we reorganize product and engineering into vertical pods before the Q4 launch?"`
- Wrap an existing planner or deploy bot with `GovernanceGateHook` so high-stakes outputs get challenged automatically
- Keep a human-readable record of each CLI run under `workspace/debates/`
- Review launch materials by framing them as decisions, for example:
  - `Should we publish this README as-is for public launch?`
  - `Run a challenger / defender / judge review on whether this README overpromises current capabilities.`

Current scenario-aware scoring in the mock path supports:

- `deploy`
- `pricing`
- `org_design`
- `generic`

Important boundary:

- The public replay demo is based on a captured real-model run and is the best no-key way to show the product surface
- The mock path is useful for structure, trigger behavior, and product-surface testing
- It is not proof that a real model is already calibrated across these domains
- If the user does not provide enough background, the result should be treated as a first-pass judgment, not final approval
- If the user does provide files, the system should use them and shrink `missing_context` rather than pretending everything is known already

## Common Failure Modes

- Topic is too vague, so the initial assessment is shallow
- User expects a debate every time, but score never crosses threshold
- User only reads the verdict and ignores challenges / defenses / audit trail
- Hook-enabled runs produce extra audit entries, but the caller still assumes a fixed 3-entry trail
- Provisional governance scores are mistaken for calibrated long-term evidence
- Developer expects the upstream planner to act as the debate defender; in embedded workflows you often want a separate `defender=` agent
- Developer expects automatic triggering from raw planner output but never defines a `DecisionPolicy`
- User assumes the CLI automatically assigns premium models to judge-like roles; role-specific overrides now exist, but model strategy is still an explicit caller decision
