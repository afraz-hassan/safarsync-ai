"""
receipt_scanner.py — Two-stage cloud-based receipt scanning pipeline for SafarSync AI.

Stage 1: extract_text_from_image()  → OCR.space  (image → raw text)
Stage 2: parse_receipt_text()       → Qwen text model (raw text → structured JSON)

No local OCR (pytesseract) and no AI vision models are used.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

import requests
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Import project config.  config.py validates secrets at import time and
# raises RuntimeError when a required key is missing; we capture that so
# individual functions can return a friendly error instead of crashing.
# ---------------------------------------------------------------------------
try:
    import config as _config

    _config_available = True
    _config_error: str | None = None
except RuntimeError as _exc:
    _config_available = False
    _config_error = str(_exc)
    _config = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Maximum pixel length on the longest side before we down-scale.
_MAX_LONG_SIDE = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ocr_api_key() -> str | None:
    """Return the OCR.space API key, or None when unavailable."""
    if not _config_available:
        return None
    key = _config.get_secret("OCR_SPACE_API_KEY")
    return key if key else None


def _resize_if_needed(img: Image.Image) -> tuple[Image.Image, bool]:
    """
    Resize *img* so the longest side is at most ``_MAX_LONG_SIDE`` pixels.

    Returns ``(image, was_resized)``.
    """
    width, height = img.size
    longest = max(width, height)
    if longest <= _MAX_LONG_SIDE:
        return img, False

    ratio = _MAX_LONG_SIDE / longest
    new_size = (int(width * ratio), int(height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    return img, True


# ---------------------------------------------------------------------------
# Stage 1 — OCR.space  (image → raw text)
# ---------------------------------------------------------------------------

def extract_text_from_image(image_path: str) -> dict:
    """
    Extract text from a receipt image using the OCR.space cloud API.

    Pipeline:
        1. Validate file exists.
        2. Open image with Pillow.
        3. Correct orientation via EXIF when possible.
        4. Resize oversized images (max 2000 px on longest side).
        5. POST image bytes to OCR.space.
        6. Extract text from ParsedResults[0].ParsedText.
        7. Return structured result or error.

    Parameters
    ----------
    image_path : str
        Path to the receipt image file.

    Returns
    -------
    dict
        {
            "raw_text":   str,    # extracted text (empty on error)
            "warnings":   list,   # human-readable warnings
            "ocr_engine": "ocr_space"
        }
        On error an additional "error" key is present.
    """
    warnings: list[str] = []

    # -- 1. Validate file exists --
    path = Path(image_path)
    if not path.is_file():
        return {
            "raw_text": "",
            "warnings": [],
            "ocr_engine": "ocr_space",
            "error": f"File not found: {image_path}",
        }

    # -- Check API key before doing expensive work --
    api_key = _get_ocr_api_key()
    if not api_key:
        return {
            "raw_text": "",
            "warnings": [],
            "ocr_engine": "ocr_space",
            "error": (
                "OCR_SPACE_API_KEY is not configured. "
                "Add it to your .env file or Streamlit secrets."
            ),
        }

    # -- 2. Open image --
    try:
        img = Image.open(path)
    except Exception as exc:
        return {
            "raw_text": "",
            "warnings": [],
            "ocr_engine": "ocr_space",
            "error": f"Unable to open image: {exc}",
        }

    # -- 3. Correct orientation via EXIF --
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        warnings.append("Could not apply EXIF orientation correction.")

    # -- 4. Resize oversized images --
    img, resized = _resize_if_needed(img)
    if resized:
        warnings.append(
            f"Image resized to {img.size[0]}×{img.size[1]} "
            f"(original exceeded {_MAX_LONG_SIDE}px on longest side)."
        )

    # -- 5. Prepare image bytes and call OCR.space --
    try:
        import io

        buffer = io.BytesIO()
        fmt = img.format or "PNG"
        img.save(buffer, format=fmt)
        image_bytes = buffer.getvalue()

        response = requests.post(
            "https://api.ocr.space/parse/image",
            headers={"apikey": api_key},
            files={"file": (path.name, image_bytes)},
            data={
                "language": "eng",
                "isOverlayRequired": "false",
                "detectOrientation": "true",
                "scale": "true",
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

    except requests.exceptions.RequestException as exc:
        return {
            "raw_text": "",
            "warnings": warnings,
            "ocr_engine": "ocr_space",
            "error": f"OCR.space API request failed: {exc}",
        }
    except (ValueError, KeyError) as exc:
        return {
            "raw_text": "",
            "warnings": warnings,
            "ocr_engine": "ocr_space",
            "error": f"Unexpected OCR.space response: {exc}",
        }

    # -- 6. Extract text from ParsedResults --
    parsed_results = result.get("ParsedResults")
    if not parsed_results:
        # Check for API-level error messages.
        error_messages = result.get("ErrorMessage") or result.get("ErrorDetails")
        detail = error_messages or "No parsed results returned."
        return {
            "raw_text": "",
            "warnings": warnings,
            "ocr_engine": "ocr_space",
            "error": f"OCR.space returned no text. {detail}",
        }

    raw_text: str = parsed_results[0].get("ParsedText", "")

    # -- 7. Empty-text guard --
    if not raw_text.strip():
        return {
            "raw_text": "",
            "warnings": warnings,
            "ocr_engine": "ocr_space",
            "error": "OCR.space returned empty text.",
        }

    return {
        "raw_text": raw_text,
        "warnings": warnings,
        "ocr_engine": "ocr_space",
    }


# ---------------------------------------------------------------------------
# Stage 2 — Qwen text interpretation  (raw text → structured JSON)
# ---------------------------------------------------------------------------

_SYSTEM_INSTRUCTION = """\
You are SafarSync AI's receipt-data extraction assistant.
Use ONLY the supplied OCR text.
Never invent information.
Return ONLY valid JSON.

Schema:
{
  "record_type": "fuel | maintenance | insurance | unknown",
  "date": "YYYY-MM-DD or null",
  "amount_pkr": number or null,
  "liters": number or null,
  "odometer_km": integer or null,
  "description": "string or null",
  "vendor_name": "string or null",
  "confidence": "high | medium | low",
  "warnings": []
}

Rules:
- Missing information must be null.
- Uncertain information must have low confidence.
- Do not guess hidden numbers.
- Normalize obvious dates.
- Normalize currency into numeric PKR.
- Keep warnings short."""


def _extract_json_object(text: str) -> dict | None:
    """
    Attempt to pull a JSON object out of *text*, tolerating surrounding prose.

    Strategy:
        1. Try ``json.loads`` directly.
        2. Find the first ``{`` … last ``}`` substring and parse that.
    """
    # Direct parse.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: locate outermost braces.
    match = re.search(r"\{.*}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def parse_receipt_text(raw_text: str) -> dict:
    """
    Interpret OCR text with Qwen (qwen-plus-character) and return structured
    receipt data.

    Parameters
    ----------
    raw_text : str
        Raw OCR text extracted from a receipt image.

    Returns
    -------
    dict
        Parsed receipt fields (see schema in ``_SYSTEM_INSTRUCTION``),
        plus ``raw_response`` and ``warnings``.  On error an ``error``
        key is included.
    """
    warnings: list[str] = []

    # -- Guard: config / secrets unavailable --
    if not _config_available:
        return {
            "error": _config_error or "Configuration unavailable.",
            "raw_response": "",
            "warnings": warnings,
        }

    # -- Call Qwen via the centralised ai_client --
    prompt = f"{_SYSTEM_INSTRUCTION}\n\nOCR text:\n{raw_text}"

    try:
        from ai_client import ask_text

        raw_response: str = ask_text(
            prompt,
            model=_config.QWEN_PLUS_CHARACTER,
            max_tokens=500,
        )
    except PermissionError as exc:
        return {
            "error": f"Qwen authentication failed: {exc}",
            "raw_response": "",
            "warnings": warnings,
        }
    except ConnectionError as exc:
        return {
            "error": f"Qwen API unavailable: {exc}",
            "raw_response": "",
            "warnings": warnings,
        }
    except TimeoutError as exc:
        return {
            "error": f"Qwen API timed out: {exc}",
            "raw_response": "",
            "warnings": warnings,
        }
    except RuntimeError as exc:
        return {
            "error": f"Qwen API error: {exc}",
            "raw_response": "",
            "warnings": warnings,
        }
    except Exception as exc:
        return {
            "error": f"Unexpected error calling Qwen: {exc}",
            "raw_response": "",
            "warnings": warnings,
        }

    # -- Parse JSON from the model response --
    parsed = _extract_json_object(raw_response)

    if parsed is None:
        return {
            "error": "Model returned malformed JSON.",
            "raw_response": raw_response,
            "warnings": ["Could not parse JSON from model response."],
        }

    # Ensure every expected key exists (fill missing with null).
    for key in (
        "record_type",
        "date",
        "amount_pkr",
        "liters",
        "odometer_km",
        "description",
        "vendor_name",
        "confidence",
        "warnings",
    ):
        parsed.setdefault(key, None)

    parsed["raw_response"] = raw_response
    return parsed


# ---------------------------------------------------------------------------
# CLI entry-point — python receipt_scanner.py image.jpg
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python receipt_scanner.py <image_path>")
        sys.exit(1)

    image_file = sys.argv[1]

    # -- Stage 1: OCR --
    print("=" * 60)
    print("Stage 1: Extracting text from image via OCR.space …")
    print("=" * 60)
    ocr_result = extract_text_from_image(image_file)

    if "error" in ocr_result:
        print(f"ERROR: {ocr_result['error']}")
        sys.exit(1)

    raw_text = ocr_result["raw_text"]
    print(f"Warnings: {ocr_result['warnings']}")
    print(f"\n--- OCR Text ---\n{raw_text}\n")

    # -- Stage 2: Interpretation --
    print("=" * 60)
    print("Stage 2: Parsing receipt text with Qwen …")
    print("=" * 60)
    parsed = parse_receipt_text(raw_text)

    if "error" in parsed:
        print(f"ERROR: {parsed['error']}")
        if parsed.get("raw_response"):
            print(f"Raw response:\n{parsed['raw_response']}")
        sys.exit(1)

    print(f"\n--- Parsed Receipt JSON ---")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
