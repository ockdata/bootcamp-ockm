"""Prompt registry — loads versioned prompt templates from files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(name: str, version: str = "v1") -> str:
    """Load a prompt template by name and version.

    Args:
        name: Prompt name without extension (e.g., "classify", "extract", "root_cause")
        version: Prompt version directory (e.g., "v1")

    Returns:
        The prompt template string with {placeholders} for formatting.
    """
    path = _PROMPTS_DIR / version / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def format_prompt(name: str, version: str = "v1", **kwargs: str) -> str:
    """Load and format a prompt template with the given variables."""
    template = load_prompt(name, version)
    return template.format(**kwargs)


def available_prompts(version: str = "v1") -> list[str]:
    """List all available prompt names for a given version."""
    path = _PROMPTS_DIR / version
    if not path.exists():
        return []
    return sorted(p.stem for p in path.glob("*.txt"))
