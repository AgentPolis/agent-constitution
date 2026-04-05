# Pre-Execution Review Context

This context describes the evidence model explored by Agent Constitution.

## Core Idea

Agent Constitution is built around the idea that some agent outputs should be reviewed as decisions before action is taken.

The focus is not runtime tool permissioning.
The focus is whether a recommendation is sound enough to act on.

## Mechanism

The current mechanism is:

- analyst gives an initial scored assessment
- critic raises structured challenges
- defender responds to those challenges
- judge issues a verdict, score delta, missing context, and next actions

The resulting artifact can include:

- challenges
- defenses
- final verdict
- score delta
- explicit missing context
- next actions

## Why This Differs From Post-Execution Audit

Post-execution audit usually tells you:

- what happened
- what policy fired
- what action was allowed or denied
- what trace was recorded

Pre-execution adversarial review instead tries to capture:

- what objections were raised before action
- which objections were answered or left unresolved
- whether confidence should be upgraded or downgraded
- what evidence was missing at decision time

## Claim Under Review

The claim is not that this replaces runtime governance.

The claim is narrower:

- for high-stakes decisions, a structured pre-execution review artifact may be more useful than post-execution audit alone
- because it records the reasoning challenge process before the action becomes irreversible

## Important Limits

- this is an early-stage evidence model
- it is not cryptographically sealed
- it does not itself enforce tool permissions
- it does not prove that post-execution audit is unnecessary

The practical question is whether this kind of artifact fills a gap that policy logs and audit trails do not fully cover.
