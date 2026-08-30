"""
ai_client.py — Reusable OpenAI-compatible client for Alibaba Cloud Model Studio.

This module exposes two public helpers:

    get_client()   → returns a configured ``openai.OpenAI`` instance (cached).
    ask_text(...)  → sends a single text prompt and returns the assistant reply.

Both functions read their credentials from ``config.get_secret()``, so they
work identically on Streamlit Community Cloud and in local development.

Usage example::

    from ai_client import ask_text
    from config import QWEN_FLASH_CHARACTER

    reply = ask_text("Summarise today's expenses.", model=QWEN_FLASH_CHARACTER)
"""

from __future__ import annotations

import logging
from functools import lru_cache

from openai import OpenAI, AuthenticationError, APIConnectionError, APITimeoutError, APIStatusError

import config

# ---------------------------------------------------------------------------
# Module-level logger — never attach the API key to a log record.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public: client factory (cached so we reuse one HTTP connection pool).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """
    Return a singleton ``openai.OpenAI`` client configured for DashScope.

    The client is created once and reused across calls thanks to
    ``@lru_cache``.  Credentials are fetched via ``config.get_secret()``
    at creation time.

    Raises
    ------
    RuntimeError
        If the API key or base URL is missing (propagated from config).
    """
    api_key: str = config.get_secret("DASHSCOPE_API_KEY")
    base_url: str = config.get_secret("DASHSCOPE_BASE_URL")

    logger.debug(
        "Creating OpenAI client for base_url=%s (key length=%d)",
        base_url,
        len(api_key),  # log length only — NEVER log the key itself
    )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=30.0,  # seconds — covers both connect and read
    )


# ---------------------------------------------------------------------------
# Public: simple text completion helper.
# ---------------------------------------------------------------------------
def ask_text(
    prompt: str,
    model: str = config.QWEN_PLUS_CHARACTER,
    max_tokens: int = 500,
    system_message: str | None = None,
) -> str:
    """
    Send a single text prompt to Alibaba Cloud Model Studio and return the
    assistant's reply as a plain string.

    Parameters
    ----------
    prompt : str
        The user message to send.
    model : str, optional
        Model identifier (default: ``config.QWEN_PLUS_CHARACTER``).
    max_tokens : int, optional
        Maximum number of tokens in the response (default: 500).
    system_message : str | None, optional
        Optional system instruction sent as a separate system-role message.
        When provided, the model receives ``[{system}, {user}]`` instead of
        a single user message.

    Returns
    -------
    str
        The assistant's text reply.  Returns an empty string if the model
        returns no content.

    Raises
    ------
    PermissionError
        If the API key is invalid or expired (HTTP 401 / 403).
    ConnectionError
        If the endpoint is unreachable (DNS failure, refused connection, etc.).
    TimeoutError
        If the request exceeds the configured timeout (30 s).
    RuntimeError
        For any other API-level error (rate-limit, server error, etc.).
    """
    client: OpenAI = get_client()

    logger.info("AI request: model=%s, tokens=%d", model, max_tokens)

    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )

        # Safely extract the assistant text.
        text: str | None = response.choices[0].message.content
        return text if text is not None else ""

    # ---- Authentication errors (bad / missing key) ----
    except AuthenticationError as exc:
        logger.error("DashScope authentication failed — check your API key.")
        raise PermissionError(
            "Authentication with DashScope failed. "
            "Please verify that DASHSCOPE_API_KEY is correct."
        ) from exc

    # ---- Network-level errors (DNS, refused connection, etc.) ----
    except APIConnectionError as exc:
        logger.error("Could not reach the DashScope endpoint: %s", exc)
        raise ConnectionError(
            "Unable to reach the DashScope API. "
            "Please check your internet connection and DASHSCOPE_BASE_URL."
        ) from exc

    # ---- Timeout errors ----
    except APITimeoutError as exc:
        logger.error("DashScope request timed out: %s", exc)
        raise TimeoutError(
            "The request to DashScope timed out (30 s limit). "
            "Please try again or reduce the prompt size."
        ) from exc

    # ---- Any other API error (rate-limit, 5xx, malformed request, …) ----
    except APIStatusError as exc:
        logger.error(
            "DashScope API error — status=%s, type=%s",
            exc.status_code,
            type(exc).__name__,
        )
        raise RuntimeError(
            f"DashScope returned an error (HTTP {exc.status_code}). "
            "Please try again later or check the DashScope dashboard."
        ) from exc


# ---------------------------------------------------------------------------
# Quick smoke test — run:  python ai_client.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("--- SafarSync AI: ai_client smoke test ---")
    print(f"Model   : {config.QWEN_PLUS_CHARACTER}")
    print(f"Base URL: {config.get_secret('DASHSCOPE_BASE_URL')}")
    print()

    try:
        reply = ask_text("Say hello in one short sentence.")
        print(f"Reply: {reply}")
    except (PermissionError, ConnectionError, TimeoutError, RuntimeError) as err:
        print(f"ERROR: {err}")
