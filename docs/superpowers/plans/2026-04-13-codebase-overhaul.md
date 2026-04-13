# Codebase Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Wasla AI Agent Backend into a domain-split architecture with shared core, replacing OpenAI native tool calling with ReAct, eliminating all code duplication, and externalizing prompts — while keeping all 3 API endpoints backward-compatible.

**Architecture:** Two domain modules (`customer/`, `company/`) each contain their own tools, operations, and HTTP client. Shared infrastructure (`shared/`) provides `BaseApiClient`, `ReactEngine`, auth helpers, and prompt loading. Routes become thin orchestrators. Prompts live in editable `.md` files.

**Tech Stack:** Python 3.11+, FastAPI, httpx, openai SDK, tenacity, pydantic-settings, Redis

**Spec:** `docs/superpowers/specs/2026-04-13-codebase-overhaul-design.md`

---

## File Map

### New Files to Create

| File | Responsibility |
|------|---------------|
| `app/shared/__init__.py` | Package init |
| `app/shared/http_client.py` | `BaseApiClient` — unified async HTTP client |
| `app/shared/react_parser.py` | ReAct text parser (moved from `app/services/react_parser.py`) |
| `app/shared/react_engine.py` | `ReactEngine` — ReAct agent loop |
| `app/shared/auth.py` | `extract_bearer()` + `require_bearer()` |
| `app/shared/prompts.py` | `load_prompt()` helper |
| `app/prompts/customer_system.md` | Customer portal system prompt |
| `app/prompts/company_system.md` | Company portal system prompt |
| `app/prompts/react_instructions.md` | ReAct format template |
| `app/customer/__init__.py` | Package init |
| `app/customer/client.py` | `CustomerClient(BaseApiClient)` |
| `app/customer/operations.py` | Customer tool implementations |
| `app/customer/tools.py` | Customer schemas + registry merged |
| `app/company/__init__.py` | Package init |
| `app/company/client.py` | `CompanyClient(BaseApiClient)` |
| `app/company/operations.py` | Company tool implementations |
| `app/company/tools.py` | Company schemas + registry merged |

### Files to Modify

| File | Change |
|------|--------|
| `app/main.py` | Update imports, lifespan init for clients/engine |
| `app/api/routes/chat.py` | Use shared auth, load prompts, call ReactEngine |
| `app/api/routes/company_chat.py` | Use shared auth, load prompts, call ReactEngine |

### Files to Delete

| File | Replaced By |
|------|------------|
| `app/services/__init__.py` | (directory removed) |
| `app/services/backend_client.py` | `app/customer/client.py` |
| `app/services/company_client.py` | `app/company/client.py` |
| `app/services/llm_service.py` | `app/shared/react_engine.py` |
| `app/services/react_parser.py` | `app/shared/react_parser.py` |
| `app/prompts/__init__.py` | (directory repurposed for .md files) |
| `app/prompts/react_prompt.py` | `app/prompts/react_instructions.md` |
| `app/tools/__init__.py` | (directory removed) |
| `app/tools/schemas.py` | `app/customer/tools.py` |
| `app/tools/registry.py` | `app/customer/tools.py` |
| `app/tools/operations.py` | `app/customer/operations.py` |
| `app/tools/company_schemas.py` | `app/company/tools.py` |
| `app/tools/company_registry.py` | `app/company/tools.py` |
| `app/tools/company_operations.py` | `app/company/operations.py` |

### Files Unchanged

| File | Reason |
|------|--------|
| `app/core/config.py` | Settings model is stable |
| `app/core/rate_limit.py` | Redis logic is clean |
| `app/api/dependencies.py` | Request/Response models preserved |
| `app/utils/context_manager.py` | `trim_messages` works well |
| `app/utils/retries.py` | Tenacity config is clean |

---

## Task 1: Create Shared HTTP Client

**Files:**
- Create: `app/shared/__init__.py`
- Create: `app/shared/http_client.py`

- [ ] **Step 1: Create `app/shared/__init__.py`**

```python
"""Shared infrastructure — HTTP client, ReAct engine, auth, prompts."""
```

- [ ] **Step 2: Create `app/shared/http_client.py`**

This is the unified base class extracted from `backend_client.py` and `company_client.py`.

```python
"""
Unified async HTTP client for Wasla backend APIs.

Provides base request handling, auth injection, error mapping,
and param cleaning. Domain clients extend this class.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("wasla.http")

_ERROR_MAP = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "unprocessable",
    429: "rate_limited",
}


class BaseApiClient:
    """Async HTTP client with auth injection, error mapping, and param cleaning."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url) and self._client is not None

    async def init(self) -> None:
        if not self._base_url:
            return
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self._base_url.rstrip("/"),
            timeout=self._timeout,
            headers={"Content-Type": "application/json"},
        )
        logger.info("HTTP client connected to %s", self._base_url)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        bearer: str | None = None,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("HTTP client not initialized.")

        headers: dict[str, str] = {}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        try:
            response = await self._client.request(
                method, path, params=params, json=body, headers=headers,
            )
        except httpx.RequestError as exc:
            logger.exception("HTTP request failed: %s", exc)
            return {"error": "service_error", "message": "API is unavailable."}

        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return {"status": "success", "data": None}
            try:
                return {"status": "success", "data": response.json()}
            except ValueError:
                return {"status": "success", "data": {"raw": response.text}}

        try:
            err = response.json()
            message = err.get("message") or err.get("error") or response.text
        except ValueError:
            message = response.text

        error_type = _ERROR_MAP.get(response.status_code, "service_error")
        return {"error": error_type, "message": message or "API request failed."}

    @staticmethod
    def clean_params(params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None}

    @staticmethod
    def clean_body(body: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in body.items() if v is not None}
```

- [ ] **Step 3: Commit**

```bash
git add app/shared/__init__.py app/shared/http_client.py
git commit -m "feat: add BaseApiClient shared HTTP client"
```

---

## Task 2: Create Shared Auth Module

**Files:**
- Create: `app/shared/auth.py`

- [ ] **Step 1: Create `app/shared/auth.py`**

Consolidates `_get_bearer_token` from `chat.py`, `_get_token` from `company_chat.py`, `_require_token` from `operations.py`, and `_need_auth` from `company_operations.py`.

```python
"""Shared authentication helpers."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials


def extract_bearer(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> str | None:
    """
    Extract bearer token from FastAPI security scheme or raw Authorization header.

    Handles both standard "Bearer xxx" and raw "eyJ..." JWT formats.
    """
    if credentials and credentials.credentials:
        return credentials.credentials
    raw = request.headers.get("authorization")
    if raw and raw.strip().startswith("eyJ"):
        return raw.strip()
    return None


def require_bearer(ctx: dict[str, Any]) -> str | dict[str, str]:
    """
    Return the bearer token string from ctx, or an error dict if missing.

    Usage in operations:
        t = require_bearer(ctx)
        if isinstance(t, dict):
            return t
        # t is the token string
    """
    token = ctx.get("bearer_token")
    if not token:
        return {
            "error": "unauthorized",
            "message": "Authentication required. Please log in first.",
        }
    return token
```

- [ ] **Step 2: Commit**

```bash
git add app/shared/auth.py
git commit -m "feat: add shared auth helpers (extract_bearer, require_bearer)"
```

---

## Task 3: Create Shared Prompt Loader and Externalized Prompts

**Files:**
- Create: `app/shared/prompts.py`
- Create: `app/prompts/customer_system.md`
- Create: `app/prompts/company_system.md`
- Create: `app/prompts/react_instructions.md`

- [ ] **Step 1: Create `app/shared/prompts.py`**

```python
"""Load prompt templates from the prompts/ directory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """
    Load a prompt file by name from app/prompts/.

    Cached after first read. Returns the file contents as a string.
    """
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Create `app/prompts/customer_system.md`**

Extracted from `app/api/routes/chat.py:_BASE_SYSTEM_PROMPT`. The auth status line is NOT included — it's appended dynamically by the route.

```markdown
You are a helpful AI assistant for the Wasla Customer Portal. You help users:
- Browse and discover service companies
- Manage their account (register, login, profile)
- Submit and manage reviews
- Create and manage service requests
- View and respond to offers

Key Concepts:
- Lead: A user who registered but hasn't been accepted by any company yet.
- Customer: A user who has been accepted by at least one company.
- Digital Signature: Auto-generated at registration, required to accept offers.
- Service Request: An inquiry submitted to a company for services.
- Offer: A quote/proposal sent by a company to a customer.

CRITICAL — Authentication is handled automatically:
- The user's JWT token (if any) is ALREADY attached to every tool call behind the scenes.
- You NEVER need to ask for email, password, or token to use protected tools.
- If the user is authenticated, just call the tool directly (e.g. get_my_reviews, get_customer_profile, get_my_offers).
- If a tool returns an "unauthorized" error, THEN tell the user they need to log in.
- NEVER ask for credentials preemptively. Just try the tool.

Rules:
1. For authenticated actions, call the tool immediately — don't ask "are you logged in?"
2. Public endpoints (list_companies, get_company_details, get_company_reviews, etc.) always work.
3. Offer acceptance requires digital signature — use get_digital_signature (it needs the user's password).
4. Always confirm before destructive actions (delete_review, reject_offer).
5. Explain results conversationally — don't dump raw JSON.
6. After completing an action, suggest relevant next steps.
7. Never log, display, or ask for tokens.
```

- [ ] **Step 3: Create `app/prompts/company_system.md`**

Extracted from `app/api/routes/company_chat.py:_SYSTEM_PROMPT`.

```markdown
You are a helpful AI assistant for company staff (Managers and Employees) managing CRM operations. You can help with:
- Customer management (create, update, view history)
- Offers/quotes (create, send, track status)
- Task assignment and tracking
- Employee management
- Expense tracking
- Dashboard analytics
- Service request handling

User Roles:
- Manager: Full access to all features
- Employee: Can view/start/complete assigned tasks, change password

CRITICAL — Authentication is handled automatically:
- The staff member's JWT token is ALREADY attached to every tool call.
- NEVER ask for credentials. Just call the tool directly.
- If a tool returns "unauthorized", tell the user to log in.
- If a tool returns "forbidden", explain they lack permission for that action.

Rules:
1. Call tools immediately for data requests — don't ask "are you logged in?"
2. Confirm before destructive actions (delete customer, delete offer, etc.)
3. Explain results conversationally with tables — don't dump raw JSON.
4. Convert dates to readable format (March 20, 2026 not 2026-03-20T00:00:00Z).
5. After completing an action, suggest relevant next steps.
6. For multi-step flows (creating offers), guide step by step.
7. Surface important info (overdue tasks, high-priority items).
8. For Employees, suggest get_my_tasks instead of get_all_tasks if they lack permission.
9. Never expose tokens or internal IDs unnecessarily.
10. WARNING: You must ONLY use the exact tool names provided. DO NOT hallucinate or invent tools.
```

- [ ] **Step 4: Create `app/prompts/react_instructions.md`**

Extracted from `app/prompts/react_prompt.py:REACT_SYSTEM_TEMPLATE`. The `{tools_description}` placeholder is filled at runtime by the ReactEngine.

```markdown
You have access to the following tools:

{tools_description}

Use the following format:

Thought: Think about what you need to do next. Analyze the situation and plan your approach.
Action: The tool name to use (must be one of the available tools).
Action Input: A JSON object with the tool parameters (e.g., {{"param": "value"}}).

After you take an action, you will receive an Observation with the result.

Continue this Thought/Action/Action Input/Observation cycle until you have enough information to provide a final answer.

When you have the final answer, respond with:
Thought: I have enough information to answer.
Final Answer: Your complete answer to the user's question.

Important rules:
1. ALWAYS start with a Thought before any Action.
2. Only use tools that are listed above.
3. Action Input MUST be valid JSON.
4. If a tool returns an error, think about what went wrong and try a different approach.
5. When you have completed the task, provide a Final Answer - do not continue with more actions.
6. Be concise in your thoughts and answers.

Remember: Think step by step, use tools when needed, and provide a clear Final Answer when done.
```

- [ ] **Step 5: Commit**

```bash
git add app/shared/prompts.py app/prompts/customer_system.md app/prompts/company_system.md app/prompts/react_instructions.md
git commit -m "feat: externalize system prompts to markdown files"
```

---

## Task 4: Move ReAct Parser to Shared

**Files:**
- Create: `app/shared/react_parser.py` (copy from `app/services/react_parser.py`)

- [ ] **Step 1: Create `app/shared/react_parser.py`**

This is a direct copy of `app/services/react_parser.py` — the logic is already clean and correct. Only the module docstring logger name changes.

```python
"""
ReAct Parser — parses LLM text output into structured ReAct components.

Parses the ReAct format:
- Thought: The reasoning step
- Action: The tool to call
- Action Input: JSON parameters for the tool
- Final Answer: The final response to the user
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("wasla.react_parser")


@dataclass
class ReActResponse:
    """Parsed ReAct response from the LLM."""

    thought: str | None = None
    action: str | None = None
    action_input: dict[str, Any] | None = None
    final_answer: str | None = None
    raw_text: str = ""

    @property
    def is_final(self) -> bool:
        return self.final_answer is not None

    @property
    def has_action(self) -> bool:
        return self.action is not None and self.action_input is not None


_THOUGHT_PATTERN = re.compile(r"Thought:\s*(.+?)(?=\n(?:Action|Final|$))", re.DOTALL | re.IGNORECASE)
_ACTION_PATTERN = re.compile(r"Action:\s*(\w+)", re.IGNORECASE)
_ACTION_INPUT_PATTERN = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL | re.IGNORECASE)
_FINAL_ANSWER_PATTERN = re.compile(r"Final Answer:\s*(.+?)$", re.DOTALL | re.IGNORECASE)


def parse_react_response(text: str) -> ReActResponse:
    """Parse LLM text output into a structured ReActResponse."""
    response = ReActResponse(raw_text=text.strip())

    thought_match = _THOUGHT_PATTERN.search(text)
    if thought_match:
        response.thought = thought_match.group(1).strip()

    final_match = _FINAL_ANSWER_PATTERN.search(text)
    if final_match:
        response.final_answer = final_match.group(1).strip()
        logger.debug("Parsed final answer: %s", response.final_answer[:50] + "...")
        return response

    action_match = _ACTION_PATTERN.search(text)
    if action_match:
        response.action = action_match.group(1).strip()
        logger.debug("Parsed action: %s", response.action)

    input_match = _ACTION_INPUT_PATTERN.search(text)
    if input_match:
        input_str = input_match.group(1).strip()
        try:
            response.action_input = json.loads(input_str)
            logger.debug("Parsed action input: %s", response.action_input)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse action input JSON: %s — raw: %s", e, input_str)
            response.action_input = _try_fix_json(input_str)

    return response


def _try_fix_json(text: str) -> dict[str, Any] | None:
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r"(\w+)\s*:", r'"\1":', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def format_observation(result: dict[str, Any] | str) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(result)
```

- [ ] **Step 2: Commit**

```bash
git add app/shared/react_parser.py
git commit -m "feat: move react_parser to shared module"
```

---

## Task 5: Create ReAct Engine

**Files:**
- Create: `app/shared/react_engine.py`

- [ ] **Step 1: Create `app/shared/react_engine.py`**

This replaces both `llm_service.py:chat_with_tools()` and `company_chat.py:_company_chat_with_tools()`.

```python
"""
ReAct Engine — model-agnostic tool calling via text parsing.

Replaces native OpenAI tool calling with the ReAct pattern
(Thought / Action / Action Input / Observation / Final Answer).
Works with any text-generation model on any OpenAI-compatible API.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI

from app.core.config import Settings
from app.shared.react_parser import parse_react_response
from app.shared.prompts import load_prompt
from app.utils.context_manager import trim_messages
from app.utils.retries import llm_retry

logger = logging.getLogger("wasla.react_engine")


def _tools_to_react_description(tools: list[dict[str, Any]]) -> str:
    """Convert tool schema dicts to human-readable text for the ReAct prompt."""
    lines = []
    for tool in tools:
        name = tool["name"]
        desc = tool["description"]
        params = tool.get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])
        param_strs = []
        for pname, pinfo in properties.items():
            pdesc = pinfo.get("description", "")
            req = " (required)" if pname in required else " (optional)"
            param_strs.append(f"    - {pname}{req}: {pdesc}")
        pblock = "\n".join(param_strs) if param_strs else "    No parameters"
        lines.append(f"- {name}: {desc}\n{pblock}")
    return "\n\n".join(lines)


class ReactEngine:
    """ReAct agent loop — model-agnostic tool calling via text parsing."""

    def __init__(self, llm_client: AsyncOpenAI, settings: Settings) -> None:
        self.client = llm_client
        self.settings = settings

    @llm_retry
    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 1024,
        use_fallback: bool = False,
    ) -> str:
        """Call the LLM and return the text response."""
        model = (
            self.settings.fallback_chat_model if use_fallback
            else self.settings.main_chat_model
        )
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def run(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict | str, dict[str, Any]], Awaitable[str]],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute the ReAct loop.

        Parameters
        ----------
        messages    : Chat messages (system + history + user).
        tools       : Tool schema dicts (name, description, parameters).
        tool_executor : Async function(tool_name, arguments, ctx) -> JSON string.
        ctx         : Context dict passed to tool_executor (bearer_token, client, etc.).

        Returns
        -------
        {"response": str, "tool_calls_made": int, "model_used": str}
        """
        settings = self.settings
        input_budget = settings.max_context_tokens - settings.max_chat_tokens

        # Inject ReAct instructions + tool descriptions into the system prompt
        react_template = load_prompt("react_instructions.md")
        tools_desc = _tools_to_react_description(tools)
        react_block = react_template.format(tools_description=tools_desc)

        # Append ReAct block to the system message
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] += "\n\n" + react_block
        else:
            messages.insert(0, {"role": "system", "content": react_block})

        messages = trim_messages(messages, max_input_tokens=input_budget)

        tool_calls_total = 0
        use_fallback = False

        for iteration in range(settings.max_tool_iterations):
            try:
                llm_text = await self._call_llm(
                    messages,
                    max_tokens=settings.max_chat_tokens,
                    use_fallback=use_fallback,
                )
            except Exception as exc:
                if not use_fallback:
                    logger.warning("Primary model failed (%s) — switching to fallback", exc)
                    use_fallback = True
                    llm_text = await self._call_llm(
                        messages,
                        max_tokens=settings.max_chat_tokens,
                        use_fallback=True,
                    )
                else:
                    raise

            logger.info("Iter %d — LLM response:\n%s", iteration + 1, llm_text[:500])

            # Append assistant message
            messages.append({"role": "assistant", "content": llm_text})

            # Parse ReAct response
            parsed = parse_react_response(llm_text)

            if parsed.thought:
                logger.info("Iter %d — Thought: %s", iteration + 1, parsed.thought[:200])

            # Final answer — return it
            if parsed.is_final:
                model = (
                    settings.fallback_chat_model if use_fallback
                    else settings.main_chat_model
                )
                return {
                    "response": parsed.final_answer or "",
                    "tool_calls_made": tool_calls_total,
                    "model_used": model,
                }

            # Action — execute tool
            if parsed.has_action:
                tool_calls_total += 1
                logger.info(
                    "Iter %d — Action: %s(%s)",
                    iteration + 1,
                    parsed.action,
                    json.dumps(parsed.action_input),
                )
                result_json = await tool_executor(
                    parsed.action, parsed.action_input, ctx,
                )
                # Append observation as user message (works with all models)
                messages.append({
                    "role": "user",
                    "content": f"Observation: {result_json}",
                })
            else:
                # LLM didn't produce a valid action or final answer — treat raw text as response
                model = (
                    settings.fallback_chat_model if use_fallback
                    else settings.main_chat_model
                )
                return {
                    "response": llm_text,
                    "tool_calls_made": tool_calls_total,
                    "model_used": model,
                }

            messages = trim_messages(messages, max_input_tokens=input_budget)

        # Iteration limit reached — force a final answer
        messages.append({
            "role": "user",
            "content": (
                "You have reached the maximum number of action steps. "
                "Please provide your Final Answer now based on all the "
                "information you have gathered."
            ),
        })
        messages = trim_messages(messages, max_input_tokens=input_budget)

        final_text = await self._call_llm(
            messages,
            max_tokens=settings.max_chat_tokens,
            use_fallback=use_fallback,
        )

        # Try to extract Final Answer from the forced response
        final_parsed = parse_react_response(final_text)
        response_text = final_parsed.final_answer or final_text

        model = (
            settings.fallback_chat_model if use_fallback
            else settings.main_chat_model
        )
        return {
            "response": response_text,
            "tool_calls_made": tool_calls_total,
            "model_used": model,
        }
```

- [ ] **Step 2: Commit**

```bash
git add app/shared/react_engine.py
git commit -m "feat: add ReactEngine — ReAct-based agent loop"
```

---

## Task 6: Create Customer Domain — Client

**Files:**
- Create: `app/customer/__init__.py`
- Create: `app/customer/client.py`

- [ ] **Step 1: Create `app/customer/__init__.py`**

```python
"""Customer portal domain — tools, operations, and HTTP client."""
```

- [ ] **Step 2: Create `app/customer/client.py`**

Thin wrapper over `BaseApiClient` with all methods from the old `backend_client.py`.

```python
"""Async HTTP client for the Wasla Customer Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.http_client import BaseApiClient


class CustomerClient(BaseApiClient):
    """Customer Portal API client — extends BaseApiClient with domain methods."""

    # ── Auth ──────────────────────────────────────────────────────

    async def register(
        self, *, email: str, password: str, first_name: str, last_name: str,
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({
            "email": email, "password": password,
            "firstName": first_name, "lastName": last_name,
            "phoneNumber": phone_number,
        })
        return await self.request("POST", "/register", body=body)

    async def login(self, *, email: str, password: str, remember_me: bool = False) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email, "password": password}
        if remember_me:
            body["rememberMe"] = True
        return await self.request("POST", "/login", body=body)

    async def refresh_token(self, *, refresh_token_str: str) -> dict[str, Any]:
        return await self.request("POST", "/refresh-token", body={"refreshToken": refresh_token_str})

    async def logout(self, *, refresh_token_str: str) -> dict[str, Any]:
        return await self.request("POST", "/logout", body={"refreshToken": refresh_token_str})

    async def logout_all(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("POST", "/logout-all", bearer=bearer_token)

    # ── Public: Companies ─────────────────────────────────────────

    async def list_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        search: str | None = None, service_type: str | None = None, sort_by: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({
            "pageIndex": page_index, "pageSize": page_size,
            "search": search, "serviceType": service_type, "sortBy": sort_by,
        })
        return await self.request("GET", "/companies", params=params)

    async def get_recommended_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
        return await self.request("GET", "/recommended-companies", params=params)

    async def get_trending_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
        return await self.request("GET", "/trending-companies", params=params)

    async def get_company_details(self, company_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/companies/{company_id}")

    async def get_company_reviews(
        self, company_id: int, *, page_index: int | None = None,
        page_size: int | None = None, sort_by: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "sortBy": sort_by})
        return await self.request("GET", f"/companies/{company_id}/reviews", params=params)

    # ── Reviews ───────────────────────────────────────────────────

    async def submit_review(
        self, bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({"rating": rating, "reviewText": review_text})
        return await self.request("POST", f"/companies/{company_id}/reviews", bearer=bearer_token, body=body)

    async def update_review(
        self, bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({"rating": rating, "reviewText": review_text})
        return await self.request("PUT", f"/companies/{company_id}/reviews", bearer=bearer_token, body=body)

    async def delete_review(self, bearer_token: str, company_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/companies/{company_id}/reviews", bearer=bearer_token)

    async def get_my_reviews(
        self, bearer_token: str, *, page_index: int | None = None, page_size: int | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size})
        return await self.request("GET", "/my/reviews", bearer=bearer_token, params=params)

    # ── Profiles ──────────────────────────────────────────────────

    async def get_customer_profile(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/profile", bearer=bearer_token)

    async def update_customer_profile(self, bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", "/my/profile", bearer=bearer_token, body=payload)

    async def get_lead_profile(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/lead-profile", bearer=bearer_token)

    async def update_lead_profile(self, bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", "/my/lead-profile", bearer=bearer_token, body=payload)

    async def get_digital_signature(self, bearer_token: str, *, password: str) -> dict[str, Any]:
        return await self.request("POST", "/my/digital-signature", bearer=bearer_token, body={"password": password})

    # ── Offers ────────────────────────────────────────────────────

    async def get_my_offers(
        self, bearer_token: str, *, page_index: int | None = None,
        page_size: int | None = None, status: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
        return await self.request("GET", "/my/offers", bearer=bearer_token, params=params)

    async def get_offer_details(self, bearer_token: str, offer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/my/offers/{offer_id}", bearer=bearer_token)

    async def accept_offer(
        self, bearer_token: str, offer_id: int, *, digital_signature: str, payment_method: int,
    ) -> dict[str, Any]:
        body = {"digitalSignature": digital_signature, "paymentMethod": payment_method}
        return await self.request("POST", f"/my/offers/{offer_id}/accept", bearer=bearer_token, body=body)

    async def reject_offer(self, bearer_token: str, offer_id: int, *, rejection_reason: str) -> dict[str, Any]:
        return await self.request("POST", f"/my/offers/{offer_id}/reject", bearer=bearer_token, body={"rejectionReason": rejection_reason})

    # ── Dashboard ─────────────────────────────────────────────────

    async def get_dashboard(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/dashboard", bearer=bearer_token)

    # ── Service Requests ──────────────────────────────────────────

    async def create_service_request(
        self, bearer_token: str, *,
        company_id: int, preferred_date: str | None = None,
        origin_address: str | None = None, destination_address: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({
            "companyId": company_id, "preferredDate": preferred_date,
            "originAddress": origin_address, "destinationAddress": destination_address,
            "notes": notes,
        })
        return await self.request("POST", "/service-requests", bearer=bearer_token, body=body)

    async def get_my_service_requests(
        self, bearer_token: str, *, page_index: int | None = None,
        page_size: int | None = None, status: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
        return await self.request("GET", "/my/service-requests", bearer=bearer_token, params=params)

    async def get_service_request_details(self, bearer_token: str, request_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/my/service-requests/{request_id}", bearer=bearer_token)
```

- [ ] **Step 3: Commit**

```bash
git add app/customer/__init__.py app/customer/client.py
git commit -m "feat: add CustomerClient extending BaseApiClient"
```

---

## Task 7: Create Customer Domain — Operations

**Files:**
- Create: `app/customer/operations.py`

- [ ] **Step 1: Create `app/customer/operations.py`**

Adapted from the old `app/tools/operations.py`. Uses `require_bearer` from shared auth and `ctx["client"]` instead of importing a module-level global.

```python
"""Tool operations — Customer Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.auth import require_bearer


# ── Auth ──────────────────────────────────────────────────────────

async def register_customer(ctx: dict, *, email: str, password: str, first_name: str, last_name: str, phone_number: str | None = None) -> dict:
    return await ctx["client"].register(email=email, password=password, first_name=first_name, last_name=last_name, phone_number=phone_number)


async def login_customer(ctx: dict, *, email: str, password: str, remember_me: bool = False) -> dict:
    return await ctx["client"].login(email=email, password=password, remember_me=remember_me)


async def refresh_token(ctx: dict, *, refresh_token: str) -> dict:
    return await ctx["client"].refresh_token(refresh_token_str=refresh_token)


async def logout(ctx: dict, *, refresh_token: str) -> dict:
    return await ctx["client"].logout(refresh_token_str=refresh_token)


async def logout_all(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].logout_all(t)


# ── Company Discovery ─────────────────────────────────────────────

async def list_companies(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                         search: str | None = None, service_type: str | None = None, sort_by: str | None = None) -> dict:
    return await ctx["client"].list_companies(page_index=page_index, page_size=page_size, search=search, service_type=service_type, sort_by=sort_by)


async def get_recommended_companies(ctx: dict, *, service_type: str | None = None,
                                     page_index: int | None = None, page_size: int | None = None) -> dict:
    return await ctx["client"].get_recommended_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_trending_companies(ctx: dict, *, service_type: str | None = None,
                                  page_index: int | None = None, page_size: int | None = None) -> dict:
    return await ctx["client"].get_trending_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_company_details(ctx: dict, *, company_id: int) -> dict:
    return await ctx["client"].get_company_details(company_id)


async def get_company_reviews(ctx: dict, *, company_id: int, page_index: int | None = None,
                               page_size: int | None = None, sort_by: str | None = None) -> dict:
    return await ctx["client"].get_company_reviews(company_id, page_index=page_index, page_size=page_size, sort_by=sort_by)


# ── Reviews ───────────────────────────────────────────────────────

async def submit_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].submit_review(t, company_id, rating=rating, review_text=review_text)


async def update_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].update_review(t, company_id, rating=rating, review_text=review_text)


async def delete_review(ctx: dict, *, company_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_review(t, company_id)


async def get_my_reviews(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_reviews(t, page_index=page_index, page_size=page_size)


# ── Profiles ──────────────────────────────────────────────────────

async def get_customer_profile(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_profile(t)


async def update_customer_profile(ctx: dict, *, first_name: str, last_name: str,
                                   phone_number: str | None = None, address: str | None = None,
                                   city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name}
    if phone_number is not None:
        payload["phoneNumber"] = phone_number
    if address is not None:
        payload["address"] = address
    if city is not None:
        payload["city"] = city
    if zip_code is not None:
        payload["zipCode"] = zip_code
    if country is not None:
        payload["country"] = country
    return await ctx["client"].update_customer_profile(t, payload)


async def get_lead_profile(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_lead_profile(t)


async def update_lead_profile(ctx: dict, *, first_name: str, last_name: str,
                               phone_number: str | None = None, address: str | None = None,
                               city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name}
    if phone_number is not None:
        payload["phoneNumber"] = phone_number
    if address is not None:
        payload["address"] = address
    if city is not None:
        payload["city"] = city
    if zip_code is not None:
        payload["zipCode"] = zip_code
    if country is not None:
        payload["country"] = country
    return await ctx["client"].update_lead_profile(t, payload)


async def get_digital_signature(ctx: dict, *, password: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_digital_signature(t, password=password)


# ── Offers ────────────────────────────────────────────────────────

async def get_my_offers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_offers(t, page_index=page_index, page_size=page_size, status=status)


async def get_offer_details(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offer_details(t, offer_id)


async def accept_offer(ctx: dict, *, offer_id: int, digital_signature: str, payment_method: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    pm_map = {"cod": 0, "online": 1}
    pm_int = pm_map.get(payment_method.lower())
    if pm_int is None:
        return {"error": "bad_request", "message": "Invalid payment method. Use 'COD' or 'Online'."}
    return await ctx["client"].accept_offer(t, offer_id, digital_signature=digital_signature, payment_method=pm_int)


async def reject_offer(ctx: dict, *, offer_id: int, rejection_reason: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].reject_offer(t, offer_id, rejection_reason=rejection_reason)


async def get_dashboard(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_dashboard(t)


# ── Service Requests ──────────────────────────────────────────────

async def create_service_request(ctx: dict, *, company_id: int, service_type: str,
                                  from_street: str | None = None, from_city: str | None = None,
                                  from_zip_code: str | None = None, from_country: str | None = None,
                                  to_street: str | None = None, to_city: str | None = None,
                                  to_zip_code: str | None = None, to_country: str | None = None,
                                  preferred_date: str | None = None, preferred_time_slot: str | None = None,
                                  notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    origin_parts = [p for p in [from_street, from_city, from_zip_code, from_country] if p]
    dest_parts = [p for p in [to_street, to_city, to_zip_code, to_country] if p]
    origin_address = ", ".join(origin_parts) if origin_parts else None
    destination_address = ", ".join(dest_parts) if dest_parts else None
    full_notes_parts = []
    if preferred_time_slot:
        full_notes_parts.append(f"Preferred time: {preferred_time_slot}")
    if service_type:
        full_notes_parts.append(f"Service type: {service_type}")
    if notes:
        full_notes_parts.append(notes)
    full_notes = ". ".join(full_notes_parts) if full_notes_parts else None
    return await ctx["client"].create_service_request(
        t, company_id=company_id, preferred_date=preferred_date,
        origin_address=origin_address, destination_address=destination_address, notes=full_notes,
    )


async def get_my_service_requests(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_service_requests(t, page_index=page_index, page_size=page_size, status=status)


async def get_service_request_details(ctx: dict, *, service_request_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_request_details(t, service_request_id)
```

- [ ] **Step 2: Commit**

```bash
git add app/customer/operations.py
git commit -m "feat: add customer operations using shared auth + ctx client"
```

---

## Task 8: Create Customer Domain — Tools (Merged Schemas + Registry)

**Files:**
- Create: `app/customer/tools.py`

- [ ] **Step 1: Create `app/customer/tools.py`**

Merges the old `app/tools/schemas.py` and `app/tools/registry.py` into one file. Each tool definition includes its handler reference.

```python
"""Customer Portal tools — schemas, registry, and executor merged."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.customer import operations as ops

logger = logging.getLogger("wasla.customer.tools")


def _tool(name: str, description: str, handler, properties: dict | None = None, required: list[str] | None = None) -> dict:
    params: dict[str, Any] = {"type": "object", "properties": properties or {}, "required": required or []}
    return {"name": name, "description": description, "parameters": params, "handler": handler}


TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _tool("register_customer",
          "Register a new customer account. Creates a Lead record and generates a Digital Signature automatically.",
          ops.register_customer,
          {"email": {"type": "string", "description": "Valid email address"},
           "password": {"type": "string", "description": "Min 6 chars, must contain at least 1 digit"},
           "first_name": {"type": "string", "description": "User's first name"},
           "last_name": {"type": "string", "description": "User's last name"},
           "phone_number": {"type": "string", "description": "Optional phone number"}},
          ["email", "password", "first_name", "last_name"]),

    _tool("login_customer",
          "Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type.",
          ops.login_customer,
          {"email": {"type": "string", "description": "User's email address"},
           "password": {"type": "string", "description": "User's password"},
           "remember_me": {"type": "boolean", "description": "If true, extends refresh token to 30 days"}},
          ["email", "password"]),

    _tool("refresh_token",
          "Get a new access token using refresh token. Each refresh token can only be used once (token rotation).",
          ops.refresh_token,
          {"refresh_token": {"type": "string", "description": "The refresh token from login response"}},
          ["refresh_token"]),

    _tool("logout",
          "Log out the current session by revoking the refresh token.",
          ops.logout,
          {"refresh_token": {"type": "string", "description": "The refresh token to revoke"}},
          ["refresh_token"]),

    _tool("logout_all",
          "Log out from ALL devices by revoking all refresh tokens. Requires authentication.",
          ops.logout_all),

    # ── Company Discovery ─────────────────────────────────────────
    _tool("list_companies",
          "Browse and search companies on the platform. No authentication required.",
          ops.list_companies,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 12)"},
           "search": {"type": "string", "description": "Search by company name"},
           "service_type": {"type": "string", "description": "Filter by service type (e.g., 'Cleaning', 'Moving')"},
           "sort_by": {"type": "string", "description": "Sort by: 'rating', 'name', 'newest' (default: 'rating')"}}),

    _tool("get_recommended_companies",
          "Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required.",
          ops.get_recommended_companies,
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_trending_companies",
          "Get companies with improving recent reviews (last 90 days).",
          ops.get_trending_companies,
          {"service_type": {"type": "string", "description": "Filter by service type"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}}),

    _tool("get_company_details",
          "Get detailed information about a specific company including contact info, services offered. No authentication required.",
          ops.get_company_details,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_company_reviews",
          "Get paginated customer reviews for a company. No authentication required.",
          ops.get_company_reviews,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "sort_by": {"type": "string", "description": "Sort by: 'newest', 'highest-rated' (default: 'newest')"}},
          ["company_id"]),

    # ── Reviews ───────────────────────────────────────────────────
    _tool("submit_review",
          "Submit a new review for a company. Requires Customer authentication. Only one review per customer per company.",
          ops.submit_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Star rating 1-5"},
           "review_text": {"type": "string", "description": "Review text, max 2000 chars (optional)"}},
          ["company_id", "rating"]),

    _tool("update_review",
          "Update an existing review. Only the customer who created the review can update it.",
          ops.update_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "rating": {"type": "integer", "description": "Updated star rating 1-5"},
           "review_text": {"type": "string", "description": "Updated review text, max 2000 chars"}},
          ["company_id", "rating"]),

    _tool("delete_review",
          "Delete the customer's own review for a company. This action cannot be undone.",
          ops.delete_review,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"}},
          ["company_id"]),

    _tool("get_my_reviews",
          "Get all reviews written by the authenticated customer across all companies.",
          ops.get_my_reviews,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"}}),

    # ── Profiles ──────────────────────────────────────────────────
    _tool("get_customer_profile",
          "Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId).",
          ops.get_customer_profile),

    _tool("update_customer_profile",
          "Update the authenticated customer's profile. Email cannot be changed.",
          ops.update_customer_profile,
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_lead_profile",
          "Get the lead's profile including list of connected companies.",
          ops.get_lead_profile),

    _tool("update_lead_profile",
          "Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
          ops.update_lead_profile,
          {"first_name": {"type": "string", "description": "First name"},
           "last_name": {"type": "string", "description": "Last name"},
           "phone_number": {"type": "string", "description": "Phone number"},
           "address": {"type": "string", "description": "Street address"},
           "city": {"type": "string", "description": "City"},
           "zip_code": {"type": "string", "description": "Zip/Postal code"},
           "country": {"type": "string", "description": "Country"}},
          ["first_name", "last_name"]),

    _tool("get_digital_signature",
          "Get the user's digital signature after password verification. Required to accept offers.",
          ops.get_digital_signature,
          {"password": {"type": "string", "description": "User's current password to verify identity"}},
          ["password"]),

    # ── Offers ────────────────────────────────────────────────────
    _tool("get_my_offers",
          "Get all offers (quotes) sent to the customer by companies.",
          ops.get_my_offers,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'"}}),

    _tool("get_offer_details",
          "Get detailed information about a specific offer including service line items and pricing breakdown.",
          ops.get_offer_details,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"}},
          ["offer_id"]),

    _tool("accept_offer",
          "Accept an offer. Requires digital signature. Choose COD (Cash on Delivery) or Online (Stripe) payment.",
          ops.accept_offer,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "digital_signature": {"type": "string", "description": "User's digital signature (get via get_digital_signature)"},
           "payment_method": {"type": "string", "description": "Payment method: 'COD' or 'Online'"}},
          ["offer_id", "digital_signature", "payment_method"]),

    _tool("reject_offer",
          "Reject an offer. Must provide a reason for rejection.",
          ops.reject_offer,
          {"offer_id": {"type": "integer", "description": "The offer's numeric ID"},
           "rejection_reason": {"type": "string", "description": "Reason for rejection (max 2000 chars)"}},
          ["offer_id", "rejection_reason"]),

    _tool("get_dashboard",
          "Get dashboard summary showing total offers, offers by status, total reviews, and recent activity.",
          ops.get_dashboard),

    # ── Service Requests ──────────────────────────────────────────
    _tool("create_service_request",
          "Submit a service inquiry to a company. Can be done by both Lead and Customer users.",
          ops.create_service_request,
          {"company_id": {"type": "integer", "description": "The company's numeric ID"},
           "service_type": {"type": "string", "description": "Type of service (e.g., 'Moving', 'Cleaning')"},
           "from_street": {"type": "string", "description": "Origin street address"},
           "from_city": {"type": "string", "description": "Origin city"},
           "from_zip_code": {"type": "string", "description": "Origin zip code"},
           "from_country": {"type": "string", "description": "Origin country"},
           "to_street": {"type": "string", "description": "Destination street address"},
           "to_city": {"type": "string", "description": "Destination city"},
           "to_zip_code": {"type": "string", "description": "Destination zip code"},
           "to_country": {"type": "string", "description": "Destination country"},
           "preferred_date": {"type": "string", "description": "Preferred service date (YYYY-MM-DD)"},
           "preferred_time_slot": {"type": "string", "description": "Preferred time (e.g., 'Morning 8am-12pm')"},
           "notes": {"type": "string", "description": "Additional notes (max 2000 chars)"}},
          ["company_id", "service_type"]),

    _tool("get_my_service_requests",
          "Get all service requests submitted by the authenticated customer.",
          ops.get_my_service_requests,
          {"page_index": {"type": "integer", "description": "Page number (default: 1)"},
           "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
           "status": {"type": "string", "description": "Filter by status: 'Pending', 'InProgress', 'Closed'"}}),

    _tool("get_service_request_details",
          "Get detailed information about a specific service request.",
          ops.get_service_request_details,
          {"service_request_id": {"type": "integer", "description": "The service request's numeric ID"}},
          ["service_request_id"]),
]

# ── Registry ──────────────────────────────────────────────────────

_REGISTRY = {t["name"]: t["handler"] for t in TOOLS}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return tool definitions for ReAct prompt generation (without handler)."""
    return [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in TOOLS
    ]


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    ctx: dict[str, Any],
) -> str:
    """Look up tool by name, execute, return JSON string."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    func = _REGISTRY.get(tool_name)
    if func is None:
        logger.warning("Unknown tool requested: %s", tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Tool %s raised an error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
```

- [ ] **Step 2: Commit**

```bash
git add app/customer/tools.py
git commit -m "feat: add customer tools (merged schemas + registry)"
```

---

## Task 9: Create Company Domain — Client

**Files:**
- Create: `app/company/__init__.py`
- Create: `app/company/client.py`

- [ ] **Step 1: Create `app/company/__init__.py`**

```python
"""Company portal domain — tools, operations, and HTTP client."""
```

- [ ] **Step 2: Create `app/company/client.py`**

Thin wrapper over `BaseApiClient` with all methods from the old `company_client.py`.

```python
"""Async HTTP client for the Wasla Company Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.http_client import BaseApiClient


class CompanyClient(BaseApiClient):
    """Company Portal API client — extends BaseApiClient with domain methods."""

    # ── Auth ──────────────────────────────────────────────────────

    async def login_staff(self, *, email: str, password: str) -> dict[str, Any]:
        return await self.request("POST", "/login", body={"email": email, "password": password})

    async def change_password(self, bearer: str, *, current_password: str, new_password: str, confirm_password: str) -> dict[str, Any]:
        return await self.request("POST", "/change-password", bearer=bearer,
                                   body={"currentPassword": current_password, "newPassword": new_password, "confirmPassword": confirm_password})

    # ── Customers ─────────────────────────────────────────────────

    async def get_customers(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Customer", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size, "search": search}))

    async def get_customer_details(self, bearer: str, customer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}", bearer=bearer)

    async def create_customer(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Customer", bearer=bearer, body=payload)

    async def update_customer(self, bearer: str, customer_id: int, payload: dict) -> dict[str, Any]:
        payload["customerId"] = customer_id
        return await self.request("PUT", "/Customer", bearer=bearer, body=payload)

    async def delete_customer(self, bearer: str, customer_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Customer/{customer_id}", bearer=bearer)

    async def get_customer_offers(self, bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}/offers", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size}))

    async def get_customer_tasks(self, bearer: str, customer_id: int, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Customer/{customer_id}/tasks", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size}))

    # ── Offers ────────────────────────────────────────────────────

    async def get_offers(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                         search_word: str | None = None, status: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Offers", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size, "searchWord": search_word, "status": status}))

    async def get_offer_details(self, bearer: str, offer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Offers/{offer_id}", bearer=bearer)

    async def create_offer(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Offers", bearer=bearer, body=payload)

    async def update_offer(self, bearer: str, offer_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Offers/{offer_id}", bearer=bearer, body=payload)

    async def update_offer_status(self, bearer: str, offer_id: int, *, status: str) -> dict[str, Any]:
        return await self.request("PATCH", f"/Offers/{offer_id}/status", bearer=bearer, body=status)

    async def delete_offer(self, bearer: str, offer_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Offers/{offer_id}", bearer=bearer)

    # ── Tasks ─────────────────────────────────────────────────────

    async def get_all_tasks(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Task/all", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size}))

    async def get_my_tasks(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Task/assigned-to-me", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size}))

    async def get_task_details(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Task/{task_id}", bearer=bearer)

    async def create_task(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Task/AddTask", bearer=bearer, body=payload)

    async def update_task(self, bearer: str, task_id: int, payload: dict) -> dict[str, Any]:
        payload["taskId"] = task_id
        return await self.request("PUT", "/Task", bearer=bearer, body=payload)

    async def start_task(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/start", bearer=bearer)

    async def complete_task(self, bearer: str, task_id: int) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/complete", bearer=bearer)

    async def reassign_task(self, bearer: str, task_id: int, *, new_assignee_id: int, reason: str) -> dict[str, Any]:
        return await self.request("POST", f"/Task/{task_id}/reassign", bearer=bearer,
                                   body={"newAssigneeId": new_assignee_id, "reason": reason})

    async def search_employees(self, bearer: str, *, search_name: str) -> dict[str, Any]:
        return await self.request("GET", "/Task/employees", bearer=bearer, params={"searchName": search_name})

    async def search_customers(self, bearer: str, *, search_name: str) -> dict[str, Any]:
        return await self.request("GET", "/Task/customers", bearer=bearer, params={"searchName": search_name})

    # ── Employees ─────────────────────────────────────────────────

    async def get_employees(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Employees", bearer=bearer, params=self.clean_params({"pageIndex": page_index, "pageSize": page_size, "search": search}))

    async def get_employee_details(self, bearer: str, user_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Employees/{user_id}", bearer=bearer)

    async def create_employee(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Employees", bearer=bearer, body=payload)

    async def update_employee(self, bearer: str, user_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Employees/{user_id}", bearer=bearer, body=payload)

    async def delete_employee(self, bearer: str, user_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Employees/{user_id}", bearer=bearer)

    async def get_employee_performance(self, bearer: str, employee_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/Employees/{employee_id}/performance", bearer=bearer)

    # ── Expenses ──────────────────────────────────────────────────

    async def get_expenses(self, bearer: str, *, page: int | None = None, page_size: int | None = None,
                           search: str | None = None, category: str | None = None,
                           from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Expenses", bearer=bearer,
                                   params=self.clean_params({"page": page, "pageSize": page_size, "search": search, "category": category, "from": from_date, "to": to_date}))

    async def create_expense(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Expenses", bearer=bearer, body=payload)

    async def update_expense(self, bearer: str, expense_id: int, payload: dict) -> dict[str, Any]:
        return await self.request("PUT", f"/Expenses/{expense_id}", bearer=bearer, body=payload)

    async def delete_expense(self, bearer: str, expense_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/Expenses/{expense_id}", bearer=bearer)

    async def get_expense_charts(self, bearer: str, *, chart_type: str, from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", f"/Expenses/{chart_type}-chart", bearer=bearer,
                                   params=self.clean_params({"from": from_date, "to": to_date}))

    # ── Appointments ──────────────────────────────────────────────

    async def get_appointments(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None,
                               search: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/Appointments", bearer=bearer,
                                   params=self.clean_params({"pageIndex": page_index, "pageSize": page_size, "search": search, "startDate": start_date, "endDate": end_date}))

    async def create_appointment(self, bearer: str, payload: dict) -> dict[str, Any]:
        return await self.request("POST", "/Appointments", bearer=bearer, body=payload)

    # ── Dashboard ─────────────────────────────────────────────────

    async def get_dashboard(self, bearer: str) -> dict[str, Any]:
        return await self.request("GET", "/CompanyDashboard", bearer=bearer)

    # ── Service Requests ──────────────────────────────────────────

    async def get_service_requests(self, bearer: str, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict[str, Any]:
        return await self.request("GET", "/company/service-requests", bearer=bearer,
                                   params=self.clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status}))

    async def get_service_request_details(self, bearer: str, request_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/company/service-requests/{request_id}", bearer=bearer)

    async def decline_service_request(self, bearer: str, request_id: int, *, reason: str | None = None) -> dict[str, Any]:
        body = {"reason": reason} if reason else {}
        return await self.request("PUT", f"/company/service-requests/{request_id}/decline", bearer=bearer, body=body)
```

- [ ] **Step 3: Commit**

```bash
git add app/company/__init__.py app/company/client.py
git commit -m "feat: add CompanyClient extending BaseApiClient"
```

---

## Task 10: Create Company Domain — Operations

**Files:**
- Create: `app/company/operations.py`

- [ ] **Step 1: Create `app/company/operations.py`**

Adapted from `app/tools/company_operations.py`. Uses `require_bearer` from shared auth and `ctx["client"]`.

```python
"""Tool operations — Company Portal API (staff-facing)."""

from __future__ import annotations

from typing import Any

from app.shared.auth import require_bearer


# ── Auth ──────────────────────────────────────────────────────────

async def login_staff(ctx: dict, *, email: str, password: str) -> dict:
    return await ctx["client"].login_staff(email=email, password=password)


async def change_password(ctx: dict, *, current_password: str, new_password: str, confirm_password: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].change_password(t, current_password=current_password, new_password=new_password, confirm_password=confirm_password)


# ── Customers ─────────────────────────────────────────────────────

async def get_customers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customers(t, page_index=page_index, page_size=page_size, search=search)


async def get_customer_details(ctx: dict, *, customer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_details(t, customer_id)


async def create_customer(ctx: dict, *, first_name: str, last_name: str, email: str, phone_number: str,
                           address: str, city: str, zip_code: str, country: str, notes: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload = {"firstName": first_name, "lastName": last_name, "email": email, "phoneNumber": phone_number,
               "address": address, "city": city, "zipCode": zip_code, "country": country, "notes": notes}
    return await ctx["client"].create_customer(t, payload)


async def update_customer(ctx: dict, *, customer_id: int, first_name: str | None = None, last_name: str | None = None,
                           email: str | None = None, phone_number: str | None = None, address: str | None = None,
                           city: str | None = None, zip_code: str | None = None, country: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if first_name is not None: payload["firstName"] = first_name
    if last_name is not None: payload["lastName"] = last_name
    if email is not None: payload["email"] = email
    if phone_number is not None: payload["phoneNumber"] = phone_number
    if address is not None: payload["address"] = address
    if city is not None: payload["city"] = city
    if zip_code is not None: payload["zipCode"] = zip_code
    if country is not None: payload["country"] = country
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].update_customer(t, customer_id, payload)


async def delete_customer(ctx: dict, *, customer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_customer(t, customer_id)


async def get_customer_offers(ctx: dict, *, customer_id: int, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_offers(t, customer_id, page_index=page_index, page_size=page_size)


async def get_customer_tasks(ctx: dict, *, customer_id: int, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_tasks(t, customer_id, page_index=page_index, page_size=page_size)


# ── Offers ────────────────────────────────────────────────────────

async def get_offers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                     search_word: str | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offers(t, page_index=page_index, page_size=page_size, search_word=search_word, status=status)


async def get_offer_details(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offer_details(t, offer_id)


async def create_offer(ctx: dict, *, customer_id: int, service_request_id: int | None = None,
                        notes_in_offer: str | None = None, notes_not_in_offer: str | None = None,
                        language_code: str | None = None, email_to_customer: bool | None = None,
                        locations: list | None = None, services: dict | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"customerId": customer_id}
    if service_request_id is not None: payload["serviceRequestId"] = service_request_id
    if notes_in_offer is not None: payload["notesInOffer"] = notes_in_offer
    if notes_not_in_offer is not None: payload["notesNotInOffer"] = notes_not_in_offer
    if language_code is not None: payload["languageCode"] = language_code
    if email_to_customer is not None: payload["emailToCustomer"] = email_to_customer
    if locations is not None: payload["locations"] = locations
    if services is not None: payload["services"] = services
    return await ctx["client"].create_offer(t, payload)


async def update_offer(ctx: dict, *, offer_id: int, customer_id: int | None = None,
                        notes_in_offer: str | None = None, notes_not_in_offer: str | None = None,
                        locations: list | None = None, services: dict | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if customer_id is not None: payload["customerId"] = customer_id
    if notes_in_offer is not None: payload["notesInOffer"] = notes_in_offer
    if notes_not_in_offer is not None: payload["notesNotInOffer"] = notes_not_in_offer
    if locations is not None: payload["locations"] = locations
    if services is not None: payload["services"] = services
    return await ctx["client"].update_offer(t, offer_id, payload)


async def update_offer_status(ctx: dict, *, offer_id: int, status: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].update_offer_status(t, offer_id, status=status)


async def delete_offer(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_offer(t, offer_id)


# ── Tasks ─────────────────────────────────────────────────────────

async def get_all_tasks(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_all_tasks(t, page_index=page_index, page_size=page_size)


async def get_my_tasks(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_tasks(t, page_index=page_index, page_size=page_size)


async def get_task_details(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_task_details(t, task_id)


async def create_task(ctx: dict, *, assigned_to_user_id: int, task_title: str, customer_id: int | None = None,
                       description: str | None = None, priority: str | None = None, due_date: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"assignedToUserId": assigned_to_user_id, "taskTitle": task_title}
    if customer_id is not None: payload["customerId"] = customer_id
    if description is not None: payload["description"] = description
    if priority is not None: payload["priority"] = priority
    if due_date is not None: payload["dueDate"] = due_date
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].create_task(t, payload)


async def update_task(ctx: dict, *, task_item_id: int, assigned_to_user_id: int | None = None,
                       customer_id: int | None = None, task_title: str | None = None,
                       description: str | None = None, priority: str | None = None,
                       due_date: str | None = None, notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if assigned_to_user_id is not None: payload["assignedToUserId"] = assigned_to_user_id
    if customer_id is not None: payload["customerId"] = customer_id
    if task_title is not None: payload["taskTitle"] = task_title
    if description is not None: payload["description"] = description
    if priority is not None: payload["priority"] = priority
    if due_date is not None: payload["dueDate"] = due_date
    if notes is not None: payload["notes"] = notes
    return await ctx["client"].update_task(t, task_item_id, payload)


async def start_task(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].start_task(t, task_id)


async def complete_task(ctx: dict, *, task_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].complete_task(t, task_id)


async def reassign_task(ctx: dict, *, task_id: int, new_assignee_id: int, reason: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].reassign_task(t, task_id, new_assignee_id=new_assignee_id, reason=reason)


async def search_employees(ctx: dict, *, search_name: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].search_employees(t, search_name=search_name)


async def search_customers(ctx: dict, *, search_name: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].search_customers(t, search_name=search_name)


# ── Employees ─────────────────────────────────────────────────────

async def get_employees(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, search: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employees(t, page_index=page_index, page_size=page_size, search=search)


async def get_employee_details(ctx: dict, *, user_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employee_details(t, user_id)


async def create_employee(ctx: dict, *, first_name: str, last_name: str, email: str, user_name: str, password: str,
                           is_active: bool | None = None, permission_ids: list | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name, "email": email, "userName": user_name, "password": password}
    if is_active is not None: payload["isActive"] = is_active
    if permission_ids is not None: payload["permissionIds"] = permission_ids
    return await ctx["client"].create_employee(t, payload)


async def update_employee(ctx: dict, *, user_id: int, first_name: str | None = None, last_name: str | None = None,
                           email: str | None = None, user_name: str | None = None, new_password: str | None = None,
                           is_active: bool | None = None, permission_ids: list | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if first_name is not None: payload["firstName"] = first_name
    if last_name is not None: payload["lastName"] = last_name
    if email is not None: payload["email"] = email
    if user_name is not None: payload["userName"] = user_name
    if new_password is not None: payload["newPassword"] = new_password
    if is_active is not None: payload["isActive"] = is_active
    if permission_ids is not None: payload["permissionIds"] = permission_ids
    return await ctx["client"].update_employee(t, user_id, payload)


async def delete_employee(ctx: dict, *, user_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_employee(t, user_id)


async def get_employee_performance(ctx: dict, *, employee_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_employee_performance(t, employee_id)


# ── Expenses ──────────────────────────────────────────────────────

async def get_expenses(ctx: dict, *, page: int | None = None, page_size: int | None = None,
                       search: str | None = None, category: str | None = None, **kw) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_expenses(t, page=page, page_size=page_size, search=search, category=category,
                                             from_date=kw.get("from"), to_date=kw.get("to"))


async def create_expense(ctx: dict, *, description: str, amount_egp: float, expense_date: str, category: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].create_expense(t, {"description": description, "amountEgp": amount_egp, "expenseDate": expense_date, "category": category})


async def update_expense(ctx: dict, *, expense_id: int, description: str | None = None, amount_egp: float | None = None,
                          expense_date: str | None = None, category: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {}
    if description is not None: payload["description"] = description
    if amount_egp is not None: payload["amountEgp"] = amount_egp
    if expense_date is not None: payload["expenseDate"] = expense_date
    if category is not None: payload["category"] = category
    return await ctx["client"].update_expense(t, expense_id, payload)


async def delete_expense(ctx: dict, *, expense_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_expense(t, expense_id)


async def get_expense_charts(ctx: dict, *, chart_type: str, **kw) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_expense_charts(t, chart_type=chart_type, from_date=kw.get("from"), to_date=kw.get("to"))


# ── Appointments ──────────────────────────────────────────────────

async def get_appointments(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                           search: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_appointments(t, page_index=page_index, page_size=page_size, search=search, start_date=start_date, end_date=end_date)


async def create_appointment(ctx: dict, *, customer_id: int, scheduled_at: str,
                             location: str | None = None, notes: str | None = None, language_code: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    payload: dict[str, Any] = {"customerId": customer_id, "scheduledAt": scheduled_at}
    if location is not None: payload["location"] = location
    if notes is not None: payload["notes"] = notes
    if language_code is not None: payload["languageCode"] = language_code
    return await ctx["client"].create_appointment(t, payload)


# ── Dashboard ─────────────────────────────────────────────────────

async def get_dashboard(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_dashboard(t)


# ── Service Requests ──────────────────────────────────────────────

async def get_service_requests(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_requests(t, page_index=page_index, page_size=page_size, status=status)


async def get_service_request_details(ctx: dict, *, request_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_request_details(t, request_id)


async def decline_service_request(ctx: dict, *, request_id: int, reason: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].decline_service_request(t, request_id, reason=reason)
```

- [ ] **Step 2: Commit**

```bash
git add app/company/operations.py
git commit -m "feat: add company operations using shared auth + ctx client"
```

---

## Task 11: Create Company Domain — Tools (Merged Schemas + Registry)

**Files:**
- Create: `app/company/tools.py`

Due to the large size of this file (40 tool definitions), this step creates `app/company/tools.py` following the exact same pattern as `app/customer/tools.py` from Task 8. The tool definitions come from the old `app/tools/company_schemas.py` and the registry/aliases from `app/tools/company_registry.py`.

- [ ] **Step 1: Create `app/company/tools.py`**

```python
"""Company Portal tools — schemas, registry, and executor merged."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.company import operations as ops

logger = logging.getLogger("wasla.company.tools")


def _tool(name: str, description: str, handler, properties: dict | None = None, required: list[str] | None = None) -> dict:
    params: dict[str, Any] = {"type": "object", "properties": properties or {}, "required": required or []}
    return {"name": name, "description": description, "parameters": params, "handler": handler}


TOOLS: list[dict[str, Any]] = [
    # ── Auth ──────────────────────────────────────────────────────
    _tool("login_staff",
          "Authenticate a company staff member (Manager or Employee). Returns JWT with company ID, role, and permissions.",
          ops.login_staff,
          {"email": {"type": "string"}, "password": {"type": "string"}},
          ["email", "password"]),

    _tool("change_password",
          "Change the current user's password. Requires authentication.",
          ops.change_password,
          {"current_password": {"type": "string"}, "new_password": {"type": "string"}, "confirm_password": {"type": "string"}},
          ["current_password", "new_password", "confirm_password"]),

    # ── Customers ─────────────────────────────────────────────────
    _tool("get_customers",
          "Get paginated list of customers. Requires can_edit_customers.",
          ops.get_customers,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}, "search": {"type": "string", "description": "Search by name or email"}}),

    _tool("get_customer_details",
          "Get detailed customer info including offer count, task count, total profit. Requires can_edit_customers.",
          ops.get_customer_details,
          {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _tool("create_customer",
          "Create a new customer record. Requires can_edit_customers.",
          ops.create_customer,
          {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
           "phone_number": {"type": "string"}, "address": {"type": "string"}, "city": {"type": "string"},
           "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
          ["first_name", "last_name", "email", "phone_number", "address", "city", "zip_code", "country", "notes"]),

    _tool("update_customer",
          "Update an existing customer's information. Requires can_edit_customers.",
          ops.update_customer,
          {"customer_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
           "email": {"type": "string"}, "phone_number": {"type": "string"}, "address": {"type": "string"},
           "city": {"type": "string"}, "zip_code": {"type": "string"}, "country": {"type": "string"}, "notes": {"type": "string"}},
          ["customer_id"]),

    _tool("delete_customer",
          "Delete a customer record. Requires can_edit_customers. Confirm with user first.",
          ops.delete_customer,
          {"customer_id": {"type": "integer"}}, ["customer_id"]),

    _tool("get_customer_offers",
          "Get offer history for a specific customer. Requires can_edit_customers.",
          ops.get_customer_offers,
          {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
          ["customer_id"]),

    _tool("get_customer_tasks",
          "Get task history for a specific customer. Requires can_edit_customers.",
          ops.get_customer_tasks,
          {"customer_id": {"type": "integer"}, "page_index": {"type": "integer"}, "page_size": {"type": "integer"}},
          ["customer_id"]),

    # ── Offers ────────────────────────────────────────────────────
    _tool("get_offers", "Get paginated list of offers. Requires can_view_offers.", ops.get_offers,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search_word": {"type": "string", "description": "Search by client name or offer number"},
           "status": {"type": "string", "description": "Filter: Pending, Sent, Accepted, Rejected, Canceled"}}),

    _tool("get_offer_details", "Get full offer details including services, locations, and line items. Requires can_view_offers.", ops.get_offer_details,
          {"offer_id": {"type": "integer"}}, ["offer_id"]),

    _tool("create_offer", "Create a new offer/quote for a customer. Can link to a service request. Requires can_view_offers.", ops.create_offer,
          {"customer_id": {"type": "integer", "description": "Customer ID (required)"},
           "service_request_id": {"type": "integer", "description": "Link to service request (auto-updates to OfferSent)"},
           "notes_in_offer": {"type": "string", "description": "Notes visible to customer"},
           "notes_not_in_offer": {"type": "string", "description": "Internal notes"},
           "language_code": {"type": "string", "description": "e.g. 'en', 'de'"},
           "email_to_customer": {"type": "boolean", "description": "Send email notification"},
           "locations": {"type": "array", "description": "List of locations (From, To)", "items": {"type": "object"}},
           "services": {"type": "object", "description": "Service details (Moving, Cleaning, Packing, etc.)"}},
          ["customer_id"]),

    _tool("update_offer", "Update an existing offer's details. Requires can_view_offers.", ops.update_offer,
          {"offer_id": {"type": "integer"}, "customer_id": {"type": "integer"},
           "notes_in_offer": {"type": "string"}, "notes_not_in_offer": {"type": "string"},
           "locations": {"type": "array", "items": {"type": "object"}}, "services": {"type": "object"}},
          ["offer_id"]),

    _tool("update_offer_status", "Change offer status (e.g. cancel). Requires can_view_offers.", ops.update_offer_status,
          {"offer_id": {"type": "integer"}, "status": {"type": "string", "enum": ["Pending", "Sent", "Accepted", "Rejected", "Canceled"]}},
          ["offer_id", "status"]),

    _tool("delete_offer", "Delete an offer. Only allowed for offers not yet accepted. Requires can_view_offers.", ops.delete_offer,
          {"offer_id": {"type": "integer"}}, ["offer_id"]),

    # ── Tasks ─────────────────────────────────────────────────────
    _tool("get_all_tasks", "Get all company tasks with summary statistics. Requires can_manage_tasks (Manager only).", ops.get_all_tasks,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _tool("get_my_tasks", "Get tasks assigned to the current employee. Available to both Manager and Employee roles.", ops.get_my_tasks,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"}}),

    _tool("get_task_details", "Get detailed task info including status, duration, files, assignment history.", ops.get_task_details,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("create_task", "Create a new task and assign to an employee. Requires can_manage_tasks.", ops.create_task,
          {"assigned_to_user_id": {"type": "integer", "description": "Employee ID to assign to"},
           "customer_id": {"type": "integer", "description": "Optional: link to customer"},
           "task_title": {"type": "string"}, "description": {"type": "string"},
           "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
           "due_date": {"type": "string", "description": "YYYY-MM-DD"}, "notes": {"type": "string"}},
          ["assigned_to_user_id", "task_title"]),

    _tool("update_task", "Update task details. Requires can_manage_tasks.", ops.update_task,
          {"task_item_id": {"type": "integer"}, "assigned_to_user_id": {"type": "integer"},
           "customer_id": {"type": "integer"}, "task_title": {"type": "string"},
           "description": {"type": "string"}, "priority": {"type": "string"},
           "due_date": {"type": "string"}, "notes": {"type": "string"}},
          ["task_item_id"]),

    _tool("start_task", "Start a task (Pending -> InProgress). Available to the assigned employee.", ops.start_task,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("complete_task", "Mark a task as completed. Available to the assigned employee.", ops.complete_task,
          {"task_id": {"type": "integer"}}, ["task_id"]),

    _tool("reassign_task", "Reassign a task to another employee. Creates audit trail. Requires can_manage_tasks.", ops.reassign_task,
          {"task_id": {"type": "integer"}, "new_assignee_id": {"type": "integer"}, "reason": {"type": "string"}},
          ["task_id", "new_assignee_id", "reason"]),

    _tool("search_employees", "Search employees by name (autocomplete helper for task assignment).", ops.search_employees,
          {"search_name": {"type": "string"}}, ["search_name"]),

    _tool("search_customers", "Search customers by name (autocomplete helper for task/offer creation).", ops.search_customers,
          {"search_name": {"type": "string"}}, ["search_name"]),

    # ── Employees ─────────────────────────────────────────────────
    _tool("get_employees", "Get paginated list of employees. Requires can_manage_users.", ops.get_employees,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string", "description": "Search by name or email"}}),

    _tool("get_employee_details", "Get employee details including permissions and task counts. Requires can_manage_users.", ops.get_employee_details,
          {"user_id": {"type": "integer"}}, ["user_id"]),

    _tool("create_employee", "Create a new employee account. Requires can_manage_users.", ops.create_employee,
          {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"},
           "user_name": {"type": "string"}, "password": {"type": "string"},
           "is_active": {"type": "boolean", "description": "Default: true"},
           "permission_ids": {"type": "array", "description": "Permission IDs to assign", "items": {"type": "integer"}}},
          ["first_name", "last_name", "email", "user_name", "password"]),

    _tool("update_employee", "Update employee information. Requires can_manage_users.", ops.update_employee,
          {"user_id": {"type": "integer"}, "first_name": {"type": "string"}, "last_name": {"type": "string"},
           "email": {"type": "string"}, "user_name": {"type": "string"},
           "new_password": {"type": "string", "description": "Optional new password"},
           "is_active": {"type": "boolean"},
           "permission_ids": {"type": "array", "items": {"type": "integer"}}},
          ["user_id"]),

    _tool("delete_employee", "Delete/deactivate an employee. Requires can_manage_users. Confirm first.", ops.delete_employee,
          {"user_id": {"type": "integer"}}, ["user_id"]),

    _tool("get_employee_performance", "Get performance report including completion rates. Requires can_manage_users.", ops.get_employee_performance,
          {"employee_id": {"type": "integer"}}, ["employee_id"]),

    # ── Expenses ──────────────────────────────────────────────────
    _tool("get_expenses", "Get paginated expenses. Requires can_view_reports.", ops.get_expenses,
          {"page": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string"}, "category": {"type": "string"},
           "from": {"type": "string", "description": "Start date YYYY-MM-DD"},
           "to": {"type": "string", "description": "End date YYYY-MM-DD"}}),

    _tool("create_expense", "Record a new expense. Requires can_view_reports.", ops.create_expense,
          {"description": {"type": "string"}, "amount_egp": {"type": "number"},
           "expense_date": {"type": "string", "description": "YYYY-MM-DD"}, "category": {"type": "string"}},
          ["description", "amount_egp", "expense_date", "category"]),

    _tool("update_expense", "Update an expense record. Requires can_view_reports.", ops.update_expense,
          {"expense_id": {"type": "integer"}, "description": {"type": "string"},
           "amount_egp": {"type": "number"}, "expense_date": {"type": "string"}, "category": {"type": "string"}},
          ["expense_id"]),

    _tool("delete_expense", "Delete an expense record. Requires can_view_reports. Confirm first.", ops.delete_expense,
          {"expense_id": {"type": "integer"}}, ["expense_id"]),

    _tool("get_expense_charts", "Get expense chart data (monthly trend or category breakdown). Requires can_view_reports.", ops.get_expense_charts,
          {"chart_type": {"type": "string", "enum": ["monthly", "category"]},
           "from": {"type": "string", "description": "Start date (optional)"},
           "to": {"type": "string", "description": "End date (optional)"}},
          ["chart_type"]),

    # ── Appointments ──────────────────────────────────────────────
    _tool("get_appointments", "Get paginated list of appointments for the company. Requires can_view_offers.", ops.get_appointments,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "search": {"type": "string", "description": "Filter by customer name or location"},
           "start_date": {"type": "string", "description": "Filter from date (ISO 8601)"},
           "end_date": {"type": "string", "description": "Filter to date (ISO 8601)"}}),

    _tool("create_appointment", "Schedule a new appointment (on-site visit). Requires can_view_offers.", ops.create_appointment,
          {"customer_id": {"type": "integer"}, "scheduled_at": {"type": "string", "description": "UTC datetime ISO 8601"},
           "location": {"type": "string", "description": "Site address"}, "notes": {"type": "string"},
           "language_code": {"type": "string", "description": "en, de, fr, it"}},
          ["customer_id", "scheduled_at"]),

    # ── Dashboard ─────────────────────────────────────────────────
    _tool("get_dashboard", "Get company dashboard with KPIs, charts, and important tasks. Requires can_view_reports.", ops.get_dashboard),

    # ── Service Requests ──────────────────────────────────────────
    _tool("get_service_requests", "Get incoming service requests from portal users. Requires can_view_offers.", ops.get_service_requests,
          {"page_index": {"type": "integer"}, "page_size": {"type": "integer"},
           "status": {"type": "string", "description": "Filter: New, Viewed, OfferSent, Declined"}}),

    _tool("get_service_request_details", "Get details of a specific service request. Requires can_view_offers.", ops.get_service_request_details,
          {"request_id": {"type": "integer"}}, ["request_id"]),

    _tool("decline_service_request", "Decline a service request from a portal user. Requires can_view_offers.", ops.decline_service_request,
          {"request_id": {"type": "integer"}, "reason": {"type": "string", "description": "Reason for declining (optional)"}},
          ["request_id"]),
]

# ── Registry ──────────────────────────────────────────────────────

_REGISTRY = {t["name"]: t["handler"] for t in TOOLS}

_ALIASES: dict[str, str] = {
    "get_top_customers": "get_customers",
    "get_my_customers": "get_customers",
    "get_all_customers": "get_customers",
    "search_customer": "search_customers",
    "search_employee": "search_employees",
    "get_dashboard_data": "get_dashboard",
    "get_all_offers": "get_offers",
    "get_my_offers": "get_offers",
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return tool definitions for ReAct prompt generation (without handler)."""
    return [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in TOOLS
    ]


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | str,
    ctx: dict[str, Any],
) -> str:
    """Look up tool by name, execute, return JSON string."""
    # Handle the Google search hallucination from Gemma specifically
    if tool_name == "google:search" or ("search" in tool_name and "google" in tool_name):
        return json.dumps({"error": "Internet search disabled. Use internal CRM tools like get_customers, get_offers, etc."})

    # Transparently map common LLM hallucinations to the correct tool
    real_tool_name = _ALIASES.get(tool_name, tool_name)

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

    func = _REGISTRY.get(real_tool_name)
    if func is None:
        logger.warning("Unknown company tool: %s (originally %s)", real_tool_name, tool_name)
        return json.dumps({"error": f"Unknown tool: {tool_name}. Check the exact tool names in your schema."})

    try:
        result = await func(ctx, **arguments)
    except Exception as exc:
        logger.exception("Company tool %s raised error", tool_name)
        result = {"error": str(exc)}

    return json.dumps(result)
```

- [ ] **Step 2: Commit**

```bash
git add app/company/tools.py
git commit -m "feat: add company tools (merged schemas + registry + aliases)"
```

---

## Task 12: Update Routes to Use New Architecture

**Files:**
- Modify: `app/api/routes/chat.py`
- Modify: `app/api/routes/company_chat.py`

- [ ] **Step 1: Rewrite `app/api/routes/chat.py`**

Replace the entire file with the new thin route that uses shared auth, prompt loading, and ReactEngine.

```python
"""
Route 1 — Customer Portal Chat (ReAct agent loop)
POST /api/chat         -> JSON response (Customer Portal agent)
POST /api/chat/{company_id} -> Legacy backward-compat route
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ChatRequest, ChatResponse, enforce_rate_limit
from app.shared.auth import extract_bearer
from app.shared.prompts import load_prompt
from app.customer import tools as customer_tools

logger = logging.getLogger("wasla.routes.chat")
router = APIRouter(tags=["Chat"])

_bearer_scheme = HTTPBearer(auto_error=False)


def _auth_status_line(is_authenticated: bool) -> str:
    if is_authenticated:
        return (
            "\n\nThe user IS authenticated — all protected tools will work. "
            "Call tools directly without asking for login."
        )
    return (
        "\n\nThe user is NOT authenticated (guest). "
        "Public tools work. For protected actions, suggest they log in first "
        "or offer to register/login via the register_customer or login_customer tools."
    )


async def _handle_chat(body: ChatRequest, request: Request, credentials, company_id: str | None = None):
    """Shared handler for both /api/chat and /api/chat/{company_id}."""
    token = extract_bearer(credentials, request)
    logger.info("Bearer extracted: %s", "YES" if token else "NO")

    engine = request.app.state.engine
    client = request.app.state.customer_client
    ctx = {"bearer_token": token, "client": client}

    system_prompt = load_prompt("customer_system.md")
    system_prompt += _auth_status_line(is_authenticated=token is not None)

    messages = [{"role": "system", "content": system_prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await engine.run(
            messages,
            tools=customer_tools.get_tool_schemas(),
            tool_executor=customer_tools.execute_tool,
            ctx=ctx,
        )
    except Exception as exc:
        logger.exception("Chat failed%s", f" for company {company_id}" if company_id else "")
        detail = "AI model is unavailable. Please try again later."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = (
                "LLM authentication failed. Set a valid LLM_API_KEY in .env."
            )
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Customer Portal — Agentic chat with tool calling",
    operation_id="portalChat",
    response_description="AI response with optional tool-call metadata.",
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
    **Customer Portal chat endpoint** — agentic tool-calling loop.

    The LLM can invoke 27 tools covering the full Customer Portal API:
    auth, companies, reviews, profiles, offers, service requests, dashboard.

    Click the **lock icon** (top-right) and paste your JWT to authenticate.
    Public actions (browse companies, view reviews) work without auth.
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

- [ ] **Step 2: Rewrite `app/api/routes/company_chat.py`**

Replace the entire file with the new thin route.

```python
"""
Company Portal Chat — staff-facing agentic endpoint.
POST /api/company/chat -> JSON response
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ChatRequest, ChatResponse
from app.shared.auth import extract_bearer
from app.shared.prompts import load_prompt
from app.company import tools as company_tools

logger = logging.getLogger("wasla.routes.company")
router = APIRouter(tags=["Company Chat"])

_bearer = HTTPBearer(auto_error=False)


def _auth_status_line(is_authenticated: bool) -> str:
    if is_authenticated:
        return "\n\nThe user IS authenticated. Call tools directly."
    return (
        "\n\nThe user is NOT authenticated. "
        "Offer to log them in via login_staff before using protected tools."
    )


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

    Click the lock icon and paste a staff JWT to authenticate.
    """
    token = extract_bearer(credentials, request)
    logger.info("Company bearer: %s", "YES" if token else "NO")

    engine = request.app.state.engine
    client = request.app.state.company_client
    ctx = {"bearer_token": token, "client": client}

    system_prompt = load_prompt("company_system.md")
    system_prompt += _auth_status_line(is_authenticated=token is not None)

    messages = [{"role": "system", "content": system_prompt}]
    if body.conversation_history:
        messages.extend(body.conversation_history)
    messages.append({"role": "user", "content": body.prompt})

    try:
        result = await engine.run(
            messages,
            tools=company_tools.get_tool_schemas(),
            tool_executor=company_tools.execute_tool,
            ctx=ctx,
        )
    except Exception as exc:
        logger.exception("Company chat failed")
        detail = "AI model is unavailable."
        if "401" in str(exc) or "Unauthorized" in str(exc):
            detail = "LLM authentication failed. Check LLM_API_KEY in .env."
        raise HTTPException(status_code=503, detail=detail) from exc

    return ChatResponse(**result)
```

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/chat.py app/api/routes/company_chat.py
git commit -m "feat: simplify routes to use ReactEngine + shared modules"
```

---

## Task 13: Update `main.py` — Lifespan and Imports

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Rewrite `app/main.py`**

Replace the entire file. Key changes: imports from new modules, lifespan creates clients and engine on `app.state` instead of module-level globals.

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
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.rate_limit import init_redis, close_redis
import app.core.rate_limit as rl
from app.shared.react_engine import ReactEngine
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

    # LLM client + ReAct engine
    llm_client = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    app.state.engine = ReactEngine(llm_client, s)

    yield

    await company_client.close()
    await customer_client.close()
    await close_redis()


# ── FastAPI app ───────────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Customer Chat",
        "description": "Customer-facing AI chat endpoint widget using an agentic tool-calling loop. Accessed externally via the Wasla Customer Portal.",
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
        "and the Internal Company CRM. It operates natively using local Ollama models (e.g. Qwen 2.5) "
        "or configured OpenRouter models to process intent and automatically execute backend actions.\n\n"
        "## Endpoints\n\n"
        "| Endpoint | Transport | Context | Capabilities |\n"
        "|----------|-----------|---------|--------------|\n"
        "| `POST /api/chat/{company_id}` | JSON | Public Customer Portal | General inquiries, submitting service requests, checking offers. |\n"
        "| `POST /api/company/chat` | JSON | Internal CRM | Full CRM capabilities (Customers, Offers, Tasks, Appointments). Requires JWT Bearer token authentication. |\n\n"
        "---\n"
        "**Authentication:** Include standard `Bearer <JWT_TOKEN>` in the headers when accessing protected internal endpoints."
    ),
    version="2.1.0",
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

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: update main.py lifespan for new architecture"
```

---

## Task 14: Delete Old Files

**Files to delete:**
- `app/services/__init__.py`
- `app/services/backend_client.py`
- `app/services/company_client.py`
- `app/services/llm_service.py`
- `app/services/react_parser.py`
- `app/prompts/__init__.py`
- `app/prompts/react_prompt.py`
- `app/tools/__init__.py`
- `app/tools/schemas.py`
- `app/tools/registry.py`
- `app/tools/operations.py`
- `app/tools/company_schemas.py`
- `app/tools/company_registry.py`
- `app/tools/company_operations.py`

- [ ] **Step 1: Delete all old files**

```bash
rm app/services/__init__.py app/services/backend_client.py app/services/company_client.py app/services/llm_service.py app/services/react_parser.py
rm app/prompts/__init__.py app/prompts/react_prompt.py
rm app/tools/__init__.py app/tools/schemas.py app/tools/registry.py app/tools/operations.py app/tools/company_schemas.py app/tools/company_registry.py app/tools/company_operations.py
```

- [ ] **Step 2: Remove empty directories**

```bash
rmdir app/services app/tools
```

Note: `app/prompts/` directory stays — it now contains the `.md` files.

- [ ] **Step 3: Clean up `__pycache__` directories**

```bash
find app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete old services/, tools/, and prompts/*.py files"
```

---

## Task 15: Verify the App Starts

- [ ] **Step 1: Check all imports resolve**

```bash
cd D:/wasla-models
python -c "from app.main import app; print('Imports OK')"
```

Expected: `Imports OK` (no `ModuleNotFoundError`)

- [ ] **Step 2: Start the server briefly**

```bash
timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 || true
```

Expected: Server starts, shows "Uvicorn running on http://0.0.0.0:8000" (it will timeout after 5s, that's fine — we just need to see it starts without import errors).

- [ ] **Step 3: Verify endpoints are registered**

```bash
python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/api/chat' in routes, '/api/chat missing'
assert '/api/chat/{company_id}' in routes, '/api/chat/{company_id} missing'
assert '/api/company/chat' in routes, '/api/company/chat missing'
assert '/health' in routes, '/health missing'
print('All 4 endpoints registered OK')
"
```

Expected: `All 4 endpoints registered OK`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verify clean startup — codebase overhaul complete"
```
