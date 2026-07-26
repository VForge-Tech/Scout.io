from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

EventHandler = Callable[["DomainEvent"], Coroutine[Any, Any, None] | None]


@dataclass
class DomainEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribed handler for event_type=%s", event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: DomainEvent):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if result:
                    await result
            except Exception:
                logger.exception("Handler failed for event %s", event.event_type)

    def publish_sync(self, event: DomainEvent):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Handler failed for event %s", event.event_type)

    def clear(self):
        self._handlers.clear()
