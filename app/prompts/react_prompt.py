"""
ReAct System Prompt — teaches the LLM to reason before acting.

This module provides the system prompt for the ReAct (Reasoning + Acting) pattern,
where the agent explicitly thinks through problems before taking actions.
"""

from __future__ import annotations

from app.tools.schemas import tools_to_react_description


REACT_SYSTEM_TEMPLATE = """You are a helpful AI assistant for company '{company_id}'. You have access to the following tools:

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

Remember: Think step by step, use tools when needed, and provide a clear Final Answer when done."""


def get_react_system_prompt(company_id: str) -> str:
    """
    Generate the ReAct system prompt for a specific company.

    Parameters
    ----------
    company_id : str
        The company identifier for tenant isolation.

    Returns
    -------
    str
        The complete system prompt with tool descriptions.
    """
    tools_description = tools_to_react_description()
    return REACT_SYSTEM_TEMPLATE.format(
        company_id=company_id,
        tools_description=tools_description,
    )


def get_react_final_answer_prompt() -> str:
    """
    Prompt to force a final answer when iteration limit is reached.

    Returns
    -------
    str
        Prompt asking the LLM to provide a final answer.
    """
    return """You have reached the maximum number of action steps. Please provide your Final Answer now based on all the information you have gathered.

Format:
Thought: I need to provide my final answer now.
Final Answer: [Your complete answer to the user's question.]"""