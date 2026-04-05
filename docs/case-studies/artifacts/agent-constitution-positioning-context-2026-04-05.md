# Agent Constitution Positioning Context

Verified on 2026-04-05 from the local repository.

## Core Positioning

Agent Constitution is a governance layer for decisions that should be judged against real documents, not just a one-line prompt.

Its focus is decision quality and judgment quality rather than runtime permission enforcement.

It is designed to sit around an existing assistant, planner, reviewer, or agent pipeline when the main question is:

- is this recommendation sound enough to act on
- what evidence is still missing
- should confidence be treated as provisional

## Primary Mechanism

- analyst produces an initial scored assessment
- critic raises structured challenges if the score crosses threshold
- defender responds
- judge issues a verdict, score delta, missing context, and next actions

The intended value is explicit challenge, auditability, and document-aware review around high-stakes recommendations.

## Evidence Model

The project treats attached files as evidence.

Examples called out in the README:

- release checklist
- rollback runbook
- deploy brief
- pricing memo
- ownership map

The claim is not that governance happens at every tool call.
The claim is that governance should happen when an answer is about to drive action.

## Current Scope And Caveats

- public replay demo exists for a recorded live-model deploy review
- zero-key CLI path without an API key uses deterministic mock responses
- governance score is described as a provisional process-level proxy, not proof of real-world decision quality
- retrospective calibration is described as an early library primitive, not a persisted production subsystem

## Self-Described Difference From Microsoft Agent Governance Toolkit

The README currently frames the difference this way:

- Microsoft Agent Governance Toolkit: runtime security and policy enforcement
- Agent Constitution: decision quality and judgment quality
- Microsoft core question: should this action be allowed
- Agent Constitution core question: is this recommendation sound enough to act on

## Main Strategic Risk

If a larger project already covers enough of the same practical need, Agent Constitution could look redundant.

If the two tools operate at different layers, then the right move is likely sharper positioning rather than direct imitation.
