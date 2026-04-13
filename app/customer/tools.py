"""Customer Portal tools — schemas, registry, and executor merged."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.customer import operations as ops

logger = logging.getLogger("wasla.customer.tools")


def _tool(name: str, description: str, handler, properties: dict | None = None, required: list[str] | None = None) -> dict:
    params: dict[str, Any] = {"type": "object", "properties": properties or {}, "required": required or []}
    return {"name": name, "description": description, "parameters": params, "handler": handler}


TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _tool("register_customer",
          "Register a new customer account. Creates a Lead record and generates a Digital Signature automatically.",
          ops.register_customer,
          {"email": {"type": "string", "description": "Valid email address"},
           "password": {"type": "string", "description": "Min 6 chars, must contain at least 1 digit"},
           "first_name": {"type": "string", "description": "User's first name"},
           "last_name": {"type": "string", "description": "User's last name"},
           "phone_number": {"type": "string", "description": "Optional phone number"}},
          ["email", "password", "first_name", "last_name"]),

    _tool("login_customer",
          "Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type.",
          ops.login_customer,
          {"email": {"type": "string", "description": "User's email address"},
           "password": {"type": "string", "description": "User's password"},
           "remember_me": {"type": "boolean", "description": "If true, extends refresh token to 30 days"}},
          ["email", "password"]),

    _tool("refresh_token",
          "Get a new access token using refresh token. Each refresh token can only be used once (token rotation).",
          ops.refresh_token,
          {"refresh_token": {"type": "string", "description": "The refresh token from login response"}},
          ["refresh_token"]),

    _tool("logout",
          "Log out the current session by revoking the refresh token.",
          ops.logout,
          {"refresh_token": {"type": "string", "description": "The refresh token to revoke"}},
          ["refresh_token"]),

    _tool("logout_all",
          "Log out from ALL devices by revoking all refresh tokens. Requires authentication.",
          ops.logout_all),

    # ── Company Discovery ─────────────────────────────────────────
    _tool("list_companies",
          "Browse and search companies on the platform. No authentication required.",
          ops.list_companies,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 12)"},
           "search": {"type": "string", "description": "Search by company name"},
           "service_type": {"type": "string", "description": "Filter by service type (e.g., 'Cleaning', 'Moving')"},
           "sort_by": {"type": "string", "description": "Sort by: 'rating', 'name', 'newest' (default: 'rating')"}}),

    _tool("get_recommended_companies",
          "Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required.",
          ops.get_recommended_companies,
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_trending_companies",
          "Get companies with improving recent reviews (last 90 days).",
          ops.get_trending_companies,
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_company_details",
          "Get detailed information about a specific company including contact info, services offered. No authentication required.",
          ops.get_company_details,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_company_reviews",
          "Get paginated customer reviews for a company. No authentication required.",
          ops.get_company_reviews,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "sort_by": {"type": "string", "description": "Sort by: 'newest', 'highest-rated' (default: 'newest')"}},
          ["company_id"]),

    # ── Reviews ───────────────────────────────────────────────────
    _tool("submit_review",
          "Submit a new review for a company. Requires Customer authentication. Only one review per customer per company.",
          ops.submit_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Star rating 1-5"},
           "review_text": {"type": "string", "description": "Review text, max 2000 chars (optional)"}},
          ["company_id", "rating"]),

    _tool("update_review",
          "Update an existing review. Only the customer who created the review can update it.",
          ops.update_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Updated star rating 1-5"},
           "review_text": {"type": "string", "description": "Updated review text, max 2000 chars"}},
          ["company_id", "rating"]),

    _tool("delete_review",
          "Delete the customer's own review for a company. This action cannot be undone.",
          ops.delete_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_my_reviews",
          "Get all reviews written by the authenticated customer across all companies.",
          ops.get_my_reviews,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"}}),

    # ── Profiles ──────────────────────────────────────────────────
    _tool("get_customer_profile",
          "Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId).",
          ops.get_customer_profile),

    _tool("update_customer_profile",
          "Update the authenticated customer's profile. Email cannot be changed.",
          ops.update_customer_profile,
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_lead_profile",
          "Get the lead's profile including list of connected companies.",
          ops.get_lead_profile),

    _tool("update_lead_profile",
          "Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
          ops.update_lead_profile,
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_digital_signature",
          "Get the user's digital signature after password verification. Required to accept offers.",
          ops.get_digital_signature,
          {"password": {"type": "string", "description": "User's current password to verify identity"}},
          ["password"]),

    # ── Offers ────────────────────────────────────────────────────
    _tool("get_my_offers",
          "Get all offers (quotes) sent to the customer by companies.",
          ops.get_my_offers,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'"}}),

    _tool("get_offer_details",
          "Get detailed information about a specific offer including service line items and pricing breakdown.",
          ops.get_offer_details,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"}},
          ["offer_id"]),

    _tool("accept_offer",
          "Accept an offer. Requires digital signature. Choose COD (Cash on Delivery) or Online (Stripe) payment.",
          ops.accept_offer,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "digital_signature": {"type": "string", "description": "User's digital signature (get via get_digital_signature)"},
           "payment_method": {"type": "string", "description": "Payment method: 'COD' or 'Online'"}},
          ["offer_id", "digital_signature", "payment_method"]),

    _tool("reject_offer",
          "Reject an offer. Must provide a reason for rejection.",
          ops.reject_offer,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "rejection_reason": {"type": "string", "description": "Reason for rejection (max 2000 chars)"}},
          ["offer_id", "rejection_reason"]),

    _tool("get_dashboard",
          "Get dashboard summary showing total offers, offers by status, total reviews, and recent activity.",
          ops.get_dashboard),

    # ── Service Requests ──────────────────────────────────────────
    _tool("create_service_request",
          "Submit a service inquiry to a company. Can be done by both Lead and Customer users.",
          ops.create_service_request,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "service_type": {"type": "string", "description": "Type of service (e.g., 'Moving', 'Cleaning')"},
           "from_street": {"type": "string", "description": "Origin street address"},
           "from_city": {"type": "string", "description": "Origin city"},
           "from_zip_code": {"type": "string", "description": "Origin zip code"},
           "from_country": {"type": "string", "description": "Origin country"},
           "to_street": {"type": "string", "description": "Destination street address"},
           "to_city": {"type": "string", "description": "Destination city"},
           "to_zip_code": {"type": "string", "description": "Destination zip code"},
           "to_country": {"type": "string", "description": "Destination country"},
           "preferred_date": {"type": "string", "description": "Preferred service date (YYYY-MM-DD)"},
           "preferred_time_slot": {"type": "string", "description": "Preferred time (e.g., 'Morning 8am-12pm')"},
           "notes": {"type": "string", "description": "Additional notes (max 2000 chars)"}},
          ["company_id", "service_type"]),

    _tool("get_my_service_requests",
          "Get all service requests submitted by the authenticated customer.",
          ops.get_my_service_requests,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'InProgress', 'Closed'"}}),

    _tool("get_service_request_details",
          "Get detailed information about a specific service request.",
          ops.get_service_request_details,
          {"service_request_id": {"type": "integer", "description": "The service request's numeric ID"}},
          ["service_request_id"]),
]

# ── Registry ──────────────────────────────────────────────────────

_REGISTRY = {t["name"]: t["handler"] for t in TOOLS}


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
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    func = _REGISTRY.get(tool_name)
    if func is None:
        logger.warning("Unknown tool requested: %s", tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Tool %s raised an error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
