# MVP Pipeline Design: Research → Evaluate → Debate

> Spec for the first runnable pipeline in agent-constitution.
> Date: 2026-03-27

---

## Problem

agent-constitution has a working governance framework (constitution injection, adversarial debate engine, retrospective calibration) but no end-to-end pipeline a user can run to see it in action on a real task. The existing demos show individual components; nothing ties them into a workflow.

## Goal

A single command that takes a topic, researches it, evaluates it, and (if the score is high enough) triggers an adversarial debate — all using the existing framework.

Two modes:
- **Mock mode** — zero config, no API key, runs with MockAdapter
- **Live mode** — real LLM calls via AnthropicAPIAdapter

---

## Agents

Three agents for MVP. No Judge — the user acts as judge.

### MarketResearcher — Rex

- **Mission:** Collect raw signals, data, and evidence about a given topic.
- **Persona:** Thorough and source-obsessed. Rex doesn't editorialize — he finds facts, tags sources, and surfaces what others miss. Prefers primary sources over summaries.
- **Tools:** WebSearch
- **Model:** haiku (fast, cheap for research)
- **Output:** Structured JSON research brief with signals, sources, and key data points.

### BusinessAnalyst — Sarah

- **Mission:** Evaluate business viability with a structured, multi-dimensional assessment.
- **Persona:** Methodical and data-driven. Sarah breaks problems into dimensions, quantifies uncertainty, and always presents risks before opportunities. She never overstates confidence.
- **Tools:** none (pure thinker — reasons over Rex's research)
- **Model:** sonnet (needs deeper reasoning for evaluation)
- **Output:** 10-dimension score (each 1-5, total /50), reasoning per dimension, overall confidence score 0.0-1.0.

### Critic — Cassandra

- **Mission:** Challenge assumptions, surface blind spots, stress-test every assessment.
- **Persona:** Named after the Trojan prophet who spoke truths nobody wanted to hear. Cassandra doesn't argue for sport — she argues because unchallenged assessments fail in the real world. Sharp, structured, relentless.
- **Tools:** none (pure thinker)
- **Model:** haiku (challenger needs speed, not depth)
- **Output:** Exactly 3 challenges per round, each with severity (LOW/MEDIUM/HIGH) and specific evidence or reasoning.

---

## Debate Approach

**The pipeline does NOT use the existing `Debate` class.** The existing `debate.py` requires 3 agents (challenger, defender, judge) and runs a single round. Our MVP needs 2 agents and multiple rounds with no judge.

Instead, `pipeline.py` implements its own debate loop by calling `BaseAgent.run()` directly for each step:

```python
# Round structure (each round = 3 agent calls)
for round_num in range(max_rounds):
    challenges = cassandra.run(challenge_prompt + debate_history)
    rebuttals = sarah.run(rebuttal_prompt + challenges)
    final = cassandra.run(final_response_prompt + rebuttals)
    debate_history.append(round_record)
```

The existing `Debate` class and `DebateResult` remain untouched — they serve the generic 3-agent debate use case (and the existing demos). The pipeline's debate is a simpler, purpose-built loop.

---

## Pipeline API

```python
@dataclass
class PipelineResult:
    topic: str
    research: str                    # Rex's raw research brief
    evaluation: dict                 # Sarah's scored assessment (parsed from JSON)
    total_score: int                 # Sum of 10 dimensions (/50)
    confidence: float                # 0.0-1.0
    debate_triggered: bool
    debate_rounds: list[dict]        # Each: {challenges, rebuttals, final_response}
    cost_usd: float                  # Total pipeline cost (summed across all agents)
    duration_ms: int

class Pipeline:
    def __init__(self, adapter: LLMAdapter = None, score_threshold: int = 30):
        """
        adapter: LLMAdapter instance. Defaults to MockAdapter.
        score_threshold: minimum score to trigger debate. Default 30 (/50).
        """
        # Creates 3 BaseAgent instances internally:
        #   researcher: role="researcher", constitution=Constitution.from_soul_md("examples/agents/researcher/SOUL.md")
        #   analyst:    role="business_analyst", constitution=Constitution.from_soul_md("examples/agents/business_analyst/SOUL.md")
        #   critic:     role="critic", constitution=Constitution.from_soul_md("examples/agents/critic/SOUL.md")
        #
        # Agent role strings use snake_case to match MockAdapter response keys.

    def run(self, topic: str, max_rounds: int = 1) -> PipelineResult:
        """Run the full pipeline: research → evaluate → debate (if triggered)."""

    def continue_debate(self, result: PipelineResult) -> PipelineResult:
        """Add another debate round to an existing result."""

    def _total_cost(self) -> float:
        """Sum cost_usd across all 3 agents."""
        return sum(a.get_total_cost() for a in [self.researcher, self.analyst, self.critic])
```

### Agent Role Strings

| Agent | `role` param | Mock key | Why |
|-------|-------------|----------|-----|
| Rex | `"researcher"` | `"researcher"` | Substring match works: "researcher" in system prompt |
| Sarah | `"business_analyst"` | `"business_analyst"` | Role string includes underscore to match mock key exactly |
| Cassandra | `"critic"` | `"critic"` | Uses existing mock key |

### Cost Tracking

CostGuard is per-agent (each BaseAgent has its own instance). The Pipeline tracks total cost by summing across all 3 agents via `_total_cost()`. No shared CostGuard needed — the pipeline aggregates at the result level.

### Error Handling

- If Rex returns empty research, Sarah evaluates with a note: "Limited data available — confidence reduced."
- If JSON parsing fails at any stage, fall back to raw text (same pattern as existing `debate.py`).
- Pipeline parses each agent's JSON response into a dict before passing to the next stage.

---

## Pipeline Flow

```
User input: topic string
    │
    ▼
┌──────────────────────────┐
│  Rex (MarketResearcher)   │
│  Research the topic       │
│  Output: research brief   │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Sarah (BusinessAnalyst)  │
│  Evaluate based on        │
│  Rex's research           │
│  Output: 10-dim score     │
└────────────┬─────────────┘
             │
             ▼
        score >= 30?
        ┌────┴────┐
        │ no      │ yes
        ▼         ▼
   Output eval  ┌──────────────────┐
   only         │  Debate Loop      │
                │  Cassandra vs     │
                │  Sarah            │
                │  (1 round default)│
                └────────┬─────────┘
                         │
                         ▼
                  Output: eval +
                  debate record +
                  summary
                         │
                         ▼
                  User: "continue"?
                  ┌────┴────┐
                  │ no      │ yes
                  ▼         ▼
               Done      continue_debate()
```

### Debate Round Structure

Each round = 3 agent calls:

1. **Challenge** — Cassandra raises 3 specific challenges against Sarah's evaluation, each tagged with severity.
2. **Rebuttal** — Sarah defends each challenge point-by-point, providing evidence or revising her position.
3. **Final Response** — Cassandra gives closing assessment per challenge: accepted (✅), partially addressed (⚠️), or unconvinced (❌).

### Debate Trigger Threshold

Score >= 30/50 (60%). Below 30, the opportunity is not worth debating — output the evaluation and move on. This is independent of `Debate.SCORE_THRESHOLD` (32/40) which is used by the existing generic debate demo.

### Continue Mechanism

```python
# In demo_pipeline.py
result = pipeline.run(topic)
print_result(result)

while True:
    user_input = input("\n> Type 'continue' for another round, or Enter to exit: ")
    if user_input.strip().lower() != "continue":
        break
    result = pipeline.continue_debate(result)
    print_latest_round(result)
```

In mock mode, `continue_debate()` returns a new round with different mock responses (round-aware mock data) so the output isn't identical each time.

---

## 10 Evaluation Dimensions

Each scored 1-5. Total: /50.

1. Market Size
2. Pain Severity
3. Willingness to Pay
4. Timing / Urgency
5. Competition Intensity (inverted: 5 = low competition)
6. Defensibility / Moat
7. Founder-Market Fit
8. Distribution Channel
9. Technical Feasibility
10. Regulatory Risk (inverted: 5 = low risk)

---

## Mock Responses

Added to `adapters/mock.py` `DEFAULT_RESPONSES`:

```python
"researcher": (
    '{"signals": ['
    '  {"title": "Growing demand for AI-assisted development", "source": "Reddit r/programming", "confidence": 0.82},'
    '  {"title": "3 funded competitors launched in last 6 months", "source": "ProductHunt", "confidence": 0.90},'
    '  {"title": "Developer survey: 67% want better code review tools", "source": "StackOverflow 2025", "confidence": 0.85}'
    '], "sources_count": 5, "key_data_points": ['
    '  "TAM estimate: $5.2B (Gartner 2025)",'
    '  "Average team spends 4.5 hrs/week on code review",'
    '  "Top pain: inconsistent review quality across team members"'
    ']}'
),

"business_analyst": (
    '{"dimensions": {'
    '  "market_size": 4, "pain_severity": 4, "willingness_to_pay": 3,'
    '  "timing": 4, "competition": 2, "defensibility": 2,'
    '  "founder_market_fit": 4, "distribution": 3,'
    '  "technical_feasibility": 4, "regulatory_risk": 5'
    '}, "total_score": 35, "confidence": 0.72,'
    '"reasoning": "Strong market fundamentals with clear pain point. '
    'Main risks: crowded market and weak moat. Timing is favorable '
    'as AI tooling adoption accelerates."}'
),
```

### Mock Debate Responses

The debate phase reuses the `"critic"` mock key for Cassandra's challenges. Sarah's rebuttals and Cassandra's final responses need dedicated mock keys:

```python
"critic_rebuttal": (
    '{"defenses": ['
    '  {"challenge": 1, "response": "TAM sourced from Gartner 2025 report — revised to $5.2B", "tag": "[verified]"},'
    '  {"challenge": 2, "response": "23% of survey respondents indicated budget allocation", "tag": "[verified]"},'
    '  {"challenge": 3, "response": "Competitors focus on enterprise; our wedge is indie developers", "tag": "[speculation]"}'
    '], "revised_confidence": 0.68}'
),

"critic_final": (
    '{"assessments": ['
    '  {"challenge": 1, "status": "accepted", "reason": "Evidence sufficient"},'
    '  {"challenge": 2, "status": "partially_addressed", "reason": "Survey sample size unclear"},'
    '  {"challenge": 3, "status": "unconvinced", "reason": "Indie wedge unproven at scale"}'
    '], "challenges_resolved": 1, "total_challenges": 3}'
),
```

### Round-Aware Mock Data

For `continue_debate()`, the Pipeline passes the round number in the prompt context. MockAdapter doesn't need round awareness — it returns the same structured response each time. This is acceptable for mock mode because:
- The purpose of mock mode is to verify the pipeline wiring, not to simulate realistic multi-round evolution.
- In live mode, the LLM naturally produces different responses because the full debate history is in the prompt context.
- If deterministic variation is needed for demos, the Pipeline can inject `round_num` into the mock key lookup (e.g., `"critic_round_2"`) as a future enhancement.

---

## SOUL.md Loading

Each agent's SOUL.md is loaded via `Constitution.from_soul_md(path)`, which extracts the `## Hard Constraints` section and merges it with the base `CONSTITUTION.md` rules. This is the existing mechanism — no changes needed.

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `examples/agents/researcher/SOUL.md` | Rex's identity |
| `examples/agents/business_analyst/SOUL.md` | Sarah's identity |
| `constitution/pipeline.py` | Pipeline class: research → evaluate → debate loop |
| `examples/demo_pipeline.py` | CLI entry point for full pipeline |
| `tests/test_pipeline.py` | Pipeline tests |

### Modified Files

| File | Change |
|------|--------|
| `examples/agents/critic/SOUL.md` | Rename Eve → Cassandra, update persona (existing `demo_debate.py` still works — it only reads the SOUL.md content, not the persona name) |
| `adapters/mock.py` | Add `researcher` and `business_analyst` mock responses |
| `constitution/__init__.py` | Export `Pipeline`, `PipelineResult` |

### Unchanged

- `constitution/debate.py` — not used by pipeline; kept for generic 3-agent debate demos
- `constitution/base_agent.py` — reuse as-is
- `constitution/constitution.py` — reuse as-is
- `constitution/cost_guard.py`, `trace.py`, `retrospective.py` — reuse as-is
- `adapters/base.py`, `adapters/anthropic_api.py`, `adapters/claude_cli.py` — unchanged
- Existing SOUL.md files for analyst/judge — kept as generic examples

---

## Test Plan

`tests/test_pipeline.py`:

1. **test_pipeline_mock_end_to_end** — run full pipeline with MockAdapter, verify PipelineResult has research, evaluation, score, and debate record
2. **test_pipeline_no_debate_below_threshold** — score < 30 skips debate, `debate_triggered` is False
3. **test_pipeline_debate_triggers_above_threshold** — score >= 30 triggers debate, `debate_rounds` is non-empty
4. **test_continue_debate** — call `continue_debate()`, verify a new round is appended
5. **test_pipeline_cost_tracking** — verify `cost_usd` accumulates across all agent calls
6. **test_pipeline_custom_threshold** — pass `score_threshold=40`, verify debate only triggers at 40+

---

## Output Format (Terminal)

```
🔍 Rex (MarketResearcher) — Researching...
  Found 3 signals from 5 sources

📊 Sarah (BusinessAnalyst) — Evaluating...
  Score: 35/50
  Top: Market Size (4), Pain Severity (4), Timing (4)
  Bottom: Competition (2), Defensibility (2)
  Confidence: 0.72

⚔️ Score 35 ≥ 30 → Debate triggered

  Cassandra challenges:
    1. [HIGH] Market size estimate unsourced — $8B TAM appears speculative
    2. [MEDIUM] No evidence of willingness to pay
    3. [MEDIUM] Three funded competitors already in market

  Sarah rebuts:
    1. TAM from Gartner 2025 — revised to $5.2B [verified]
    2. 23% survey respondents indicated budget [verified]
    3. Competitors target enterprise; wedge is indie devs

  Cassandra's final response:
    1. ✅ Accepted — evidence sufficient
    2. ⚠️ Partially addressed — sample size unclear
    3. ❌ Unconvinced — indie wedge unproven

📋 Summary
  Initial Score: 35/50 | Confidence: 0.72
  Challenges resolved: 1/3
  Recommendation: proceed_with_caution

> Type "continue" for another round, or Enter to exit
```

---

## Run Commands

```bash
# Mock mode (zero config)
python examples/demo_pipeline.py "AI code review tool"

# Live mode (real LLM)
ANTHROPIC_API_KEY=sk-ant-... python examples/demo_pipeline.py --live "AI code review tool"
```

---

## Future (GitHub release, not MVP)

- Discord integration: one bot, webhook-based multi-identity (Rex/Sarah/Cassandra each post as themselves)
- Judge agent (Solomon) as optional auto-judge
- More agents: RiskAnalyst (Marcus), UserResearcher (Luna), etc.
- Retrospective calibration: track whether past evaluations were correct
- MCP integration for external tool access
