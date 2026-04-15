"""LLM provider protocol — structural subtyping, no ABC needed."""

from __future__ import annotations

from typing import Protocol, Type, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class LLMProvider(Protocol):
    """Any class that implements generate() can be used as an LLM provider."""

    async def generate(
        self,
        prompt: str,
        response_model: Type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> T:
        """Send prompt to LLM, parse response into response_model."""
        ...
