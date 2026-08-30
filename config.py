"""
config.py — Central configuration for the SafarSync AI project.

This file is the single source of truth for all secrets and model names.
It works in two environments:
  • Streamlit Community Cloud  → secrets come from st.secrets
  • Local development          → secrets come from the .env file (via python-dotenv)

Usage in other modules:
    from config import DASHSCOPE_API_KEY, QWEN_PLUS_CHARACTER
"""

from __future__ import annotations

import os
import logging

# ---------------------------------------------------------------------------
# Step 1: Load the .env file (only used during local development).
#         On Streamlit Community Cloud the file simply won't exist,
#         so override=False keeps any real env-vars untouched.
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# Step 2: Set up a lightweight logger so we can surface config problems
#         without printing secrets to stdout.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 3: Helper that reads a secret from whichever source has it.
# ---------------------------------------------------------------------------
def get_secret(key: str) -> str:
    """
    Retrieve a secret value by name.

    Resolution order:
        1. Streamlit's st.secrets  (Community Cloud injects secrets here)
        2. Environment variables   (loaded from .env or set by the OS)
        3. Empty string            (safe fallback — callers decide what to do)

    The function NEVER logs or prints the value of a secret.
    """
    # --- Try Streamlit secrets first ---
    try:
        import streamlit as st  # local import so non-Streamlit contexts still work

        value: str | None = st.secrets.get(key)  # type: ignore[attr-defined]
        if value:
            return str(value)
    except Exception:
        # Streamlit is not available or secrets are not configured — that's fine.
        pass

    # --- Fall back to environment variables (.env / OS) ---
    value = os.getenv(key)
    if value is not None:
        return value

    # --- Not found anywhere — return empty string ---
    logger.warning("Secret '%s' was not found in st.secrets or environment variables.", key)
    return ""


# ---------------------------------------------------------------------------
# Step 4: Read the secrets we need.
#         Variable names match the .env / st.secrets keys exactly.
# ---------------------------------------------------------------------------

# API key used to authenticate with Alibaba Cloud's DashScope service.
DASHSCOPE_API_KEY: str = get_secret("DASHSCOPE_API_KEY")

# Base URL for the OpenAI-compatible DashScope endpoint.
DASHSCOPE_BASE_URL: str = get_secret("DASHSCOPE_BASE_URL")

# API key for the OCR.space receipt-scanning service.
# Optional — only required when OCR_ENGINE is set to "ocr_space".
OCR_SPACE_API_KEY: str = get_secret("OCR_SPACE_API_KEY")


# ---------------------------------------------------------------------------
# Step 5: Validate critical secrets and raise a clear error when missing.
# ---------------------------------------------------------------------------
def _require_secret(name: str, value: str) -> str:
    """
    Raise a descriptive RuntimeError if a required secret is empty.

    The message tells the developer exactly where to put the key,
    without ever echoing the key itself.
    """
    if not value:
        raise RuntimeError(
            f"[config] Required secret '{name}' is missing.\n"
            f"  • Local dev  → add  {name}=YOUR_VALUE  to your .env file\n"
            f"  • Cloud      → add  {name}  to Streamlit Community Cloud secrets"
        )
    return value


# Validate immediately so errors surface at import time, not deep in a request.
DASHSCOPE_API_KEY = _require_secret("DASHSCOPE_API_KEY", DASHSCOPE_API_KEY)
DASHSCOPE_BASE_URL = _require_secret("DASHSCOPE_BASE_URL", DASHSCOPE_BASE_URL)
# OCR_SPACE_API_KEY is optional — validated at usage time in receipt_scanner.py.


# ---------------------------------------------------------------------------
# Step 6: Model name constants.
#         Using constants (instead of raw strings) prevents typos and makes
#         it easy to swap models in one place.
# ---------------------------------------------------------------------------

# Higher-quality, slightly slower model — good for detailed analysis.
QWEN_PLUS_CHARACTER: str = "qwen-plus-character"

# Faster, cheaper model — good for quick / lightweight tasks.
QWEN_FLASH_CHARACTER: str = "qwen-flash-character"

# ---------------------------------------------------------------------------
# Step 7: OCR engine and vision model configuration.
# ---------------------------------------------------------------------------

# Which OCR engine to use for receipt text extraction.
#   "ocr_space" → OCR.space cloud API  (requires OCR_SPACE_API_KEY)
#   "qwen_vl"   → Qwen-VL via DashScope multimodal endpoint
OCR_ENGINE: str = os.getenv("OCR_ENGINE", "ocr_space").strip().lower()

# Qwen vision-language model used when OCR_ENGINE is "qwen_vl".
QWEN_VL_MODEL: str = "qwen-vl-plus"

# API protocol style for Qwen text calls.
#   "openai" → use OpenAI-compatible system/user message separation (default)
# Any other value falls back to a single combined user prompt.
QWEN_API_MODE: str = os.getenv("QWEN_API_MODE", "openai").strip().lower()
