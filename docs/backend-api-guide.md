# Backend API Guide

This guide is for backend integrators consuming Wasla conversational APIs. It explains authentication, session continuity, endpoint contracts, and error handling so client apps can integrate reliably.

## Authentication

All protected API routes use Bearer token authentication.

- Header format: `Authorization: Bearer <token>`
- Token scope: call only routes your token is authorized for
- Transport: HTTPS only in production environments

### Swagger UI Bearer setup

If you test APIs from Swagger UI:

1. Open the API docs page.
2. Select **Authorize**.
3. Choose **HTTPBearer** and paste only the raw token (JWT string).
4. Execute requests normally; Swagger injects the `Authorization` header.

Do not paste the `Bearer` prefix in the authorize input box. Swagger adds the scheme automatically.

## Session Continuity

Conversation state is preserved with `session_id`.

- **First request**: omit `session_id` to start a new session.
- **Server behavior**: response includes a generated `session_id`.
- **Follow-up requests**: send the same `session_id` to continue context.
- **Session reset**: start a new conversation by omitting the previous `session_id` or using a newly issued one.

Recommended client behavior:

- Persist `session_id` per active conversation thread.
- Do not reuse the same `session_id` across different users.
- Session memory uses in-process `MemorySaver`; all sessions reset when the API process restarts.

## Endpoints

### `POST /api/chat`

General chat endpoint for user-facing conversational interactions.

Request example:

```json
{
  "message": "What are the required documents for company registration in Cairo?",
  "session_id": "sess_7dbf12a2f8c64d5f9d5f4f2b3a11c901"
}
```

Response example:

```json
{
  "response": "For company registration in Cairo, you typically need...",
  "session_id": "sess_7dbf12a2f8c64d5f9d5f4f2b3a11c901",
  "tool_calls_made": 1,
  "model_used": "qwen2.5:3b",
  "charts": []
}
```

### `POST /api/company/chat`

Company-scoped assistant endpoint for organization-specific workflows and policy-aware responses.

Request example:

```json
{
  "message": "Summarize unpaid invoices older than 30 days.",
  "session_id": "sess_bf1e57f8f1fc4a0a866be1f9e2f646c4"
}
```

Response example:

```json
{
  "response": "You currently have 4 unpaid invoices older than 30 days...",
  "session_id": "sess_bf1e57f8f1fc4a0a866be1f9e2f646c4",
  "tool_calls_made": 3,
  "model_used": "qwen2.5:3b",
  "charts": [
    {
      "id": "ar_over_30_days",
      "chart_type": "bar",
      "title": "Invoices Over 30 Days",
      "labels": ["March", "April", "May"],
      "datasets": [
        {
          "label": "Amount (EGP)",
          "data": [98000, 121000, 87000]
        }
      ]
    }
  ]
}
```

### `GET /health`

Lightweight health probe endpoint for uptime checks and load balancers.

Request: no request body (`GET /health`).

Response example:

```json
{
  "status": "ok",
  "llm_provider": "ollama",
  "main_model": "qwen2.5:3b",
  "fallback_model": "qwen2.5:3b",
  "max_context_tokens": 8192
}
```

## Error Handling Matrix

Use the matrix below to map backend responses to deterministic client actions.

| HTTP Status | Typical Cause | Client Action Guidance |
| --- | --- | --- |
| `200 OK` | Successful graph completion with `ChatResponse` payload | Persist returned `session_id`; render `response`; optionally render any `charts`. |
| `500 Internal Server Error` | Graph finished in an unexpected state (no `AIMessage`) | Treat as non-retryable for the same request body; log payload + timestamp and escalate. |
| `503 Service Unavailable` | LLM/provider/graph invoke failure (provider down, auth/model issues, upstream failure) | Retry with exponential backoff; if persistent, fail over operationally and alert support. |
| `429 Too Many Requests` | Legacy rate-limit path (route-specific and deployment-dependent) | If encountered, honor `Retry-After` when present and back off; do not assume all routes enforce it. |

For support escalation, always log and share:

- endpoint and HTTP method
- request timestamp (UTC)
- response status code
- request body without secrets
