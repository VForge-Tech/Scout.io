import pytest

from app.domain.event_bus import EventBus, DomainEvent


@pytest.fixture
def bus():
    return EventBus()


@pytest.mark.asyncio
async def test_publish_and_subscribe(bus):
    received = []

    async def handler(event: DomainEvent):
        received.append(event.payload)

    bus.subscribe("test.event", handler)
    await bus.publish(DomainEvent(event_type="test.event", payload={"key": "val"}))

    assert len(received) == 1
    assert received[0] == {"key": "val"}


def test_publish_sync(bus):
    received = []

    def handler(event: DomainEvent):
        received.append(event.payload)

    bus.subscribe("test.sync", handler)
    bus.publish_sync(DomainEvent(event_type="test.sync", payload={"n": 42}))

    assert len(received) == 1
    assert received[0] == {"n": 42}


def test_unsubscribe(bus):
    received = []

    def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("test.unsub", handler)
    bus.unsubscribe("test.unsub", handler)
    bus.publish_sync(DomainEvent(event_type="test.unsub"))

    assert len(received) == 0


def test_no_handlers_no_error(bus):
    bus.publish_sync(DomainEvent(event_type="nonexistent"))


def test_handler_exception_does_not_crash(bus):
    def failing_handler(event: DomainEvent):
        raise ValueError("oops")

    def good_handler(event: DomainEvent):
        pass

    bus.subscribe("test.crash", failing_handler)
    bus.subscribe("test.crash", good_handler)
    bus.publish_sync(DomainEvent(event_type="test.crash"))


def test_clear(bus):
    bus.subscribe("test", lambda e: None)
    bus.clear()
    assert bus._handlers == {}
