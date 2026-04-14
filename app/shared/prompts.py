"""Load prompt templates from the prompts/ directory."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """
    Load a prompt file by name from app/prompts/.

    Not cached so edits are visible under ``uvicorn --reload`` without a process restart.
    """
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")
