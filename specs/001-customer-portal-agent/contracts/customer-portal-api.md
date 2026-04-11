# API Contract: Customer Portal Agent Routes

**Branch**: `001-customer-portal-agent` | **Date**: 2026-03-14

This document defines the API routes that the Wasla backend exposes for the customer portal agent. These are the **inbound** contracts — what frontend clients call to interact with the customer portal agent.

---

## Base Path

`/api/customer-portal`

## Authentication

All routes require a `Authorization: Bearer <token>` header. The backend forwards this token to the CRM API for authentication and does not validate it locally.

---

## Route 1 — Customer Portal Chat (Tool-Calling Loop)

| Property | Value |
|----------|-------|
| **Method** | POST |
| **Path** | `/api/customer-portal/chat` |
| **Auth** | Bearer token (forwarded to CRM API) |
| **Rate Limit** | Per-customer sliding window via Redis |

### Request Body

```json
{
  "prompt": "I need moving services from Zurich to Geneva",
  "conversation_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help you today?"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | The customer's message |
| `conversation_history` | array | No | Previous messages (role + content) |

### Response (200)

```json
{
  "response": "I found 5 moving companies near Zurich. Here are the top-rated ones:\n\n1. **Swift Movers GmbH** — ★4.8 (Moving, Packing)\n2. ...",
  "tool_calls_made": 1,
  "model_used": "meta-llama/Llama-3.3-70B-Instruct"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Agent's response (may contain Markdown) |
| `tool_calls_made` | int | Number of CRM API calls made |
| `model_used` | string | HF model that generated the response |

### Error Responses

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid bearer token (detected via CRM API 401) |
| 429 | Rate limit exceeded |
| 503 | AI model unavailable |

---

## Route 2 — Customer Portal Chat Stream (SSE)

| Property | Value |
|----------|-------|
| **Method** | POST |
| **Path** | `/api/customer-portal/chat/stream` |
| **Auth** | Bearer token (forwarded to CRM API) |
| **Rate Limit** | Per-customer sliding window via Redis |

### Request Body

Same as Route 1.

### Response (200 — text/event-stream)

```
data: I found

data:  5 moving

data:  companies

data: [DONE]

```

Each `data:` frame contains a token fragment. Stream ends with `data: [DONE]`.

**Note**: The streaming route does **not** support tool calling. It is for simple conversational responses only (e.g., follow-up questions, explanations). Clients should use Route 1 for any interaction that may require CRM API calls.

---

## Tool Contracts (Internal — Agent ↔ CRM API)

The following tools are available to the agent during the chat tool-calling loop. Each tool maps to one or more CRM API endpoints. These are internal contracts (not exposed to frontend clients).

### Public Tools (No auth forwarding needed)

#### `search_companies`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mode` | string | Yes | One of: `list`, `recommended`, `trending` |
| `service_type` | string | No | Filter by service type |
| `search` | string | No | Search by company name (list mode only) |
| `sort_by` | string | No | `rating` or `newest` (list mode only) |
| `page_index` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |

#### `get_company_profile`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | int | Yes | Company ID |

#### `get_company_reviews`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | int | Yes | Company ID |
| `sort_by` | string | No | `newest` or `highest-rated` (default: newest) |
| `page_index` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |

### Authenticated Tools (Bearer token forwarded)

#### `submit_service_request`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | int | Yes | Target company |
| `preferred_date` | string | No | ISO 8601 datetime |
| `origin_address` | string | No | Pick-up address |
| `destination_address` | string | No | Delivery address |
| `notes` | string | No | Additional instructions |

#### `get_my_service_requests`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | int | No | Specific request ID (omit for list) |
| `status` | string | No | Filter by status |
| `page_index` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |

#### `get_my_offers`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `offer_id` | int | No | Specific offer ID (omit for list) |
| `status` | string | No | Filter by status |
| `page_index` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |

#### `accept_offer`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `offer_id` | int | Yes | Offer to accept |
| `digital_signature` | string | Yes | Format: SIG-XXXXX-XXXXX |
| `payment_method` | int | Yes | 0 (COD) or 1 (Online) |

#### `reject_offer`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `offer_id` | int | Yes | Offer to reject |
| `rejection_reason` | string | Yes | Reason for rejection |

#### `manage_review`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | `submit`, `update`, `delete`, or `list_mine` |
| `company_id` | int | Conditional | Required for submit/update/delete |
| `rating` | int | Conditional | 1–5, required for submit/update |
| `review_text` | string | No | Review content |
| `page_index` | int | No | For list_mine: page number |
| `page_size` | int | No | For list_mine: items per page |

#### `get_my_profile`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profile_type` | string | Yes | `customer` or `lead` |

#### `update_my_profile`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profile_type` | string | Yes | `customer` or `lead` |
| `first_name` | string | No | Updated first name |
| `last_name` | string | No | Updated last name |
| `email` | string | No | Updated email |
| `phone_number` | string | No | Updated phone |
| `address` | string | No | Updated address |
| `city` | string | No | Updated city |
| `zip_code` | string | No | Updated ZIP |
| `country` | string | No | Updated country |

#### `get_dashboard`

No parameters. Returns summary metrics for the authenticated customer.
