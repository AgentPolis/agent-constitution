import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Prediction:
    id: str
    agent_role: str
    claim: str                      # What was predicted
    confidence: float               # 0.0-1.0 at time of prediction
    made_at: datetime
    verify_after_days: int = 7
    outcome: Optional[str] = None   # "correct", "incorrect", "partial"
    verified_at: Optional[datetime] = None
    credibility_delta: float = 0.0


class Retrospective:
    CREDIBILITY_CORRECT = +0.05
    CREDIBILITY_INCORRECT = -0.10
    CREDIBILITY_PARTIAL = +0.01

    def __init__(self):
        self.predictions: list[Prediction] = []
        self.agent_credibility: dict[str, float] = {}  # role -> credibility score

    def record_prediction(
        self,
        agent_role: str,
        claim: str,
        confidence: float,
        verify_after_days: int = 7,
    ) -> Prediction:
        """Record a new prediction for future verification."""
        pred = Prediction(
            id=str(uuid.uuid4()),
            agent_role=agent_role,
            claim=claim,
            confidence=confidence,
            made_at=datetime.now(),
            verify_after_days=verify_after_days,
        )
        self.predictions.append(pred)
        if agent_role not in self.agent_credibility:
            self.agent_credibility[agent_role] = 1.0
        return pred

    def verify(self, prediction_id: str, outcome: str) -> float:
        """
        Mark prediction as verified. outcome: "correct", "incorrect", "partial"
        Returns credibility delta applied.
        """
        pred = next((p for p in self.predictions if p.id == prediction_id), None)
        if not pred:
            raise ValueError(f"Prediction {prediction_id} not found")
        if pred.outcome is not None:
            raise ValueError(f"Prediction {prediction_id} already verified as '{pred.outcome}'")

        delta_map = {
            "correct": self.CREDIBILITY_CORRECT,
            "incorrect": self.CREDIBILITY_INCORRECT,
            "partial": self.CREDIBILITY_PARTIAL,
        }
        delta = delta_map.get(outcome, 0.0)

        pred.outcome = outcome
        pred.verified_at = datetime.now()
        pred.credibility_delta = delta
        self.agent_credibility[pred.agent_role] = max(
            0.0,
            min(2.0, self.agent_credibility.get(pred.agent_role, 1.0) + delta),
        )

        return delta

    def get_pending(self) -> list[Prediction]:
        """Return predictions due for verification (past verify_after_days, not yet verified)."""
        now = datetime.now()
        return [
            p for p in self.predictions
            if p.outcome is None and (now - p.made_at).days >= p.verify_after_days
        ]

    def get_credibility(self, agent_role: str) -> float:
        return self.agent_credibility.get(agent_role, 1.0)

    def summary(self) -> dict:
        verified = [p for p in self.predictions if p.outcome is not None]
        correct = [p for p in verified if p.outcome == "correct"]
        return {
            "total_predictions": len(self.predictions),
            "verified": len(verified),
            "correct": len(correct),
            "accuracy": len(correct) / len(verified) if verified else 0.0,
            "agent_credibility": dict(self.agent_credibility),
        }
