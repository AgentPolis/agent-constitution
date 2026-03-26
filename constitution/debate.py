import json
from dataclasses import dataclass, field
from .base_agent import BaseAgent


@dataclass
class DebateResult:
    verdict: str                    # "proceed", "reject", "proceed_with_caution", "reconsider"
    score_delta: int                # Positive or negative adjustment
    reasoning: str
    challenges: list[str] = field(default_factory=list)
    defenses: list[str] = field(default_factory=list)
    audit_trail: list[dict] = field(default_factory=list)


class Debate:
    SCORE_THRESHOLD = 32            # Trigger debate when score >= this

    def __init__(self, challenger: BaseAgent, defender: BaseAgent, judge: BaseAgent):
        self.challenger = challenger
        self.defender = defender
        self.judge = judge

    def should_trigger(self, score: int) -> bool:
        return score >= self.SCORE_THRESHOLD

    def run(self, topic: str, initial_score: int = 35) -> DebateResult:
        """
        Run a structured adversarial debate.
        1. Challenger generates 3 challenges
        2. Defender responds to each
        3. Judge evaluates and returns verdict + score_delta
        """
        audit_trail = []
        challenges = []
        defenses = []

        # Step 1: Challenger generates challenges
        challenger_prompt = f"""Topic: {topic}

Generate exactly 3 specific challenges to this assessment. Format as JSON:
{{"challenges": ["challenge1", "challenge2", "challenge3"], "severity": "low|medium|high"}}"""

        challenger_response = self.challenger.run(challenger_prompt)
        audit_trail.append({"role": "challenger", "content": challenger_response})

        # Parse challenges (with fallback)
        try:
            data = json.loads(challenger_response)
            challenges = data.get("challenges", [challenger_response])
        except (json.JSONDecodeError, AttributeError):
            challenges = [challenger_response]

        # Step 2: Defender responds
        defender_prompt = f"""Topic: {topic}

Challenges raised:
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(challenges))}

Provide a defense for each challenge. Format as JSON:
{{"defenses": ["defense1", "defense2", "defense3"], "confidence": 0.0-1.0}}"""

        defender_response = self.defender.run(defender_prompt)
        audit_trail.append({"role": "defender", "content": defender_response})

        try:
            data = json.loads(defender_response)
            defenses = data.get("defenses", [defender_response])
        except (json.JSONDecodeError, AttributeError):
            defenses = [defender_response]

        # Step 3: Judge evaluates
        judge_prompt = f"""Topic: {topic}
Initial score: {initial_score}/40

Challenges: {challenges}
Defenses: {defenses}

Evaluate the debate and return verdict. Format as JSON:
{{"verdict": "proceed|reject|proceed_with_caution|reconsider", "score_delta": -10 to +5, "reasoning": "...", "confidence": 0.0-1.0}}"""

        judge_response = self.judge.run(judge_prompt)
        audit_trail.append({"role": "judge", "content": judge_response})

        try:
            data = json.loads(judge_response)
            verdict = data.get("verdict", "proceed_with_caution")
            score_delta = data.get("score_delta", -3)
            reasoning = data.get("reasoning", judge_response)
        except (json.JSONDecodeError, AttributeError):
            verdict = "proceed_with_caution"
            score_delta = -3
            reasoning = judge_response

        return DebateResult(
            verdict=verdict,
            score_delta=score_delta,
            reasoning=reasoning,
            challenges=challenges,
            defenses=defenses,
            audit_trail=audit_trail,
        )
