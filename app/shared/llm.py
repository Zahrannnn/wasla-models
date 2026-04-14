"""
LLM Factory — creates LangChain chat models with provider selection,
per-model tool binding, and automatic fallback chaining.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

from langchain_core.tools import BaseTool

from app.core.config import Settings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger("wasla.llm")


def _resolve_api_key(settings: Settings, *env_fallbacks: str) -> str:
    """
    Non-empty API key for OpenAI-compatible / Anthropic clients.

    LangChain passes ``api_key`` through to the SDK; ``None`` is rejected at
    client construction, so we require a real string or raise with setup hints.
    """
    key = (settings.llm_api_key or "").strip()
    if key:
        return key
    for name in env_fallbacks:
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    env_hint = ", ".join(env_fallbacks) if env_fallbacks else "OPENAI_API_KEY"
    raise ValueError(
        "No LLM API key configured. Set LLM_API_KEY in .env (OpenRouter, HF, etc.), "
        f"or export {env_hint}. For local models without a cloud key, set LLM_PROVIDER=ollama."
    )


def _create_provider(settings: Settings, model_name: str) -> BaseChatModel:
    """Instantiate the correct LangChain chat model based on provider setting."""
    match settings.llm_provider:
        case "openrouter":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                api_key=_resolve_api_key(settings, "OPENAI_API_KEY"),
                base_url=settings.llm_base_url,
            )
        case "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=model_name,
                base_url=settings.ollama_base_url,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model_name,
                api_key=_resolve_api_key(settings, "ANTHROPIC_API_KEY", "OPENAI_API_KEY"),
            )
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def create_llm(
    settings: Settings,
    tools: Optional[list[BaseTool]] = None,
) -> BaseChatModel:
    """
    Create LLM with tools bound and fallback chained.

    Tools must be bound to EACH model individually BEFORE chaining with
    with_fallbacks(). Calling bind_tools() on a RunnableWithFallbacks does
    not reliably propagate schemas to both underlying models.
    """
    primary = _create_provider(settings, settings.main_chat_model)
    fallback = _create_provider(settings, settings.fallback_chat_model)

    if tools:
        primary = primary.bind_tools(tools)
        fallback = fallback.bind_tools(tools)

    logger.info(
        "LLM created: provider=%s primary=%s fallback=%s tools=%d",
        settings.llm_provider,
        settings.main_chat_model,
        settings.fallback_chat_model,
        len(tools) if tools else 0,
    )

    return primary.with_fallbacks([fallback])
