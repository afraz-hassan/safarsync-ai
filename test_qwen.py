"""
test_qwen.py — Temporary smoke test for Alibaba Cloud Model Studio.

Tests the qwen-plus-character model via the DashScope OpenAI-compatible
endpoint.  Reads credentials from .env and prints only the assistant reply.
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, AuthenticationError, OpenAIError

# ---------------------------------------------------------------------------
# 1. Load environment variables from .env
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# 2-3. Read credentials
# ---------------------------------------------------------------------------
api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip()

if not api_key:
    print("ERROR: DASHSCOPE_API_KEY is not set. Add it to your .env file.")
    sys.exit(1)

if not base_url:
    print("ERROR: DASHSCOPE_BASE_URL is not set. Add it to your .env file.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 4. Create OpenAI-compatible client
# ---------------------------------------------------------------------------
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=30,
)

# ---------------------------------------------------------------------------
# 5-7. Send the test prompt and print the response
# ---------------------------------------------------------------------------
try:
    response = client.chat.completions.create(
        model="qwen-flash-character",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are SafarSync AI. Reply with: "
                    "SafarSync API test successful."
                ),
            },
        ],
    )
    print(response.choices[0].message.content.strip())

# ---------------------------------------------------------------------------
# 9. Error handling
# ---------------------------------------------------------------------------
except AuthenticationError:
    print("ERROR: Authentication failed. Check your DASHSCOPE_API_KEY.")
    sys.exit(1)
except APIConnectionError:
    print("ERROR: Could not reach the AI service. Check your internet connection.")
    sys.exit(1)
except OpenAIError as exc:
    print(f"ERROR: API error — {type(exc).__name__}")
    sys.exit(1)
except Exception as exc:
    print(f"ERROR: Unexpected failure — {type(exc).__name__}")
    sys.exit(1)
