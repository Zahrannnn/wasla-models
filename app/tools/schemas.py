"""Tool definitions — JSON schemas for the LLM (Customer Portal API)."""

from __future__ import annotations

from typing import Any


def _tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    params: dict[str, Any] = {"type": "object", "properties": properties or {}, "required": required or []}
    return {"type": "function", "function": {"name": name, "description": description, "parameters": params}}


TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _tool("register_customer",
          "Register a new customer account. Creates a Lead record and generates a Digital Signature automatically.",
          {"email": {"type": "string", "description": "Valid email address"},
           "password": {"type": "string", "description": "Min 6 chars, must contain at least 1 digit"},
           "first_name": {"type": "string", "description": "User's first name"},
           "last_name": {"type": "string", "description": "User's last name"},
           "phone_number": {"type": "string", "description": "Optional phone number"}},
          ["email", "password", "first_name", "last_name"]),

    _tool("login_customer",
          "Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type.",
          {"email": {"type": "string", "description": "User's email address"},
           "password": {"type": "string", "description": "User's password"},
           "remember_me": {"type": "boolean", "description": "If true, extends refresh token to 30 days"}},
          ["email", "password"]),

    _tool("refresh_token",
          "Get a new access token using refresh token. Each refresh token can only be used once (token rotation).",
          {"refresh_token": {"type": "string", "description": "The refresh token from login response"}},
          ["refresh_token"]),

    _tool("logout",
          "Log out the current session by revoking the refresh token.",
          {"refresh_token": {"type": "string", "description": "The refresh token to revoke"}},
          ["refresh_token"]),

    _tool("logout_all",
          "Log out from ALL devices by revoking all refresh tokens. Requires authentication."),

    # ── Company Discovery ─────────────────────────────────────────
    _tool("list_companies",
          "Browse and search companies on the platform. No authentication required.",
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 12)"},
           "search": {"type": "string", "description": "Search by company name"},
           "service_type": {"type": "string", "description": "Filter by service type (e.g., 'Cleaning', 'Moving')"},
           "sort_by": {"type": "string", "description": "Sort by: 'rating', 'name', 'newest' (default: 'rating')"}}),

    _tool("get_recommended_companies",
          "Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required. Best for 'Find me the best company' requests.",
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_trending_companies",
          "Get companies with improving recent reviews (last 90 days). Great for 'Hot new companies' or 'Companies on the rise' requests.",
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_company_details",
          "Get detailed information about a specific company including contact info, services offered. No authentication required.",
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_company_reviews",
          "Get paginated customer reviews for a company. No authentication required.",
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "sort_by": {"type": "string", "description": "Sort by: 'newest', 'highest-rated' (default: 'newest')"}},
          ["company_id"]),

    # ── Reviews ───────────────────────────────────────────────────
    _tool("submit_review",
          "Submit a new review for a company. Requires Customer authentication. Only one review per customer per company.",
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Star rating 1-5"},
           "review_text": {"type": "string", "description": "Review text, max 2000 chars (optional)"}},
          ["company_id", "rating"]),

    _tool("update_review",
          "Update an existing review. Only the customer who created the review can update it.",
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Updated star rating 1-5"},
           "review_text": {"type": "string", "description": "Updated review text, max 2000 chars"}},
          ["company_id", "rating"]),

    _tool("delete_review",
          "Delete the customer's own review for a company. This action cannot be undone.",
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_my_reviews",
          "Get all reviews written by the authenticated customer across all companies.",
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"}}),

    # ── Profiles ──────────────────────────────────────────────────
    _tool("get_customer_profile",
          "Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId)."),

    _tool("update_customer_profile",
          "Update the authenticated customer's profile. Email cannot be changed.",
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_lead_profile",
          "Get the lead's profile including list of connected companies. Use for users who registered but haven't been accepted by any company yet."),

    _tool("update_lead_profile",
          "Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_digital_signature",
          "Get the user's digital signature after password verification. Required to accept offers. IMPORTANT: Requires password re-verification.",
          {"password": {"type": "string", "description": "User's current password to verify identity"}},
          ["password"]),

    # ── Offers ────────────────────────────────────────────────────
    _tool("get_my_offers",
          "Get all offers (quotes) sent to the customer by companies.",
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'"}}),

    _tool("get_offer_details",
          "Get detailed information about a specific offer including service line items and pricing breakdown.",
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"}},
          ["offer_id"]),

    _tool("accept_offer",
          "Accept an offer. Requires digital signature. Choose COD (Cash on Delivery) or Online (Stripe) payment. For online, returns a Stripe checkout URL.",
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "digital_signature": {"type": "string", "description": "User's digital signature (get via get_digital_signature)"},
           "payment_method": {"type": "string", "description": "Payment method: 'COD' or 'Online'"}},
          ["offer_id", "digital_signature", "payment_method"]),

    _tool("reject_offer",
          "Reject an offer. Must provide a reason for rejection.",
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "rejection_reason": {"type": "string", "description": "Reason for rejection (max 2000 chars)"}},
          ["offer_id", "rejection_reason"]),

    _tool("get_dashboard",
          "Get dashboard summary showing total offers, offers by status, total reviews, and recent activity."),

    # ── Service Requests ──────────────────────────────────────────
    _tool("create_service_request",
          "Submit a service inquiry to a company. Can be done by both Lead and Customer users.",
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
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'InProgress', 'Closed'"}}),

    _tool("get_service_request_details",
          "Get detailed information about a specific service request.",
          {"service_request_id": {"type": "integer", "description": "The service request's numeric ID"}},
          ["service_request_id"]),
]


def tools_to_react_description() -> str:
    """Convert tool definitions to human-readable format for ReAct prompts."""
    lines = []
    for tool in TOOLS:
        func = tool["function"]
        name = func["name"]
        desc = func["description"]
        params = func.get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])
        param_strs = []
        for pname, pinfo in properties.items():
            pdesc = pinfo.get("description", "")
            req = " (required)" if pname in required else " (optional)"
            param_strs.append(f"    - {pname}{req}: {pdesc}")
        pblock = "\n".join(param_strs) if param_strs else "    No parameters"
        lines.append(f"- {name}: {desc}\n{pblock}")
    return "\n\n".join(lines)
