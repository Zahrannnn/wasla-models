# Implementation Plan: Customer Portal Agent Prompt

**Branch**: `001-customer-portal-agent` | **Date**: 2026-03-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-customer-portal-agent/spec.md`

## Summary

Build an AI agent prompt and tool integration that enables the Wasla CRM backend to act on behalf of customers in the Customer Portal. The agent discovers service companies, submits service requests, manages offers (accept/reject with digital signature and payment), writes/manages reviews, and handles profile and dashboard retrieval — all through the existing ReAct tool-calling architecture. This requires new tool schemas, async HTTP operations against the Wasla CRM API, a dedicated customer portal system prompt, and a new API route that authenticates customers via JWT bearer tokens rather than the existing company-scoped routing.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.115.6, huggingface_hub >=0.27.1, pydantic 2.10.4, httpx (new — async HTTP client for CRM API calls), tenacity 9.0.0  
**Storage**: N/A — stateless agent; chat history passed by client per constitution  
**Testing**: pytest (to be introduced; no test infrastructure exists yet)  
**Target Platform**: Linux server (Docker-ready via uvicorn)  
**Project Type**: Web service (AI agent backend)  
**Performance Goals**: Agent responses within 10 seconds end-to-end (including CRM API round-trips); CRM API calls under 2 seconds individually  
**Constraints**: HF free-tier rate limits; 8,192 token context window; max 3 tool iterations per request  
**Scale/Scope**: Single-customer sessions; 21 CRM API endpoints to integrate as tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. API-First Design — PASS

| Requirement | Compliance |
|-------------|------------|
| REST endpoint for customer portal chat | New `POST /api/customer-portal/chat` route |
| SSE for streaming | New `POST /api/customer-portal/chat/stream` route |
| JSON input/output with clear schemas | Pydantic request/response models |
| Graceful degradation | Existing fallback model pattern; CRM API timeout handling via httpx |

### II. Responsible AI Resource Management — PASS

| Requirement | Compliance |
|-------------|------------|
| Context window awareness | Existing `context_manager.py` — customer portal prompt + tool descriptions must fit within 8,192 token budget |
| Rate limit handling | Existing `@hf_retry` decorator for HF calls; httpx retry for CRM API calls |
| Fallback strategies | Existing Llama-70B → Qwen-72B fallback chain |
| Token budgets | Chat route: max 1024 output tokens (configurable) |

### III. Observability by Default — PASS

| Requirement | Compliance |
|-------------|------------|
| Structured logging | All new tool operations will log requests/responses |
| Health endpoints | Existing `/health`; no new health checks needed |
| Error propagation | CRM API errors mapped to user-friendly messages per FR-017 |
| Rate limit visibility | Existing Redis-based per-company rate limiting; customer portal adds per-customer scope |

### Security — PASS

| Requirement | Compliance |
|-------------|------------|
| Company isolation | Customer portal is customer-scoped; JWT bearer token provides customer identity |
| API key protection | CRM API base URL and any API keys loaded from environment variables |
| Rate limiting | Per-customer rate limiting via existing Redis sliding-window mechanism |
| Input validation | Pydantic models for all request payloads |

### Development Workflow — PASS

| Requirement | Compliance |
|-------------|------------|
| Service layer pattern | New `services/crm_client.py` for HTTP calls; tools in `tools/` |
| Tool registry pattern | New tools registered in `tools/registry.py` with schemas in `tools/schemas.py` |
| Configuration centralization | CRM API base URL added to `core/config.py` |

## Project Structure

### Documentation (this feature)

```text
specs/001-customer-portal-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── customer-portal-api.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
app/
├── main.py                          # Add customer portal router
├── api/
│   ├── dependencies.py              # Add CustomerPortalChatRequest, get_customer_token
│   └── routes/
│       ├── chat.py                  # Existing (unchanged)
│       ├── voice.py                 # Existing (unchanged)
│       └── customer_portal.py       # NEW — customer portal chat + stream routes
├── core/
│   ├── config.py                    # Add CRM API base URL, customer portal settings
│   └── rate_limit.py               # Existing (unchanged)
├── prompts/
│   ├── __init__.py
│   ├── react_prompt.py             # Existing (unchanged)
│   └── customer_portal_prompt.py   # NEW — customer portal system prompt
├── services/
│   ├── llm_service.py              # Extend to support customer portal tool loop
│   ├── crm_client.py               # NEW — async httpx client for CRM API
│   ├── tts_service.py              # Existing (unchanged)
│   ├── stt_service.py              # Existing (unchanged)
│   └── react_parser.py             # Existing (reused by customer portal)
├── tools/
│   ├── schemas.py                  # Add customer portal tool schemas
│   ├── operations.py               # Existing company-scoped tools (unchanged)
│   ├── customer_portal_ops.py      # NEW — customer portal tool operations
│   └── registry.py                 # Register customer portal tools
└── utils/
    ├── context_manager.py          # Existing (unchanged)
    └── retries.py                  # Existing (unchanged)
```

**Structure Decision**: Follows existing layered architecture. Customer portal additions are placed in parallel files (`customer_portal.py`, `customer_portal_prompt.py`, `customer_portal_ops.py`) to avoid breaking existing company-scoped functionality. The new `crm_client.py` service encapsulates all HTTP communication with the CRM API, keeping tool operations clean.

## Constitution Check — Post-Design Re-evaluation

*Re-evaluated after Phase 1 design completion.*

### I. API-First Design — PASS (confirmed)

- New routes `POST /api/customer-portal/chat` and `POST /api/customer-portal/chat/stream` follow the existing REST + SSE pattern.
- All request/response bodies use Pydantic models with JSON schemas.
- Graceful degradation: httpx client has configurable timeouts; CRM API errors are mapped to structured dicts for LLM interpretation. HF model fallback chain is reused.

### II. Responsible AI Resource Management — PASS (confirmed)

- 12 tool schemas (vs 21 endpoints) keep prompt token overhead manageable (~600-800 tokens for schemas, leaving ~6,400 for conversation + output).
- Max tool iterations increased to 5 (configurable) for multi-step customer workflows — researched in Decision 9.
- Context trimming via existing `context_manager.py` is reused.
- HF retry with exponential backoff via existing `@hf_retry` decorator is reused.

### III. Observability by Default — PASS (confirmed)

- `crm_client.py` logs all outbound requests and responses with structured logging.
- Tool execution logging in `registry.py` applies to customer portal tools via the new `execute_customer_portal_tool()` dispatcher.
- CRM API errors are mapped to descriptive error objects (Decision 7) — no opaque failures.

### Security — PASS (confirmed)

- JWT bearer token is forwarded to CRM API, not validated locally (Decision 3) — auth boundary stays at CRM API.
- Per-customer rate limiting via existing Redis sliding-window mechanism.
- All request payloads validated via Pydantic models.
- No secrets stored: CRM API base URL from env vars, JWT from request headers.

### Development Workflow — PASS (confirmed)

- Tool schemas in `tools/schemas.py`, operations in `tools/customer_portal_ops.py`, registry in `tools/registry.py` — follows constitution pattern.
- CRM HTTP client in `services/crm_client.py` — follows service layer pattern.
- Config additions in `core/config.py` — follows configuration centralization.
- No new patterns or abstractions introduced beyond what the constitution requires.

**Post-design verdict**: All constitution gates pass. No violations or complexity justifications needed.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
