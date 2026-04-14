"""Shared authentication helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from app.shared import graph_request_context as _graph_ctx


def _configurable_dict(config: Any) -> dict[str, Any]:
    """Return the ``configurable`` map from a RunnableConfig (handles Mapping subclasses)."""
    if config is None:
        return {}
    if isinstance(config, Mapping):
        raw = config.get("configurable")
        if isinstance(raw, Mapping):
            return dict(raw)
    conf = getattr(config, "configurable", None)
    if isinstance(conf, Mapping):
        return dict(conf)
    return {}


def resolve_tool_bearer(state_bearer: str | None, config: Any) -> str | None:
    """
    Resolve JWT for CRM tools.

    Resolution order:

    1. ``configurable["bearer_token"]`` from ``RunnableConfig`` (set by chat routes).
    2. :func:`app.shared.graph_request_context.graph_bearer_get` — set in ASGI
       middleware from the raw ``Authorization`` header so tools still see the
       JWT if LangGraph drops custom ``configurable`` keys or runs work in a
       context where the merged config is incomplete.
    3. Graph state (``InjectedState("bearer_token")``) as a last resort.
    """
    conf = _configurable_dict(config)
    cfg_bearer = conf.get("bearer_token")
    if isinstance(cfg_bearer, str) and cfg_bearer.strip():
        return strip_bearer_prefix(cfg_bearer)

    ctx_bearer = _graph_ctx.graph_bearer_get()
    if isinstance(ctx_bearer, str) and ctx_bearer.strip():
        return strip_bearer_prefix(ctx_bearer)

    return strip_bearer_prefix(state_bearer)


def strip_bearer_prefix(value: str | None) -> str | None:
    """
    Return the JWT/credential string without a leading ``Bearer `` prefix.

    Swagger's **Authorize** dialog for HTTP Bearer usually expects **only** the
    token; if someone pastes ``Bearer eyJ...`` anyway, FastAPI still forwards that
    whole string as ``credentials``, and we would otherwise emit
    ``Authorization: Bearer Bearer eyJ...`` to the CRM.
    """
    if not value:
        return None
    t = value.strip()
    while True:
        lower = t.lower()
        if lower.startswith("bearer "):
            t = t[7:].strip()
            continue
        break
    return t or None


def extract_bearer(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> str | None:
    """
    Extract bearer token from FastAPI security scheme or raw ``Authorization`` header.

    Accepts ``Bearer <jwt>``, bare ``<jwt>`` (``eyJ...``), and strips duplicate
    ``Bearer `` prefixes from paste mistakes.
    """
    if credentials and credentials.credentials:
        return strip_bearer_prefix(credentials.credentials)
    raw = request.headers.get("authorization") or request.headers.get("Authorization")
    if not raw:
        return None
    raw = raw.strip()
    if raw.lower().startswith("bearer "):
        return strip_bearer_prefix(raw)
    if raw.startswith("eyJ"):
        return strip_bearer_prefix(raw)
    return None


def require_bearer(ctx: dict[str, Any]) -> str | dict[str, str]:
    """
    Return the bearer token string from ctx, or an error dict if missing.

    Usage in operations:
        t = require_bearer(ctx)
        if isinstance(t, dict):
            return t
        # t is the token string
    """
    token = strip_bearer_prefix(ctx.get("bearer_token"))
    if not token:
        return {
            "error": "unauthorized",
            "message": "Authentication required. Please log in first.",
        }
    return token
