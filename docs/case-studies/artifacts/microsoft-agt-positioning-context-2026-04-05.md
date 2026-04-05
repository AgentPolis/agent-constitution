# Microsoft Agent Governance Toolkit Positioning Context

Verified on 2026-04-05 from the public repository and Microsoft open source blog.

## Repository Facts

- Repository: `microsoft/agent-governance-toolkit`
- URL: <https://github.com/microsoft/agent-governance-toolkit>
- Stars at time of review: `689`
- License: `MIT`
- Default branch: `main`

## Public Positioning

The project describes itself as runtime governance infrastructure for AI agents.

Its README says the toolkit provides:

- deterministic policy enforcement
- zero-trust identity
- execution sandboxing
- reliability engineering

It explicitly says it sits between an agent framework and the actions agents take.

It also explicitly says it is not a model safety or prompt guardrails tool, and that it governs agent actions such as:

- tool calls
- resource access
- inter-agent communication

## Claimed Strengths

The README and Microsoft launch materials emphasize:

- 10/10 OWASP Agentic Top 10 coverage
- 9,500+ tests
- multi-language SDK support
- integrations with common frameworks including LangChain, CrewAI, OpenAI Agents, and others
- policy checks before execution
- sub-millisecond enforcement claims for policy evaluation

## Strategic Implication For Agent Constitution

Microsoft Agent Governance Toolkit appears strongest when the main problem is:

- whether an agent action should be allowed
- how to enforce policy before execution
- how to add runtime security controls and governance infrastructure to an agent stack

This is close to, but not identical with, Agent Constitution's stated focus on:

- challenging high-stakes recommendations
- reviewing judgment quality
- using attached documents as evidence in a structured debate

## Main Competitive Question

The real question is not whether the two projects use the same vocabulary.

The real question is whether users will see enough practical difference between:

- action-level runtime enforcement
- decision-level adversarial review

If the distinction is not clear, Agent Constitution may need sharper positioning and more concrete evidence of complementary value.
