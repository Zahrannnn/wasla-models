"""
Tenacity retry configuration for LLM API calls.

Apply ``@llm_retry`` to any async function that calls the LLM API.
Retries on rate-limit (429) and transient server errors (5xx)
up to 5 times with exponential delays (2 s -> 60 s).
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
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

logger = logging.getLogger("wasla.retries")


llm_retry = retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    before_sleep=lambda rs: logger.warning(
        "LLM rate-limited — retrying in %.1f s (attempt %d)",
        rs.next_action.sleep,  # type: ignore[union-attr]
        rs.attempt_number,
    ),
    reraise=True,
)

# Backward compat alias
hf_retry = llm_retry


def serialize_message(msg: Any) -> dict[str, Any]:
    """
    Convert an LLM response message object (or plain dict) into
    a JSON-safe dict for the messages list.
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
