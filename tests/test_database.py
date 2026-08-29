"""
test_database.py — Unit tests for the database module.

Every test uses a fresh temporary database (via pytest's ``tmp_path`` fixture)
so the real ``safarsync.db`` is never touched.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

import database


# ---------------------------------------------------------------------------
# Fixture: redirect DB_PATH to a throwaway file for every test.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace ``database.DB_PATH`` with a temp file and initialise the schema
    before every test.  The temp file is destroyed automatically when the
    test finishes.
    """
    tmp_db: str = str(tmp_path / "test_safarsync.db")
    monkeypatch.setattr(database, "DB_PATH", tmp_db)
    database.init_db()


# ---------------------------------------------------------------------------
# 1. Database initialisation
# ---------------------------------------------------------------------------
class TestInitDB:
    """Schema creation and idempotency."""

    def test_tables_exist(self) -> None:
        """Both vehicles and records tables should exist after init_db()."""
        conn = sqlite3.connect(database.DB_PATH)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()
        assert "vehicles" in tables
        assert "records" in tables

    def test_init_idempotent(self) -> None:
        """Calling init_db() twice must not raise or duplicate tables."""
        database.init_db()  # second call — should be harmless
        assert database.get_vehicles() == []


# ---------------------------------------------------------------------------
# 2–4. Vehicles
# ---------------------------------------------------------------------------
class TestVehicles:
    """add_vehicle / get_vehicles."""

    def test_add_vehicle(self) -> None:
        """add_vehicle returns a positive integer id."""
        vid = database.add_vehicle("Honda Civic", "XYZ-9999")
        assert isinstance(vid, int)
        assert vid > 0

    def test_add_multiple_vehicles(self) -> None:
        """Each vehicle gets a unique id."""
        id1 = database.add_vehicle("Car A", "AAA-1111")
        id2 = database.add_vehicle("Car B", "BBB-2222")
        assert id1 != id2

    def test_get_vehicles(self) -> None:
        """get_vehicles returns all inserted vehicles."""
        database.add_vehicle("Car A")
        database.add_vehicle("Car B")
        database.add_vehicle("Car C")
        vehicles = database.get_vehicles()
        assert len(vehicles) == 3
        names = {v["name"] for v in vehicles}
        assert names == {"Car A", "Car B", "Car C"}

    def test_vehicle_fields(self) -> None:
        """Returned dicts contain the expected keys and values."""
        database.add_vehicle("Toyota", "REG-001")
        vehicle = database.get_vehicles()[0]
        assert vehicle["name"] == "Toyota"
        assert vehicle["registration_number"] == "REG-001"
        assert vehicle["created_at"] != ""
        assert "id" in vehicle

    def test_empty_registration(self) -> None:
        """registration_number defaults to empty string."""
        database.add_vehicle("Unnamed")
        vehicle = database.get_vehicles()[0]
        assert vehicle["registration_number"] == ""


# ---------------------------------------------------------------------------
# 5–7. Adding different record types
# ---------------------------------------------------------------------------
class TestAddRecords:
    """add_record for fuel, maintenance, and insurance."""

    @pytest.fixture()
    def vid(self) -> int:
        return database.add_vehicle("Test Car")

    def test_add_fuel_record(self, vid: int) -> None:
        rid = database.add_record(
            vid, "fuel", "2026-08-01",
            amount_pkr=5000.0, liters=20.5, odometer_km=12000,
        )
        assert rid > 0
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["record_type"] == "fuel"
        assert row["amount_pkr"] == 5000.0
        assert row["liters"] == 20.5
        assert row["odometer_km"] == 12000

    def test_add_maintenance_record(self, vid: int) -> None:
        rid = database.add_record(
            vid, "maintenance", "2026-08-15",
            amount_pkr=15000.0,
            description="Oil change + filter",
            vendor_name="AutoCare Lahore",
        )
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["record_type"] == "maintenance"
        assert row["description"] == "Oil change + filter"
        assert row["vendor_name"] == "AutoCare Lahore"

    def test_add_insurance_record(self, vid: int) -> None:
        rid = database.add_record(
            vid, "insurance", "2026-01-01",
            amount_pkr=45000.0,
            description="Annual comprehensive insurance",
            vendor_name="EFU General Insurance",
        )
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["record_type"] == "insurance"
        assert row["amount_pkr"] == 45000.0

    def test_record_optional_fields_default_none(self, vid: int) -> None:
        """Optional columns should be None when not provided."""
        rid = database.add_record(vid, "toll", "2026-08-20")
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["amount_pkr"] is None
        assert row["liters"] is None
        assert row["odometer_km"] is None
        assert row["vendor_name"] is None
        assert row["raw_ocr_json"] is None


# ---------------------------------------------------------------------------
# 8–10. Retrieving and filtering records
# ---------------------------------------------------------------------------
class TestGetRecords:
    """get_records with vehicle_id and record_type filters."""

    @pytest.fixture()
    def setup(self) -> dict[str, int]:
        v1 = database.add_vehicle("Car One")
        v2 = database.add_vehicle("Car Two")
        database.add_record(v1, "fuel", "2026-08-01", amount_pkr=3000)
        database.add_record(v1, "fuel", "2026-08-10", amount_pkr=4000)
        database.add_record(v1, "maintenance", "2026-08-15", amount_pkr=8000)
        database.add_record(v2, "fuel", "2026-08-05", amount_pkr=2500)
        return {"v1": v1, "v2": v2}

    def test_get_all_records_for_vehicle(self, setup: dict[str, int]) -> None:
        records = database.get_records(setup["v1"])
        assert len(records) == 3

    def test_filter_by_vehicle(self, setup: dict[str, int]) -> None:
        v2_records = database.get_records(setup["v2"])
        assert len(v2_records) == 1
        assert v2_records[0]["amount_pkr"] == 2500

    def test_filter_by_record_type(self, setup: dict[str, int]) -> None:
        fuel_records = database.get_records(setup["v1"], record_type="fuel")
        assert len(fuel_records) == 2
        assert all(r["record_type"] == "fuel" for r in fuel_records)

    def test_filter_no_match(self, setup: dict[str, int]) -> None:
        """Filtering by a type with no rows returns an empty list."""
        records = database.get_records(setup["v1"], record_type="insurance")
        assert records == []


# ---------------------------------------------------------------------------
# 11. Get record by ID
# ---------------------------------------------------------------------------
class TestGetRecordById:

    def test_existing_record(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01", amount_pkr=1000)
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["id"] == rid

    def test_nonexistent_record(self) -> None:
        """Must return None for an id that doesn't exist."""
        assert database.get_record_by_id(99999) is None


# ---------------------------------------------------------------------------
# 12. Update record
# ---------------------------------------------------------------------------
class TestUpdateRecord:

    @pytest.fixture()
    def rid(self) -> int:
        vid = database.add_vehicle("Car")
        return database.add_record(
            vid, "fuel", "2026-08-01",
            amount_pkr=5000, liters=20.0,
        )

    def test_update_single_field(self, rid: int) -> None:
        ok = database.update_record(rid, amount_pkr=6000)
        assert ok is True
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["amount_pkr"] == 6000

    def test_update_multiple_fields(self, rid: int) -> None:
        database.update_record(rid, liters=25.0, description="Updated")
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["liters"] == 25.0
        assert row["description"] == "Updated"

    def test_update_nonexistent_returns_false(self) -> None:
        ok = database.update_record(99999, amount_pkr=100)
        assert ok is False

    def test_update_unknown_column_raises(self, rid: int) -> None:
        with pytest.raises(ValueError, match="Unknown column"):
            database.update_record(rid, bogus_field="x")

    def test_update_no_columns_raises(self, rid: int) -> None:
        with pytest.raises(ValueError, match="No valid columns"):
            database.update_record(rid)


# ---------------------------------------------------------------------------
# 13. Delete record
# ---------------------------------------------------------------------------
class TestDeleteRecord:

    def test_delete_existing(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01")
        assert database.delete_record(rid) is True
        assert database.get_record_by_id(rid) is None

    def test_delete_nonexistent(self) -> None:
        assert database.delete_record(99999) is False


# ---------------------------------------------------------------------------
# 14. Empty database edge cases
# ---------------------------------------------------------------------------
class TestEmptyDB:
    """Behaviour when the database has no data."""

    def test_get_vehicles_empty(self) -> None:
        assert database.get_vehicles() == []

    def test_get_records_empty(self) -> None:
        """get_records on a nonexistent vehicle returns empty list, not error."""
        assert database.get_records(99999) == []


# ---------------------------------------------------------------------------
# 15. Invalid / unusual data
# ---------------------------------------------------------------------------
class TestInvalidData:

    def test_foreign_key_violation(self) -> None:
        """Inserting a record with a bad vehicle_id must raise."""
        with pytest.raises(sqlite3.IntegrityError):
            database.add_record(99999, "fuel", "2026-08-01")

    def test_zero_amount(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01", amount_pkr=0.0)
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["amount_pkr"] == 0.0

    def test_negative_amount(self) -> None:
        """Negative amounts are allowed (refunds)."""
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01", amount_pkr=-500.0)
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["amount_pkr"] == -500.0

    def test_empty_string_description(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01", description="")
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["description"] == ""

    def test_unicode_text(self) -> None:
        """UTF-8 content (Urdu, emoji) must round-trip correctly."""
        vid = database.add_vehicle("گاڑی", "اردو-123")
        rid = database.add_record(
            vid, "fuel", "2026-08-01",
            description="پٹرول ⛽ بھروایا",
        )
        vehicle = database.get_vehicles()[0]
        record = database.get_record_by_id(rid)
        assert vehicle["name"] == "گاڑی"
        assert record is not None
        assert "⛽" in record["description"]


# ---------------------------------------------------------------------------
# 16. SQL-injection-like input
# ---------------------------------------------------------------------------
class TestSQLInjection:
    """Parameterized queries must neutralise injection attempts."""

    MALICIOUS: str = "'; DROP TABLE vehicles; --"

    def test_injection_in_vehicle_name(self) -> None:
        vid = database.add_vehicle(self.MALICIOUS)
        vehicles = database.get_vehicles()
        assert len(vehicles) == 1
        assert vehicles[0]["name"] == self.MALICIOUS

    def test_injection_in_record_description(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(
            vid, "fuel", "2026-08-01",
            description=self.MALICIOUS,
        )
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["description"] == self.MALICIOUS

    def test_injection_in_registration_number(self) -> None:
        payload = "1 OR 1=1; DELETE FROM vehicles;"
        vid = database.add_vehicle("Car", registration_number=payload)
        vehicle = database.get_vehicles()[0]
        assert vehicle["registration_number"] == payload
        # Table must still exist and have exactly one row.
        assert len(database.get_vehicles()) == 1

    def test_injection_in_update(self) -> None:
        vid = database.add_vehicle("Car")
        rid = database.add_record(vid, "fuel", "2026-08-01", description="safe")
        payload = "'; DROP TABLE records; --"
        database.update_record(rid, description=payload)
        row = database.get_record_by_id(rid)
        assert row is not None
        assert row["description"] == payload


# ---------------------------------------------------------------------------
# 17. Connection management
# ---------------------------------------------------------------------------
class TestConnections:
    """Verify that connections are closed after each operation."""

    def test_connection_closed_after_init(self) -> None:
        """init_db() should not leave open connections to the temp DB."""
        database.init_db()
        # If a connection were still held, this exclusive lock would fail
        # on Windows (where SQLite locks are mandatory).
        conn = sqlite3.connect(database.DB_PATH, isolation_level="EXCLUSIVE")
        try:
            conn.execute("BEGIN EXCLUSIVE")
            conn.execute("SELECT 1")
            conn.commit()
        finally:
            conn.close()

    def test_connection_closed_after_add(self) -> None:
        vid = database.add_vehicle("Car")
        database.add_record(vid, "fuel", "2026-08-01")
        # Exclusive lock should succeed — proves prior connections closed.
        conn = sqlite3.connect(database.DB_PATH, isolation_level="EXCLUSIVE")
        try:
            conn.execute("BEGIN EXCLUSIVE")
            conn.commit()
        finally:
            conn.close()

    def test_connection_closed_after_error(self) -> None:
        """Even when an operation raises, the connection must be closed."""
        with pytest.raises(sqlite3.IntegrityError):
            database.add_record(99999, "fuel", "2026-08-01")
        # Connection should still be usable for a fresh operation.
        vid = database.add_vehicle("Recovery Car")
        assert vid > 0
