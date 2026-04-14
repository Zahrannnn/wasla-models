"""Customer Portal tools — LangChain StructuredTool wrappers.

Each tool wraps an unchanged function from operations.py using:
- Pydantic args_schema for LLM input validation
- InjectedState for bearer_token (from LangGraph state)
- RunnableConfig for HTTP client (non-serializable, not in state)
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from app.shared.auth import resolve_tool_bearer
from app.shared.graph_request_context import graph_crm_client_get
from app.shared.langgraph_tool_node import InjectedState

from app.customer import operations as ops
from app.customer import report_operations as reports
from app.customer.schemas import (
    AcceptOfferInput,
    CreateServiceRequestInput,
    DeleteReviewInput,
    GenerateMyActivityReportInput,
    GetCompanyDetailsInput,
    GetCompanyReviewsInput,
    GetCustomerProfileInput,
    GetDashboardInput,
    GetDigitalSignatureInput,
    GetLeadProfileInput,
    GetMyOffersInput,
    GetMyReviewsInput,
    GetMyServiceRequestsInput,
    GetOfferDetailsInput,
    GetRecommendedCompaniesInput,
    GetServiceRequestDetailsInput,
    GetTrendingCompaniesInput,
    ListCompaniesInput,
    LoginCustomerInput,
    LogoutAllInput,
    LogoutInput,
    RefreshTokenInput,
    RegisterCustomerInput,
    RejectOfferInput,
    SubmitReviewInput,
    UpdateCustomerProfileInput,
    UpdateLeadProfileInput,
    UpdateReviewInput,
)

logger = logging.getLogger("wasla.customer.tools")


def _build_ctx(
    bearer_token: str | None,
    config: RunnableConfig | None,
) -> dict[str, Any]:
    """Build the legacy ctx dict from LangGraph state + ``configurable`` + request context."""
    client = (config or {}).get("configurable", {}).get("client")
    if client is None:
        client = graph_crm_client_get()
    return {"bearer_token": resolve_tool_bearer(bearer_token, config), "client": client}


def _dump(obj: Any) -> str:
    """JSON-serialize with Arabic character support."""
    return json.dumps(obj, ensure_ascii=False)


def _make_wrapper(op_func):
    """Create an async wrapper that bridges InjectedState/RunnableConfig → ctx."""
    async def wrapper(
        bearer_token: Annotated[str | None, InjectedState("bearer_token")] = None,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> str:
        ctx = _build_ctx(bearer_token, config)
        result = await op_func(ctx, **kwargs)
        return _dump(result)

    return wrapper


def _make_customer_tools() -> list[StructuredTool]:
    """Build all 27 customer portal LangChain tools."""
    return [
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.register_customer),
            name="register_customer",
            description="Register a new customer account. Creates a Lead record and generates a Digital Signature automatically.",
            args_schema=RegisterCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.login_customer),
            name="login_customer",
            description="Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type.",
            args_schema=LoginCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.refresh_token),
            name="refresh_token",
            description="Get a new access token using refresh token. Each refresh token can only be used once (token rotation).",
            args_schema=RefreshTokenInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.logout),
            name="logout",
            description="Log out the current session by revoking the refresh token.",
            args_schema=LogoutInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.logout_all),
            name="logout_all",
            description="Log out from ALL devices by revoking all refresh tokens. Requires authentication.",
            args_schema=LogoutAllInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.list_companies),
            name="list_companies",
            description="Browse and search companies on the platform. No authentication required.",
            args_schema=ListCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_recommended_companies),
            name="get_recommended_companies",
            description="Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required.",
            args_schema=GetRecommendedCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_trending_companies),
            name="get_trending_companies",
            description="Get companies with improving recent reviews (last 90 days).",
            args_schema=GetTrendingCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_company_details),
            name="get_company_details",
            description="Get detailed information about a specific company including contact info, services offered. No authentication required.",
            args_schema=GetCompanyDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_company_reviews),
            name="get_company_reviews",
            description="Get paginated customer reviews for a company. No authentication required.",
            args_schema=GetCompanyReviewsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.submit_review),
            name="submit_review",
            description="Submit a new review for a company. Requires Customer authentication. Only one review per customer per company.",
            args_schema=SubmitReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_review),
            name="update_review",
            description="Update an existing review. Only the customer who created the review can update it.",
            args_schema=UpdateReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_review),
            name="delete_review",
            description="Delete the customer's own review for a company. This action cannot be undone.",
            args_schema=DeleteReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_reviews),
            name="get_my_reviews",
            description="Get all reviews written by the authenticated customer across all companies.",
            args_schema=GetMyReviewsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_profile),
            name="get_customer_profile",
            description="Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId).",
            args_schema=GetCustomerProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_customer_profile),
            name="update_customer_profile",
            description="Update the authenticated customer's profile. Email cannot be changed.",
            args_schema=UpdateCustomerProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_lead_profile),
            name="get_lead_profile",
            description="Get the lead's profile including list of connected companies.",
            args_schema=GetLeadProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_lead_profile),
            name="update_lead_profile",
            description="Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
            args_schema=UpdateLeadProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_digital_signature),
            name="get_digital_signature",
            description="Get the user's digital signature after password verification. Required to accept offers.",
            args_schema=GetDigitalSignatureInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_offers),
            name="get_my_offers",
            description="Get all offers (quotes) sent to the customer by companies.",
            args_schema=GetMyOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offer_details),
            name="get_offer_details",
            description="Get detailed information about a specific offer including service line items and pricing breakdown.",
            args_schema=GetOfferDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.accept_offer),
            name="accept_offer",
            description="Accept an offer. Requires digital signature. Choose COD (Cash on Delivery) or Online (Stripe) payment.",
            args_schema=AcceptOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.reject_offer),
            name="reject_offer",
            description="Reject an offer. Must provide a reason for rejection.",
            args_schema=RejectOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_dashboard),
            name="get_dashboard",
            description="Get dashboard summary showing total offers, offers by status, total reviews, and recent activity.",
            args_schema=GetDashboardInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_service_request),
            name="create_service_request",
            description="Submit a service inquiry to a company. Can be done by both Lead and Customer users.",
            args_schema=CreateServiceRequestInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_service_requests),
            name="get_my_service_requests",
            description="Get all service requests submitted by the authenticated customer.",
            args_schema=GetMyServiceRequestsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_request_details),
            name="get_service_request_details",
            description="Get detailed information about a specific service request.",
            args_schema=GetServiceRequestDetailsInput,
        ),

        # ── Analytical Reports ───────────────────────────────────
        StructuredTool.from_function(
            coroutine=_make_wrapper(reports.generate_my_activity_report),
            name="generate_my_activity_report",
            description="Generate a personal activity report: dashboard summary, all offers, reviews, and service requests in one view. Use when the user asks for an overview of their activity, a summary of their account, or 'show me everything'.",
            args_schema=GenerateMyActivityReportInput,
        ),
    ]


TOOLS = _make_customer_tools()
