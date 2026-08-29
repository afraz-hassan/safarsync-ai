"""
insights.py — AI-driven insights generation from expense and maintenance data.

Combines verified, Python-calculated facts from three sources — analytics
metrics, maintenance status, and anomaly detection — then asks
*qwen-plus-character* to rewrite them as a short, user-friendly insight.

If the AI call fails for **any** reason, a plain text fallback built from
the same facts is returned instead, so the caller always gets a usable
string.

Public API::

    from insights import get_vehicle_insight

    insight_text = get_vehicle_insight(vehicle_id=1)
"""

from __future__ import annotations

import logging
from typing import Any

import analytics
import anomaly
import config
import maintenance
from ai_client import ask_text

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# Maximum words we ask the AI model to produce.
_MAX_INSIGHT_WORDS: int = 120

# Max tokens sent to the model — generous enough for ~120 words but keeps
# cost and latency in check.
_MAX_TOKENS: int = 250


# ---------------------------------------------------------------------------
# Internal: build a compact facts block from verified data
# ---------------------------------------------------------------------------
def _build_facts(vehicle_id: int) -> tuple[str, dict[str, Any]]:
    """Collect verified facts from analytics, maintenance, and anomaly modules.

    Returns
    -------
    tuple[str, dict]
        A two-element tuple:
        * A multi-line string of human-readable facts ready for the prompt.
        * A dict of the raw data used to build it (for the fallback path).
    """
    # --- 1. Summary metrics ---
    metrics: dict[str, Any] = analytics.get_summary_metrics(vehicle_id)

    # --- 2. Maintenance status ---
    maint_status: list[dict[str, Any]] = maintenance.check_due_maintenance(vehicle_id)

    # --- 3. Anomalies ---
    anomalies_list: list[dict[str, Any]] = anomaly.find_anomalies(vehicle_id)

    # --- Compose fact lines ---
    lines: list[str] = []

    # Spending
    lines.append(f"Total spending: PKR {metrics['total_spend']:,.0f}.")
    if metrics["fuel_spend"]:
        lines.append(f"Fuel spending: PKR {metrics['fuel_spend']:,.0f}.")
    if metrics["maintenance_spend"]:
        lines.append(f"Maintenance spending: PKR {metrics['maintenance_spend']:,.0f}.")
    if metrics["insurance_spend"]:
        lines.append(f"Insurance spending: PKR {metrics['insurance_spend']:,.0f}.")

    # Distance & efficiency
    if metrics["total_distance"]:
        lines.append(f"Total distance tracked: {metrics['total_distance']:,} km.")
    if metrics["average_fuel_efficiency"] is not None:
        lines.append(
            f"Average fuel efficiency: {metrics['average_fuel_efficiency']:.1f} km/L."
        )
    if metrics["cost_per_km"] is not None:
        lines.append(f"Cost per km: PKR {metrics['cost_per_km']:.2f}.")

    # Maintenance status — only mention actionable items
    overdue = [s for s in maint_status if s["status"] == "overdue"]
    due_soon = [s for s in maint_status if s["status"] == "due_soon"]

    if overdue:
        names = ", ".join(s["type"].replace("_", " ") for s in overdue)
        lines.append(f"Overdue services: {names}.")
    if due_soon:
        names = ", ".join(s["type"].replace("_", " ") for s in due_soon)
        lines.append(f"Services due soon: {names}.")
    if not overdue and not due_soon:
        lines.append("All scheduled maintenance is up to date.")

    # Anomalies — include the most severe ones (cap at 5 to stay compact)
    if anomalies_list:
        # Sort: high > warning > info, then take top 5
        severity_order = {"high": 0, "warning": 1, "info": 2}
        sorted_anomalies = sorted(
            anomalies_list,
            key=lambda a: severity_order.get(a.get("severity", "info"), 3),
        )
        top_anomalies = sorted_anomalies[:5]
        lines.append("Anomalies detected:")
        for a in top_anomalies:
            lines.append(f"  - [{a['severity'].upper()}] {a['message']}")
    else:
        lines.append("No spending anomalies detected.")

    facts_text = "\n".join(lines)
    raw_data = {
        "metrics": metrics,
        "maintenance": maint_status,
        "anomalies": anomalies_list,
    }

    return facts_text, raw_data


# ---------------------------------------------------------------------------
# Internal: build a plain-text fallback when AI is unavailable
# ---------------------------------------------------------------------------
def _build_fallback(facts_text: str) -> str:
    """Return a simple summary of facts when the AI model cannot be reached.

    Just wraps the verified facts in a readable header so the user still
    gets useful information.
    """
    return (
        "Here is a summary of your vehicle data:\n\n"
        f"{facts_text}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_vehicle_insight(vehicle_id: int) -> str:
    """Generate a short, AI-written insight for a vehicle.

    The function:

    1. Calls :func:`analytics.get_summary_metrics` for verified spending and
       efficiency numbers.
    2. Calls :func:`maintenance.check_due_maintenance` for service status.
    3. Calls :func:`anomaly.find_anomalies` for spending / efficiency outliers.
    4. Composes a compact text block of **only** verified facts.
    5. Sends the facts to *qwen-plus-character* via
       :func:`ai_client.ask_text` with strict instructions: use only the
       supplied facts, mention specific numbers, keep it under 120 words,
       and prioritise actionable advice.
    6. Returns the AI-generated insight.

    If **any** step fails (data retrieval, AI call, empty response), a plain
    text summary of the Python-calculated facts is returned instead — the
    function never raises.

    Parameters
    ----------
    vehicle_id : int
        The vehicle to generate an insight for.

    Returns
    -------
    str
        A short insight paragraph (under 120 words), or a factual fallback
        summary when AI is unavailable.
    """
    try:
        return _generate(vehicle_id)
    except Exception:
        logger.exception("Unexpected error in get_vehicle_insight(%s)", vehicle_id)
        return "Unable to generate insight at this time. Please try again later."


# ---------------------------------------------------------------------------
# Generation engine (private)
# ---------------------------------------------------------------------------
def _generate(vehicle_id: int) -> str:
    # --- Collect verified facts ---
    facts_text, _raw = _build_facts(vehicle_id)

    # --- Build the prompt ---
    prompt: str = (
        "You are a friendly vehicle insights advisor for the SafarSync AI app.\n"
        "Below are verified facts about the vehicle — calculated by our system.\n\n"
        f"{facts_text}\n\n"
        "Write a short, user-friendly insight paragraph based ONLY on these facts.\n"
        "Rules:\n"
        "• Use only the numbers and facts provided above.\n"
        "• Do NOT invent measurements, costs, or statistics.\n"
        "• Do NOT diagnose mechanical failures or speculate on causes.\n"
        "• Mention specific numbers from the data (e.g. exact PKR amounts, km values).\n"
        "• Prioritise actionable information the user can act on today.\n"
        f"• Keep your response under {_MAX_INSIGHT_WORDS} words."
    )

    # --- Call the AI model ---
    try:
        insight: str = ask_text(
            prompt,
            model=config.QWEN_PLUS_CHARACTER,
            max_tokens=_MAX_TOKENS,
        )
        if insight and insight.strip():
            return insight.strip()
    except (PermissionError, ConnectionError, TimeoutError, RuntimeError) as exc:
        logger.warning("AI insight generation failed: %s", exc)

    # --- Fallback: return plain facts ---
    return _build_fallback(facts_text)
