# Wasla AI Agent Backend — Codebase Overhaul Design

**Date:** 2026-04-13
**Status:** Approved
**Scope:** Code quality, folder architecture, clean code, best practices

---

## Goals

1. Eliminate ~580 lines of duplicated code across HTTP clients, tool-calling loops, and auth helpers
2. Replace OpenAI native tool calling with a ReAct (Reasoning + Acting) engine for model portability and reasoning transparency
3. Reorganize folder structure around domain boundaries (customer, company) with shared infrastructure
4. Externalize system prompts to editable markdown files
5. Maintain full backward compatibility — all 3 API endpoints keep their paths and request/response shapes

## Constraints

- Endpoints preserved: `POST /api/chat`, `POST /api/chat/{company_id}`, `POST /api/company/chat`
- Request model (`ChatRequest`) and response model (`ChatResponse`) unchanged
- No tests in this phase — restructuring only
- Python 3.11+, FastAPI, httpx, openai SDK, tenacity, pydantic-settings

---

## Architecture: Domain-Split with Shared Core

### Final Folder Structure

```
app/
├── main.py                          # FastAPI app init, CORS, lifespan (updated imports)
├── __init__.py
│
├── core/                            # UNCHANGED
│   ├── __init__.py
│   ├── config.py                    # Pydantic BaseSettings
│   └── rate_limit.py                # Redis sliding-window limiter
│
├── shared/                          # NEW — shared infrastructure
│   ├── __init__.py
│   ├── http_client.py               # BaseApiClient class
│   ├── react_engine.py              # ReactEngine class
│   ├── react_parser.py              # ReAct text parser (moved from services/)
│   ├── auth.py                      # Bearer extraction + auth guard
│   └── prompts.py                   # load_prompt() helper
│
├── prompts/                         # NEW — externalized prompt markdown files
│   ├── customer_system.md
│   ├── company_system.md
│   └── react_instructions.md
│
├── customer/                        # NEW — customer portal domain
│   ├── __init__.py
│   ├── tools.py                     # schemas + registry merged
│   ├── operations.py                # tool implementations
│   └── client.py                    # CustomerClient(BaseApiClient)
│
├── company/                         # NEW — company portal domain
│   ├── __init__.py
│   ├── tools.py                     # schemas + registry merged
│   ├── operations.py                # tool implementations
│   └── client.py                    # CompanyClient(BaseApiClient)
│
├── api/                             # KEPT — routes become thinner
│   ├── __init__.py
│   ├── dependencies.py              # ChatRequest/ChatResponse (unchanged)
│   └── routes/
│       ├── __init__.py
│       ├── chat.py                  # Customer endpoint (thin, calls ReactEngine)
│       └── company_chat.py          # Company endpoint (thin, calls ReactEngine)
│
└── utils/                           # KEPT
    ├── __init__.py
    ├── context_manager.py           # trim_messages (unchanged)
    └── retries.py                   # tenacity config (unchanged)
```

### Deleted Files

| Old Path | Reason |
|----------|--------|
| `app/tools/` (entire directory — 6 files) | Split into `customer/tools.py` + `company/tools.py` |
| `app/services/backend_client.py` | Replaced by `customer/client.py` extending `BaseApiClient` |
| `app/services/company_client.py` | Replaced by `company/client.py` extending `BaseApiClient` |
| `app/services/llm_service.py` | Replaced by `shared/react_engine.py` |
| `app/services/react_parser.py` | Moved to `shared/react_parser.py` |
| `app/prompts/react_prompt.py` | Content moved to `prompts/react_instructions.md` |
| `app/prompts/__init__.py` | Directory repurposed for `.md` files |
| `app/services/__init__.py` | Directory becomes empty, deleted |

---

## Component Designs

### 1. Shared HTTP Client (`app/shared/http_client.py`)

Replaces the duplicated HTTP logic in `backend_client.py` (~290 lines) and `company_client.py` (~290 lines).

```python
class BaseApiClient:
    """Async HTTP client with auth injection, error mapping, and param cleaning."""

    def __init__(self, base_url: str, timeout: int):
        self._base_url = base_url
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def init(self) -> None:
        """Create the underlying httpx.AsyncClient. Called from app lifespan."""
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self._base_url.rstrip("/"),
            timeout=self._timeout,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        """Close the client. Called from app lifespan."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self, method: str, path: str, *,
        bearer: str | None = None,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        """
        Make an HTTP request. Returns:
        - Success: {"status": "success", "data": <json>}
        - 204:     {"status": "success", "data": None}
        - Error:   {"error": "<type>", "message": "<msg>"}
        """
        # Auth header injection
        # Status code → error type mapping (400→bad_request, 401→unauthorized, etc.)
        # JSON parsing with fallback to raw text
        ...

    @staticmethod
    def clean_params(params: dict) -> dict:
        """Strip None values from query params."""
        return {k: v for k, v in params.items() if v is not None}
```

Domain clients extend this with domain-specific methods:

```python
# customer/client.py
class CustomerClient(BaseApiClient):
    async def list_companies(self, *, page_index=None, page_size=None, ...) -> dict:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, ...})
        return await self.request("GET", "/companies", params=params)
    # ... ~25 methods, each 2-3 lines

# company/client.py
class CompanyClient(BaseApiClient):
    async def get_customers(self, bearer, *, page_index=None, ...) -> dict:
        params = self.clean_params({"pageIndex": page_index, ...})
        return await self.request("GET", "/Customer", bearer=bearer, params=params)
    # ... ~40 methods, each 2-3 lines
```

Clients are instantiated in `main.py` lifespan (not at module level):

```python
# main.py lifespan
customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
await customer_client.init()
await company_client.init()
# Store on app.state for access in routes
app.state.customer_client = customer_client
app.state.company_client = company_client
```

**How operations access the client:** Each domain's operations module receives the client instance via the `ctx` dict. The route injects it:

```python
ctx = {"bearer_token": token, "client": request.app.state.customer_client}
```

Operations then use `ctx["client"]` instead of importing a module-level global:

```python
async def list_companies(ctx: dict, *, page_index=None, ...) -> dict:
    return await ctx["client"].list_companies(page_index=page_index, ...)
```

This eliminates the import-time coupling between operations and client modules.

### 2. ReAct Engine (`app/shared/react_engine.py`)

Replaces both `llm_service.py:chat_with_tools()` and `company_chat.py:_company_chat_with_tools()` with a single ReAct-based agent loop.

```python
class ReactEngine:
    """ReAct agent loop — model-agnostic tool calling via text parsing."""

    def __init__(self, llm_client: AsyncOpenAI, settings: Settings):
        self.client = llm_client
        self.settings = settings

    async def run(
        self,
        messages: list[dict],
        *,
        tools: list[dict],
        tool_executor: Callable[[str, dict | str, dict], Awaitable[str]],
        ctx: dict,
    ) -> dict:
        """
        Execute the ReAct loop.

        Returns: {"response": str, "tool_calls_made": int, "model_used": str}
        """
```

**Loop flow:**

1. Trim messages to fit context budget (`trim_messages`)
2. Call LLM with plain text (no `tools=` parameter) — works with any model
3. Parse response with `react_parser.parse_react_response()`
4. If `Final Answer` → return response
5. If `Action` + `Action Input` → execute tool via `tool_executor`, append `Observation:` to messages, continue
6. If iteration limit → append final-answer prompt, call LLM once more
7. Fallback logic: if primary model fails, switch to `fallback_chat_model`

**ReAct prompt injection:**

The engine prepends ReAct format instructions and tool descriptions to the system prompt. Tool descriptions are generated from the schema dicts (reusing the existing `tools_to_react_description()` pattern).

Message format sent to LLM:
```
[System]: {loaded .md prompt} + {auth status line} + {react_instructions.md} + {tool descriptions}
[User]: ...
[Assistant]: Thought: ... Action: ... Action Input: ...
[User]: Observation: {tool result}
[Assistant]: Thought: ... Final Answer: ...
```

**Key detail:** ReAct uses user/assistant message pairs (not the `tool` role), so it works with models that don't support function calling. The `Observation:` is injected as a user message.

### 3. Shared Auth (`app/shared/auth.py`)

Consolidates three duplicated patterns into two functions:

```python
def extract_bearer(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request,
) -> str | None:
    """Extract bearer token from security scheme or raw Authorization header."""
    # Handles both "Bearer xxx" and raw "eyJ..." formats
    ...

def require_bearer(ctx: dict) -> str | dict:
    """
    Returns the bearer token string, or an error dict if missing.
    Used by operations.py files as an auth guard.
    """
    token = ctx.get("bearer_token")
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return token
```

### 4. Domain Tools (`customer/tools.py`, `company/tools.py`)

Each merges schemas + registry into one file. A tool is defined with its handler reference:

```python
# customer/tools.py
from app.customer import operations as ops

TOOLS = [
    {
        "name": "list_companies",
        "description": "Browse and search companies...",
        "parameters": {"type": "object", "properties": {...}, "required": [...]},
        "handler": ops.list_companies,
    },
    ...
]

_REGISTRY = {t["name"]: t["handler"] for t in TOOLS}

def get_tool_schemas() -> list[dict]:
    """Return tool definitions formatted for ReAct prompt generation."""
    return [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in TOOLS
    ]

def tools_to_react_description() -> str:
    """Convert tool schemas to human-readable text for the ReAct prompt."""
    ...

async def execute_tool(tool_name: str, arguments: dict | str, ctx: dict) -> str:
    """Look up tool by name, execute, return JSON string."""
    ...
```

Company tools preserve the existing alias mapping (`get_top_customers` → `get_customers`, etc.) and the Google search hallucination guard.

### 5. Externalized Prompts (`app/prompts/`)

Three markdown files loaded at startup:

**`customer_system.md`** — Extracted from `chat.py:_BASE_SYSTEM_PROMPT`. Contains the customer portal assistant instructions, key concepts, authentication rules, and behavioral rules. Does NOT contain the auth status line (that's appended dynamically).

**`company_system.md`** — Extracted from `company_chat.py:_SYSTEM_PROMPT`. Contains staff CRM assistant instructions, role descriptions, and behavioral rules.

**`react_instructions.md`** — Extracted from `react_prompt.py:REACT_SYSTEM_TEMPLATE`. Contains the ReAct format instructions (Thought/Action/Action Input/Observation/Final Answer). Has a `{tools_description}` placeholder filled at runtime.

Loaded via `shared/prompts.py`:

```python
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")
```

### 6. Simplified Routes

Routes become thin orchestrators:

```python
# routes/chat.py
@router.post("/api/chat", response_model=ChatResponse)
async def portal_chat(body: ChatRequest, request: Request, credentials=Depends(_bearer)):
    token = extract_bearer(credentials, request)
    ctx = {"bearer_token": token}

    system_prompt = load_prompt("customer_system.md")
    system_prompt += _auth_status_line(token is not None)

    messages = [{"role": "system", "content": system_prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    result = await engine.run(
        messages,
        tools=customer_tools.get_tool_schemas(),
        tool_executor=customer_tools.execute_tool,
        ctx=ctx,
    )
    return ChatResponse(**result)
```

The legacy `/api/chat/{company_id}` endpoint delegates to the same logic (backward compatible).

### 7. Updated `main.py` Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()

    # Redis
    try:
        await asyncio.wait_for(init_redis(), timeout=5.0)
    except asyncio.TimeoutError:
        rl._redis = None

    # HTTP clients (no more module-level globals)
    customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
    company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
    await customer_client.init()
    await company_client.init()
    app.state.customer_client = customer_client
    app.state.company_client = company_client

    # LLM client + ReAct engine (single instance, shared)
    llm_client = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    app.state.engine = ReactEngine(llm_client, s)

    yield

    await company_client.close()
    await customer_client.close()
    await close_redis()
```

No more module-level `AsyncOpenAI(...)` or `httpx.AsyncClient(...)` instantiation at import time.

---

## What Does NOT Change

| Component | Why |
|-----------|-----|
| `core/config.py` | Settings model is stable |
| `core/rate_limit.py` | Redis logic is clean, no duplication |
| `api/dependencies.py` | `ChatRequest`/`ChatResponse` models preserved |
| `utils/context_manager.py` | `trim_messages` works well as-is |
| `utils/retries.py` | Tenacity config is clean |
| API endpoints | All 3 paths and response shapes unchanged |
| `.env` / `docker-compose.yml` | No config changes needed |

---

## Migration Path

This is a single-pass restructure, not incremental. The steps:

1. Create `app/shared/` with new modules (http_client, react_engine, react_parser, auth, prompts)
2. Create `app/prompts/` with extracted `.md` files
3. Create `app/customer/` domain (tools, operations, client)
4. Create `app/company/` domain (tools, operations, client)
5. Update `app/api/routes/` to use new imports
6. Update `main.py` lifespan for proper client/engine initialization
7. Delete old files (`app/tools/`, `app/services/`, `app/prompts/*.py`)
8. Verify all imports resolve and the app starts cleanly

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Total Python files | 26 | 22 |
| Duplicated HTTP client code | ~580 lines across 2 files | 0 (single BaseApiClient) |
| Duplicated tool-calling loops | 2 copies (~60 lines each) | 0 (single ReactEngine) |
| Duplicated auth helpers | 3 copies | 0 (single shared/auth.py) |
| Dead code files | 2 (react_prompt.py, react_parser.py) | 0 (integrated into engine) |
| System prompt location | Inline in 2 route files | 3 editable .md files |
| Module-level side effects | 2 (AsyncOpenAI at import time) | 0 (lifespan init) |
| Model compatibility | Requires native tool calling | Any text-generation model (ReAct) |
