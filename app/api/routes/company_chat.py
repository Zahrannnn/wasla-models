"""
Company Portal Chat — staff-facing agentic endpoint.

POST /api/company/chat → JSON response
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ChatRequest, ChatResponse
from app.core.config import get_settings
from app.tools.company_schemas import COMPANY_TOOLS
from app.tools.company_registry import execute_company_tool
from app.utils.context_manager import trim_messages
from app.utils.retries import llm_retry, serialize_message

from openai import AsyncOpenAI

logger = logging.getLogger("wasla.routes.company")
router = APIRouter(tags=["Company Chat"])

_bearer = HTTPBearer(auto_error=False)

_SYSTEM_PROMPT = """\
You are a helpful AI assistant for company staff (Managers and Employees) managing CRM operations. You can help with:
- Customer management (create, update, view history)
- Offers/quotes (create, send, track status)
- Task assignment and tracking
- Employee management
- Expense tracking
- Dashboard analytics
- Service request handling

User Roles:
- Manager: Full access to all features
- Employee: Can view/start/complete assigned tasks, change password

CRITICAL — Authentication is handled automatically:
- The staff member's JWT token is ALREADY attached to every tool call.
- NEVER ask for credentials. Just call the tool directly.
- If a tool returns "unauthorized", tell the user to log in.
- If a tool returns "forbidden", explain they lack permission for that action.

Rules:
1. Call tools immediately for data requests — don't ask "are you logged in?"
2. Confirm before destructive actions (delete customer, delete offer, etc.)
3. Explain results conversationally with tables — don't dump raw JSON.
4. Convert dates to readable format (March 20, 2026 not 2026-03-20T00:00:00Z).
5. After completing an action, suggest relevant next steps.
6. For multi-step flows (creating offers), guide step by step.
7. Surface important info (overdue tasks, high-priority items).
8. For Employees, suggest get_my_tasks instead of get_all_tasks if they lack permission.
9. Never expose tokens or internal IDs unnecessarily.
10. WARNING: You must ONLY use the exact tool names provided in your tools array. DO NOT hallucinate or invent tools (e.g., use get_dashboard or get_customers instead of inventing get_top_customers)."""


def _build_prompt(is_authenticated: bool) -> str:
    if is_authenticated:
        return _SYSTEM_PROMPT + "\n\nThe user IS authenticated. Call tools directly."
    return _SYSTEM_PROMPT + (
        "\n\nThe user is NOT authenticated. "
        "Offer to log them in via login_staff before using protected tools."
    )


def _get_token(creds: Optional[HTTPAuthorizationCredentials], request: Request) -> str | None:
    if creds and creds.credentials:
        return creds.credentials
    raw = request.headers.get("authorization")
    if raw and raw.strip().startswith("eyJ"):
        return raw.strip()
    return None


# Separate LLM client for company agent (reuses same config)
_settings = get_settings()
_client = AsyncOpenAI(base_url=_settings.llm_base_url, api_key=_settings.llm_api_key)


@llm_retry
async def _call_llm(messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
                     max_tokens: int = 1024, use_fallback: bool = False):
    model = _settings.fallback_chat_model if use_fallback else _settings.main_chat_model
    kw: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if tools:
        kw["tools"] = tools
    return await _client.chat.completions.create(**kw)


async def _company_chat_with_tools(messages: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    settings = _settings
    budget = settings.max_context_tokens - settings.max_chat_tokens
    messages = trim_messages(messages, max_input_tokens=budget)

    total_calls = 0
    fallback = False

    for iteration in range(settings.max_tool_iterations):
        try:
            resp = await _call_llm(messages, tools=COMPANY_TOOLS, max_tokens=settings.max_chat_tokens, use_fallback=fallback)
        except Exception as exc:
            if not fallback:
                logger.warning("Primary failed (%s) — fallback", exc)
                fallback = True
                resp = await _call_llm(messages, tools=COMPANY_TOOLS, max_tokens=settings.max_chat_tokens, use_fallback=True)
            else:
                raise

        msg = resp.choices[0].message
        messages.append(serialize_message(msg))

        if not msg.tool_calls:
            return {"response": msg.content or "", "tool_calls_made": total_calls,
                    "model_used": settings.fallback_chat_model if fallback else settings.main_chat_model}

        for tc in msg.tool_calls:
            total_calls += 1
            logger.info("Iter %d — %s(%s)", iteration + 1, tc.function.name, tc.function.arguments)
            result = await execute_company_tool(tc.function.name, tc.function.arguments, ctx)
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": result})

        messages = trim_messages(messages, max_input_tokens=budget)

    messages.append({"role": "user", "content": "Tool iteration limit reached. Summarise what you have so far."})
    messages = trim_messages(messages, max_input_tokens=budget)
    final = await _call_llm(messages, max_tokens=settings.max_chat_tokens, use_fallback=fallback)
    return {"response": final.choices[0].message.content or "", "tool_calls_made": total_calls,
            "model_used": settings.fallback_chat_model if fallback else settings.main_chat_model}


@router.post(
    "/api/company/chat",
    response_model=ChatResponse,
    summary="Company Portal — Staff agentic chat",
    operation_id="companyChat",
    responses={200: {"description": "AI response."}, 503: {"description": "AI unavailable."}},
)
async def company_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    Staff-facing chat endpoint with 40 tools for CRM operations:
    customers, offers, tasks, employees, expenses, dashboard, service requests.

    Click the lock icon and paste a staff JWT to authenticate.
    """
    token = _get_token(credentials, request)
    logger.info("Company bearer: %s", "YES" if token else "NO")
    ctx = {"bearer_token": token}
    prompt = _build_prompt(is_authenticated=token is not None)

    messages = [{"role": "system", "content": prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await _company_chat_with_tools(messages, ctx)
    except Exception as exc:
        logger.exception("Company chat failed")
        detail = "AI model is unavailable."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "LLM authentication failed. Check LLM_API_KEY in .env."
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)
