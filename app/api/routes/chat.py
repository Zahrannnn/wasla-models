"""
Route 1 — Customer Portal Chat (ReAct agent loop)
POST /api/chat         -> JSON response (Customer Portal agent)
POST /api/chat/{company_id} -> Legacy backward-compat route
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ChatRequest, ChatResponse, enforce_rate_limit
from app.shared.auth import extract_bearer
from app.shared.prompts import load_prompt
from app.customer import tools as customer_tools

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Chat"])

_bearer_scheme = HTTPBearer(auto_error=False)


def _auth_status_line(is_authenticated: bool) -> str:
    if is_authenticated:
        return (
            "\n\nThe user IS authenticated — all protected tools will work. "
            "Call tools directly without asking for login."
        )
    return (
        "\n\nThe user is NOT authenticated (guest). "
        "Public tools work. For protected actions, suggest they log in first "
        "or offer to register/login via the register_customer or login_customer tools."
    )


async def _handle_chat(body: ChatRequest, request: Request, credentials, company_id: str | None = None):
    """Shared handler for both /api/chat and /api/chat/{company_id}."""
    token = extract_bearer(credentials, request)
    logger.info("Bearer extracted: %s", "YES" if token else "NO")

    engine = request.app.state.engine
    client = request.app.state.customer_client
    ctx = {"bearer_token": token, "client": client}

    system_prompt = load_prompt("customer_system.md")
    system_prompt += _auth_status_line(is_authenticated=token is not None)

    messages = [{"role": "system", "content": system_prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await engine.run(
            messages,
            tools=customer_tools.get_tool_schemas(),
            tool_executor=customer_tools.execute_tool,
            ctx=ctx,
        )
    except Exception as exc:
        logger.exception("Chat failed%s", f" for company {company_id}" if company_id else "")
        detail = "AI model is unavailable. Please try again later."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = (
                "LLM authentication failed. Set a valid LLM_API_KEY in .env."
            )
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Customer Portal — Agentic chat with tool calling",
    operation_id="portalChat",
    response_description="AI response with optional tool-call metadata.",
    responses={
        200: {"description": "Successful AI response."},
        429: {"description": "Rate limit exceeded."},
        503: {"description": "AI model is temporarily unavailable."},
    },
)
async def portal_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """
    **Customer Portal chat endpoint** — agentic tool-calling loop.

    The LLM can invoke 27 tools covering the full Customer Portal API:
    auth, companies, reviews, profiles, offers, service requests, dashboard.

    Click the **lock icon** (top-right) and paste your JWT to authenticate.
    Public actions (browse companies, view reviews) work without auth.
    """
    return await _handle_chat(body, request, credentials)


@router.post(
    "/api/chat/{company_id}",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Company-scoped chat (legacy)",
    operation_id="mainChat",
    include_in_schema=False,
)
async def main_chat(
    company_id: str,
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """Legacy company-scoped endpoint — delegates to portal chat."""
    return await _handle_chat(body, request, credentials, company_id=company_id)
