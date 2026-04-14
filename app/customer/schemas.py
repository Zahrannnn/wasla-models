"""Pydantic input schemas for Customer Portal tools (27 total).

Each BaseModel is used as ``args_schema`` for a StructuredTool, providing
strict type validation of LLM-generated arguments before they reach
the business logic in operations.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────


class RegisterCustomerInput(BaseModel):
    """Register a new customer account."""
    email: str = Field(description="Valid email address")
    password: str = Field(description="Min 6 chars, must contain at least 1 digit")
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")
    phone_number: str | None = Field(default=None, description="Optional phone number")


class LoginCustomerInput(BaseModel):
    """Authenticate a user."""
    email: str = Field(description="User's email address")
    password: str = Field(description="User's password")
    remember_me: bool = Field(default=False, description="If true, extends refresh token to 30 days")


class RefreshTokenInput(BaseModel):
    """Refresh an access token."""
    refresh_token: str = Field(description="The refresh token from login response")


class LogoutInput(BaseModel):
    """Log out the current session."""
    refresh_token: str = Field(description="The refresh token to revoke")


class LogoutAllInput(BaseModel):
    """Log out from all devices."""

    pass


# ── Company Discovery ─────────────────────────────────────────────


class ListCompaniesInput(BaseModel):
    """Browse and search companies."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 12)")
    search: str | None = Field(default=None, description="Search by company name")
    service_type: str | None = Field(default=None, description="Filter by service type (e.g., 'Cleaning', 'Moving')")
    sort_by: str | None = Field(default=None, description="Sort by: 'rating', 'name', 'newest' (default: 'rating')")


class GetRecommendedCompaniesInput(BaseModel):
    """Get AI-ranked company recommendations."""
    service_type: str | None = Field(default=None, description="Filter by service type")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")


class GetTrendingCompaniesInput(BaseModel):
    """Get trending companies."""
    service_type: str | None = Field(default=None, description="Filter by service type")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")


class GetCompanyDetailsInput(BaseModel):
    """Get company details."""
    company_id: int = Field(description="The company's numeric ID")


class GetCompanyReviewsInput(BaseModel):
    """Get reviews for a company."""
    company_id: int = Field(description="The company's numeric ID")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")
    sort_by: str | None = Field(default=None, description="Sort by: 'newest', 'highest-rated' (default: 'newest')")


# ── Reviews ───────────────────────────────────────────────────────


class SubmitReviewInput(BaseModel):
    """Submit a review for a company."""
    company_id: int = Field(description="The company's numeric ID")
    rating: int = Field(description="Star rating 1-5")
    review_text: str | None = Field(default=None, description="Review text, max 2000 chars (optional)")


class UpdateReviewInput(BaseModel):
    """Update an existing review."""
    company_id: int = Field(description="The company's numeric ID")
    rating: int = Field(description="Updated star rating 1-5")
    review_text: str | None = Field(default=None, description="Updated review text, max 2000 chars")


class DeleteReviewInput(BaseModel):
    """Delete a review."""
    company_id: int = Field(description="The company's numeric ID")


class GetMyReviewsInput(BaseModel):
    """Get all reviews by the authenticated customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page (default: 10)")


# ── Profiles ──────────────────────────────────────────────────────


class GetCustomerProfileInput(BaseModel):
    """Get customer profile."""

    pass


class UpdateCustomerProfileInput(BaseModel):
    """Update customer profile."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Street address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip/Postal code")
    country: str | None = Field(default=None, description="Country")


class GetLeadProfileInput(BaseModel):
    """Get lead profile."""

    pass


class UpdateLeadProfileInput(BaseModel):
    """Update lead profile."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Street address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip/Postal code")
    country: str | None = Field(default=None, description="Country")


class GetDigitalSignatureInput(BaseModel):
    """Get digital signature after password verification."""
    password: str = Field(description="User's current password to verify identity")


# ── Offers ────────────────────────────────────────────────────────


class GetMyOffersInput(BaseModel):
    """Get offers sent to the customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")
    status: str | None = Field(default=None, description="Filter: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'")


class GetOfferDetailsInput(BaseModel):
    """Get offer details."""
    offer_id: int = Field(description="The offer's numeric ID")


class AcceptOfferInput(BaseModel):
    """Accept an offer."""
    offer_id: int = Field(description="The offer's numeric ID")
    digital_signature: str = Field(description="User's digital signature (get via get_digital_signature)")
    payment_method: str = Field(description="Payment method: 'COD' or 'Online'")


class RejectOfferInput(BaseModel):
    """Reject an offer."""
    offer_id: int = Field(description="The offer's numeric ID")
    rejection_reason: str = Field(description="Reason for rejection (max 2000 chars)")


class GetDashboardInput(BaseModel):
    """Get dashboard summary."""

    pass


# ── Service Requests ──────────────────────────────────────────────


class CreateServiceRequestInput(BaseModel):
    """Submit a service inquiry to a company."""
    company_id: int = Field(description="The company's numeric ID")
    service_type: str = Field(description="Type of service (e.g., 'Moving', 'Cleaning')")
    from_street: str | None = Field(default=None, description="Origin street address")
    from_city: str | None = Field(default=None, description="Origin city")
    from_zip_code: str | None = Field(default=None, description="Origin zip code")
    from_country: str | None = Field(default=None, description="Origin country")
    to_street: str | None = Field(default=None, description="Destination street address")
    to_city: str | None = Field(default=None, description="Destination city")
    to_zip_code: str | None = Field(default=None, description="Destination zip code")
    to_country: str | None = Field(default=None, description="Destination country")
    preferred_date: str | None = Field(default=None, description="Preferred service date (YYYY-MM-DD)")
    preferred_time_slot: str | None = Field(default=None, description="Preferred time (e.g., 'Morning 8am-12pm')")
    notes: str | None = Field(default=None, description="Additional notes (max 2000 chars)")


class GetMyServiceRequestsInput(BaseModel):
    """Get service requests by the authenticated customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page (default: 10)")
    status: str | None = Field(default=None, description="Filter: 'Pending', 'InProgress', 'Closed'")


class GetServiceRequestDetailsInput(BaseModel):
    """Get service request details."""
    service_request_id: int = Field(description="The service request's numeric ID")


# ── Analytical Reports ───────────────────────────────────────────


class GenerateMyActivityReportInput(BaseModel):
    """Generate a personal activity report (dashboard, offers, reviews, service requests)."""

    pass
