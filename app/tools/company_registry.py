"""Tool registry — Company Portal agent (staff-facing)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Coroutine

from app.tools import company_operations as ops

logger = logging.getLogger("wasla.company_tools")

_REG: dict[str, Callable[..., Coroutine]] = {
    "login_staff": ops.login_staff,
    "change_password": ops.change_password,
    "get_customers": ops.get_customers,
    "get_customer_details": ops.get_customer_details,
    "create_customer": ops.create_customer,
    "update_customer": ops.update_customer,
    "delete_customer": ops.delete_customer,
    "get_customer_offers": ops.get_customer_offers,
    "get_customer_tasks": ops.get_customer_tasks,
    "get_offers": ops.get_offers,
    "get_offer_details": ops.get_offer_details,
    "create_offer": ops.create_offer,
    "update_offer": ops.update_offer,
    "update_offer_status": ops.update_offer_status,
    "delete_offer": ops.delete_offer,
    "get_all_tasks": ops.get_all_tasks,
    "get_my_tasks": ops.get_my_tasks,
    "get_task_details": ops.get_task_details,
    "create_task": ops.create_task,
    "update_task": ops.update_task,
    "start_task": ops.start_task,
    "complete_task": ops.complete_task,
    "reassign_task": ops.reassign_task,
    "search_employees": ops.search_employees,
    "search_customers": ops.search_customers,
    "get_employees": ops.get_employees,
    "get_employee_details": ops.get_employee_details,
    "create_employee": ops.create_employee,
    "update_employee": ops.update_employee,
    "delete_employee": ops.delete_employee,
    "get_employee_performance": ops.get_employee_performance,
    "get_expenses": ops.get_expenses,
    "create_expense": ops.create_expense,
    "update_expense": ops.update_expense,
    "delete_expense": ops.delete_expense,
    "get_expense_charts": ops.get_expense_charts,
    "get_appointments": ops.get_appointments,
    "create_appointment": ops.create_appointment,
    "get_dashboard": ops.get_dashboard,
    "get_service_requests": ops.get_service_requests,
    "get_service_request_details": ops.get_service_request_details,
    "decline_service_request": ops.decline_service_request,
}


_ALIASES: dict[str, str] = {
    "get_top_customers": "get_customers",
    "get_my_customers": "get_customers",
    "get_all_customers": "get_customers",
    "search_customer": "search_customers",
    "search_employee": "search_employees",
    "get_dashboard_data": "get_dashboard",
    "get_all_offers": "get_offers",
    "get_my_offers": "get_offers",
    "get_my_tasks": "get_my_tasks",
}

async def execute_company_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    ctx: dict[str, Any],
) -> str:
    # Handle the Google search hallucination from Gemma specifically
    if tool_name == "google:search" or "search" in tool_name and "google" in tool_name:
        return json.dumps({"error": "Internet search disabled. Use internal CRM tools like get_customers, get_offers, etc."})

    # Transparently map common LLM hallucinations to the correct tool
    real_tool_name = _ALIASES.get(tool_name, tool_name)
    func = _REG.get(real_tool_name)

    if func is None:
        logger.warning("Unknown company tool: %s (originally %s)", real_tool_name, tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}. Check the exact tool names in your schema."})

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    try:
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Company tool %s raised error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
