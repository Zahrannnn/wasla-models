# Wasla AI Agent Backend — LangGraph / LangChain Migration Design

**Date:** 2026-04-14
**Status:** Approved
**Scope:** Replace custom ReAct engine with LangGraph StateGraph + LangChain tool calling

---

## Goals

1. Replace the custom `ReactEngine` + `react_parser` with a LangGraph `StateGraph` agent
2. Switch from text-based ReAct parsing to LangChain native tool calling (`bind_tools()`)
3. Adopt LangChain's model abstraction for multi-provider support (`ChatOpenAI`, `ChatOllama`, `ChatAnthropic`)
4. Implement server-side conversation memory via LangGraph checkpointing (session-based API)
5. Convert 67 tools to Pydantic-first `StructuredTool` wrappers without modifying business logic
6. Enable LangChain ecosystem features: `with_fallbacks()`, callbacks, tracing (LangSmith)

## Constraints

- All existing `operations.py` and `client.py` files remain **unchanged** — zero modifications to business logic
- API endpoint paths preserved: `POST /api/chat`, `POST /api/company/chat`, `GET /health`
- API contract changes (breaking): `conversation_history` removed, `session_id` added — acceptable because no frontend exists yet
- Python 3.11+, FastAPI, httpx (still used by domain clients)
- No tests in this phase — migration only

---

## Decisions Log

### 1. LangGraph Approach: Custom StateGraph (not prebuilt)

**Chosen:** Custom `StateGraph` with explicit `agent` and `tools` nodes and conditional edges.

**Rejected alternatives:**
- `create_react_agent()` prebuilt — less control over graph topology, harder to customize for validation nodes or human-in-the-loop
- `AgentExecutor` (LangChain legacy) — actively deprecated in favor of LangGraph, no graph-based control flow

**Why:** Full control over graph topology. Easy to extend with human-in-the-loop, parallel tool calls, or conditional routing in the future.

### 2. Tool Migration: Pydantic-first with StructuredTool

**Chosen:** Define a Pydantic `BaseModel` per tool input, wrap existing functions with `StructuredTool.from_function()`.

**Rejected alternatives:**
- `@tool` decorator — creates tight coupling with LangChain, pollutes business logic docstrings with LLM prompting
- Plain `StructuredTool.from_function()` without schemas — loses type safety, no validation before execution

**Why:** Maximum type safety, catches LLM hallucinations before functions execute, generates perfect JSON schemas. Operations remain framework-agnostic.

### 3. Memory: Server-side checkpointing from Day 1

**Chosen:** LangGraph checkpointing with `MemorySaver` (dev) / `AsyncSqliteSaver` (local prod) / `AsyncPostgresSaver` (distributed prod). Client sends `session_id`, not full conversation history.

**Rejected alternatives:**
- Stateless (client sends `conversation_history`) — forces frontend to manage complex LangChain message structures (ToolCall, ToolMessage), massive network payloads
- Stateless now, design for memory later — delays inevitable migration, frontend would build around wrong contract

**Why:** Drastically simplifies frontend work. Natively unlocks human-in-the-loop and state rewinding. Frontend only needs `session_id` + new message.

### 4. Fallback Logic: LangChain `with_fallbacks()`

**Chosen:** `primary_llm.with_fallbacks([fallback_llm])` at the model level.

**Rejected alternatives:**
- Custom fallback node in LangGraph — clutters the agent graph with infrastructure concerns
- Drop fallback entirely — unacceptable for production reliability

**Why:** Clean separation between agent reasoning (LangGraph) and infrastructure resilience (LangChain). The graph sees a successful response regardless of which model answered.

### 5. Hallucination Guards: Defense-in-depth in ToolNode

**Chosen:** Keep guards in the tool execution layer. LangGraph's built-in `ToolNode` already handles unknown tool names by returning error `ToolMessage` to the LLM, prompting self-correction.

**Rejected alternatives:**
- Drop guards entirely (rely on `bind_tools()`) — risky with free/open-weight fallback models
- Custom validation node in the graph — overcomplicates graph topology

**Why:** `bind_tools()` constrains the LLM but some models still hallucinate. The built-in `ToolNode` catches unknown tools natively. No custom code needed.

### 6. System Prompt Handling: Injected in agent_node, not ainvoke()

**Chosen:** System prompt prepended to messages inside `agent_node()` before calling the LLM. Never saved to checkpointed state.

**Why:** Passing `SystemMessage` via `ainvoke()` would permanently append it to the database on every request. After N turns, the history would contain N duplicate system messages, bloating context and confusing the LLM. By prepending in `agent_node`, the system prompt is ephemeral — used for the LLM call but never persisted.

### 7. Non-serializable Dependencies: RunnableConfig (not state)

**Chosen:** HTTP clients (`CustomerClient`, `CompanyClient`) passed via `RunnableConfig["configurable"]` at graph invocation time. Never stored in `AgentState`.

**Why:** LangGraph checkpointer serializes all state fields to the database. HTTP client objects are not JSON-serializable — including them in state would crash the checkpointer with `TypeError`. `RunnableConfig` is specifically designed for runtime dependencies that should never touch persistence.

---

## Component Designs

### 1. Dependencies & LLM Factory

**New dependencies (`requirements.txt`):**

```
langchain-core>=0.3.0
langchain-openai>=0.3.0
langchain-ollama>=0.3.0
langchain-anthropic>=0.3.0
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=0.1.0
```

**Kept dependencies:**
- `openai>=1.50.0` — required transitively by `langchain-openai` (it imports the `openai` SDK internally)
- `httpx>=0.27.0` — still used by domain clients (`BaseApiClient`)

**New settings in `app/core/config.py`:**

```python
# Provider selection
llm_provider: str = "openrouter"  # "openrouter" | "ollama" | "anthropic"

# Ollama-specific
ollama_base_url: str = "http://localhost:11434"
```

Existing `llm_api_key`, `llm_base_url`, `main_chat_model`, `fallback_chat_model` fields unchanged.

**LLM factory (`app/shared/llm.py`):**

```python
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.core.config import Settings

def _create_provider(settings: Settings, model_name: str) -> BaseChatModel:
    """Instantiate the correct LangChain chat model based on provider setting."""
    match settings.llm_provider:
        case "openrouter":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        case "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model_name,
                base_url=settings.ollama_base_url,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_name,
                api_key=settings.llm_api_key,
            )
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

def create_llm(
    settings: Settings,
    tools: Optional[list[BaseTool]] = None,
) -> BaseChatModel:
    """Create LLM with tools bound and fallback chained."""
    primary = _create_provider(settings, settings.main_chat_model)
    fallback = _create_provider(settings, settings.fallback_chat_model)

    # Bind tools to EACH model individually BEFORE chaining
    # (with_fallbacks() returns RunnableWithFallbacks — bind_tools() on that
    # does not reliably propagate schemas to both models)
    if tools:
        primary = primary.bind_tools(tools)
        fallback = fallback.bind_tools(tools)

    return primary.with_fallbacks([fallback])
```

### 2. LangGraph State & Agent Graph

**State schema (`app/shared/state.py`):**

```python
from typing import Annotated, Any
import operator
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    """Extended state for Wasla agent graph.

    Inherits `messages: list[BaseMessage]` from MessagesState.
    All fields must be JSON-serializable (checkpointer persists state to DB).
    """
    bearer_token: str | None = None
    tool_calls_made: Annotated[int, operator.add] = 0
    model_used: str = ""
```

Key design points:
- `bearer_token` is a serializable string — safe for checkpointing
- `tool_calls_made` uses `operator.add` reducer — returning `{"tool_calls_made": 1}` from any node increments the total automatically
- **No `client` field** — HTTP clients are non-serializable and would crash the checkpointer. Passed via `RunnableConfig` instead.

**Agent graph (`app/shared/agent.py`):**

```python
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.shared.state import AgentState

def build_agent_graph(llm, tools, system_prompt, checkpointer=None):
    """Build the Wasla agent StateGraph.

    Parameters
    ----------
    llm          : BaseChatModel with tools bound and fallbacks chained.
    tools        : List of StructuredTool instances.
    system_prompt: Base system prompt text (from .md file).
    checkpointer : LangGraph checkpointer for session persistence.
    """

    tool_node = ToolNode(tools)

    async def agent_node(state: AgentState):
        # 1. Build dynamic system prompt with auth status
        sys_text = system_prompt
        if state.get("bearer_token"):
            sys_text += "\n\nThe user IS authenticated. Call tools directly."
        else:
            sys_text += (
                "\n\nThe user is NOT authenticated (guest). "
                "Public tools work. For protected actions, suggest they log in first."
            )

        # 2. Prepend SystemMessage to history for LLM (NOT saved to state)
        messages_for_llm = [SystemMessage(content=sys_text)] + state["messages"]

        # 3. Optional: trim long histories to fit context window
        # messages_for_llm = [messages_for_llm[0]] + trim_messages(messages_for_llm[1:], ...)

        # 4. Invoke LLM
        response = await llm.ainvoke(messages_for_llm)

        # 5. Return only the AI response to update persistent state
        return {
            "messages": [response],
            "model_used": response.response_metadata.get("model_name", ""),
        }

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return "end"

    # Build graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
```

**Graph topology:**
```
          ┌──────────┐
    ────▶ │  agent   │ ──── (no tool calls) ──▶ END
          │ (LLM)    │
          └────┬─────┘
               │ (has tool calls)
               ▼
          ┌──────────┐
          │  tools   │
          │(ToolNode)│
          └────┬─────┘
               │
               └──── back to agent
```

LangGraph's `ToolNode`:
- Executes the correct tool based on the `tool_calls` in the AI message
- Handles unknown tool names natively — returns error `ToolMessage` prompting self-correction
- Returns `ToolMessage` objects that get appended to the state

### 3. Tool Migration (Pydantic Schemas + StructuredTool)

**File structure per domain:**

```
app/customer/
├── operations.py    # UNCHANGED — pure business logic
├── schemas.py       # NEW — Pydantic BaseModel per tool input
├── tools.py         # REWRITTEN — StructuredTool wrappers
└── client.py        # UNCHANGED
```

**Example `customer/schemas.py`:**

```python
from pydantic import BaseModel, Field

class RegisterCustomerInput(BaseModel):
    """Register a new customer account."""
    email: str = Field(description="Valid email address")
    password: str = Field(description="Min 6 chars, must contain at least 1 digit")
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")
    phone_number: str | None = Field(default=None, description="Optional phone number")

class ListCompaniesInput(BaseModel):
    """Browse and search companies."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 12)")
    search: str | None = Field(default=None, description="Search by company name")
    service_type: str | None = Field(default=None, description="Filter by service type")
    sort_by: str | None = Field(default=None, description="Sort by: 'rating', 'name', 'newest'")

# ... one BaseModel per tool (27 total for customer, 40 for company)
```

**Example `customer/tools.py` (rewritten):**

```python
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from typing import Annotated, Any

from app.customer import operations as ops
from app.customer.schemas import RegisterCustomerInput, ListCompaniesInput  # ...

async def _register_customer_wrapper(
    bearer_token: Annotated[str | None, InjectedState("bearer_token")],
    config: RunnableConfig,
    **kwargs,
):
    """Bridge between LangGraph and legacy business logic."""
    client = config.get("configurable", {}).get("client")
    ctx = {"bearer_token": bearer_token, "client": client}
    return await ops.register_customer(ctx, **kwargs)

async def _list_companies_wrapper(
    bearer_token: Annotated[str | None, InjectedState("bearer_token")],
    config: RunnableConfig,
    **kwargs,
):
    client = config.get("configurable", {}).get("client")
    ctx = {"bearer_token": bearer_token, "client": client}
    return await ops.list_companies(ctx, **kwargs)

# ... one wrapper per tool

def _make_customer_tools() -> list[StructuredTool]:
    """Build all customer portal LangChain tools."""
    return [
        StructuredTool.from_function(
            coroutine=_register_customer_wrapper,
            name="register_customer",
            description=(
                "Register a new customer account. Creates a Lead record "
                "and generates a Digital Signature automatically."
            ),
            args_schema=RegisterCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_list_companies_wrapper,
            name="list_companies",
            description="Browse and search companies on the platform. No authentication required.",
            args_schema=ListCompaniesInput,
        ),
        # ... 27 total
    ]

TOOLS = _make_customer_tools()
```

**How it works end-to-end:**
1. LLM sees tool schemas derived from Pydantic models (via `bind_tools()`)
2. LLM produces a structured `tool_calls` response
3. LangGraph's `ToolNode` validates arguments against the Pydantic schema
4. Wrapper function receives validated `**kwargs` + `bearer_token` (from state) + `RunnableConfig` (with client)
5. Wrapper builds legacy `ctx` dict and calls the unchanged `operations.py` function
6. Result returned as `ToolMessage` to the LLM

### 4. Session Management & API Contract

**New API contract (`app/api/dependencies.py`):**

```python
class ChatRequest(BaseModel):
    """Request body for chat endpoints."""
    message: str = Field(
        ..., min_length=1,
        description="The user's message to the AI assistant.",
        json_schema_extra={"examples": ["Show me the top 5 customers"]},
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Session ID for conversation continuity. "
            "Omit on first message to create a new session."
        ),
    )

class ChatResponse(BaseModel):
    """Response body from chat endpoints."""
    response: str = Field(
        description="The AI assistant's response text (may contain Markdown).",
    )
    session_id: str = Field(
        description="Session ID — pass this back in the next request to continue the conversation.",
    )
    tool_calls_made: int = Field(
        default=0,
        description="Number of tool calls executed during this request.",
    )
    model_used: str = Field(
        default="",
        description="The LLM model that produced the response.",
    )
```

**Changes from current contract:**
- `prompt` renamed to `message`
- `conversation_history` removed — server manages state via checkpointer
- `session_id` added to request (optional, omit for new session) and response (always returned)

**Route integration (`app/api/routes/chat.py`):**

```python
from uuid import uuid4
from langchain_core.messages import HumanMessage

@router.post("/api/chat", response_model=ChatResponse)
async def portal_chat(body: ChatRequest, request: Request, credentials=Depends(_bearer)):
    token = extract_bearer(credentials, request)
    session_id = body.session_id or str(uuid4())

    graph = request.app.state.customer_graph

    run_config = {
        "configurable": {
            "thread_id": session_id,
            "client": request.app.state.customer_client,
        }
    }

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=body.message)],
            "bearer_token": token,
        },
        config=run_config,
    )

    ai_message = result["messages"][-1]

    return ChatResponse(
        response=ai_message.content,
        session_id=session_id,
        tool_calls_made=result.get("tool_calls_made", 0),
        model_used=result.get("model_used", ""),
    )
```

**Checkpointer setup in `app/main.py` lifespan:**

```python
from langgraph.checkpoint.memory import MemorySaver
# Production: from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()

    # Redis (rate limiting)
    try:
        await asyncio.wait_for(init_redis(), timeout=5.0)
    except asyncio.TimeoutError:
        rl._redis = None

    # HTTP clients
    customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
    company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
    await customer_client.init()
    await company_client.init()
    app.state.customer_client = customer_client
    app.state.company_client = company_client

    # Checkpointer
    checkpointer = MemorySaver()  # Swap for AsyncSqliteSaver/AsyncPostgresSaver in production

    # LLM + Graphs
    from app.customer.tools import TOOLS as customer_tools
    from app.company.tools import TOOLS as company_tools

    customer_llm = create_llm(s, tools=customer_tools)
    company_llm = create_llm(s, tools=company_tools)

    app.state.customer_graph = build_agent_graph(
        llm=customer_llm,
        tools=customer_tools,
        system_prompt=load_prompt("customer_system.md"),
        checkpointer=checkpointer,
    )
    app.state.company_graph = build_agent_graph(
        llm=company_llm,
        tools=company_tools,
        system_prompt=load_prompt("company_system.md"),
        checkpointer=checkpointer,
    )

    yield

    await company_client.close()
    await customer_client.close()
    await close_redis()
```

**Multi-worker deployment note:** `MemorySaver` stores state in application RAM — only works with a single Uvicorn worker. For multi-worker or containerized deployments, swap to `AsyncSqliteSaver` (single server) or `AsyncPostgresSaver` (distributed). The checkpointer is a constructor argument — swapping requires changing one line.

### 5. Context Window Management

`app/utils/context_manager.py` (`trim_messages`) is kept and can be used inside `agent_node` for long conversations:

```python
async def agent_node(state: AgentState):
    full_history = state["messages"]
    safe_history = trim_messages(full_history, max_input_tokens=8000)
    messages_for_llm = [SystemMessage(content=sys_text)] + safe_history
    response = await llm.ainvoke(messages_for_llm)
    # ...
```

The full conversation history remains in the checkpointer database. Only the trimmed window is sent to the LLM. This preserves context while respecting token limits.

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `app/shared/llm.py` | LLM factory — `create_llm(settings, tools)` with provider selection, per-model `bind_tools()`, and `with_fallbacks()` |
| `app/shared/state.py` | `AgentState(MessagesState)` — `bearer_token`, `tool_calls_made` (operator.add reducer), `model_used` |
| `app/shared/agent.py` | `build_agent_graph()` — `StateGraph` with `agent_node`, `ToolNode`, conditional edges, checkpointer |
| `app/customer/schemas.py` | 27 Pydantic `BaseModel` input schemas for customer tools |
| `app/company/schemas.py` | 40 Pydantic `BaseModel` input schemas for company tools |

### Rewritten Files

| File | Changes |
|------|---------|
| `app/customer/tools.py` | `StructuredTool.from_function()` wrappers with `args_schema`, `RunnableConfig` for client, `InjectedState` for token |
| `app/company/tools.py` | Same pattern, 40 tools |
| `app/api/dependencies.py` | `ChatRequest` → `message` + `session_id`; `ChatResponse` → adds `session_id`; drops `conversation_history` |
| `app/api/routes/chat.py` | Invokes `customer_graph.ainvoke()` with `HumanMessage` + `run_config` |
| `app/api/routes/company_chat.py` | Same pattern for company graph |
| `app/main.py` | Lifespan creates LLMs via factory, builds both graphs with checkpointer, stores on `app.state` |
| `app/core/config.py` | Adds `llm_provider`, `ollama_base_url` settings |
| `requirements.txt` | Adds `langchain-core`, `langchain-openai`, `langchain-ollama`, `langchain-anthropic`, `langgraph`, `langgraph-checkpoint-sqlite` |

### Deleted Files

| File | Reason |
|------|--------|
| `app/shared/react_engine.py` | Replaced by `app/shared/agent.py` (LangGraph StateGraph) |
| `app/shared/react_parser.py` | LangGraph handles tool call parsing natively via `bind_tools()` |
| `app/prompts/react_instructions.md` | ReAct text format instructions no longer needed with native tool calling |

### Unchanged Files

| File | Why |
|------|-----|
| `app/customer/operations.py` | Pure business logic — zero changes |
| `app/company/operations.py` | Pure business logic — zero changes |
| `app/customer/client.py` | HTTP client — zero changes |
| `app/company/client.py` | HTTP client — zero changes |
| `app/shared/http_client.py` | `BaseApiClient` — zero changes |
| `app/shared/auth.py` | `extract_bearer`, `require_bearer` — zero changes |
| `app/shared/prompts.py` | `load_prompt()` — still used for system prompts |
| `app/prompts/customer_system.md` | System prompt content unchanged |
| `app/prompts/company_system.md` | System prompt content unchanged |
| `app/core/rate_limit.py` | Redis rate limiting — zero changes |
| `app/utils/context_manager.py` | `trim_messages` — kept for use in `agent_node` context windowing |
| `app/utils/retries.py` | Tenacity config — kept, may become unused |

---

## Final Folder Structure

```
app/
├── main.py                          # Updated lifespan: LLM factory + graph builder + checkpointer
├── core/
│   ├── config.py                    # + llm_provider, ollama_base_url
│   └── rate_limit.py               # Unchanged
├── shared/
│   ├── http_client.py              # Unchanged
│   ├── llm.py                      # NEW — LLM factory (provider selection, bind_tools, fallbacks)
│   ├── state.py                    # NEW — AgentState(MessagesState)
│   ├── agent.py                    # NEW — build_agent_graph() (replaces react_engine.py)
│   ├── auth.py                     # Unchanged
│   └── prompts.py                  # Unchanged
├── prompts/
│   ├── customer_system.md          # Unchanged
│   └── company_system.md           # Unchanged
├── customer/
│   ├── schemas.py                  # NEW — 27 Pydantic input models
│   ├── tools.py                    # REWRITTEN — StructuredTool wrappers
│   ├── operations.py               # UNCHANGED
│   └── client.py                   # UNCHANGED
├── company/
│   ├── schemas.py                  # NEW — 40 Pydantic input models
│   ├── tools.py                    # REWRITTEN — StructuredTool wrappers
│   ├── operations.py               # UNCHANGED
│   └── client.py                   # UNCHANGED
├── api/
│   ├── dependencies.py             # REWRITTEN — new ChatRequest/ChatResponse with session_id
│   └── routes/
│       ├── chat.py                 # REWRITTEN — graph invocation via ainvoke()
│       └── company_chat.py         # REWRITTEN — graph invocation via ainvoke()
└── utils/
    ├── context_manager.py          # Kept — context window guard for agent_node
    └── retries.py                  # Kept — may become unused
```

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Agent engine | Custom ReAct (regex parsing) | LangGraph StateGraph (native tool calling) |
| Tool calling | Text-based (fragile) | Native `bind_tools()` (structured JSON) |
| Model providers | OpenAI-compatible only | OpenRouter + Ollama + Anthropic (pluggable) |
| Conversation state | Client-managed (stateless) | Server-managed (LangGraph checkpointer) |
| Fallback logic | Custom try/except in engine | `with_fallbacks()` (LangChain native) |
| Tool definitions | Plain dicts with handler refs | Pydantic schemas + StructuredTool |
| Type safety on tool args | None (raw JSON parsing) | Full Pydantic validation |
| business logic changes | — | Zero (operations.py + client.py unchanged) |
| Custom code deleted | react_engine.py, react_parser.py, react_instructions.md | Replaced by ~3 focused LangGraph modules |
