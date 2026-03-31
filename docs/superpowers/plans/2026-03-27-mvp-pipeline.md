# MVP Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Research → Evaluate → Debate pipeline to agent-constitution so users can run one command and see the full governance workflow in action.

**Architecture:** Three agents (Rex/researcher, Sarah/business_analyst, Cassandra/critic) orchestrated by a `Pipeline` class. Pipeline builds its own 2-agent debate loop (does NOT use the existing `Debate` class which requires a judge). MockAdapter enables zero-config demo; AnthropicAPIAdapter for live mode.

**Tech Stack:** Python 3.11+, pytest, rich (for terminal output), existing agent-constitution framework

**Spec:** `docs/superpowers/specs/2026-03-27-mvp-pipeline-design.md`

---

## Chunk 1: SOUL.md Files and Mock Responses

### Task 1: Create Rex's SOUL.md

**Files:**
- Create: `examples/agents/researcher/SOUL.md`

- [ ] **Step 1: Create the SOUL.md file**

```markdown
# MarketResearcher — Rex

## Mission
Collect raw signals, data, and evidence about a given topic.

## Persona
Thorough and source-obsessed. Rex doesn't editorialize — he finds facts, tags sources,
and surfaces what others miss. Prefers primary sources over summaries.
When in doubt, Rex says "data insufficient" rather than speculating.

## Values
- Primary sources over summaries — always link to the original
- Breadth before depth — scan wide, then drill into the strongest signals
- Source tagging — every claim traced to a URL or dataset
- Silence over fabrication — "no data found" is a valid finding

## Hard Constraints
- Inherits all rules from ../../CONSTITUTION.md
- Every signal must include a source attribution (URL or dataset name)
- Must tag confidence per signal as a float 0.0-1.0
- Must not editorialize or evaluate — only collect and organize
- Output must be valid JSON matching the research brief schema

## Tools
- WebSearch (for market data, news, community signals)

## Collaboration
- **Line**: Research Line
- **Primary collaborators**: business_analyst, critic
- **Pipeline role**: First stage — provides raw material for evaluation
```

- [ ] **Step 2: Verify the file loads with existing Constitution loader**

Run: `python3 -c "from constitution import Constitution; c = Constitution.from_soul_md('examples/agents/researcher/SOUL.md'); print('OK:', 'source attribution' in c.text)"`
Expected: `OK: True` (extracts Hard Constraints section which contains "source attribution")

- [ ] **Step 3: Commit**

```bash
git add examples/agents/researcher/SOUL.md
git commit -m "feat: add Rex (MarketResearcher) SOUL.md"
```

---

### Task 2: Create Sarah's SOUL.md

**Files:**
- Create: `examples/agents/business_analyst/SOUL.md`

- [ ] **Step 1: Create the SOUL.md file**

```markdown
# BusinessAnalyst — Sarah

## Mission
Evaluate business viability with a structured, multi-dimensional assessment.

## Persona
Methodical and data-driven. Sarah breaks problems into dimensions, quantifies uncertainty,
and always presents risks before opportunities. She never overstates confidence.
When evidence is thin, she lowers her scores rather than guessing high.

## Values
- Structured rigor — use the 10-dimension framework, no shortcuts
- Risks before opportunities — bad news first, always
- Quantified uncertainty — every assessment includes a confidence score
- Evidence-based adjustment — revise positions when challenged with evidence

## Hard Constraints
- Inherits all rules from ../../CONSTITUTION.md
- Must score all 10 dimensions (1-5 each, total /50):
  market_size, pain_severity, willingness_to_pay, timing,
  competition, defensibility, founder_market_fit, distribution,
  technical_feasibility, regulatory_risk
- competition and regulatory_risk are inverted (5 = low risk/competition)
- Must include overall confidence score 0.0-1.0
- Must present risks before opportunities in reasoning
- Output must be valid JSON matching the evaluation schema

## Tools
(none — pure thinker, reasons over research data)

## Collaboration
- **Line**: Research Line
- **Primary collaborators**: researcher, critic
- **Pipeline role**: Second stage — evaluates research into structured scores
- **Debate role**: Defender (defends evaluation when challenged by critic)
```

- [ ] **Step 2: Verify the file loads**

Run: `python3 -c "from constitution import Constitution; c = Constitution.from_soul_md('examples/agents/business_analyst/SOUL.md'); print('OK:', 'market_size' in c.text)"`
Expected: `OK: True`

- [ ] **Step 3: Commit**

```bash
git add examples/agents/business_analyst/SOUL.md
git commit -m "feat: add Sarah (BusinessAnalyst) SOUL.md"
```

---

### Task 3: Rename Eve → Cassandra in Critic SOUL.md

**Files:**
- Modify: `examples/agents/critic/SOUL.md`

- [ ] **Step 1: Update the SOUL.md**

Replace the entire content with:

```markdown
# Critic — Cassandra

## Mission
Challenge assumptions, surface blind spots, and stress-test every assessment.

## Persona
Named after the Trojan prophet who spoke truths nobody wanted to hear.
Cassandra doesn't argue for sport — she argues because unchallenged assessments
fail in the real world. Sharp, structured, relentless.
She asks "what are we missing?" and "what has to be true for this to work?"

## Values
- Healthy skepticism — assume the bull case is optimistic until proven otherwise
- Structured challenge — three specific challenges, not vague doubt
- Intellectual honesty — acknowledge when the defense is valid
- Devil's advocate — represent the risks that optimism tends to suppress

## Hard Constraints
- Inherits all rules from ../../CONSTITUTION.md
- Must raise exactly 3 challenges per debate round (no more, no less)
- Must specify severity for each challenge: LOW / MEDIUM / HIGH
- Cannot simply repeat the same challenge reworded — each must be distinct
- Must acknowledge when a defense fully addresses a challenge

## Tools
- WebSearch (to find counterexamples and risk data)
- Read (for due diligence documents)

## Collaboration
- **Line**: Research Line
- **Reports to**: Risk Analyst, CMO
- **Primary collaborators**: business_analyst, judge
- **Debate role**: Challenger (raises challenges to stress-test evaluations)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: All tests pass (no test references "Eve" by name)

- [ ] **Step 3: Commit**

```bash
git add examples/agents/critic/SOUL.md
git commit -m "feat: rename critic Eve → Cassandra"
```

---

### Task 4: Add mock responses for new roles

**Files:**
- Modify: `adapters/mock.py`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: Write failing tests for new mock roles**

Append to `tests/test_adapters.py`:

```python
class TestMockAdapterPipelineRoles:
    def test_detects_researcher_role(self):
        adapter = MockAdapter()
        response = adapter.call(
            messages=[{"role": "user", "content": "Research AI tools"}],
            system_prompt="You are researcher. Goal: Collect signals.",
        )
        data = json.loads(response.content)
        assert "signals" in data

    def test_detects_business_analyst_role(self):
        adapter = MockAdapter()
        response = adapter.call(
            messages=[{"role": "user", "content": "Evaluate opportunity"}],
            system_prompt="You are business_analyst. Goal: Evaluate viability.",
        )
        data = json.loads(response.content)
        assert "dimensions" in data
        assert "total_score" in data

    def test_detects_critic_rebuttal_from_message(self):
        adapter = MockAdapter()
        response = adapter.call(
            messages=[{"role": "user", "content": "This is a critic_rebuttal phase. Defend your position."}],
            system_prompt="You are business_analyst. Goal: Evaluate viability.",
        )
        data = json.loads(response.content)
        assert "defenses" in data

    def test_detects_critic_final_from_message(self):
        adapter = MockAdapter()
        response = adapter.call(
            messages=[{"role": "user", "content": "This is a critic_final phase. Assess the defense."}],
            system_prompt="You are critic. Goal: Challenge assumptions.",
        )
        data = json.loads(response.content)
        assert "assessments" in data

    def test_business_analyst_not_confused_with_analyst(self):
        adapter = MockAdapter()
        response = adapter.call(
            messages=[{"role": "user", "content": "Evaluate this"}],
            system_prompt="You are business_analyst.",
        )
        data = json.loads(response.content)
        # Should match business_analyst (10 dimensions), not analyst (5 dimensions)
        assert "dimensions" in data
        assert "total_score" in data
```

Add `import json` at top of file if not already there.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_adapters.py::TestMockAdapterPipelineRoles -v`
Expected: FAIL — "signals" not in data (researcher returns "default" response)

- [ ] **Step 3: Add mock responses and fix `_detect_role` in `adapters/mock.py`**

**3a. Add new entries to `DEFAULT_RESPONSES` dict** (after `"judge"`, before `"default"`):

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

**3b. Fix `_detect_role` to handle substring collisions and phase markers.**

Two bugs to fix:
1. `"analyst"` is a substring of `"business_analyst"` — so `analyst` key matches when it shouldn't
2. Phase markers (`critic_rebuttal`, `critic_final`) are in user messages, but `_detect_role` only scans system_prompt

Replace the `_detect_role` method and update `call` to pass messages:

```python
    def _detect_role(self, system_prompt: str, messages: list[dict] = None) -> str:
        sorted_keys = sorted(
            (k for k in self.role_responses if k != "default"),
            key=len,
            reverse=True,
        )

        # First: scan user messages for phase markers (higher priority).
        # Phase markers like "critic_rebuttal" are placed in user prompts
        # by the Pipeline and should override the agent's base role.
        if messages:
            msg_text = " ".join(
                msg.get("content", "").lower()
                for msg in messages
                if isinstance(msg.get("content", ""), str)
            )
            for role in sorted_keys:
                if role in msg_text:
                    return role

        # Then: fall back to system prompt for base role detection.
        # Length-descending sort ensures "business_analyst" matches
        # before "analyst".
        lowered = system_prompt.lower()
        for role in sorted_keys:
            if role in lowered:
                return role
        return "default"
```

And update the `call` method to pass messages to `_detect_role`:

```python
        role = self._detect_role(system_prompt, messages)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_adapters.py -v`
Expected: ALL pass (both old and new tests)

- [ ] **Step 5: Commit**

```bash
git add adapters/mock.py tests/test_adapters.py
git commit -m "feat: add mock responses for pipeline roles (researcher, business_analyst, debate phases)"
```

---

## Chunk 2: Pipeline Core

### Task 5: Write PipelineResult dataclass and Pipeline skeleton

**Files:**
- Create: `constitution/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test for PipelineResult**

Create `tests/test_pipeline.py`:

```python
"""Tests for the Pipeline class."""

import json
import pytest

from constitution.pipeline import Pipeline, PipelineResult
from adapters import MockAdapter


class TestPipelineResult:
    def test_pipeline_result_fields(self):
        r = PipelineResult(
            topic="test",
            research="{}",
            evaluation={},
            total_score=0,
            confidence=0.0,
            debate_triggered=False,
            debate_rounds=[],
            cost_usd=0.0,
            duration_ms=0,
        )
        assert r.topic == "test"
        assert r.debate_triggered is False
        assert r.debate_rounds == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_pipeline.py::TestPipelineResult -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'constitution.pipeline'`

- [ ] **Step 3: Create `constitution/pipeline.py` with PipelineResult and Pipeline skeleton**

```python
"""
Pipeline: Research → Evaluate → Debate

Orchestrates three agents (researcher, business_analyst, critic) into an
end-to-end evaluation workflow. Does NOT use the existing Debate class —
implements its own 2-agent debate loop without a judge.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .base_agent import BaseAgent
from .constitution import Constitution
from adapters import LLMAdapter, MockAdapter


@dataclass
class PipelineResult:
    topic: str
    research: str
    evaluation: dict
    total_score: int
    confidence: float
    debate_triggered: bool
    debate_rounds: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    duration_ms: int = 0


# Dimension names for the 10-dimension scoring
DIMENSIONS = [
    "market_size", "pain_severity", "willingness_to_pay", "timing",
    "competition", "defensibility", "founder_market_fit", "distribution",
    "technical_feasibility", "regulatory_risk",
]


class Pipeline:
    def __init__(self, adapter: LLMAdapter = None, score_threshold: int = 30):
        self.adapter = adapter or MockAdapter(simulate_delay_ms=0)
        self.score_threshold = score_threshold

        # Locate SOUL.md files relative to this package
        agents_dir = Path(__file__).parent.parent / "examples" / "agents"

        base_constitution = Constitution.default()

        self.researcher = BaseAgent(
            role="researcher",
            goal="Collect raw signals, data, and evidence about a given topic",
            persona="Thorough and source-obsessed. Finds facts, tags sources, surfaces what others miss.",
            adapter=self.adapter,
            constitution=self._load_soul(agents_dir / "researcher" / "SOUL.md", base_constitution),
        )
        self.analyst = BaseAgent(
            role="business_analyst",
            goal="Evaluate business viability with a structured 10-dimension assessment",
            persona="Methodical and data-driven. Presents risks before opportunities. Never overstates confidence.",
            adapter=self.adapter,
            constitution=self._load_soul(agents_dir / "business_analyst" / "SOUL.md", base_constitution),
        )
        self.critic = BaseAgent(
            role="critic",
            goal="Challenge assumptions, surface blind spots, stress-test every assessment",
            persona="Named after the Trojan prophet Cassandra. Sharp, structured, relentless.",
            adapter=self.adapter,
            constitution=self._load_soul(agents_dir / "critic" / "SOUL.md", base_constitution),
        )

    @staticmethod
    def _load_soul(path: Path, fallback: Constitution) -> Constitution:
        """Load SOUL.md and merge with default constitution. Falls back to default if file missing."""
        try:
            soul = Constitution.from_soul_md(path)
            return fallback.merge(soul)
        except (FileNotFoundError, ValueError):
            return fallback

    def _total_cost(self) -> float:
        return sum(a.get_total_cost() for a in [self.researcher, self.analyst, self.critic])

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse JSON from agent response, with fallback."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"raw": text}

    def run(self, topic: str, max_rounds: int = 1) -> PipelineResult:
        """Run the full pipeline: research → evaluate → debate (if triggered)."""
        start = time.time()

        # Stage 1: Research
        research_prompt = (
            f"Research the following topic and return a JSON object with "
            f'"signals" (list of objects with title, source, confidence) and '
            f'"key_data_points" (list of strings).\n\nTopic: {topic}'
        )
        research_raw = self.researcher.run(research_prompt)
        research_data = self._parse_json(research_raw)

        # Stage 2: Evaluate
        eval_prompt = (
            f"Based on the following research, evaluate the business viability of: {topic}\n\n"
            f"Research data:\n{research_raw}\n\n"
            f"Return a JSON object with:\n"
            f'- "dimensions": object with keys {DIMENSIONS} each scored 1-5\n'
            f'- "total_score": sum of all dimensions (max 50)\n'
            f'- "confidence": float 0.0-1.0\n'
            f'- "reasoning": string explaining the assessment'
        )
        eval_raw = self.analyst.run(eval_prompt)
        eval_data = self._parse_json(eval_raw)

        total_score = eval_data.get("total_score", 0)
        confidence = eval_data.get("confidence", 0.0)

        # Stage 3: Debate (if score meets threshold)
        debate_triggered = total_score >= self.score_threshold
        debate_rounds = []

        if debate_triggered:
            debate_rounds = self._run_debate(topic, eval_raw, eval_data, max_rounds)

        duration_ms = int((time.time() - start) * 1000)

        return PipelineResult(
            topic=topic,
            research=research_raw,
            evaluation=eval_data,
            total_score=total_score,
            confidence=confidence,
            debate_triggered=debate_triggered,
            debate_rounds=debate_rounds,
            cost_usd=self._total_cost(),
            duration_ms=duration_ms,
        )

    def _run_debate(
        self, topic: str, eval_raw: str, eval_data: dict, max_rounds: int,
        existing_history: list[dict] = None,
    ) -> list[dict]:
        """Run debate rounds between critic (Cassandra) and analyst (Sarah)."""
        rounds = list(existing_history or [])

        for round_num in range(max_rounds):
            history_text = self._format_debate_history(rounds)

            # Challenge
            challenge_prompt = (
                f"Topic: {topic}\n\n"
                f"Assessment to challenge:\n{eval_raw}\n\n"
                f"{history_text}"
                f"Generate exactly 3 specific challenges. Return JSON:\n"
                f'{{"challenges": [{{"title": "...", "severity": "LOW|MEDIUM|HIGH", "reasoning": "..."}}], '
                f'"confidence": 0.0-1.0}}'
            )
            challenges_raw = self.critic.run(challenge_prompt)
            challenges_data = self._parse_json(challenges_raw)

            # Rebuttal — use critic_rebuttal phase marker in prompt so MockAdapter can detect it
            rebuttal_prompt = (
                f"Topic: {topic}\n\n"
                f"Your evaluation:\n{eval_raw}\n\n"
                f"Challenges raised:\n{challenges_raw}\n\n"
                f"This is a critic_rebuttal phase. Defend each challenge point-by-point. Return JSON:\n"
                f'{{"defenses": [{{"challenge": 1, "response": "...", "tag": "[verified]|[speculation]"}}], '
                f'"revised_confidence": 0.0-1.0}}'
            )
            rebuttal_raw = self.analyst.run(rebuttal_prompt)
            rebuttal_data = self._parse_json(rebuttal_raw)

            # Final Response — use critic_final phase marker
            final_prompt = (
                f"Topic: {topic}\n\n"
                f"Your challenges:\n{challenges_raw}\n\n"
                f"Defense received:\n{rebuttal_raw}\n\n"
                f"This is a critic_final phase. For each challenge, assess the defense. Return JSON:\n"
                f'{{"assessments": [{{"challenge": 1, "status": "accepted|partially_addressed|unconvinced", '
                f'"reason": "..."}}], "challenges_resolved": N, "total_challenges": 3}}'
            )
            final_raw = self.critic.run(final_prompt)
            final_data = self._parse_json(final_raw)

            rounds.append({
                "round": len(rounds) + 1,
                "challenges": challenges_data,
                "rebuttals": rebuttal_data,
                "final_response": final_data,
            })

        return rounds

    def _format_debate_history(self, rounds: list[dict]) -> str:
        """Format prior debate rounds as context for the next round."""
        if not rounds:
            return ""
        parts = ["Previous debate rounds:\n"]
        for r in rounds:
            parts.append(f"Round {r['round']}:")
            parts.append(f"  Challenges: {json.dumps(r['challenges'])}")
            parts.append(f"  Rebuttals: {json.dumps(r['rebuttals'])}")
            parts.append(f"  Final: {json.dumps(r['final_response'])}")
        parts.append("")
        return "\n".join(parts)

    def continue_debate(self, result: PipelineResult) -> PipelineResult:
        """Add another debate round to an existing result."""
        if not result.debate_triggered:
            return result

        new_rounds = self._run_debate(
            result.topic,
            json.dumps(result.evaluation),
            result.evaluation,
            max_rounds=1,
            existing_history=result.debate_rounds,
        )

        return PipelineResult(
            topic=result.topic,
            research=result.research,
            evaluation=result.evaluation,
            total_score=result.total_score,
            confidence=result.confidence,
            debate_triggered=True,
            debate_rounds=new_rounds,
            cost_usd=self._total_cost(),
            duration_ms=result.duration_ms,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_pipeline.py::TestPipelineResult -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add constitution/pipeline.py tests/test_pipeline.py
git commit -m "feat: add Pipeline class and PipelineResult dataclass"
```

---

### Task 6: Pipeline end-to-end tests

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write end-to-end test**

Append to `tests/test_pipeline.py`:

```python
class TestPipelineEndToEnd:
    def test_mock_end_to_end(self):
        pipeline = Pipeline(adapter=MockAdapter(simulate_delay_ms=0))
        result = pipeline.run("AI code review tool")

        assert result.topic == "AI code review tool"
        assert result.research  # non-empty
        assert result.evaluation  # non-empty dict
        assert result.total_score == 35
        assert result.confidence == 0.72
        assert result.debate_triggered is True  # 35 >= 30
        assert len(result.debate_rounds) == 1
        assert result.cost_usd >= 0.0

    def test_no_debate_below_threshold(self):
        # Use custom mock that returns low score
        low_score_response = (
            '{"dimensions": {'
            '  "market_size": 1, "pain_severity": 1, "willingness_to_pay": 1,'
            '  "timing": 1, "competition": 1, "defensibility": 1,'
            '  "founder_market_fit": 1, "distribution": 1,'
            '  "technical_feasibility": 1, "regulatory_risk": 1'
            '}, "total_score": 10, "confidence": 0.3,'
            '"reasoning": "Weak opportunity across all dimensions."}'
        )
        adapter = MockAdapter(
            role_responses={"business_analyst": low_score_response},
            simulate_delay_ms=0,
        )
        pipeline = Pipeline(adapter=adapter)
        result = pipeline.run("Fax machine social network")

        assert result.total_score == 10
        assert result.debate_triggered is False
        assert result.debate_rounds == []

    def test_debate_triggers_above_threshold(self):
        pipeline = Pipeline(adapter=MockAdapter(simulate_delay_ms=0))
        result = pipeline.run("AI code review tool")

        assert result.debate_triggered is True
        assert len(result.debate_rounds) >= 1
        round1 = result.debate_rounds[0]
        assert "challenges" in round1
        assert "rebuttals" in round1
        assert "final_response" in round1

    def test_custom_threshold(self):
        pipeline = Pipeline(
            adapter=MockAdapter(simulate_delay_ms=0),
            score_threshold=40,
        )
        result = pipeline.run("AI code review tool")
        # Default mock score is 35, below threshold of 40
        assert result.total_score == 35
        assert result.debate_triggered is False

    def test_continue_debate(self):
        pipeline = Pipeline(adapter=MockAdapter(simulate_delay_ms=0))
        result = pipeline.run("AI code review tool")
        assert len(result.debate_rounds) == 1

        result2 = pipeline.continue_debate(result)
        assert len(result2.debate_rounds) == 2
        assert result2.debate_rounds[0]["round"] == 1
        assert result2.debate_rounds[1]["round"] == 2

    def test_cost_tracking(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        pipeline = Pipeline(adapter=adapter)
        result = pipeline.run("AI code review tool")
        # MockAdapter returns cost_usd=0.0, so total is 0.0
        # But cost_usd field should be populated
        assert isinstance(result.cost_usd, float)
```

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest tests/test_pipeline.py -v`
Expected: ALL pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add pipeline end-to-end tests"
```

---

### Task 7: Update `constitution/__init__.py` exports

**Files:**
- Modify: `constitution/__init__.py`

- [ ] **Step 1: Add Pipeline and PipelineResult to exports**

Add to `constitution/__init__.py`:

```python
from .pipeline import Pipeline, PipelineResult
```

And add `"Pipeline", "PipelineResult"` to the `__all__` list.

- [ ] **Step 2: Verify imports work**

Run: `python3 -c "from constitution import Pipeline, PipelineResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/ -q`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add constitution/__init__.py
git commit -m "feat: export Pipeline and PipelineResult from constitution package"
```

---

## Chunk 3: Demo Script and Final Verification

### Task 8: Create demo_pipeline.py

**Files:**
- Create: `examples/demo_pipeline.py`

- [ ] **Step 1: Create the demo script**

```python
#!/usr/bin/env python3
"""
Agent Constitution — Pipeline Demo

Runs the full Research → Evaluate → Debate pipeline.

Usage:
    python examples/demo_pipeline.py "AI code review tool"
    python examples/demo_pipeline.py --live "AI code review tool"
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path so imports work when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from constitution import Pipeline, PipelineResult
from adapters import MockAdapter

try:
    from adapters import AnthropicAPIAdapter
except ImportError:
    AnthropicAPIAdapter = None


def print_header():
    print()
    print("=" * 60)
    print("  Agent Constitution — Pipeline Demo")
    print("  Research → Evaluate → Debate")
    print("=" * 60)
    print()


def print_research(result: PipelineResult):
    data = json.loads(result.research) if isinstance(result.research, str) else result.research
    signals = data.get("signals", [])
    sources = data.get("sources_count", len(signals))
    print(f"  Found {len(signals)} signals from {sources} sources")
    for s in signals:
        conf = s.get("confidence", "?")
        print(f"    - {s.get('title', '?')} ({s.get('source', '?')}) [confidence: {conf}]")
    print()


def print_evaluation(result: PipelineResult):
    dims = result.evaluation.get("dimensions", {})
    # Sort by score to find top/bottom
    sorted_dims = sorted(dims.items(), key=lambda x: x[1], reverse=True)
    top3 = sorted_dims[:3]
    bottom3 = sorted_dims[-3:]

    print(f"  Score: {result.total_score}/50")
    print(f"  Top:    {', '.join(f'{k} ({v})' for k, v in top3)}")
    print(f"  Bottom: {', '.join(f'{k} ({v})' for k, v in bottom3)}")
    print(f"  Confidence: {result.confidence}")
    if result.evaluation.get("reasoning"):
        print(f"  Reasoning: {result.evaluation['reasoning']}")
    print()


def print_debate_round(round_data: dict):
    round_num = round_data.get("round", "?")
    print(f"  --- Round {round_num} ---")
    print()

    # Challenges
    challenges = round_data.get("challenges", {})
    challenge_list = challenges.get("challenges", [])
    if isinstance(challenge_list, list):
        print("  Cassandra challenges:")
        for i, c in enumerate(challenge_list, 1):
            if isinstance(c, dict):
                severity = c.get("severity", "?")
                title = c.get("title", c.get("reasoning", str(c)))
                print(f"    {i}. [{severity}] {title}")
            else:
                print(f"    {i}. {c}")
    print()

    # Rebuttals
    rebuttals = round_data.get("rebuttals", {})
    defense_list = rebuttals.get("defenses", [])
    if isinstance(defense_list, list):
        print("  Sarah rebuts:")
        for d in defense_list:
            if isinstance(d, dict):
                tag = d.get("tag", "")
                print(f"    {d.get('challenge', '?')}. {d.get('response', '?')} {tag}")
            else:
                print(f"    - {d}")
    print()

    # Final response
    final = round_data.get("final_response", {})
    assessments = final.get("assessments", [])
    if isinstance(assessments, list):
        status_icons = {
            "accepted": "\u2705",
            "partially_addressed": "\u26a0\ufe0f",
            "unconvinced": "\u274c",
        }
        print("  Cassandra's final response:")
        for a in assessments:
            if isinstance(a, dict):
                status = a.get("status", "?")
                icon = status_icons.get(status, "?")
                print(f"    {a.get('challenge', '?')}. {icon} {status.replace('_', ' ').title()} — {a.get('reason', '')}")
    print()


def print_summary(result: PipelineResult):
    print(f"  Initial Score: {result.total_score}/50 | Confidence: {result.confidence}")

    if result.debate_rounds:
        last_round = result.debate_rounds[-1]
        final = last_round.get("final_response", {})
        resolved = final.get("challenges_resolved", "?")
        total = final.get("total_challenges", "?")
        print(f"  Challenges resolved: {resolved}/{total}")

        if isinstance(resolved, int) and isinstance(total, int):
            if resolved == total:
                rec = "proceed"
            elif resolved >= total / 2:
                rec = "proceed_with_caution"
            else:
                rec = "reconsider"
            print(f"  Recommendation: {rec}")

    print(f"  Cost: ${result.cost_usd:.4f} | Duration: {result.duration_ms}ms")


def main():
    parser = argparse.ArgumentParser(description="Agent Constitution Pipeline Demo")
    parser.add_argument("topic", help="Topic to research and evaluate")
    parser.add_argument("--live", action="store_true", help="Use real LLM (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--threshold", type=int, default=30, help="Debate trigger threshold (default: 30)")
    args = parser.parse_args()

    print_header()

    if args.live:
        if AnthropicAPIAdapter is None:
            print("Error: anthropic package not installed. Run: pip install anthropic")
            sys.exit(1)
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not set")
            sys.exit(1)
        adapter = AnthropicAPIAdapter(api_key=api_key)
        mode = "Live (Anthropic API)"
    else:
        adapter = MockAdapter(simulate_delay_ms=50)
        mode = "Mock (no API key)"

    print(f"  Mode: {mode}")
    print(f"  Topic: {args.topic}")
    print(f"  Debate threshold: {args.threshold}/50")
    print()

    pipeline = Pipeline(adapter=adapter, score_threshold=args.threshold)

    # Stage 1: Research
    print(f"\U0001f50d Rex (MarketResearcher) — Researching...")
    result = pipeline.run(args.topic)

    print_research(result)

    # Stage 2: Evaluate
    print(f"\U0001f4ca Sarah (BusinessAnalyst) — Evaluating...")
    print_evaluation(result)

    # Stage 3: Debate
    if result.debate_triggered:
        print(f"\u2694\ufe0f Score {result.total_score} \u2265 {args.threshold} \u2192 Debate triggered")
        print()
        for round_data in result.debate_rounds:
            print_debate_round(round_data)
    else:
        print(f"  Score {result.total_score} < {args.threshold} — No debate needed")
        print()

    # Summary
    print("\U0001f4cb Summary")
    print_summary(result)

    # Continue loop
    while result.debate_triggered:
        try:
            user_input = input("\n> Type 'continue' for another round, or Enter to exit: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() != "continue":
            break
        result = pipeline.continue_debate(result)
        latest = result.debate_rounds[-1]
        print()
        print_debate_round(latest)
        print("\U0001f4cb Updated Summary")
        print_summary(result)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test mock mode runs without errors**

Run: `cd /Users/hsing/MySquad/agent-constitution && python3 examples/demo_pipeline.py "AI code review tool"`
Expected: Full output showing research → evaluation → debate → summary (no errors)

- [ ] **Step 3: Test with custom threshold (no debate)**

Run: `python3 examples/demo_pipeline.py --threshold 40 "AI code review tool"`
Expected: Shows research + evaluation, then "Score 35 < 40 — No debate needed"

- [ ] **Step 4: Commit**

```bash
git add examples/demo_pipeline.py
git commit -m "feat: add demo_pipeline.py — full Research → Evaluate → Debate demo"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: ALL tests pass (existing + new pipeline tests)

- [ ] **Step 2: Run demo end-to-end**

Run: `python3 examples/demo_pipeline.py "AI code review tool"`
Expected: Clean output matching the format in the spec

- [ ] **Step 3: Verify existing demos still work**

Run: `python3 examples/demo_debate.py`
Expected: Existing debate demo runs without errors

- [ ] **Step 4: Final commit with all files verified**

Run `git status` to confirm everything is committed and clean.
