# Wasla Backend Professional Documentation & FastAPI Docs Enhancement Design

**Date:** 2026-04-14
**Status:** Approved
**Scope:** Backend-facing documentation package + FastAPI OpenAPI/Swagger/ReDoc quality upgrade

---

## Goals

1. Produce professional backend documentation that serves both internal engineers and API integrators.
2. Document key techniques used to build the backend in practical, implementation-grounded language.
3. Add maintainable architecture and flow diagrams using Mermaid (Markdown-native).
4. Upgrade generated FastAPI docs (`/docs`, `/redoc`, `/openapi.json`) to be descriptive, consistent, and integration-friendly.

## Non-Goals

- No API behavior changes.
- No endpoint path changes.
- No business-logic refactoring unrelated to documentation clarity.
- No custom Swagger UI branding/theme work in this phase.

---

## Audience & Tone

**Primary audience:** mixed:
- Internal backend developers
- Frontend/mobile/API integrators

**Documentation tone:** balanced:
- Clear enough for integrators to consume quickly
- Technical enough for backend engineers to understand implementation choices

---

## Chosen Approach

### Approach Selected: Split by Intent (Recommended)

Create two high-value backend docs plus OpenAPI metadata improvements:

1. `docs/backend-architecture-guide.md`
2. `docs/backend-api-guide.md`
3. FastAPI docs metadata enrichment across app/router/schema layers

### Why this approach

- Avoids a single oversized "all-in-one" file.
- Keeps conceptual architecture and practical API usage separately readable.
- Makes docs easier to maintain as endpoints and internals evolve.
- Aligns Markdown docs with generated API docs so wording remains consistent.

---

## Deliverables

### 1) `docs/backend-architecture-guide.md`

A technical architecture guide focused on "how the backend works."

**Sections**
- Purpose and audience
- Backend system context
- Module boundaries (api/customer/company/shared/utils/core/prompts)
- Techniques used in implementation
- Reliability and error-handling strategy
- Authentication and request context strategy
- Backend request lifecycle walkthrough

**Required Mermaid diagrams**
- Component architecture diagram
- Chat request sequence diagram (`POST /api/chat`)
- Auth handling flow
- Error propagation flow

### 2) `docs/backend-api-guide.md`

A practical integration guide focused on "how to consume the backend safely."

**Sections**
- Base URL and environment conventions
- Authentication usage and bearer token expectations
- Endpoint reference (starting with chat + health routes)
- Request/response examples
- Session continuity behavior
- Error matrix + recommended client actions
- Integrator notes (timeouts, retries, markdown rendering expectations, charts if present)

### 3) FastAPI generated docs upgrade

Enhance OpenAPI metadata so `/docs` and `/redoc` become professional and descriptive.

**Improvement layers**
- **App-level:** clearer title/description/version/tag metadata
- **Route-level:** meaningful summaries/descriptions/responses/examples
- **Schema-level:** polished field descriptions/examples for request/response models

---

## FastAPI Documentation Upgrade Design

### App-Level (`app/main.py`)

- Refine `FastAPI(...)` metadata text to match current architecture and domain split.
- Ensure tag metadata is explicit and user-centered (who should use each endpoint group).
- Keep descriptions consistent with Markdown docs terminology (session, tool calls, model used, charts).

### Route-Level (`app/api/routes/chat.py`, `app/api/routes/company_chat.py`)

- Ensure each endpoint includes:
  - `summary` with one-line purpose
  - `description` with practical behavior notes
  - `responses` mapping with clear status-specific meaning and usage guidance
- Clarify auth handling details and expected Swagger bearer input behavior.

### Schema-Level (`app/api/dependencies.py` and related models)

- Improve model field descriptions/examples to avoid ambiguous generated schemas.
- Keep names/types aligned with current contract while improving explanatory quality.
- Ensure response metadata fields are documented in provider-agnostic language.

---

## Diagram Strategy (Mermaid Only)

Because maintainability is a requirement, diagrams will remain in Markdown via Mermaid.

**Diagram standards**
- Keep node names domain-specific and readable.
- Avoid overly dense mega-diagrams; each diagram answers one question.
- Co-locate each diagram with explanatory text in its relevant section.

**Planned diagrams**
1. **Component architecture:** major backend modules and boundaries
2. **Chat sequence flow:** request to response lifecycle including tool orchestration
3. **Auth flow:** bearer extraction and auth-dependent behavior
4. **Error flow:** validation/runtime/service failure handling path

---

## Content Consistency Rules

To keep docs professional and avoid drift:

1. Use one canonical term per concept across all docs and OpenAPI text.
2. Keep error semantics consistent between `responses` docs and markdown error matrices.
3. Keep model/field naming exactly aligned with current API contract.
4. Avoid speculative features or undocumented behavior.

---

## File-Level Change Plan

### New Files

- `docs/backend-architecture-guide.md`
- `docs/backend-api-guide.md`

### Modified Files

- `app/main.py` (OpenAPI metadata/tags/description polish)
- `app/api/routes/chat.py` (route docs enrichment)
- `app/api/routes/company_chat.py` (route docs enrichment)
- `app/api/dependencies.py` (schema description/example polish)

No endpoint logic or data contracts are intentionally changed.

---

## Risks & Mitigations

1. **Risk:** Documentation drift between markdown and code annotations.
   - **Mitigation:** Align terminology first, then update route metadata and schema descriptions in same pass.

2. **Risk:** Overly verbose endpoint descriptions reduce scanability.
   - **Mitigation:** Keep route `summary` concise, move contextual depth to guide docs.

3. **Risk:** Diagrams become stale as architecture evolves.
   - **Mitigation:** Keep diagrams focused and directly tied to stable module boundaries.

---

## Acceptance Criteria

1. Two backend docs exist and are readable for both target audiences.
2. Each new guide contains actionable content and concrete examples.
3. At least four Mermaid diagrams are included across the guides.
4. Swagger/ReDoc endpoint pages include professional summaries/descriptions/response docs.
5. Generated schema documentation is clear for request and response fields.
6. No API behavior regressions introduced by documentation changes.

---

## Out of Scope (Explicit)

- Frontend documentation redesign
- Docs site generator adoption (e.g., MkDocs/Docusaurus)
- API versioning changes
- New endpoint development

