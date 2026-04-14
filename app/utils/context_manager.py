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


def _is_system_message(msg: Any) -> bool:
    if isinstance(msg, dict):
        return msg.get("role") == "system"
    return getattr(msg, "type", None) == "system"


def _estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token for English text."""
    return max(1, len(text) // 4)


def _content_for_token_estimate(content: Any) -> str:
    """Flatten message content (str, multimodal block list, etc.) for token heuristics."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                parts.append(text if isinstance(text, str) else json.dumps(block, ensure_ascii=False))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def trim_messages(
    messages: list[Any],
    max_input_tokens: int,
) -> list[Any]:
    """
    Keep the system prompt + as many recent messages as fit inside
    *max_input_tokens*.
    """
    if not messages:
        return messages

    system: list[Any] = []
    rest: list[Any] = list(messages)

    # Preserve system prompt (dict or LangChain SystemMessage)
    if rest and _is_system_message(rest[0]):
        system = [rest.pop(0)]
        first = system[0]
        if isinstance(first, dict):
            max_input_tokens -= _estimate_tokens(_content_for_token_estimate(first.get("content")))
        else:
            max_input_tokens -= _estimate_tokens(_content_for_token_estimate(getattr(first, "content", "")))

    kept: list[Any] = []
    budget = max_input_tokens

    for msg in reversed(rest):
        content = ""
        if isinstance(msg, dict):
            content = _content_for_token_estimate(msg.get("content"))
            if "tool_calls" in msg:
                content += json.dumps(msg["tool_calls"])
        elif hasattr(msg, "content"):
            content = _content_for_token_estimate(msg.content)
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
