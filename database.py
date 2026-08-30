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

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

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
    conn: sqlite3.Connection = _get_connection()
    try:
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
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------
def add_vehicle(name: str, registration_number: str = "") -> int:
    """
    Insert a new vehicle and return its auto-generated ``id``.

    Parameters
    ----------
    name : str
        Human-readable vehicle name (e.g. "My Corolla").
    registration_number : str, optional
        License / registration plate (default: empty string).

    Returns
    -------
    int
        The ``id`` of the newly created vehicle row.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO vehicles (name, registration_number, created_at) VALUES (?, ?, ?)",
            (name, registration_number, _utcnow()),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_vehicles() -> list[dict[str, Any]]:
    """
    Return all vehicles ordered by creation date (newest first).

    Returns an empty list when the database has no vehicles yet.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM vehicles ORDER BY created_at DESC"
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_vehicle_by_id(vehicle_id: int) -> dict[str, Any] | None:
    """Return a single vehicle by *id*, or ``None`` if not found."""
    conn: sqlite3.Connection = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


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
    source, confidence, raw_ocr_json : optional
        Additional columns — pass ``None`` or omit for unused fields.

    Returns
    -------
    int
        The ``id`` of the newly created record row.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO records
                (vehicle_id, record_type, date, amount_pkr, liters, odometer_km,
                 description, vendor_name, source, confidence, raw_ocr_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                _utcnow(),
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_records(
    vehicle_id: int,
    record_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return records for a vehicle, optionally filtered by type.

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose records to fetch.
    record_type : str or None, optional
        If given, only records matching this type are returned.

    Returns
    -------
    list[dict]
        Matching rows (newest first).  Empty list if none found.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        if record_type is not None:
            rows = conn.execute(
                "SELECT * FROM records WHERE vehicle_id = ? AND record_type = ? ORDER BY date DESC",
                (vehicle_id, record_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM records WHERE vehicle_id = ? ORDER BY date DESC",
                (vehicle_id,),
            ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_record_by_id(record_id: int) -> dict[str, Any] | None:
    """
    Fetch a single record by its primary key.

    Returns ``None`` if no row with that ``id`` exists.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_record(record_id: int, **kwargs: Any) -> bool:
    """
    Update one or more columns of an existing record.

    Only the columns explicitly passed as keyword arguments are touched;
    everything else is left unchanged.

    Allowed keyword arguments: ``record_type``, ``date``, ``amount_pkr``,
    ``liters``, ``odometer_km``, ``description``, ``vendor_name``,
    ``source``, ``confidence``, ``raw_ocr_json``.

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

    conn: sqlite3.Connection = _get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE records SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_record(record_id: int) -> bool:
    """
    Delete a record by its primary key.

    Returns ``True`` if a row was deleted, ``False`` if it didn't exist.
    """
    conn: sqlite3.Connection = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


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
