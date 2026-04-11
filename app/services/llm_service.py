"""
LLM service — tool-calling loop & streaming.

Uses the standard OpenAI client (works with OpenRouter, HF, Groq, etc.)

Exposes:
    - ``chat_with_tools()``  — agentic tool loop  (Route 1)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.tools.schemas import TOOLS
from app.tools.registry import execute_tool
from app.utils.context_manager import trim_messages
from app.utils.retries import llm_retry, serialize_message

logger = logging.getLogger("wasla.llm")
_settings = get_settings()

_client = AsyncOpenAI(
    base_url=_settings.llm_base_url,
    api_key=_settings.llm_api_key,
)


# ─────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────

@llm_retry
async def _call_llm(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    use_fallback: bool = False,
):
    model = (
        _settings.fallback_chat_model if use_fallback
        else _settings.main_chat_model
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
    return await _client.chat.completions.create(**kwargs)



# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────

async def chat_with_tools(
    messages: list[dict[str, Any]],
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the agentic tool-calling loop.

    Parameters
    ----------
    messages : Chat messages (system + history + user).
    ctx      : Context dict passed to every tool (e.g. bearer_token).

    Returns
    -------
    ``{"response": str, "tool_calls_made": int, "model_used": str}``
    """
    if ctx is None:
        ctx = {}
    settings = _settings
    input_budget = settings.max_context_tokens - settings.max_chat_tokens
    messages = trim_messages(messages, max_input_tokens=input_budget)

    tool_calls_total = 0
    use_fallback = False

    for iteration in range(settings.max_tool_iterations):
        try:
            response = await _call_llm(
                messages,
                tools=TOOLS,
                max_tokens=settings.max_chat_tokens,
                use_fallback=use_fallback,
            )
        except Exception as exc:
            if not use_fallback:
                logger.warning("Primary model failed (%s) — switching to fallback", exc)
                use_fallback = True
                response = await _call_llm(
                    messages,
                    tools=TOOLS,
                    max_tokens=settings.max_chat_tokens,
                    use_fallback=True,
                )
            else:
                raise

        ai_message = response.choices[0].message
        messages.append(serialize_message(ai_message))

        if not ai_message.tool_calls:
            model = (
                settings.fallback_chat_model if use_fallback
                else settings.main_chat_model
            )
            return {
                "response": ai_message.content or "",
                "tool_calls_made": tool_calls_total,
                "model_used": model,
            }

        for tc in ai_message.tool_calls:
            tool_calls_total += 1
            logger.info(
                "Iter %d — tool %s(%s)", iteration + 1,
                tc.function.name, tc.function.arguments,
            )
            result_json = await execute_tool(
                tc.function.name, tc.function.arguments, ctx,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": result_json,
            })

        messages = trim_messages(messages, max_input_tokens=input_budget)

    messages.append({
        "role": "user",
        "content": (
            "Tool iteration limit reached. Please summarise all "
            "the data you have collected so far and provide a "
            "complete answer."
        ),
    })
    messages = trim_messages(messages, max_input_tokens=input_budget)

    final = await _call_llm(
        messages,
        max_tokens=settings.max_chat_tokens,
        use_fallback=use_fallback,
    )
    model = (
        settings.fallback_chat_model if use_fallback
        else settings.main_chat_model
    )
    return {
        "response": final.choices[0].message.content or "",
        "tool_calls_made": tool_calls_total,
        "model_used": model,
    }



