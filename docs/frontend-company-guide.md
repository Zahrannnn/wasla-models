# Company Portal — Frontend Integration Guide

This guide covers everything the frontend team needs to integrate the Wasla Company Portal (CRM) AI chat agent for staff users (Managers and Employees).

---

## Endpoint

```
POST /api/company/chat
```

**Base URL:** configured per environment (e.g. `https://api.wasla.app` or `http://localhost:8000`)

---

## Authentication

A Bearer JWT token is **expected** on every request. Without it, most tools will return "Authentication required" errors inside the response text.

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

The agent also exposes a `login_staff` tool, so staff can authenticate through the chat itself if needed.

### User Roles

| Role | Access |
|------|--------|
| **Manager** | Full access: all CRM tools, employee management, all tasks, reports |
| **Employee** | Limited: own tasks (`get_my_tasks`), start/complete tasks, change password |

Role-based restrictions are enforced server-side. If a tool returns "forbidden", the agent will explain the user lacks permission.

---

## Request

```typescript
interface ChatRequest {
  message: string;      // required, min 1 character
  session_id?: string;  // null/omitted on first turn, then reuse from response
}
```

### Session Flow

1. **First message:** omit `session_id` (or send `null`). The server creates a new LangGraph thread and returns a UUID.
2. **Subsequent messages:** pass the `session_id` from the previous response to continue the same conversation thread.
3. **New conversation:** omit `session_id` again to start fresh.

```
Turn 1:  { "message": "Show me the dashboard" }
         → response includes session_id: "f9e8d7c6-..."

Turn 2:  { "message": "Which tasks are overdue?", "session_id": "f9e8d7c6-..." }
         → same session_id returned

New chat: { "message": "Generate a financial report" }
         → new session_id returned
```

---

## Response

```typescript
interface ChatResponse {
  response: string;        // AI-generated text (may contain Markdown)
  session_id: string;      // reuse on next request
  tool_calls_made: number; // tools called during THIS request only
  model_used: string;      // LLM model id (may be empty)
  charts: ChartBlock[];    // interactive chart data (may be empty)
}

interface ChartDataset {
  label: string;           // legend label ("Count", "Amount (EGP)", "Completed")
  data: number[];          // one value per label
}

interface ChartBlock {
  id: string;              // stable key: "expense_monthly", "offers_by_status", etc.
  chart_type: string;      // "bar" | "line" | "pie" | "doughnut"
  title: string;           // "Monthly Expenses"
  labels: string[];        // category / X-axis labels
  datasets: ChartDataset[];// one or more data series
}
```

### Rendering the `response` field

The `response` field contains **rich Markdown**. The company agent produces:

- **Tables** for lists (customers, offers, tasks, employees, expenses)
- **Report structure** with headers: Executive Summary → Key Metrics → Analysis → Recommendations
- **Ranked tables** for employee comparisons
- **Trend indicators** in metric tables
- **Bullet lists** for observations and action items

Use a Markdown renderer (e.g. `react-markdown`, `marked`) in your UI.

### Rendering `charts`

When `charts` is non-empty, render each `ChartBlock` as an interactive chart **below** the Markdown response. Use Chart.js or Recharts.

**Chart IDs for the Company Portal:**

| `id` | Source Tool | Chart Type | What it shows |
|---|---|---|---|
| `expense_monthly` | `generate_business_report`, `generate_financial_report`, `get_expense_charts` | bar | Monthly expense totals |
| `expense_category` | `generate_business_report`, `generate_financial_report`, `get_expense_charts` | doughnut | Expenses broken down by category |
| `offers_by_status` | `generate_business_report`, `generate_pipeline_report` | doughnut | Offers grouped by status (Pending, Sent, Accepted, ...) |
| `tasks_by_status` | `generate_business_report` | doughnut | Tasks grouped by status |
| `service_requests_by_status` | `generate_pipeline_report` | doughnut | Service requests grouped by status |
| `employee_tasks` | `generate_team_performance_report` | bar | Per-employee completed vs total tasks (multi-dataset) |
| `customer_engagement` | `generate_customer_report` | bar | Top 15 customers: offers vs tasks (multi-dataset) |

**Multi-dataset charts:** Some charts (e.g. `employee_tasks`) have multiple datasets. Render them as grouped/stacked bars:

```typescript
// employee_tasks example:
{
  id: "employee_tasks",
  chart_type: "bar",
  title: "Employee Task Overview",
  labels: ["Ahmed", "Sara", "Omar"],
  datasets: [
    { label: "Completed", data: [12, 8, 15] },
    { label: "Total Assigned", data: [14, 10, 16] }
  ]
}
```

**Example rendering (React + Chart.js):**

```tsx
import { Doughnut, Pie, Bar, Line } from "react-chartjs-2";

function ChatChart({ chart }: { chart: ChartBlock }) {
  const chartData = {
    labels: chart.labels,
    datasets: chart.datasets.map((ds) => ({
      label: ds.label,
      data: ds.data,
    })),
  };

  const options = {
    responsive: true,
    plugins: { title: { display: true, text: chart.title } },
  };

  switch (chart.chart_type) {
    case "pie":       return <Pie data={chartData} options={options} />;
    case "doughnut":  return <Doughnut data={chartData} options={options} />;
    case "line":      return <Line data={chartData} options={options} />;
    default:          return <Bar data={chartData} options={options} />;
  }
}

// In the chat message component:
function AssistantMessage({ response, charts }: ChatResponse) {
  return (
    <div>
      <Markdown>{response}</Markdown>
      {charts.length > 0 && (
        <div className="charts-grid">
          {charts.map((chart) => (
            <ChatChart key={chart.id} chart={chart} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Error Handling

| Status | Meaning | Frontend Action |
|--------|---------|-----------------|
| `200`  | Success | Parse `ChatResponse` |
| `422`  | Validation error (empty message) | Show "Please enter a message" |
| `500`  | Unexpected server error | Show "Something went wrong. Please try again." |
| `503`  | LLM unavailable (model not loaded, API key issue) | Show "AI assistant is temporarily unavailable." The `detail` field contains a diagnostic message. |

> **Note:** Auth and permission errors (`401`, `403`) are surfaced inside the `response` text, not as HTTP status codes.

---

## Health Check

```
GET /health
```

```typescript
interface HealthResponse {
  status: string;            // "ok"
  llm_provider: string;      // "ollama", "openrouter", or "anthropic"
  main_model: string;        // e.g. "qwen2.5:3b"
  fallback_model: string;    // backup model
  max_context_tokens: number;
}
```

---

## Available Tools (47 total)

The agent decides which tools to call based on the user's message. Understanding the tool set helps you design the UI.

### Auth (2)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `login_staff` | Authenticate staff (Manager/Employee), get JWT | No |
| `change_password` | Change current user's password | Yes |

### Customers (7)
| Tool | Description | Role |
|------|-------------|------|
| `get_customers` | Paginated list (search by name/email) | `can_edit_customers` |
| `get_customer_details` | Detail view with offer/task counts and total profit | `can_edit_customers` |
| `create_customer` | Create new customer record | `can_edit_customers` |
| `update_customer` | Update customer info | `can_edit_customers` |
| `delete_customer` | Delete customer (agent confirms first) | `can_edit_customers` |
| `get_customer_offers` | Offer history for a customer | `can_edit_customers` |
| `get_customer_tasks` | Task history for a customer | `can_edit_customers` |

### Offers (6)
| Tool | Description | Role |
|------|-------------|------|
| `get_offers` | Paginated list (search, filter by status) | `can_view_offers` |
| `get_offer_details` | Full details with services, locations, line items | `can_view_offers` |
| `create_offer` | Create offer for a customer (can link to service request) | `can_view_offers` |
| `update_offer` | Update offer details | `can_view_offers` |
| `update_offer_status` | Change status (Pending/Sent/Canceled) | `can_view_offers` |
| `delete_offer` | Delete (only if not yet accepted) | `can_view_offers` |

### Tasks (9)
| Tool | Description | Role |
|------|-------------|------|
| `get_all_tasks` | All company tasks with stats | `can_manage_tasks` (Manager) |
| `get_my_tasks` | Tasks assigned to current user | Any |
| `get_task_details` | Detail view with status, duration, history | Any |
| `create_task` | Create and assign to an employee | `can_manage_tasks` |
| `update_task` | Update task details | `can_manage_tasks` |
| `start_task` | Start task (Pending → InProgress) | Assigned employee |
| `complete_task` | Mark task completed | Assigned employee |
| `reassign_task` | Reassign to another employee (audit trail) | `can_manage_tasks` |
| `search_employees` | Autocomplete helper for task assignment | Any |

### Employees (6)
| Tool | Description | Role |
|------|-------------|------|
| `get_employees` | Paginated list (search by name/email) | `can_manage_users` |
| `get_employee_details` | Detail view with permissions and task counts | `can_manage_users` |
| `create_employee` | Create new employee account | `can_manage_users` |
| `update_employee` | Update employee info/permissions | `can_manage_users` |
| `delete_employee` | Delete/deactivate (agent confirms first) | `can_manage_users` |
| `get_employee_performance` | Performance report with completion rates | `can_manage_users` |

### Expenses (5)
| Tool | Description | Role |
|------|-------------|------|
| `get_expenses` | Paginated list (search, filter by category/date) | `can_view_reports` |
| `create_expense` | Record new expense | `can_view_reports` |
| `update_expense` | Update expense record | `can_view_reports` |
| `delete_expense` | Delete expense (agent confirms first) | `can_view_reports` |
| `get_expense_charts` | Chart data: monthly trend or category breakdown | `can_view_reports` |

### Appointments (2)
| Tool | Description | Role |
|------|-------------|------|
| `get_appointments` | Paginated list (filter by date, customer) | `can_view_offers` |
| `create_appointment` | Schedule on-site visit | `can_view_offers` |

### Service Requests (3)
| Tool | Description | Role |
|------|-------------|------|
| `get_service_requests` | Incoming requests from portal users | `can_view_offers` |
| `get_service_request_details` | Single request details | `can_view_offers` |
| `decline_service_request` | Decline a request (optional reason) | `can_view_offers` |

### Dashboard (1)
| Tool | Description | Role |
|------|-------------|------|
| `get_dashboard` | KPIs, charts, important tasks | `can_view_reports` |

### Search (1)
| Tool | Description | Role |
|------|-------------|------|
| `search_customers` | Autocomplete helper for offer/task creation | Any |

### Analytical Reports (5)
| Tool | Description | Role |
|------|-------------|------|
| `generate_business_report` | Full overview: KPIs + offers + tasks + expense trends | `can_view_reports` |
| `generate_financial_report` | Expenses: monthly trends + category + records (date range optional) | `can_view_reports` |
| `generate_team_performance_report` | All employees: metrics, completion rates, workload | `can_manage_users` |
| `generate_pipeline_report` | Sales funnel: service requests → offers by status | `can_view_offers` |
| `generate_customer_report` | Per-customer engagement: offer/task activity | `can_edit_customers` |

These report tools aggregate multiple API calls in one shot, so the agent responds faster with comprehensive data.

---

## Example Integration (TypeScript)

```typescript
const API_BASE = "https://api.wasla.app";

interface ChatState {
  sessionId: string | null;
  token: string;  // JWT from company auth
}

async function sendCompanyMessage(
  message: string,
  state: ChatState
): Promise<{ response: string; sessionId: string; toolCalls: number; charts: ChartBlock[] }> {
  const res = await fetch(`${API_BASE}/api/company/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${state.token}`,
    },
    body: JSON.stringify({
      message,
      session_id: state.sessionId,
    }),
  });

  if (!res.ok) {
    if (res.status === 503) {
      throw new Error("AI assistant is temporarily unavailable.");
    }
    throw new Error(`Chat failed: ${res.status}`);
  }

  const data = await res.json();
  return {
    response: data.response,     // Render as Markdown
    sessionId: data.session_id,  // Store for next turn
    toolCalls: data.tool_calls_made,
    charts: data.charts || [],   // Render as interactive charts
  };
}
```

### Usage in a React component

```tsx
const [sessionId, setSessionId] = useState<string | null>(null);
const { token } = useCompanyAuth();  // your auth context

async function handleSend(message: string) {
  setLoading(true);
  try {
    const result = await sendCompanyMessage(message, { sessionId, token });
    setSessionId(result.sessionId);
    appendMessage({
      role: "assistant",
      content: result.response,
      charts: result.charts,  // pass charts to the message component
    });
  } catch (err) {
    appendMessage({ role: "error", content: err.message });
  } finally {
    setLoading(false);
  }
}
```

---

## Conversational Data Gathering

The agent will **ask for required information step by step** before calling create/update tools. For example, when a user says "create a new customer", the agent will ask for name, email, phone, and address across multiple turns — then confirm with a summary before creating.

**Frontend implications:**
- Expect multi-turn conversations for create/update actions
- The agent confirms with a summary before executing — no extra confirmation modals needed
- If the user provides all data upfront (e.g., "Create customer Ahmed, ahmed@email.com, ..."), the agent skips steps and confirms directly
- The `tool_calls_made` will be `0` during gathering turns — the tool is only called after the user confirms
- Charts won't appear during data-gathering turns (no report tools involved)

---

## UX Recommendations

1. **Show a typing/loading indicator** — the agent may call 3-6 tools for reports before responding. Show `tool_calls_made` after the response (e.g. "Queried 4 data sources").
2. **Render Markdown + Charts** — responses contain tables, headers, and structured reports. When `charts` is non-empty, render interactive charts below the text.
3. **Persist `session_id`** — store in component state or session storage. Losing it means losing conversation history.
4. **Role-aware quick actions** — offer different suggested prompts by role:
   - **Manager:** "Business report", "Team performance", "Pipeline overview", "Show all tasks"
   - **Employee:** "My tasks", "Start task #X", "Complete task #X"
5. **New conversation button** — clear `session_id` to start a fresh thread.
6. **Report-aware UI** — for analytical reports, the response will be long and structured with charts. Consider a wider display area or expandable sections.
7. **The agent confirms destructive actions** (delete customer, delete offer, delete employee) before executing — no separate confirmation modals needed for agent actions.
8. **Charts sizing** — use a grid layout (2 charts per row on desktop, 1 on mobile). Recommended chart width: 400-500px.

---

## Manager vs Employee Experience

Design your UI to adapt based on role:

### Manager View
- Full CRM dashboard prompts: "How are we doing?", "Generate a business report"
- Employee management: "Show team performance", "Create new employee"
- All task management: "Show all overdue tasks", "Reassign task #5 to Ahmed"

### Employee View
- Task-focused prompts: "Show my tasks", "Start task #12", "Complete task #8"
- Password management: "Change my password"
- The agent will suggest `get_my_tasks` instead of `get_all_tasks` if the employee lacks permissions

---

## Differences from Customer Portal

| Aspect | Customer (`/api/chat`) | Company (`/api/company/chat`) |
|--------|----------------------|-------------------------------|
| Auth | Optional (public tools work without) | Expected (most tools need it) |
| Tools | 28 | 47 |
| Reports | 1 (activity report) | 5 (business, financial, team, pipeline, customer) |
| Chart IDs | 3 (`my_offers_by_status`, `my_requests_by_status`, `my_reviews_by_rating`) | 7 (`expense_monthly`, `expense_category`, `offers_by_status`, `tasks_by_status`, `service_requests_by_status`, `employee_tasks`, `customer_engagement`) |
| Roles | Lead / Customer | Manager / Employee |
| Response style | Conversational, tables, suggestions | Professional reports, ranked tables, KPI dashboards |
