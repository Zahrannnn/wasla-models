"""
Prompts package — LLM prompt templates.

This package contains prompt templates for different agent patterns:
- ReAct: Reasoning + Acting pattern with explicit thought traces
"""

from app.prompts.react_prompt import (
    get_react_final_answer_prompt,
    get_react_system_prompt,
    REACT_SYSTEM_TEMPLATE,
)

__all__ = [
    "REACT_SYSTEM_TEMPLATE",
    "get_react_system_prompt",
    "get_react_final_answer_prompt",
]