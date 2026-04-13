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
