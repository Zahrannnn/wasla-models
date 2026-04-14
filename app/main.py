"""
Wasla AI Agent Backend — FastAPI application init.

Run with:

.\.venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import get_settings
from app.core.rate_limit import init_redis, close_redis
import app.core.rate_limit as rl
from app.shared.agent import build_agent_graph
from app.shared.llm import create_llm
from app.shared.prompts import load_prompt
from app.customer.client import CustomerClient
from app.company.client import CompanyClient
from app.api.dependencies import HealthResponse
from app.api.routes import chat
from app.api.routes import company_chat
from app.shared.auth import extract_bearer
from app.shared.graph_request_context import graph_bearer_reset, graph_bearer_set

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-22s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if not (s.llm_api_key or "").strip() and s.llm_provider != "ollama":
        logging.getLogger("wasla").warning(
            "LLM_API_KEY is empty — startup will fail unless OPENAI_API_KEY (or ANTHROPIC_API_KEY) "
            "is set in the environment. Prefer LLM_API_KEY in .env (OpenRouter, HF, etc.), "
            "or set LLM_PROVIDER=ollama for local models."
        )

    try:
        await asyncio.wait_for(init_redis(), timeout=5.0)
    except asyncio.TimeoutError:
        rl._redis = None
        logging.getLogger("wasla").warning("Redis connection timed out — rate limiting disabled")

    customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
    company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
    await customer_client.init()
    await company_client.init()
    app.state.customer_client = customer_client
    app.state.company_client = company_client

    checkpointer = MemorySaver()

    from app.customer.tools import TOOLS as customer_tools
    from app.company.tools import TOOLS as company_tools

    customer_llm = create_llm(s, tools=customer_tools)
    company_llm = create_llm(s, tools=company_tools)

    app.state.customer_graph = build_agent_graph(
        llm=customer_llm,
        tools=customer_tools,
        system_prompt=load_prompt("customer_system.md"),
        checkpointer=checkpointer,
    )
    app.state.company_graph = build_agent_graph(
        llm=company_llm,
        tools=company_tools,
        system_prompt=load_prompt("company_system.md"),
        checkpointer=checkpointer,
    )

    yield

    await company_client.close()
    await customer_client.close()
    await close_redis()


# ── FastAPI app ───────────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Customer Chat",
        "description": (
            "Customer-facing conversational endpoint for portal users. "
            "Uses a LangGraph workflow with LangChain tool calling to execute customer tools, "
            "and supports optional `Authorization: Bearer` for authenticated actions. "
            "Conversation continuity is tracked with `session_id`."
        ),
    },
    {
        "name": "Company Chat",
        "description": (
            "Staff-focused conversational endpoint for internal CRM workflows. "
            "Runs the same LangGraph architecture with company CRM tools and expects "
            "a Bearer JWT for most protected operations."
        ),
    },
    {
        "name": "Health",
        "description": "Liveness and non-secret LLM configuration echo (`GET /health`).",
    },
]

app = FastAPI(
    title="Wasla Conversational API Platform",
    summary="Production API surface for Wasla Customer Portal and Company CRM conversational assistants.",
    description=(
        "This API exposes Wasla conversational assistants for the **Customer Portal** and **Company CRM**. "
        "Each request is processed by a LangGraph workflow that can call backend tools before returning a final answer.\n\n"
        "## Chat\n\n"
        "| Method | Path | Role |\n"
        "|--------|------|------|\n"
        "| `POST` | `/api/chat` | Customer assistant for portal flows; Bearer token optional. |\n"
        "| `POST` | `/api/company/chat` | Company CRM assistant for staff workflows; Bearer JWT typically required. |\n\n"
        "Request schema: [`ChatRequest`](#/components/schemas/ChatRequest) with `message` and optional `session_id`. "
        "Response schema: [`ChatResponse`](#/components/schemas/ChatResponse) with `response`, `session_id`, "
        "`tool_calls_made` (count for this HTTP request only), and `model_used`.\n\n"
        "## LLM configuration\n\n"
        "Set via environment / `.env` (see `app/core/config.py`): **`LLM_PROVIDER`** "
        "`ollama` | `openrouter` | `anthropic`, **`MAIN_CHAT_MODEL`**, **`FALLBACK_CHAT_MODEL`**, "
        "**`LLM_API_KEY`** (not required for Ollama), **`OLLAMA_BASE_URL`**, **`LLM_BASE_URL`**.\n\n"
        "## Other\n\n"
        "- **`GET /health`** — process up + effective model ids (no secrets).\n"
        "- **`GET /docs`** / **`GET /redoc`** — this OpenAPI UI.\n"
        "- Conversation threads use server-side checkpoints; **restart the process** clears in-memory sessions.\n"
    ),
    version="3.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    license_info={"name": "MIT"},
    contact={"name": "Wasla AI", "url": "https://wasla.ai"},
)

class GraphBearerContextMiddleware(BaseHTTPMiddleware):
    """Expose ``Authorization: Bearer`` to LangGraph tools via :mod:`contextvars`."""

    async def dispatch(self, request: Request, call_next):
        token = extract_bearer(None, request)
        handle = graph_bearer_set(token)
        try:
            return await call_next(request)
        finally:
            graph_bearer_reset(handle)


# Graph bearer first, CORS last → CORS is outermost (correct for browser preflight).
app.add_middleware(GraphBearerContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(company_chat.router)


@app.get("/ping", include_in_schema=False)
async def ping():
    return {"pong": True}


_ROOT_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Wasla AI Agent API</title></head><body>
<h1>Wasla AI Agent API</h1>
<p>JSON API — use the links below (browsers may sit on “loading” if you only open this tab and expect a full page without navigating).</p>
<ul>
  <li><a href="/docs">Swagger UI</a> (<code>/docs</code>)</li>
  <li><a href="/redoc">ReDoc</a> (<code>/redoc</code>)</li>
  <li><a href="/openapi.json">OpenAPI JSON</a></li>
  <li><a href="/health">Health</a> (<code>/health</code>)</li>
</ul>
<p><small>Machine JSON: <code>curl -H &quot;Accept: application/json&quot; http://localhost:8000/</code></small></p>
</body></html>"""


def _root_json() -> dict:
    return {"service": "Wasla AI Agent API", "docs": "/docs", "health": "/health"}


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """HTML for browsers (fast paint); JSON when the client asks for ``application/json`` only."""
    accept = (request.headers.get("accept") or "").lower()
    wants_json = "application/json" in accept
    wants_html = "text/html" in accept or "*/*" in accept
    if wants_json and not wants_html:
        return JSONResponse(_root_json())
    return HTMLResponse(content=_ROOT_HTML)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Avoid the browser waiting on a missing favicon while the tab is “loading”."""
    return Response(status_code=204)


@app.get(
    "/health",
    tags=["Health"],
    summary="Service health check",
    response_model=HealthResponse,
    response_description="Liveness plus configured LLM provider and model ids (no API keys).",
)
async def health_check() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        status="ok",
        llm_provider=s.llm_provider,
        main_model=s.main_chat_model,
        fallback_model=s.fallback_chat_model,
        max_context_tokens=s.max_context_tokens,
    )
