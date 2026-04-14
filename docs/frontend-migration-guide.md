# Frontend Migration Guide — Charts & Conversational Gathering

**Date:** April 2026
**Affects:** Both Customer Portal (`/api/chat`) and Company Portal (`/api/company/chat`)

> This guide covers what changed in the latest backend update. For the full integration docs see `frontend-customer-guide.md` and `frontend-company-guide.md`.

---

## What Changed

| # | Change | Type | Effort |
|---|--------|------|--------|
| 1 | `ChatResponse` has a new `charts` field | **Additive** (non-breaking) | Medium |
| 2 | Agent now asks for data before creating records | **Behavioral** (non-breaking) | None — just be aware |

---

## 1. New `charts` field on `ChatResponse`

### Before

```typescript
interface ChatResponse {
  response: string;
  session_id: string;
  tool_calls_made: number;
  model_used: string;
}
```

### After

```typescript
interface ChatResponse {
  response: string;
  session_id: string;
  tool_calls_made: number;
  model_used: string;
  charts: ChartBlock[];     // NEW — may be empty array
}

interface ChartDataset {
  label: string;            // "Amount (EGP)", "Count", "Completed"
  data: number[];           // one value per label
}

interface ChartBlock {
  id: string;               // "expense_monthly", "offers_by_status", etc.
  chart_type: string;       // "bar" | "line" | "pie" | "doughnut"
  title: string;            // "Monthly Expenses"
  labels: string[];         // X-axis / category labels
  datasets: ChartDataset[]; // one or more data series
}
```

### Is this breaking?

**No.** `charts` defaults to `[]`. Existing frontends that ignore the field continue to work. Charts are purely additive.

### When do charts appear?

Charts are returned when the user triggers **report or chart tools**:

**Company Portal (7 chart IDs):**

| `id` | Triggered by | `chart_type` | Description |
|------|-------------|---|---|
| `expense_monthly` | Business report, Financial report, Expense charts | `bar` | Monthly expense totals |
| `expense_category` | Business report, Financial report, Expense charts | `doughnut` | Expenses by category |
| `offers_by_status` | Business report, Pipeline report | `doughnut` | Offer status distribution |
| `tasks_by_status` | Business report | `doughnut` | Task status distribution |
| `service_requests_by_status` | Pipeline report | `doughnut` | Service request status distribution |
| `employee_tasks` | Team performance report | `bar` | Per-employee completed vs total (multi-dataset) |
| `customer_engagement` | Customer report | `bar` | Top 15 customers: offers vs tasks (multi-dataset) |

**Customer Portal (3 chart IDs):**

| `id` | Triggered by | `chart_type` | Description |
|------|-------------|---|---|
| `my_offers_by_status` | Activity report | `doughnut` | User's offers by status |
| `my_requests_by_status` | Activity report | `doughnut` | User's service requests by status |
| `my_reviews_by_rating` | Activity report | `pie` | User's reviews by star rating |

For regular queries ("show my tasks", "list customers"), `charts` will be `[]`.

### Minimal integration (5 minutes)

If you just want to not break, add the type and ignore the data:

```typescript
// Just add charts to your type — no rendering needed yet
const data: ChatResponse = await res.json();
// data.charts exists but you can ignore it
```

### Full integration (render charts)

Install a chart library and render inline:

```bash
npm install chart.js react-chartjs-2
```

```tsx
import { Bar, Doughnut, Pie, Line } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, ArcElement, PointElement, LineElement,
  Title, Tooltip, Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend
);

function ChatChart({ chart }: { chart: ChartBlock }) {
  const data = {
    labels: chart.labels,
    datasets: chart.datasets.map((ds) => ({
      label: ds.label,
      data: ds.data,
    })),
  };
  const opts = {
    responsive: true,
    plugins: { title: { display: true, text: chart.title } },
  };

  switch (chart.chart_type) {
    case "pie":      return <Pie data={data} options={opts} />;
    case "doughnut": return <Doughnut data={data} options={opts} />;
    case "line":     return <Line data={data} options={opts} />;
    default:         return <Bar data={data} options={opts} />;
  }
}
```

Then in your message component:

```tsx
function AssistantMessage({ response, charts }: ChatResponse) {
  return (
    <div>
      <Markdown>{response}</Markdown>
      {charts.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: 16, marginTop: 16 }}>
          {charts.map((c) => <ChatChart key={c.id} chart={c} />)}
        </div>
      )}
    </div>
  );
}
```

### Multi-dataset charts

Some charts have 2+ datasets (e.g., `employee_tasks` has "Completed" and "Total Assigned"). Chart.js renders these as grouped bars automatically — no extra config needed.

```json
{
  "id": "employee_tasks",
  "chart_type": "bar",
  "title": "Employee Task Overview",
  "labels": ["Ahmed", "Sara", "Omar"],
  "datasets": [
    { "label": "Completed", "data": [12, 8, 15] },
    { "label": "Total Assigned", "data": [14, 10, 16] }
  ]
}
```

---

## 2. Conversational Data Gathering

### Before

The agent would call create/update tools immediately, sometimes with incomplete or hallucinated data.

### After

For **create and update actions**, the agent now:

1. Asks for required fields step by step
2. Summarizes the data and asks "Shall I go ahead?"
3. Only calls the tool after confirmation

### Example conversation

```
User:    "I want to create a new customer"
Agent:   "Sure! What's their full name?"
User:    "Ahmed Hassan"
Agent:   "What's Ahmed's email and phone number?"
User:    "ahmed@example.com, 01012345678"
Agent:   "And the address?"
User:    "15 Nile St, Cairo, 11511, Egypt"
Agent:   "Here's what I'll create:
          • Name: Ahmed Hassan
          • Email: ahmed@example.com
          • Phone: 01012345678
          • Address: 15 Nile St, Cairo, 11511, Egypt
          Shall I go ahead?"
User:    "Yes"
Agent:   "Done! Customer Ahmed Hassan has been created."
```

### Frontend implications

| What | Impact |
|------|--------|
| Extra turns needed | Data-gathering turns have `tool_calls_made: 0` and `charts: []` — render as normal text |
| No UI modals needed | The agent handles confirmation in-chat — no separate modal for "are you sure?" |
| Shortcut still works | If user says "Create customer Ahmed, ahmed@email.com, 01012345678, Cairo" in one message, the agent skips steps and confirms directly |
| No code changes needed | This is purely a behavioral change in the AI — the API contract is the same |

---

## Migration Checklist

- [ ] Update your `ChatResponse` TypeScript interface to include `charts: ChartBlock[]`
- [ ] (Optional) Install `chart.js` + `react-chartjs-2` and add the `ChatChart` component
- [ ] (Optional) Add a chart grid below message text when `charts.length > 0`
- [ ] Test with: "Generate a business report" (Company) or "Show my activity report" (Customer)
- [ ] Verify regular messages still work with `charts: []`

**Total effort:** ~30 min for full chart rendering, 0 min if you just want to ignore charts for now.
