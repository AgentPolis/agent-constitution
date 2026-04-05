# Discussion #276 Decision-Evidence Context

Verified on 2026-04-06 from Microsoft Agent Governance Toolkit Discussion #276:

<https://github.com/microsoft/agent-governance-toolkit/discussions/276>

## Question Being Discussed

The thread asks whether agent governance should treat the decision itself as a first-class artifact rather than only as part of policy enforcement logs and audit trails.

The framing introduced in the thread is:

`Intent -> Policy -> Decision -> Evidence -> Execution`

## Microsoft AGT Maintainer Response

Microsoft AGT maintainer `imran-siddique` said the toolkit already models structured decisions in part:

- `PolicyDecision` objects include fields like `allowed`, `matched_rule`, `action`, `reason`, `evaluation_ms`, and an `audit_entry`
- `AuditChain` is hash-chained and tamper-evident
- the flight recorder captures full execution traces for replay

But he also explicitly said the toolkit does **not** yet treat the decision as a sealed, independently verifiable artifact in the way described by the thread author.

His wording was that the decision and evidence are currently embedded in the audit trail rather than being first-class objects that can be passed around or externally verified.

## Guardian Position

`xsa520`, author of the Guardian prototype, described a different evidence model:

- the decision record itself becomes a first-class artifact
- the record includes intent, policy outcome, and metadata
- that record is written into a hash-chained evidence ledger

The claimed benefits are:

- deterministic replay
- integrity verification
- tamper detection between policy evaluation and execution

This is still primarily a cryptographic and ledger-oriented model of decision evidence.

## What The Thread Does Not Yet Cover

The thread does not yet explore a third evidence model:

- a pre-execution adversarial review artifact
- where a challenger raises concerns
- a defender responds
- a judge issues a verdict, score delta, missing context, and next actions

That would produce structured decision evidence before action, but not as a policy log or hash receipt.

## Main Open Question

For high-stakes agent decisions, is post-execution audit enough, or should governance produce a richer pre-execution decision artifact before execution begins?
