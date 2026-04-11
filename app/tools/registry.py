"""
Tool registry — maps tool JSON names to Python functions.

The ``execute_tool`` dispatcher is the single entry-point used by
``llm_service.py`` to run whichever tool the model chose.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Coroutine

from app.tools import operations as ops

logger = logging.getLogger("wasla.tools")

_REGISTRY: dict[str, Callable[..., Coroutine]] = {
    # Auth
    "register_customer": ops.register_customer,
    "login_customer": ops.login_customer,
    "refresh_token": ops.refresh_token,
    "logout": ops.logout,
    "logout_all": ops.logout_all,
    # Company Discovery
    "list_companies": ops.list_companies,
    "get_recommended_companies": ops.get_recommended_companies,
    "get_trending_companies": ops.get_trending_companies,
    "get_company_details": ops.get_company_details,
    "get_company_reviews": ops.get_company_reviews,
    # Reviews
    "submit_review": ops.submit_review,
    "update_review": ops.update_review,
    "delete_review": ops.delete_review,
    "get_my_reviews": ops.get_my_reviews,
    # Profiles
    "get_customer_profile": ops.get_customer_profile,
    "update_customer_profile": ops.update_customer_profile,
    "get_lead_profile": ops.get_lead_profile,
    "update_lead_profile": ops.update_lead_profile,
    "get_digital_signature": ops.get_digital_signature,
    # Offers
    "get_my_offers": ops.get_my_offers,
    "get_offer_details": ops.get_offer_details,
    "accept_offer": ops.accept_offer,
    "reject_offer": ops.reject_offer,
    "get_dashboard": ops.get_dashboard,
    # Service Requests
    "create_service_request": ops.create_service_request,
    "get_my_service_requests": ops.get_my_service_requests,
    "get_service_request_details": ops.get_service_request_details,
}


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    ctx: dict[str, Any],
) -> str:
    """
    Look up *tool_name*, call the matching function, return result as JSON string.

    Parameters
    ----------
    tool_name  : Function name the model chose to invoke.
    arguments  : Parsed dict or raw JSON string from the model.
    ctx        : Context dict with optional bearer_token, etc.
    """
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
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Tool %s raised an error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
