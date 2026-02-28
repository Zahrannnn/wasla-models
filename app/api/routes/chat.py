"""
Route 1 — Main Chat (tool-calling loop)
Route 2 — Voice Stream (SSE)

POST /api/chat/{company_id}         → JSON response
POST /api/chat/{company_id}/stream  → text/event-stream
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    ChatRequest,
    ChatResponse,
    VoiceChatRequest,
    enforce_rate_limit,
)
from app.services.llm_service import chat_with_tools, stream_chat

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Chat"])


# ─────────────────────────────────────────────────────────────────
#  Route 1 — Main Chat + Tool Calling
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/api/chat/{company_id}",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Route 1 — Agentic chat with tool calling",
    operation_id="mainChat",
    response_description="AI response with optional tool-call metadata.",
    responses={
        200: {
            "description": "Successful AI response.",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Here are your top 5 customers:\n\n1. Acme Corp — $12,400\n2. ...",
                        "tool_calls_made": 1,
                        "model_used": "meta-llama/Llama-3.3-70B-Instruct",
                    }
                }
            },
        },
        429: {"description": "Rate limit exceeded for this company."},
        503: {"description": "AI model is temporarily unavailable."},
    },
)
async def main_chat(company_id: str, body: ChatRequest):
    """
    **Agentic chat endpoint** — runs a 3-iteration tool-calling loop.

    The LLM can invoke tools (get customers, search products, create orders, etc.)
    and automatically incorporates tool results into its answer.

    - **Primary model:** `Llama-3.3-70B-Instruct`
    - **Fallback model:** `Qwen/Qwen2.5-72B-Instruct` (auto-switch on failure)
    - **Rate limited:** 30 requests per 60 seconds per company (configurable)
    """
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a professional assistant for company '{company_id}'. "
                "Format responses in Markdown. "
                "Use the provided tools when the user's request requires "
                "data retrieval or actions."
            ),
        },
    ]

    if body.conversation_history:
        messages.extend(body.conversation_history)

    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await chat_with_tools(company_id, messages)
    except Exception as exc:
        logger.exception("Chat failed for company %s", company_id)
        raise HTTPException(
            status_code=503,
            detail="AI model is unavailable. Please try again later.",
        ) from exc

    return ChatResponse(**result)


# ─────────────────────────────────────────────────────────────────
#  Route 2 — Voice Stream (SSE)
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/api/chat/{company_id}/stream",
    dependencies=[Depends(enforce_rate_limit)],
    summary="Route 2 — Low-latency voice SSE streaming",
    operation_id="voiceChatStream",
    response_description="Server-Sent Events stream of tokens.",
    responses={
        200: {
            "description": "SSE token stream.",
            "content": {
                "text/event-stream": {
                    "example": "data: Hello\n\ndata:  there!\n\ndata: [DONE]\n\n",
                }
            },
        },
        429: {"description": "Rate limit exceeded for this company."},
        503: {"description": "AI model is temporarily unavailable."},
    },
)
async def voice_chat_stream(company_id: str, body: VoiceChatRequest):
    """
    **Low-latency voice streaming endpoint** — returns tokens via SSE.

    Each `data:` frame contains a single token. The stream ends with
    `data: [DONE]`. Ideal for piping directly into a TTS engine on
    the frontend.

    - **Model:** `Llama-3.1-8B-Instruct` (optimised for speed)
    - Responses are short (≤ 2 sentences), conversational, no Markdown.
    """
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a voice assistant for company '{company_id}'. "
                "Keep answers under 2 sentences. "
                "Do NOT use markdown, bullet points, or code blocks. "
                "Speak naturally as if talking to a person."
            ),
        },
    ]

    if body.conversation_history:
        messages.extend(body.conversation_history)

    messages.append({"role": "user", "content": body.prompt})

    return StreamingResponse(
        stream_chat(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
