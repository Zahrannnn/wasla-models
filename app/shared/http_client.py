"""
Unified async HTTP client for Wasla backend APIs.

Provides base request handling, auth injection, error mapping,
and param cleaning. Domain clients extend this class.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("wasla.http")

_ERROR_MAP = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "unprocessable",
    429: "rate_limited",
}


class BaseApiClient:
    """Async HTTP client with auth injection, error mapping, and param cleaning."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url) and self._client is not None

    async def init(self) -> None:
        if not self._base_url:
            return
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self._base_url.rstrip("/"),
            timeout=self._timeout,
            headers={"Content-Type": "application/json"},
        )
        logger.info("HTTP client connected to %s", self._base_url)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        bearer: str | None = None,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("HTTP client not initialized.")

        headers: dict[str, str] = {}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        try:
            response = await self._client.request(
                method, path, params=params, json=body, headers=headers,
            )
        except httpx.RequestError as exc:
            logger.exception("HTTP request failed: %s", exc)
            return {"error": "service_error", "message": "API is unavailable."}

        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return {"status": "success", "data": None}
            try:
                return {"status": "success", "data": response.json()}
            except ValueError:
                return {"status": "success", "data": {"raw": response.text}}

        try:
            err = response.json()
            message = err.get("message") or err.get("error") or response.text
        except ValueError:
            message = response.text

        error_type = _ERROR_MAP.get(response.status_code, "service_error")
        return {"error": error_type, "message": message or "API request failed."}

    @staticmethod
    def clean_params(params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None}

    @staticmethod
    def clean_body(body: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in body.items() if v is not None}
