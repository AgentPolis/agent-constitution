import json
import logging
from dataclasses import dataclass, field

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

VALID_VERDICTS = {"proceed", "reject", "proceed_with_caution", "reconsider"}


class DebateValidationError(ValueError):
    """Raised when LLM output fails schema validation."""


@dataclass
class DebateResult:
    verdict: str                    # "proceed", "reject", "proceed_with_caution", "reconsider"
    score_delta: int                # Positive or negative adjustment
    reasoning: str
    challenges: list[str] = field(default_factory=list)
    defenses: list[str] = field(default_factory=list)
    audit_trail: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validators — separated from generation per Generator/Validator pattern
# ---------------------------------------------------------------------------

def _validate_challenges(raw: str) -> list[str]:
    """Validate challenger output: must be JSON with 'challenges' list of strings."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise DebateValidationError(f"Challenger returned invalid JSON: {exc}") from exc
    challenges = data.get("challenges")
    if not isinstance(challenges, list) or not all(isinstance(c, str) for c in challenges):
        raise DebateValidationError(
            f"Expected 'challenges' as list[str], got: {type(challenges)}"
        )
    if len(challenges) == 0:
        raise DebateValidationError("Challenger returned empty challenges list")
    return challenges


def _validate_defenses(raw: str) -> list[str]:
    """Validate defender output: must be JSON with 'defenses' list of strings."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise DebateValidationError(f"Defender returned invalid JSON: {exc}") from exc
    defenses = data.get("defenses")
    if not isinstance(defenses, list) or not all(isinstance(d, str) for d in defenses):
        raise DebateValidationError(
            f"Expected 'defenses' as list[str], got: {type(defenses)}"
        )
    return defenses


def _validate_verdict(raw: str) -> tuple[str, int, str]:
    """Validate judge output: must be JSON with verdict, score_delta, reasoning."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise DebateValidationError(f"Judge returned invalid JSON: {exc}") from exc
    verdict = data.get("verdict")
    if verdict not in VALID_VERDICTS:
        raise DebateValidationError(
            f"Invalid verdict '{verdict}', must be one of {VALID_VERDICTS}"
        )
    score_delta = data.get("score_delta")
    if not isinstance(score_delta, (int, float)):
        raise DebateValidationError(f"score_delta must be numeric, got: {type(score_delta)}")
    score_delta = max(-10, min(5, int(score_delta)))
    reasoning = data.get("reasoning", "")
    if not isinstance(reasoning, str):
        raise DebateValidationError(f"reasoning must be string, got: {type(reasoning)}")
    return verdict, score_delta, reasoning


class Debate:
    SCORE_THRESHOLD = 32            # Trigger debate when score >= this

    def __init__(
        self,
        challenger: BaseAgent,
        defender: BaseAgent,
        judge: BaseAgent,
        *,
        strict_validation: bool = True,
    ):
        self.challenger = challenger
        self.defender = defender
        self.judge = judge
        self.strict_validation = strict_validation

    def should_trigger(self, score: int) -> bool:
        return score >= self.SCORE_THRESHOLD

    def run(self, topic: str, initial_score: int = 35) -> DebateResult:
        """
        Run a structured adversarial debate.
        1. Challenger generates challenges → validator checks schema
        2. Defender responds → validator checks schema
        3. Judge evaluates → validator checks schema
        """
        audit_trail = []

        # --- Step 1: Generate + Validate challenges ---
        challenger_prompt = f"""Topic: {topic}

Generate exactly 3 specific challenges to this assessment. Format as JSON:
{{"challenges": ["challenge1", "challenge2", "challenge3"], "severity": "low|medium|high"}}"""

        challenger_response = self.challenger.run(challenger_prompt)
        audit_trail.append({"role": "challenger", "content": challenger_response})

        try:
            challenges = _validate_challenges(challenger_response)
        except DebateValidationError as exc:
            logger.warning("Challenger validation failed: %s", exc)
            if self.strict_validation:
                raise
            challenges = [challenger_response]

        # --- Step 2: Generate + Validate defenses ---
        defender_prompt = f"""Topic: {topic}

Challenges raised:
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(challenges))}

Provide a defense for each challenge. Format as JSON:
{{"defenses": ["defense1", "defense2", "defense3"], "confidence": 0.0-1.0}}"""

        defender_response = self.defender.run(defender_prompt)
        audit_trail.append({"role": "defender", "content": defender_response})

        try:
            defenses = _validate_defenses(defender_response)
        except DebateValidationError as exc:
            logger.warning("Defender validation failed: %s", exc)
            if self.strict_validation:
                raise
            defenses = [defender_response]

        # --- Step 3: Generate + Validate verdict ---
        judge_prompt = f"""Topic: {topic}
Initial score: {initial_score}/40

Challenges: {challenges}
Defenses: {defenses}

Evaluate the debate and return verdict. Format as JSON:
{{"verdict": "proceed|reject|proceed_with_caution|reconsider", "score_delta": -10 to +5, "reasoning": "...", "confidence": 0.0-1.0}}"""

        judge_response = self.judge.run(judge_prompt)
        audit_trail.append({"role": "judge", "content": judge_response})

        try:
            verdict, score_delta, reasoning = _validate_verdict(judge_response)
        except DebateValidationError as exc:
            logger.warning("Judge validation failed: %s", exc)
            if self.strict_validation:
                raise
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
