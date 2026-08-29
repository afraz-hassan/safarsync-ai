"""
test_ocr_space.py — Temporary test script for OCR.space API.

Usage:
    python test_ocr_space.py path/to/receipt.jpg

This script is standalone and self-contained.
Delete this file once testing is complete.
"""

import io
import os
import sys

import requests
from dotenv import load_dotenv
from PIL import Image

# ---------------------------------------------------------------------------
# 1. Load environment variables from .env
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# 2. Validate API key
# ---------------------------------------------------------------------------
api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()

if not api_key:
    print("ERROR: OCR_SPACE_API_KEY is not set in .env — cannot proceed.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 3. Read and validate image path from sys.argv
# ---------------------------------------------------------------------------
if len(sys.argv) < 2:
    print("Usage: python test_ocr_space.py <image_path>")
    sys.exit(1)

image_path = sys.argv[1]

if not os.path.isfile(image_path):
    print(f"ERROR: Image file not found: {image_path}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 4. Open image with Pillow, resize if larger than 2000px on any side
# ---------------------------------------------------------------------------
MAX_DIMENSION = 2000

try:
    img = Image.open(image_path)
except Exception as exc:
    print(f"ERROR: Could not open image ({type(exc).__name__}).")
    sys.exit(1)

original_size = img.size
resized = False

if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
    # Maintain aspect ratio — scale so the longest side is MAX_DIMENSION.
    ratio = min(MAX_DIMENSION / img.width, MAX_DIMENSION / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    resized = True

# Convert to RGB if needed (OCR.space expects standard formats).
if img.mode not in ("RGB", "L"):
    img = img.convert("RGB")

# Encode to JPEG bytes for the upload.
buffer = io.BytesIO()
img.save(buffer, format="JPEG", quality=85)
buffer.seek(0)
image_bytes = buffer.getvalue()

print(f"Image   : {image_path}")
print(f"Size    : {original_size[0]}x{original_size[1]}"
      + (f" → {img.size[0]}x{img.size[1]} (resized)" if resized else ""))
print(f"Upload  : {len(image_bytes):,} bytes (JPEG)")
print("-" * 60)

# ---------------------------------------------------------------------------
# 5. Send image to OCR.space API
# ---------------------------------------------------------------------------
OCR_URL = "https://api.ocr.space/parse/image"

headers = {
    "apikey": api_key,
}

params = {
    "language": "eng",
    "isOverlayRequired": "false",
}

try:
    response = requests.post(
        OCR_URL,
        headers=headers,
        data=params,
        files={"file": ("receipt.jpg", image_bytes, "image/jpeg")},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

except requests.exceptions.HTTPError as exc:
    status = exc.response.status_code if exc.response is not None else "?"
    print(f"ERROR: HTTP {status} from OCR.space.")
    # Do NOT print the response body — it may echo the API key.
    sys.exit(1)

except requests.exceptions.ConnectionError:
    print("ERROR: Could not reach OCR.space. Check your internet connection.")
    sys.exit(1)

except requests.exceptions.Timeout:
    print("ERROR: Request timed out (30 s). OCR.space may be busy — retry.")
    sys.exit(1)

except Exception as exc:
    print(f"ERROR: Unexpected failure ({type(exc).__name__}).")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 6. Parse and print extracted text
# ---------------------------------------------------------------------------

# Check for API-level errors (OCR.space returns 200 even on some errors).
if result.get("IsErroredOnProcessing", False):
    error_messages = result.get("ErrorMessage", ["Unknown error"])
    print(f"ERROR: OCR.space returned an error: {error_messages[0]}")
    sys.exit(1)

parsed_results = result.get("ParsedResults")

if not parsed_results:
    print("ERROR: OCR.space returned no results (empty ParsedResults).")
    sys.exit(1)

parsed_text = parsed_results[0].get("ParsedText", "").strip()

if not parsed_text:
    print("ERROR: OCR.space returned empty text — no text detected in image.")
    sys.exit(1)

print("\nExtracted text:\n")
print(parsed_text)

# Print processing metadata if available.
processing_time = result.get("ProcessingTimeInMilliseconds")
if processing_time:
    print("-" * 60)
    print(f"Processing time: {processing_time} ms")
