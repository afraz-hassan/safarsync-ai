"""
test_analytics.py — Unit tests for the analytics module.

Uses a temporary SQLite database (via monkeypatch on ``database.DB_PATH``)
so the real ``safarsync.db`` is never touched.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

import database as db
import analytics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> int:
    """
    Create an isolated temporary database, initialise it, add a vehicle,
    and return the vehicle id.

    ``database.DB_PATH`` is monkey-patched so every connection in the
    module under test points at the temp file.
    """
    db_file = str(tmp_path / "test_safarsync.db")
    monkeypatch.setattr(db, "DB_PATH", db_file)
    db.init_db()
    vid = db.add_vehicle("Test Car", "TEST-0001")
    return vid  # type: ignore[return-value]


# ===================================================================
# calculate_fuel_efficiency
# ===================================================================
class TestCalculateFuelEfficiency:
    """Tests for ``analytics.calculate_fuel_efficiency``."""

    def test_empty_fuel_records(self, tmp_db: int) -> None:
        """No fuel records → empty list."""
        vid = tmp_db
        result = analytics.calculate_fuel_efficiency(vid)
        assert result == []

    def test_single_fuel_record(self, tmp_db: int) -> None:
        """A single fuel record cannot produce an efficiency entry (no prior odometer)."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0, odometer_km=10000)

        result = analytics.calculate_fuel_efficiency(vid)
        # First valid record is consumed as the baseline — no efficiency produced
        assert result == []

    def test_normal_efficiency_calculation(self, tmp_db: int) -> None:
        """Two valid fuel records produce one efficiency entry."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=6000, liters=25.0, odometer_km=10500)

        result = analytics.calculate_fuel_efficiency(vid)
        assert len(result) == 1

        entry = result[0]
        assert "warning" not in entry
        assert entry["distance_km"] == 500
        assert entry["liters"] == 25.0
        assert entry["efficiency_km_per_l"] == 20.0  # 500 / 25
        assert entry["date"] == "2026-01-15"

    def test_three_records_two_efficiencies(self, tmp_db: int) -> None:
        """Three valid records produce two efficiency entries."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=25.0, odometer_km=10500)
        db.add_record(vid, "fuel", "2026-01-20", liters=30.0, odometer_km=11100)

        result = analytics.calculate_fuel_efficiency(vid)
        assert len(result) == 2

        assert result[0]["distance_km"] == 500
        assert result[0]["efficiency_km_per_l"] == 20.0

        assert result[1]["distance_km"] == 600
        assert result[1]["efficiency_km_per_l"] == 20.0

    def test_skip_missing_odometer(self, tmp_db: int) -> None:
        """A record with no odometer reading produces a warning."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=25.0, odometer_km=None)
        db.add_record(vid, "fuel", "2026-01-20", liters=30.0, odometer_km=11000)

        result = analytics.calculate_fuel_efficiency(vid)

        warnings = [r for r in result if "warning" in r]
        assert len(warnings) == 1
        assert "missing odometer" in warnings[0]["warning"].lower()

    def test_skip_missing_liters(self, tmp_db: int) -> None:
        """A record with no liters value produces a warning."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=None, odometer_km=10500)
        db.add_record(vid, "fuel", "2026-01-20", liters=30.0, odometer_km=11000)

        result = analytics.calculate_fuel_efficiency(vid)

        warnings = [r for r in result if "warning" in r]
        assert len(warnings) == 1
        assert "missing or zero liters" in warnings[0]["warning"].lower()

    def test_skip_zero_liters(self, tmp_db: int) -> None:
        """A record with zero liters produces a warning (avoid ÷0)."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=0.0, odometer_km=10500)

        result = analytics.calculate_fuel_efficiency(vid)

        warnings = [r for r in result if "warning" in r]
        assert len(warnings) == 1
        assert "liters" in warnings[0]["warning"].lower()

    def test_skip_zero_distance(self, tmp_db: int) -> None:
        """Two records with the same odometer produce a zero-distance warning."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=25.0, odometer_km=10000)

        result = analytics.calculate_fuel_efficiency(vid)

        warnings = [r for r in result if "warning" in r]
        assert len(warnings) == 1
        assert "zero distance" in warnings[0]["warning"].lower()

    def test_skip_negative_distance(self, tmp_db: int) -> None:
        """An odometer that goes backwards triggers a negative-distance warning."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", liters=25.0, odometer_km=9500)

        result = analytics.calculate_fuel_efficiency(vid)

        warnings = [r for r in result if "warning" in r]
        assert len(warnings) == 1
        assert "negative distance" in warnings[0]["warning"].lower()

    def test_non_fuel_records_ignored(self, tmp_db: int) -> None:
        """Maintenance records must not affect fuel efficiency."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", liters=20.0, odometer_km=10000)
        db.add_record(vid, "maintenance", "2026-01-05", amount_pkr=3000)
        db.add_record(vid, "fuel", "2026-01-10", liters=25.0, odometer_km=10500)

        result = analytics.calculate_fuel_efficiency(vid)
        assert len(result) == 1
        assert result[0]["efficiency_km_per_l"] == 20.0


# ===================================================================
# monthly_spending_summary
# ===================================================================
class TestMonthlySpendingSummary:
    """Tests for ``analytics.monthly_spending_summary``."""

    def test_empty_records(self, tmp_db: int) -> None:
        """No records → empty list."""
        vid = tmp_db
        result = analytics.monthly_spending_summary(vid)
        assert result == []

    def test_single_record(self, tmp_db: int) -> None:
        """A single record produces one group."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-03-15", amount_pkr=5000)

        result = analytics.monthly_spending_summary(vid)
        assert len(result) == 1
        assert result[0]["month"] == "2026-03"
        assert result[0]["record_type"] == "fuel"
        assert result[0]["total_amount"] == 5000.0
        assert result[0]["count"] == 1

    def test_grouping_by_month_and_type(self, tmp_db: int) -> None:
        """Records in the same month and type are aggregated."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-05", amount_pkr=3000)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=4000)
        db.add_record(vid, "maintenance", "2026-01-10", amount_pkr=2000)
        db.add_record(vid, "fuel", "2026-02-05", amount_pkr=5000)

        result = analytics.monthly_spending_summary(vid)

        # Expect 3 groups: Jan-fuel, Jan-maintenance, Feb-fuel
        assert len(result) == 3

        # Sorted: newest month first
        feb = [r for r in result if r["month"] == "2026-02"]
        jan = [r for r in result if r["month"] == "2026-01"]

        assert len(feb) == 1
        assert feb[0]["total_amount"] == 5000.0

        assert len(jan) == 2
        jan_fuel = [r for r in jan if r["record_type"] == "fuel"]
        jan_maint = [r for r in jan if r["record_type"] == "maintenance"]
        assert jan_fuel[0]["total_amount"] == 7000.0
        assert jan_fuel[0]["count"] == 2
        assert jan_maint[0]["total_amount"] == 2000.0

    def test_none_amount_treated_as_zero(self, tmp_db: int) -> None:
        """Records with None amount_pkr must not crash the aggregation."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-04-01", amount_pkr=None)
        db.add_record(vid, "fuel", "2026-04-10", amount_pkr=3000)

        result = analytics.monthly_spending_summary(vid)
        assert len(result) == 1
        assert result[0]["total_amount"] == 3000.0

    def test_sort_order(self, tmp_db: int) -> None:
        """Results are sorted newest-month-first."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=1000)
        db.add_record(vid, "fuel", "2026-03-10", amount_pkr=1000)
        db.add_record(vid, "fuel", "2026-02-10", amount_pkr=1000)

        result = analytics.monthly_spending_summary(vid)
        months = [r["month"] for r in result]
        assert months == ["2026-03", "2026-02", "2026-01"]


# ===================================================================
# total_cost_per_km
# ===================================================================
class TestTotalCostPerKm:
    """Tests for ``analytics.total_cost_per_km``."""

    def test_empty_records(self, tmp_db: int) -> None:
        """No records → None."""
        vid = tmp_db
        assert analytics.total_cost_per_km(vid) is None

    def test_normal_calculation(self, tmp_db: int) -> None:
        """Standard total_spend / (max_odo - min_odo)."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=5000, odometer_km=11000)

        result = analytics.total_cost_per_km(vid)
        assert result == 10.0  # 10000 / 1000

    def test_no_odometer_records(self, tmp_db: int) -> None:
        """Records without odometer → None (cannot compute distance)."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=3000)

        assert analytics.total_cost_per_km(vid) is None

    def test_zero_distance_range(self, tmp_db: int) -> None:
        """All odometers identical → None (avoid ÷0)."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=3000, odometer_km=10000)

        assert analytics.total_cost_per_km(vid) is None

    def test_single_odometer_record(self, tmp_db: int) -> None:
        """Only one record with odometer → distance range is 0 → None."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, odometer_km=10000)

        assert analytics.total_cost_per_km(vid) is None

    def test_zero_spending(self, tmp_db: int) -> None:
        """Odometer range exists but spending is zero → 0.0."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=0, odometer_km=11000)

        assert analytics.total_cost_per_km(vid) == 0.0

    def test_mixed_odometer_and_non_odometer(self, tmp_db: int) -> None:
        """Only records with odometer are used for the range."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, odometer_km=10000)
        db.add_record(vid, "maintenance", "2026-01-10", amount_pkr=2000, odometer_km=None)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=3000, odometer_km=11000)

        result = analytics.total_cost_per_km(vid)
        assert result == 10.0  # (5000+2000+3000) / (11000-10000)


# ===================================================================
# get_summary_metrics
# ===================================================================
class TestGetSummaryMetrics:
    """Tests for ``analytics.get_summary_metrics``."""

    def test_empty_vehicle(self, tmp_db: int) -> None:
        """A vehicle with no records returns safe defaults."""
        vid = tmp_db
        metrics = analytics.get_summary_metrics(vid)

        assert metrics["total_spend"] == 0.0
        assert metrics["fuel_spend"] == 0.0
        assert metrics["maintenance_spend"] == 0.0
        assert metrics["insurance_spend"] == 0.0
        assert metrics["average_fuel_efficiency"] is None
        assert metrics["total_distance"] == 0
        assert metrics["cost_per_km"] is None

    def test_full_scenario(self, tmp_db: int) -> None:
        """A realistic mix of record types produces correct metrics."""
        vid = tmp_db

        # Fuel records
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=6000, liters=25.0, odometer_km=10500)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=7000, liters=30.0, odometer_km=11100)

        # Maintenance
        db.add_record(vid, "maintenance", "2026-01-10", amount_pkr=3000)

        # Insurance
        db.add_record(vid, "insurance", "2026-01-05", amount_pkr=12000)

        metrics = analytics.get_summary_metrics(vid)

        # Spending
        assert metrics["total_spend"] == 33000.0
        assert metrics["fuel_spend"] == 18000.0
        assert metrics["maintenance_spend"] == 3000.0
        assert metrics["insurance_spend"] == 12000.0

        # Distance: max(11100) - min(10000) = 1100
        assert metrics["total_distance"] == 1100

        # Cost per km: 33000 / 1100 = 30.0
        assert metrics["cost_per_km"] == 30.0

        # Fuel efficiency:
        #   fill 1 (Jan 15): (10500-10000)/25 = 20.0
        #   fill 2 (Feb  1): (11100-10500)/30 = 20.0
        #   average = 20.0
        assert metrics["average_fuel_efficiency"] == 20.0

    def test_only_fuel_no_odometer(self, tmp_db: int) -> None:
        """Fuel records without odometer → no efficiency, no distance."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)

        metrics = analytics.get_summary_metrics(vid)

        assert metrics["fuel_spend"] == 5000.0
        assert metrics["total_distance"] == 0
        assert metrics["average_fuel_efficiency"] is None
        assert metrics["cost_per_km"] is None

    def test_none_amount_does_not_crash(self, tmp_db: int) -> None:
        """Records with None amount_pkr are treated as zero."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=None, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=None, odometer_km=11000)

        metrics = analytics.get_summary_metrics(vid)
        assert metrics["total_spend"] == 0.0
        assert metrics["total_distance"] == 1000
        assert metrics["cost_per_km"] == 0.0

    def test_unknown_record_types_counted_in_total(self, tmp_db: int) -> None:
        """A 'toll' record adds to total_spend but not to fuel/maintenance/insurance."""
        vid = tmp_db
        db.add_record(vid, "toll", "2026-01-01", amount_pkr=500, odometer_km=10000)
        db.add_record(vid, "toll", "2026-01-10", amount_pkr=500, odometer_km=11000)

        metrics = analytics.get_summary_metrics(vid)
        assert metrics["total_spend"] == 1000.0
        assert metrics["fuel_spend"] == 0.0
        assert metrics["maintenance_spend"] == 0.0
        assert metrics["insurance_spend"] == 0.0
