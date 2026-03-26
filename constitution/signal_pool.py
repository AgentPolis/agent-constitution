import re
from datetime import datetime, timedelta
from .signal import Signal


class SignalPool:
    def __init__(self, dedup_window_hours: int = 24):
        self.signals: list[Signal] = []
        self.dedup_window_hours = dedup_window_hours

    def _normalize_title(self, title: str) -> str:
        """Lowercase and remove punctuation for comparison."""
        return re.sub(r'[^\w\s]', '', title.lower()).strip()

    def _is_duplicate(self, signal: Signal) -> bool:
        """Check if signal is a duplicate within the dedup window."""
        window_start = signal.timestamp - timedelta(hours=self.dedup_window_hours)
        normalized = self._normalize_title(signal.title)
        for existing in self.signals:
            if existing.timestamp < window_start:
                continue
            if (existing.direction == signal.direction and
                    self._normalize_title(existing.title) == normalized):
                return True
        return False

    def ingest(self, signal: Signal) -> bool:
        """Add signal if not duplicate. Returns True if added."""
        if self._is_duplicate(signal):
            return False
        self.signals.append(signal)
        return True

    def merge(self, signals: list[Signal]) -> None:
        """Ingest multiple signals, deduplicating."""
        for signal in signals:
            self.ingest(signal)

    def cross_reference(self) -> list[Signal]:
        """Return signals confirmed by 2+ sources (same direction + similar title)."""
        from collections import defaultdict
        groups: dict[tuple, list[Signal]] = defaultdict(list)
        for signal in self.signals:
            key = (signal.direction, self._normalize_title(signal.title))
            groups[key].append(signal)

        result = []
        for key, group_signals in groups.items():
            sources = {s.source for s in group_signals}
            if len(sources) >= 2:
                result.extend(group_signals)
        return result

    def get_actionable(self, min_confidence: float = 0.65) -> list[Signal]:
        """Return signals above confidence threshold, sorted by confidence desc."""
        filtered = [s for s in self.signals if s.confidence >= min_confidence]
        return sorted(filtered, key=lambda s: s.confidence, reverse=True)

    def clear(self) -> None:
        self.signals.clear()
