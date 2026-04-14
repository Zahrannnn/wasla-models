# LangGraph / LangChain Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the custom ReAct engine with a LangGraph StateGraph agent using LangChain native tool calling, Pydantic-validated tools, and server-side session memory.

**Architecture:** A custom LangGraph `StateGraph` with `agent` and `tools` nodes replaces `ReactEngine`. Each domain's 67 tools (27 customer + 40 company) are wrapped as `StructuredTool` with Pydantic input schemas. Server-side conversation state via LangGraph checkpointing replaces client-managed `conversation_history`. LLM factory supports OpenRouter, Ollama, and Anthropic providers with `with_fallbacks()`.

**Tech Stack:** LangGraph, LangChain Core, langchain-openai, langchain-ollama, langchain-anthropic, FastAPI, Pydantic v2, httpx

**Spec:** `docs/superpowers/specs/2026-04-14-langgraph-migration-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `requirements.txt` | Modify | Add LangChain/LangGraph deps |
| `app/core/config.py` | Modify | Add `llm_provider`, `ollama_base_url` |
| `app/shared/llm.py` | Create | LLM factory with provider selection, `bind_tools`, `with_fallbacks` |
| `app/shared/state.py` | Create | `AgentState(MessagesState)` |
| `app/shared/agent.py` | Create | `build_agent_graph()` — StateGraph with agent + tools nodes |
| `app/customer/schemas.py` | Create | 27 Pydantic `BaseModel` input schemas |
| `app/customer/tools.py` | Rewrite | `StructuredTool` wrappers with `InjectedState` + `RunnableConfig` |
| `app/company/schemas.py` | Create | 40 Pydantic `BaseModel` input schemas |
| `app/company/tools.py` | Rewrite | `StructuredTool` wrappers with `InjectedState` + `RunnableConfig` |
| `app/api/dependencies.py` | Rewrite | New `ChatRequest`/`ChatResponse` with `session_id` |
| `app/api/routes/chat.py` | Rewrite | Graph invocation via `ainvoke()` |
| `app/api/routes/company_chat.py` | Rewrite | Graph invocation via `ainvoke()` |
| `app/main.py` | Rewrite | Lifespan builds LLMs + graphs + checkpointer |
| `app/shared/react_engine.py` | Delete | Replaced by `agent.py` |
| `app/shared/react_parser.py` | Delete | LangGraph handles tool call parsing |
| `app/prompts/react_instructions.md` | Delete | No longer needed with native tool calling |

**Unchanged files:** `app/customer/operations.py`, `app/company/operations.py`, `app/customer/client.py`, `app/company/client.py`, `app/shared/http_client.py`, `app/shared/auth.py`, `app/shared/prompts.py`, `app/prompts/customer_system.md`, `app/prompts/company_system.md`, `app/core/rate_limit.py`, `app/utils/context_manager.py`, `app/utils/retries.py`

---

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add LangChain and LangGraph packages**

Open `requirements.txt` and add the new dependencies. Keep `openai` (required by `langchain-openai` internally).

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
openai>=1.50.0
huggingface_hub>=0.27.1,<1.0
aiohttp>=3.9.0
httpx>=0.27.0
tenacity==9.0.0
pydantic==2.10.4
pydantic-settings==2.7.1
python-dotenv==1.0.1
redis==5.2.1
langchain-core>=0.3.0
langchain-openai>=0.3.0
langchain-ollama>=0.3.0
langchain-anthropic>=0.3.0
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=0.1.0
```

- [ ] **Step 2: Install the new dependencies**

Run:
```bash
pip install -r requirements.txt
```

Expected: All packages install successfully. Verify with:
```bash
python -c "import langchain_core; import langgraph; print('OK')"
```
Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add langchain-core, langgraph, and provider packages"
```

---

### Task 2: Add LLM Provider Settings

**Files:**
- Modify: `app/core/config.py:15-67`

- [ ] **Step 1: Add new settings fields**

Add `llm_provider` and `ollama_base_url` to the `Settings` class. Insert after the `llm_base_url` field (line 25):

```python
    # Provider selection: "openrouter" | "ollama" | "anthropic"
    llm_provider: str = "openrouter"

    # Ollama-specific (only used when llm_provider == "ollama")
    ollama_base_url: str = "http://localhost:11434"
```

- [ ] **Step 2: Verify the app still loads settings**

Run:
```bash
python -c "from app.core.config import get_settings; s = get_settings(); print(s.llm_provider, s.ollama_base_url)"
```

Expected output: `openrouter http://localhost:11434`

- [ ] **Step 3: Commit**

```bash
git add app/core/config.py
git commit -m "config: add llm_provider and ollama_base_url settings"
```

---

### Task 3: Create LLM Factory

**Files:**
- Create: `app/shared/llm.py`

- [ ] **Step 1: Create the LLM factory module**

```python
"""
LLM Factory — creates LangChain chat models with provider selection,
per-model tool binding, and automatic fallback chaining.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.config import Settings

logger = logging.getLogger("wasla.llm")


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
    """
    Create LLM with tools bound and fallback chained.

    Tools must be bound to EACH model individually BEFORE chaining with
    with_fallbacks(). Calling bind_tools() on a RunnableWithFallbacks does
    not reliably propagate schemas to both underlying models.
    """
    primary = _create_provider(settings, settings.main_chat_model)
    fallback = _create_provider(settings, settings.fallback_chat_model)

    if tools:
        primary = primary.bind_tools(tools)
        fallback = fallback.bind_tools(tools)

    logger.info(
        "LLM created: provider=%s primary=%s fallback=%s tools=%d",
        settings.llm_provider,
        settings.main_chat_model,
        settings.fallback_chat_model,
        len(tools) if tools else 0,
    )

    return primary.with_fallbacks([fallback])
```

- [ ] **Step 2: Verify the module imports cleanly**

Run:
```bash
python -c "from app.shared.llm import create_llm; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/shared/llm.py
git commit -m "feat: add LLM factory with provider selection and fallback chaining"
```

---

### Task 4: Create Agent State

**Files:**
- Create: `app/shared/state.py`

- [ ] **Step 1: Create the AgentState module**

```python
"""
Agent State — LangGraph state schema for Wasla agent graphs.

All fields must be JSON-serializable because the LangGraph checkpointer
persists state to a database after every node execution.
"""

from __future__ import annotations

import operator
from typing import Annotated

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Extended state for Wasla agent graph.

    Inherits ``messages: list[BaseMessage]`` from MessagesState.

    Notes
    -----
    - ``bearer_token`` is a plain string — safe for serialization.
    - ``tool_calls_made`` uses ``operator.add`` as a reducer so returning
      ``{"tool_calls_made": 1}`` from any node increments the running total.
    - HTTP clients are NOT stored here (non-serializable). They are passed
      via ``RunnableConfig["configurable"]["client"]`` at invocation time.
    """

    bearer_token: str | None = None
    tool_calls_made: Annotated[int, operator.add] = 0
    model_used: str = ""
```

- [ ] **Step 2: Verify the module imports cleanly**

Run:
```bash
python -c "from app.shared.state import AgentState; print(AgentState.__annotations__)"
```

Expected: Prints the annotations dict including `messages`, `bearer_token`, `tool_calls_made`, `model_used`.

- [ ] **Step 3: Commit**

```bash
git add app/shared/state.py
git commit -m "feat: add AgentState with serializable fields and operator.add reducer"
```

---

### Task 5: Create Agent Graph Builder

**Files:**
- Create: `app/shared/agent.py`

- [ ] **Step 1: Create the agent graph module**

```python
"""
Agent Graph — LangGraph StateGraph builder for Wasla agents.

Builds a two-node graph:
  agent (LLM) ──► tools (ToolNode) ──► agent ──► END

The system prompt is prepended inside agent_node (NOT saved to checkpointed
state) to avoid duplication across turns.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.shared.state import AgentState
from app.utils.context_manager import trim_messages

logger = logging.getLogger("wasla.agent")


def build_agent_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    checkpointer: Any = None,
):
    """
    Build and compile the Wasla agent StateGraph.

    Parameters
    ----------
    llm           : BaseChatModel with tools already bound and fallbacks chained.
    tools         : List of StructuredTool instances (for the ToolNode).
    system_prompt : Base system prompt text loaded from a .md file.
    checkpointer  : LangGraph checkpointer for session persistence (MemorySaver,
                    AsyncSqliteSaver, etc.). Pass None for stateless operation.

    Returns
    -------
    Compiled LangGraph StateGraph ready for ``ainvoke()`` / ``astream()``.
    """

    tool_node = ToolNode(tools)

    async def agent_node(state: AgentState) -> dict[str, Any]:
        # 1. Build dynamic system prompt with auth status
        sys_text = system_prompt
        if state.get("bearer_token"):
            sys_text += (
                "\n\nThe user IS authenticated — all protected tools will work. "
                "Call tools directly without asking for login."
            )
        else:
            sys_text += (
                "\n\nThe user is NOT authenticated (guest). "
                "Public tools work. For protected actions, suggest they log in first "
                "or offer to register/login via the appropriate auth tools."
            )

        # 2. Prepend SystemMessage to history for LLM (NOT saved to state)
        messages_for_llm = [SystemMessage(content=sys_text)] + list(state["messages"])

        # 3. Trim to fit context window (keep system + recent messages)
        messages_for_llm = trim_messages(messages_for_llm, max_input_tokens=7168)

        # 4. Invoke LLM
        response = await llm.ainvoke(messages_for_llm)

        logger.info(
            "Agent response: tool_calls=%d content_len=%d",
            len(response.tool_calls) if hasattr(response, "tool_calls") and response.tool_calls else 0,
            len(response.content) if response.content else 0,
        )

        # 5. Return only the AI response to update persistent state
        model_name = ""
        if hasattr(response, "response_metadata"):
            model_name = response.response_metadata.get("model_name", "")
        
        return {
            "messages": [response],
            "model_used": model_name,
            "tool_calls_made": len(response.tool_calls) if hasattr(response, "tool_calls") and response.tool_calls else 0,
        }

    def should_continue(state: AgentState) -> str:
        """Route to tools if the last message has tool calls, otherwise end."""
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

    logger.info("Agent graph built with %d tools", len(tools))

    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 2: Verify the module imports cleanly**

Run:
```bash
python -c "from app.shared.agent import build_agent_graph; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/shared/agent.py
git commit -m "feat: add LangGraph agent builder with agent/tools nodes and checkpointer"
```

---

### Task 6: Create Customer Tool Schemas (Pydantic Models)

**Files:**
- Create: `app/customer/schemas.py`

- [ ] **Step 1: Create all 27 Pydantic input schemas**

Each schema maps exactly to the parameters of the corresponding function in `app/customer/operations.py`. Field descriptions come from the existing tool definitions in `app/customer/tools.py`.

```python
"""Pydantic input schemas for Customer Portal tools (27 total).

Each BaseModel is used as ``args_schema`` for a StructuredTool, providing
strict type validation of LLM-generated arguments before they reach
the business logic in operations.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────

class RegisterCustomerInput(BaseModel):
    """Register a new customer account."""
    email: str = Field(description="Valid email address")
    password: str = Field(description="Min 6 chars, must contain at least 1 digit")
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")
    phone_number: str | None = Field(default=None, description="Optional phone number")


class LoginCustomerInput(BaseModel):
    """Authenticate a user."""
    email: str = Field(description="User's email address")
    password: str = Field(description="User's password")
    remember_me: bool = Field(default=False, description="If true, extends refresh token to 30 days")


class RefreshTokenInput(BaseModel):
    """Refresh an access token."""
    refresh_token: str = Field(description="The refresh token from login response")


class LogoutInput(BaseModel):
    """Log out the current session."""
    refresh_token: str = Field(description="The refresh token to revoke")


# logout_all has no parameters (empty schema)
class LogoutAllInput(BaseModel):
    """Log out from all devices."""
    pass


# ── Company Discovery ─────────────────────────────────────────────

class ListCompaniesInput(BaseModel):
    """Browse and search companies."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 12)")
    search: str | None = Field(default=None, description="Search by company name")
    service_type: str | None = Field(default=None, description="Filter by service type (e.g., 'Cleaning', 'Moving')")
    sort_by: str | None = Field(default=None, description="Sort by: 'rating', 'name', 'newest' (default: 'rating')")


class GetRecommendedCompaniesInput(BaseModel):
    """Get AI-ranked company recommendations."""
    service_type: str | None = Field(default=None, description="Filter by service type")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")


class GetTrendingCompaniesInput(BaseModel):
    """Get trending companies."""
    service_type: str | None = Field(default=None, description="Filter by service type")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")


class GetCompanyDetailsInput(BaseModel):
    """Get company details."""
    company_id: int = Field(description="The company's numeric ID")


class GetCompanyReviewsInput(BaseModel):
    """Get reviews for a company."""
    company_id: int = Field(description="The company's numeric ID")
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")
    sort_by: str | None = Field(default=None, description="Sort by: 'newest', 'highest-rated' (default: 'newest')")


# ── Reviews ───────────────────────────────────────────────────────

class SubmitReviewInput(BaseModel):
    """Submit a review for a company."""
    company_id: int = Field(description="The company's numeric ID")
    rating: int = Field(description="Star rating 1-5")
    review_text: str | None = Field(default=None, description="Review text, max 2000 chars (optional)")


class UpdateReviewInput(BaseModel):
    """Update an existing review."""
    company_id: int = Field(description="The company's numeric ID")
    rating: int = Field(description="Updated star rating 1-5")
    review_text: str | None = Field(default=None, description="Updated review text, max 2000 chars")


class DeleteReviewInput(BaseModel):
    """Delete a review."""
    company_id: int = Field(description="The company's numeric ID")


class GetMyReviewsInput(BaseModel):
    """Get all reviews by the authenticated customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page (default: 10)")


# ── Profiles ──────────────────────────────────────────────────────

# get_customer_profile has no parameters
class GetCustomerProfileInput(BaseModel):
    """Get customer profile."""
    pass


class UpdateCustomerProfileInput(BaseModel):
    """Update customer profile."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Street address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip/Postal code")
    country: str | None = Field(default=None, description="Country")


# get_lead_profile has no parameters
class GetLeadProfileInput(BaseModel):
    """Get lead profile."""
    pass


class UpdateLeadProfileInput(BaseModel):
    """Update lead profile."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Street address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip/Postal code")
    country: str | None = Field(default=None, description="Country")


class GetDigitalSignatureInput(BaseModel):
    """Get digital signature after password verification."""
    password: str = Field(description="User's current password to verify identity")


# ── Offers ────────────────────────────────────────────────────────

class GetMyOffersInput(BaseModel):
    """Get offers sent to the customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page, max 50 (default: 10)")
    status: str | None = Field(default=None, description="Filter: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'")


class GetOfferDetailsInput(BaseModel):
    """Get offer details."""
    offer_id: int = Field(description="The offer's numeric ID")


class AcceptOfferInput(BaseModel):
    """Accept an offer."""
    offer_id: int = Field(description="The offer's numeric ID")
    digital_signature: str = Field(description="User's digital signature (get via get_digital_signature)")
    payment_method: str = Field(description="Payment method: 'COD' or 'Online'")


class RejectOfferInput(BaseModel):
    """Reject an offer."""
    offer_id: int = Field(description="The offer's numeric ID")
    rejection_reason: str = Field(description="Reason for rejection (max 2000 chars)")


# get_dashboard has no parameters
class GetDashboardInput(BaseModel):
    """Get dashboard summary."""
    pass


# ── Service Requests ──────────────────────────────────────────────

class CreateServiceRequestInput(BaseModel):
    """Submit a service inquiry to a company."""
    company_id: int = Field(description="The company's numeric ID")
    service_type: str = Field(description="Type of service (e.g., 'Moving', 'Cleaning')")
    from_street: str | None = Field(default=None, description="Origin street address")
    from_city: str | None = Field(default=None, description="Origin city")
    from_zip_code: str | None = Field(default=None, description="Origin zip code")
    from_country: str | None = Field(default=None, description="Origin country")
    to_street: str | None = Field(default=None, description="Destination street address")
    to_city: str | None = Field(default=None, description="Destination city")
    to_zip_code: str | None = Field(default=None, description="Destination zip code")
    to_country: str | None = Field(default=None, description="Destination country")
    preferred_date: str | None = Field(default=None, description="Preferred service date (YYYY-MM-DD)")
    preferred_time_slot: str | None = Field(default=None, description="Preferred time (e.g., 'Morning 8am-12pm')")
    notes: str | None = Field(default=None, description="Additional notes (max 2000 chars)")


class GetMyServiceRequestsInput(BaseModel):
    """Get service requests by the authenticated customer."""
    page_index: int | None = Field(default=None, description="Page number (default: 1)")
    page_size: int | None = Field(default=None, description="Items per page (default: 10)")
    status: str | None = Field(default=None, description="Filter: 'Pending', 'InProgress', 'Closed'")


class GetServiceRequestDetailsInput(BaseModel):
    """Get service request details."""
    service_request_id: int = Field(description="The service request's numeric ID")
```

- [ ] **Step 2: Verify all schemas import cleanly**

Run:
```bash
python -c "from app.customer.schemas import *; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/customer/schemas.py
git commit -m "feat: add 27 Pydantic input schemas for customer tools"
```

---

### Task 7: Rewrite Customer Tools (StructuredTool Wrappers)

**Files:**
- Rewrite: `app/customer/tools.py`

- [ ] **Step 1: Replace the entire file with StructuredTool wrappers**

Each wrapper bridges LangGraph (via `InjectedState` + `RunnableConfig`) to the unchanged `operations.py` functions. The `**kwargs` pattern avoids duplicating argument lists — Pydantic's `args_schema` controls what the LLM can pass.

```python
"""Customer Portal tools — LangChain StructuredTool wrappers.

Each tool wraps an unchanged function from operations.py using:
- Pydantic args_schema for LLM input validation
- InjectedState for bearer_token (from LangGraph state)
- RunnableConfig for HTTP client (non-serializable, not in state)
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import InjectedState

from app.customer import operations as ops
from app.customer.schemas import (
    AcceptOfferInput,
    CreateServiceRequestInput,
    DeleteReviewInput,
    GetCompanyDetailsInput,
    GetCompanyReviewsInput,
    GetCustomerProfileInput,
    GetDashboardInput,
    GetDigitalSignatureInput,
    GetLeadProfileInput,
    GetMyOffersInput,
    GetMyReviewsInput,
    GetMyServiceRequestsInput,
    GetOfferDetailsInput,
    GetRecommendedCompaniesInput,
    GetServiceRequestDetailsInput,
    GetTrendingCompaniesInput,
    ListCompaniesInput,
    LoginCustomerInput,
    LogoutAllInput,
    LogoutInput,
    RefreshTokenInput,
    RegisterCustomerInput,
    RejectOfferInput,
    SubmitReviewInput,
    UpdateCustomerProfileInput,
    UpdateLeadProfileInput,
    UpdateReviewInput,
)

logger = logging.getLogger("wasla.customer.tools")


def _build_ctx(
    bearer_token: str | None,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Build the legacy ctx dict from LangGraph injections."""
    client = config.get("configurable", {}).get("client")
    return {"bearer_token": bearer_token, "client": client}


def _dump(obj: Any) -> str:
    """JSON-serialize with Arabic character support."""
    return json.dumps(obj, ensure_ascii=False)


# ── Wrapper factory ──────────────────────────────────────────────

def _make_wrapper(op_func):
    """Create an async wrapper that bridges InjectedState/RunnableConfig → ctx."""
    async def wrapper(
        bearer_token: Annotated[str | None, InjectedState("bearer_token")] = None,
        config: RunnableConfig = None,
        **kwargs,
    ) -> str:
        ctx = _build_ctx(bearer_token, config)
        result = await op_func(ctx, **kwargs)
        return _dump(result)
    return wrapper


# ── Tool definitions ─────────────────────────────────────────────

def _make_customer_tools() -> list[StructuredTool]:
    """Build all 27 customer portal LangChain tools."""
    return [
        # Auth
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.register_customer),
            name="register_customer",
            description="Register a new customer account. Creates a Lead record and generates a Digital Signature automatically.",
            args_schema=RegisterCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.login_customer),
            name="login_customer",
            description="Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type.",
            args_schema=LoginCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.refresh_token),
            name="refresh_token",
            description="Get a new access token using refresh token. Each refresh token can only be used once (token rotation).",
            args_schema=RefreshTokenInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.logout),
            name="logout",
            description="Log out the current session by revoking the refresh token.",
            args_schema=LogoutInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.logout_all),
            name="logout_all",
            description="Log out from ALL devices by revoking all refresh tokens. Requires authentication.",
            args_schema=LogoutAllInput,
        ),

        # Company Discovery
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.list_companies),
            name="list_companies",
            description="Browse and search companies on the platform. No authentication required.",
            args_schema=ListCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_recommended_companies),
            name="get_recommended_companies",
            description="Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required.",
            args_schema=GetRecommendedCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_trending_companies),
            name="get_trending_companies",
            description="Get companies with improving recent reviews (last 90 days).",
            args_schema=GetTrendingCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_company_details),
            name="get_company_details",
            description="Get detailed information about a specific company including contact info, services offered. No authentication required.",
            args_schema=GetCompanyDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_company_reviews),
            name="get_company_reviews",
            description="Get paginated customer reviews for a company. No authentication required.",
            args_schema=GetCompanyReviewsInput,
        ),

        # Reviews
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.submit_review),
            name="submit_review",
            description="Submit a new review for a company. Requires Customer authentication. Only one review per customer per company.",
            args_schema=SubmitReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_review),
            name="update_review",
            description="Update an existing review. Only the customer who created the review can update it.",
            args_schema=UpdateReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_review),
            name="delete_review",
            description="Delete the customer's own review for a company. This action cannot be undone.",
            args_schema=DeleteReviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_reviews),
            name="get_my_reviews",
            description="Get all reviews written by the authenticated customer across all companies.",
            args_schema=GetMyReviewsInput,
        ),

        # Profiles
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_profile),
            name="get_customer_profile",
            description="Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId).",
            args_schema=GetCustomerProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_customer_profile),
            name="update_customer_profile",
            description="Update the authenticated customer's profile. Email cannot be changed.",
            args_schema=UpdateCustomerProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_lead_profile),
            name="get_lead_profile",
            description="Get the lead's profile including list of connected companies.",
            args_schema=GetLeadProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_lead_profile),
            name="update_lead_profile",
            description="Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
            args_schema=UpdateLeadProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_digital_signature),
            name="get_digital_signature",
            description="Get the user's digital signature after password verification. Required to accept offers.",
            args_schema=GetDigitalSignatureInput,
        ),

        # Offers
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_offers),
            name="get_my_offers",
            description="Get all offers (quotes) sent to the customer by companies.",
            args_schema=GetMyOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offer_details),
            name="get_offer_details",
            description="Get detailed information about a specific offer including service line items and pricing breakdown.",
            args_schema=GetOfferDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.accept_offer),
            name="accept_offer",
            description="Accept an offer. Requires digital signature. Choose COD (Cash on Delivery) or Online (Stripe) payment.",
            args_schema=AcceptOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.reject_offer),
            name="reject_offer",
            description="Reject an offer. Must provide a reason for rejection.",
            args_schema=RejectOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_dashboard),
            name="get_dashboard",
            description="Get dashboard summary showing total offers, offers by status, total reviews, and recent activity.",
            args_schema=GetDashboardInput,
        ),

        # Service Requests
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_service_request),
            name="create_service_request",
            description="Submit a service inquiry to a company. Can be done by both Lead and Customer users.",
            args_schema=CreateServiceRequestInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_service_requests),
            name="get_my_service_requests",
            description="Get all service requests submitted by the authenticated customer.",
            args_schema=GetMyServiceRequestsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_request_details),
            name="get_service_request_details",
            description="Get detailed information about a specific service request.",
            args_schema=GetServiceRequestDetailsInput,
        ),
    ]


TOOLS = _make_customer_tools()
```

- [ ] **Step 2: Verify all tools instantiate correctly**

Run:
```bash
python -c "from app.customer.tools import TOOLS; print(f'{len(TOOLS)} tools loaded'); print([t.name for t in TOOLS])"
```

Expected: `27 tools loaded` followed by the list of tool names.

- [ ] **Step 3: Commit**

```bash
git add app/customer/tools.py
git commit -m "feat: rewrite customer tools as StructuredTool wrappers with Pydantic schemas"
```

---

### Task 8: Create Company Tool Schemas (Pydantic Models)

**Files:**
- Create: `app/company/schemas.py`

- [ ] **Step 1: Create all 40 Pydantic input schemas**

Each schema maps exactly to the parameters of the corresponding function in `app/company/operations.py`.

```python
"""Pydantic input schemas for Company Portal tools (40 total).

Each BaseModel is used as ``args_schema`` for a StructuredTool, providing
strict type validation of LLM-generated arguments before they reach
the business logic in operations.py.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────

class LoginStaffInput(BaseModel):
    """Authenticate a staff member."""
    email: str = Field(description="Staff email address")
    password: str = Field(description="Staff password")


class ChangePasswordInput(BaseModel):
    """Change the current user's password."""
    current_password: str = Field(description="Current password")
    new_password: str = Field(description="New password")
    confirm_password: str = Field(description="Confirm new password")


# ── Customers ─────────────────────────────────────────────────────

class GetCustomersInput(BaseModel):
    """Get paginated customer list."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search by name or email")


class GetCustomerDetailsInput(BaseModel):
    """Get customer details."""
    customer_id: int = Field(description="Customer ID")


class CreateCustomerInput(BaseModel):
    """Create a new customer."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    email: str = Field(description="Email address")
    phone_number: str = Field(description="Phone number")
    address: str = Field(description="Street address")
    city: str = Field(description="City")
    zip_code: str = Field(description="Zip/Postal code")
    country: str = Field(description="Country")
    notes: str = Field(description="Notes about the customer")


class UpdateCustomerInput(BaseModel):
    """Update customer information."""
    customer_id: int = Field(description="Customer ID")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    email: str | None = Field(default=None, description="Email")
    phone_number: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Address")
    city: str | None = Field(default=None, description="City")
    zip_code: str | None = Field(default=None, description="Zip code")
    country: str | None = Field(default=None, description="Country")
    notes: str | None = Field(default=None, description="Notes")


class DeleteCustomerInput(BaseModel):
    """Delete a customer."""
    customer_id: int = Field(description="Customer ID")


class GetCustomerOffersInput(BaseModel):
    """Get offer history for a customer."""
    customer_id: int = Field(description="Customer ID")
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")


class GetCustomerTasksInput(BaseModel):
    """Get task history for a customer."""
    customer_id: int = Field(description="Customer ID")
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")


# ── Offers ────────────────────────────────────────────────────────

class GetOffersInput(BaseModel):
    """Get paginated offers."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search_word: str | None = Field(default=None, description="Search by client name or offer number")
    status: str | None = Field(default=None, description="Filter: Pending, Sent, Accepted, Rejected, Canceled")


class GetOfferDetailsInput(BaseModel):
    """Get offer details."""
    offer_id: int = Field(description="Offer ID")


class CreateOfferInput(BaseModel):
    """Create a new offer."""
    customer_id: int = Field(description="Customer ID (required)")
    service_request_id: int | None = Field(default=None, description="Link to service request (auto-updates to OfferSent)")
    notes_in_offer: str | None = Field(default=None, description="Notes visible to customer")
    notes_not_in_offer: str | None = Field(default=None, description="Internal notes")
    language_code: str | None = Field(default=None, description="e.g. 'en', 'de'")
    email_to_customer: bool | None = Field(default=None, description="Send email notification")
    locations: list[Any] | None = Field(default=None, description="List of locations (From, To)")
    services: dict[str, Any] | None = Field(default=None, description="Service details (Moving, Cleaning, Packing, etc.)")


class UpdateOfferInput(BaseModel):
    """Update an offer."""
    offer_id: int = Field(description="Offer ID")
    customer_id: int | None = Field(default=None, description="Customer ID")
    notes_in_offer: str | None = Field(default=None, description="Notes visible to customer")
    notes_not_in_offer: str | None = Field(default=None, description="Internal notes")
    locations: list[Any] | None = Field(default=None, description="Locations")
    services: dict[str, Any] | None = Field(default=None, description="Services")


class UpdateOfferStatusInput(BaseModel):
    """Change offer status."""
    offer_id: int = Field(description="Offer ID")
    status: str = Field(description="New status: Pending, Sent, Accepted, Rejected, Canceled")


class DeleteOfferInput(BaseModel):
    """Delete an offer."""
    offer_id: int = Field(description="Offer ID")


# ── Tasks ─────────────────────────────────────────────────────────

class GetAllTasksInput(BaseModel):
    """Get all company tasks."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")


class GetMyTasksInput(BaseModel):
    """Get tasks assigned to the current employee."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")


class GetTaskDetailsInput(BaseModel):
    """Get task details."""
    task_id: int = Field(description="Task ID")


class CreateTaskInput(BaseModel):
    """Create a new task."""
    assigned_to_user_id: int = Field(description="Employee ID to assign to")
    task_title: str = Field(description="Task title")
    customer_id: int | None = Field(default=None, description="Link to customer")
    description: str | None = Field(default=None, description="Task description")
    priority: str | None = Field(default=None, description="Priority: Low, Medium, High, Urgent")
    due_date: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    notes: str | None = Field(default=None, description="Additional notes")


class UpdateTaskInput(BaseModel):
    """Update a task."""
    task_item_id: int = Field(description="Task item ID")
    assigned_to_user_id: int | None = Field(default=None, description="Reassign to employee ID")
    customer_id: int | None = Field(default=None, description="Customer ID")
    task_title: str | None = Field(default=None, description="Task title")
    description: str | None = Field(default=None, description="Description")
    priority: str | None = Field(default=None, description="Priority")
    due_date: str | None = Field(default=None, description="Due date")
    notes: str | None = Field(default=None, description="Notes")


class StartTaskInput(BaseModel):
    """Start a task."""
    task_id: int = Field(description="Task ID")


class CompleteTaskInput(BaseModel):
    """Complete a task."""
    task_id: int = Field(description="Task ID")


class ReassignTaskInput(BaseModel):
    """Reassign a task."""
    task_id: int = Field(description="Task ID")
    new_assignee_id: int = Field(description="New employee ID")
    reason: str = Field(description="Reason for reassignment")


class SearchEmployeesInput(BaseModel):
    """Search employees by name."""
    search_name: str = Field(description="Name to search for")


class SearchCustomersInput(BaseModel):
    """Search customers by name."""
    search_name: str = Field(description="Name to search for")


# ── Employees ─────────────────────────────────────────────────────

class GetEmployeesInput(BaseModel):
    """Get paginated employee list."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search by name or email")


class GetEmployeeDetailsInput(BaseModel):
    """Get employee details."""
    user_id: int = Field(description="Employee user ID")


class CreateEmployeeInput(BaseModel):
    """Create a new employee."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    email: str = Field(description="Email")
    user_name: str = Field(description="Username")
    password: str = Field(description="Password")
    is_active: bool | None = Field(default=None, description="Active status (default: true)")
    permission_ids: list[int] | None = Field(default=None, description="Permission IDs to assign")


class UpdateEmployeeInput(BaseModel):
    """Update an employee."""
    user_id: int = Field(description="Employee user ID")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    email: str | None = Field(default=None, description="Email")
    user_name: str | None = Field(default=None, description="Username")
    new_password: str | None = Field(default=None, description="New password")
    is_active: bool | None = Field(default=None, description="Active status")
    permission_ids: list[int] | None = Field(default=None, description="Permission IDs")


class DeleteEmployeeInput(BaseModel):
    """Delete an employee."""
    user_id: int = Field(description="Employee user ID")


class GetEmployeePerformanceInput(BaseModel):
    """Get employee performance report."""
    employee_id: int = Field(description="Employee ID")


# ── Expenses ──────────────────────────────────────────────────────

class GetExpensesInput(BaseModel):
    """Get paginated expenses."""
    page: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Search expenses")
    category: str | None = Field(default=None, description="Filter by category")
    date_from: str | None = Field(default=None, alias="from", description="Start date YYYY-MM-DD")
    date_to: str | None = Field(default=None, alias="to", description="End date YYYY-MM-DD")


class CreateExpenseInput(BaseModel):
    """Record a new expense."""
    description: str = Field(description="Expense description")
    amount_egp: float = Field(description="Amount in EGP")
    expense_date: str = Field(description="Date (YYYY-MM-DD)")
    category: str = Field(description="Expense category")


class UpdateExpenseInput(BaseModel):
    """Update an expense."""
    expense_id: int = Field(description="Expense ID")
    description: str | None = Field(default=None, description="Description")
    amount_egp: float | None = Field(default=None, description="Amount in EGP")
    expense_date: str | None = Field(default=None, description="Date")
    category: str | None = Field(default=None, description="Category")


class DeleteExpenseInput(BaseModel):
    """Delete an expense."""
    expense_id: int = Field(description="Expense ID")


class GetExpenseChartsInput(BaseModel):
    """Get expense chart data."""
    chart_type: str = Field(description="Chart type: 'monthly' or 'category'")
    date_from: str | None = Field(default=None, alias="from", description="Start date (optional)")
    date_to: str | None = Field(default=None, alias="to", description="End date (optional)")


# ── Appointments ──────────────────────────────────────────────────

class GetAppointmentsInput(BaseModel):
    """Get paginated appointments."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    search: str | None = Field(default=None, description="Filter by customer name or location")
    start_date: str | None = Field(default=None, description="Filter from date (ISO 8601)")
    end_date: str | None = Field(default=None, description="Filter to date (ISO 8601)")


class CreateAppointmentInput(BaseModel):
    """Schedule a new appointment."""
    customer_id: int = Field(description="Customer ID")
    scheduled_at: str = Field(description="UTC datetime ISO 8601")
    location: str | None = Field(default=None, description="Site address")
    notes: str | None = Field(default=None, description="Notes")
    language_code: str | None = Field(default=None, description="Language: en, de, fr, it")


# ── Dashboard ─────────────────────────────────────────────────────

class GetDashboardInput(BaseModel):
    """Get company dashboard."""
    pass


# ── Service Requests ──────────────────────────────────────────────

class GetServiceRequestsInput(BaseModel):
    """Get incoming service requests."""
    page_index: int | None = Field(default=None, description="Page number")
    page_size: int | None = Field(default=None, description="Items per page")
    status: str | None = Field(default=None, description="Filter: New, Viewed, OfferSent, Declined")


class GetServiceRequestDetailsInput(BaseModel):
    """Get service request details."""
    request_id: int = Field(description="Service request ID")


class DeclineServiceRequestInput(BaseModel):
    """Decline a service request."""
    request_id: int = Field(description="Service request ID")
    reason: str | None = Field(default=None, description="Reason for declining (optional)")
```

- [ ] **Step 2: Verify all schemas import cleanly**

Run:
```bash
python -c "from app.company.schemas import *; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/company/schemas.py
git commit -m "feat: add 40 Pydantic input schemas for company tools"
```

---

### Task 9: Rewrite Company Tools (StructuredTool Wrappers)

**Files:**
- Rewrite: `app/company/tools.py`

- [ ] **Step 1: Replace the entire file with StructuredTool wrappers**

Uses the same `_make_wrapper` / `_build_ctx` pattern as customer tools. The `get_expenses` and `get_expense_charts` operations use `**kw` to receive `from`/`to` params — the wrapper handles this by extracting aliased fields from the Pydantic model.

```python
"""Company Portal tools — LangChain StructuredTool wrappers.

Each tool wraps an unchanged function from operations.py using:
- Pydantic args_schema for LLM input validation
- InjectedState for bearer_token (from LangGraph state)
- RunnableConfig for HTTP client (non-serializable, not in state)
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import InjectedState

from app.company import operations as ops
from app.company.schemas import (
    ChangePasswordInput,
    CreateAppointmentInput,
    CreateCustomerInput,
    CreateEmployeeInput,
    CreateExpenseInput,
    CreateOfferInput,
    CreateTaskInput,
    CompleteTaskInput,
    DeclineServiceRequestInput,
    DeleteCustomerInput,
    DeleteEmployeeInput,
    DeleteExpenseInput,
    DeleteOfferInput,
    GetAllTasksInput,
    GetAppointmentsInput,
    GetCustomerDetailsInput,
    GetCustomerOffersInput,
    GetCustomerTasksInput,
    GetCustomersInput,
    GetDashboardInput,
    GetEmployeeDetailsInput,
    GetEmployeePerformanceInput,
    GetEmployeesInput,
    GetExpenseChartsInput,
    GetExpensesInput,
    GetMyTasksInput,
    GetOfferDetailsInput,
    GetOffersInput,
    GetServiceRequestDetailsInput,
    GetServiceRequestsInput,
    GetTaskDetailsInput,
    LoginStaffInput,
    ReassignTaskInput,
    SearchCustomersInput,
    SearchEmployeesInput,
    StartTaskInput,
    UpdateCustomerInput,
    UpdateEmployeeInput,
    UpdateExpenseInput,
    UpdateOfferInput,
    UpdateOfferStatusInput,
    UpdateTaskInput,
)

logger = logging.getLogger("wasla.company.tools")


def _build_ctx(
    bearer_token: str | None,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Build the legacy ctx dict from LangGraph injections."""
    client = config.get("configurable", {}).get("client")
    return {"bearer_token": bearer_token, "client": client}


def _dump(obj: Any) -> str:
    """JSON-serialize with Arabic character support."""
    return json.dumps(obj, ensure_ascii=False)


def _make_wrapper(op_func):
    """Create an async wrapper that bridges InjectedState/RunnableConfig → ctx."""
    async def wrapper(
        bearer_token: Annotated[str | None, InjectedState("bearer_token")] = None,
        config: RunnableConfig = None,
        **kwargs,
    ) -> str:
        ctx = _build_ctx(bearer_token, config)
        result = await op_func(ctx, **kwargs)
        return _dump(result)
    return wrapper


def _make_expense_wrapper(op_func):
    """Special wrapper for expense operations that use 'from'/'to' kwargs.

    The Pydantic schemas use ``date_from``/``date_to`` field names with
    ``alias="from"``/``alias="to"``. The operations.py functions expect
    these as ``**kw`` and access them via ``kw.get("from")``.
    We remap the aliased fields back to the ``from``/``to`` keys.
    """
    async def wrapper(
        bearer_token: Annotated[str | None, InjectedState("bearer_token")] = None,
        config: RunnableConfig = None,
        **kwargs,
    ) -> str:
        ctx = _build_ctx(bearer_token, config)
        # Remap aliased fields: date_from -> from, date_to -> to
        if "date_from" in kwargs:
            kwargs["from"] = kwargs.pop("date_from")
        if "date_to" in kwargs:
            kwargs["to"] = kwargs.pop("date_to")
        result = await op_func(ctx, **kwargs)
        return _dump(result)
    return wrapper


# ── Tool definitions ─────────────────────────────────────────────

def _make_company_tools() -> list[StructuredTool]:
    """Build all 40 company portal LangChain tools."""
    return [
        # Auth
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.login_staff),
            name="login_staff",
            description="Authenticate a company staff member (Manager or Employee). Returns JWT with company ID, role, and permissions.",
            args_schema=LoginStaffInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.change_password),
            name="change_password",
            description="Change the current user's password. Requires authentication.",
            args_schema=ChangePasswordInput,
        ),

        # Customers
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customers),
            name="get_customers",
            description="Get paginated list of customers. Requires can_edit_customers.",
            args_schema=GetCustomersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_details),
            name="get_customer_details",
            description="Get detailed customer info including offer count, task count, total profit. Requires can_edit_customers.",
            args_schema=GetCustomerDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_customer),
            name="create_customer",
            description="Create a new customer record. Requires can_edit_customers.",
            args_schema=CreateCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_customer),
            name="update_customer",
            description="Update an existing customer's information. Requires can_edit_customers.",
            args_schema=UpdateCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_customer),
            name="delete_customer",
            description="Delete a customer record. Requires can_edit_customers. Confirm with user first.",
            args_schema=DeleteCustomerInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_offers),
            name="get_customer_offers",
            description="Get offer history for a specific customer. Requires can_edit_customers.",
            args_schema=GetCustomerOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_customer_tasks),
            name="get_customer_tasks",
            description="Get task history for a specific customer. Requires can_edit_customers.",
            args_schema=GetCustomerTasksInput,
        ),

        # Offers
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offers),
            name="get_offers",
            description="Get paginated list of offers. Requires can_view_offers.",
            args_schema=GetOffersInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_offer_details),
            name="get_offer_details",
            description="Get full offer details including services, locations, and line items. Requires can_view_offers.",
            args_schema=GetOfferDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_offer),
            name="create_offer",
            description="Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers.",
            args_schema=CreateOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_offer),
            name="update_offer",
            description="Update an existing offer's details. Requires can_view_offers.",
            args_schema=UpdateOfferInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_offer_status),
            name="update_offer_status",
            description="Change offer status (e.g. cancel). Requires can_view_offers.",
            args_schema=UpdateOfferStatusInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_offer),
            name="delete_offer",
            description="Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers.",
            args_schema=DeleteOfferInput,
        ),

        # Tasks
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_all_tasks),
            name="get_all_tasks",
            description="Get all company tasks with summary statistics. Requires can_manage_tasks (Manager only).",
            args_schema=GetAllTasksInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_my_tasks),
            name="get_my_tasks",
            description="Get tasks assigned to the current employee. Available to both Manager and Employee roles.",
            args_schema=GetMyTasksInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_task_details),
            name="get_task_details",
            description="Get detailed task info including status, duration, files, assignment history.",
            args_schema=GetTaskDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_task),
            name="create_task",
            description="Create a new task and assign to an employee. Requires can_manage_tasks.",
            args_schema=CreateTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_task),
            name="update_task",
            description="Update task details. Requires can_manage_tasks.",
            args_schema=UpdateTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.start_task),
            name="start_task",
            description="Start a task (Pending -> InProgress). Available to the assigned employee.",
            args_schema=StartTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.complete_task),
            name="complete_task",
            description="Mark a task as completed. Available to the assigned employee.",
            args_schema=CompleteTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.reassign_task),
            name="reassign_task",
            description="Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks.",
            args_schema=ReassignTaskInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.search_employees),
            name="search_employees",
            description="Search employees by name (autocomplete helper for task assignment).",
            args_schema=SearchEmployeesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.search_customers),
            name="search_customers",
            description="Search customers by name (autocomplete helper for task/offer creation).",
            args_schema=SearchCustomersInput,
        ),

        # Employees
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employees),
            name="get_employees",
            description="Get paginated list of employees. Requires can_manage_users.",
            args_schema=GetEmployeesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employee_details),
            name="get_employee_details",
            description="Get employee details including permissions and task counts. Requires can_manage_users.",
            args_schema=GetEmployeeDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_employee),
            name="create_employee",
            description="Create a new employee account. Requires can_manage_users.",
            args_schema=CreateEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_employee),
            name="update_employee",
            description="Update employee information. Requires can_manage_users.",
            args_schema=UpdateEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_employee),
            name="delete_employee",
            description="Delete/deactivate an employee. Requires can_manage_users. Confirm first.",
            args_schema=DeleteEmployeeInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_employee_performance),
            name="get_employee_performance",
            description="Get performance report including completion rates. Requires can_manage_users.",
            args_schema=GetEmployeePerformanceInput,
        ),

        # Expenses
        StructuredTool.from_function(
            coroutine=_make_expense_wrapper(ops.get_expenses),
            name="get_expenses",
            description="Get paginated expenses. Requires can_view_reports.",
            args_schema=GetExpensesInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_expense),
            name="create_expense",
            description="Record a new expense. Requires can_view_reports.",
            args_schema=CreateExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.update_expense),
            name="update_expense",
            description="Update an expense record. Requires can_view_reports.",
            args_schema=UpdateExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.delete_expense),
            name="delete_expense",
            description="Delete an expense record. Requires can_view_reports. Confirm first.",
            args_schema=DeleteExpenseInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_expense_wrapper(ops.get_expense_charts),
            name="get_expense_charts",
            description="Get expense chart data (monthly trend or category breakdown). Requires can_view_reports.",
            args_schema=GetExpenseChartsInput,
        ),

        # Appointments
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_appointments),
            name="get_appointments",
            description="Get paginated list of appointments for the company. Requires can_view_offers.",
            args_schema=GetAppointmentsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.create_appointment),
            name="create_appointment",
            description="Schedule a new appointment (on-site visit). Requires can_view_offers.",
            args_schema=CreateAppointmentInput,
        ),

        # Dashboard
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_dashboard),
            name="get_dashboard",
            description="Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports.",
            args_schema=GetDashboardInput,
        ),

        # Service Requests
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_requests),
            name="get_service_requests",
            description="Get incoming service requests from portal users. Requires can_view_offers.",
            args_schema=GetServiceRequestsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.get_service_request_details),
            name="get_service_request_details",
            description="Get details of a specific service request. Requires can_view_offers.",
            args_schema=GetServiceRequestDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_make_wrapper(ops.decline_service_request),
            name="decline_service_request",
            description="Decline a service request from a portal user. Requires can_view_offers.",
            args_schema=DeclineServiceRequestInput,
        ),
    ]


TOOLS = _make_company_tools()
```

- [ ] **Step 2: Verify all tools instantiate correctly**

Run:
```bash
python -c "from app.company.tools import TOOLS; print(f'{len(TOOLS)} tools loaded'); print([t.name for t in TOOLS])"
```

Expected: `40 tools loaded` followed by the list of tool names.

- [ ] **Step 3: Commit**

```bash
git add app/company/tools.py
git commit -m "feat: rewrite company tools as StructuredTool wrappers with Pydantic schemas"
```

---

### Task 10: Rewrite API Contract (ChatRequest / ChatResponse)

**Files:**
- Rewrite: `app/api/dependencies.py`

- [ ] **Step 1: Replace the request/response models**

```python
"""
Reusable FastAPI dependencies.

Provides the session-based ChatRequest/ChatResponse models and
per-request rate-limit enforcement.
"""

from __future__ import annotations

from fastapi import Path

from pydantic import BaseModel, Field

from app.core.rate_limit import check_rate_limit


# ── Request / response models ────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    message: str = Field(
        ...,
        min_length=1,
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Show me the top 5 customers",
                    "session_id": None,
                },
                {
                    "message": "Tell me more about the first one",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                },
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response body from chat endpoints."""

    response: str = Field(
        ...,
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "Here are your top 5 customers:\n\n1. Acme Corp ...",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "tool_calls_made": 1,
                    "model_used": "arcee-ai/trinity-large-preview:free",
                }
            ]
        }
    }


# ── Dependency functions ─────────────────────────────────────────

async def get_company_id(
    company_id: str = Path(
        ...,
        description="Tenant / company identifier (e.g. `acme-corp`).",
        examples=["acme-corp", "demo-company"],
    ),
) -> str:
    """Extract and validate the company_id path parameter."""
    return company_id


async def enforce_rate_limit(
    company_id: str = Path(
        ...,
        description="Tenant identifier — used for per-company rate limiting.",
    ),
) -> None:
    """Check the per-company rate limit via Redis (30 req / 60 s by default)."""
    await check_rate_limit(company_id)
```

- [ ] **Step 2: Verify the module imports cleanly**

Run:
```bash
python -c "from app.api.dependencies import ChatRequest, ChatResponse; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/dependencies.py
git commit -m "feat: rewrite ChatRequest/ChatResponse with session_id contract"
```

---

### Task 11: Rewrite Routes (Graph Invocation)

**Files:**
- Rewrite: `app/api/routes/chat.py`
- Rewrite: `app/api/routes/company_chat.py`

- [ ] **Step 1: Rewrite the customer chat route**

```python
"""
Customer Portal Chat — LangGraph agent endpoint.
POST /api/chat         -> JSON response (session-based)
POST /api/chat/{company_id} -> Legacy backward-compat route
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import HumanMessage

from app.api.dependencies import ChatRequest, ChatResponse, enforce_rate_limit
from app.shared.auth import extract_bearer

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Customer Chat"])

_bearer_scheme = HTTPBearer(auto_error=False)


async def _handle_chat(body: ChatRequest, request: Request, credentials, company_id: str | None = None):
    """Shared handler for both /api/chat and /api/chat/{company_id}."""
    token = extract_bearer(credentials, request)
    logger.info("Bearer extracted: %s", "YES" if token else "NO")

    session_id = body.session_id or str(uuid4())
    graph = request.app.state.customer_graph

    run_config = {
        "configurable": {
            "thread_id": session_id,
            "client": request.app.state.customer_client,
        }
    }

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=body.message)],
                "bearer_token": token,
            },
            config=run_config,
        )
    except Exception as exc:
        logger.exception("Chat failed%s", f" for company {company_id}" if company_id else "")
        detail = "AI model is unavailable. Please try again later."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "LLM authentication failed. Set a valid LLM_API_KEY in .env."
        raise HTTPException(status_code=503, detail=detail) from exc

    ai_message = result["messages"][-1]

    return ChatResponse(
        response=ai_message.content or "",
        session_id=session_id,
        tool_calls_made=result.get("tool_calls_made", 0),
        model_used=result.get("model_used", ""),
    )


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Customer Portal — Agentic chat with tool calling",
    operation_id="portalChat",
    response_description="AI response with session ID and tool-call metadata.",
    responses={
        200: {"description": "Successful AI response."},
        429: {"description": "Rate limit exceeded."},
        503: {"description": "AI model is temporarily unavailable."},
    },
)
async def portal_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """
    **Customer Portal chat endpoint** — LangGraph agentic tool-calling loop.

    The agent can invoke 27 tools covering the full Customer Portal API:
    auth, companies, reviews, profiles, offers, service requests, dashboard.

    Omit ``session_id`` on first request to start a new session.
    Pass the returned ``session_id`` in subsequent requests to continue.
    """
    return await _handle_chat(body, request, credentials)


@router.post(
    "/api/chat/{company_id}",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Company-scoped chat (legacy)",
    operation_id="mainChat",
    include_in_schema=False,
)
async def main_chat(
    company_id: str,
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """Legacy company-scoped endpoint — delegates to portal chat."""
    return await _handle_chat(body, request, credentials, company_id=company_id)
```

- [ ] **Step 2: Rewrite the company chat route**

```python
"""
Company Portal Chat — staff-facing LangGraph agent endpoint.
POST /api/company/chat -> JSON response (session-based)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import HumanMessage

from app.api.dependencies import ChatRequest, ChatResponse
from app.shared.auth import extract_bearer

logger = logging.getLogger("wasla.routes.company")
router = APIRouter(tags=["Company Chat"])

_bearer = HTTPBearer(auto_error=False)


@router.post(
    "/api/company/chat",
    response_model=ChatResponse,
    summary="Company Portal — Staff agentic chat",
    operation_id="companyChat",
    responses={200: {"description": "AI response."}, 503: {"description": "AI unavailable."}},
)
async def company_chat(
    body: ChatRequest,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    Staff-facing chat endpoint with 40 tools for CRM operations:
    customers, offers, tasks, employees, expenses, dashboard, service requests.

    Omit ``session_id`` on first request to start a new session.
    Pass the returned ``session_id`` in subsequent requests to continue.
    """
    token = extract_bearer(credentials, request)
    logger.info("Company bearer: %s", "YES" if token else "NO")

    session_id = body.session_id or str(uuid4())
    graph = request.app.state.company_graph

    run_config = {
        "configurable": {
            "thread_id": session_id,
            "client": request.app.state.company_client,
        }
    }

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=body.message)],
                "bearer_token": token,
            },
            config=run_config,
        )
    except Exception as exc:
        logger.exception("Company chat failed")
        detail = "AI model is unavailable."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "LLM authentication failed. Check LLM_API_KEY in .env."
        raise HTTPException(status_code=503, detail=detail) from exc

    ai_message = result["messages"][-1]

    return ChatResponse(
        response=ai_message.content or "",
        session_id=session_id,
        tool_calls_made=result.get("tool_calls_made", 0),
        model_used=result.get("model_used", ""),
    )
```

- [ ] **Step 3: Verify both routes import cleanly**

Run:
```bash
python -c "from app.api.routes.chat import router; from app.api.routes.company_chat import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/api/routes/chat.py app/api/routes/company_chat.py
git commit -m "feat: rewrite routes to invoke LangGraph agent with session-based contract"
```

---

### Task 12: Rewrite main.py Lifespan

**Files:**
- Rewrite: `app/main.py`

- [ ] **Step 1: Update the lifespan and imports**

```python
"""
Wasla AI Agent Backend — FastAPI application init.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import get_settings
from app.core.rate_limit import init_redis, close_redis
import app.core.rate_limit as rl
from app.shared.llm import create_llm
from app.shared.agent import build_agent_graph
from app.shared.prompts import load_prompt
from app.customer.client import CustomerClient
from app.company.client import CompanyClient
from app.api.routes import chat
from app.api.routes import company_chat

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-22s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if not s.llm_api_key:
        logging.getLogger("wasla").warning(
            "LLM_API_KEY is not set. Copy .env.example to .env and set a valid API key. "
            "Supported: OpenRouter (openrouter.ai), HuggingFace (hf.co/settings/tokens), or any OpenAI-compatible provider."
        )

    # Redis
    try:
        await asyncio.wait_for(init_redis(), timeout=5.0)
    except asyncio.TimeoutError:
        rl._redis = None
        logging.getLogger("wasla").warning("Redis connection timed out — rate limiting disabled")

    # HTTP clients
    customer_client = CustomerClient(s.crm_api_base_url, s.crm_api_timeout_seconds)
    company_client = CompanyClient(s.company_api_base_url, s.company_api_timeout_seconds)
    await customer_client.init()
    await company_client.init()
    app.state.customer_client = customer_client
    app.state.company_client = company_client

    # Checkpointer (swap for AsyncSqliteSaver/AsyncPostgresSaver in production)
    checkpointer = MemorySaver()

    # LLM + Agent graphs
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


# ── FastAPI app ───────────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Customer Chat",
        "description": "Customer-facing AI chat endpoint widget using a LangGraph agentic tool-calling loop. Accessed externally via the Wasla Customer Portal.",
    },
    {
        "name": "Company Chat",
        "description": "Staff-facing (Manager / Employee) AI chat with 40 tools for full CRM operations.",
    },
    {
        "name": "Health",
        "description": "Service health check and configuration status.",
    },
]

app = FastAPI(
    title="Wasla AI Agent APIs",
    summary="Agentic AI backend for Wasla CRM and Customer Portals",
    description=(
        "This API provides agentic conversational interfaces for both the Wasla Customer Portal "
        "and the Internal Company CRM. It uses LangGraph agent graphs with LangChain native tool calling "
        "to process intent and automatically execute backend actions.\n\n"
        "## Endpoints\n\n"
        "| Endpoint | Transport | Context | Capabilities |\n"
        "|----------|-----------|---------|--------------|\n"
        "| `POST /api/chat` | JSON | Public Customer Portal | General inquiries, submitting service requests, checking offers. |\n"
        "| `POST /api/company/chat` | JSON | Internal CRM | Full CRM capabilities (Customers, Offers, Tasks, Appointments). Requires JWT Bearer token authentication. |\n\n"
        "---\n"
        "**Authentication:** Include standard `Bearer <JWT_TOKEN>` in the headers when accessing protected internal endpoints.\n\n"
        "**Sessions:** Pass `session_id` from the previous response to continue a conversation. Omit to start a new session."
    ),
    version="3.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    license_info={"name": "MIT"},
    contact={"name": "Wasla AI", "url": "https://wasla.ai"},
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(company_chat.router)


# ── Root & health ─────────────────────────────────────────────────
@app.get("/ping", include_in_schema=False)
async def ping():
    return {"pong": True}


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Wasla AI Agent API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"], summary="Service health check",
         response_description="Current service status and configured models.")
async def health_check():
    s = get_settings()
    return {
        "status": "ok",
        "main_model": s.main_chat_model,
        "fallback_model": s.fallback_chat_model,
        "max_context_tokens": s.max_context_tokens,
    }
```

- [ ] **Step 2: Verify the app module imports cleanly**

Run:
```bash
python -c "from app.main import app; print(app.title)"
```

Expected output: `Wasla AI Agent APIs`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: rewrite main.py lifespan to build LangGraph agents with checkpointer"
```

---

### Task 13: Delete Old Files

**Files:**
- Delete: `app/shared/react_engine.py`
- Delete: `app/shared/react_parser.py`
- Delete: `app/prompts/react_instructions.md`

- [ ] **Step 1: Remove the old ReAct engine files**

```bash
git rm app/shared/react_engine.py app/shared/react_parser.py app/prompts/react_instructions.md
```

- [ ] **Step 2: Verify no imports reference the deleted files**

Run:
```bash
grep -r "react_engine\|react_parser\|react_instructions" app/ --include="*.py" --include="*.md"
```

Expected: No results (all references should have been removed in previous tasks).

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: delete old ReAct engine, parser, and instructions (replaced by LangGraph)"
```

---

### Task 14: Smoke Test

- [ ] **Step 1: Verify the full app starts without errors**

Run:
```bash
python -c "
import asyncio
from app.main import app
from app.core.config import get_settings
print('Settings:', get_settings().llm_provider)
print('App title:', app.title)
print('Routes:', [r.path for r in app.routes if hasattr(r, 'path')])
print('All imports OK')
"
```

Expected output includes:
- `Settings: openrouter`
- `App title: Wasla AI Agent APIs`
- Routes listing `/api/chat`, `/api/company/chat`, `/health`, etc.
- `All imports OK`

- [ ] **Step 2: Try starting uvicorn (brief check, not a full run)**

Run:
```bash
timeout 5 uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 || true
```

Expected: Server starts (may show warnings about missing LLM_API_KEY or Redis), but no import errors or crashes. The `timeout` ensures it exits after 5 seconds.

- [ ] **Step 3: Commit any fixes if needed, then tag the migration**

```bash
git tag v3.0.0-langgraph -m "LangGraph migration complete"
```
