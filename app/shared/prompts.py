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
