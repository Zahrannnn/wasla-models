"""
Per-request values for LangGraph tool execution.

LangGraph / ``ToolNode`` often runs tools under ``asyncio.gather`` with a
``RunnableConfig`` that **drops** non-JSON-safe ``configurable`` entries (notably
the async CRM ``client``). We mirror those values in :mod:`contextvars` so
``_build_ctx`` can always resolve bearer + client for the active HTTP request.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Optional

_graph_bearer: ContextVar[Optional[str]] = ContextVar("wasla_graph_bearer", default=None)
_graph_crm_client: ContextVar[Any] = ContextVar("wasla_graph_crm_client", default=None)


def graph_bearer_set(token: Optional[str]) -> Token:
    """Bind ``token`` for this request; returns a handle for :func:`graph_bearer_reset`."""
    return _graph_bearer.set(token)


def graph_bearer_reset(handle: Token) -> None:
    """Restore the previous value (call from ``finally``)."""
    _graph_bearer.reset(handle)


def graph_bearer_get() -> Optional[str]:
    """JWT for the active request, if any."""
    return _graph_bearer.get()


def graph_crm_client_set(client: Any) -> Token:
    """Bind the portal HTTP client (``CustomerClient`` or ``CompanyClient``) for this graph invoke."""
    return _graph_crm_client.set(client)


def graph_crm_client_reset(handle: Token) -> None:
    _graph_crm_client.reset(handle)


def graph_crm_client_get() -> Any:
    return _graph_crm_client.get()
