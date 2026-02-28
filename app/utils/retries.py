"""
Tenacity retry configuration for Hugging Face free-tier 429 errors.

Apply ``@hf_retry`` to any async function that calls the HF
Inference API.  It will automatically back off on 429 errors and
retry up to 5 times with exponential delays (2 s → 60 s).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from huggingface_hub.errors import HfHubHTTPError

logger = logging.getLogger("wasla.retries")


# ── Retry decorator ──────────────────────────────────────────────
hf_retry = retry(
    retry=retry_if_exception_type(HfHubHTTPError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    before_sleep=lambda rs: logger.warning(
        "HF rate-limited — retrying in %.1f s (attempt %d)",
        rs.next_action.sleep,  # type: ignore[union-attr]
        rs.attempt_number,
    ),
    reraise=True,
)


# ── Message serialisation helper ─────────────────────────────────
def serialize_message(msg: Any) -> dict[str, Any]:
    """
    Convert a ``ChatCompletionOutputMessage`` (or plain dict) into
    a JSON-safe dict that can be appended back to the messages list.
    """
    if isinstance(msg, dict):
        return msg

    result: dict[str, Any] = {"role": msg.role}

    if msg.content:
        result["content"] = msg.content

    if hasattr(msg, "tool_calls") and msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": (
                        tc.function.arguments
                        if isinstance(tc.function.arguments, str)
                        else json.dumps(tc.function.arguments)
                    ),
                },
            }
            for tc in msg.tool_calls
        ]

    return result
