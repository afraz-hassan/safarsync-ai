"""
validation.py — Input and data validation utilities for SafarSync AI.

Provides ``validate_receipt(data)`` which checks a parsed-receipt dictionary
against the canonical schema produced by ``receipt_scanner.parse_receipt_text``
and returns a structured validation result.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Allowed enum values.
_VALID_RECORD_TYPES = frozenset({"fuel", "maintenance", "insurance", "unknown"})
_VALID_CONFIDENCE_LEVELS = frozenset({"high", "medium", "low"})

# Fields that must be present (non-null) for a record to be valid.
_REQUIRED_FIELDS = frozenset({"record_type", "confidence"})

# Fields that are optional — their absence is not an error.
_OPTIONAL_FIELDS = frozenset({
    "amount_pkr",
    "liters",
    "odometer_km",
    "date",
    "description",
    "vendor_name",
    "warnings",
    # raw_response is carried through from the scanner; not validated.
    "raw_response",
})


def _is_number(value: object) -> bool:
    """Return True for int/float values, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_receipt(data: dict) -> dict:
    """
    Validate a receipt dictionary against the SafarSync AI schema.

    The function never raises an exception, even on severely malformed input.

    Parameters
    ----------
    data : dict
        Dictionary produced by ``parse_receipt_text`` or equivalent.

    Returns
    -------
    dict
        {
            "valid":    bool,
            "errors":   list[str],
            "warnings": list[str],
            "data":     dict | {}
        }
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Guard: non-dict input
    # ------------------------------------------------------------------
    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["Input is not a dictionary."],
            "warnings": [],
            "data": {},
        }

    # ------------------------------------------------------------------
    # record_type — required, enum
    # ------------------------------------------------------------------
    record_type = data.get("record_type")
    if record_type is None:
        errors.append("Missing required field: record_type.")
    elif not isinstance(record_type, str):
        errors.append("record_type must be a string.")
    elif record_type not in _VALID_RECORD_TYPES:
        errors.append(
            f"Invalid record_type '{record_type}'. "
            f"Must be one of: {', '.join(sorted(_VALID_RECORD_TYPES))}."
        )

    # ------------------------------------------------------------------
    # amount_pkr — optional, null or >= 0
    # ------------------------------------------------------------------
    amount_pkr = data.get("amount_pkr")
    if amount_pkr is not None:
        if not _is_number(amount_pkr):
            errors.append("amount_pkr must be a number or null.")
        elif amount_pkr < 0:
            errors.append("amount_pkr must be >= 0.")

    # ------------------------------------------------------------------
    # liters — optional, null or > 0
    # ------------------------------------------------------------------
    liters = data.get("liters")
    if liters is not None:
        if not _is_number(liters):
            errors.append("liters must be a number or null.")
        elif liters <= 0:
            errors.append("liters must be > 0.")

    # ------------------------------------------------------------------
    # odometer_km — optional, null or >= 0
    # ------------------------------------------------------------------
    odometer_km = data.get("odometer_km")
    if odometer_km is not None:
        if not _is_number(odometer_km):
            errors.append("odometer_km must be a number or null.")
        elif odometer_km < 0:
            errors.append("odometer_km must be >= 0.")

    # ------------------------------------------------------------------
    # date — optional, null or valid YYYY-MM-DD
    # ------------------------------------------------------------------
    date = data.get("date")
    if date is not None:
        if not isinstance(date, str):
            errors.append("date must be a string or null.")
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Invalid date format '{date}'. Expected YYYY-MM-DD.")

    # ------------------------------------------------------------------
    # confidence — required, enum
    # ------------------------------------------------------------------
    confidence = data.get("confidence")
    if confidence is None:
        errors.append("Missing required field: confidence.")
    elif not isinstance(confidence, str):
        errors.append("confidence must be a string.")
    elif confidence not in _VALID_CONFIDENCE_LEVELS:
        errors.append(
            f"Invalid confidence '{confidence}'. "
            f"Must be one of: {', '.join(sorted(_VALID_CONFIDENCE_LEVELS))}."
        )

    # ------------------------------------------------------------------
    # warnings field — if present, must be a list
    # ------------------------------------------------------------------
    data_warnings = data.get("warnings")
    if data_warnings is not None and not isinstance(data_warnings, list):
        errors.append("warnings must be a list.")

    # ------------------------------------------------------------------
    # Low-confidence advisory warning (does not affect valid flag)
    # ------------------------------------------------------------------
    if confidence == "low":
        warnings.append("Low confidence — manual review recommended.")

    # ------------------------------------------------------------------
    # Surface scanner-level warnings carried inside the data dict
    # ------------------------------------------------------------------
    if isinstance(data_warnings, list):
        for item in data_warnings:
            if isinstance(item, str):
                warnings.append(item)

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "data": data if valid else {},
    }
