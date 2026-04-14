"""
Company Portal Chat — staff-facing LangGraph agent endpoint.
POST /api/company/chat -> JSON response (session-based)
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
    extract_charts_from_messages,
    graph_invoke_503_detail,
)
from app.shared.auth import extract_bearer
from app.shared.graph_request_context import graph_crm_client_reset, graph_crm_client_set

logger = logging.getLogger("wasla.routes.company")
router = APIRouter(tags=["Company Chat"])

_bearer = HTTPBearer(auto_error=False)


@router.post(
    "/api/company/chat",
    response_model=ChatResponse,
    summary="Company CRM staff assistant chat",
    description=(
        "Accepts a staff message and runs one LangGraph turn for the Company CRM assistant. "
        "Use `session_id` from earlier responses to continue thread context across turns; "
        "omit it to start a fresh thread. "
        "Most operational CRM tools require a valid Bearer JWT."
    ),
    operation_id="companyChat",
    response_description="Assistant reply with session continuity fields and per-request tool call count.",
    responses={
        200: {"description": "Graph finished with an assistant message."},
        500: {"description": "Graph ended without an AIMessage (unexpected)."},
        503: {
            "description": (
                "Service unavailable: LLM or graph invocation failed (for example Ollama is down, "
                "model tag is invalid, cloud API key is missing, or upstream authentication failed)."
            )
        },
    },
)
async def company_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    Runs the **company** LangGraph with **40** staff CRM tools (customers, offers, tasks,
    employees, expenses, dashboard, service requests, …).

    **Session:** same pattern as customer chat — reuse `session_id` for continuity.

    **Auth (Swagger):** click **Authorize**, choose **HTTPBearer**, and paste **only** the JWT
    (the three segments starting with `eyJ`). Do not include the word `Bearer` in the box;
    Swagger adds the scheme. Pasting `Bearer eyJ...` would send a double prefix and the CRM
    will reject the call.
    """
    token = extract_bearer(credentials, request)
    logger.info("Company bearer: %s", "YES" if token else "NO")

    session_id = body.session_id or str(uuid4())
    graph = request.app.state.company_graph

    run_config = {
        "configurable": {
            "thread_id": session_id,
            "client": request.app.state.company_client,
            "bearer_token": token,
        }
    }

    client_handle = graph_crm_client_set(request.app.state.company_client)
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
        logger.exception("Company chat failed")
        detail = graph_invoke_503_detail(
            exc,
            default="AI model is unavailable. For cloud LLMs set `LLM_API_KEY`; for Ollama ensure the model is pulled.",
        )
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
