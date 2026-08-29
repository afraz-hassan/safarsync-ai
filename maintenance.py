"""
maintenance.py — Vehicle maintenance tracking and scheduling for SafarSync AI.

Tracks scheduled service intervals (oil change, air filter, brake check,
tire rotation) and determines whether each service is overdue, due soon,
or still within tolerance.  An AI advice helper combines the maintenance
status with recent fuel-efficiency data and asks *qwen-plus-character* for
a short plain-language summary.

All persistence goes through :mod:`database`; this module never writes SQL
directly.
"""

from __future__ import annotations

import logging
from typing import Any

import database as db
import analytics
import config
from ai_client import ask_text

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Maintenance schedule — kilometres between services.
# ---------------------------------------------------------------------------
MAINTENANCE_SCHEDULE_KM: dict[str, int] = {
    "oil_change": 5000,
    "air_filter": 10000,
    "brake_check": 15000,
    "tire_rotation": 8000,
}

# A service is "due soon" when the remaining distance to its interval is
# at or below this threshold (km).
_DUE_SOON_THRESHOLD_KM: int = 1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_odometer(vehicle_id: int) -> int | None:
    """
    Return the highest odometer reading across *all* records for a vehicle.

    Returns ``None`` when no record carries an odometer value.
    """
    records: list[dict[str, Any]] = db.get_records(vehicle_id)
    odometers: list[int] = [
        rec["odometer_km"]
        for rec in records
        if rec.get("odometer_km") is not None
    ]
    return max(odometers) if odometers else None


def _latest_service_odometer(vehicle_id: int, service_type: str) -> int | None:
    """
    Return the odometer reading of the most recent maintenance record whose
    ``record_type`` matches *service_type*.

    ``get_records`` returns rows newest-first, so the first record with a
    non-``None`` odometer is the latest one.

    Returns ``None`` when no matching record exists or none carries an
    odometer value.
    """
    records: list[dict[str, Any]] = db.get_records(vehicle_id, record_type=service_type)
    for rec in records:  # already newest-first
        odo: int | None = rec.get("odometer_km")
        if odo is not None:
            return odo
    return None


# ---------------------------------------------------------------------------
# Public: check due maintenance
# ---------------------------------------------------------------------------
def check_due_maintenance(vehicle_id: int) -> list[dict[str, Any]]:
    """
    Evaluate every scheduled service for a vehicle and return its status.

    For each entry in :data:`MAINTENANCE_SCHEDULE_KM` the function:

    1. Determines the current (maximum) odometer reading.
    2. Finds the most recent matching maintenance record.
    3. Calculates the kilometres driven since that service.
    4. Assigns a status:

       * ``"not_due"``  — more than *_DUE_SOON_THRESHOLD_KM* remaining.
       * ``"due_soon"`` — within *_DUE_SOON_THRESHOLD_KM* of the interval.
       * ``"overdue"``  — ``km_since_last`` ≥ interval.
       * ``"unknown"``  — current odometer unavailable.

    Parameters
    ----------
    vehicle_id : int
        The vehicle to evaluate.

    Returns
    -------
    list[dict]
        One entry per scheduled service, each containing:

        * ``type`` – service name (e.g. ``"oil_change"``)
        * ``interval_km`` – scheduled interval (int)
        * ``km_since_last`` – km since last service (int or ``None``)
        * ``status`` – one of ``not_due``, ``due_soon``, ``overdue``, ``unknown``
        * ``overdue_by`` – km past the interval (int or ``None``)
    """
    current_odo: int | None = _current_odometer(vehicle_id)
    results: list[dict[str, Any]] = []

    for service_type, interval in MAINTENANCE_SCHEDULE_KM.items():
        last_service_odo: int | None = _latest_service_odometer(vehicle_id, service_type)

        # --- Cannot evaluate without a current odometer ---
        if current_odo is None:
            results.append({
                "type": service_type,
                "interval_km": interval,
                "km_since_last": None,
                "status": "unknown",
                "overdue_by": None,
            })
            continue

        # --- No prior service on record → treat as overdue ---
        if last_service_odo is None:
            results.append({
                "type": service_type,
                "interval_km": interval,
                "km_since_last": None,
                "status": "overdue",
                "overdue_by": None,
            })
            continue

        km_since: int = current_odo - last_service_odo
        remaining: int = interval - km_since

        if km_since >= interval:
            status = "overdue"
            overdue_by: int | None = km_since - interval
        elif remaining <= _DUE_SOON_THRESHOLD_KM:
            status = "due_soon"
            overdue_by = None
        else:
            status = "not_due"
            overdue_by = None

        results.append({
            "type": service_type,
            "interval_km": interval,
            "km_since_last": km_since,
            "status": status,
            "overdue_by": overdue_by,
        })

    return results


# ---------------------------------------------------------------------------
# Public: AI maintenance advice
# ---------------------------------------------------------------------------
def get_ai_maintenance_advice(vehicle_id: int) -> str:
    """
    Generate a short AI-driven maintenance recommendation.

    The function:

    1. Computes maintenance status locally via :func:`check_due_maintenance`.
    2. Fetches recent fuel-efficiency data from
       :func:`analytics.calculate_fuel_efficiency`.
    3. Composes a prompt containing **only verified facts** — the model is
       explicitly instructed not to invent numbers.
    4. Sends the prompt to *qwen-plus-character* via :func:`ai_client.ask_text`.
    5. Returns a 2-4 sentence recommendation.

    If the API call fails for any reason (network, auth, timeout, server
    error), a safe fallback message is returned instead.

    Parameters
    ----------
    vehicle_id : int
        The vehicle to advise on.

    Returns
    -------
    str
        A short maintenance recommendation (2-4 sentences), or a fallback
        message when the AI service is unavailable.
    """
    # --- 1. Local maintenance status ---
    maintenance_status: list[dict[str, Any]] = check_due_maintenance(vehicle_id)

    # --- 2. Recent fuel efficiency (last 3 valid entries) ---
    efficiency_data: list[dict[str, Any]] = analytics.calculate_fuel_efficiency(vehicle_id)
    recent_efficiency: list[dict[str, Any]] = [
        e for e in efficiency_data if "efficiency_km_per_l" in e
    ][-3:]  # last 3 valid entries (chronological)

    # --- 3. Build prompt with verified facts only ---
    overdue_services: list[dict[str, Any]] = [
        s for s in maintenance_status if s["status"] == "overdue"
    ]
    due_soon_services: list[dict[str, Any]] = [
        s for s in maintenance_status if s["status"] == "due_soon"
    ]

    facts_lines: list[str] = []

    if overdue_services:
        names = ", ".join(s["type"].replace("_", " ") for s in overdue_services)
        facts_lines.append(f"Overdue services: {names}.")
    else:
        facts_lines.append("No overdue services.")

    if due_soon_services:
        names = ", ".join(s["type"].replace("_", " ") for s in due_soon_services)
        facts_lines.append(f"Services due soon: {names}.")
    else:
        facts_lines.append("No services due soon.")

    if recent_efficiency:
        avg_eff = sum(e["efficiency_km_per_l"] for e in recent_efficiency) / len(recent_efficiency)
        facts_lines.append(f"Recent average fuel efficiency: {avg_eff:.1f} km/L.")
    else:
        facts_lines.append("No recent fuel efficiency data available.")

    facts_block: str = "\n".join(facts_lines)

    prompt: str = (
        "You are a vehicle maintenance advisor for the SafarSync AI app.\n"
        "Below are verified facts about the vehicle's maintenance status.\n"
        "Use ONLY these facts — do NOT invent numbers or services.\n\n"
        f"{facts_block}\n\n"
        "Write 2-4 sentences of practical maintenance advice based on these facts."
    )

    # --- 4. Call the AI model ---
    try:
        advice: str = ask_text(prompt, model=config.QWEN_PLUS_CHARACTER, max_tokens=200)
        if advice:
            return advice
    except (PermissionError, ConnectionError, TimeoutError, RuntimeError) as exc:
        logger.warning("AI maintenance advice failed: %s", exc)

    # --- 5. Fallback response ---
    fallback_parts: list[str] = []
    if overdue_services:
        names = ", ".join(s["type"].replace("_", " ") for s in overdue_services)
        fallback_parts.append(f"Attention needed: {names} is/are overdue for service.")
    if due_soon_services:
        names = ", ".join(s["type"].replace("_", " ") for s in due_soon_services)
        fallback_parts.append(f"Upcoming: {names} will be due soon.")
    if not fallback_parts:
        fallback_parts.append("All scheduled maintenance is up to date.")

    return " ".join(fallback_parts)
