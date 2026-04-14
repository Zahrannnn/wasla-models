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
      ``{"tool_calls_made": N}`` from a node increments the **session** total
      persisted by the checkpointer. API responses expose the **per-request**
      delta (computed in routes), not this cumulative value alone.
    - HTTP clients are NOT stored here (non-serializable). They are passed
      via ``RunnableConfig["configurable"]["client"]`` at invocation time.
    """

    bearer_token: str | None = None
    tool_calls_made: Annotated[int, operator.add] = 0
    model_used: str = ""
