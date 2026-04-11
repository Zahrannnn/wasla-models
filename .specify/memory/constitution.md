<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: Initial → 1.0.0
Modified principles: N/A (initial creation)
Added sections:
  - Core Principles (3 principles)
  - Security Requirements
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check placeholder exists)
  - .specify/templates/spec-template.md ✅ (Requirements section compatible)
  - .specify/templates/tasks-template.md ✅ (Task categorization compatible)
Follow-up TODOs: None
================================================================================
-->

# Wasla AI Agent Backend Constitution

## Core Principles

### I. API-First Design

All functionality MUST be exposed through well-defined REST or WebSocket interfaces. APIs MUST follow these rules:

- **RESTful endpoints** for synchronous operations (`POST /api/chat/{company_id}`)
- **Server-Sent Events (SSE)** for streaming responses (`/stream` endpoints)
- **WebSocket** for full-duplex communication (voice conversation route)
- **JSON input/output** with clear schema definitions
- **Graceful degradation** when external services (Redis, Hugging Face) are unavailable

**Rationale**: This project is a drop-in replacement for Google Gemini-2.5-Flash. API compatibility and predictability are essential for integration.

### II. Responsible AI Resource Management

AI model usage MUST account for free-tier constraints and context limitations:

- **Context window awareness**: All chat history MUST be trimmed to fit within model limits (8,192 tokens max) via `context_manager.py`
- **Rate limit handling**: All Hugging Face API calls MUST use retry logic with exponential backoff (`@hf_retry` decorator)
- **Fallback strategies**: Primary model failures MUST automatically fall back to alternatives (Llama-70B → Qwen-72B)
- **Token budgets**: Max output tokens MUST be configurable per route type (chat: 1024, voice: 250)

**Rationale**: Free-tier Hugging Face models have strict rate limits and smaller context windows than commercial alternatives. Proactive management prevents service disruption.

### III. Observability by Default

All operations MUST be traceable for debugging and monitoring:

- **Structured logging**: All services MUST log requests, responses, and errors with consistent formatting
- **Health endpoints**: A `/health` endpoint MUST report service status and model availability
- **Error propagation**: Errors MUST be returned with clear HTTP status codes and descriptive messages
- **Rate limit visibility**: Per-company rate limiting MUST be trackable via Redis

**Rationale**: Text I/O architecture enables debuggability. When issues arise in production, clear visibility into model calls, rate limits, and errors is critical.

## Security Requirements

### Authentication & Authorization

- **Company isolation**: All routes MUST validate `company_id` from path parameters
- **API key protection**: `HUGGINGFACE_TOKEN` MUST be loaded from environment variables, never hardcoded
- **Rate limiting**: Per-company sliding-window rate limiting MUST be enforced when Redis is available

### Input Validation

- **Request validation**: All incoming JSON payloads MUST be validated via Pydantic models
- **Audio input limits**: Audio payloads for STT MUST have size limits to prevent memory exhaustion
- **Prompt sanitization**: User prompts MUST be processed through the tool-calling loop to prevent injection

### Data Handling

- **No persistent storage**: Chat history MUST NOT be stored server-side (passed by client)
- **Environment isolation**: All secrets MUST be loaded from `.env` files excluded from version control

## Development Workflow

### Code Organization

- **Service layer pattern**: Business logic MUST live in `services/`, routes in `api/routes/`, models in `core/`
- **Tool registry pattern**: New tools MUST be registered in `tools/registry.py` with JSON schemas in `tools/schemas.py`
- **Configuration centralization**: All settings MUST flow through `core/config.py` using Pydantic BaseSettings

### Adding New Capabilities

1. Define JSON schema in `app/tools/schemas.py`
2. Implement async function in `app/tools/operations.py`
3. Register mapping in `app/tools/registry.py`
4. Document in README.md under "Adding New Tools"

### Testing Expectations

- **Contract tests**: API contracts MUST be tested for stability
- **Integration tests**: Tool-calling loop MUST be tested end-to-end
- **Graceful degradation tests**: Behavior without Redis MUST be verified

## Governance

This constitution supersedes all other development practices and conventions.

**Amendment Process**:
1. Proposed changes MUST be documented with rationale
2. Changes MUST be reviewed for impact on existing routes and services
3. Version MUST be incremented per semantic versioning:
   - **MAJOR**: Breaking changes to principles or governance
   - **MINOR**: New principles or expanded guidance
   - **PATCH**: Clarifications and wording improvements
4. All dependent templates MUST be updated to reflect amendments

**Compliance Review**:
- All pull requests MUST verify adherence to Core Principles
- New features MUST include documentation updates
- Security-sensitive changes MUST be flagged for review

**Version**: 1.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-02-28