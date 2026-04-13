"""Company Portal tools — schemas, registry, and executor merged."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.company import operations as ops

logger = logging.getLogger("wasla.company.tools")


def _tool(name: str, description: str, handler, properties: dict | None = None, required: list[str] | None = None) -> dict:
    params: dict[str, Any] = {"type": "object", "properties": properties or {}, "required": required or []}
    return {"name": name, "description": description, "parameters": params, "handler": handler}


TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _tool("login_staff",
          "Authenticate a company staff member (Manager or Employee). Returns JWT with company ID, role, and permissions.",
          ops.login_staff,
          {"email": {"type": "string"}, "password": {"type": "string"}},
          ["email", "password"]),

    _tool("change_password",
          "Change the current user's password. Requires authentication.",
          ops.change_password,
          {"current_password": {"type": "string"}, "new_password": {"type": "string"}, "confirm_password": {"type": "string"}},
          ["current_password", "new_password", "confirm_password"]),

    # ── Customers ─────────────────────────────────────────────────
    _tool("get_customers",
          "Get paginated list of customers. Requires can_edit_customers.",
          ops.get_customers,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}, "search": {"type": "string", "description": "Search by name or email"}}),

    _tool("get_customer_details",
          "Get detailed customer info including offer count, task count, total profit. Requires can_edit_customers.",
          ops.get_customer_details,
          {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _tool("create_customer",
          "Create a new customer record. Requires can_edit_customers.",
          ops.create_customer,
          {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
           "phone_number": {"type": "string"}, "address": {"type": "string"}, "city": {"type": "string"},
           "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
          ["first_name", "last_name", "email", "phone_number", "address", "city", "zip_code", "country", "notes"]),

    _tool("update_customer",
          "Update an existing customer's information. Requires can_edit_customers.",
          ops.update_customer,
          {"customer_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
           "email": {"type": "string"}, "phone_number": {"type": "string"}, "address": {"type": "string"},
           "city": {"type": "string"}, "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
          ["customer_id"]),

    _tool("delete_customer",
          "Delete a customer record. Requires can_edit_customers. Confirm with user first.",
          ops.delete_customer,
          {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _tool("get_customer_offers",
          "Get offer history for a specific customer. Requires can_edit_customers.",
          ops.get_customer_offers,
          {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
          ["customer_id"]),

    _tool("get_customer_tasks",
          "Get task history for a specific customer. Requires can_edit_customers.",
          ops.get_customer_tasks,
          {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
          ["customer_id"]),

    # ── Offers ────────────────────────────────────────────────────
    _tool("get_offers", "Get paginated list of offers. Requires can_view_offers.", ops.get_offers,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search_word": {"type": "string", "description": "Search by client name or offer number"},
           "status": {"type": "string", "description": "Filter: Pending, Sent, Accepted, Rejected, Canceled"}}),

    _tool("get_offer_details", "Get full offer details including services, locations, and line items. Requires can_view_offers.", ops.get_offer_details,
          {"offer_id": {"type": "integer"}}, ["offer_id"]),

    _tool("create_offer", "Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers.", ops.create_offer,
          {"customer_id": {"type": "integer", "description": "Customer ID (required)"},
           "service_request_id": {"type": "integer", "description": "Link to service request (auto-updates to OfferSent)"},
           "notes_in_offer": {"type": "string", "description": "Notes visible to customer"},
           "notes_not_in_offer": {"type": "string", "description": "Internal notes"},
           "language_code": {"type": "string", "description": "e.g. 'en', 'de'"},
           "email_to_customer": {"type": "boolean", "description": "Send email notification"},
           "locations": {"type": "array", "description": "List of locations (From, To)", "items": {"type": "object"}},
           "services": {"type": "object", "description": "Service details (Moving, Cleaning, Packing, etc.)"}},
          ["customer_id"]),

    _tool("update_offer", "Update an existing offer's details. Requires can_view_offers.", ops.update_offer,
          {"offer_id": {"type": "integer"}, "customer_id": {"type": "integer"},
           "notes_in_offer": {"type": "string"}, "notes_not_in_offer": {"type": "string"},
           "locations": {"type": "array", "items": {"type": "object"}}, "services": {"type": "object"}},
          ["offer_id"]),

    _tool("update_offer_status", "Change offer status (e.g. cancel). Requires can_view_offers.", ops.update_offer_status,
          {"offer_id": {"type": "integer"}, "status": {"type": "string", "enum": ["Pending", "Sent", "Accepted", "Rejected", "Canceled"]}},
          ["offer_id", "status"]),

    _tool("delete_offer", "Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers.", ops.delete_offer,
          {"offer_id": {"type": "integer"}}, ["offer_id"]),

    # ── Tasks ─────────────────────────────────────────────────────
    _tool("get_all_tasks", "Get all company tasks with summary statistics. Requires can_manage_tasks (Manager only).", ops.get_all_tasks,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _tool("get_my_tasks", "Get tasks assigned to the current employee. Available to both Manager and Employee roles.", ops.get_my_tasks,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _tool("get_task_details", "Get detailed task info including status, duration, files, assignment history.", ops.get_task_details,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("create_task", "Create a new task and assign to an employee. Requires can_manage_tasks.", ops.create_task,
          {"assigned_to_user_id": {"type": "integer", "description": "Employee ID to assign to"},
           "customer_id": {"type": "integer", "description": "Optional: link to customer"},
           "task_title": {"type": "string"}, "description": {"type": "string"},
           "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
           "due_date": {"type": "string", "description": "YYYY-MM-DD"}, "notes": {"type": "string"}},
          ["assigned_to_user_id", "task_title"]),

    _tool("update_task", "Update task details. Requires can_manage_tasks.", ops.update_task,
          {"task_item_id": {"type": "integer"}, "assigned_to_user_id": {"type": "integer"},
           "customer_id": {"type": "integer"}, "task_title": {"type": "string"},
           "description": {"type": "string"}, "priority": {"type": "string"},
           "due_date": {"type": "string"}, "notes": {"type": "string"}},
          ["task_item_id"]),

    _tool("start_task", "Start a task (Pending -> InProgress). Available to the assigned employee.", ops.start_task,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("complete_task", "Mark a task as completed. Available to the assigned employee.", ops.complete_task,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("reassign_task", "Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks.", ops.reassign_task,
          {"task_id": {"type": "integer"}, "new_assignee_id": {"type": "integer"}, "reason": {"type": "string"}},
          ["task_id", "new_assignee_id", "reason"]),

    _tool("search_employees", "Search employees by name (autocomplete helper for task assignment).", ops.search_employees,
          {"search_name": {"type": "string"}}, ["search_name"]),

    _tool("search_customers", "Search customers by name (autocomplete helper for task/offer creation).", ops.search_customers,
          {"search_name": {"type": "string"}}, ["search_name"]),

    # ── Employees ─────────────────────────────────────────────────
    _tool("get_employees", "Get paginated list of employees. Requires can_manage_users.", ops.get_employees,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string", "description": "Search by name or email"}}),

    _tool("get_employee_details", "Get employee details including permissions and task counts. Requires can_manage_users.", ops.get_employee_details,
          {"user_id": {"type": "integer"}}, ["user_id"]),

    _tool("create_employee", "Create a new employee account. Requires can_manage_users.", ops.create_employee,
          {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
           "user_name": {"type": "string"}, "password": {"type": "string"},
           "is_active": {"type": "boolean", "description": "Default: true"},
           "permission_ids": {"type": "array", "description": "Permission IDs to assign", "items": {"type": "integer"}}},
          ["first_name", "last_name", "email", "user_name", "password"]),

    _tool("update_employee", "Update employee information. Requires can_manage_users.", ops.update_employee,
          {"user_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
           "email": {"type": "string"}, "user_name": {"type": "string"},
           "new_password": {"type": "string", "description": "Optional new password"},
           "is_active": {"type": "boolean"},
           "permission_ids": {"type": "array", "items": {"type": "integer"}}},
          ["user_id"]),

    _tool("delete_employee", "Delete/deactivate an employee. Requires can_manage_users. Confirm first.", ops.delete_employee,
          {"user_id": {"type": "integer"}}, ["user_id"]),

    _tool("get_employee_performance", "Get performance report including completion rates. Requires can_manage_users.", ops.get_employee_performance,
          {"employee_id": {"type": "integer"}}, ["employee_id"]),

    # ── Expenses ──────────────────────────────────────────────────
    _tool("get_expenses", "Get paginated expenses. Requires can_view_reports.", ops.get_expenses,
          {"page": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string"}, "category": {"type": "string"},
           "from": {"type": "string", "description": "Start date YYYY-MM-DD"},
           "to": {"type": "string", "description": "End date YYYY-MM-DD"}}),

    _tool("create_expense", "Record a new expense. Requires can_view_reports.", ops.create_expense,
          {"description": {"type": "string"}, "amount_egp": {"type": "number"},
           "expense_date": {"type": "string", "description": "YYYY-MM-DD"}, "category": {"type": "string"}},
          ["description", "amount_egp", "expense_date", "category"]),

    _tool("update_expense", "Update an expense record. Requires can_view_reports.", ops.update_expense,
          {"expense_id": {"type": "integer"}, "description": {"type": "string"},
           "amount_egp": {"type": "number"}, "expense_date": {"type": "string"}, "category": {"type": "string"}},
          ["expense_id"]),

    _tool("delete_expense", "Delete an expense record. Requires can_view_reports. Confirm first.", ops.delete_expense,
          {"expense_id": {"type": "integer"}}, ["expense_id"]),

    _tool("get_expense_charts", "Get expense chart data (monthly trend or category breakdown). Requires can_view_reports.", ops.get_expense_charts,
          {"chart_type": {"type": "string", "enum": ["monthly", "category"]},
           "from": {"type": "string", "description": "Start date (optional)"},
           "to": {"type": "string", "description": "End date (optional)"}},
          ["chart_type"]),

    # ── Appointments ──────────────────────────────────────────────
    _tool("get_appointments", "Get paginated list of appointments for the company. Requires can_view_offers.", ops.get_appointments,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string", "description": "Filter by customer name or location"},
           "start_date": {"type": "string", "description": "Filter from date (ISO 8601)"},
           "end_date": {"type": "string", "description": "Filter to date (ISO 8601)"}}),

    _tool("create_appointment", "Schedule a new appointment (on-site visit). Requires can_view_offers.", ops.create_appointment,
          {"customer_id": {"type": "integer"}, "scheduled_at": {"type": "string", "description": "UTC datetime ISO 8601"},
           "location": {"type": "string", "description": "Site address"}, "notes": {"type": "string"},
           "language_code": {"type": "string", "description": "en, de, fr, it"}},
          ["customer_id", "scheduled_at"]),

    # ── Dashboard ─────────────────────────────────────────────────
    _tool("get_dashboard", "Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports.", ops.get_dashboard),

    # ── Service Requests ──────────────────────────────────────────
    _tool("get_service_requests", "Get incoming service requests from portal users. Requires can_view_offers.", ops.get_service_requests,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "status": {"type": "string", "description": "Filter: New, Viewed, OfferSent, Declined"}}),

    _tool("get_service_request_details", "Get details of a specific service request. Requires can_view_offers.", ops.get_service_request_details,
          {"request_id": {"type": "integer"}}, ["request_id"]),

    _tool("decline_service_request", "Decline a service request from a portal user. Requires can_view_offers.", ops.decline_service_request,
          {"request_id": {"type": "integer"}, "reason": {"type": "string", "description": "Reason for declining (optional)"}},
          ["request_id"]),
]

# ── Registry ──────────────────────────────────────────────────────

_REGISTRY = {t["name"]: t["handler"] for t in TOOLS}

_ALIASES: dict[str, str] = {
    "get_top_customers": "get_customers",
    "get_my_customers": "get_customers",
    "get_all_customers": "get_customers",
    "search_customer": "search_customers",
    "search_employee": "search_employees",
    "get_dashboard_data": "get_dashboard",
    "get_all_offers": "get_offers",
    "get_my_offers": "get_offers",
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return tool definitions for ReAct prompt generation (without handler)."""
    return [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in TOOLS
    ]


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    ctx: dict[str, Any],
) -> str:
    """Look up tool by name, execute, return JSON string."""
    # Handle the Google search hallucination from Gemma specifically
    if tool_name == "google:search" or ("search" in tool_name and "google" in tool_name):
        return json.dumps({"error": "Internet search disabled. Use internal CRM tools like get_customers, get_offers, etc."})

    # Transparently map common LLM hallucinations to the correct tool
    real_tool_name = _ALIASES.get(tool_name, tool_name)

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    func = _REGISTRY.get(real_tool_name)
    if func is None:
        logger.warning("Unknown company tool: %s (originally %s)", real_tool_name, tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}. Check the exact tool names in your schema."})

    try:
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Company tool %s raised error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
