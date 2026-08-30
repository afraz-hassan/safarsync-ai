"""
test_anomaly.py — Unit tests for the anomaly detection module.

Uses a temporary SQLite database (via monkeypatch on ``database.DB_PATH``)
so the real ``safarsync.db`` is never touched.
"""

from __future__ import annotations

from typing import Any

import pytest

import database as db
import anomaly


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> int:
    """
    Create an isolated temporary database, initialise it, add a vehicle,
    and return the vehicle id.
    """
    db_file = str(tmp_path / "test_safarsync.db")
    monkeypatch.setattr(db, "DB_PATH", db_file)
    db.init_db()
    vid = db.add_vehicle("Test Car", "TEST-0001")
    return vid  # type: ignore[return-value]


# ===================================================================
# TestEmptyRecords
# ===================================================================
class TestEmptyRecords:
    """No records → returns empty list."""

    def test_no_records_returns_empty(self, tmp_db: int) -> None:
        vid = tmp_db
        result = anomaly.find_anomalies(vid)
        assert result == []


# ===================================================================
# TestInsufficientHistory
# ===================================================================
class TestInsufficientHistory:
    """Less than 3 records → no anomalies flagged."""

    def test_one_record_no_anomaly(self, tmp_db: int) -> None:
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        result = anomaly.find_anomalies(vid)
        assert result == []

    def test_two_records_no_anomaly(self, tmp_db: int) -> None:
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=20000, liters=80.0)
        result = anomaly.find_anomalies(vid)
        assert result == []


# ===================================================================
# TestFuelAmountAnomaly
# ===================================================================
class TestFuelAmountAnomaly:
    """Create records where one fuel amount is 2x the baseline average → should flag warning."""

    def test_fuel_amount_spike_warning(self, tmp_db: int) -> None:
        vid = tmp_db
        # 3 baseline records with avg = 5000
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        # Spike: 2x the avg = 10000 → ratio = 2.0 → warning
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=10000, liters=20.0)

        result = anomaly.find_anomalies(vid)
        fuel_amount_anomalies = [a for a in result if a["type"] == "fuel_amount"]
        assert len(fuel_amount_anomalies) >= 1
        assert fuel_amount_anomalies[0]["severity"] == "warning"


# ===================================================================
# TestFuelEfficiencyDecline
# ===================================================================
class TestFuelEfficiencyDecline:
    """Create records with declining km/L → should detect."""

    def test_efficiency_decline_detected(self, tmp_db: int) -> None:
        vid = tmp_db
        # Build 4+ fuel records with consistent efficiency baseline
        # Baseline: 20 km/L for at least 3 trips
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0, odometer_km=10400)  # 400km/20L = 20 km/L
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0, odometer_km=10800)  # 400km/20L = 20 km/L
        db.add_record(vid, "fuel", "2026-01-30", amount_pkr=5000, liters=20.0, odometer_km=11200)  # 400km/20L = 20 km/L
        # Now a sharp decline: only 100 km on 20 L = 5 km/L
        # avg_eff = 20, current = 5, decline_ratio = 20/5 = 4.0 → high
        db.add_record(vid, "fuel", "2026-02-10", amount_pkr=5000, liters=20.0, odometer_km=11300)

        result = anomaly.find_anomalies(vid)
        eff_anomalies = [a for a in result if a["type"] == "fuel_efficiency"]
        assert len(eff_anomalies) >= 1
        assert eff_anomalies[0]["severity"] in ("info", "warning", "high")


# ===================================================================
# TestMaintenanceCostSpike
# ===================================================================
class TestMaintenanceCostSpike:
    """Create maintenance records where one is 3x average → should flag high."""

    def test_maintenance_cost_spike_high(self, tmp_db: int) -> None:
        vid = tmp_db
        # 3 baseline maintenance records with avg = 5000
        db.add_record(vid, "maintenance", "2026-01-01", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-02-01", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-03-01", amount_pkr=5000)
        # Spike: 3x the avg = 15000 → ratio = 3.0 → high
        db.add_record(vid, "maintenance", "2026-04-01", amount_pkr=15000)

        result = anomaly.find_anomalies(vid)
        maint_anomalies = [a for a in result if a["type"] == "maintenance_cost"]
        assert len(maint_anomalies) >= 1
        assert maint_anomalies[0]["severity"] == "high"


# ===================================================================
# TestSeverityTiers
# ===================================================================
class TestSeverityTiers:
    """Verify info (1.5x), warning (2.0x), high (3.0x) thresholds."""

    def test_info_threshold(self, tmp_db: int) -> None:
        vid = tmp_db
        # avg = 5000; spike = 7500 → ratio = 1.5 → info
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=7500, liters=20.0)

        result = anomaly.find_anomalies(vid)
        fuel_amounts = [a for a in result if a["type"] == "fuel_amount"]
        assert len(fuel_amounts) >= 1
        assert fuel_amounts[0]["severity"] == "info"

    def test_warning_threshold(self, tmp_db: int) -> None:
        vid = tmp_db
        # avg = 5000; spike = 10000 → ratio = 2.0 → warning
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=10000, liters=20.0)

        result = anomaly.find_anomalies(vid)
        fuel_amounts = [a for a in result if a["type"] == "fuel_amount"]
        assert len(fuel_amounts) >= 1
        assert fuel_amounts[0]["severity"] == "warning"

    def test_high_threshold(self, tmp_db: int) -> None:
        vid = tmp_db
        # avg = 5000; spike = 15000 → ratio = 3.0 → high
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=15000, liters=20.0)

        result = anomaly.find_anomalies(vid)
        fuel_amounts = [a for a in result if a["type"] == "fuel_amount"]
        assert len(fuel_amounts) >= 1
        assert fuel_amounts[0]["severity"] == "high"

    def test_below_info_no_anomaly(self, tmp_db: int) -> None:
        vid = tmp_db
        # avg = 5000; value = 7000 → ratio = 1.4 → below info threshold
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=7000, liters=20.0)

        result = anomaly.find_anomalies(vid)
        fuel_amounts = [a for a in result if a["type"] == "fuel_amount"]
        assert len(fuel_amounts) == 0


# ===================================================================
# TestMixedRecordTypes
# ===================================================================
class TestMixedRecordTypes:
    """Fuel anomalies don't trigger on maintenance records and vice versa."""

    def test_fuel_spike_ignores_maintenance(self, tmp_db: int) -> None:
        """A fuel amount spike should NOT produce a maintenance_cost anomaly."""
        vid = tmp_db
        # Add normal fuel records + a spike
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=15000, liters=20.0)  # high spike

        # Add normal maintenance records (no spike)
        db.add_record(vid, "maintenance", "2026-01-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-02-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-03-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-04-05", amount_pkr=5000)

        result = anomaly.find_anomalies(vid)
        fuel_anomalies = [a for a in result if a["type"] == "fuel_amount"]
        maint_anomalies = [a for a in result if a["type"] == "maintenance_cost"]
        assert len(fuel_anomalies) >= 1  # fuel spike detected
        assert len(maint_anomalies) == 0  # no maintenance anomaly

    def test_maintenance_spike_ignores_fuel(self, tmp_db: int) -> None:
        """A maintenance cost spike should NOT produce a fuel_amount anomaly."""
        vid = tmp_db
        # Add normal fuel records (no spike)
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-10", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-01-20", amount_pkr=5000, liters=20.0)
        db.add_record(vid, "fuel", "2026-02-01", amount_pkr=5000, liters=20.0)

        # Add maintenance records with a spike
        db.add_record(vid, "maintenance", "2026-01-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-02-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-03-05", amount_pkr=5000)
        db.add_record(vid, "maintenance", "2026-04-05", amount_pkr=15000)  # high spike

        result = anomaly.find_anomalies(vid)
        fuel_anomalies = [a for a in result if a["type"] == "fuel_amount"]
        maint_anomalies = [a for a in result if a["type"] == "maintenance_cost"]
        assert len(fuel_anomalies) == 0  # no fuel anomaly
        assert len(maint_anomalies) >= 1  # maintenance spike detected
