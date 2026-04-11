# Research: Customer Portal Agent

**Branch**: `001-customer-portal-agent` | **Date**: 2026-03-14

## Decision 1: Async HTTP Client for CRM API Calls

**Decision**: Use `httpx` with `AsyncClient` for all outbound HTTP calls to the Wasla CRM API.

**Rationale**: httpx is the standard async HTTP client in the Python ecosystem for FastAPI projects. It provides native `async/await` support, connection pooling via `AsyncClient`, automatic JSON serialization, configurable timeouts, and retry compatibility with tenacity. The existing project already uses async patterns throughout (AsyncInferenceClient, async tool operations), so httpx fits naturally.

**Alternatives considered**:
- `aiohttp`: More mature but heavier API surface, requires manual session lifecycle management, and is being superseded by httpx in modern FastAPI projects.
- `requests` + `asyncio.to_thread`: Would work but wastes a thread per call and loses true async benefits. Only justified if httpx can't be installed.

---

## Decision 2: Tool Architecture — Separate Operations File, Shared Registry

**Decision**: Add customer portal tool schemas to `tools/schemas.py` as a separate `CUSTOMER_PORTAL_TOOLS` list, create `tools/customer_portal_ops.py` for operations, and extend `tools/registry.py` with a `_CUSTOMER_PORTAL_REGISTRY` and dedicated `execute_customer_portal_tool()` dispatcher.

**Rationale**: The existing tool pattern passes `company_id` as the first positional arg to every operation. Customer portal tools need `bearer_token` instead (JWT forwarded from the customer's request). A separate registry dispatcher avoids polluting the existing company-scoped tool path while respecting the constitution's requirement that "New tools MUST be registered in `tools/registry.py` with JSON schemas in `tools/schemas.py`."

**Alternatives considered**:
- Putting everything in the existing `operations.py` and `_REGISTRY`: Would mix two incompatible calling conventions (`company_id` vs `bearer_token`) and make the code confusing.
- Creating entirely separate `customer_portal_schemas.py` and `customer_portal_registry.py`: Would violate the constitution's code organization rule that tools go in `schemas.py` and `registry.py`.

---

## Decision 3: JWT Auth Forwarding Strategy

**Decision**: The customer portal route extracts the `Authorization: Bearer <token>` header from the incoming request and passes it through to every CRM API call via the `crm_client.py` service. The backend does NOT validate the JWT itself — validation is the CRM API's responsibility.

**Rationale**: The Wasla backend is a proxy/agent layer between the customer and the CRM API. It has no access to the CRM API's JWT signing key. Forwarding the token transparently keeps the auth boundary clean: the CRM API is the single source of truth for authentication and authorization. If the token is expired or invalid, the CRM API returns 401, which the agent maps to a user-friendly re-authentication prompt.

**Alternatives considered**:
- Validating the JWT locally: Would require sharing or fetching the CRM API's signing key, creating a tight coupling. Also adds a maintenance burden when key rotation occurs.
- Using API key authentication instead of JWT forwarding: Would require a separate auth mechanism and lose the customer identity context embedded in the JWT.

---

## Decision 4: ReAct vs Native Function-Calling for Customer Portal

**Decision**: Use the native HF function-calling approach (same as existing `chat_with_tools`) rather than the ReAct text-parsing pattern.

**Rationale**: The existing `chat_with_tools()` in `llm_service.py` uses HF's native function-calling API with structured `tool_calls` in the response. This is more reliable than ReAct text parsing (regex-based, fragile with varied model outputs). The ReAct prompt and parser exist in the codebase but are not wired into the main flow — they appear to be an experimental path. The customer portal agent should use the proven native path.

**Alternatives considered**:
- ReAct pattern via `react_prompt.py` + `react_parser.py`: Already present but unused. Regex parsing is brittle with 21 tools and complex argument structures. Would require significant testing to ensure reliability.
- Hybrid (function-calling with ReAct-style thinking): Could work but adds complexity for marginal benefit. The native function-calling already includes tool selection reasoning in the model's internal processing.

---

## Decision 5: Tool Grouping Strategy — 21 Endpoints to ~12 Tools

**Decision**: Group related CRM API endpoints into logical tools that match how customers think about actions, rather than mapping 1:1 to API endpoints.

**Rationale**: With 21 API endpoints, presenting each as a separate tool would overwhelm the LLM's tool selection (more tools = more prompt tokens and more decision confusion). Grouping by domain concept reduces cognitive load for the model and fits better within the 8,192 token context window.

**Tool grouping**:

| Tool Name | Endpoints Covered | Type |
|-----------|------------------|------|
| `search_companies` | GET /companies, GET /recommended-companies, GET /trending-companies | Read (public) |
| `get_company_profile` | GET /companies/{id} | Read (public) |
| `get_company_reviews` | GET /companies/{id}/reviews | Read (public) |
| `submit_service_request` | POST /service-requests | Write (auth) |
| `get_my_service_requests` | GET /my/service-requests, GET /my/service-requests/{id} | Read (auth) |
| `get_my_offers` | GET /my/offers, GET /my/offers/{id} | Read (auth) |
| `accept_offer` | POST /my/offers/{id}/accept | Write (auth) |
| `reject_offer` | POST /my/offers/{id}/reject | Write (auth) |
| `manage_review` | POST/PUT/DELETE /companies/{id}/reviews, GET /my/reviews | Read/Write (auth) |
| `get_my_profile` | GET /my/profile, GET /my/lead-profile | Read (auth) |
| `update_my_profile` | PUT /my/profile, PUT /my/lead-profile | Write (auth) |
| `get_dashboard` | GET /my/dashboard | Read (auth) |

**Total**: 12 tools covering all 21 endpoints.

**Alternatives considered**:
- 1:1 mapping (21 tools): Too many tools, exceeds practical prompt budget. Each tool schema is ~50-80 tokens; 21 tools = ~1,200 tokens for schemas alone, leaving limited space for conversation history.
- Extreme grouping (4-5 mega-tools): Too coarse — the model would need complex parameter switching to distinguish sub-operations, increasing error rate.

---

## Decision 6: CRM Client Service Design

**Decision**: Create `services/crm_client.py` as a singleton `httpx.AsyncClient` with lifecycle managed by FastAPI's lifespan (startup/shutdown). The client provides typed methods for each endpoint group with built-in timeout, error mapping, and structured logging.

**Rationale**: A singleton client enables connection pooling (HTTP/2 keep-alive) for efficient communication with the CRM API. Lifespan management ensures clean startup/shutdown. Typed methods keep tool operations thin (just parameter mapping) while the client handles HTTP concerns.

**Configuration** (added to `core/config.py`):
- `crm_api_base_url`: Base URL for the CRM API (default: `https://api.wasla-crm.com/api/customer-portal`)
- `crm_api_timeout_seconds`: Request timeout (default: 10)

---

## Decision 7: Error Handling Strategy

**Decision**: Map CRM API HTTP status codes to structured error responses in `crm_client.py`. Tool operations return error dicts that the LLM interprets and translates into user-friendly messages.

**Error mapping**:

| CRM Status | Tool Response | Agent Behavior |
|------------|--------------|----------------|
| 200-204 | `{"status": "success", "data": ...}` | Present results |
| 400 | `{"error": "bad_request", "message": "..."}` | Explain validation failure, suggest correction |
| 401 | `{"error": "unauthorized", "message": "..."}` | Prompt re-authentication |
| 404 | `{"error": "not_found", "message": "..."}` | Explain resource not found |
| 409 | `{"error": "conflict", "message": "..."}` | Explain constraint (e.g., already reviewed) |
| 422 | `{"error": "unprocessable", "message": "..."}` | Explain configuration issue |
| 5xx | `{"error": "service_error", "message": "..."}` | Suggest retry |

**Rationale**: Returning structured error dicts rather than raising exceptions allows the LLM to reason about errors and provide helpful responses (e.g., "You've already reviewed this company. Would you like to update your review?"). This aligns with FR-017 (handle all documented error codes with user-friendly explanations).

---

## Decision 8: Customer Portal LLM Service Integration

**Decision**: Extend `llm_service.py` with a new `customer_portal_chat_with_tools()` function that accepts `bearer_token`, uses `CUSTOMER_PORTAL_TOOLS`, and calls `execute_customer_portal_tool()`.

**Rationale**: The existing `chat_with_tools()` is tightly coupled to company-scoped tools (uses global `TOOLS` list and `execute_tool` with `company_id`). Rather than making the existing function generic (which would require changing its signature and all callers), a parallel function keeps the existing path stable while adding the customer portal path.

**Alternatives considered**:
- Making `chat_with_tools()` generic with `tools` and `executor` parameters: Cleaner long-term but riskier short-term. Would require updating the existing chat route and testing for regressions. Can be refactored later.
- Creating an entirely separate LLM service: Overkill — the HF client singletons and retry logic should be shared.

---

## Decision 9: Max Tool Iterations for Customer Portal

**Decision**: Use 5 max tool iterations for the customer portal (vs. 3 for company chat), configurable via `max_customer_portal_tool_iterations` in settings.

**Rationale**: Customer portal workflows are multi-step (e.g., search companies → get profile → get reviews → submit request). The current 3-iteration limit is designed for simpler company-agent tools. 5 iterations covers the most complex customer journey (discover → select → detail → request → confirm) without excessive latency.
