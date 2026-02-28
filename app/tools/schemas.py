"""
Tool definitions — JSON schemas for the LLM.

Each entry follows the OpenAI / HF-compatible function-calling format.
Add new tools here and then wire them in ``operations.py`` + ``registry.py``.
"""

from __future__ import annotations

from typing import Any

TOOLS: list[dict[str, Any]] = [
    # ── Read operations ───────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_customer_list",
            "description": "Fetches a list of customers for the company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of customers to return.",
                    },
                },
                "required": ["limit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_details",
            "description": "Fetches detailed information about a single customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The unique identifier of the customer.",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    # ── Search / Navigate ─────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Searches the product catalog by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or phrase.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional product category filter.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ── Write operations ──────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Creates a new order for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer placing the order.",
                    },
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product IDs to include in the order.",
                    },
                },
                "required": ["customer_id", "product_ids"],
            },
        },
    },
]
