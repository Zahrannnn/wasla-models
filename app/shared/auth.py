"""Shared authentication helpers."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials


def extract_bearer(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> str | None:
    """
    Extract bearer token from FastAPI security scheme or raw Authorization header.

    Handles both standard "Bearer xxx" and raw "eyJ..." JWT formats.
    """
    if credentials and credentials.credentials:
        return credentials.credentials
    raw = request.headers.get("authorization")
    if raw and raw.strip().startswith("eyJ"):
        return raw.strip()
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
    token = ctx.get("bearer_token")
    if not token:
        return {
            "error": "unauthorized",
            "message": "Authentication required. Please log in first.",
        }
    return token
