class CostGuard:
    def __init__(self, soft_limit_usd: float = 1.0, hard_limit_usd: float = 5.0):
        self.soft_limit_usd = soft_limit_usd
        self.hard_limit_usd = hard_limit_usd
        self.total_cost: float = 0.0
        self._calls: list[float] = []

    def record(self, cost_usd: float) -> None:
        self.total_cost += cost_usd
        self._calls.append(cost_usd)
        if self.total_cost >= self.hard_limit_usd:
            raise RuntimeError(
                f"Hard cost limit ${self.hard_limit_usd} exceeded (total: ${self.total_cost:.4f})"
            )

    def check_soft_limit(self) -> bool:
        """Returns True if soft limit is reached (warning signal, doesn't raise)."""
        return self.total_cost >= self.soft_limit_usd

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def reset(self) -> None:
        self.total_cost = 0.0
        self._calls.clear()
