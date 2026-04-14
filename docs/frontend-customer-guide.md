# Customer Portal — Frontend Integration Guide

This guide covers everything the frontend team needs to integrate the Wasla Customer Portal AI chat agent.

---

## Endpoint

```
POST /api/chat
```

**Base URL:** configured per environment ( `http://localhost:8000`)

---

## Authentication

Authentication is **optional**. The endpoint accepts an `Authorization` header with a Bearer JWT token.

- **Without a token:** public tools work (browse companies, view reviews, company details, trending/recommended companies).
- **With a token:** all tools work (profile, offers, reviews, service requests, dashboard, etc.).

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

The agent can also perform login/registration through the chat itself — the `login_customer` and `register_customer` tools are available without auth.

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
Turn 1:  { "message": "Show trending companies" }
         → response includes session_id: "a1b2c3d4-..."

Turn 2:  { "message": "Tell me more about the first one", "session_id": "a1b2c3d4-..." }
         → same session_id returned

New chat: { "message": "What are my offers?" }
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
  label: string;           // legend label ("Count", "Amount (EGP)")
  data: number[];          // one value per label
}

interface ChartBlock {
  id: string;              // stable key: "my_offers_by_status", "my_reviews_by_rating"
  chart_type: string;      // "bar" | "line" | "pie" | "doughnut"
  title: string;           // "My Offers by Status"
  labels: string[];        // category labels
  datasets: ChartDataset[];// data series
}
```

### Rendering the `response` field

The `response` field contains **Markdown-formatted text**. The agent uses:

- **Tables** for lists (companies, offers, reviews)
- **Bold/headers** for structure
- **Star ratings** (e.g. ★★★★☆)
- **Bullet lists** for recommendations and next steps
- **Code blocks** — rare but possible

Use a Markdown renderer (e.g. `react-markdown`, `marked`) in your UI.

### Rendering `charts`

When `charts` is non-empty, render each `ChartBlock` as an interactive chart **below** the Markdown response, in the order they appear. Use a chart library like Chart.js or Recharts.

**Chart types and recommended rendering:**

| `chart_type` | Rendering | Best for |
|---|---|---|
| `pie` | Pie chart with labels | Rating distribution |
| `doughnut` | Doughnut with center label | Status breakdown (offers, requests) |
| `bar` | Vertical bar chart | Comparisons |
| `line` | Line chart with data points | Trends over time |

**Chart IDs for the Customer Portal:**

| `id` | When returned | Chart Type | What it shows |
|---|---|---|---|
| `my_offers_by_status` | Activity report | doughnut | Offers grouped by status (Pending, Accepted, Rejected, ...) |
| `my_requests_by_status` | Activity report | doughnut | Service requests grouped by status |
| `my_reviews_by_rating` | Activity report | pie | Reviews grouped by star rating |

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

  switch (chart.chart_type) {
    case "pie":       return <Pie data={chartData} options={{ plugins: { title: { display: true, text: chart.title } } }} />;
    case "doughnut":  return <Doughnut data={chartData} options={{ plugins: { title: { display: true, text: chart.title } } }} />;
    case "bar":       return <Bar data={chartData} options={{ plugins: { title: { display: true, text: chart.title } } }} />;
    case "line":      return <Line data={chartData} options={{ plugins: { title: { display: true, text: chart.title } } }} />;
    default:          return <Bar data={chartData} />;
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

> **Note:** There is no `401` from this endpoint. Auth errors surface inside the `response` text (e.g. "You need to log in to view your offers.").

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

Use this to show connection status in the UI or disable the chat input when the backend is down.

---

## Available Tools (28 total)

The agent has access to these tools. You don't call them directly — the AI decides which to use based on the user's message. Understanding them helps you design the UI and user prompts.

### Auth (5)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `register_customer` | Register new account (creates Lead + Digital Signature) | No |
| `login_customer` | Authenticate, get JWT | No |
| `refresh_token` | Get new access token using refresh token | No |
| `logout` | Revoke current session refresh token | No |
| `logout_all` | Revoke all refresh tokens (all devices) | Yes |

### Company Discovery (5)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `list_companies` | Browse/search companies (name, service type, sort) | No |
| `get_recommended_companies` | AI-ranked recommendations | No |
| `get_trending_companies` | Companies with improving recent reviews | No |
| `get_company_details` | Company info by ID | No |
| `get_company_reviews` | Paginated reviews for a company | No |

### Reviews (4)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `submit_review` | Submit review (1-5 stars + text) | Yes |
| `update_review` | Update own review | Yes |
| `delete_review` | Delete own review | Yes |
| `get_my_reviews` | All reviews by this customer | Yes |

### Profiles (5)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `get_customer_profile` | Get profile (must be accepted by a company) | Yes |
| `update_customer_profile` | Update profile (email cannot change) | Yes |
| `get_lead_profile` | Get lead profile | Yes |
| `update_lead_profile` | Update lead profile | Yes |
| `get_digital_signature` | Get signature (needs password verification) | Yes |

### Offers (4)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `get_my_offers` | All offers/quotes from companies | Yes |
| `get_offer_details` | Single offer with pricing breakdown | Yes |
| `accept_offer` | Accept offer (requires digital signature + payment method) | Yes |
| `reject_offer` | Reject offer (requires reason) | Yes |

### Service Requests (3)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `create_service_request` | Submit inquiry to a company | Yes |
| `get_my_service_requests` | All submitted service requests | Yes |
| `get_service_request_details` | Single request details | Yes |

### Dashboard & Reports (2)
| Tool | Description | Auth Required |
|------|-------------|:---:|
| `get_dashboard` | Summary: total offers, by status, reviews, activity | Yes |
| `generate_my_activity_report` | Full overview: dashboard + offers + reviews + service requests | Yes |

---

## Example Integration (TypeScript)

```typescript
const API_BASE = "https://api.wasla.app";

interface ChatState {
  sessionId: string | null;
  token: string | null;  // JWT from your auth system
}

async function sendMessage(
  message: string,
  state: ChatState
): Promise<{ response: string; sessionId: string; toolCalls: number; charts: ChartBlock[] }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers,
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

async function handleSend(message: string) {
  setLoading(true);
  try {
    const result = await sendMessage(message, {
      sessionId,
      token: authToken,  // from your auth context
    });
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

## UX Recommendations

1. **Show a typing indicator** — the agent may call multiple tools before responding (check `tool_calls_made` to show "Looked up 3 sources" after the response).
2. **Render Markdown** — the response contains tables, bold text, and lists.
3. **Persist `session_id`** — store in component state or session storage. Losing it means losing conversation history.
4. **Handle auth gracefully** — if the response mentions "log in" or "unauthorized", prompt the user to sign in through your auth flow, then retry.
5. **Suggest prompts** — offer quick-action buttons like "Show trending companies", "My offers", "My activity report" to guide users.
6. **New conversation button** — let users start a fresh session by clearing `session_id`.

---

## Conversational Data Gathering

The agent will **ask for required information step by step** before calling create/submit tools. For example, when a user says "I want to submit a review", the agent will ask for the company, rating, and text across multiple turns — then confirm before submitting.

**Frontend implications:**
- Expect multi-turn conversations for create/submit actions
- The agent confirms with a summary before executing — no extra confirmation modals needed
- If the user provides all data upfront, the agent skips the step-by-step and confirms directly
- The `tool_calls_made` will be `0` during gathering turns (the tool is only called after confirmation)

---

## Key Concepts for UI Design

- **Lead vs Customer:** A user starts as a Lead after registration. They become a Customer once accepted by a company. The agent handles both states transparently.
- **Digital Signature:** Auto-generated at registration. Required to accept offers. The agent will ask for the user's password to retrieve it via `get_digital_signature`.
- **Offer acceptance flow:** Get signature (password required) → Accept offer (signature + payment method: COD or Online).
- **The agent confirms destructive actions** (delete review, reject offer) before executing them — you don't need separate confirmation modals for agent actions.
- **Charts appear with reports** — when the user asks for an activity report, the response will include both text AND chart data. Render charts below the Markdown text.
