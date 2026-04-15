"""Event store protocol for persistence (BigQuery or in-memory)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from schemas.events import EnrichedEvent, RawEvent
    from schemas.observability import LLMCallRecord


@runtime_checkable
class EventStore(Protocol):
    """Any class that can read raw events and write enriched events."""

    async def fetch_unprocessed(self, limit: int = 10) -> list[RawEvent]: ...

    async def mark_processed(self, event_ids: list[str]) -> None: ...

    async def save_enriched(self, events: list[EnrichedEvent]) -> None: ...

    async def save_llm_calls(self, records: list[LLMCallRecord]) -> None: ...
