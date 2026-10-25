"""Tests de RunningStats y MetricAnalyzer (sin base de datos)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.queries.queries import PipelineQueries
from src.resources.metric_analyzer import MetricAnalyzer, RunningStats


class FakeResult:
    """Imita el Result de SQLAlchemy para mappings().first()."""

    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row

    def mappings(self) -> FakeResult:
        return self

    def first(self) -> dict[str, Any] | None:
        return self.row


class FakeConnection:
    """Conexión falsa que devuelve una fila fija de pipeline_stats."""

    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row

    def execute(self, query: Any, params: dict | None = None) -> FakeResult:
        return FakeResult(self.row)


def test_empty_state() -> None:
    analyzer = MetricAnalyzer()

    assert analyzer.stats == RunningStats()
    assert analyzer.stats.price_avg is None
    assert analyzer.snapshot() == {
        "row_count": 0,
        "price_sum": Decimal("0"),
        "price_min": None,
        "price_max": None,
        "price_avg": None,
    }


def test_single_value_sets_min_and_max() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update(Decimal("42.50"))

    stats = analyzer.stats
    assert stats.count == 1
    assert stats.price_sum == Decimal("42.50")
    assert stats.price_min == stats.price_max == Decimal("42.50")
    assert stats.price_avg == Decimal("42.50")


def test_several_values() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update_batch([Decimal("50"), Decimal("87"), Decimal("14"), Decimal("95")])

    stats = analyzer.stats
    assert stats.count == 4
    assert stats.price_sum == Decimal("246")
    assert stats.price_min == Decimal("14")
    assert stats.price_max == Decimal("95")
    assert stats.price_avg == Decimal("61.5")


def test_negative_values() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update_batch([Decimal("-10"), Decimal("5"), Decimal("-30")])

    stats = analyzer.stats
    assert stats.price_min == Decimal("-30")
    assert stats.price_max == Decimal("5")
    assert stats.price_sum == Decimal("-35")


def test_none_prices_are_ignored() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update_batch([Decimal("50"), None, Decimal("10"), None])

    stats = analyzer.stats
    assert stats.count == 2
    assert stats.price_sum == Decimal("60")
    assert stats.price_avg == Decimal("30")
    assert stats.price_min == Decimal("10")
    assert stats.price_max == Decimal("50")


def test_batch_with_only_none_prices_keeps_state() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update_batch([None, None])

    assert analyzer.stats == RunningStats()


def test_decimal_avoids_float_error() -> None:
    analyzer = MetricAnalyzer()
    analyzer.update_batch([Decimal("0.1")] * 3)

    assert analyzer.stats.price_sum == Decimal("0.3")


def test_incremental_matches_full_recalculation() -> None:
    prices = [Decimal(p) for p in ("50", "87", "64", "20", "14", "95", "95", "62")]
    analyzer = MetricAnalyzer()
    analyzer.update_batch(prices[:3])
    analyzer.update_batch(prices[3:])

    stats = analyzer.stats
    assert stats.count == len(prices)
    assert stats.price_avg == sum(prices) / len(prices)
    assert stats.price_min == min(prices)
    assert stats.price_max == max(prices)


def test_resume_from_initial_state() -> None:
    initial = RunningStats(
        count=2, price_sum=Decimal("30"), price_min=Decimal("10"), price_max=Decimal("20")
    )
    analyzer = MetricAnalyzer(initial)
    analyzer.update(Decimal("5"))

    stats = analyzer.stats
    assert stats.count == 3
    assert stats.price_sum == Decimal("35")
    assert stats.price_min == Decimal("5")
    assert stats.price_max == Decimal("20")


def test_load_from_db_restores_state() -> None:
    row = {
        "row_count": 4,
        "price_sum": Decimal("246.00"),
        "price_min": Decimal("14.00"),
        "price_max": Decimal("95.00"),
        "price_avg": Decimal("61.5000"),
    }
    analyzer = MetricAnalyzer()
    analyzer.update(Decimal("999"))
    analyzer.load_from_db(FakeConnection(row), PipelineQueries())

    stats = analyzer.stats
    assert stats.count == 4
    assert stats.price_sum == Decimal("246.00")
    assert stats.price_min == Decimal("14.00")
    assert stats.price_max == Decimal("95.00")
    assert stats.price_avg == Decimal("61.5")


def test_load_from_db_without_rows_resets_state() -> None:
    row = {"row_count": 0, "price_sum": Decimal("0"), "price_min": None, "price_max": None}
    analyzer = MetricAnalyzer()
    analyzer.update(Decimal("10"))
    analyzer.load_from_db(FakeConnection(row), PipelineQueries())

    assert analyzer.stats == RunningStats()
