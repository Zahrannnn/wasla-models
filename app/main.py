"""
Wasla AI Agent Backend — FastAPI application init.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.rate_limit import init_redis, close_redis
from app.api.routes import chat, voice

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-22s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)


# ── Lifespan (Redis connect / disconnect) ─────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open Redis pool.  Shutdown: close it."""
    await init_redis()
    yield
    await close_redis()


# ── FastAPI app ───────────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Chat",
        "description": (
            "Text-based AI chat endpoints. "
            "**Route 1** uses a 3-iteration agentic tool-calling loop with "
            "Llama-3.3-70B (fallback: Qwen-72B). "
            "**Route 2** streams tokens via SSE using Llama-3.1-8B for low latency."
        ),
    },
    {
        "name": "Voice",
        "description": (
            "Voice endpoints for text-to-speech and real-time voice conversations. "
            "**Route 4** converts text to speech (Kokoro-82M, local). "
            "**Route 5** is a full-duplex WebSocket for voice conversations "
            "(Whisper STT → LLM streaming → Kokoro TTS streaming)."
        ),
    },
    {
        "name": "Health",
        "description": "Service health check and configuration status.",
    },
]

app = FastAPI(
    title="Wasla AI Agent API",
    summary="AI customer-support backend — chat, voice streaming, and voice conversations.",
    description=(
        "Drop-in replacement for Google Gemini-2.5-Flash, powered entirely by "
        "**free Hugging Face open-weights models**.\n\n"
        "## Endpoints\n\n"
        "| # | Endpoint | Transport | Purpose |\n"
        "|---|----------|-----------|----------|\n"
        "| 1 | `POST /api/chat/{company_id}` | JSON | Agentic chat with tool calling |\n"
        "| 2 | `POST /api/chat/{company_id}/stream` | SSE | Low-latency token streaming |\n"
        "| 4 | `POST /api/voice/tts` | Binary | One-shot text-to-speech |\n"
        "| 5 | `WS /api/voice/conversation/{company_id}` | WebSocket | Full-duplex voice conversation |\n\n"
        "## Models\n\n"
        "| Task | Model |\n"
        "|------|-------|\n"
        "| Chat (tool calling) | `meta-llama/Llama-3.3-70B-Instruct` |\n"
        "| Chat fallback | `Qwen/Qwen2.5-72B-Instruct` |\n"
        "| Voice streaming | `meta-llama/Llama-3.1-8B-Instruct` |\n"
        "| Text-to-speech | `hexgrad/Kokoro-82M` (local, 24 kHz) |\n"
        "| Speech-to-text | `openai/whisper-large-v3-turbo` (HF API) |\n"
    ),
    version="2.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    license_info={"name": "MIT"},
    contact={"name": "Wasla AI", "url": "https://wasla.ai"},
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # TODO: lock down for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(voice.router)


# ── Root & health ─────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Wasla AI Agent API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"], summary="Service health check",
         response_description="Current service status and configured models.")
async def health_check():
    """
    Returns the service status, configured model names, and key settings.

    Use this endpoint to verify the API is running and to inspect which
    models and voices are currently active.
    """
    from app.core.config import get_settings
    s = get_settings()
    return {
        "status": "ok",
        "main_model": s.main_chat_model,
        "fallback_model": s.fallback_chat_model,
        "voice_model": s.voice_stream_model,
        "tts_voice": s.tts_voice,
        "stt_model": s.stt_model,
        "max_context_tokens": s.max_context_tokens,
    }
