"""Company Portal tools — LangChain StructuredTool wrappers.

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

from app.company import operations as ops
from app.company import report_operations as reports
from app.company.schemas import (
    ChangePasswordInput,
    CreateAppointmentInput,
    CreateCustomerInput,
    CreateEmployeeInput,
    CreateExpenseInput,
    CreateOfferInput,
    CreateTaskInput,
    CompleteTaskInput,
    DeclineServiceRequestInput,
    DeleteCustomerInput,
    DeleteEmployeeInput,
    DeleteExpenseInput,
    DeleteOfferInput,
    GenerateBusinessReportInput,
    GenerateCustomerReportInput,
    GenerateFinancialReportInput,
    GeneratePipelineReportInput,
    GenerateTeamPerformanceReportInput,
    GetAllTasksInput,
    GetAppointmentsInput,
    GetCustomerDetailsInput,
    GetCustomerOffersInput,
    GetCustomerTasksInput,
    GetCustomersInput,
    GetDashboardInput,
    GetEmployeeDetailsInput,
    GetEmployeePerformanceInput,
    GetEmployeesInput,
    GetExpenseChartsInput,
    GetExpensesInput,
    GetMyTasksInput,
    GetOfferDetailsInput,
    GetOffersInput,
    GetServiceRequestDetailsInput,
    GetServiceRequestsInput,
    GetTaskDetailsInput,
    LoginStaffInput,
    ReassignTaskInput,
    SearchCustomersInput,
    SearchEmployeesInput,
    StartTaskInput,
    UpdateCustomerInput,
    UpdateEmployeeInput,
    UpdateExpenseInput,
    UpdateOfferInput,
    UpdateOfferStatusInput,
    UpdateTaskInput,
)

logger = logging.getLogger("wasla.company.tools")


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


def _make_expense_wrapper(op_func):
    """Remap date_from/date_to to ``from``/``to`` for operations kwargs."""
    async def wrapper(
        bearer_token: Annotated[str | None, InjectedState("bearer_token")] = None,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> str:
        ctx = _build_ctx(bearer_token, config)
        if "date_from" in kwargs:
            kwargs["from"] = kwargs.pop("date_from")
        if "date_to" in kwargs:
            kwargs["to"] = kwargs.pop("date_to")
        result = await op_func(ctx, **kwargs)
        return _dump(result)

    return wrapper


def _make_company_tools() -> list[StructuredTool]:
    """Build all 40 company portal LangChain tools."""
    return [
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.login_staff),
            name="login_staff",
            description="Authenticate a company staff member (Manager or Employee). Returns JWT with company ID, role, and permissions.",
            args_schema=LoginStaffInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.change_password),
            name="change_password",
            description="Change the current user's password. Requires authentication.",
            args_schema=ChangePasswordInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customers),
            name="get_customers",
            description="Get paginated list of customers. Requires can_edit_customers.",
            args_schema=GetCustomersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_details),
            name="get_customer_details",
            description="Get detailed customer info including offer count, task count, total profit. Requires can_edit_customers.",
            args_schema=GetCustomerDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_customer),
            name="create_customer",
            description="Create a new customer record. Requires can_edit_customers.",
            args_schema=CreateCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_customer),
            name="update_customer",
            description="Update an existing customer's information. Requires can_edit_customers.",
            args_schema=UpdateCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_customer),
            name="delete_customer",
            description="Delete a customer record. Requires can_edit_customers. Confirm with user first.",
            args_schema=DeleteCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_offers),
            name="get_customer_offers",
            description="Get offer history for a specific customer. Requires can_edit_customers.",
            args_schema=GetCustomerOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_tasks),
            name="get_customer_tasks",
            description="Get task history for a specific customer. Requires can_edit_customers.",
            args_schema=GetCustomerTasksInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offers),
            name="get_offers",
            description="Get paginated list of offers. Requires can_view_offers.",
            args_schema=GetOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offer_details),
            name="get_offer_details",
            description="Get full offer details including services, locations, and line items. Requires can_view_offers.",
            args_schema=GetOfferDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_offer),
            name="create_offer",
            description="Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers.",
            args_schema=CreateOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_offer),
            name="update_offer",
            description="Update an existing offer's details. Requires can_view_offers.",
            args_schema=UpdateOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_offer_status),
            name="update_offer_status",
            description="Change offer status (e.g. cancel). Requires can_view_offers.",
            args_schema=UpdateOfferStatusInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_offer),
            name="delete_offer",
            description="Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers.",
            args_schema=DeleteOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_all_tasks),
            name="get_all_tasks",
            description="Get all company tasks with summary statistics. Requires can_manage_tasks (Manager only).",
            args_schema=GetAllTasksInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_tasks),
            name="get_my_tasks",
            description="Get tasks assigned to the current employee. Available to both Manager and Employee roles.",
            args_schema=GetMyTasksInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_task_details),
            name="get_task_details",
            description="Get detailed task info including status, duration, files, assignment history.",
            args_schema=GetTaskDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_task),
            name="create_task",
            description="Create a new task and assign to an employee. Requires can_manage_tasks.",
            args_schema=CreateTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_task),
            name="update_task",
            description="Update task details. Requires can_manage_tasks.",
            args_schema=UpdateTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.start_task),
            name="start_task",
            description="Start a task (Pending -> InProgress). Available to the assigned employee.",
            args_schema=StartTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.complete_task),
            name="complete_task",
            description="Mark a task as completed. Available to the assigned employee.",
            args_schema=CompleteTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.reassign_task),
            name="reassign_task",
            description="Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks.",
            args_schema=ReassignTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.search_employees),
            name="search_employees",
            description="Search employees by name (autocomplete helper for task assignment).",
            args_schema=SearchEmployeesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.search_customers),
            name="search_customers",
            description="Search customers by name (autocomplete helper for task/offer creation).",
            args_schema=SearchCustomersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employees),
            name="get_employees",
            description="Get paginated list of employees. Requires can_manage_users.",
            args_schema=GetEmployeesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employee_details),
            name="get_employee_details",
            description="Get employee details including permissions and task counts. Requires can_manage_users.",
            args_schema=GetEmployeeDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_employee),
            name="create_employee",
            description="Create a new employee account. Requires can_manage_users.",
            args_schema=CreateEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_employee),
            name="update_employee",
            description="Update employee information. Requires can_manage_users.",
            args_schema=UpdateEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_employee),
            name="delete_employee",
            description="Delete/deactivate an employee. Requires can_manage_users. Confirm first.",
            args_schema=DeleteEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employee_performance),
            name="get_employee_performance",
            description="Get performance report including completion rates. Requires can_manage_users.",
            args_schema=GetEmployeePerformanceInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_expense_wrapper(ops.get_expenses),
            name="get_expenses",
            description="Get paginated expenses. Requires can_view_reports.",
            args_schema=GetExpensesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_expense),
            name="create_expense",
            description="Record a new expense. Requires can_view_reports.",
            args_schema=CreateExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_expense),
            name="update_expense",
            description="Update an expense record. Requires can_view_reports.",
            args_schema=UpdateExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_expense),
            name="delete_expense",
            description="Delete an expense record. Requires can_view_reports. Confirm first.",
            args_schema=DeleteExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_expense_wrapper(ops.get_expense_charts),
            name="get_expense_charts",
            description="Get expense chart data (monthly trend or category breakdown). Requires can_view_reports.",
            args_schema=GetExpenseChartsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_appointments),
            name="get_appointments",
            description="Get paginated list of appointments for the company. Requires can_view_offers.",
            args_schema=GetAppointmentsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_appointment),
            name="create_appointment",
            description="Schedule a new appointment (on-site visit). Requires can_view_offers.",
            args_schema=CreateAppointmentInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_dashboard),
            name="get_dashboard",
            description="Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports.",
            args_schema=GetDashboardInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_requests),
            name="get_service_requests",
            description="Get incoming service requests from portal users. Requires can_view_offers.",
            args_schema=GetServiceRequestsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_request_details),
            name="get_service_request_details",
            description="Get details of a specific service request. Requires can_view_offers.",
            args_schema=GetServiceRequestDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.decline_service_request),
            name="decline_service_request",
            description="Decline a service request from a portal user. Requires can_view_offers.",
            args_schema=DeclineServiceRequestInput,
        ),

        # ── Analytical Reports ───────────────────────────────────
        StructuredTool.from_function(
            coroutine=_make_wrapper(reports.generate_business_report),
            name="generate_business_report",
            description="Generate a comprehensive business overview: dashboard KPIs, offers breakdown, tasks summary, and expense trends. Use when the user asks for a business report, company overview, or general performance summary.",
            args_schema=GenerateBusinessReportInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_expense_wrapper(reports.generate_financial_report),
            name="generate_financial_report",
            description="Generate a financial analysis: monthly expense trends, category breakdown, and recent expense records. Supports optional date range filtering. Use when the user asks about finances, expenses, spending, or budget analysis.",
            args_schema=GenerateFinancialReportInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(reports.generate_team_performance_report),
            name="generate_team_performance_report",
            description="Generate a team performance report: all employees with individual performance metrics, completion rates, and task statistics. Use when the user asks about team performance, employee comparison, or workforce analytics.",
            args_schema=GenerateTeamPerformanceReportInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(reports.generate_pipeline_report),
            name="generate_pipeline_report",
            description="Generate a sales pipeline report: service requests by status and offers by status, showing the full lead-to-deal conversion funnel. Use when the user asks about the sales pipeline, lead conversion, or request-to-offer flow.",
            args_schema=GeneratePipelineReportInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(reports.generate_customer_report),
            name="generate_customer_report",
            description="Generate a customer engagement report: all customers with per-customer offer and task counts. Use when the user asks about customer activity, engagement, or wants a customer overview.",
            args_schema=GenerateCustomerReportInput,
        ),
    ]


TOOLS = _make_company_tools()
