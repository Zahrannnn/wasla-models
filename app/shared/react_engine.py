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
from app.shared.prompts import load_prompt
from app.shared.react_parser import parse_react_response
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
