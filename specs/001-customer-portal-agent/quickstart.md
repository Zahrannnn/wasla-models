# Quickstart: Customer Portal Agent

**Branch**: `001-customer-portal-agent` | **Date**: 2026-03-14

## Prerequisites

- Python 3.11+
- Existing Wasla backend running (`uvicorn app.main:app`)
- A valid Wasla CRM API JWT token (for authenticated endpoints)
- Redis running (optional — for rate limiting)

## New Dependency

Add `httpx` to `requirements.txt`:

```
httpx>=0.27.0,<1.0
```

Install:

```bash
pip install -r requirements.txt
```

## New Environment Variables

Add to `.env`:

```env
# Customer Portal CRM API
CRM_API_BASE_URL=https://api.wasla-crm.com/api/customer-portal
CRM_API_TIMEOUT_SECONDS=10

# Customer Portal Agent settings
MAX_CUSTOMER_PORTAL_TOOL_ITERATIONS=5
```

## Files to Create

| File | Purpose |
|------|---------|
| `app/services/crm_client.py` | Async HTTP client for CRM API calls |
| `app/tools/customer_portal_ops.py` | Tool operation implementations |
| `app/prompts/customer_portal_prompt.py` | System prompt for customer portal agent |
| `app/api/routes/customer_portal.py` | FastAPI routes for customer portal chat |

## Files to Modify

| File | Change |
|------|--------|
| `app/core/config.py` | Add CRM API config fields |
| `app/tools/schemas.py` | Add `CUSTOMER_PORTAL_TOOLS` list |
| `app/tools/registry.py` | Add customer portal registry and dispatcher |
| `app/services/llm_service.py` | Add `customer_portal_chat_with_tools()` function |
| `app/api/dependencies.py` | Add `CustomerPortalChatRequest` and `get_bearer_token` dependency |
| `app/main.py` | Register customer portal router, add httpx client lifecycle |
| `requirements.txt` | Add httpx |
| `.env.example` | Add new environment variables |

## Verification

### 1. Public endpoint (no auth)

```bash
curl -X POST http://localhost:8000/api/customer-portal/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me moving companies in Zurich"}'
```

Expected: Agent returns company list from CRM API (public endpoint, no auth needed).

### 2. Authenticated endpoint

```bash
curl -X POST http://localhost:8000/api/customer-portal/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"prompt": "Show me my pending offers"}'
```

Expected: Agent returns offers from CRM API using the forwarded token.

### 3. Error handling

```bash
curl -X POST http://localhost:8000/api/customer-portal/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Accept offer 15 with signature SIG-ABC12-34567 and COD payment"}'
```

Expected: Agent should explain that authentication is required to accept offers.

## Implementation Order

1. **Config** — Add CRM API settings to `core/config.py`
2. **CRM Client** — Create `services/crm_client.py` with httpx AsyncClient
3. **Tool Schemas** — Add `CUSTOMER_PORTAL_TOOLS` to `tools/schemas.py`
4. **Tool Operations** — Create `tools/customer_portal_ops.py`
5. **Tool Registry** — Add customer portal registry to `tools/registry.py`
6. **System Prompt** — Create `prompts/customer_portal_prompt.py`
7. **LLM Service** — Add `customer_portal_chat_with_tools()` to `services/llm_service.py`
8. **Dependencies** — Add request model and auth dependency to `api/dependencies.py`
9. **Route** — Create `api/routes/customer_portal.py`
10. **Main** — Register router and httpx lifecycle in `main.py`
