"""
Tests for CostGuard.
"""

import pytest

from constitution import CostGuard
from constitution.cost_guard import CostLimitExceeded


class TestCostGuardRecord:
    def test_record_accumulates_total_cost(self):
        guard = CostGuard()
        guard.record(0.50)
        guard.record(0.25)
        assert abs(guard.total_cost - 0.75) < 1e-9

    def test_record_single_call(self):
        guard = CostGuard()
        guard.record(1.23)
        assert abs(guard.total_cost - 1.23) < 1e-9

    def test_record_raises_runtime_error_when_hard_limit_exceeded(self):
        guard = CostGuard(soft_limit_usd=1.0, hard_limit_usd=2.0)
        with pytest.raises(RuntimeError):
            guard.record(3.0)

    def test_record_raises_at_exactly_hard_limit(self):
        guard = CostGuard(hard_limit_usd=1.0)
        with pytest.raises(RuntimeError):
            guard.record(1.0)

    def test_record_does_not_raise_below_hard_limit(self):
        guard = CostGuard(hard_limit_usd=5.0)
        guard.record(4.99)  # should not raise


class TestCostGuardSoftLimit:
    def test_check_soft_limit_returns_true_when_over(self):
        guard = CostGuard(soft_limit_usd=1.0, hard_limit_usd=10.0)
        guard.record(1.50)
        assert guard.check_soft_limit() is True

    def test_check_soft_limit_returns_false_when_under(self):
        guard = CostGuard(soft_limit_usd=1.0)
        guard.record(0.50)
        assert guard.check_soft_limit() is False

    def test_check_soft_limit_true_at_exact_limit(self):
        guard = CostGuard(soft_limit_usd=1.0, hard_limit_usd=10.0)
        guard.record(1.0)
        assert guard.check_soft_limit() is True


class TestCostGuardCallCount:
    def test_call_count_increments(self):
        guard = CostGuard()
        assert guard.call_count == 0
        guard.record(0.01)
        assert guard.call_count == 1
        guard.record(0.01)
        assert guard.call_count == 2

    def test_call_count_starts_at_zero(self):
        guard = CostGuard()
        assert guard.call_count == 0

    def test_call_count_not_incremented_on_hard_limit_exceeded(self):
        """Pre-check: cost is NOT recorded if it would exceed hard limit."""
        guard = CostGuard(hard_limit_usd=1.0)
        try:
            guard.record(2.0)
        except RuntimeError:
            pass
        assert guard.call_count == 0
        assert guard.total_cost == 0.0


class TestCostGuardReset:
    def test_reset_clears_total_cost(self):
        guard = CostGuard()
        guard.record(0.50)
        guard.reset()
        assert guard.total_cost == 0.0

    def test_reset_clears_call_count(self):
        guard = CostGuard()
        guard.record(0.10)
        guard.record(0.10)
        guard.reset()
        assert guard.call_count == 0

    def test_reset_allows_re_record(self):
        guard = CostGuard(hard_limit_usd=5.0)
        guard.record(3.0)
        guard.reset()
        guard.record(3.0)  # would exceed original cumulative but not after reset
        assert abs(guard.total_cost - 3.0) < 1e-9


class TestCostGuardTotalCostProperty:
    def test_total_cost_is_accessible(self):
        guard = CostGuard()
        _ = guard.total_cost

    def test_total_cost_starts_at_zero(self):
        guard = CostGuard()
        assert guard.total_cost == 0.0

    def test_total_cost_reflects_all_records(self):
        guard = CostGuard()
        guard.record(0.10)
        guard.record(0.20)
        guard.record(0.30)
        assert abs(guard.total_cost - 0.60) < 1e-9
