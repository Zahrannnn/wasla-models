"""Composite report operations — Company Portal.

Each function aggregates multiple API calls into a single structured report,
saving 3-6 LLM tool-call round trips per report.

Functions return a ``_charts`` list so the route handler can send chart
payloads to the frontend for interactive rendering.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.shared.auth import require_bearer

logger = logging.getLogger("wasla.company.reports")


def _safe(result: Any) -> dict:
    """Return result if it's a valid dict, else wrap the error."""
    if isinstance(result, dict):
        return result
    return {"error": "unexpected_response", "raw": str(result)}


def _data_of(result: Any) -> Any:
    """Extract the ``data`` payload from a CRM response, falling back to the raw result."""
    if isinstance(result, dict):
        return result.get("data", result)
    return result


# ── Chart builders ──────────────────────────────────────────────────


def _build_status_chart(
    items: list[dict],
    *,
    status_key: str = "status",
    chart_id: str,
    title: str,
    chart_type: str = "doughnut",
) -> dict | None:
    """Build a status-distribution chart from a list of items."""
    if not items:
        return None
    counts: dict[str, int] = {}
    for item in items:
        s = str(item.get(status_key, "Unknown"))
        counts[s] = counts.get(s, 0) + 1
    return {
        "id": chart_id,
        "chart_type": chart_type,
        "title": title,
        "labels": list(counts.keys()),
        "datasets": [{"label": "Count", "data": list(counts.values())}],
    }


def _build_expense_charts(monthly_resp: Any, category_resp: Any) -> list[dict]:
    """Build chart blocks from CRM expense chart API responses."""
    charts: list[dict] = []
    # Monthly trend — bar chart
    m_data = _data_of(monthly_resp)
    if isinstance(m_data, list) and m_data:
        labels = [str(p.get("month") or p.get("label") or p.get("period") or f"#{i+1}") for i, p in enumerate(m_data)]
        values = [float(p.get("total") or p.get("amount") or p.get("value") or 0) for p in m_data]
        charts.append({
            "id": "expense_monthly",
            "chart_type": "bar",
            "title": "Monthly Expenses",
            "labels": labels,
            "datasets": [{"label": "Amount (EGP)", "data": values}],
        })
    elif isinstance(m_data, dict):
        # Single-object chart format (labels + values already structured)
        charts.append({
            "id": "expense_monthly",
            "chart_type": "bar",
            "title": "Monthly Expenses",
            "labels": m_data.get("labels", []),
            "datasets": [{"label": "Amount (EGP)", "data": m_data.get("data") or m_data.get("values", [])}],
        })

    # Category breakdown — doughnut chart
    c_data = _data_of(category_resp)
    if isinstance(c_data, list) and c_data:
        labels = [str(p.get("category") or p.get("label") or p.get("name") or f"#{i+1}") for i, p in enumerate(c_data)]
        values = [float(p.get("total") or p.get("amount") or p.get("value") or 0) for p in c_data]
        charts.append({
            "id": "expense_category",
            "chart_type": "doughnut",
            "title": "Expenses by Category",
            "labels": labels,
            "datasets": [{"label": "Amount (EGP)", "data": values}],
        })
    elif isinstance(c_data, dict):
        charts.append({
            "id": "expense_category",
            "chart_type": "doughnut",
            "title": "Expenses by Category",
            "labels": c_data.get("labels", []),
            "datasets": [{"label": "Amount (EGP)", "data": c_data.get("data") or c_data.get("values", [])}],
        })

    return charts


def _extract_items(response: Any) -> list[dict]:
    """Pull the item list from a paginated CRM response."""
    if not isinstance(response, dict):
        return []
    data = response.get("data", response)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items") or data.get("data") or data.get("results") or []
    return []


# ── Report functions ────────────────────────────────────────────────


async def generate_business_report(ctx: dict) -> dict:
    """Dashboard KPIs + offers breakdown + tasks summary + expenses overview."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    dashboard, offers, tasks, expenses_monthly, expenses_category = await asyncio.gather(
        client.get_dashboard(t),
        client.get_offers(t, page_size=50),
        client.get_all_tasks(t, page_size=50),
        client.get_expense_charts(t, chart_type="monthly"),
        client.get_expense_charts(t, chart_type="category"),
        return_exceptions=True,
    )

    # Build charts
    charts: list[dict] = _build_expense_charts(expenses_monthly, expenses_category)

    offer_items = _extract_items(offers)
    offer_chart = _build_status_chart(offer_items, chart_id="offers_by_status", title="Offers by Status")
    if offer_chart:
        charts.append(offer_chart)

    task_items = _extract_items(tasks)
    task_chart = _build_status_chart(task_items, chart_id="tasks_by_status", title="Tasks by Status")
    if task_chart:
        charts.append(task_chart)

    return {
        "report_type": "business_overview",
        "dashboard": _safe(dashboard),
        "offers": _safe(offers),
        "tasks": _safe(tasks),
        "expense_trends": {
            "monthly": _safe(expenses_monthly),
            "by_category": _safe(expenses_category),
        },
        "_charts": charts,
    }


async def generate_financial_report(
    ctx: dict,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Expense charts (monthly + category) + recent expense records for a period."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    monthly, category, expenses = await asyncio.gather(
        client.get_expense_charts(t, chart_type="monthly", from_date=date_from, to_date=date_to),
        client.get_expense_charts(t, chart_type="category", from_date=date_from, to_date=date_to),
        client.get_expenses(t, page_size=50, from_date=date_from, to_date=date_to),
        return_exceptions=True,
    )

    charts = _build_expense_charts(monthly, category)

    return {
        "report_type": "financial_analysis",
        "period": {"from": date_from, "to": date_to},
        "monthly_trend": _safe(monthly),
        "category_breakdown": _safe(category),
        "recent_expenses": _safe(expenses),
        "_charts": charts,
    }


async def generate_team_performance_report(ctx: dict) -> dict:
    """All employees + individual performance metrics for each."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    employees_resp = await client.get_employees(t, page_size=50)

    if not isinstance(employees_resp, dict):
        return {"error": "failed_to_fetch_employees", "raw": str(employees_resp)}

    # Extract employee list — handle both paginated and flat responses
    items = employees_resp.get("items") or employees_resp.get("data") or []
    if not isinstance(items, list):
        items = []

    # Fetch performance for each employee concurrently
    async def _get_perf(emp: dict) -> dict:
        emp_id = emp.get("userId") or emp.get("id") or emp.get("employeeId")
        if not emp_id:
            return {**emp, "performance": {"error": "no_employee_id"}}
        try:
            perf = await client.get_employee_performance(t, emp_id)
        except Exception as exc:
            perf = {"error": str(exc)}
        return {**emp, "performance": _safe(perf)}

    enriched = await asyncio.gather(*[_get_perf(e) for e in items])

    # Build charts: tasks completed per employee
    charts: list[dict] = []
    names: list[str] = []
    completed: list[int] = []
    total: list[int] = []
    for emp in enriched:
        name = f"{emp.get('firstName', '')} {emp.get('lastName', '')}".strip() or str(emp.get("userName", "?"))
        perf = emp.get("performance", {})
        perf_data = perf.get("data", perf) if isinstance(perf, dict) else {}
        if not isinstance(perf_data, dict):
            perf_data = {}
        names.append(name)
        completed.append(int(perf_data.get("completedTasks") or perf_data.get("completed") or 0))
        total.append(int(perf_data.get("totalTasks") or perf_data.get("total") or 0))

    if names:
        charts.append({
            "id": "employee_tasks",
            "chart_type": "bar",
            "title": "Employee Task Overview",
            "labels": names,
            "datasets": [
                {"label": "Completed", "data": completed},
                {"label": "Total Assigned", "data": total},
            ],
        })

    return {
        "report_type": "team_performance",
        "total_employees": len(enriched),
        "employees": list(enriched),
        "_charts": charts,
    }


async def generate_pipeline_report(ctx: dict) -> dict:
    """Service requests by status + offers by status = full sales pipeline view."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    sr_all, offers_all = await asyncio.gather(
        client.get_service_requests(t, page_size=50),
        client.get_offers(t, page_size=50),
        return_exceptions=True,
    )

    charts: list[dict] = []

    sr_items = _extract_items(sr_all)
    sr_chart = _build_status_chart(sr_items, chart_id="service_requests_by_status", title="Service Requests by Status", chart_type="doughnut")
    if sr_chart:
        charts.append(sr_chart)

    offer_items = _extract_items(offers_all)
    offer_chart = _build_status_chart(offer_items, chart_id="offers_by_status", title="Offers by Status", chart_type="doughnut")
    if offer_chart:
        charts.append(offer_chart)

    return {
        "report_type": "sales_pipeline",
        "service_requests": _safe(sr_all),
        "offers": _safe(offers_all),
        "_charts": charts,
    }


async def generate_customer_report(ctx: dict) -> dict:
    """Customer list with engagement stats (offer count, task count per customer)."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    customers_resp = await client.get_customers(t, page_size=50)

    if not isinstance(customers_resp, dict):
        return {"error": "failed_to_fetch_customers", "raw": str(customers_resp)}

    items = customers_resp.get("items") or customers_resp.get("data") or []
    if not isinstance(items, list):
        items = []

    # Fetch offer + task counts for each customer concurrently
    async def _enrich(cust: dict) -> dict:
        cid = cust.get("customerId") or cust.get("id")
        if not cid:
            return {**cust, "offers_summary": None, "tasks_summary": None}
        try:
            offers, tasks = await asyncio.gather(
                client.get_customer_offers(t, cid, page_size=1),
                client.get_customer_tasks(t, cid, page_size=1),
            )
        except Exception:
            offers, tasks = {}, {}
        return {
            **cust,
            "offers_summary": _safe(offers),
            "tasks_summary": _safe(tasks),
        }

    enriched = await asyncio.gather(*[_enrich(c) for c in items])

    # Build chart: offers + tasks per customer (top 15)
    charts: list[dict] = []
    sorted_custs = sorted(enriched, key=lambda c: (
        _count_from(c.get("offers_summary")) + _count_from(c.get("tasks_summary"))
    ), reverse=True)[:15]

    if sorted_custs:
        names = []
        offer_counts = []
        task_counts = []
        for c in sorted_custs:
            name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or str(c.get("email", "?"))
            names.append(name)
            offer_counts.append(_count_from(c.get("offers_summary")))
            task_counts.append(_count_from(c.get("tasks_summary")))
        charts.append({
            "id": "customer_engagement",
            "chart_type": "bar",
            "title": "Customer Engagement (Top 15)",
            "labels": names,
            "datasets": [
                {"label": "Offers", "data": offer_counts},
                {"label": "Tasks", "data": task_counts},
            ],
        })

    return {
        "report_type": "customer_engagement",
        "total_customers": len(enriched),
        "customers": list(enriched),
        "_charts": charts,
    }


def _count_from(summary: dict | None) -> int:
    """Extract a total/count from a paginated summary response."""
    if not isinstance(summary, dict):
        return 0
    data = summary.get("data", summary)
    if isinstance(data, dict):
        return int(data.get("totalCount") or data.get("total") or data.get("count") or len(data.get("items") or []))
    if isinstance(data, list):
        return len(data)
    return 0
