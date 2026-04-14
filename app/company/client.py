"""Async HTTP client for the Wasla Company Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.http_client import BaseApiClient


class CompanyClient(BaseApiClient):
    """Company Portal API client — extends BaseApiClient with domain methods."""

    # ── Auth ──────────────────────────────────────────────────────

    async def login_staff(self, *, email: str, password: str) -> dict[str, Any]:
        return await self.request("POST", "/login", body={"email": email, "password": password})

    async def change_password(self, bearer: str, *, current_password: str, new_password: str, confirm_password: str) -> dict[str, Any]:
        return await self.request("POST", "/change-password", bearer=bearer,
                                   body={"currentPassword": current_password, "newPassword": new_password, "confirmPassword": confirm_password})

    # ── Customers ─────────────────────────────────────────────────

    async def get_customers(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Customer", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size, "search": search}))

    async def get_customer_details(self, bearer: str, customer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}", bearer=bearer)

    async def create_customer(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Customer", bearer=bearer, body=payload)

    async def update_customer(self, bearer: str, customer_id: int, payload: dict) -> dict[str, Any]:
        payload["customerId"] = customer_id
        return await self.request("PUT", "/Customer", bearer=bearer, body=payload)

    async def delete_customer(self, bearer: str, customer_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Customer/{customer_id}", bearer=bearer)

    async def get_customer_offers(self, bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}/offers", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size}))

    async def get_customer_tasks(self, bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}/tasks", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size}))

    # ── Offers ────────────────────────────────────────────────────

    async def get_offers(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                         search_word: str | None = None, status: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Offers", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size, "searchWord": search_word, "status": status}))

    async def get_offer_details(self, bearer: str, offer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Offers/{offer_id}", bearer=bearer)

    async def create_offer(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Offers", bearer=bearer, body=payload)

    async def update_offer(self, bearer: str, offer_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Offers/{offer_id}", bearer=bearer, body=payload)

    async def update_offer_status(self, bearer: str, offer_id: int, *, status: str) -> dict[str, Any]:
        # Backend expects a JSON string primitive (e.g. "Sent"), not {"status": "..."}.
        return await self.request("PATCH", f"/Offers/{offer_id}/status", bearer=bearer, body=status)

    async def delete_offer(self, bearer: str, offer_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Offers/{offer_id}", bearer=bearer)

    # ── Tasks ─────────────────────────────────────────────────────

    async def get_all_tasks(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Task/all", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size}))

    async def get_my_tasks(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Task/assigned-to-me", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size}))

    async def get_task_details(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Task/{task_id}", bearer=bearer)

    async def create_task(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Task/AddTask", bearer=bearer, body=payload)

    async def update_task(self, bearer: str, task_id: int, payload: dict) -> dict[str, Any]:
        payload["taskId"] = task_id
        return await self.request("PUT", "/Task", bearer=bearer, body=payload)

    async def start_task(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/start", bearer=bearer)

    async def complete_task(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/complete", bearer=bearer)

    async def reassign_task(self, bearer: str, task_id: int, *, new_assignee_id: int, reason: str) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/reassign", bearer=bearer,
                                   body={"newAssigneeId": new_assignee_id, "reason": reason})

    async def search_employees(self, bearer: str, *, search_name: str) -> dict[str, Any]:
        return await self.request("GET", "/Task/employees", bearer=bearer, params={"searchName": search_name})

    async def search_customers(self, bearer: str, *, search_name: str) -> dict[str, Any]:
        return await self.request("GET", "/Task/customers", bearer=bearer, params={"searchName": search_name})

    # ── Employees ─────────────────────────────────────────────────

    async def get_employees(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Employees", bearer=bearer, params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size, "search": search}))

    async def get_employee_details(self, bearer: str, user_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Employees/{user_id}", bearer=bearer)

    async def create_employee(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Employees", bearer=bearer, body=payload)

    async def update_employee(self, bearer: str, user_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Employees/{user_id}", bearer=bearer, body=payload)

    async def delete_employee(self, bearer: str, user_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Employees/{user_id}", bearer=bearer)

    async def get_employee_performance(self, bearer: str, employee_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Employees/{employee_id}/performance", bearer=bearer)

    # ── Expenses ──────────────────────────────────────────────────

    async def get_expenses(self, bearer: str, *, page: int | None = None, page_size: int | None = None,
                           search: str | None = None, category: str | None = None,
                           from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Expenses", bearer=bearer,
                                   params=self.clean_params({"page": page, "pageSize": page_size, "search": search, "category": category, "from": from_date, "to": to_date}))

    async def create_expense(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Expenses", bearer=bearer, body=payload)

    async def update_expense(self, bearer: str, expense_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Expenses/{expense_id}", bearer=bearer, body=payload)

    async def delete_expense(self, bearer: str, expense_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Expenses/{expense_id}", bearer=bearer)

    async def get_expense_charts(self, bearer: str, *, chart_type: str, from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Expenses/{chart_type}-chart", bearer=bearer,
                                   params=self.clean_params({"from": from_date, "to": to_date}))

    # ── Appointments ──────────────────────────────────────────────

    async def get_appointments(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                               search: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Appointments", bearer=bearer,
                                   params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size, "search": search, "startDate": start_date, "endDate": end_date}))

    async def create_appointment(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Appointments", bearer=bearer, body=payload)

    # ── Dashboard ─────────────────────────────────────────────────

    async def get_dashboard(self, bearer: str) -> dict[str, Any]:
        return await self.request("GET", "/CompanyDashboard", bearer=bearer)

    # ── Service Requests ──────────────────────────────────────────

    async def get_service_requests(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/company/service-requests", bearer=bearer,
                                   params=self.clean_params({"pageIndex": self.normalize_page_index(page_index), "pageSize": page_size, "status": status}))

    async def get_service_request_details(self, bearer: str, request_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/company/service-requests/{request_id}", bearer=bearer)

    async def decline_service_request(self, bearer: str, request_id: int, *, reason: str | None = None) -> dict[str, Any]:
        body = {"reason": reason} if reason else {}
        return await self.request("PUT", f"/company/service-requests/{request_id}/decline", bearer=bearer, body=body)
