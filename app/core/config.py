"""
Pydantic BaseSettings — environment variable validation.

All configuration is read from ``.env`` at startup.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    # ── LLM Provider (any OpenAI-compatible endpoint) ────────────
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("llm_api_key", "huggingface_token"),
    )
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("llm_base_url", "hf_router_base_url"),
    )

    # Provider selection: "openrouter" | "ollama" | "anthropic"
    llm_provider: str = "ollama"

    # Ollama-specific (only used when llm_provider == "ollama")
    ollama_base_url: str = "http://localhost:11434"

    # Primary chat model (Ollama tag, e.g. qwen2.5:3b, or OpenRouter id when using openrouter)
    main_chat_model: str = "qwen2.5:3b"

    # Fallback model (same tag is fine for Ollama to avoid pulling two models)
    fallback_chat_model: str = "qwen2.5:3b"

    # ── Agent loop ────────────────────────────────────────────────
    max_tool_iterations: int = 3
    max_chat_tokens: int = 1024

    # ── Context window ────────────────────────────────────────────
    # HF free-tier models generally cap at 8 192 tokens.
    # We reserve tokens for the reply, so the *input* budget is
    # (max_context_tokens - max_chat_tokens).
    max_context_tokens: int = 8192

    # ── Customer Portal API (only source for customer data) ─────────
    crm_api_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("crm_api_base_url", "backend_api_base_url"),
    )
    crm_api_timeout_seconds: int = Field(
        default=10,
        validation_alias=AliasChoices("crm_api_timeout_seconds", "backend_api_timeout_seconds"),
    )

    # ── Company Portal API (staff-facing CRM operations) ──────────
    company_api_base_url: str = ""
    company_api_timeout_seconds: int = 10

    # ── Redis ─────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 30          # max requests …
    rate_limit_window_seconds: int = 60    # … per this window

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # ignore unknown env vars (e.g. old backend_api_*)
    }


@lru_cache()
def get_settings() -> Settings:
    """Singleton accessor — the .env file is parsed only once."""
    return Settings()
