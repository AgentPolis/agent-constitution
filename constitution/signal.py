from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Signal:
    tier: str                    # "tier1", "tier2", "tier3"
    direction: str               # "bullish", "bearish", "neutral"
    title: str
    summary: str
    source: str                  # originating source identifier
    confidence: float            # 0.0 - 1.0
    timestamp: datetime
    tags: list[str] = field(default_factory=list)
    raw_data: Optional[dict] = None
