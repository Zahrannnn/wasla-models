"""
Pydantic BaseSettings — environment variable validation.

All configuration is read from ``.env`` at startup.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    # ── Hugging Face ──────────────────────────────────────────────
    huggingface_token: str = "hf_your_free_token_here"

    # Primary models
    main_chat_model: str = "meta-llama/Llama-3.3-70B-Instruct"
    voice_stream_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # Fallback model (if primary is rate-limited or down)
    fallback_chat_model: str = "Qwen/Qwen2.5-72B-Instruct"

    # ── Agent loop ────────────────────────────────────────────────
    max_tool_iterations: int = 3
    max_chat_tokens: int = 1024
    max_voice_tokens: int = 250

    # ── Context window ────────────────────────────────────────────
    # HF free-tier models generally cap at 8 192 tokens.
    # We reserve tokens for the reply, so the *input* budget is
    # (max_context_tokens - max_chat_tokens).
    max_context_tokens: int = 8192

    # ── Redis ─────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 30          # max requests …
    rate_limit_window_seconds: int = 60    # … per this window

    # ── TTS (Kokoro-82M local) ────────────────────────────────────
    tts_voice: str = "af_heart"        # Kokoro voice preset
    tts_lang_code: str = "a"           # "a" = American English

    # ── STT (Hugging Face Inference API) ──────────────────────────
    stt_model: str = "openai/whisper-large-v3-turbo"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    """Singleton accessor — the .env file is parsed only once."""
    return Settings()
