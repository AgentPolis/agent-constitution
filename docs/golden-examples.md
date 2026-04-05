# Golden Examples

These are fixed prompts you can run today to verify that `agent-constitution` is doing more than generic scoring.

All examples assume the default `MockAdapter`, which is deterministic for the same prompt text.

## 1. Deploy Decision With Evidence

Command:

```bash
ac debate "Should we deploy the billing-auth hotfix to production tonight?" \
  --context-file examples/context/deploy/release-checklist.md \
  --context-file examples/context/deploy/rollback-runbook.md \
  --context-file examples/context/deploy/deploy-brief.md
```

What should happen:

- scenario is effectively `deploy`
- analyst dimensions are:
  - `impact`
  - `readiness`
  - `rollback`
  - `blast_radius`
  - `evidence`
- score should clear the debate threshold when the supporting files are attached
- judge output should include:
  - `next_actions`
  - `upgrade_condition`
  - `downgrade_condition`

What you are checking:

- the tool recognizes a deploy-style decision
- the attached files materially change the judgment instead of being ignored
- the output is about rollback, blast radius, monitoring, and ownership
- the result tells you what to prove before shipping

## 2. Pricing Exception

Command:

```bash
ac debate "Should we approve this pricing exception for a strategic enterprise account?"
```

What should happen:

- scenario is effectively `pricing`
- analyst dimensions are:
  - `upside`
  - `precedent_risk`
  - `reversibility`
  - `evidence`
  - `strategic_fit`
- score should usually clear the debate threshold
- judge output should talk about:
  - margin floor
  - precedent guardrails
  - time-boxing the exception

What you are checking:

- the tool does not reuse deploy logic for pricing
- the output is about finance, precedent, and commercial guardrails
- the result gives you concrete conditions for upgrading or downgrading the recommendation

## 3. Organization Design

Command:

```bash
ac debate "Should we reorganize product and engineering into vertical pods before the Q4 launch?"
```

What should happen:

- scenario is effectively `org_design`
- analyst dimensions are:
  - `clarity`
  - `disruption`
  - `timing`
  - `reversibility`
  - `execution_risk`
- this prompt should often stay below the debate threshold in the mock path

What you are checking:

- the tool can decide not to trigger debate
- the initial score is still scenario-aware
- the output reflects launch timing and execution risk rather than generic strategy language

## 4. README / Launch Review As A Decision

Command:

```bash
ac debate "Should we publish this README as-is for public launch?"
```

What should happen:

- the package treats this as a decision review, not generic prose critique
- the output gives you a recommendation plus conditions for shipping

What you are checking:

- you can use Agent Constitution on launch materials
- the framing matters: ask a decision question, not just `review this`

## Why these examples matter

These are useful because they test three different things:

- trigger behavior
- scenario-aware dimensions
- whether attached documents actually change the judgment
- actionability of the final judgment

If all three examples look too similar, the package is not yet doing enough real work.
