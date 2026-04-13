"""
Wasla AI Agent Backend — FastAPI application init.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.rate_limit import init_redis, close_redis
import app.core.rate_limit as rl
from app.shared.react_engine import ReactEngine
from app.customer.client import CustomerClient
from app.company.client import CompanyClient
from app.api.routes import chat
from app.api.routes import company_chat

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
    if not s.llm_api_key:
        logging.getLogger("wasla").warning(
            "LLM_API_KEY is not set. Copy .env.example to .env and set a valid API key. "
            "Supported: OpenRouter (openrouter.ai), HuggingFace (hf.co/settings/tokens), or any OpenAI-compatible provider."
        )

    # Redis
    try:
        await asyncio.wait_for(init_redis(), timeout=5.0)
    except asyncio.TimeoutError:
        rl._redis = None
        logging.getLogger("wasla").warning("Redis connection timed out — rate limiting disabled")

    # HTTP clients
    customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
    company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
    await customer_client.init()
    await company_client.init()
    app.state.customer_client = customer_client
    app.state.company_client = company_client

    # LLM client + ReAct engine
    llm_client = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    app.state.engine = ReactEngine(llm_client, s)

    yield

    await company_client.close()
    await customer_client.close()
    await close_redis()


# ── FastAPI app ───────────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Customer Chat",
        "description": "Customer-facing AI chat endpoint widget using an agentic tool-calling loop. Accessed externally via the Wasla Customer Portal.",
    },
    {
        "name": "Company Chat",
        "description": "Staff-facing (Manager / Employee) AI chat with 40 tools for full CRM operations.",
    },
    {
        "name": "Health",
        "description": "Service health check and configuration status.",
    },
]

app = FastAPI(
    title="Wasla AI Agent APIs",
    summary="Agentic AI backend for Wasla CRM and Customer Portals",
    description=(
        "This API provides agentic conversational interfaces for both the Wasla Customer Portal "
        "and the Internal Company CRM. It operates natively using local Ollama models (e.g. Qwen 2.5) "
        "or configured OpenRouter models to process intent and automatically execute backend actions.\n\n"
        "## Endpoints\n\n"
        "| Endpoint | Transport | Context | Capabilities |\n"
        "|----------|-----------|---------|--------------|\n"
        "| `POST /api/chat/{company_id}` | JSON | Public Customer Portal | General inquiries, submitting service requests, checking offers. |\n"
        "| `POST /api/company/chat` | JSON | Internal CRM | Full CRM capabilities (Customers, Offers, Tasks, Appointments). Requires JWT Bearer token authentication. |\n\n"
        "---\n"
        "**Authentication:** Include standard `Bearer <JWT_TOKEN>` in the headers when accessing protected internal endpoints."
    ),
    version="2.1.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    license_info={"name": "MIT"},
    contact={"name": "Wasla AI", "url": "https://wasla.ai"},
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(company_chat.router)


# ── Root & health ─────────────────────────────────────────────────
@app.get("/ping", include_in_schema=False)
async def ping():
    return {"pong": True}


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Wasla AI Agent API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"], summary="Service health check",
         response_description="Current service status and configured models.")
async def health_check():
    s = get_settings()
    return {
        "status": "ok",
        "main_model": s.main_chat_model,
        "fallback_model": s.fallback_chat_model,
        "max_context_tokens": s.max_context_tokens,
    }
