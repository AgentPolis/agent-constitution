# Pre-Execution Review vs Post-Execution Audit Artifact

Source artifact generated on 2026-04-06 for the question:

`Should high-stakes agent decisions produce a pre-execution decision artifact, or is post-execution audit sufficient?`

## Inputs

- `docs/case-studies/artifacts/discussion-276-decision-evidence-context-2026-04-06.md`
- `docs/case-studies/artifacts/pre-execution-review-context-2026-04-06.md`

## Automatic CLI Attempt

The standard `ac debate` path was attempted first with the Claude adapter.

That run failed schema validation because the model returned non-JSON routing text instead of the expected analyst JSON object in this environment.

This is worth recording because it reflects current adapter behavior in the local execution environment, not a judgment on the underlying question.

## Manual Structured Debate

The question was then continued with explicit JSON prompts using the same model family.

### Analyst

- Initial score: `61/100 (Caution)`
- Confidence: `70%`

Summary:

> Pre-execution adversarial review fills a specific gap for high-stakes agent decisions: it captures reasoning challenges before irreversible action, not just what happened after. However, the approach is early-stage, lacks cryptographic rigor, and has no integration with runtime governance. The value proposition is strongest for decisions where consequences are irreversible, review latency is acceptable, and adversarial challenge can surface blind spots. This is complementary to, not a replacement for, post-execution audit.

### Critic

Severity: `medium`

1. Pre-execution review adds latency that can itself become risky in time-sensitive scenarios.
2. Review quality may degrade with scale if teams overuse it or broaden the definition of high-stakes.
3. Decision artifacts capture reasoning quality but not execution correctness, which still depends on runtime validation and post-execution audit.

### Defender

1. Latency is acceptable only for the narrow class of irreversible, non-time-sensitive decisions.
2. The approach should be rare and surgical, not a blanket review layer for every consequential event.
3. Pre-execution review and post-execution audit serve different failure modes and are strongest together.

### Judge

- Verdict: `proceed_with_caution`
- Score delta: `+8`
- Final score: `61 -> 69/100`
- Confidence: `75%`

Judge reasoning:

> Pre-execution review is defensible for a specific niche: irreversible decisions where hours or days of deliberation are acceptable. The critic's operational concerns are real, but the defender successfully narrowed the scope and clarified that this is a complementary layer, not a replacement for runtime governance or post-execution audit.

## Missing Context

- How often these genuinely irreversible, non-time-sensitive decisions appear in practice
- A usable operational definition for `high-stakes` and `irreversible`
- Evidence that adversarial review changes decisions rather than becoming process theater

## Next Actions

1. Define explicit criteria for when this layer should trigger and when it should not.
2. Run a small pilot on 5-10 real decisions and track latency, blind spots surfaced, and decision changes.
3. Collect examples where post-execution audit alone was too late to prevent an avoidable mistake.

## Takeaway

The review supports a narrower claim than "pre-execution review should replace audit."

It supports this claim instead:

- for a small class of irreversible decisions, a structured pre-execution decision artifact may add governance value that post-execution audit alone does not provide
