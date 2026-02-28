"""
Tool operations — the actual Python functions (Read, Write, Navigate).

Every function receives ``company_id`` as its first positional arg
so tools are always scoped to the requesting tenant.

Replace the stub bodies with real DB / API calls.
"""

from __future__ import annotations


# ── Read operations ───────────────────────────────────────────────

async def get_customer_list(company_id: str, *, limit: int = 10) -> dict:
    """Fetch a paginated customer list.  *Stub — replace with DB query.*"""
    return {
        "status": "success",
        "company_id": company_id,
        "customers": [
            {"id": f"cust_{i}", "name": f"Customer {i}"}
            for i in range(1, limit + 1)
        ],
    }


async def get_customer_details(company_id: str, *, customer_id: str) -> dict:
    """Fetch one customer's details.  *Stub.*"""
    return {
        "status": "success",
        "company_id": company_id,
        "customer": {
            "id": customer_id,
            "name": "Acme Corp",
            "email": "contact@acme.example",
            "plan": "enterprise",
        },
    }


# ── Navigate / Search ────────────────────────────────────────────

async def search_products(
    company_id: str,
    *,
    query: str,
    category: str | None = None,
) -> dict:
    """Search the product catalog.  *Stub.*"""
    return {
        "status": "success",
        "query": query,
        "category": category,
        "results": [
            {"id": "prod_1", "name": f"Widget matching '{query}'", "price": 9.99},
        ],
    }


# ── Write operations ─────────────────────────────────────────────

async def create_order(
    company_id: str,
    *,
    customer_id: str,
    product_ids: list[str],
) -> dict:
    """Place a new order.  *Stub.*"""
    return {
        "status": "success",
        "order_id": "order_abc123",
        "customer_id": customer_id,
        "items": product_ids,
    }
