"""
test_validation.py — Unit tests for the validation module.

Covers every validation rule defined in ``validate_receipt()``:
    1. Valid record
    2. Negative amount
    3. Zero liters
    4. Negative odometer
    5. Invalid date
    6. Invalid record_type
    7. Missing optional values
    8. Low confidence
    9. Malformed dictionary
"""

from __future__ import annotations

import pytest

from validation import validate_receipt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_receipt(**overrides) -> dict:
    """Return a fully-valid receipt dict, with optional field overrides."""
    base = {
        "record_type": "fuel",
        "date": "2026-08-29",
        "amount_pkr": 5000,
        "liters": 20.5,
        "odometer_km": 42000,
        "description": "Petrol fill-up",
        "vendor_name": "Shell Pakistan",
        "confidence": "high",
        "warnings": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Valid record
# ---------------------------------------------------------------------------

class TestValidRecord:
    def test_all_fields(self):
        result = validate_receipt(_valid_receipt())
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["data"]["record_type"] == "fuel"
        assert result["data"]["amount_pkr"] == 5000

    def test_maintenance_type(self):
        result = validate_receipt(_valid_receipt(
            record_type="maintenance",
            liters=None,
            description="Oil change",
        ))
        assert result["valid"] is True

    def test_insurance_type(self):
        result = validate_receipt(_valid_receipt(
            record_type="insurance",
            liters=None,
            odometer_km=None,
            amount_pkr=25000,
        ))
        assert result["valid"] is True

    def test_unknown_type(self):
        result = validate_receipt(_valid_receipt(record_type="unknown"))
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 2. Negative amount
# ---------------------------------------------------------------------------

class TestNegativeAmount:
    def test_negative_amount_is_invalid(self):
        result = validate_receipt(_valid_receipt(amount_pkr=-500))
        assert result["valid"] is False
        assert any("amount_pkr" in e for e in result["errors"])

    def test_zero_amount_is_valid(self):
        # 0 is allowed (>= 0).
        result = validate_receipt(_valid_receipt(amount_pkr=0))
        assert result["valid"] is True

    def test_none_amount_is_valid(self):
        result = validate_receipt(_valid_receipt(amount_pkr=None))
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 3. Zero liters
# ---------------------------------------------------------------------------

class TestZeroLiters:
    def test_zero_liters_is_invalid(self):
        result = validate_receipt(_valid_receipt(liters=0))
        assert result["valid"] is False
        assert any("liters" in e for e in result["errors"])

    def test_negative_liters_is_invalid(self):
        result = validate_receipt(_valid_receipt(liters=-5))
        assert result["valid"] is False
        assert any("liters" in e for e in result["errors"])

    def test_none_liters_is_valid(self):
        result = validate_receipt(_valid_receipt(liters=None))
        assert result["valid"] is True

    def test_positive_liters_is_valid(self):
        result = validate_receipt(_valid_receipt(liters=10.2))
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 4. Negative odometer
# ---------------------------------------------------------------------------

class TestNegativeOdometer:
    def test_negative_odometer_is_invalid(self):
        result = validate_receipt(_valid_receipt(odometer_km=-100))
        assert result["valid"] is False
        assert any("odometer_km" in e for e in result["errors"])

    def test_zero_odometer_is_valid(self):
        # 0 is allowed (>= 0).
        result = validate_receipt(_valid_receipt(odometer_km=0))
        assert result["valid"] is True

    def test_none_odometer_is_valid(self):
        result = validate_receipt(_valid_receipt(odometer_km=None))
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 5. Invalid date
# ---------------------------------------------------------------------------

class TestInvalidDate:
    def test_garbage_date(self):
        result = validate_receipt(_valid_receipt(date="not-a-date"))
        assert result["valid"] is False
        assert any("date" in e for e in result["errors"])

    def test_wrong_format(self):
        result = validate_receipt(_valid_receipt(date="29-08-2026"))
        assert result["valid"] is False
        assert any("date" in e for e in result["errors"])

    def test_impossible_date(self):
        # February 30 does not exist.
        result = validate_receipt(_valid_receipt(date="2026-02-30"))
        assert result["valid"] is False
        assert any("date" in e for e in result["errors"])

    def test_none_date_is_valid(self):
        result = validate_receipt(_valid_receipt(date=None))
        assert result["valid"] is True

    def test_valid_date(self):
        result = validate_receipt(_valid_receipt(date="2026-08-29"))
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 6. Invalid record_type
# ---------------------------------------------------------------------------

class TestInvalidRecordType:
    def test_unknown_string(self):
        result = validate_receipt(_valid_receipt(record_type="grocery"))
        assert result["valid"] is False
        assert any("record_type" in e for e in result["errors"])

    def test_missing_record_type(self):
        data = _valid_receipt()
        del data["record_type"]
        result = validate_receipt(data)
        assert result["valid"] is False
        assert any("record_type" in e for e in result["errors"])

    def test_none_record_type(self):
        result = validate_receipt(_valid_receipt(record_type=None))
        assert result["valid"] is False
        assert any("record_type" in e for e in result["errors"])

    def test_integer_record_type(self):
        result = validate_receipt(_valid_receipt(record_type=42))
        assert result["valid"] is False
        assert any("record_type" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 7. Missing optional values
# ---------------------------------------------------------------------------

class TestMissingOptionalValues:
    def test_only_required_fields(self):
        # record_type and confidence are the only required fields.
        data = {"record_type": "fuel", "confidence": "high"}
        result = validate_receipt(data)
        assert result["valid"] is True
        assert result["data"]["record_type"] == "fuel"

    def test_all_optional_null(self):
        data = {
            "record_type": "maintenance",
            "confidence": "medium",
            "amount_pkr": None,
            "liters": None,
            "odometer_km": None,
            "date": None,
            "description": None,
            "vendor_name": None,
            "warnings": [],
        }
        result = validate_receipt(data)
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 8. Low confidence
# ---------------------------------------------------------------------------

class TestLowConfidence:
    def test_low_confidence_is_valid_with_warning(self):
        result = validate_receipt(_valid_receipt(confidence="low"))
        assert result["valid"] is True
        assert any("low confidence" in w.lower() for w in result["warnings"])

    def test_invalid_confidence_value(self):
        result = validate_receipt(_valid_receipt(confidence="very_high"))
        assert result["valid"] is False
        assert any("confidence" in e for e in result["errors"])

    def test_missing_confidence(self):
        data = _valid_receipt()
        del data["confidence"]
        result = validate_receipt(data)
        assert result["valid"] is False
        assert any("confidence" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 9. Malformed dictionary
# ---------------------------------------------------------------------------

class TestMalformedDictionary:
    def test_none_input(self):
        result = validate_receipt(None)  # type: ignore[arg-type]
        assert result["valid"] is False
        assert result["data"] == {}

    def test_string_input(self):
        result = validate_receipt("not a dict")  # type: ignore[arg-type]
        assert result["valid"] is False
        assert result["data"] == {}

    def test_integer_input(self):
        result = validate_receipt(42)  # type: ignore[arg-type]
        assert result["valid"] is False

    def test_list_input(self):
        result = validate_receipt([1, 2, 3])  # type: ignore[arg-type]
        assert result["valid"] is False

    def test_empty_dict(self):
        result = validate_receipt({})
        assert result["valid"] is False
        # Should flag both missing required fields.
        assert any("record_type" in e for e in result["errors"])
        assert any("confidence" in e for e in result["errors"])

    def test_wrong_type_amount(self):
        result = validate_receipt(_valid_receipt(amount_pkr="five thousand"))
        assert result["valid"] is False
        assert any("amount_pkr" in e for e in result["errors"])

    def test_boolean_as_number(self):
        # bool is a subclass of int — must still be rejected.
        result = validate_receipt(_valid_receipt(amount_pkr=True))
        assert result["valid"] is False
        assert any("amount_pkr" in e for e in result["errors"])

    def test_warnings_field_not_a_list(self):
        result = validate_receipt(_valid_receipt(warnings="bad"))
        assert result["valid"] is False
        assert any("warnings" in e for e in result["errors"])
