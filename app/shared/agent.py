"""
Agent Graph — LangGraph StateGraph builder for Wasla agents.

Builds a two-node graph:
  agent (LLM) ──► tools (ToolNode) ──► agent ──► END

The system prompt is prepended inside agent_node (NOT saved to checkpointed
state) to avoid duplication across turns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from app.shared.langgraph_tool_node import ToolNode

from app.core.config import get_settings
from app.shared.state import AgentState
from app.utils.context_manager import trim_messages

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

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
        settings = get_settings()
        input_budget = settings.max_context_tokens - settings.max_chat_tokens
        messages_for_llm = trim_messages(messages_for_llm, max_input_tokens=input_budget)

        # 4. Invoke LLM
        response = await llm.ainvoke(messages_for_llm)

        logger.info(
            "Agent response: tool_calls=%d content_len=%d",
            len(response.tool_calls) if hasattr(response, "tool_calls") and response.tool_calls else 0,
            len(response.content) if response.content else 0,
        )

        # 5. Return only the AI response to update persistent state
        model_name = ""
        if hasattr(response, "response_metadata") and response.response_metadata:
            model_name = response.response_metadata.get("model_name", "") or ""

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
