"""
test_receipt_scanner.py — Unit tests for the receipt_scanner module.

Tests ``parse_receipt_text()`` and ``_extract_json_object()`` by mocking
the AI client to return controlled JSON strings.  No real API calls are made.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

import receipt_scanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mock_ai_response(json_dict: dict[str, Any]) -> MagicMock:
    """
    Build a mock OpenAI client whose ``chat.completions.create`` returns
    *json_dict* serialised as JSON in the message content.
    """
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(json_dict)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


# ===================================================================
# TestValidJSON — AI returns clean JSON → correct parsing
# ===================================================================
class TestValidJSON:

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_clean_json_parsed(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        ai_json: dict[str, Any] = {
            "record_type": "fuel",
            "date": "2026-08-15",
            "amount_pkr": 5000,
            "liters": 20.5,
            "odometer_km": 42000,
            "description": "Petrol fill-up",
            "vendor_name": "Shell Pakistan",
            "confidence": "high",
            "warnings": [],
            "line_items": [],
            "category": None,
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("receipt_scanner._get_ai_client", return_value=mock_client, create=True):
            # Patch the local import target
            with patch("ai_client.get_client", return_value=mock_client):
                result = receipt_scanner.parse_receipt_text("Shell Pakistan\nPetrol 5000 PKR\n20.5 liters")

        assert result.get("record_type") == "fuel"
        assert result.get("amount_pkr") == 5000.0
        assert result.get("liters") == 20.5
        assert result.get("odometer_km") == 42000
        assert "error" not in result


# ===================================================================
# TestJSONInMarkdown — AI returns ```json ... ``` wrapped → fallback parser
# ===================================================================
class TestJSONInMarkdown:

    def test_markdown_wrapped_json_extracted(self) -> None:
        """_extract_json_object pulls JSON from markdown code fences."""
        wrapped = '```json\n{"record_type": "fuel", "amount_pkr": 3000}\n```'
        result = receipt_scanner._extract_json_object(wrapped)
        assert result is not None
        assert result["record_type"] == "fuel"
        assert result["amount_pkr"] == 3000

    def test_json_with_surrounding_prose(self) -> None:
        """_extract_json_object finds JSON embedded in prose."""
        text = 'Here is the result:\n{"record_type": "maintenance", "amount_pkr": 8000}\nDone.'
        result = receipt_scanner._extract_json_object(text)
        assert result is not None
        assert result["record_type"] == "maintenance"


# ===================================================================
# TestMalformedJSON — AI returns garbage → returns error dict
# ===================================================================
class TestMalformedJSON:

    def test_garbage_returns_none(self) -> None:
        """_extract_json_object returns None for unparseable text."""
        result = receipt_scanner._extract_json_object("this is not json at all!!!")
        assert result is None

    def test_empty_braces(self) -> None:
        """_extract_json_object returns empty dict for {}."""
        result = receipt_scanner._extract_json_object("{}")
        assert result == {}

    def test_no_json_in_markdown(self) -> None:
        """Markdown fence with no valid JSON inside → None."""
        result = receipt_scanner._extract_json_object("```json\nnot valid json\n```")
        assert result is None


# ===================================================================
# TestTypeCoercion — amount_pkr as string → float; liters as string → float;
#                    odometer as string → int
# ===================================================================
class TestTypeCoercion:

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_string_amount_coerced_to_float(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        ai_json: dict[str, Any] = {
            "record_type": "fuel",
            "date": "2026-08-15",
            "amount_pkr": "1500",
            "liters": "35.5",
            "odometer_km": "45000",
            "description": "Fill-up",
            "vendor_name": "PSO",
            "confidence": "high",
            "warnings": [],
            "line_items": [],
            "category": None,
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("ai_client.get_client", return_value=mock_client):
            result = receipt_scanner.parse_receipt_text("PSO receipt")

        assert isinstance(result.get("amount_pkr"), float)
        assert result["amount_pkr"] == 1500.0
        assert isinstance(result.get("liters"), float)
        assert result["liters"] == 35.5
        assert isinstance(result.get("odometer_km"), int)
        assert result["odometer_km"] == 45000


# ===================================================================
# TestMissingFields — AI returns partial JSON → missing fields filled with None
# ===================================================================
class TestMissingFields:

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_missing_fields_default_none(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        # Only provide record_type and confidence — everything else missing
        ai_json: dict[str, Any] = {
            "record_type": "fuel",
            "confidence": "medium",
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("ai_client.get_client", return_value=mock_client):
            result = receipt_scanner.parse_receipt_text("Minimal receipt text")

        assert result.get("record_type") == "fuel"
        assert result.get("date") is None
        assert result.get("amount_pkr") is None
        assert result.get("liters") is None
        assert result.get("odometer_km") is None
        assert result.get("description") is None
        assert result.get("vendor_name") is None
        assert result.get("line_items") == []
        assert result.get("category") is None


# ===================================================================
# TestLineItems — AI returns line_items array → correctly processed
# ===================================================================
class TestLineItems:

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_line_items_processed(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        ai_json: dict[str, Any] = {
            "record_type": "maintenance",
            "date": "2026-08-15",
            "amount_pkr": 12000,
            "confidence": "high",
            "warnings": [],
            "line_items": [
                {"description": "Engine oil", "quantity": "2", "unit_price": "3500", "total": "7000"},
                {"description": "Oil filter", "quantity": "1", "unit_price": "500", "total": "500"},
            ],
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("ai_client.get_client", return_value=mock_client):
            result = receipt_scanner.parse_receipt_text("AutoCare garage receipt")

        items = result.get("line_items")
        assert isinstance(items, list)
        assert len(items) == 2
        assert items[0]["description"] == "Engine oil"
        assert items[0]["quantity"] == 2  # coerced to int
        assert items[0]["unit_price"] == 3500.0
        assert items[0]["total"] == 7000.0
        assert items[1]["quantity"] == 1


# ===================================================================
# TestCategory — AI returns category field → preserved as string
# ===================================================================
class TestCategory:

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_category_preserved(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        ai_json: dict[str, Any] = {
            "record_type": "maintenance",
            "date": "2026-08-15",
            "amount_pkr": 7000,
            "confidence": "high",
            "warnings": [],
            "line_items": [],
            "category": "engine_oil",
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("ai_client.get_client", return_value=mock_client):
            result = receipt_scanner.parse_receipt_text("Oil change receipt")

        assert result.get("category") == "engine_oil"

    @patch("receipt_scanner._config_available", True)
    @patch("receipt_scanner._config")
    def test_category_null_when_absent(self, mock_config: MagicMock) -> None:
        mock_config.QWEN_PLUS_CHARACTER = "qwen-plus-character"
        mock_config.QWEN_API_MODE = "openai"

        ai_json: dict[str, Any] = {
            "record_type": "fuel",
            "confidence": "high",
        }

        mock_client = _mock_ai_response(ai_json)
        with patch("ai_client.get_client", return_value=mock_client):
            result = receipt_scanner.parse_receipt_text("Simple fuel receipt")

        assert result.get("category") is None


# ===================================================================
# TestEmptyOCRText — Empty input → returns error dict
# ===================================================================
class TestEmptyOCRText:

    def test_extract_json_from_empty_string(self) -> None:
        """_extract_json_object returns None for an empty string."""
        result = receipt_scanner._extract_json_object("")
        assert result is None

    def test_extract_json_from_whitespace(self) -> None:
        """_extract_json_object returns None for whitespace-only input."""
        result = receipt_scanner._extract_json_object("   \n\t  ")
        assert result is None
