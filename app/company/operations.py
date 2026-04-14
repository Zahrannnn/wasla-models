"""Tool operations — Company Portal API (staff-facing)."""

from __future__ import annotations

from typing import Any

from app.shared.auth import require_bearer


# ── Auth ──────────────────────────────────────────────────────────

async def login_staff(ctx: dict, *, email: str, password: str) -> dict:
    return await ctx["client"].login_staff(email=email, password=password)


async def change_password(ctx: dict, *, current_password: str, new_password: str, confirm_password: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].change_password(t, current_password=current_password, new_password=new_password, confirm_password=confirm_password)


# ── Customers ─────────────────────────────────────────────────────

async def get_customers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customers(t, page_index=page_index, page_size=page_size, search=search)


async def get_customer_details(ctx: dict, *, customer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_details(t, customer_id)


async def create_customer(ctx: dict, *, first_name: str, last_name: str, email: str, phone_number: str,
                           address: str, city: str, zip_code: str, country: str, notes: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload = {"firstName": first_name, "lastName": last_name, "email": email, "phoneNumber": phone_number,
               "address": address, "city": city, "zipCode": zip_code, "country": country, "notes": notes}
    return await ctx["client"].create_customer(t, payload)


async def update_customer(ctx: dict, *, customer_id: int, first_name: str | None = None, last_name: str | None = None,
                           email: str | None = None, phone_number: str | None = None, address: str | None = None,
                           city: str | None = None, zip_code: str | None = None, country: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if first_name is not None: payload["firstName"] = first_name
    if last_name is not None: payload["lastName"] = last_name
    if email is not None: payload["email"] = email
    if phone_number is not None: payload["phoneNumber"] = phone_number
    if address is not None: payload["address"] = address
    if city is not None: payload["city"] = city
    if zip_code is not None: payload["zipCode"] = zip_code
    if country is not None: payload["country"] = country
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].update_customer(t, customer_id, payload)


async def delete_customer(ctx: dict, *, customer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_customer(t, customer_id)


async def get_customer_offers(ctx: dict, *, customer_id: int, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_offers(t, customer_id, page_index=page_index, page_size=page_size)


async def get_customer_tasks(ctx: dict, *, customer_id: int, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_tasks(t, customer_id, page_index=page_index, page_size=page_size)


# ── Offers ────────────────────────────────────────────────────────

async def get_offers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                     search_word: str | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offers(t, page_index=page_index, page_size=page_size, search_word=search_word, status=status)


async def get_offer_details(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offer_details(t, offer_id)


async def create_offer(ctx: dict, *, customer_id: int, service_request_id: int | None = None,
                        notes_in_offer: str | None = None, notes_not_in_offer: str | None = None,
                        language_code: str | None = None, email_to_customer: bool | None = None,
                        locations: list | None = None, services: dict | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"customerId": customer_id}
    if service_request_id is not None: payload["serviceRequestId"] = service_request_id
    if notes_in_offer is not None: payload["notesInOffer"] = notes_in_offer
    if notes_not_in_offer is not None: payload["notesNotInOffer"] = notes_not_in_offer
    if language_code is not None: payload["languageCode"] = language_code
    if email_to_customer is not None: payload["emailToCustomer"] = email_to_customer
    if locations is not None: payload["locations"] = locations
    if services is not None: payload["services"] = services
    return await ctx["client"].create_offer(t, payload)


async def update_offer(ctx: dict, *, offer_id: int, customer_id: int | None = None,
                        notes_in_offer: str | None = None, notes_not_in_offer: str | None = None,
                        locations: list | None = None, services: dict | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if customer_id is not None: payload["customerId"] = customer_id
    if notes_in_offer is not None: payload["notesInOffer"] = notes_in_offer
    if notes_not_in_offer is not None: payload["notesNotInOffer"] = notes_not_in_offer
    if locations is not None: payload["locations"] = locations
    if services is not None: payload["services"] = services
    return await ctx["client"].update_offer(t, offer_id, payload)


async def update_offer_status(ctx: dict, *, offer_id: int, status: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].update_offer_status(t, offer_id, status=status)


async def delete_offer(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_offer(t, offer_id)


# ── Tasks ─────────────────────────────────────────────────────────

async def get_all_tasks(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_all_tasks(t, page_index=page_index, page_size=page_size)


async def get_my_tasks(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_tasks(t, page_index=page_index, page_size=page_size)


async def get_task_details(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_task_details(t, task_id)


async def create_task(ctx: dict, *, assigned_to_user_id: int, task_title: str, customer_id: int | None = None,
                       description: str | None = None, priority: str | None = None, due_date: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"assignedToUserId": assigned_to_user_id, "taskTitle": task_title}
    if customer_id is not None: payload["customerId"] = customer_id
    if description is not None: payload["description"] = description
    if priority is not None: payload["priority"] = priority
    if due_date is not None: payload["dueDate"] = due_date
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].create_task(t, payload)


async def update_task(ctx: dict, *, task_item_id: int, assigned_to_user_id: int | None = None,
                       customer_id: int | None = None, task_title: str | None = None,
                       description: str | None = None, priority: str | None = None,
                       due_date: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if assigned_to_user_id is not None: payload["assignedToUserId"] = assigned_to_user_id
    if customer_id is not None: payload["customerId"] = customer_id
    if task_title is not None: payload["taskTitle"] = task_title
    if description is not None: payload["description"] = description
    if priority is not None: payload["priority"] = priority
    if due_date is not None: payload["dueDate"] = due_date
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].update_task(t, task_item_id, payload)


async def start_task(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].start_task(t, task_id)


async def complete_task(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].complete_task(t, task_id)


async def reassign_task(ctx: dict, *, task_id: int, new_assignee_id: int, reason: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].reassign_task(t, task_id, new_assignee_id=new_assignee_id, reason=reason)


async def search_employees(ctx: dict, *, search_name: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].search_employees(t, search_name=search_name)


async def search_customers(ctx: dict, *, search_name: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].search_customers(t, search_name=search_name)


# ── Employees ─────────────────────────────────────────────────────

async def get_employees(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employees(t, page_index=page_index, page_size=page_size, search=search)


async def get_employee_details(ctx: dict, *, user_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employee_details(t, user_id)


async def create_employee(ctx: dict, *, first_name: str, last_name: str, email: str, user_name: str, password: str,
                           is_active: bool | None = None, permission_ids: list | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name, "email": email, "userName": user_name, "password": password}
    if is_active is not None: payload["isActive"] = is_active
    if permission_ids is not None: payload["permissionIds"] = permission_ids
    return await ctx["client"].create_employee(t, payload)


async def update_employee(ctx: dict, *, user_id: int, first_name: str | None = None, last_name: str | None = None,
                           email: str | None = None, user_name: str | None = None, new_password: str | None = None,
                           is_active: bool | None = None, permission_ids: list | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if first_name is not None: payload["firstName"] = first_name
    if last_name is not None: payload["lastName"] = last_name
    if email is not None: payload["email"] = email
    if user_name is not None: payload["userName"] = user_name
    if new_password is not None: payload["newPassword"] = new_password
    if is_active is not None: payload["isActive"] = is_active
    if permission_ids is not None: payload["permissionIds"] = permission_ids
    return await ctx["client"].update_employee(t, user_id, payload)


async def delete_employee(ctx: dict, *, user_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_employee(t, user_id)


async def get_employee_performance(ctx: dict, *, employee_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employee_performance(t, employee_id)


# ── Expenses ──────────────────────────────────────────────────────

async def get_expenses(ctx: dict, *, page: int | None = None, page_size: int | None = None,
                       search: str | None = None, category: str | None = None, **kw) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_expenses(t, page=page, page_size=page_size, search=search, category=category,
                                             from_date=kw.get("from"), to_date=kw.get("to"))


async def create_expense(ctx: dict, *, description: str, amount_egp: float, expense_date: str, category: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].create_expense(t, {"description": description, "amountEgp": amount_egp, "expenseDate": expense_date, "category": category})


async def update_expense(ctx: dict, *, expense_id: int, description: str | None = None, amount_egp: float | None = None,
                          expense_date: str | None = None, category: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if description is not None: payload["description"] = description
    if amount_egp is not None: payload["amountEgp"] = amount_egp
    if expense_date is not None: payload["expenseDate"] = expense_date
    if category is not None: payload["category"] = category
    return await ctx["client"].update_expense(t, expense_id, payload)


async def delete_expense(ctx: dict, *, expense_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_expense(t, expense_id)


async def get_expense_charts(ctx: dict, *, chart_type: str, **kw) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    result = await ctx["client"].get_expense_charts(t, chart_type=chart_type, from_date=kw.get("from"), to_date=kw.get("to"))

    # Attach _charts metadata for interactive frontend rendering
    if isinstance(result, dict) and "error" not in result:
        _meta = {
            "monthly": {"id": "expense_monthly", "chart_type": "bar", "title": "Monthly Expenses"},
            "category": {"id": "expense_category", "chart_type": "doughnut", "title": "Expenses by Category"},
        }
        meta = _meta.get(chart_type, {"id": f"expense_{chart_type}", "chart_type": "bar", "title": f"Expense Chart ({chart_type})"})
        data = result.get("data", result)
        labels: list[str] = []
        values: list[float] = []
        if isinstance(data, list):
            for i, p in enumerate(data):
                labels.append(str(p.get("month") or p.get("category") or p.get("label") or p.get("name") or f"#{i+1}"))
                values.append(float(p.get("total") or p.get("amount") or p.get("value") or 0))
        elif isinstance(data, dict):
            labels = data.get("labels", [])
            values = data.get("data") or data.get("values", [])
        result["_charts"] = [{**meta, "labels": labels, "datasets": [{"label": "Amount (EGP)", "data": values}]}]

    return result


# ── Appointments ──────────────────────────────────────────────────

async def get_appointments(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                           search: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_appointments(t, page_index=page_index, page_size=page_size, search=search, start_date=start_date, end_date=end_date)


async def create_appointment(ctx: dict, *, customer_id: int, scheduled_at: str,
                             location: str | None = None, notes: str | None = None, language_code: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"customerId": customer_id, "scheduledAt": scheduled_at}
    if location is not None: payload["location"] = location
    if notes is not None: payload["notes"] = notes
    if language_code is not None: payload["languageCode"] = language_code
    return await ctx["client"].create_appointment(t, payload)


# ── Dashboard ─────────────────────────────────────────────────────

async def get_dashboard(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_dashboard(t)


# ── Service Requests ──────────────────────────────────────────────

async def get_service_requests(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_requests(t, page_index=page_index, page_size=page_size, status=status)


async def get_service_request_details(ctx: dict, *, request_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_request_details(t, request_id)


async def decline_service_request(ctx: dict, *, request_id: int, reason: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].decline_service_request(t, request_id, reason=reason)
