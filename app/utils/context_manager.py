"""
Context manager — trims chat history to fit HF 8 k token limits.

Strategy:
1. Always keep messages[0] if it is the system prompt.
2. Walk backwards from the newest message, accumulating
   estimated token cost, and stop when the budget runs out.
3. Return [system] + [kept tail].
"""

from __future__ import annotations

import json
from typing import Any


def _estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token for English text."""
    return max(1, len(text) // 4)


def trim_messages(
    messages: list[dict[str, Any]],
    max_input_tokens: int,
) -> list[dict[str, Any]]:
    """
    Keep the system prompt + as many recent messages as fit inside
    *max_input_tokens*.
    """
    if not messages:
        return messages

    system: list[dict] = []
    rest: list[dict] = list(messages)

    # Preserve system prompt
    if rest[0].get("role") == "system":
        system = [rest.pop(0)]
        max_input_tokens -= _estimate_tokens(
            system[0].get("content") or ""
        )

    kept: list[dict] = []
    budget = max_input_tokens

    for msg in reversed(rest):
        content = ""
        if isinstance(msg, dict):
            content = msg.get("content") or ""
            if "tool_calls" in msg:
                content += json.dumps(msg["tool_calls"])
        elif hasattr(msg, "content"):
            content = msg.content or ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                content += json.dumps(
                    [
                        tc.model_dump() if hasattr(tc, "model_dump") else str(tc)
                        for tc in msg.tool_calls
                    ]
                )

        cost = _estimate_tokens(content)
        if cost > budget:
            break
        budget -= cost
        kept.append(msg)

    kept.reverse()

    # At minimum keep the very last message
    if not kept and rest:
        kept = [rest[-1]]

    return system + kept
