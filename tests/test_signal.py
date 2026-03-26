"""
Tests for Signal dataclass and SignalPool.
"""

from datetime import datetime, timedelta

import pytest

from constitution import Signal, SignalPool


def _make_signal(
    title: str = "Markets rise",
    source: str = "source_a",
    direction: str = "bullish",
    confidence: float = 0.80,
    timestamp: datetime = None,
) -> Signal:
    return Signal(
        tier="tier1",
        direction=direction,
        title=title,
        summary="A test signal.",
        source=source,
        confidence=confidence,
        timestamp=timestamp or datetime.now(),
        tags=[],
    )


class TestSignalDataclass:
    def test_signal_has_tier(self):
        s = _make_signal()
        assert hasattr(s, "tier")

    def test_signal_has_direction(self):
        s = _make_signal()
        assert hasattr(s, "direction")

    def test_signal_has_title(self):
        s = _make_signal()
        assert hasattr(s, "title")

    def test_signal_has_summary(self):
        s = _make_signal()
        assert hasattr(s, "summary")

    def test_signal_has_source(self):
        s = _make_signal()
        assert hasattr(s, "source")

    def test_signal_confidence_is_float(self):
        s = _make_signal(confidence=0.75)
        assert isinstance(s.confidence, float)

    def test_signal_has_timestamp(self):
        s = _make_signal()
        assert isinstance(s.timestamp, datetime)

    def test_signal_tags_default_empty(self):
        s = Signal(
            tier="tier2",
            direction="bearish",
            title="test",
            summary="test",
            source="src",
            confidence=0.5,
            timestamp=datetime.now(),
        )
        assert s.tags == []

    def test_signal_raw_data_default_none(self):
        s = _make_signal()
        assert s.raw_data is None


class TestSignalPoolIngest:
    def test_ingest_new_signal_returns_true(self):
        pool = SignalPool()
        s = _make_signal()
        assert pool.ingest(s) is True

    def test_ingest_adds_to_pool(self):
        pool = SignalPool()
        s = _make_signal()
        pool.ingest(s)
        assert len(pool.signals) == 1

    def test_ingest_duplicate_same_source_returns_false(self):
        pool = SignalPool()
        now = datetime.now()
        s1 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        s2 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        pool.ingest(s1)
        result = pool.ingest(s2)
        assert result is False

    def test_ingest_duplicate_does_not_add_to_pool(self):
        pool = SignalPool()
        now = datetime.now()
        s1 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        s2 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        pool.ingest(s1)
        pool.ingest(s2)
        assert len(pool.signals) == 1

    def test_ingest_same_title_different_source_returns_true(self):
        pool = SignalPool()
        now = datetime.now()
        s1 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        s2 = _make_signal(title="Markets rise", source="source_b", timestamp=now)
        pool.ingest(s1)
        result = pool.ingest(s2)
        assert result is True

    def test_ingest_same_title_different_source_adds_to_pool(self):
        pool = SignalPool()
        now = datetime.now()
        s1 = _make_signal(title="Markets rise", source="source_a", timestamp=now)
        s2 = _make_signal(title="Markets rise", source="source_b", timestamp=now)
        pool.ingest(s1)
        pool.ingest(s2)
        assert len(pool.signals) == 2

    def test_ingest_outside_dedup_window_is_not_duplicate(self):
        pool = SignalPool(dedup_window_hours=1)
        old_time = datetime.now() - timedelta(hours=2)
        new_time = datetime.now()
        s1 = _make_signal(title="Markets rise", source="source_a", timestamp=old_time)
        s2 = _make_signal(title="Markets rise", source="source_a", timestamp=new_time)
        pool.ingest(s1)
        result = pool.ingest(s2)
        assert result is True


class TestSignalPoolMerge:
    def test_merge_ingests_multiple_signals(self):
        pool = SignalPool()
        signals = [
            _make_signal(title="Signal 1", source="src_a"),
            _make_signal(title="Signal 2", source="src_b"),
            _make_signal(title="Signal 3", source="src_c"),
        ]
        pool.merge(signals)
        assert len(pool.signals) == 3

    def test_merge_deduplicates(self):
        pool = SignalPool()
        now = datetime.now()
        signals = [
            _make_signal(title="Markets rise", source="src_a", timestamp=now),
            _make_signal(title="Markets rise", source="src_a", timestamp=now),
        ]
        pool.merge(signals)
        assert len(pool.signals) == 1


class TestSignalPoolCrossReference:
    def test_cross_reference_returns_signals_confirmed_by_two_sources(self):
        pool = SignalPool()
        now = datetime.now()
        pool.ingest(_make_signal(title="Markets rise", source="src_a", direction="bullish", timestamp=now))
        pool.ingest(_make_signal(title="Markets rise", source="src_b", direction="bullish", timestamp=now))
        confirmed = pool.cross_reference()
        assert len(confirmed) == 2

    def test_cross_reference_empty_if_only_one_source(self):
        pool = SignalPool()
        pool.ingest(_make_signal(title="Single source signal", source="src_a"))
        confirmed = pool.cross_reference()
        assert confirmed == []

    def test_cross_reference_does_not_return_single_source_signals(self):
        pool = SignalPool()
        now = datetime.now()
        pool.ingest(_make_signal(title="Common topic", source="src_a", direction="bullish", timestamp=now))
        pool.ingest(_make_signal(title="Common topic", source="src_b", direction="bullish", timestamp=now))
        pool.ingest(_make_signal(title="Unique topic", source="src_c", direction="bearish", timestamp=now))
        confirmed = pool.cross_reference()
        titles = [s.title for s in confirmed]
        assert "Unique topic" not in titles
        assert all(t == "Common topic" for t in titles)


class TestSignalPoolGetActionable:
    def test_get_actionable_filters_by_min_confidence(self):
        pool = SignalPool()
        pool.ingest(_make_signal(title="High confidence", confidence=0.9))
        pool.ingest(_make_signal(title="Low confidence", confidence=0.4))
        actionable = pool.get_actionable(min_confidence=0.65)
        assert len(actionable) == 1
        assert actionable[0].title == "High confidence"

    def test_get_actionable_sorts_by_confidence_descending(self):
        pool = SignalPool()
        pool.ingest(_make_signal(title="Medium", source="a", confidence=0.75))
        pool.ingest(_make_signal(title="Highest", source="b", confidence=0.95))
        pool.ingest(_make_signal(title="High", source="c", confidence=0.85))
        actionable = pool.get_actionable(min_confidence=0.65)
        confidences = [s.confidence for s in actionable]
        assert confidences == sorted(confidences, reverse=True)

    def test_get_actionable_at_exact_threshold(self):
        pool = SignalPool()
        pool.ingest(_make_signal(title="At threshold", confidence=0.65))
        actionable = pool.get_actionable(min_confidence=0.65)
        assert len(actionable) == 1

    def test_get_actionable_empty_pool_returns_empty(self):
        pool = SignalPool()
        assert pool.get_actionable() == []


class TestSignalPoolClear:
    def test_clear_empties_pool(self):
        pool = SignalPool()
        pool.ingest(_make_signal(title="s1"))
        pool.ingest(_make_signal(title="s2", source="src_b"))
        pool.clear()
        assert pool.signals == []

    def test_clear_allows_re_ingest(self):
        pool = SignalPool()
        s = _make_signal()
        pool.ingest(s)
        pool.clear()
        result = pool.ingest(s)
        assert result is True
