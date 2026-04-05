# Case Study: Agent Constitution Reviewed Its Own README Before Launch

Before treating this repository as launch-ready, we used Agent Constitution to review its own public README as a decision:

`Should we publish this README as-is for public launch?`

This is not a benchmark. It is a self-dogfooding case study meant to answer a simpler question:

Can the framework surface useful launch-readiness concerns when pointed at its own public story?

## Setup

- Topic: `Should we publish this README as-is for public launch?`
- Context files:
  - `README.md`
  - `CONTRIBUTING.md`
  - `pyproject.toml`
- Adapter path: Claude
- Date: 2026-04-05

## Why This Case Matters

The project claims to help challenge important recommendations before action.

A launch README is exactly that kind of recommendation. It is a public statement about what the project does, how mature it is, and what a new user should expect.

That makes it a good first self-review target:

- the stakes are real but bounded
- the evidence is concrete
- the result can directly improve the repo

## Before

Before this review, the README already had several strengths:

- clear positioning around document-driven decision review
- a real replay demo instead of only abstract architecture claims
- explicit caveats around calibration and maturity
- concrete examples for deploy and pricing-style decisions

But it also sat near the upper edge of what the implementation could honestly support.

## Result

### Analyst Pass

- Initial score: `57/100`
- Band: `Caution`
- Confidence: `65%`
- Initial recommendation: `Do not publish as-is`

The first real-model pass did **not** trigger automatic debate because the score stayed below the current `70/100` threshold.

That outcome was still useful.

The model flagged three core concerns:

- the supplied excerpt was truncated, so the model could not verify the full document
- there was no visible evidence of external review or user validation
- launch-facing claims needed stronger verification than the excerpt could support

## What We Changed After Review

The self-review was useful because it pushed us toward concrete fixes rather than abstract polish.

Changes made after the review included:

- tightening maturity language for `retrospective.py`, `signal.py`, and `signal_pool.py`
- removing personal `CLAUDE.md` routing instructions that did not belong in a public repo
- strengthening the public story around document-driven review with clearer use-case framing
- tightening several launch-surface inconsistencies between docs and implementation

## What This Case Does And Does Not Prove

What it shows:

- the framework is capable of producing a useful launch-readiness review artifact against real repo materials
- even a non-triggering analyst pass can surface actionable trust gaps
- self-dogfooding can improve the public surface in a concrete way

What it does not show:

- that Agent Constitution is already calibrated across domains
- that one README review proves real-world decision quality
- that mock demos are a substitute for real-model evidence

## Artifact

Supporting artifact:

- [README self-review artifact](artifacts/readme-launch-review-2026-04-05.md)

## Takeaway

This review did not prove that Agent Constitution is the correct answer to agent governance.

It did show that the framework can be usefully turned on its own public materials and surface where the story was ahead of the evidence.
