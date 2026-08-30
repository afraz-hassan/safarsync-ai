"""
analytics.py — Expense analytics and reporting logic for SafarSync AI.

Provides fuel-efficiency calculations, monthly spending breakdowns,
cost-per-kilometre metrics, and high-level summary dashboards.

All data is read through :mod:`database`; this module never touches SQL
directly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import streamlit as st

import database as db
from database import get_db_version


def _safe_cache(**kwargs):
    """Return st.cache_data decorator only when Streamlit runtime is active."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return st.cache_data(**kwargs)
    except Exception:
        pass
    # No Streamlit context — return identity decorator (no caching)
    return lambda fn: fn


# ---------------------------------------------------------------------------
# Fuel efficiency
# ---------------------------------------------------------------------------
@_safe_cache(ttl=300, show_spinner=False)
def calculate_fuel_efficiency(vehicle_id: int, db_version: int = 0) -> list[dict[str, Any]]:
    """
    Calculate per-fill fuel efficiency (km/L) for a vehicle.

    For every consecutive pair of *fuel* records (ordered chronologically),
    efficiency is computed as::

        (current_odometer − previous_odometer) / current_liters

    Records are **skipped** (with a warning entry) when any of the
    following apply:

    * ``odometer_km`` is ``None``
    * ``liters`` is ``None`` or zero
    * The distance delta is zero or negative

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose fuel records to analyse.

    Returns
    -------
    list[dict]
        Each dict contains:

        * ``date`` – date string of the current record
        * ``distance_km`` – odometer delta (int)
        * ``liters`` – fuel volume of the current fill-up (float)
        * ``efficiency_km_per_l`` – computed km/L (float, rounded to 2 dp)
        * ``record_id`` – id of the current record

        Skipped records produce a dict with:

        * ``date`` – date string
        * ``record_id`` – id of the skipped record
        * ``warning`` – human-readable reason for skipping
    """
    fuel_records: list[dict[str, Any]] = db.get_records(vehicle_id, record_type="fuel")

    if not fuel_records:
        return []

    # get_records returns newest-first; reverse for chronological order.
    fuel_records = list(reversed(fuel_records))

    results: list[dict[str, Any]] = []
    prev_odometer: int | None = None

    for record in fuel_records:
        current_odometer: int | None = record.get("odometer_km")
        current_liters: float | None = record.get("liters")

        # --- Skip conditions ---
        # Missing odometer
        if current_odometer is None:
            results.append({
                "date": record.get("date"),
                "record_id": record["id"],
                "warning": "Skipped: missing odometer reading",
            })
            continue

        # Missing / zero liters
        if current_liters is None or current_liters == 0:
            results.append({
                "date": record.get("date"),
                "record_id": record["id"],
                "warning": "Skipped: missing or zero liters",
            })
            prev_odometer = current_odometer
            continue

        # First valid odometer — no previous to diff against
        if prev_odometer is None:
            prev_odometer = current_odometer
            continue

        distance: int = current_odometer - prev_odometer

        # Zero or negative distance
        if distance <= 0:
            results.append({
                "date": record.get("date"),
                "record_id": record["id"],
                "warning": (
                    "Skipped: zero distance" if distance == 0
                    else "Skipped: negative distance"
                ),
            })
            prev_odometer = current_odometer
            continue

        efficiency: float = distance / current_liters
        results.append({
            "date": record.get("date"),
            "distance_km": distance,
            "liters": current_liters,
            "efficiency_km_per_l": round(efficiency, 2),
            "record_id": record["id"],
        })
        prev_odometer = current_odometer

    return results


# ---------------------------------------------------------------------------
# Monthly spending summary
# ---------------------------------------------------------------------------
@_safe_cache(ttl=300, show_spinner=False)
def monthly_spending_summary(vehicle_id: int, db_version: int = 0) -> list[dict[str, Any]]:
    """
    Aggregate spending by month and record type.

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose records to summarise.

    Returns
    -------
    list[dict]
        Each dict contains:

        * ``month`` – ``"YYYY-MM"`` string
        * ``record_type`` – category (e.g. ``"fuel"``)
        * ``total_amount`` – sum of ``amount_pkr`` for that group (float)
        * ``count`` – number of records in that group (int)

        The list is sorted by month descending, then record_type ascending.
        Returns an empty list when there are no records.
    """
    records: list[dict[str, Any]] = db.get_records(vehicle_id)

    if not records:
        return []

    # Accumulate totals keyed by (YYYY-MM, record_type)
    groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"total_amount": 0.0, "count": 0}
    )

    for rec in records:
        date_str: str = rec.get("date", "")
        # Extract YYYY-MM; tolerate partial dates gracefully.
        month_key: str = date_str[:7] if len(date_str) >= 7 else date_str
        record_type: str = rec.get("record_type", "unknown")
        _raw = rec.get("amount_pkr")
        amount: float = _raw if _raw is not None else 0.0

        key = (month_key, record_type)
        groups[key]["total_amount"] += amount
        groups[key]["count"] += 1

    results: list[dict[str, Any]] = [
        {
            "month": month,
            "record_type": rtype,
            "total_amount": round(data["total_amount"], 2),
            "count": data["count"],
        }
        for (month, rtype), data in groups.items()
    ]

    # Sort: month descending, then record_type ascending
    results.sort(key=lambda r: (r["month"], r["record_type"]), reverse=False)
    results.sort(key=lambda r: r["month"], reverse=True)

    return results


# ---------------------------------------------------------------------------
# Total cost per kilometre
# ---------------------------------------------------------------------------
@_safe_cache(ttl=300, show_spinner=False)
def total_cost_per_km(vehicle_id: int, db_version: int = 0) -> float | None:
    """
    Compute the overall cost per kilometre for a vehicle.

    Formula::

        total_spending / (max_odometer − min_odometer)

    Parameters
    ----------
    vehicle_id : int
        The vehicle to evaluate.

    Returns
    -------
    float or None
        Cost per km (rounded to 2 dp), or ``None`` when:

        * there are no records with spending,
        * the odometer range is zero or unavailable (avoiding ÷ 0).
    """
    records: list[dict[str, Any]] = db.get_records(vehicle_id)

    if not records:
        return None

    total_spending: float = sum(
        rec.get("amount_pkr") or 0.0 for rec in records
    )

    odometers: list[int] = [
        rec["odometer_km"]
        for rec in records
        if rec.get("odometer_km") is not None
    ]

    if not odometers:
        return None

    distance_range: int = max(odometers) - min(odometers)

    if distance_range == 0:
        return None

    if total_spending == 0.0:
        return 0.0

    return round(total_spending / distance_range, 2)


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
@_safe_cache(ttl=300, show_spinner=False)
def get_summary_metrics(vehicle_id: int, db_version: int = 0) -> dict[str, Any]:
    """
    Return a high-level metrics dashboard for a vehicle.

    Parameters
    ----------
    vehicle_id : int
        The vehicle to summarise.

    Returns
    -------
    dict
        Keys:

        * ``total_spend`` – sum of all ``amount_pkr`` (float)
        * ``fuel_spend`` – sum where ``record_type == 'fuel'`` (float)
        * ``maintenance_spend`` – sum where ``record_type == 'maintenance'`` (float)
        * ``insurance_spend`` – sum where ``record_type == 'insurance'`` (float)
        * ``average_fuel_efficiency`` – mean km/L from
          :func:`calculate_fuel_efficiency` (float or ``None``)
        * ``total_distance`` – ``max_odometer − min_odometer`` (int or 0)
        * ``cost_per_km`` – from :func:`total_cost_per_km` (float or ``None``)

        All monetary values default to ``0.0``; distances default to ``0``.
    """
    # Single DB call — all records for this vehicle.
    records: list[dict[str, Any]] = db.get_records(vehicle_id)

    total_spend: float = 0.0
    fuel_spend: float = 0.0
    maintenance_spend: float = 0.0
    insurance_spend: float = 0.0

    odometers: list[int] = []

    for rec in records:
        amount: float = rec.get("amount_pkr") or 0.0
        total_spend += amount

        rtype: str = rec.get("record_type", "")
        if rtype == "fuel":
            fuel_spend += amount
        elif rtype == "maintenance":
            maintenance_spend += amount
        elif rtype == "insurance":
            insurance_spend += amount

        odo: int | None = rec.get("odometer_km")
        if odo is not None:
            odometers.append(odo)

    total_distance: int = (max(odometers) - min(odometers)) if odometers else 0

    # ── Fuel efficiency (inline — same algorithm as calculate_fuel_efficiency) ─
    fuel_recs: list[dict[str, Any]] = sorted(
        [r for r in records if r.get("record_type") == "fuel"],
        key=lambda r: r.get("date", ""),
    )

    efficiencies: list[float] = []
    prev_odo: int | None = None

    for rec in fuel_recs:
        cur_odo: int | None = rec.get("odometer_km")
        cur_liters: float | None = rec.get("liters")

        if cur_odo is None:
            continue
        if cur_liters is None or cur_liters == 0:
            prev_odo = cur_odo
            continue
        if prev_odo is None:
            prev_odo = cur_odo
            continue

        distance: int = cur_odo - prev_odo
        if distance <= 0:
            prev_odo = cur_odo
            continue

        efficiencies.append(round(distance / cur_liters, 2))
        prev_odo = cur_odo

    average_fuel_efficiency: float | None = (
        round(sum(efficiencies) / len(efficiencies), 2)
        if efficiencies
        else None
    )

    # ── Cost per km (inline — same algorithm as total_cost_per_km) ──────────
    cost_per_km: float | None = (
        round(total_spend / total_distance, 2) if total_distance > 0 else None
    )
    if cost_per_km is None and total_spend == 0.0 and total_distance > 0:
        cost_per_km = 0.0

    return {
        "total_spend": round(total_spend, 2),
        "fuel_spend": round(fuel_spend, 2),
        "maintenance_spend": round(maintenance_spend, 2),
        "insurance_spend": round(insurance_spend, 2),
        "average_fuel_efficiency": average_fuel_efficiency,
        "total_distance": total_distance,
        "cost_per_km": cost_per_km,
    }


# ---------------------------------------------------------------------------
# Summary metrics from a pre-filtered record list
# ---------------------------------------------------------------------------
def get_summary_metrics_for_records(
    records: list[dict[str, Any]],
    vehicle_id: int,
) -> dict[str, Any]:
    """
    Compute summary metrics from a pre-filtered record list.

    Mirrors the output structure of :func:`get_summary_metrics` but operates
    entirely on the passed-in *records* list — no additional DB queries are
    issued (fuel-efficiency is computed inline from the same list).

    Parameters
    ----------
    records : list[dict]
        Pre-filtered records in the same dict format returned by
        ``db.get_records()``.  May be in any order; the function sorts
        chronologically internally where needed.
    vehicle_id : int
        Vehicle id — kept for API symmetry with :func:`get_summary_metrics`.

    Returns
    -------
    dict
        Same keys as :func:`get_summary_metrics`:
        ``total_spend``, ``fuel_spend``, ``maintenance_spend``,
        ``insurance_spend``, ``average_fuel_efficiency``,
        ``total_distance``, ``cost_per_km``.
    """
    total_spend: float = 0.0
    fuel_spend: float = 0.0
    maintenance_spend: float = 0.0
    insurance_spend: float = 0.0

    odometers: list[int] = []

    for rec in records:
        amount: float = rec.get("amount_pkr") or 0.0
        total_spend += amount

        rtype: str = rec.get("record_type", "")
        if rtype == "fuel":
            fuel_spend += amount
        elif rtype == "maintenance":
            maintenance_spend += amount
        elif rtype == "insurance":
            insurance_spend += amount

        odo: int | None = rec.get("odometer_km")
        if odo is not None:
            odometers.append(odo)

    total_distance: int = (max(odometers) - min(odometers)) if odometers else 0

    # ── Fuel efficiency (inline, same algorithm as calculate_fuel_efficiency) ─
    fuel_recs: list[dict[str, Any]] = sorted(
        [r for r in records if r.get("record_type") == "fuel"],
        key=lambda r: r.get("date", ""),
    )

    efficiencies: list[float] = []
    prev_odo: int | None = None

    for rec in fuel_recs:
        cur_odo: int | None = rec.get("odometer_km")
        cur_liters: float | None = rec.get("liters")

        if cur_odo is None:
            continue
        if cur_liters is None or cur_liters == 0:
            prev_odo = cur_odo
            continue
        if prev_odo is None:
            prev_odo = cur_odo
            continue

        distance: int = cur_odo - prev_odo
        if distance <= 0:
            prev_odo = cur_odo
            continue

        efficiencies.append(round(distance / cur_liters, 2))
        prev_odo = cur_odo

    average_fuel_efficiency: float | None = (
        round(sum(efficiencies) / len(efficiencies), 2)
        if efficiencies
        else None
    )

    # ── Cost per km ───────────────────────────────────────────────────────────
    cost_per_km: float | None = (
        round(total_spend / total_distance, 2) if total_distance > 0 else None
    )
    if cost_per_km is None and total_spend == 0.0 and total_distance > 0:
        cost_per_km = 0.0

    return {
        "total_spend": round(total_spend, 2),
        "fuel_spend": round(fuel_spend, 2),
        "maintenance_spend": round(maintenance_spend, 2),
        "insurance_spend": round(insurance_spend, 2),
        "average_fuel_efficiency": average_fuel_efficiency,
        "total_distance": total_distance,
        "cost_per_km": cost_per_km,
    }
