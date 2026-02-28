"""
Tool registry — maps tool JSON names to actual Python functions.

The ``execute_tool`` dispatcher is the single entry-point used by
``llm_service.py`` to run whichever tool the model chose.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Coroutine

from app.tools import operations

logger = logging.getLogger("wasla.tools")

# ── Name → function mapping ──────────────────────────────────────
_REGISTRY: dict[str, Callable[..., Coroutine]] = {
    "get_customer_list": operations.get_customer_list,
    "get_customer_details": operations.get_customer_details,
    "search_products": operations.search_products,
    "create_order": operations.create_order,
}


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    company_id: str,
) -> str:
    """
    Look up *tool_name*, call the matching function with
    **arguments, and return the result as a JSON string.

    Parameters
    ----------
    tool_name   : Function name the model chose to invoke.
    arguments   : Parsed dict **or** raw JSON string from the model.
    company_id  : Passed to every tool as positional context.

    Returns
    -------
    A JSON-encoded string suitable for the ``tool`` message role.
    """
    # Parse raw JSON if the model returned a string
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    func = _REGISTRY.get(tool_name)
    if func is None:
        logger.warning("Unknown tool requested: %s", tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = await func(company_id, **arguments)
    except Exception as exc:
        logger.exception("Tool %s raised an error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
