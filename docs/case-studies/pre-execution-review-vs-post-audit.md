# Case Study: Pre-Execution Review vs Post-Execution Audit

This case study explores a question that surfaced in Microsoft Agent Governance Toolkit Discussion [#276](https://github.com/microsoft/agent-governance-toolkit/discussions/276):

`Should high-stakes agent decisions produce a pre-execution decision artifact, or is post-execution audit sufficient?`

The point was not to argue that runtime governance is unnecessary.

The point was to test whether a different evidence form is worth treating as a first-class governance layer:

- not a policy receipt
- not only an audit log
- but a structured decision artifact produced before action

## Setup

- Topic: `Should high-stakes agent decisions produce a pre-execution decision artifact, or is post-execution audit sufficient?`
- Context files:
  - `docs/case-studies/artifacts/discussion-276-decision-evidence-context-2026-04-06.md`
  - `docs/case-studies/artifacts/pre-execution-review-context-2026-04-06.md`
- Automatic path attempted first: normal `ac debate` with Claude
- Debate continuation: manual structured JSON prompts using the same model family
- Date: 2026-04-06

## Why This Case Matters

The public discussion in `#276` mostly covered two evidence models:

- policy and audit records embedded in a runtime governance stack
- decision artifacts stored as sealed or hash-chained records

What the thread did not yet cover was a third option:

- a pre-execution adversarial review artifact with challenges, defenses, verdict, and score delta

That is the gap this case tests.

## Result

### Automatic CLI Attempt

The normal `ac debate` path was attempted first.

In this environment, the Claude adapter returned non-JSON routing text instead of the analyst schema, so the automatic run could not complete cleanly. That limitation is part of the record.

### Completed Structured Debate

The same question was then continued manually with explicit JSON prompts.

The result:

- Initial score: `61/100`
- Verdict: `proceed_with_caution`
- Score delta: `+8`
- Final score: `69/100`
- Confidence: `75%`

## What The Debate Clarified

The critic surfaced the strongest objections:

- pre-execution review adds latency
- it may not scale well if overused
- it does not validate execution correctness

The defender narrowed the claim in a useful way:

- this layer is only for a small subset of irreversible, non-time-sensitive decisions
- it should be rare, not universal
- it does not replace runtime governance or post-execution audit

That made the final answer more credible.

The useful claim is not:

- "pre-execution review should replace audit"

The useful claim is:

- "for a small class of irreversible decisions, a structured pre-execution artifact may capture governance value that post-execution audit alone misses"

## What This Does And Does Not Prove

What it shows:

- there is a coherent third evidence model between policy receipt and audit replay
- adversarial review can be described as decision evidence, not only as prompt choreography
- the strongest version of the idea is narrow and scoped, not universal

What it does not show:

- that this layer scales across frequent operational decisions
- that it should replace runtime policy enforcement
- that the current implementation is already operationally mature

## Artifact

Supporting artifact:

- [Pre-execution review artifact](artifacts/pre-execution-review-2026-04-06.md)

## Takeaway

This review supports treating structured adversarial review as a possible decision-evidence layer for a small class of high-stakes decisions.

It does not support overselling it as a general substitute for post-execution audit or runtime governance.
