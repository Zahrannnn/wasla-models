"""
Customer Portal Chat — LangGraph agent endpoint.
POST /api/chat         -> JSON response (session-based)
POST /api/chat/{company_id} -> Legacy backward-compat route
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import AIMessage, HumanMessage

from app.api.dependencies import (
    ChatRequest,
    ChatResponse,
    ai_message_text,
    checkpoint_tool_calls_total,
    enforce_rate_limit,
    extract_charts_from_messages,
    graph_invoke_503_detail,
)
from app.shared.auth import extract_bearer
from app.shared.graph_request_context import graph_crm_client_reset, graph_crm_client_set

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Customer Chat"])

_bearer_scheme = HTTPBearer(auto_error=False)


async def _handle_chat(body: ChatRequest, request: Request, credentials, company_id: str | None = None):
    """Shared handler for both /api/chat and /api/chat/{company_id}."""
    token = extract_bearer(credentials, request)
    logger.info("Bearer extracted: %s", "YES" if token else "NO")

    session_id = body.session_id or str(uuid4())
    graph = request.app.state.customer_graph

    run_config = {
        "configurable": {
            "thread_id": session_id,
            "client": request.app.state.customer_client,
            "bearer_token": token,
        }
    }

    client_handle = graph_crm_client_set(request.app.state.customer_client)
    try:
        tool_calls_before = await checkpoint_tool_calls_total(graph, run_config)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=body.message)],
                "bearer_token": token,
            },
            config=run_config,
        )
    except Exception as exc:
        logger.exception("Chat failed%s", f" for company {company_id}" if company_id else "")
        detail = graph_invoke_503_detail(exc)
        raise HTTPException(status_code=503, detail=detail) from exc
    finally:
        graph_crm_client_reset(client_handle)

    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=500, detail="Unexpected graph output (missing messages).")

    last = messages[-1]
    if not isinstance(last, AIMessage):
        raise HTTPException(status_code=500, detail="Unexpected graph output (no AIMessage).")

    tool_calls_after = int(result.get("tool_calls_made") or 0)
    charts = extract_charts_from_messages(messages)
    return ChatResponse(
        response=ai_message_text(last),
        session_id=session_id,
        tool_calls_made=max(0, tool_calls_after - tool_calls_before),
        model_used=result.get("model_used", ""),
        charts=charts,
    )


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Customer Portal assistant agentic chat",
    description=(
        "Accepts a customer message and runs one LangGraph turn for the Customer Portal assistant. "
        "Provide `session_id` from a previous response to continue the same conversation thread; "
        "omit it to start a new server-managed thread. "
        "A Bearer token is optional and unlocks authenticated tool actions."
    ),
    operation_id="portalChat",
    response_description="Assistant reply with session continuity fields and per-request tool call count.",
    responses={
        200: {"description": "Graph finished with an assistant message."},
        429: {"description": "Rate limit exceeded (legacy `POST /api/chat/{company_id}` only)."},
        500: {"description": "Graph ended without an AIMessage (unexpected)."},
        503: {
            "description": (
                "Service unavailable: LLM or graph invocation failed (for example Ollama is down, "
                "model tag is invalid, cloud API key is missing, or upstream authentication failed)."
            )
        },
    },
)
async def portal_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """
    Runs the **customer** LangGraph once per request: your `message` is appended to the thread,
    then the model may call **Customer Portal** tools (auth, companies, reviews, offers,
    service requests, dashboard, etc.) until it returns a final answer.

    **Session:** omit `session_id` the first time; reuse the returned id on later turns.
    **Auth:** optional `Authorization: Bearer <JWT>` — without it, only public tools succeed.
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
