# Tasks: Customer Portal Agent Prompt

**Input**: Design documents from `/specs/001-customer-portal-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/customer-portal-api.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add the new dependency and configuration required by the customer portal agent.

- [X] T001 Add `httpx>=0.27.0,<1.0` dependency to requirements.txt
- [X] T002 [P] Add CRM API config fields (`crm_api_base_url`, `crm_api_timeout_seconds`, `max_customer_portal_tool_iterations`) to app/core/config.py
- [X] T003 [P] Add `CRM_API_BASE_URL`, `CRM_API_TIMEOUT_SECONDS`, `MAX_CUSTOMER_PORTAL_TOOL_ITERATIONS` to .env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented. Includes the CRM HTTP client, tool dispatch system, LLM service extension, system prompt skeleton, request models, route, and main app registration.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create CRM client service in app/services/crm_client.py with singleton `httpx.AsyncClient`, lifecycle management (`init_crm_client`/`close_crm_client`), configurable timeout, structured error mapping (400→bad_request, 401→unauthorized, 404→not_found, 409→conflict, 422→unprocessable, 5xx→service_error), and typed async methods for all 21 CRM API endpoints grouped by domain (companies, service-requests, offers, reviews, profiles, dashboard)
- [X] T005 [P] Add empty `CUSTOMER_PORTAL_TOOLS` list and `customer_portal_tools_to_description()` helper function to app/tools/schemas.py
- [X] T006 [P] Add `_CUSTOMER_PORTAL_REGISTRY` dict and `execute_customer_portal_tool(tool_name, arguments, bearer_token)` dispatcher to app/tools/registry.py
- [X] T007 [P] Create customer portal system prompt template in app/prompts/customer_portal_prompt.py with role definition (customer assistant for Wasla CRM), mission (discover companies, manage requests/offers/reviews/profiles), core principles (confirm before acting, summarize intent, handle errors gracefully, maintain context), and `get_customer_portal_system_prompt(tools_description)` function
- [X] T008 Add `customer_portal_chat_with_tools(bearer_token, messages)` function to app/services/llm_service.py using `CUSTOMER_PORTAL_TOOLS`, `execute_customer_portal_tool`, `customer_portal_tools_to_description`, and configurable `max_customer_portal_tool_iterations` (default 5)
- [X] T009 [P] Add `CustomerPortalChatRequest` model and `get_bearer_token` dependency (extracts optional `Authorization` header) to app/api/dependencies.py
- [X] T010 Create customer portal chat route (`POST /api/customer-portal/chat` with tool-calling loop) and stream route (`POST /api/customer-portal/chat/stream` with SSE) in app/api/routes/customer_portal.py
- [X] T011 Register customer portal router in app/main.py and add httpx client lifecycle (`init_crm_client` on startup, `close_crm_client` on shutdown) to FastAPI lifespan

**Checkpoint**: Foundation ready — customer portal routes are live but have no tools. User story implementation can now begin.

---

## Phase 3: User Story 1 — Discover and Compare Service Companies (Priority: P1) 🎯 MVP

**Goal**: Customers can search for companies by service type, view recommended/trending companies, drill into company profiles, and read reviews — all without authentication.

**Independent Test**: Send `POST /api/customer-portal/chat` with prompt "Show me moving companies in Zurich" — agent should call `search_companies` and return a list. Follow up with "Tell me about the first one" — agent should call `get_company_profile`. Ask "Show me their reviews" — agent should call `get_company_reviews`.

### Implementation for User Story 1

- [X] T012 [P] [US1] Add `search_companies` tool schema (mode: list/recommended/trending, service_type, search, sort_by, page_index, page_size) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T013 [P] [US1] Add `get_company_profile` tool schema (company_id) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T014 [P] [US1] Add `get_company_reviews` tool schema (company_id, sort_by, page_index, page_size) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T015 [P] [US1] Create app/tools/customer_portal_ops.py with `search_companies`, `get_company_profile`, `get_company_reviews` operations that call CRM client public endpoint methods (no bearer token needed)
- [X] T016 [US1] Register `search_companies`, `get_company_profile`, `get_company_reviews` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T017 [US1] Add company discovery behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: present companies with name/rating/service types, explain recommended vs trending, handle 404 gracefully, support pagination

**Checkpoint**: User Story 1 is fully functional. Customers can discover and compare companies through the agent. This is the MVP.

---

## Phase 4: User Story 2 — Submit a Service Request (Priority: P2)

**Goal**: Authenticated customers can submit service requests to companies, with the agent gathering details (date, addresses, notes) before submission. Customers can also track their submitted requests.

**Independent Test**: Send `POST /api/customer-portal/chat` with bearer token and prompt "I want to request moving services from Swift Movers for next Monday" — agent should gather details and call `submit_service_request`. Follow up with "Show me my requests" — agent should call `get_my_service_requests`.

### Implementation for User Story 2

- [X] T018 [P] [US2] Add `submit_service_request` tool schema (company_id, preferred_date, origin_address, destination_address, notes) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T019 [P] [US2] Add `get_my_service_requests` tool schema (request_id, status, page_index, page_size) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T020 [P] [US2] Implement `submit_service_request` and `get_my_service_requests` operations in app/tools/customer_portal_ops.py (call CRM client authenticated endpoints with bearer token)
- [X] T021 [US2] Register `submit_service_request`, `get_my_service_requests` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T022 [US2] Add service request behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: prompt for missing details before submitting, confirm before executing, handle 404 (company not found), prompt for auth if token missing

**Checkpoint**: User Stories 1 and 2 both work independently. Customers can discover companies AND submit service requests.

---

## Phase 5: User Story 3 — Manage Offers (Priority: P2)

**Goal**: Authenticated customers can view pending offers, review offer details with line items, accept offers (with digital signature and payment method choice), or reject offers with a reason.

**Independent Test**: Send prompt "Show me my pending offers" — agent calls `get_my_offers`. "Show details of offer 15" — agent calls `get_my_offers` with offer_id. "Accept it with COD, my signature is SIG-ABC12-34567" — agent calls `accept_offer`. Test rejection: "Reject offer 16, reason: too expensive" — agent calls `reject_offer`.

### Implementation for User Story 3

- [X] T023 [P] [US3] Add `get_my_offers` tool schema (offer_id, status, page_index, page_size) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T024 [P] [US3] Add `accept_offer` tool schema (offer_id, digital_signature, payment_method) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T025 [P] [US3] Add `reject_offer` tool schema (offer_id, rejection_reason) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T026 [P] [US3] Implement `get_my_offers`, `accept_offer`, `reject_offer` operations in app/tools/customer_portal_ops.py (call CRM client authenticated endpoints, handle COD vs Online payment responses)
- [X] T027 [US3] Register `get_my_offers`, `accept_offer`, `reject_offer` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T028 [US3] Add offer management behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: explain COD vs Online payment, confirm before accepting/rejecting, handle terminal state errors (400), invalid signature (401), missing payment config (422), present Stripe checkout URL for online payments

**Checkpoint**: User Stories 1–3 all work. The core transaction flow (discover → request → offer management) is complete.

---

## Phase 6: User Story 4 — Write and Manage Reviews (Priority: P3)

**Goal**: Authenticated customers can submit, update, and delete reviews for companies. They can also view all their reviews across companies.

**Independent Test**: Send prompt "I want to review Swift Movers, 5 stars, excellent service" — agent calls `manage_review` with action=submit. "Update my review to 4 stars" — action=update. "Show all my reviews" — action=list_mine. "Delete my review for Swift Movers" — action=delete with confirmation.

### Implementation for User Story 4

- [X] T029 [P] [US4] Add `manage_review` tool schema (action: submit/update/delete/list_mine, company_id, rating, review_text, page_index, page_size) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T030 [P] [US4] Implement `manage_review` operation in app/tools/customer_portal_ops.py with action routing (submit→POST, update→PUT, delete→DELETE, list_mine→GET /my/reviews), handle 409 conflict (already reviewed), 400 moderation rejection
- [X] T031 [US4] Register `manage_review` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T032 [US4] Add review management behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: confirm before submitting/deleting, handle moderation rejection with revision suggestion, detect 409 and offer update instead, present rating as 1-5 stars

**Checkpoint**: User Stories 1–4 all work. Customers can discover, request, manage offers, and review companies.

---

## Phase 7: User Story 5 — Manage Profile and Lead Information (Priority: P3)

**Goal**: Authenticated customers can view and update their customer profile and lead profile, including seeing all company connection history.

**Independent Test**: Send prompt "Show me my profile" — agent calls `get_my_profile` with profile_type=customer. "Show my company connections" — calls `get_my_profile` with profile_type=lead. "Update my address to Bahnhofstrasse 10" — calls `update_my_profile`.

### Implementation for User Story 5

- [X] T033 [P] [US5] Add `get_my_profile` tool schema (profile_type: customer/lead) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T034 [P] [US5] Add `update_my_profile` tool schema (profile_type, first_name, last_name, email, phone_number, address, city, zip_code, country) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T035 [P] [US5] Implement `get_my_profile` and `update_my_profile` operations in app/tools/customer_portal_ops.py (route by profile_type to /my/profile or /my/lead-profile)
- [X] T036 [US5] Register `get_my_profile`, `update_my_profile` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T037 [US5] Add profile management behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: show connection statuses (Pending/Accepted/Rejected), confirm before updates, explain lead profile pre-fill behavior

**Checkpoint**: User Stories 1–5 all work. Only dashboard remains.

---

## Phase 8: User Story 6 — View Dashboard Summary (Priority: P3)

**Goal**: Authenticated customers can ask for a quick overview and receive dashboard metrics (open requests, active offers, recent activity).

**Independent Test**: Send prompt "Give me an overview of my activity" — agent calls `get_dashboard` and presents summary metrics. Test with empty activity: agent should suggest discovering companies.

### Implementation for User Story 6

- [X] T038 [P] [US6] Add `get_dashboard` tool schema (no parameters) to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py
- [X] T039 [P] [US6] Implement `get_dashboard` operation in app/tools/customer_portal_ops.py (call CRM client /my/dashboard endpoint)
- [X] T040 [US6] Register `get_dashboard` in `_CUSTOMER_PORTAL_REGISTRY` in app/tools/registry.py
- [X] T041 [US6] Add dashboard behavior instructions to system prompt in app/prompts/customer_portal_prompt.py: present metrics clearly, suggest actions for zero-activity customers, use dashboard as conversation opener

**Checkpoint**: All 6 user stories are complete. All 12 tools covering 21 CRM API endpoints are functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that span multiple user stories.

- [X] T042 [P] Update README.md with customer portal agent section: overview, new routes, environment variables, usage examples
- [X] T043 [P] Add structured logging for all customer portal operations in app/tools/customer_portal_ops.py (log tool name, parameters, CRM API response status, timing)
- [X] T044 Review and optimize system prompt token usage in app/prompts/customer_portal_prompt.py to ensure total prompt (system + tools + history) fits within 8,192 token context window
- [ ] T045 Validate end-to-end by running quickstart.md verification commands (public search, authenticated offer management, error handling)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–8)**: All depend on Foundational phase completion
  - User stories can then proceed in priority order (P1 → P2 → P3)
  - US2 and US3 (both P2) can run in parallel after US1
  - US4, US5, and US6 (all P3) can run in parallel after US1
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — No dependencies on other stories. **MVP scope.**
- **US2 (P2)**: Can start after Foundational — Independent of US1 (different tools, different CRM endpoints)
- **US3 (P2)**: Can start after Foundational — Independent of US1 and US2
- **US4 (P3)**: Can start after Foundational — Independent of all other stories
- **US5 (P3)**: Can start after Foundational — Independent of all other stories
- **US6 (P3)**: Can start after Foundational — Independent of all other stories

**Note**: All user stories are truly independent because each adds its own tool schemas, operations, and registry entries. The only shared resources are the files themselves (`schemas.py`, `registry.py`, `customer_portal_ops.py`, `customer_portal_prompt.py`), but tasks within each story modify different sections of these files.

### Within Each User Story

1. Tool schemas [P] and tool operations [P] can run in parallel
2. Registry registration depends on both schemas and operations being defined
3. Prompt instructions can run in parallel with registry but should be last for coherence

### Parallel Opportunities

**Phase 2 parallel batch**:
- T005, T006, T007, T009 can all run in parallel (different files, no dependencies)

**Phase 3 (US1) parallel batch**:
- T012, T013, T014, T015 can all run in parallel (schemas + operations creation)

**Across user stories** (after foundational):
- US1 (T012–T017) and US2 (T018–T022) can run in parallel if modifying different file sections
- US4 (T029–T032), US5 (T033–T037), US6 (T038–T041) can all run in parallel

---

## Parallel Example: User Story 1

```text
# Launch schemas and operations in parallel:
Task: "Add search_companies schema to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py"
Task: "Add get_company_profile schema to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py"
Task: "Add get_company_reviews schema to CUSTOMER_PORTAL_TOOLS in app/tools/schemas.py"
Task: "Create customer_portal_ops.py with search/profile/reviews operations"

# Then sequentially:
Task: "Register US1 tools in registry"
Task: "Add discovery instructions to system prompt"
```

## Parallel Example: P3 Stories

```text
# After foundational, launch all P3 stories in parallel:
Task: "US4 — Add manage_review schema, operation, registration, prompt"
Task: "US5 — Add profile schemas, operations, registration, prompt"
Task: "US6 — Add dashboard schema, operation, registration, prompt"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T011)
3. Complete Phase 3: User Story 1 (T012–T017)
4. **STOP and VALIDATE**: Test company discovery through the agent
5. Deploy/demo if ready — customers can already discover and compare companies

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → **Deploy (MVP!)**
3. Add US2 + US3 → Test independently → Deploy (core transaction flow complete)
4. Add US4 + US5 + US6 → Test independently → Deploy (full feature set)
5. Polish → Final validation → Production-ready

### Sequential Solo Developer Path

1. Phases 1–2: Setup + Foundation (T001–T011)
2. Phase 3: US1 — MVP ✓
3. Phase 4: US2 — Service requests ✓
4. Phase 5: US3 — Offer management ✓
5. Phase 6: US4 — Reviews ✓
6. Phase 7: US5 — Profiles ✓
7. Phase 8: US6 — Dashboard ✓
8. Phase 9: Polish ✓

---

## Notes

- [P] tasks = different files or file sections, no dependencies
- [Story] label maps task to specific user story for traceability
- All user stories are independently testable after the foundational phase
- The system prompt grows incrementally — each user story adds its behavior section
- Tool schemas, operations, and registry entries are additive (append-only to shared files)
- The CRM client (T004) is the largest single task — it implements typed methods for all 21 endpoints
- Token budget awareness: monitor prompt size after each user story phase
