"""
LLM service — Hugging Face Inference API logic & tool-calling loop.

Houses the two HF ``AsyncInferenceClient`` singletons (main + fallback)
and exposes:
    • ``chat_with_tools()``  — 3-iteration agentic tool loop  (Route 1)
    • ``stream_chat()``      — token-by-token SSE generator   (Route 2)
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from huggingface_hub import AsyncInferenceClient

from app.core.config import get_settings
from app.tools.schemas import TOOLS
from app.tools.registry import execute_tool
from app.utils.context_manager import trim_messages
from app.utils.retries import hf_retry, serialize_message

logger = logging.getLogger("wasla.llm")
_settings = get_settings()

# ── Client singletons ────────────────────────────────────────────
_main_client = AsyncInferenceClient(
    model=_settings.main_chat_model,
    token=_settings.huggingface_token,
)

_fallback_client = AsyncInferenceClient(
    model=_settings.fallback_chat_model,
    token=_settings.huggingface_token,
)

_voice_client = AsyncInferenceClient(
    model=_settings.voice_stream_model,
    token=_settings.huggingface_token,
)


# ─────────────────────────────────────────────────────────────────
#  Internal helpers (retry-wrapped)
# ─────────────────────────────────────────────────────────────────

@hf_retry
async def _call_hf(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    use_fallback: bool = False,
):
    client = _fallback_client if use_fallback else _main_client
    kwargs: dict[str, Any] = {"messages": messages, "max_tokens": max_tokens}
    if tools:
        kwargs["tools"] = tools
    return await client.chat_completion(**kwargs)


@hf_retry
async def _call_hf_stream(
    messages: list[dict[str, Any]],
    max_tokens: int,
):
    return await _voice_client.chat_completion(
        messages=messages,
        stream=True,
        max_tokens=max_tokens,
    )


# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────

async def chat_with_tools(
    company_id: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run the 3-iteration agentic tool-calling loop.

    Returns
    -------
    ``{"response": str, "tool_calls_made": int, "model_used": str}``
    """
    settings = _settings
    input_budget = settings.max_context_tokens - settings.max_chat_tokens
    messages = trim_messages(messages, max_input_tokens=input_budget)

    tool_calls_total = 0
    use_fallback = False

    for iteration in range(settings.max_tool_iterations):
        try:
            response = await _call_hf(
                messages,
                tools=TOOLS,
                max_tokens=settings.max_chat_tokens,
                use_fallback=use_fallback,
            )
        except Exception as exc:
            if not use_fallback:
                logger.warning("Primary model failed (%s) — switching to fallback", exc)
                use_fallback = True
                response = await _call_hf(
                    messages,
                    tools=TOOLS,
                    max_tokens=settings.max_chat_tokens,
                    use_fallback=True,
                )
            else:
                raise

        ai_message = response.choices[0].message
        messages.append(serialize_message(ai_message))

        # No tool calls → final answer
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

        # Execute each requested tool
        for tc in ai_message.tool_calls:
            tool_calls_total += 1
            logger.info(
                "Iter %d — tool %s(%s)", iteration + 1,
                tc.function.name, tc.function.arguments,
            )
            result_json = await execute_tool(
                tc.function.name, tc.function.arguments, company_id,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": result_json,
            })

        # Re-trim after adding tool results
        messages = trim_messages(messages, max_input_tokens=input_budget)

    # ── Loop exhausted — force a summary ──────────────────────────
    messages.append({
        "role": "user",
        "content": (
            "Tool iteration limit reached. Please summarise all "
            "the data you have collected so far and provide a "
            "complete answer."
        ),
    })
    messages = trim_messages(messages, max_input_tokens=input_budget)

    final = await _call_hf(
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


async def stream_chat(
    messages: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """
    Yield SSE-formatted tokens from the voice model.

    Each yielded string is a complete ``data: …\\n\\n`` SSE frame.
    The final frame is ``data: [DONE]\\n\\n``.
    """
    settings = _settings
    input_budget = settings.max_context_tokens - settings.max_voice_tokens
    messages = trim_messages(messages, max_input_tokens=input_budget)

    try:
        stream = await _call_hf_stream(messages, max_tokens=settings.max_voice_tokens)
        async for chunk in stream:
            delta = chunk.choices[0].delta
            token = delta.content if delta else None
            if token:
                yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        logger.error("Voice stream error: %s", exc)
        yield f"data: [ERROR] {exc}\n\n"
