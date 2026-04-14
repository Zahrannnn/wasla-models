"""
Reusable FastAPI dependencies.

Provides the session-based ChatRequest/ChatResponse models and
per-request rate-limit enforcement.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Path
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel, Field

from app.core.rate_limit import check_rate_limit
from app.shared.chart_models import ChartBlock, ChartDataset

logger = logging.getLogger("wasla.api.dependencies")


def graph_invoke_503_detail(exc: BaseException, *, default: str = "AI model is unavailable. Please try again later.") -> str:
    """Turn graph/LLM failures into a short message for HTTP 503 (Ollama vs cloud)."""
    text = f"{exc!s}".lower()
    if "model" in text and ("not found" in text or "404" in text):
        return (
            "Ollama does not have this model installed. Run `ollama pull` with the same tag as "
            "MAIN_CHAT_MODEL in .env (e.g. `qwen2.5:3b`). Ollama tags differ from Hugging Face names."
        )
    if "401" in str(exc) or "unauthorized" in text:
        return (
            "LLM authentication failed. For OpenRouter/Anthropic set `LLM_API_KEY` (or "
            "`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`). Ollama ignores API keys."
        )
    return default


def ai_message_text(msg: AIMessage) -> str:
    """Normalize ``AIMessage.content`` (str, multimodal blocks, or other) to plain text."""
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(x) for x in content)
    return str(content) if content is not None else ""


async def checkpoint_tool_calls_total(graph: Any, run_config: dict) -> int:
    """Return accumulated ``tool_calls_made`` for this thread before the current invoke."""
    try:
        snap = await graph.aget_state(run_config)
    except Exception:
        logger.debug("aget_state failed; treating tool_calls baseline as 0", exc_info=True)
        return 0
    values = snap.values
    if not isinstance(values, dict):
        return 0
    return int(values.get("tool_calls_made") or 0)


# ── Request / response models ────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for `POST /api/chat` and `POST /api/company/chat`."""

    message: str = Field(
        ...,
        min_length=1,
        description=(
            "End-user message for the assistant turn. "
            "The orchestration layer may call backend tools before composing the final response."
        ),
        json_schema_extra={
            "examples": [
                "List companies near me",
                "Show my open service requests",
            ]
        },
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Server-issued conversation identifier returned by a previous response. "
            "Omit on the first turn to start a new thread; the API returns a new UUID."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What companies are trending?",
                    "session_id": None,
                },
                {
                    "message": "Book a follow-up for the first one.",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                },
            ]
        }
    }


class ChatResponse(BaseModel):
    """Successful reply from a chat graph invocation."""

    response: str = Field(
        ...,
        description="Final assistant output after any intermediate tool calls (may contain Markdown).",
    )
    session_id: str = Field(
        description="Send this value back as `session_id` in subsequent requests to continue the same thread.",
    )
    tool_calls_made: int = Field(
        default=0,
        description=(
            "Number of tool calls executed during this HTTP request only "
            "(not the full session cumulative stored in the graph checkpoint)."
        ),
    )
    model_used: str = Field(
        default="",
        description="Model identifier reported by the provider for the final LLM turn (may be empty on some hosts).",
    )
    charts: list[ChartBlock] = Field(
        default_factory=list,
        description=(
            "Interactive chart payloads extracted from tool results. "
            "Each block contains structured data for the frontend to render "
            "as a Chart.js / Recharts chart inline in the conversation."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "Here are three companies matching your criteria …",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "tool_calls_made": 2,
                    "model_used": "qwen2.5:3b",
                    "charts": [],
                },
                {
                    "response": "Here is your financial report for Q1…",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "tool_calls_made": 1,
                    "model_used": "qwen2.5:3b",
                    "charts": [
                        {
                            "id": "expense_monthly",
                            "chart_type": "bar",
                            "title": "Monthly Expenses",
                            "labels": ["Jan 2026", "Feb 2026", "Mar 2026"],
                            "datasets": [{"label": "Amount (EGP)", "data": [12500, 15200, 9800]}],
                        }
                    ],
                },
            ]
        }
    }


class HealthResponse(BaseModel):
    """`GET /health` — process is up and LLM-related settings in effect."""

    status: str = Field(description="`ok` when the HTTP service is running.")
    llm_provider: str = Field(
        description="Configured `LLM_PROVIDER`: `ollama` (local), `openrouter`, or `anthropic`.",
    )
    main_model: str = Field(
        description="Primary chat model (`MAIN_CHAT_MODEL` / Ollama tag or OpenRouter id).",
    )
    fallback_model: str = Field(
        description="Fallback model when the primary fails or is overloaded.",
    )
    max_context_tokens: int = Field(
        description="Context budget used for trimming history (`MAX_CONTEXT_TOKENS`).",
    )


# ── Chart extraction ────────────────────────────────────────────


def extract_charts_from_messages(messages: list) -> list[ChartBlock]:
    """Scan ToolMessages for ``_charts`` payloads and return validated ChartBlocks.

    Tools that produce chart data include a ``_charts`` key in their JSON
    result.  This function pulls those out, validates each block against
    the ``ChartBlock`` schema, and returns them for inclusion in the HTTP
    response.  Invalid / unparseable blocks are silently skipped.
    """
    charts: list[ChartBlock] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        raw_charts = payload.get("_charts")
        if not isinstance(raw_charts, list):
            continue
        for raw in raw_charts:
            if not isinstance(raw, dict):
                continue
            try:
                # Validate datasets sub-objects
                datasets = []
                for ds in raw.get("datasets", []):
                    if not isinstance(ds, dict):
                        continue
                    datasets.append(ChartDataset(label=ds.get("label", ""), data=ds.get("data", [])))
                charts.append(ChartBlock(
                    id=raw["id"],
                    chart_type=raw["chart_type"],
                    title=raw["title"],
                    labels=raw.get("labels", []),
                    datasets=datasets,
                ))
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug("Skipping invalid chart block: %s", exc)
    return charts


# ── Dependency functions ─────────────────────────────────────────


async def get_company_id(
    company_id: str = Path(
        ...,
        description="Tenant / company identifier (e.g. `acme-corp`).",
        examples=["acme-corp", "demo-company"],
    ),
) -> str:
    """Extract and validate the company_id path parameter."""
    return company_id


async def enforce_rate_limit(
    company_id: str = Path(
        ...,
        description="Tenant identifier — used for per-company rate limiting.",
    ),
) -> None:
    """Check the per-company rate limit via Redis (30 req / 60 s by default)."""
    await check_rate_limit(company_id)
