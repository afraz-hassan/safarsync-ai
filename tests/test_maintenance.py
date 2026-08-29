"""
test_maintenance.py — Unit tests for the maintenance module.

Uses a temporary SQLite database (via monkeypatch on ``database.DB_PATH``)
so the real ``safarsync.db`` is never touched.

AI advice tests mock ``maintenance.ask_text`` to avoid real API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch, MagicMock

import pytest

import database as db
import maintenance
from maintenance import MAINTENANCE_SCHEDULE_KM


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


def _get_status(results: list[dict[str, Any]], service_type: str) -> dict[str, Any]:
    """Helper: extract a single service entry from check_due_maintenance results."""
    for entry in results:
        if entry["type"] == service_type:
            return entry
    raise AssertionError(f"Service type '{service_type}' not found in results")


# ===================================================================
# check_due_maintenance
# ===================================================================
class TestCheckDueMaintenance:
    """Tests for ``maintenance.check_due_maintenance``."""

    def test_no_records_all_unknown(self, tmp_db: int) -> None:
        """
        A vehicle with zero records has no odometer data — every service
        must be reported as 'unknown'.
        """
        vid = tmp_db
        results = maintenance.check_due_maintenance(vid)

        assert len(results) == len(MAINTENANCE_SCHEDULE_KM)
        for entry in results:
            assert entry["status"] == "unknown"
            assert entry["km_since_last"] is None
            assert entry["overdue_by"] is None

    def test_no_service_records_all_overdue(self, tmp_db: int) -> None:
        """
        When odometer data exists but no maintenance records have been
        logged, every service is considered overdue.
        """
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-01-01", odometer_km=20000)

        results = maintenance.check_due_maintenance(vid)

        assert len(results) == len(MAINTENANCE_SCHEDULE_KM)
        for entry in results:
            assert entry["status"] == "overdue"
            assert entry["km_since_last"] is None
            assert entry["overdue_by"] is None

    def test_not_due(self, tmp_db: int) -> None:
        """
        A service performed well within its interval → 'not_due'.

        oil_change interval = 5000 km.
        Last service at 10 000 km, current at 11 000 km → 1000 km since.
        Remaining = 4000 km > 1000 km threshold → not_due.
        """
        vid = tmp_db
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=10000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=11000)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        assert oil["status"] == "not_due"
        assert oil["km_since_last"] == 1000
        assert oil["overdue_by"] is None
        assert oil["interval_km"] == 5000

    def test_due_soon(self, tmp_db: int) -> None:
        """
        A service approaching its interval → 'due_soon'.

        oil_change interval = 5000 km.
        Last service at 10 000 km, current at 14 500 km → 4500 km since.
        Remaining = 500 km ≤ 1000 km threshold → due_soon.
        """
        vid = tmp_db
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=10000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=14500)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        assert oil["status"] == "due_soon"
        assert oil["km_since_last"] == 4500
        assert oil["overdue_by"] is None

    def test_overdue(self, tmp_db: int) -> None:
        """
        A service past its interval → 'overdue' with correct overdue_by.

        oil_change interval = 5000 km.
        Last service at 10 000 km, current at 16 000 km → 6000 km since.
        Overdue by = 6000 - 5000 = 1000 km.
        """
        vid = tmp_db
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=10000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=16000)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        assert oil["status"] == "overdue"
        assert oil["km_since_last"] == 6000
        assert oil["overdue_by"] == 1000

    def test_exactly_at_interval(self, tmp_db: int) -> None:
        """
        km_since_last == interval → 'overdue' (overdue_by = 0).

        oil_change interval = 5000 km.
        Last service at 10 000 km, current at 15 000 km → 5000 km since.
        """
        vid = tmp_db
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=10000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=15000)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        assert oil["status"] == "overdue"
        assert oil["km_since_last"] == 5000
        assert oil["overdue_by"] == 0

    def test_mixed_statuses(self, tmp_db: int) -> None:
        """
        Different services at different stages produce correct individual statuses.
        """
        vid = tmp_db

        # oil_change: serviced at 12000, current 13000 → km_since=1000 → not_due
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=12000)

        # air_filter: serviced at 5000, current 13000 → km_since=8000 → not_due
        #   (interval 10000, remaining 2000 > 1000)
        db.add_record(vid, "air_filter", "2026-01-01", odometer_km=5000)

        # brake_check: serviced at 2000, current 13000 → km_since=11000 → overdue
        #   (interval 15000, overdue_by=0? No: 11000 < 15000, remaining=4000 > 1000 → not_due)
        db.add_record(vid, "brake_check", "2026-01-01", odometer_km=2000)

        # tire_rotation: never serviced → overdue
        # (no record added)

        # Current odometer
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=13000)

        results = maintenance.check_due_maintenance(vid)

        oil = _get_status(results, "oil_change")
        assert oil["status"] == "not_due"
        assert oil["km_since_last"] == 1000

        air = _get_status(results, "air_filter")
        assert air["status"] == "not_due"
        assert air["km_since_last"] == 8000

        brake = _get_status(results, "brake_check")
        assert brake["status"] == "not_due"
        assert brake["km_since_last"] == 11000

        tire = _get_status(results, "tire_rotation")
        assert tire["status"] == "overdue"

    def test_missing_odometer_on_service_record(self, tmp_db: int) -> None:
        """
        If the service record has no odometer, treat the service as never
        logged → overdue (when current odometer exists).
        """
        vid = tmp_db
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=None)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        # Service record exists but has no odometer → treated as no service
        assert oil["status"] == "overdue"
        assert oil["km_since_last"] is None

    def test_all_four_services_returned(self, tmp_db: int) -> None:
        """Exactly one entry per scheduled service type is returned."""
        vid = tmp_db
        results = maintenance.check_due_maintenance(vid)

        types_returned = {r["type"] for r in results}
        assert types_returned == set(MAINTENANCE_SCHEDULE_KM.keys())

    def test_latest_service_used_when_multiple(self, tmp_db: int) -> None:
        """
        When multiple service records exist, the most recent odometer
        (by record date, newest-first from DB) is used.
        """
        vid = tmp_db
        # Two oil changes — the newer one at 14000 should be used
        db.add_record(vid, "oil_change", "2026-01-01", odometer_km=10000)
        db.add_record(vid, "oil_change", "2026-03-01", odometer_km=14000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=15000)

        results = maintenance.check_due_maintenance(vid)
        oil = _get_status(results, "oil_change")

        # km_since_last = 15000 - 14000 = 1000 (uses latest service)
        assert oil["km_since_last"] == 1000
        assert oil["status"] == "not_due"


# ===================================================================
# get_ai_maintenance_advice
# ===================================================================
class TestGetAiMaintenanceAdvice:
    """Tests for ``maintenance.get_ai_maintenance_advice``."""

    @patch("maintenance.ask_text")
    def test_ai_advice_success(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        When the AI model returns a valid response, that text is used
        verbatim.
        """
        vid = tmp_db
        # Service all types recently so only factual summary appears
        for svc in MAINTENANCE_SCHEDULE_KM:
            db.add_record(vid, svc, "2026-01-01", odometer_km=10000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=11000)

        expected_reply = "All services are in good standing. Continue regular monitoring."
        mock_ask.return_value = expected_reply

        result = maintenance.get_ai_maintenance_advice(vid)

        assert result == expected_reply
        mock_ask.assert_called_once()

        # Verify the prompt contains the verified-facts block
        prompt_arg: str = mock_ask.call_args[0][0]
        assert "no overdue services" in prompt_arg.lower()
        assert "verified facts" in prompt_arg.lower()

    @patch("maintenance.ask_text")
    def test_ai_advice_fallback_on_api_error(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        When the AI call raises an exception, a meaningful fallback is
        returned instead.
        """
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)

        mock_ask.side_effect = ConnectionError("Network unreachable")

        result = maintenance.get_ai_maintenance_advice(vid)

        # Fallback should mention overdue services (all are overdue since
        # there are no maintenance records)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "overdue" in result.lower()

    @patch("maintenance.ask_text")
    def test_ai_advice_fallback_mentions_overdue(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        Fallback text names the specific overdue services.
        """
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)

        mock_ask.side_effect = TimeoutError("Request timed out")

        result = maintenance.get_ai_maintenance_advice(vid)

        # All services are overdue — fallback should mention at least one
        assert "oil change" in result.lower() or "overdue" in result.lower()

    @patch("maintenance.ask_text")
    def test_ai_advice_fallback_all_up_to_date(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        When no services are overdue or due soon, the fallback says
        everything is up to date.
        """
        vid = tmp_db
        # Service all four types well within interval
        for service_type in MAINTENANCE_SCHEDULE_KM:
            db.add_record(vid, service_type, "2026-06-01", odometer_km=19000)
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)

        mock_ask.side_effect = RuntimeError("Server error")

        result = maintenance.get_ai_maintenance_advice(vid)

        assert "up to date" in result.lower()

    @patch("maintenance.ask_text")
    def test_ai_advice_empty_reply_triggers_fallback(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        If the AI model returns an empty string, the fallback is used.
        """
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)

        mock_ask.return_value = ""

        result = maintenance.get_ai_maintenance_advice(vid)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("maintenance.ask_text")
    def test_ai_advice_includes_fuel_efficiency_in_prompt(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """
        The prompt sent to the AI includes recent fuel efficiency data
        when available.
        """
        vid = tmp_db
        # Create fuel records that produce an efficiency entry
        db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0, odometer_km=10000)
        db.add_record(vid, "fuel", "2026-01-15", amount_pkr=6000, liters=25.0, odometer_km=10500)

        mock_ask.return_value = "Good efficiency at 20.0 km/L. Keep it up."

        maintenance.get_ai_maintenance_advice(vid)

        prompt_arg: str = mock_ask.call_args[0][0]
        assert "km/L" in prompt_arg
        assert "20.0" in prompt_arg

    @patch("maintenance.ask_text")
    def test_ai_advice_permission_error_fallback(self, mock_ask: MagicMock, tmp_db: int) -> None:
        """PermissionError (bad API key) triggers fallback."""
        vid = tmp_db
        db.add_record(vid, "fuel", "2026-06-01", odometer_km=20000)
        mock_ask.side_effect = PermissionError("Bad API key")

        result = maintenance.get_ai_maintenance_advice(vid)
        assert isinstance(result, str)
        assert len(result) > 0
