"""
anomaly.py — Anomaly detection in expense and maintenance data for SafarSync AI.

Detects statistical outliers in fuel spending, fuel volume, fuel efficiency
(km/L), and maintenance costs by comparing each record against the historical
baseline built from earlier records of the same vehicle.

All calculations are pure Python — no AI or external analytics involved.

Public API::

    from anomaly import find_anomalies

    anomalies = find_anomalies(vehicle_id=1)
    for a in anomalies:
        print(a["type"], a["severity"], a["message"])
"""

from __future__ import annotations

import logging
from typing import Any

import database as db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

# Minimum number of *prior* records of the same type needed before we can
# establish a reliable baseline.  Below this count anomalies are NOT flagged.
_MIN_HISTORY: int = 3

# Multiplier thresholds — ratio of (value / baseline_avg) at which each
# severity level triggers.  Checked high → low so the first match wins.
_INFO_THRESHOLD: float = 1.5
_WARNING_THRESHOLD: float = 2.0
_HIGH_THRESHOLD: float = 3.0

# For fuel-efficiency decline the ratio is inverted (current / baseline),
# so *lower* is worse.  These thresholds apply to the inverse ratio
# (baseline / current) so the same high→low logic works uniformly.
_EFFICIENCY_INFO_THRESHOLD: float = 1.3
_EFFICIENCY_WARNING_THRESHOLD: float = 1.6
_EFFICIENCY_HIGH_THRESHOLD: float = 2.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _severity_for_ratio(
    ratio: float,
    *,
    info: float,
    warning: float,
    high: float,
) -> str | None:
    """Return severity label for *ratio* (value / avg), or ``None`` if below
    the lowest threshold."""
    if ratio >= high:
        return "high"
    if ratio >= warning:
        return "warning"
    if ratio >= info:
        return "info"
    return None


def _avg(values: list[float]) -> float:
    """Arithmetic mean — caller guarantees *values* is non-empty."""
    return sum(values) / len(values)


def _make_anomaly(
    anomaly_type: str,
    severity: str,
    message: str,
    record_id: int,
) -> dict[str, Any]:
    """Build a single anomaly dict with the canonical key set."""
    return {
        "type": anomaly_type,
        "severity": severity,
        "message": message,
        "record_id": record_id,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def find_anomalies(vehicle_id: int) -> list[dict[str, Any]]:
    """Detect anomalies in a vehicle's expense and maintenance records.

    The function scans **all** fuel and maintenance records for the given
    vehicle.  Each record is compared against the average of all *earlier*
    records of the same type (chronological baseline).  Anomalies are
    reported only when there are at least :data:`_MIN_HISTORY` prior records
    to form a meaningful baseline.

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose records should be analysed.

    Returns
    -------
    list[dict]
        Zero or more anomaly dicts, each containing:

        * ``type``        — ``"fuel_amount"`` | ``"fuel_liters"`` |
          ``"fuel_efficiency"`` | ``"maintenance_cost"``
        * ``severity``    — ``"info"`` | ``"warning"`` | ``"high"``
        * ``message``     — human-readable explanation
        * ``record_id``   — primary key of the flagged record

        Returns an empty list when there is insufficient data or on any
        unexpected error (the function **never** raises).
    """
    try:
        return _detect(vehicle_id)
    except Exception:
        logger.exception("Unexpected error in find_anomalies(%s)", vehicle_id)
        return []


# ---------------------------------------------------------------------------
# Detection engine (private)
# ---------------------------------------------------------------------------
def _detect(vehicle_id: int) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []

    # -- fetch records and sort chronologically (oldest first) -------------
    all_records: list[dict[str, Any]] = db.get_records(vehicle_id)
    all_records.sort(key=lambda r: r.get("date") or "")

    fuel_records: list[dict[str, Any]] = [
        r for r in all_records if r.get("record_type") == "fuel"
    ]
    maintenance_records: list[dict[str, Any]] = [
        r for r in all_records if r.get("record_type") == "maintenance"
    ]

    # -- 1. Fuel amount spikes ---------------------------------------------
    anomalies.extend(_check_fuel_amount(fuel_records))

    # -- 2. Fuel liter spikes ----------------------------------------------
    anomalies.extend(_check_fuel_liters(fuel_records))

    # -- 3. Fuel-efficiency decline ----------------------------------------
    anomalies.extend(_check_fuel_efficiency(fuel_records))

    # -- 4. Maintenance cost spikes ----------------------------------------
    anomalies.extend(_check_maintenance_cost(maintenance_records))

    return anomalies


# -- individual checkers ---------------------------------------------------

def _check_fuel_amount(
    fuel_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    history: list[float] = []

    for rec in fuel_records:
        amount = rec.get("amount_pkr")
        if amount is None or amount <= 0:
            continue

        if len(history) >= _MIN_HISTORY:
            avg = _avg(history)
            if avg > 0:
                ratio = amount / avg
                sev = _severity_for_ratio(
                    ratio,
                    info=_INFO_THRESHOLD,
                    warning=_WARNING_THRESHOLD,
                    high=_HIGH_THRESHOLD,
                )
                if sev is not None:
                    anomalies.append(_make_anomaly(
                        "fuel_amount",
                        sev,
                        f"Fuel amount PKR {amount:,.0f} is {ratio:.1f}x the "
                        f"recent average of PKR {avg:,.0f}",
                        rec["id"],
                    ))

        history.append(amount)

    return anomalies


def _check_fuel_liters(
    fuel_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    history: list[float] = []

    for rec in fuel_records:
        liters = rec.get("liters")
        if liters is None or liters <= 0:
            continue

        if len(history) >= _MIN_HISTORY:
            avg = _avg(history)
            if avg > 0:
                ratio = liters / avg
                sev = _severity_for_ratio(
                    ratio,
                    info=_INFO_THRESHOLD,
                    warning=_WARNING_THRESHOLD,
                    high=_HIGH_THRESHOLD,
                )
                if sev is not None:
                    anomalies.append(_make_anomaly(
                        "fuel_liters",
                        sev,
                        f"Fuel volume {liters:.1f} L is {ratio:.1f}x the "
                        f"recent average of {avg:.1f} L",
                        rec["id"],
                    ))

        history.append(liters)

    return anomalies


def _check_fuel_efficiency(
    fuel_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect significant drops in km-per-litre.

    For every pair of consecutive fuel records that both carry an odometer
    reading, the trip distance is divided by the *current* fill-up's liters
    to obtain km/L.  This is compared against the average km/L of all
    earlier qualifying trips.
    """
    anomalies: list[dict[str, Any]] = []
    efficiency_history: list[float] = []

    prev_odometer: float | None = None

    for rec in fuel_records:
        odometer = rec.get("odometer_km")
        liters = rec.get("liters")

        if odometer is not None and prev_odometer is not None and \
                liters and liters > 0 and odometer > prev_odometer:
            km_per_liter = (odometer - prev_odometer) / liters

            if len(efficiency_history) >= _MIN_HISTORY:
                avg_eff = _avg(efficiency_history)
                if avg_eff > 0 and km_per_liter > 0:
                    # Invert: higher = worse efficiency
                    decline_ratio = avg_eff / km_per_liter
                    sev = _severity_for_ratio(
                        decline_ratio,
                        info=_EFFICIENCY_INFO_THRESHOLD,
                        warning=_EFFICIENCY_WARNING_THRESHOLD,
                        high=_EFFICIENCY_HIGH_THRESHOLD,
                    )
                    if sev is not None:
                        anomalies.append(_make_anomaly(
                            "fuel_efficiency",
                            sev,
                            f"Fuel efficiency {km_per_liter:.1f} km/L is a "
                            f"{decline_ratio:.1f}x decline from the average "
                            f"of {avg_eff:.1f} km/L",
                            rec["id"],
                        ))

            efficiency_history.append(km_per_liter)

        if odometer is not None and (prev_odometer is None or odometer >= prev_odometer):
            prev_odometer = odometer

    return anomalies


def _check_maintenance_cost(
    maintenance_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    history: list[float] = []

    for rec in maintenance_records:
        amount = rec.get("amount_pkr")
        if amount is None or amount <= 0:
            continue

        if len(history) >= _MIN_HISTORY:
            avg = _avg(history)
            if avg > 0:
                ratio = amount / avg
                sev = _severity_for_ratio(
                    ratio,
                    info=_INFO_THRESHOLD,
                    warning=_WARNING_THRESHOLD,
                    high=_HIGH_THRESHOLD,
                )
                if sev is not None:
                    anomalies.append(_make_anomaly(
                        "maintenance_cost",
                        sev,
                        f"Maintenance cost PKR {amount:,.0f} is {ratio:.1f}x "
                        f"the recent average of PKR {avg:,.0f}",
                        rec["id"],
                    ))

        history.append(amount)

    return anomalies
