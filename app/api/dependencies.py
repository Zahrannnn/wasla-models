"""
Reusable FastAPI dependencies.

Provides common path-parameter extraction and per-request
rate-limit enforcement so routes stay clean.
"""

from __future__ import annotations

from fastapi import Path

from pydantic import BaseModel, Field

from app.core.rate_limit import check_rate_limit


# ── Request / response models ────────────────────────────────────

class ChatRequest(BaseModel):
    """Body for the main chat endpoint (Route 1)."""

    prompt: str = Field(
        ...,
        min_length=1,
        description="The user's message to the AI assistant.",
        json_schema_extra={"examples": ["Show me the top 5 customers"]},
    )
    conversation_history: list[dict] = Field(
        default_factory=list,
        description=(
            "Previous messages for multi-turn context. "
            "Each dict must have `role` (user/assistant/system) and `content` keys."
        ),
        json_schema_extra={
            "examples": [
                [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help you?"},
                ]
            ]
        },
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Show me the top 5 customers",
                    "conversation_history": [],
                },
                {
                    "prompt": "Tell me more about the first one",
                    "conversation_history": [
                        {"role": "user", "content": "Show me the top 5 customers"},
                        {"role": "assistant", "content": "Here are your top 5 customers..."},
                    ],
                },
            ]
        }
    }



class ChatResponse(BaseModel):
    """JSON response from the main chat endpoint."""

    response: str = Field(
        ...,
        description="The AI assistant's response text (may contain Markdown).",
    )
    tool_calls_made: int = Field(
        default=0,
        description="Number of tool calls executed during this request.",
    )
    model_used: str = Field(
        default="",
        description="The HF model that produced the response.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "Here are your top 5 customers:\n\n1. Acme Corp — $12,400\n2. ...",
                    "tool_calls_made": 1,
                    "model_used": "meta-llama/Llama-3.3-70B-Instruct",
                }
            ]
        }
    }



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
