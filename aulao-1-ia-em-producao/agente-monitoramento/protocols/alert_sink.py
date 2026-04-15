"""Alert sink protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from schemas.alerts import Alert


@runtime_checkable
class AlertSink(Protocol):
    """Any class that can send alerts."""

    async def send(self, alert: Alert) -> bool: ...
