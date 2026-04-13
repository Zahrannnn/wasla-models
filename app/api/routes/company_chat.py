"""
Company Portal Chat — staff-facing agentic endpoint.
POST /api/company/chat -> JSON response
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ChatRequest, ChatResponse
from app.shared.auth import extract_bearer
from app.shared.prompts import load_prompt
from app.company import tools as company_tools

logger = logging.getLogger("wasla.routes.company")
router = APIRouter(tags=["Company Chat"])

_bearer = HTTPBearer(auto_error=False)


def _auth_status_line(is_authenticated: bool) -> str:
    if is_authenticated:
        return "\n\nThe user IS authenticated. Call tools directly."
    return (
        "\n\nThe user is NOT authenticated. "
        "Offer to log them in via login_staff before using protected tools."
    )


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
    token = extract_bearer(credentials, request)
    logger.info("Company bearer: %s", "YES" if token else "NO")

    engine = request.app.state.engine
    client = request.app.state.company_client
    ctx = {"bearer_token": token, "client": client}

    system_prompt = load_prompt("company_system.md")
    system_prompt += _auth_status_line(is_authenticated=token is not None)

    messages = [{"role": "system", "content": system_prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await engine.run(
            messages,
            tools=company_tools.get_tool_schemas(),
            tool_executor=company_tools.execute_tool,
            ctx=ctx,
        )
    except Exception as exc:
        logger.exception("Company chat failed")
        detail = "AI model is unavailable."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "LLM authentication failed. Check LLM_API_KEY in .env."
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)
