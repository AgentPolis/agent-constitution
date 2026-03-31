class CostLimitExceeded(RuntimeError):
    """Raised when cumulative cost would exceed the hard limit."""


class CostGuard:
    def __init__(self, soft_limit_usd: float = 1.0, hard_limit_usd: float = 5.0):
        self.soft_limit_usd = soft_limit_usd
        self.hard_limit_usd = hard_limit_usd
        self._total_cost: float = 0.0
        self._calls: list[float] = []

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def record(self, cost_usd: float) -> None:
        new_total = self._total_cost + cost_usd
        if new_total >= self.hard_limit_usd:
            raise CostLimitExceeded(
                f"Hard cost limit ${self.hard_limit_usd} would be exceeded "
                f"(current: ${self._total_cost:.4f}, attempted: ${cost_usd:.4f})"
            )
        self._total_cost = new_total
        self._calls.append(cost_usd)

    def check_soft_limit(self) -> bool:
        """Returns True if soft limit is reached (warning signal, doesn't raise)."""
        return self.total_cost >= self.soft_limit_usd

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def reset(self) -> None:
        self._total_cost = 0.0
        self._calls.clear()
