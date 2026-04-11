"""Tool definitions — JSON schemas for the Company Portal agent (staff-facing)."""

from __future__ import annotations
from typing import Any


def _t(name: str, desc: str, props: dict | None = None, req: list[str] | None = None) -> dict:
    p: dict[str, Any] = {"type": "object", "properties": props or {}, "required": req or []}
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": p}}


COMPANY_TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _t("login_staff",
       "Authenticate a company staff member (Manager or Employee). Returns JWT with company ID, role, and permissions.",
       {"email": {"type": "string"}, "password": {"type": "string"}},
       ["email", "password"]),

    _t("change_password",
       "Change the current user's password. Requires authentication.",
       {"current_password": {"type": "string"}, "new_password": {"type": "string"}, "confirm_password": {"type": "string"}},
       ["current_password", "new_password", "confirm_password"]),

    # ── Customers ─────────────────────────────────────────────────
    _t("get_customers",
       "Get paginated list of customers. Requires can_edit_customers.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}, "search": {"type": "string", "description": "Search by name or email"}}),

    _t("get_customer_details",
       "Get detailed customer info including offer count, task count, total profit. Requires can_edit_customers.",
       {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _t("create_customer",
       "Create a new customer record. Requires can_edit_customers.",
       {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
        "phone_number": {"type": "string"}, "address": {"type": "string"}, "city": {"type": "string"},
        "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
       ["first_name", "last_name", "email", "phone_number", "address", "city", "zip_code", "country", "notes"]),

    _t("update_customer",
       "Update an existing customer's information. Requires can_edit_customers.",
       {"customer_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
        "email": {"type": "string"}, "phone_number": {"type": "string"}, "address": {"type": "string"},
        "city": {"type": "string"}, "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
       ["customer_id"]),

    _t("delete_customer",
       "Delete a customer record. Requires can_edit_customers. Confirm with user first.",
       {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _t("get_customer_offers",
       "Get offer history for a specific customer. Requires can_edit_customers.",
       {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
       ["customer_id"]),

    _t("get_customer_tasks",
       "Get task history for a specific customer. Requires can_edit_customers.",
       {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
       ["customer_id"]),

    # ── Offers ────────────────────────────────────────────────────
    _t("get_offers",
       "Get paginated list of offers. Requires can_view_offers.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
        "search_word": {"type": "string", "description": "Search by client name or offer number"},
        "status": {"type": "string", "description": "Filter: Pending, Sent, Accepted, Rejected, Canceled"}}),

    _t("get_offer_details",
       "Get full offer details including services, locations, and line items. Requires can_view_offers.",
       {"offer_id": {"type": "integer"}}, ["offer_id"]),

    _t("create_offer",
       "Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers.",
       {"customer_id": {"type": "integer", "description": "Customer ID (required)"},
        "service_request_id": {"type": "integer", "description": "Link to service request (auto-updates to OfferSent)"},
        "notes_in_offer": {"type": "string", "description": "Notes visible to customer"},
        "notes_not_in_offer": {"type": "string", "description": "Internal notes"},
        "language_code": {"type": "string", "description": "e.g. 'en', 'de'"},
        "email_to_customer": {"type": "boolean", "description": "Send email notification"},
        "locations": {"type": "array", "description": "List of locations (From, To)", "items": {"type": "object"}},
        "services": {"type": "object", "description": "Service details (Moving, Cleaning, Packing, etc.)"}},
       ["customer_id"]),

    _t("update_offer",
       "Update an existing offer's details. Requires can_view_offers.",
       {"offer_id": {"type": "integer"}, "customer_id": {"type": "integer"},
        "notes_in_offer": {"type": "string"}, "notes_not_in_offer": {"type": "string"},
        "locations": {"type": "array", "items": {"type": "object"}},
        "services": {"type": "object"}},
       ["offer_id"]),

    _t("update_offer_status",
       "Change offer status (e.g. cancel). Customer Accept/Reject is via portal. Requires can_view_offers.",
       {"offer_id": {"type": "integer"},
        "status": {"type": "string", "enum": ["Pending", "Sent", "Accepted", "Rejected", "Canceled"]}},
       ["offer_id", "status"]),

    _t("delete_offer",
       "Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers.",
       {"offer_id": {"type": "integer"}}, ["offer_id"]),

    # ── Tasks ─────────────────────────────────────────────────────
    _t("get_all_tasks",
       "Get all company tasks with summary statistics. Requires can_manage_tasks (Manager only).",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _t("get_my_tasks",
       "Get tasks assigned to the current employee. Available to both Manager and Employee roles.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _t("get_task_details",
       "Get detailed task info including status, duration, files, assignment history.",
       {"task_id": {"type": "integer"}}, ["task_id"]),

    _t("create_task",
       "Create a new task and assign to an employee. Requires can_manage_tasks.",
       {"assigned_to_user_id": {"type": "integer", "description": "Employee ID to assign to"},
        "customer_id": {"type": "integer", "description": "Optional: link to customer"},
        "task_title": {"type": "string"}, "description": {"type": "string"},
        "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
        "due_date": {"type": "string", "description": "YYYY-MM-DD"}, "notes": {"type": "string"}},
       ["assigned_to_user_id", "task_title"]),

    _t("update_task",
       "Update task details. Requires can_manage_tasks.",
       {"task_item_id": {"type": "integer"}, "assigned_to_user_id": {"type": "integer"},
        "customer_id": {"type": "integer"}, "task_title": {"type": "string"},
        "description": {"type": "string"}, "priority": {"type": "string"},
        "due_date": {"type": "string"}, "notes": {"type": "string"}},
       ["task_item_id"]),

    _t("start_task",
       "Start a task (Pending → InProgress). Available to the assigned employee.",
       {"task_id": {"type": "integer"}}, ["task_id"]),

    _t("complete_task",
       "Mark a task as completed. Available to the assigned employee.",
       {"task_id": {"type": "integer"}}, ["task_id"]),

    _t("reassign_task",
       "Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks.",
       {"task_id": {"type": "integer"}, "new_assignee_id": {"type": "integer"}, "reason": {"type": "string"}},
       ["task_id", "new_assignee_id", "reason"]),

    _t("search_employees",
       "Search employees by name (autocomplete helper for task assignment).",
       {"search_name": {"type": "string"}}, ["search_name"]),

    _t("search_customers",
       "Search customers by name (autocomplete helper for task/offer creation).",
       {"search_name": {"type": "string"}}, ["search_name"]),

    # ── Employees ─────────────────────────────────────────────────
    _t("get_employees",
       "Get paginated list of employees. Requires can_manage_users.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
        "search": {"type": "string", "description": "Search by name or email"}}),

    _t("get_employee_details",
       "Get employee details including permissions and task counts. Requires can_manage_users.",
       {"user_id": {"type": "integer"}}, ["user_id"]),

    _t("create_employee",
       "Create a new employee account. Requires can_manage_users.",
       {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
        "user_name": {"type": "string"}, "password": {"type": "string"},
        "is_active": {"type": "boolean", "description": "Default: true"},
        "permission_ids": {"type": "array", "description": "Permission IDs to assign", "items": {"type": "integer"}}},
       ["first_name", "last_name", "email", "user_name", "password"]),

    _t("update_employee",
       "Update employee information. Requires can_manage_users.",
       {"user_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
        "email": {"type": "string"}, "user_name": {"type": "string"},
        "new_password": {"type": "string", "description": "Optional new password"},
        "is_active": {"type": "boolean"},
        "permission_ids": {"type": "array", "items": {"type": "integer"}}},
       ["user_id"]),

    _t("delete_employee",
       "Delete/deactivate an employee. Requires can_manage_users. Confirm first.",
       {"user_id": {"type": "integer"}}, ["user_id"]),

    _t("get_employee_performance",
       "Get performance report including completion rates. Requires can_manage_users.",
       {"employee_id": {"type": "integer"}}, ["employee_id"]),

    # ── Expenses ──────────────────────────────────────────────────
    _t("get_expenses",
       "Get paginated expenses. Requires can_view_reports.",
       {"page": {"type": "integer"}, "page_size": {"type": "integer"},
        "search": {"type": "string"}, "category": {"type": "string"},
        "from": {"type": "string", "description": "Start date YYYY-MM-DD"},
        "to": {"type": "string", "description": "End date YYYY-MM-DD"}}),

    _t("create_expense",
       "Record a new expense. Requires can_view_reports.",
       {"description": {"type": "string"}, "amount_egp": {"type": "number"},
        "expense_date": {"type": "string", "description": "YYYY-MM-DD"}, "category": {"type": "string"}},
       ["description", "amount_egp", "expense_date", "category"]),

    _t("update_expense",
       "Update an expense record. Requires can_view_reports.",
       {"expense_id": {"type": "integer"}, "description": {"type": "string"},
        "amount_egp": {"type": "number"}, "expense_date": {"type": "string"}, "category": {"type": "string"}},
       ["expense_id"]),

    _t("delete_expense",
       "Delete an expense record. Requires can_view_reports. Confirm first.",
       {"expense_id": {"type": "integer"}}, ["expense_id"]),

    _t("get_expense_charts",
       "Get expense chart data (monthly trend or category breakdown). Requires can_view_reports.",
       {"chart_type": {"type": "string", "enum": ["monthly", "category"]},
        "from": {"type": "string", "description": "Start date (optional, for category chart)"},
        "to": {"type": "string", "description": "End date (optional, for category chart)"}},
       ["chart_type"]),

    # ── Appointments ──────────────────────────────────────────────
    _t("get_appointments",
       "Get paginated list of appointments for the company. Requires can_view_offers.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
        "search": {"type": "string", "description": "Filter by customer name or location"},
        "start_date": {"type": "string", "description": "Filter from date (ISO 8601)"},
        "end_date": {"type": "string", "description": "Filter to date (ISO 8601)"}}),

    _t("create_appointment",
       "Schedule a new appointment (on-site visit). Automatically sends confirmation email. Requires can_view_offers.",
       {"customer_id": {"type": "integer"}, "scheduled_at": {"type": "string", "description": "UTC datetime ISO 8601"},
        "location": {"type": "string", "description": "Site address"}, "notes": {"type": "string"},
        "language_code": {"type": "string", "description": "en, de, fr, it"}},
       ["customer_id", "scheduled_at"]),

    # ── Dashboard ─────────────────────────────────────────────────
    _t("get_dashboard",
       "Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports."),

    # ── Service Requests ──────────────────────────────────────────
    _t("get_service_requests",
       "Get incoming service requests from portal users. Requires can_view_offers.",
       {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
        "status": {"type": "string", "description": "Filter: New, Viewed, OfferSent, Declined"}}),

    _t("get_service_request_details",
       "Get details of a specific service request. Requires can_view_offers.",
       {"request_id": {"type": "integer"}}, ["request_id"]),

    _t("decline_service_request",
       "Decline a service request from a portal user. Requires can_view_offers.",
       {"request_id": {"type": "integer"}, "reason": {"type": "string", "description": "Reason for declining (optional)"}},
       ["request_id"]),
]
