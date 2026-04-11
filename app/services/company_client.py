"""
Async HTTP client for the Wasla Company Portal API.

Used by company staff (Managers / Employees) to manage CRM operations:
customers, offers, tasks, employees, expenses, dashboard, service requests.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("wasla.company")

_client: httpx.AsyncClient | None = None


async def init_company_client() -> None:
    global _client
    settings = get_settings()
    if not settings.company_api_base_url:
        return
    if _client is not None:
        return
    _client = httpx.AsyncClient(
        base_url=settings.company_api_base_url.rstrip("/"),
        timeout=settings.company_api_timeout_seconds,
        headers={"Content-Type": "application/json"},
    )
    logger.info("Company client connected to %s", settings.company_api_base_url)


async def close_company_client() -> None:
    global _client
    if _client is None:
        return
    await _client.aclose()
    _client = None


def _require() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("Company client not initialized.")
    return _client


def _auth(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _err(status: int, msg: str | None = None) -> dict[str, str]:
    m = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
         409: "conflict", 422: "unprocessable", 429: "rate_limited"}
    return {"error": m.get(status, "service_error"), "message": msg or "API request failed."}


async def _req(
    method: str, path: str, *,
    bearer: str | None = None,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = _require()
    try:
        r = await client.request(method, path, params=params, json=body, headers=_auth(bearer))
    except httpx.RequestError as exc:
        logger.exception("Company API request failed: %s", exc)
        return {"error": "service_error", "message": "Company API is unavailable."}
    if 200 <= r.status_code < 300:
        if r.status_code == 204:
            return {"status": "success", "data": None}
        try:
            return {"status": "success", "data": r.json()}
        except ValueError:
            return {"status": "success", "data": {"raw": r.text}}
    try:
        e = r.json()
        msg = e.get("message") or e.get("error") or r.text
    except ValueError:
        msg = r.text
    return _err(r.status_code, msg)


def _p(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


# ── Auth ──────────────────────────────────────────────────────────

async def login_staff(*, email: str, password: str) -> dict:
    return await _req("POST", "/login", body={"email": email, "password": password})


async def change_password(bearer: str, *, current_password: str, new_password: str, confirm_password: str) -> dict:
    return await _req("POST", "/change-password", bearer=bearer,
                       body={"currentPassword": current_password, "newPassword": new_password, "confirmPassword": confirm_password})


# ── Customers ─────────────────────────────────────────────────────

async def get_customers(bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    return await _req("GET", "/Customer", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size, "search": search}))


async def get_customer_details(bearer: str, customer_id: int) -> dict:
    return await _req("GET", f"/Customer/{customer_id}", bearer=bearer)


async def create_customer(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Customer", bearer=bearer, body=payload)


async def update_customer(bearer: str, customer_id: int, payload: dict) -> dict:
    payload["customerId"] = customer_id
    return await _req("PUT", "/Customer", bearer=bearer, body=payload)


async def delete_customer(bearer: str, customer_id: int) -> dict:
    return await _req("DELETE", f"/Customer/{customer_id}", bearer=bearer)


async def get_customer_offers(bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    return await _req("GET", f"/Customer/{customer_id}/offers", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size}))


async def get_customer_tasks(bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    return await _req("GET", f"/Customer/{customer_id}/tasks", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size}))


# ── Offers ────────────────────────────────────────────────────────

async def get_offers(bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                     search_word: str | None = None, status: str | None = None) -> dict:
    return await _req("GET", "/Offers", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size, "searchWord": search_word, "status": status}))


async def get_offer_details(bearer: str, offer_id: int) -> dict:
    return await _req("GET", f"/Offers/{offer_id}", bearer=bearer)


async def create_offer(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Offers", bearer=bearer, body=payload)


async def update_offer(bearer: str, offer_id: int, payload: dict) -> dict:
    return await _req("PUT", f"/Offers/{offer_id}", bearer=bearer, body=payload)


async def update_offer_status(bearer: str, offer_id: int, *, status: str) -> dict:
    return await _req("PATCH", f"/Offers/{offer_id}/status", bearer=bearer, body=status)


async def delete_offer(bearer: str, offer_id: int) -> dict:
    return await _req("DELETE", f"/Offers/{offer_id}", bearer=bearer)


# ── Tasks ─────────────────────────────────────────────────────────

async def get_all_tasks(bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    return await _req("GET", "/Task/all", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size}))


async def get_my_tasks(bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    return await _req("GET", "/Task/assigned-to-me", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size}))


async def get_task_details(bearer: str, task_id: int) -> dict:
    return await _req("GET", f"/Task/{task_id}", bearer=bearer)


async def create_task(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Task/AddTask", bearer=bearer, body=payload)


async def update_task(bearer: str, task_id: int, payload: dict) -> dict:
    payload["taskId"] = task_id
    return await _req("PUT", "/Task", bearer=bearer, body=payload)


async def start_task(bearer: str, task_id: int) -> dict:
    return await _req("POST", f"/Task/{task_id}/start", bearer=bearer)


async def complete_task(bearer: str, task_id: int) -> dict:
    return await _req("POST", f"/Task/{task_id}/complete", bearer=bearer)


async def reassign_task(bearer: str, task_id: int, *, new_assignee_id: int, reason: str) -> dict:
    return await _req("POST", f"/Task/{task_id}/reassign", bearer=bearer,
                       body={"newAssigneeId": new_assignee_id, "reason": reason})


async def search_employees(bearer: str, *, search_name: str) -> dict:
    return await _req("GET", "/Task/employees", bearer=bearer, params={"searchName": search_name})


async def search_customers(bearer: str, *, search_name: str) -> dict:
    return await _req("GET", "/Task/customers", bearer=bearer, params={"searchName": search_name})


# ── Employees ─────────────────────────────────────────────────────

async def get_employees(bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    return await _req("GET", "/Employees", bearer=bearer, params=_p({"pageIndex": page_index, "pageSize": page_size, "search": search}))


async def get_employee_details(bearer: str, user_id: int) -> dict:
    return await _req("GET", f"/Employees/{user_id}", bearer=bearer)


async def create_employee(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Employees", bearer=bearer, body=payload)


async def update_employee(bearer: str, user_id: int, payload: dict) -> dict:
    return await _req("PUT", f"/Employees/{user_id}", bearer=bearer, body=payload)


async def delete_employee(bearer: str, user_id: int) -> dict:
    return await _req("DELETE", f"/Employees/{user_id}", bearer=bearer)


async def get_employee_performance(bearer: str, employee_id: int) -> dict:
    return await _req("GET", f"/Employees/{employee_id}/performance", bearer=bearer)


# ── Expenses ──────────────────────────────────────────────────────

async def get_expenses(bearer: str, *, page: int | None = None, page_size: int | None = None,
                       search: str | None = None, category: str | None = None,
                       from_date: str | None = None, to_date: str | None = None) -> dict:
    return await _req("GET", "/Expenses", bearer=bearer,
                       params=_p({"page": page, "pageSize": page_size, "search": search, "category": category, "from": from_date, "to": to_date}))


async def create_expense(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Expenses", bearer=bearer, body=payload)


async def update_expense(bearer: str, expense_id: int, payload: dict) -> dict:
    return await _req("PUT", f"/Expenses/{expense_id}", bearer=bearer, body=payload)


async def delete_expense(bearer: str, expense_id: int) -> dict:
    return await _req("DELETE", f"/Expenses/{expense_id}", bearer=bearer)


async def get_expense_charts(bearer: str, *, chart_type: str, from_date: str | None = None, to_date: str | None = None) -> dict:
    return await _req("GET", f"/Expenses/{chart_type}-chart", bearer=bearer,
                       params=_p({"from": from_date, "to": to_date}))


# ── Appointments ──────────────────────────────────────────────────

async def get_appointments(bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                           search: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    return await _req("GET", "/Appointments", bearer=bearer,
                       params=_p({"pageIndex": page_index, "pageSize": page_size, "search": search, "startDate": start_date, "endDate": end_date}))


async def create_appointment(bearer: str, payload: dict) -> dict:
    return await _req("POST", "/Appointments", bearer=bearer, body=payload)


# ── Dashboard ─────────────────────────────────────────────────────

async def get_dashboard(bearer: str) -> dict:
    return await _req("GET", "/CompanyDashboard", bearer=bearer)


# ── Service Requests ──────────────────────────────────────────────

async def get_service_requests(bearer: str, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    return await _req("GET", "/company/service-requests", bearer=bearer,
                       params=_p({"pageIndex": page_index, "pageSize": page_size, "status": status}))


async def get_service_request_details(bearer: str, request_id: int) -> dict:
    return await _req("GET", f"/company/service-requests/{request_id}", bearer=bearer)


async def decline_service_request(bearer: str, request_id: int, *, reason: str | None = None) -> dict:
    body = {"reason": reason} if reason else {}
    return await _req("PUT", f"/company/service-requests/{request_id}/decline", bearer=bearer, body=body)
