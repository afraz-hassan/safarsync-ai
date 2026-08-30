"""
database.py — Database connection and data-access layer for SafarSync AI.

All persistence lives here.  Every other module talks to the database
through the public functions in this file — never by writing raw SQL.

Database : SQLite 3  (file: safarsync.db, created automatically)
Tables   : vehicles, records  (records.vehicle_id → vehicles.id)

Usage example::

    import database as db

    db.init_db()
    vid = db.add_vehicle("My Corolla", "ABC-1234")
    db.add_record(vid, "fuel", "2026-08-29", amount_pkr=5000, liters=20.5)
    print(db.get_records(vid))
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import streamlit as st

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache-busting helpers — bump a session-state counter after every write so
# that @st.cache_data-decorated readers invalidate automatically.
# ---------------------------------------------------------------------------
def _bump_db_version():
    """Increment DB version counter to invalidate cached results."""
    if hasattr(st, "session_state"):
        st.session_state["_db_version"] = st.session_state.get("_db_version", 0) + 1


def get_db_version() -> int:
    """Return current DB version for cache keying."""
    if hasattr(st, "session_state"):
        return st.session_state.get("_db_version", 0)
    return 0

# ---------------------------------------------------------------------------
# Database file path — lives next to this script.
# ---------------------------------------------------------------------------
_DB_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(_DB_DIR, "safarsync.db")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection with sensible defaults.

    • ``row_factory = sqlite3.Row`` so every row behaves like a dict.
    • ``PRAGMA foreign_keys = ON`` so the FK constraint on records is enforced.

    Callers are responsible for closing the connection (use ``with`` or
    ``try / finally``).
    """
    conn: sqlite3.Connection = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that opens, commits/rolls-back, and closes a connection."""
    conn: sqlite3.Connection = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a sqlite3.Row to a plain dict, or return None."""
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert a list of sqlite3.Rows to a list of plain dicts."""
    return [dict(r) for r in rows]


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string (no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------
def init_db() -> None:
    """
    Create the ``vehicles`` and ``records`` tables if they don't already exist.

    Safe to call multiple times — uses ``CREATE TABLE IF NOT EXISTS``.
    The foreign key ``records.vehicle_id → vehicles.id`` is enforced via
    ``PRAGMA foreign_keys = ON`` set in every connection.
    """
    with _connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT    NOT NULL,
                registration_number TEXT,
                created_at        TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS records (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id        INTEGER NOT NULL,
                record_type       TEXT    NOT NULL,
                date              TEXT    NOT NULL,
                amount_pkr        REAL,
                liters            REAL,
                odometer_km       INTEGER,
                description       TEXT,
                vendor_name       TEXT,
                source            TEXT,
                confidence        TEXT,
                raw_ocr_json      TEXT,
                created_at        TEXT    NOT NULL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            );
            """
        )

        # Migration: add metadata column to records if missing
        cur = conn.execute("PRAGMA table_info(records)")
        columns = {row[1] for row in cur.fetchall()}
        if "metadata" not in columns:
            conn.execute("ALTER TABLE records ADD COLUMN metadata TEXT")
            logger.warning("Migration applied: added 'metadata' column to records table.")

        # Migration: add onboarding columns to vehicles if missing
        cur = conn.execute("PRAGMA table_info(vehicles)")
        columns = {row[1] for row in cur.fetchall()}
        for col, col_type in [("make", "TEXT"), ("model", "TEXT"), ("year", "INTEGER"), ("initial_mileage", "INTEGER")]:
            if col not in columns:
                conn.execute(f"ALTER TABLE vehicles ADD COLUMN {col} {col_type}")
                logger.warning("Migration applied: added '%s' column to vehicles table.", col)

        # Indexes for common query patterns
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_records_vehicle_id ON records(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_records_vehicle_date ON records(vehicle_id, date DESC);
            CREATE INDEX IF NOT EXISTS idx_records_vehicle_type ON records(vehicle_id, record_type);
            """
        )

    logger.info("Database initialized")


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------
def add_vehicle(
    name: str,
    registration_number: str = "",
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    initial_mileage: int | None = None,
) -> int:
    """
    Insert a new vehicle and return its auto-generated ``id``.

    Parameters
    ----------
    name : str
        Human-readable vehicle name (e.g. "My Corolla").
    registration_number : str, optional
        License / registration plate (default: empty string).
    make, model : str or None, optional
        Vehicle manufacturer and model name.
    year : int or None, optional
        Manufacturing year.
    initial_mileage : int or None, optional
        Odometer reading at the time of onboarding.

    Returns
    -------
    int
        The ``id`` of the newly created vehicle row.
    """
    with _connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vehicles
                (name, registration_number, created_at, make, model, year, initial_mileage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, registration_number, _utcnow(), make, model, year, initial_mileage),
        )
        new_id = cursor.lastrowid
    _bump_db_version()
    return new_id  # type: ignore[return-value]


def get_vehicles() -> list[dict[str, Any]]:
    """
    Return all vehicles ordered by creation date (newest first).

    Returns an empty list when the database has no vehicles yet.
    """
    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM vehicles ORDER BY created_at DESC"
        ).fetchall()
        return _rows_to_list(rows)


def get_vehicle_by_id(vehicle_id: int) -> dict[str, Any] | None:
    """Return a single vehicle by *id*, or ``None`` if not found."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
def add_record(
    vehicle_id: int,
    record_type: str,
    date: str,
    amount_pkr: float | None = None,
    liters: float | None = None,
    odometer_km: int | None = None,
    description: str | None = None,
    vendor_name: str | None = None,
    source: str | None = None,
    confidence: str | None = None,
    raw_ocr_json: str | None = None,
    metadata: str | None = None,
) -> int:
    """
    Insert a new expense / maintenance record and return its ``id``.

    Parameters
    ----------
    vehicle_id : int
        FK pointing to ``vehicles.id``.
    record_type : str
        Category such as "fuel", "maintenance", "toll", etc.
    date : str
        Date string (ISO-8601 recommended: "2026-08-29").
    amount_pkr, liters, odometer_km, description, vendor_name,
    source, confidence, raw_ocr_json, metadata : optional
        Additional columns — pass ``None`` or omit for unused fields.

    Returns
    -------
    int
        The ``id`` of the newly created record row.
    """
    with _connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO records
                (vehicle_id, record_type, date, amount_pkr, liters, odometer_km,
                 description, vendor_name, source, confidence, raw_ocr_json, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vehicle_id,
                record_type,
                date,
                amount_pkr,
                liters,
                odometer_km,
                description,
                vendor_name,
                source,
                confidence,
                raw_ocr_json,
                metadata,
                _utcnow(),
            ),
        )
        new_id = cursor.lastrowid
    _bump_db_version()
    return new_id  # type: ignore[return-value]


def get_records(
    vehicle_id: int,
    record_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return records for a vehicle, optionally filtered by type and date range.

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose records to fetch.
    record_type : str or None, optional
        If given, only records matching this type are returned.
    start_date : str or None, optional
        If given, only records on or after this date are returned.
    end_date : str or None, optional
        If given, only records on or before this date are returned.

    Returns
    -------
    list[dict]
        Matching rows (newest first).  Empty list if none found.
    """
    conditions: list[str] = ["vehicle_id = ?"]
    params: list[Any] = [vehicle_id]

    if record_type is not None:
        conditions.append("record_type = ?")
        params.append(record_type)
    if start_date is not None:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("date <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)
    query = f"SELECT * FROM records WHERE {where_clause} ORDER BY date DESC"

    with _connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return _rows_to_list(rows)


def get_record_by_id(record_id: int) -> dict[str, Any] | None:
    """
    Fetch a single record by its primary key.

    Returns ``None`` if no row with that ``id`` exists.
    """
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        return _row_to_dict(row)


def update_record(record_id: int, **kwargs: Any) -> bool:
    """
    Update one or more columns of an existing record.

    Only the columns explicitly passed as keyword arguments are touched;
    everything else is left unchanged.

    Allowed keyword arguments: ``record_type``, ``date``, ``amount_pkr``,
    ``liters``, ``odometer_km``, ``description``, ``vendor_name``,
    ``source``, ``confidence``, ``raw_ocr_json``, ``metadata``.

    Returns
    -------
    bool
        ``True`` if a row was updated, ``False`` if no matching record exists.

    Raises
    ------
    ValueError
        If no valid column names are supplied or an unknown column is given.
    """
    # Whitelist of columns that may be updated through this function.
    allowed: set[str] = {
        "record_type", "date", "amount_pkr", "liters", "odometer_km",
        "description", "vendor_name", "source", "confidence", "raw_ocr_json",
        "metadata",
    }

    # Filter to only allowed keys; reject unknown ones.
    updates: dict[str, Any] = {k: v for k, v in kwargs.items() if k in allowed}
    unknown: set[str] = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"Unknown column(s) in update_record: {unknown}")
    if not updates:
        raise ValueError("No valid columns supplied to update_record.")

    set_clause: str = ", ".join(f"{col} = ?" for col in updates)
    values: list[Any] = list(updates.values()) + [record_id]

    with _connection() as conn:
        cursor = conn.execute(
            f"UPDATE records SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        updated = cursor.rowcount > 0
    if updated:
        _bump_db_version()
    return updated


def delete_record(record_id: int) -> bool:
    """
    Delete a record by its primary key.

    Returns ``True`` if a row was deleted, ``False`` if it didn't exist.
    """
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        deleted = cursor.rowcount > 0
    if deleted:
        _bump_db_version()
    return deleted


# ---------------------------------------------------------------------------
# Quick smoke test — run:  python database.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialise (or upgrade) the schema.
    init_db()
    print("Database initialized successfully!")

    # Verify the schema by inserting a throwaway vehicle and reading it back.
    _vid = add_vehicle("__test__", "TEST-000")
    _vehicles = get_vehicles()
    print(f"Vehicles in DB: {len(_vehicles)}")

    _rid = add_record(_vid, "fuel", "2026-08-29", amount_pkr=5000.0, liters=20.5)
    _records = get_records(_vid)
    print(f"Records for test vehicle: {len(_records)}")

    # Clean up test data.
    delete_record(_rid)
    # (vehicle row left in place — cheap to ignore, expensive to cascade-test)

    print("Smoke test passed.")
