# Company Portal API - Agent-Friendly Documentation

> **For AI Chatbot Developers**: This document helps you build an agentic AI chatbot to assist company staff (Managers and Employees) with CRM operations. It includes system instructions, tool definitions, conversation examples, and decision-making guidelines.

---

## Table of Contents

1. [System Instructions for AI Agent](#1-system-instructions-for-ai-agent)
2. [Tool Definitions (Function Calling)](#2-tool-definitions-function-calling)
3. [Decision Tree: Which Tool to Use](#3-decision-tree-which-tool-to-use)
4. [User Flows & Conversation Examples](#4-user-flows--conversation-examples)
5. [Tool Details & Usage](#5-tool-details--usage)
6. [Error Handling Guide](#6-error-handling-guide)
7. [Best Practices](#7-best-practices)

---

## 1. System Instructions for AI Agent

### Role
You are a helpful AI assistant that helps company staff (Managers and Employees) manage their CRM operations. You can help users:
- Manage customers (create, update, view history)
- Create and manage offers/quotes
- Assign and track tasks
- Manage employees
- Track expenses
- View dashboard analytics
- Configure company settings

### User Types & Permissions

| Role | Permissions |
|------|-------------|
| **Manager** | Full access: customers, offers, tasks, employees, expenses, dashboard, settings |
| **Employee** | Limited access: view assigned tasks, start/complete tasks, view own task history |

### Permission Policies

| Policy | Description | Who Has It |
|--------|-------------|------------|
| `can_edit_customers` | Create, update, delete customers | Manager |
| `can_view_offers` | View and manage offers, service requests, appointments | Manager |
| `can_manage_tasks` | Create, update, reassign tasks; view all tasks | Manager |
| `can_manage_users` | Manage employees (CRUD, permissions) | Manager |
| `can_view_reports` | View dashboard, expenses, analytics | Manager |

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Company** | The business entity that the staff works for (scoped via JWT `CompanyId` claim) |
| **Customer** | A client record belonging to a company (can have offers, tasks) |
| **Offer** | A quote/proposal sent to a customer (includes services, pricing, locations) |
| **Task** | An operational assignment for an employee (Pending → InProgress → Completed) |
| **Service Request** | An inquiry from portal users that can be converted to an Offer |
| **Employee** | A staff member who can be assigned tasks |
| **Expense** | A business cost tracked for reporting |

### Offer Workflow

```
Service Request (from portal)
        │
        ▼
    Create Offer ──► Status: Pending
        │
        ▼
    Send Offer ──► Status: Sent
        │
        ├──────────────────┐
        ▼                  ▼
  Customer Accepts    Customer Rejects
  (Digital Signature)   (Reason)
        │                  │
        ▼                  ▼
  Status: Accepted    Status: Rejected
```

### Task Workflow

```
Manager Creates Task
        │
        ▼
    Status: Pending
        │
        ▼
  Employee Starts Task
        │
        ▼
    Status: InProgress
        │
        ▼
  Employee Completes Task
        │
        ▼
    Status: Completed
```

### Authentication

All company endpoints require JWT authentication with:
- `CompanyId` claim (for company scoping)
- `Role` claim (Manager or Employee)
- `permission` claims (for policy-based access)

---

## 2. Tool Definitions (Function Calling)

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "login_staff",
        "description": "Authenticate a company staff member (Manager or Employee). Returns JWT token with company ID, role, and permissions.",
        "parameters": {
          "type": "object",
          "properties": {
            "email": {"type": "string", "description": "Staff member's email"},
            "password": {"type": "string", "description": "Staff member's password"}
          },
          "required": ["email", "password"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_customers",
        "description": "Get paginated list of customers for the company. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "search": {"type": "string", "description": "Search by name or email"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_customer_details",
        "description": "Get detailed customer info including offer count, task count, and total profit. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer's ID"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_customer",
        "description": "Create a new customer record for the company. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "first_name": {"type": "string", "description": "Customer first name (required)"},
            "last_name": {"type": "string", "description": "Customer last name (required)"},
            "email": {"type": "string", "description": "Customer email (required)"},
            "phone_number": {"type": "string", "description": "Phone number (required)"},
            "address": {"type": "string", "description": "Street address (required)"},
            "city": {"type": "string", "description": "City (required)"},
            "zip_code": {"type": "string", "description": "Postal/ZIP code (required)"},
            "country": {"type": "string", "description": "Country (required)"},
            "notes": {"type": "string", "description": "Additional notes (required)"}
          },
          "required": ["first_name", "last_name", "email", "phone_number", "address", "city", "zip_code", "country", "notes"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_customer",
        "description": "Update an existing customer's information. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID (required)"},
            "first_name": {"type": "string", "description": "Customer first name"},
            "last_name": {"type": "string", "description": "Customer last name"},
            "email": {"type": "string", "description": "Customer email"},
            "phone_number": {"type": "string", "description": "Phone number"},
            "address": {"type": "string", "description": "Street address"},
            "city": {"type": "string", "description": "City"},
            "zip_code": {"type": "string", "description": "Postal/ZIP code"},
            "country": {"type": "string", "description": "Country"},
            "notes": {"type": "string", "description": "Additional notes"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "delete_customer",
        "description": "Delete a customer record. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID to delete"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_customer_offers",
        "description": "Get offer history for a specific customer. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID"},
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_customer_tasks",
        "description": "Get task history for a specific customer. Requires can_edit_customers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID"},
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_offers",
        "description": "Get paginated list of offers for the company. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "search_word": {"type": "string", "description": "Search by client name or offer number"},
            "status": {"type": "string", "description": "Filter by status: Pending, Sent, Accepted, Rejected, Canceled"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_offer_details",
        "description": "Get full offer details including services, locations, and line items. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "Offer ID"}
          },
          "required": ["offer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_offer",
        "description": "Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID (required)"},
            "service_request_id": {"type": "integer", "description": "Optional: Link to service request (auto-updates status to OfferSent)"},
            "notes_in_offer": {"type": "string", "description": "Notes visible to customer"},
            "notes_not_in_offer": {"type": "string", "description": "Internal notes (not visible to customer)"},
            "language_code": {"type": "string", "description": "Offer language (e.g., 'en', 'de')"},
            "email_to_customer": {"type": "boolean", "description": "Send email notification to customer"},
            "locations": {"type": "array", "description": "List of locations (From, To)", "items": {"type": "object", "properties": {"location_type": {"type": "string"}, "address": {"type": "string"}}}},
            "services": {"type": "object", "description": "Service details (Move, Cleaning, Packing, etc.)"}
          },
          "required": ["customer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_offer",
        "description": "Update an existing offer's details. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "Offer ID (required)"},
            "customer_id": {"type": "integer", "description": "Customer ID"},
            "notes_in_offer": {"type": "string", "description": "Notes visible to customer"},
            "notes_not_in_offer": {"type": "string", "description": "Internal notes"},
            "locations": {"type": "array", "description": "List of locations"},
            "services": {"type": "object", "description": "Service details"}
          },
          "required": ["offer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_offer_status",
        "description": "Manually update offer status (e.g., cancel an offer). Customer Accept/Reject is handled through portal. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "Offer ID (required)"},
            "status": {"type": "string", "description": "New status: Pending, Sent, Accepted, Rejected, Canceled", "enum": ["Pending", "Sent", "Accepted", "Rejected", "Canceled"]}
          },
          "required": ["offer_id", "status"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "delete_offer",
        "description": "Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "Offer ID to delete"}
          },
          "required": ["offer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_all_tasks",
        "description": "Get all company tasks with summary statistics. Requires can_manage_tasks permission (Manager only).",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_my_tasks",
        "description": "Get tasks assigned to the current employee. Available to both Manager and Employee roles.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_task_details",
        "description": "Get detailed task information including status, duration, files, and assignment history.",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {"type": "integer", "description": "Task ID"}
          },
          "required": ["task_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_task",
        "description": "Create a new task and assign it to an employee. Supports file attachments. Requires can_manage_tasks permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "assigned_to_user_id": {"type": "integer", "description": "Employee ID to assign task to (required)"},
            "customer_id": {"type": "integer", "description": "Optional: Link to customer"},
            "task_title": {"type": "string", "description": "Task title (required)"},
            "description": {"type": "string", "description": "Task description"},
            "priority": {"type": "string", "description": "Priority: Low, Medium, High, Urgent", "enum": ["Low", "Medium", "High", "Urgent"]},
            "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
            "notes": {"type": "string", "description": "Additional notes"}
          },
          "required": ["assigned_to_user_id", "task_title"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_task",
        "description": "Update task details. Requires can_manage_tasks permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "task_item_id": {"type": "integer", "description": "Task ID (required)"},
            "assigned_to_user_id": {"type": "integer", "description": "Employee ID"},
            "customer_id": {"type": "integer", "description": "Customer ID"},
            "task_title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Description"},
            "priority": {"type": "string", "description": "Priority"},
            "due_date": {"type": "string", "description": "Due date"},
            "notes": {"type": "string", "description": "Notes"}
          },
          "required": ["task_item_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "start_task",
        "description": "Start a task (change status from Pending to InProgress). Available to assigned employee.",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {"type": "integer", "description": "Task ID to start"}
          },
          "required": ["task_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "complete_task",
        "description": "Mark a task as completed. Available to assigned employee. Can attach result files.",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {"type": "integer", "description": "Task ID to complete"}
          },
          "required": ["task_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "reassign_task",
        "description": "Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {"type": "integer", "description": "Task ID (required)"},
            "new_assignee_id": {"type": "integer", "description": "New employee's user ID (required)"},
            "reason": {"type": "string", "description": "Reason for reassignment (required)"}
          },
          "required": ["task_id", "new_assignee_id", "reason"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "search_employees",
        "description": "Search employees by name (autocomplete helper for task assignment).",
        "parameters": {
          "type": "object",
          "properties": {
            "search_name": {"type": "string", "description": "Name to search for"}
          },
          "required": ["search_name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "search_customers",
        "description": "Search customers by name (autocomplete helper for task/offer creation).",
        "parameters": {
          "type": "object",
          "properties": {
            "search_name": {"type": "string", "description": "Name to search for"}
          },
          "required": ["search_name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_employees",
        "description": "Get paginated list of employees. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "search": {"type": "string", "description": "Search by name or email"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_employee_details",
        "description": "Get employee details including permissions and task counts. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "user_id": {"type": "integer", "description": "Employee's user ID"}
          },
          "required": ["user_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_employee",
        "description": "Create a new employee account. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "first_name": {"type": "string", "description": "First name (required)"},
            "last_name": {"type": "string", "description": "Last name (required)"},
            "email": {"type": "string", "description": "Email address (required)"},
            "user_name": {"type": "string", "description": "Username (required)"},
            "password": {"type": "string", "description": "Password (required)"},
            "is_active": {"type": "boolean", "description": "Whether account is active (default: true)"},
            "permission_ids": {"type": "array", "description": "List of permission IDs to assign", "items": {"type": "integer"}}
          },
          "required": ["first_name", "last_name", "email", "user_name", "password"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_employee",
        "description": "Update employee information. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "user_id": {"type": "integer", "description": "Employee's user ID (required)"},
            "first_name": {"type": "string", "description": "First name"},
            "last_name": {"type": "string", "description": "Last name"},
            "email": {"type": "string", "description": "Email"},
            "user_name": {"type": "string", "description": "Username"},
            "new_password": {"type": "string", "description": "New password (optional)"},
            "is_active": {"type": "boolean", "description": "Active status"},
            "permission_ids": {"type": "array", "description": "Permission IDs", "items": {"type": "integer"}}
          },
          "required": ["user_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "delete_employee",
        "description": "Delete/deactivate an employee. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "user_id": {"type": "integer", "description": "Employee's user ID"}
          },
          "required": ["user_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_employee_performance",
        "description": "Get performance report for an employee including completion rates. Requires can_manage_users permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "employee_id": {"type": "integer", "description": "Employee's user ID"}
          },
          "required": ["employee_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_expenses",
        "description": "Get paginated list of expenses. Requires can_view_reports permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "page": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "search": {"type": "string", "description": "Search term"},
            "category": {"type": "string", "description": "Filter by category"},
            "from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "to": {"type": "string", "description": "End date (YYYY-MM-DD)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_expense",
        "description": "Record a new expense. Requires can_view_reports permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "description": {"type": "string", "description": "Expense description (required)"},
            "amount_egp": {"type": "number", "description": "Amount in EGP (required)"},
            "expense_date": {"type": "string", "description": "Date of expense (YYYY-MM-DD, required)"},
            "category": {"type": "string", "description": "Expense category (required)"}
          },
          "required": ["description", "amount_egp", "expense_date", "category"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_expense",
        "description": "Update an expense record. Requires can_view_reports permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "expense_id": {"type": "integer", "description": "Expense ID (required)"},
            "description": {"type": "string", "description": "Description"},
            "amount_egp": {"type": "number", "description": "Amount in EGP"},
            "expense_date": {"type": "string", "description": "Date"},
            "category": {"type": "string", "description": "Category"}
          },
          "required": ["expense_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "delete_expense",
        "description": "Delete an expense record. Requires can_view_reports permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "expense_id": {"type": "integer", "description": "Expense ID"}
          },
          "required": ["expense_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_expense_charts",
        "description": "Get expense data for charts (monthly trend and category breakdown). Requires can_view_reports permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "chart_type": {"type": "string", "description": "Type of chart data: 'monthly' or 'category'", "enum": ["monthly", "category"]},
            "from": {"type": "string", "description": "Start date for category chart (optional)"},
            "to": {"type": "string", "description": "End date for category chart (optional)"}
          },
          "required": ["chart_type"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_dashboard",
        "description": "Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports permission.",
        "parameters": {"type": "object", "properties": {}}
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_service_requests",
        "description": "Get incoming service requests from portal users. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "status": {"type": "string", "description": "Filter by status: New, Viewed, OfferSent, Declined"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_service_request_details",
        "description": "Get details of a specific service request. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "request_id": {"type": "integer", "description": "Service request ID"}
          },
          "required": ["request_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "decline_service_request",
        "description": "Decline a service request from a portal user. Requires can_view_offers permission.",
        "parameters": {
          "type": "object",
          "properties": {
            "request_id": {"type": "integer", "description": "Service request ID (required)"},
            "reason": {"type": "string", "description": "Reason for declining (optional)"}
          },
          "required": ["request_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "change_password",
        "description": "Change current user's password. Requires authentication.",
        "parameters": {
          "type": "object",
          "properties": {
            "current_password": {"type": "string", "description": "Current password (required)"},
            "new_password": {"type": "string", "description": "New password (required)"},
            "confirm_password": {"type": "string", "description": "Confirm new password (required)"}
          },
          "required": ["current_password", "new_password", "confirm_password"]
        }
      }
    }
  ]
}
```

---

## 3. Decision Tree: Which Tool to Use

### Authentication

```
User wants to log in?
    └─► login_staff

User wants to change password?
    └─► change_password
```

### Customer Management (Manager Only)

```
User wants to manage customers?
    │
    ├─► "Show all customers" → get_customers
    │
    ├─► "Customer details" → get_customer_details (customer_id known)
    │
    ├─► "Create new customer" → create_customer
    │
    ├─► "Update customer" → update_customer
    │
    ├─► "Delete customer" → delete_customer
    │
    ├─► "Customer's offers" → get_customer_offers
    │
    └─► "Customer's tasks" → get_customer_tasks
```

### Offer Management (Manager Only)

```
User wants to manage offers?
    │
    ├─► "Show all offers" → get_offers
    │
    ├─► "Offer details" → get_offer_details (offer_id known)
    │
    ├─► "Create offer" → create_offer
    │       └─► Can link to service_request_id
    │
    ├─► "Update offer" → update_offer
    │
    ├─► "Cancel offer" → update_offer_status (status: "Canceled")
    │
    └─► "Delete offer" → delete_offer
```

### Task Management

```
User wants to manage tasks?
    │
    ├─► Manager wants all tasks → get_all_tasks
    │
    ├─► Employee wants their tasks → get_my_tasks
    │
    ├─► Task details → get_task_details
    │
    ├─► Create task (Manager) → create_task
    │
    ├─► Update task (Manager) → update_task
    │
    ├─► Start task (Assigned employee) → start_task
    │
    ├─► Complete task (Assigned employee) → complete_task
    │
    ├─► Reassign task (Manager) → reassign_task
    │
    └─► Search for autocomplete:
            ├─► search_employees
            └─► search_customers
```

### Employee Management (Manager Only)

```
User wants to manage employees?
    │
    ├─► "Show all employees" → get_employees
    │
    ├─► "Employee details" → get_employee_details
    │
    ├─► "Create employee" → create_employee
    │
    ├─► "Update employee" → update_employee
    │
    ├─► "Delete employee" → delete_employee
    │
    └─► "Employee performance" → get_employee_performance
```

### Expense Management (Manager Only)

```
User wants to manage expenses?
    │
    ├─► "Show expenses" → get_expenses
    │
    ├─► "Add expense" → create_expense
    │
    ├─► "Update expense" → update_expense
    │
    ├─► "Delete expense" → delete_expense
    │
    └─► "Expense charts" → get_expense_charts
            ├─► chart_type: "monthly"
            └─► chart_type: "category"
```

### Service Requests (Manager Only)

```
User wants to manage service requests?
    │
    ├─► "Show requests" → get_service_requests
    │
    ├─► "Request details" → get_service_request_details
    │
    └─► "Decline request" → decline_service_request
            └─► To create offer from request, use create_offer with service_request_id
```

### Dashboard (Manager Only)

```
User wants to see dashboard?
    └─► get_dashboard
```

---

## 4. User Flows & Conversation Examples

### Flow 1: Manager Creating an Offer from Service Request

**Conversation:**
> **Manager:** I have a new service request. Show me pending requests
> **AI:** *(calls get_service_requests with status: "New")*
> 
> You have **3 new service requests**:
> 
> | # | Reference | Customer | Service | Date |
> |---|-----------|----------|---------|------|
> | 1 | SR-1-0001 | John Doe | Moving | Mar 15 |
> | 2 | SR-1-0002 | Jane Smith | Cleaning | Mar 18 |
> | 3 | SR-1-0003 | Bob Wilson | Moving | Mar 20 |
> 
> Would you like to see details of any request or create an offer?

> **Manager:** Show me details for request #1
> **AI:** *(calls get_service_request_details with request_id: 1)*
> 
> **Service Request: SR-1-0001**
> 
> **Customer:** John Doe  
> **Email:** john.doe@example.com  
> **Phone:** +41 79 123 45 67
> 
> **Service:** Moving  
> **Preferred Date:** March 15, 2026  
> **Preferred Time:** Morning 8am-12pm
> 
> **From:** Bahnhofstrasse 10, 8001 Zürich  
> **To:** Bundesplatz 5, 3000 Bern
> 
> **Notes:** Fragile items - piano and antique furniture
> 
> Would you like to create an offer from this request?

> **Manager:** Yes, create an offer. Price is 2500 EGP for the move, include packing service for 500 EGP
> **AI:** *(calls create_offer)*
> 
> I'll create an offer with:
> - **Customer:** John Doe
> - **Service Request:** SR-1-0001 (will be marked as OfferSent)
> - **Locations:**
>   - From: Bahnhofstrasse 10, 8001 Zürich
>   - To: Bundesplatz 5, 3000 Bern
> - **Services:**
>   - Moving: 2,500 EGP
>   - Packing: 500 EGP
> - **Total:** 3,000 EGP
> 
> Should I send this offer to the customer via email?

> **Manager:** Yes, send it
> **AI:** *(calls create_offer with email_to_customer: true)*
> 
> ✅ **Offer Created Successfully!**
> 
> **Offer Number:** OFF-2026-005  
> **Status:** Sent  
> **Customer:** John Doe  
> **Total Amount:** 3,000 EGP
> 
> The offer has been emailed to the customer. They can view it in their portal and accept or reject it.
> 
> The service request SR-1-0001 has been updated to status "OfferSent".

---

### Flow 2: Manager Assigning a Task

**Conversation:**
> **Manager:** I need to create a task for the Wilson moving job
> **AI:** I can help you create a task. I'll need some details:
> 
> - **Task Title:** (e.g., "Moving job - Wilson family")
> - **Assignee:** Which employee should handle this?
> - **Customer:** Is this linked to a customer?
> - **Due Date:** When should it be completed?
> - **Priority:** Low, Medium, High, or Urgent?
> - **Description:** Task details

> **Manager:** Title is "Wilson Moving Job", assign to... let me see available employees
> **AI:** *(calls search_employees with search_name: "")*
> 
> Here are your employees:
> 
> | ID | Name | Active Tasks | Status |
> |----|------|--------------|--------|
> | 5 | Michael Brown | 2 | Available |
> | 6 | Sarah Johnson | 4 | Busy |
> | 7 | David Lee | 1 | Available |
> 
> Who would you like to assign the task to?

> **Manager:** Assign to Michael Brown
> **AI:** Got it! Michael Brown (ID: 5) will be assigned.
> 
> Please provide the remaining details:
> - **Customer:** (optional)
> - **Due Date:** 
> - **Priority:**
> - **Description:**

> **Manager:** Customer is Bob Wilson, due March 20th, high priority. Description: Pack and move household items from Zürich to Bern. Includes piano.
> **AI:** *(calls create_task)*
> 
> ✅ **Task Created Successfully!**
> 
> | Field | Value |
> |-------|-------|
> | **Task** | Wilson Moving Job |
> | **Assigned To** | Michael Brown |
> | **Customer** | Bob Wilson |
> | **Due Date** | March 20, 2026 |
> | **Priority** | 🔴 High |
> | **Status** | Pending |
> 
> Michael has been notified of the new assignment.

---

### Flow 3: Employee Completing a Task

**Conversation:**
> **Employee:** Show me my tasks
> **AI:** *(calls get_my_tasks)*
> 
> **Your Tasks:**
> 
> | # | Title | Customer | Priority | Due | Status |
> |---|-------|----------|----------|-----|--------|
> | 1 | Wilson Moving Job | Bob Wilson | 🔴 High | Mar 20 | Pending |
> | 2 | Office Cleaning | ACME Corp | 🟡 Medium | Mar 22 | InProgress |
> | 3 | Furniture Assembly | Jane Doe | 🟢 Low | Mar 25 | Pending |
> 
> You have 1 task in progress and 2 pending.

> **Employee:** I want to start the Wilson Moving Job
> **AI:** *(calls start_task with task_id: 1)*
> 
> ✅ **Task Started!**
> 
> **Wilson Moving Job** is now **In Progress**.
> 
> Don't forget to mark it complete when finished!

> **Employee:** I finished the Wilson job. Mark it complete
> **AI:** *(calls complete_task with task_id: 1)*
> 
> ✅ **Task Completed!**
> 
> **Wilson Moving Job** has been marked as **Completed**.
> 
> Great job! The task duration has been recorded:
> - **Time in Progress:** 4 hours 30 minutes
> - **Completed:** March 18, 2026 at 3:30 PM

---

### Flow 4: Manager Viewing Dashboard

**Conversation:**
> **Manager:** Show me the dashboard
> **AI:** *(calls get_dashboard)*
> 
> **📊 Company Dashboard**
> 
> **📈 Key Metrics (This Month)**
> | Metric | Value | Change |
> |--------|-------|--------|
> | Revenue | 45,000 EGP | +12% |
> | New Customers | 8 | +3 |
> | Open Tasks | 5 | -2 |
> | Pending Offers | 3 | — |
> 
> **💰 Offer Status Distribution**
> - ✅ Accepted: 12 (60%)
> - 📤 Sent: 5 (25%)
> - ⏳ Pending: 2 (10%)
> - ❌ Rejected: 1 (5%)
> 
> **📦 Revenue by Service**
> - Moving: 28,000 EGP (62%)
> - Cleaning: 12,000 EGP (27%)
> - Packing: 5,000 EGP (11%)
> 
> **⚠️ Important Tasks**
> | Task | Assignee | Due | Priority |
> |------|----------|-----|----------|
> | Wilson Moving | Michael | Mar 20 | 🔴 High |
> | Office Clean | Sarah | Mar 22 | 🟡 Medium |
> 
> Would you like more details on any section?

---

### Flow 5: Adding an Employee

**Conversation:**
> **Manager:** I need to add a new employee
> **AI:** I can help you create a new employee account. Please provide:
> 
> - **First Name:** 
> - **Last Name:**
> - **Email:**
> - **Username:**
> - **Password:** (temporary password they'll change)
> - **Permissions:** What should they be able to do?

> **Manager:** Name is Alex Thompson, email alex@company.com, username athompson, password Temp@123
> **AI:** What permissions should Alex have?
> 
> Available permissions:
> - `can_edit_customers` - Manage customer records
> - `can_view_offers` - View and create offers
> - `can_manage_tasks` - Create and assign tasks
> - `can_manage_users` - Manage employees
> - `can_view_reports` - View dashboard and expenses

> **Manager:** They should be able to manage customers, view offers, and manage tasks
> **AI:** *(calls create_employee)*
> 
> ✅ **Employee Created Successfully!**
> 
> | Field | Value |
> |-------|-------|
> | **Name** | Alex Thompson |
> | **Email** | alex@company.com |
> | **Username** | athompson |
> | **Permissions** | can_edit_customers, can_view_offers, can_manage_tasks |
> | **Status** | Active |
> 
> Alex can now log in with the temporary password. They should change it on first login.

---

## 5. Tool Details & Usage

### Authentication Tools

| Tool | When to Use | Required Role |
|------|-------------|---------------|
| `login_staff` | Staff login | None |
| `change_password` | Change password | Any authenticated |

### Customer Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_customers` | List customers | can_edit_customers |
| `get_customer_details` | Customer info | can_edit_customers |
| `create_customer` | Add customer | can_edit_customers |
| `update_customer` | Edit customer | can_edit_customers |
| `delete_customer` | Remove customer | can_edit_customers |
| `get_customer_offers` | Customer offers | can_edit_customers |
| `get_customer_tasks` | Customer tasks | can_edit_customers |

### Offer Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_offers` | List offers | can_view_offers |
| `get_offer_details` | Offer details | can_view_offers |
| `create_offer` | Create quote | can_view_offers |
| `update_offer` | Edit offer | can_view_offers |
| `update_offer_status` | Change status | can_view_offers |
| `delete_offer` | Remove offer | can_view_offers |

### Task Tools

| Tool | When to Use | Required Role/Permission |
|------|-------------|--------------------------|
| `get_all_tasks` | All company tasks | can_manage_tasks |
| `get_my_tasks` | Assigned tasks | Manager/Employee |
| `get_task_details` | Task info | Manager/Employee |
| `create_task` | Create task | can_manage_tasks |
| `update_task` | Edit task | can_manage_tasks |
| `start_task` | Start task | Assigned Employee |
| `complete_task` | Finish task | Assigned Employee |
| `reassign_task` | Change assignee | can_manage_tasks |
| `search_employees` | Autocomplete | Manager/Employee |
| `search_customers` | Autocomplete | Manager/Employee |

### Employee Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_employees` | List employees | can_manage_users |
| `get_employee_details` | Employee info | can_manage_users |
| `create_employee` | Add employee | can_manage_users |
| `update_employee` | Edit employee | can_manage_users |
| `delete_employee` | Remove employee | can_manage_users |
| `get_employee_performance` | Performance report | can_manage_users |

### Expense Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_expenses` | List expenses | can_view_reports |
| `create_expense` | Add expense | can_view_reports |
| `update_expense` | Edit expense | can_view_reports |
| `delete_expense` | Remove expense | can_view_reports |
| `get_expense_charts` | Chart data | can_view_reports |

### Service Request Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_service_requests` | List requests | can_view_offers |
| `get_service_request_details` | Request info | can_view_offers |
| `decline_service_request` | Decline request | can_view_offers |

### Dashboard Tools

| Tool | When to Use | Required Permission |
|------|-------------|---------------------|
| `get_dashboard` | Company KPIs | can_view_reports |

---

## 6. Error Handling Guide

### HTTP Status Codes

| Code | Meaning | What to Tell User |
|------|---------|-------------------|
| 200 | Success | Operation completed |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input - check error details |
| 401 | Unauthorized | Please log in again |
| 403 | Forbidden | You don't have permission for this |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Something went wrong on our end |

### Common Error Scenarios

**Permission Denied (403)**
```
Employee: "I want to see all tasks"
AI: "Viewing all company tasks requires manager permission. However, I can show you tasks assigned to you. Would you like to see your tasks instead?"
```

**Not Found (404)**
```
Manager: "Show me customer #999"
AI: "I couldn't find a customer with ID 999. They may have been deleted or the ID is incorrect. Would you like me to search for customers by name?"
```

**Cannot Delete (400)**
```
Manager: "Delete offer #5"
AI: "This offer cannot be deleted because it has already been accepted by the customer. Accepted offers must be canceled instead. Would you like to cancel this offer?"
```

**Task Reassignment to Same Person (400)**
```
Manager: "Reassign task to Michael"
AI: "This task is already assigned to Michael. Would you like to reassign it to someone else?"
```

**Employee Not Found (404)**
```
Manager: "Show performance for employee #50"
AI: "I couldn't find an employee with ID 50. Would you like me to list your employees so you can find the correct ID?"
```

---

## 7. Best Practices

### 1. Check User Role First
Before suggesting actions, know what the user can do:
```
AI: "I see you're logged in as an Employee. You can view and complete your assigned tasks. For creating new tasks or managing customers, you'll need to contact your manager."
```

### 2. Provide Context in Lists
When showing lists, summarize and let user choose:
```
AI: "You have 12 pending offers. 3 are from this week. Would you like to see all pending offers, or filter by a specific time period?"
```

### 3. Guide Through Complex Flows
For multi-step processes like creating offers:
```
AI: "To create an offer, I'll need:
1. Customer selection
2. Service details (Moving, Cleaning, etc.)
3. Locations (From/To)
4. Pricing

Let's start - which customer is this offer for?"
```

### 4. Confirm Before Destructive Actions
Always confirm deletes and status changes:
```
AI: "Are you sure you want to delete customer 'John Doe'? This will also remove their offer history. This action cannot be undone."
```

### 5. Use Natural Language for Dates
Convert ISO dates to readable format:
```
Instead of: "Due: 2026-03-20T00:00:00Z"
Say: "Due: March 20, 2026"
```

### 6. Explain Business Rules
When actions have side effects:
```
AI: "Creating this offer will automatically mark service request SR-1-0001 as 'OfferSent' and notify the customer."
```

### 7. Offer Quick Actions
After showing info, suggest next steps:
```
AI: "Offer OFF-2026-005 is currently 'Sent' and awaiting customer response. 
- View full details
- Update pricing
- Cancel offer
- Create a task for this job"
```

### 8. Handle Partial Information
When user provides incomplete info:
```
Manager: "Create a task for the Johnson job"
AI: "I'll create a task for the Johnson job. I need a few more details:
- Which employee should be assigned?
- When is it due?
- What's the priority level?"
```

### 9. Surface Important Info
Highlight critical items:
```
AI: "⚠️ You have 2 high-priority tasks due this week:
- Wilson Moving (Due Mar 20)
- Office Clean (Due Mar 22)"
```

### 10. Autocomplete Helper
For finding users/customers:
```
Manager: "Assign to Sa..."
AI: "I found these employees starting with 'Sa':
- Sarah Johnson
- Sam Williams
Which one did you mean?"
```

---

## Quick Reference: Common Manager Questions → Tool Mapping

| Manager Question | Tool to Use |
|-----------------|-------------|
| "Show dashboard" | `get_dashboard` |
| "List customers" | `get_customers` |
| "Add customer" | `create_customer` |
| "Customer details" | `get_customer_details` |
| "Show offers" | `get_offers` |
| "Create offer" | `create_offer` |
| "Cancel offer" | `update_offer_status` (Canceled) |
| "Show service requests" | `get_service_requests` |
| "List employees" | `get_employees` |
| "Add employee" | `create_employee` |
| "Employee performance" | `get_employee_performance` |
| "Show all tasks" | `get_all_tasks` |
| "Create task" | `create_task` |
| "Reassign task" | `reassign_task` |
| "Show expenses" | `get_expenses` |
| "Add expense" | `create_expense` |
| "Expense charts" | `get_expense_charts` |

## Quick Reference: Employee Questions → Tool Mapping

| Employee Question | Tool to Use |
|-------------------|-------------|
| "My tasks" | `get_my_tasks` |
| "Task details" | `get_task_details` |
| "Start task" | `start_task` |
| "Complete task" | `complete_task` |
| "Change password" | `change_password` |

---

*Document Version: 1.0*  
*Last Updated: March 2026*
