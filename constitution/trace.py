from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TraceEntry:
    timestamp: datetime
    prompt: str
    response: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class RunTrace:
    def __init__(self, agent_role: str):
        self.agent_role = agent_role
        self.entries: list[TraceEntry] = []

    def record(
        self,
        prompt: str,
        response: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
    ) -> None:
        self.entries.append(TraceEntry(
            timestamp=datetime.now(),
            prompt=prompt,
            response=response,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
        ))

    def to_dict(self) -> dict:
        return {
            "agent_role": self.agent_role,
            "total_entries": len(self.entries),
            "entries": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "tokens_in": e.tokens_in,
                    "tokens_out": e.tokens_out,
                    "cost_usd": e.cost_usd,
                    "prompt_preview": e.prompt[:100],
                    "response_preview": e.response[:100],
                }
                for e in self.entries
            ],
        }

    def summary(self) -> str:
        total_cost = sum(e.cost_usd for e in self.entries)
        total_tokens = sum(e.tokens_in + e.tokens_out for e in self.entries)
        return (
            f"[{self.agent_role}] {len(self.entries)} calls, "
            f"{total_tokens} tokens, ${total_cost:.4f}"
        )
