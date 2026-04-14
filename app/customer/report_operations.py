"""Composite report operations — Customer Portal.

Aggregates multiple API calls into a single structured activity report.
Includes ``_charts`` for interactive frontend rendering.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.shared.auth import require_bearer


def _safe(result: Any) -> dict:
    if isinstance(result, dict):
        return result
    return {"error": "unexpected_response", "raw": str(result)}


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


async def generate_my_activity_report(ctx: dict) -> dict:
    """Dashboard + offers + reviews + service requests in one call."""
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t

    client = ctx["client"]
    dashboard, offers, reviews, service_requests = await asyncio.gather(
        client.get_dashboard(t),
        client.get_my_offers(t, page_size=50),
        client.get_my_reviews(t, page_size=50),
        client.get_my_service_requests(t, page_size=50),
        return_exceptions=True,
    )

    # Build charts from the response data
    charts: list[dict] = []

    offer_items = _extract_items(offers)
    offer_chart = _build_status_chart(offer_items, chart_id="my_offers_by_status", title="My Offers by Status")
    if offer_chart:
        charts.append(offer_chart)

    sr_items = _extract_items(service_requests)
    sr_chart = _build_status_chart(sr_items, chart_id="my_requests_by_status", title="My Service Requests by Status")
    if sr_chart:
        charts.append(sr_chart)

    # Reviews rating distribution
    review_items = _extract_items(reviews)
    if review_items:
        rating_counts: dict[str, int] = {}
        for r in review_items:
            stars = str(r.get("rating") or r.get("stars") or "?")
            label = f"{stars} star{'s' if stars != '1' else ''}"
            rating_counts[label] = rating_counts.get(label, 0) + 1
        if rating_counts:
            charts.append({
                "id": "my_reviews_by_rating",
                "chart_type": "pie",
                "title": "My Reviews by Rating",
                "labels": list(rating_counts.keys()),
                "datasets": [{"label": "Count", "data": list(rating_counts.values())}],
            })

    return {
        "report_type": "my_activity",
        "dashboard": _safe(dashboard),
        "offers": _safe(offers),
        "reviews": _safe(reviews),
        "service_requests": _safe(service_requests),
        "_charts": charts,
    }
