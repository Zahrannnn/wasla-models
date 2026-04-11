"""
Route 1 — Customer Portal Chat (tool-calling loop)
POST /api/chat         → JSON response (Customer Portal agent)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import (
    ChatRequest,
    ChatResponse,
    enforce_rate_limit,
)
from app.services.llm_service import chat_with_tools

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Chat"])

# auto_error=False so unauthenticated requests still work (public tools)
_bearer_scheme = HTTPBearer(auto_error=False)

_BASE_SYSTEM_PROMPT = """\
You are a helpful AI assistant for the Wasla Customer Portal. You help users:
- Browse and discover service companies
- Manage their account (register, login, profile)
- Submit and manage reviews
- Create and manage service requests
- View and respond to offers

Key Concepts:
- Lead: A user who registered but hasn't been accepted by any company yet.
- Customer: A user who has been accepted by at least one company.
- Digital Signature: Auto-generated at registration, required to accept offers.
- Service Request: An inquiry submitted to a company for services.
- Offer: A quote/proposal sent by a company to a customer.

CRITICAL — Authentication is handled automatically:
- The user's JWT token (if any) is ALREADY attached to every tool call behind the scenes.
- You NEVER need to ask for email, password, or token to use protected tools.
- If the user is authenticated, just call the tool directly (e.g. get_my_reviews, get_customer_profile, get_my_offers).
- If a tool returns an "unauthorized" error, THEN tell the user they need to log in.
- NEVER ask for credentials preemptively. Just try the tool.

Rules:
1. For authenticated actions, call the tool immediately — don't ask "are you logged in?"
2. Public endpoints (list_companies, get_company_details, get_company_reviews, etc.) always work.
3. Offer acceptance requires digital signature — use get_digital_signature (it needs the user's password).
4. Always confirm before destructive actions (delete_review, reject_offer).
5. Explain results conversationally — don't dump raw JSON.
6. After completing an action, suggest relevant next steps.
7. Never log, display, or ask for tokens."""


def _build_system_prompt(is_authenticated: bool) -> str:
    auth_line = (
        "\n\nThe user IS authenticated — all protected tools will work. "
        "Call tools directly without asking for login."
        if is_authenticated
        else "\n\nThe user is NOT authenticated (guest). "
        "Public tools work. For protected actions, suggest they log in first "
        "or offer to register/login via the register_customer or login_customer tools."
    )
    return _BASE_SYSTEM_PROMPT + auth_line


def _get_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> str | None:
    """Extract bearer token from security scheme or raw Authorization header."""
    if credentials and credentials.credentials:
        return credentials.credentials
    # Fallback: read raw header (handles clients that don't use "Bearer " prefix)
    raw = request.headers.get("authorization")
    if raw and raw.strip().startswith("eyJ"):
        return raw.strip()
    return None


# ─────────────────────────────────────────────────────────────────
#  Route 1 — Customer Portal Chat + Tool Calling
# ─────────────────────────────────────────────────────────────────
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
    bearer_token = _get_bearer_token(credentials, request)
    logger.info("Bearer extracted: %s", "YES" if bearer_token else "NO")
    ctx = {"bearer_token": bearer_token}
    system_prompt = _build_system_prompt(is_authenticated=bearer_token is not None)

    messages = [{"role": "system", "content": system_prompt}]

    if body.conversation_history:
        messages.extend(body.conversation_history)

    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await chat_with_tools(messages, ctx=ctx)
    except Exception as exc:
        logger.exception("Chat failed")
        detail = "AI model is unavailable. Please try again later."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = (
                "Hugging Face authentication failed. Set a valid HUGGINGFACE_TOKEN in .env "
                "with 'Make calls to Inference Providers' permission."
            )
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)


# ── Legacy company-scoped route (backward compatibility) ──────────
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
    bearer_token = _get_bearer_token(credentials, request)
    ctx = {"bearer_token": bearer_token}
    system_prompt = _build_system_prompt(is_authenticated=bearer_token is not None)

    messages = [{"role": "system", "content": system_prompt}]

    if body.conversation_history:
        messages.extend(body.conversation_history)

    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await chat_with_tools(messages, ctx=ctx)
    except Exception as exc:
        logger.exception("Chat failed for company %s", company_id)
        detail = "AI model is unavailable. Please try again later."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "Hugging Face authentication failed."
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)



