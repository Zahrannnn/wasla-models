"""Pydantic input schemas for Company Portal tools (40 total).

Each BaseModel is used as ``args_schema`` for a StructuredTool, providing
strict type validation of LLM-generated arguments before they reach
the business logic in operations.py.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Auth ──────────────────────────────────────────────────────────


class LoginStaffInput(BaseModel):
    """Authenticate a staff member."""
    email: str = Field(description="Staff email address")
    password: str = Field(description="Staff password")


class ChangePasswordInput(BaseModel):
    """Change the current user's password."""
    current_password: str = Field(description="Current password")
    new_password: str = Field(description="New password")
    confirm_password: str = Field(description="Confirm new password")


# ── Customers ─────────────────────────────────────────────────────


class GetCustomersInput(BaseModel):
    """Get paginated customer list."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search by name or email")


class GetCustomerDetailsInput(BaseModel):
    """Get customer details."""
    customer_id: int = Field(description="Customer ID")


class CreateCustomerInput(BaseModel):
    """Create a new customer."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    email: str = Field(description="Email address")
    phone_number: str = Field(description="Phone number")
    address: str = Field(description="Street address")
    city: str = Field(description="City")
    zip_code: str = Field(description="Zip/Postal code")
    country: str = Field(description="Country")
    notes: str = Field(description="Notes about the customer")


class UpdateCustomerInput(BaseModel):
    """Update customer information."""
    customer_id: int = Field(description="Customer ID")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    email: str | None = Field(default=None, description="Email")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip code")
    country: str | None = Field(default=None, description="Country")
    notes: str | None = Field(default=None, description="Notes")


class DeleteCustomerInput(BaseModel):
    """Delete a customer."""
    customer_id: int = Field(description="Customer ID")


class GetCustomerOffersInput(BaseModel):
    """Get offer history for a customer."""
    customer_id: int = Field(description="Customer ID")
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")


class GetCustomerTasksInput(BaseModel):
    """Get task history for a customer."""
    customer_id: int = Field(description="Customer ID")
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")


# ── Offers ────────────────────────────────────────────────────────


class GetOffersInput(BaseModel):
    """Get paginated offers."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")
    search_word: str | None = Field(default=None, description="Search by client name or offer number")
    status: str | None = Field(default=None, description="Filter: Pending, Sent, Accepted, Rejected, Canceled")


class GetOfferDetailsInput(BaseModel):
    """Get offer details."""
    offer_id: int = Field(description="Offer ID")


class CreateOfferInput(BaseModel):
    """Create a new offer."""
    customer_id: int = Field(description="Customer ID (required)")
    service_request_id: int | None = Field(default=None, description="Link to service request (auto-updates to OfferSent)")
    notes_in_offer: str | None = Field(default=None, description="Notes visible to customer")
    notes_not_in_offer: str | None = Field(default=None, description="Internal notes")
    language_code: str | None = Field(default=None, description="e.g. 'en', 'de'")
    email_to_customer: bool | None = Field(default=None, description="Send email notification")
    locations: list[Any] | None = Field(default=None, description="List of locations (From, To)")
    services: dict[str, Any] | None = Field(default=None, description="Service details (Moving, Cleaning, Packing, etc.)")


class UpdateOfferInput(BaseModel):
    """Update an offer."""
    offer_id: int = Field(description="Offer ID")
    customer_id: int | None = Field(default=None, description="Customer ID")
    notes_in_offer: str | None = Field(default=None, description="Notes visible to customer")
    notes_not_in_offer: str | None = Field(default=None, description="Internal notes")
    locations: list[Any] | None = Field(default=None, description="Locations")
    services: dict[str, Any] | None = Field(default=None, description="Services")


class UpdateOfferStatusInput(BaseModel):
    """Change offer status."""
    offer_id: int = Field(description="Offer ID")
    status: str = Field(description="New status: Pending, Sent, Accepted, Rejected, Canceled")


class DeleteOfferInput(BaseModel):
    """Delete an offer."""
    offer_id: int = Field(description="Offer ID")


# ── Tasks ─────────────────────────────────────────────────────────


class GetAllTasksInput(BaseModel):
    """Get all company tasks."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")


class GetMyTasksInput(BaseModel):
    """Get tasks assigned to the current employee."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")


class GetTaskDetailsInput(BaseModel):
    """Get task details."""
    task_id: int = Field(description="Task ID")


class CreateTaskInput(BaseModel):
    """Create a new task."""
    assigned_to_user_id: int = Field(description="Employee ID to assign to")
    task_title: str = Field(description="Task title")
    customer_id: int | None = Field(default=None, description="Link to customer")
    description: str | None = Field(default=None, description="Task description")
    priority: str | None = Field(default=None, description="Priority: Low, Medium, High, Urgent")
    due_date: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    notes: str | None = Field(default=None, description="Additional notes")


class UpdateTaskInput(BaseModel):
    """Update a task."""
    task_item_id: int = Field(description="Task item ID")
    assigned_to_user_id: int | None = Field(default=None, description="Reassign to employee ID")
    customer_id: int | None = Field(default=None, description="Customer ID")
    task_title: str | None = Field(default=None, description="Task title")
    description: str | None = Field(default=None, description="Description")
    priority: str | None = Field(default=None, description="Priority")
    due_date: str | None = Field(default=None, description="Due date")
    notes: str | None = Field(default=None, description="Notes")


class StartTaskInput(BaseModel):
    """Start a task."""
    task_id: int = Field(description="Task ID")


class CompleteTaskInput(BaseModel):
    """Complete a task."""
    task_id: int = Field(description="Task ID")


class ReassignTaskInput(BaseModel):
    """Reassign a task."""
    task_id: int = Field(description="Task ID")
    new_assignee_id: int = Field(description="New employee ID")
    reason: str = Field(description="Reason for reassignment")


class SearchEmployeesInput(BaseModel):
    """Search employees by name."""
    search_name: str = Field(description="Name to search for")


class SearchCustomersInput(BaseModel):
    """Search customers by name."""
    search_name: str = Field(description="Name to search for")


# ── Employees ─────────────────────────────────────────────────────


class GetEmployeesInput(BaseModel):
    """Get paginated employee list."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search by name or email")


class GetEmployeeDetailsInput(BaseModel):
    """Get employee details."""
    user_id: int = Field(description="Employee user ID")


class CreateEmployeeInput(BaseModel):
    """Create a new employee."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    email: str = Field(description="Email")
    user_name: str = Field(description="Username")
    password: str = Field(description="Password")
    is_active: bool | None = Field(default=None, description="Active status (default: true)")
    permission_ids: list[int] | None = Field(default=None, description="Permission IDs to assign")


class UpdateEmployeeInput(BaseModel):
    """Update an employee."""
    user_id: int = Field(description="Employee user ID")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    email: str | None = Field(default=None, description="Email")
    user_name: str | None = Field(default=None, description="Username")
    new_password: str | None = Field(default=None, description="New password")
    is_active: bool | None = Field(default=None, description="Active status")
    permission_ids: list[int] | None = Field(default=None, description="Permission IDs")


class DeleteEmployeeInput(BaseModel):
    """Delete an employee."""
    user_id: int = Field(description="Employee user ID")


class GetEmployeePerformanceInput(BaseModel):
    """Get employee performance report."""
    employee_id: int = Field(description="Employee ID")


# ── Expenses ──────────────────────────────────────────────────────


class GetExpensesInput(BaseModel):
    """Get paginated expenses."""

    model_config = ConfigDict(populate_by_name=True)

    page: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search expenses")
    category: str | None = Field(default=None, description="Filter by category")
    date_from: str | None = Field(default=None, alias="from", description="Start date YYYY-MM-DD")
    date_to: str | None = Field(default=None, alias="to", description="End date YYYY-MM-DD")


class CreateExpenseInput(BaseModel):
    """Record a new expense."""
    description: str = Field(description="Expense description")
    amount_egp: float = Field(description="Amount in EGP")
    expense_date: str = Field(description="Date (YYYY-MM-DD)")
    category: str = Field(description="Expense category")


class UpdateExpenseInput(BaseModel):
    """Update an expense."""
    expense_id: int = Field(description="Expense ID")
    description: str | None = Field(default=None, description="Description")
    amount_egp: float | None = Field(default=None, description="Amount in EGP")
    expense_date: str | None = Field(default=None, description="Date")
    category: str | None = Field(default=None, description="Category")


class DeleteExpenseInput(BaseModel):
    """Delete an expense."""
    expense_id: int = Field(description="Expense ID")


class GetExpenseChartsInput(BaseModel):
    """Get expense chart data."""

    model_config = ConfigDict(populate_by_name=True)

    chart_type: str = Field(description="Chart type: 'monthly' or 'category'")
    date_from: str | None = Field(default=None, alias="from", description="Start date (optional)")
    date_to: str | None = Field(default=None, alias="to", description="End date (optional)")


# ── Appointments ──────────────────────────────────────────────────


class GetAppointmentsInput(BaseModel):
    """Get paginated appointments."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Filter by customer name or location")
    start_date: str | None = Field(default=None, description="Filter from date (ISO 8601)")
    end_date: str | None = Field(default=None, description="Filter to date (ISO 8601)")


class CreateAppointmentInput(BaseModel):
    """Schedule a new appointment."""
    customer_id: int = Field(description="Customer ID")
    scheduled_at: str = Field(description="UTC datetime ISO 8601")
    location: str | None = Field(default=None, description="Site address")
    notes: str | None = Field(default=None, description="Notes")
    language_code: str | None = Field(default=None, description="Language: en, de, fr, it")


# ── Dashboard ─────────────────────────────────────────────────────


class GetDashboardInput(BaseModel):
    """Get company dashboard."""

    pass


# ── Service Requests ──────────────────────────────────────────────


class GetServiceRequestsInput(BaseModel):
    """Get incoming service requests."""
    page_index: int | None = Field(default=None, description="1-based page index (first page is 1; 0 is treated as 1).")
    page_size: int | None = Field(default=None, description="Items per page")
    status: str | None = Field(default=None, description="Filter: New, Viewed, OfferSent, Declined")


class GetServiceRequestDetailsInput(BaseModel):
    """Get service request details."""
    request_id: int = Field(description="Service request ID")


class DeclineServiceRequestInput(BaseModel):
    """Decline a service request."""
    request_id: int = Field(description="Service request ID")
    reason: str | None = Field(default=None, description="Reason for declining (optional)")


# ── Analytical Reports ───────────────────────────────────────────


class GenerateBusinessReportInput(BaseModel):
    """Generate a comprehensive business overview report."""

    pass


class GenerateFinancialReportInput(BaseModel):
    """Generate a financial analysis report with expense trends."""

    model_config = ConfigDict(populate_by_name=True)

    date_from: str | None = Field(default=None, alias="from", description="Start date YYYY-MM-DD (optional)")
    date_to: str | None = Field(default=None, alias="to", description="End date YYYY-MM-DD (optional)")


class GenerateTeamPerformanceReportInput(BaseModel):
    """Generate a team performance report with per-employee metrics."""

    pass


class GeneratePipelineReportInput(BaseModel):
    """Generate a sales pipeline report (service requests + offers)."""

    pass


class GenerateCustomerReportInput(BaseModel):
    """Generate a customer engagement report with per-customer stats."""

    pass
