# Agent Constitution Skill

Use this project when you want a governance harness around a machine-made decision, not just a stronger raw answer.

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
2. Debate triggers only if the initial score is `>= 32/40`

This means `ac debate` may end after the initial assessment if the score is below threshold.

Important implication:

- `ac debate` is an **assessment-first** command
- It does **not** guarantee a full challenger / defender / judge round
- If you need to force a debate after your own scoring logic, use the library API instead of assuming the CLI will bypass the threshold

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
- Fastest CLI workflow: `ac debate "topic"`
- Real-model CLI workflow: `ac debate "topic" --adapter ...`
- Programmatic control over scoring and triggering: `Debate.should_trigger(score)` + `Debate.run(...)`
- Embedded pipeline gate: `GovernanceGateHook(challenger=..., judge=..., trigger_policy=...)`
- Specialized contradiction / governance demo: `python examples/demo_memory_contradiction.py`
- External planner / deploy gate demo: `python examples/demo_governance_gate.py`
- Chat-style before/after demo: `python examples/demo_chat_surface.py`

## Fastest Paths

Zero-config CLI:

```bash
pip install agent-constitution
ac debate "Should we build an AI code review tool?"
```

Zero-config demo:

```bash
python examples/demo_debate.py --topic "Should we build an AI code review tool?"
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
6. audit trail

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
- `DecisionPolicy` can trigger debate from score, action type, environment, decision type, or critical keywords
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

Examples:

- "Should we launch this feature next quarter?"
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

Avoid framing it as generic brainstorming. This project is strongest when the task is a judgment call with meaningful downside risk.

## Common Failure Modes

- Topic is too vague, so the initial assessment is shallow
- User expects a debate every time, but score never crosses threshold
- User only reads the verdict and ignores challenges / defenses / audit trail
- Hook-enabled runs produce extra audit entries, but the caller still assumes a fixed 3-entry trail
- Provisional governance scores are mistaken for calibrated long-term evidence
- Developer expects the upstream planner to act as the debate defender; in embedded workflows you often want a separate `defender=` agent
- Developer expects automatic triggering from raw planner output but never defines a `DecisionPolicy`
- User assumes the CLI automatically assigns premium models to judge-like roles; role-specific overrides now exist, but model strategy is still an explicit caller decision
