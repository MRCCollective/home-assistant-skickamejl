"""Tests for incoming Skickamejl webhooks."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

from custom_components.skickamejl.const import (
    EVENT_EMAIL,
    webhook_event_signal,
)
from custom_components.skickamejl.events import SkickamejlWebhookEvent
from custom_components.skickamejl.webhook import _handle_webhook, ensure_webhook_id


class FakeBus:
    """Collect fired Home Assistant events."""

    def __init__(self) -> None:
        """Initialize the fake bus."""
        self.events: list[tuple[str, dict[str, Any]]] = []

    def async_fire(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Store a fired event."""
        self.events.append((event_type, event_data))


class FakeConfigEntries:
    """Collect config entry updates."""

    def __init__(self) -> None:
        """Initialize the fake config entry manager."""
        self.updated_data: dict[str, Any] | None = None

    def async_update_entry(self, _entry: Any, *, data: dict[str, Any]) -> None:
        """Store updated config entry data."""
        self.updated_data = data


class FakeRequest:
    """Fake aiohttp request with a JSON body."""

    def __init__(self, payload: Any) -> None:
        """Initialize the fake request."""
        self._payload = payload

    async def json(self) -> Any:
        """Return the fake payload."""
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


def test_webhook_event_normalizes_template_and_delivery_fields() -> None:
    """Webhook payloads should expose stable snake_case automation fields."""
    event = SkickamejlWebhookEvent.from_payload(
        {
            "eventType": "email.sent",
            "templateId": "account-created",
            "deliveryId": "delivery-1",
            "emailMessageId": "email-1",
            "messageId": "message-1",
            "to": "new.user@example.com",
            "from": "noreply@example.com",
        },
        received_at_utc="2026-08-03T13:00:00Z",
    )

    assert event.event == "email.sent"
    assert event.template_id == "account-created"
    assert event.delivery_id == "delivery-1"
    assert event.status == "queued"
    assert event.as_event_data()["template_id"] == "account-created"
    assert event.as_send_result().delivery_id == "delivery-1"  # type: ignore[union-attr]


async def test_handle_webhook_stores_event_updates_delivery_and_fires_ha_event(
    monkeypatch: Any,
) -> None:
    """Incoming webhooks update runtime state and fire an automation event."""
    dispatched: list[str] = []
    recorded: list[Any] = []
    hass = SimpleNamespace(bus=FakeBus())
    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(last_webhook_event=None, last_send=None),
    )

    monkeypatch.setattr(
        "custom_components.skickamejl.webhook.async_dispatcher_send",
        lambda _hass, signal: dispatched.append(signal),
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.webhook.async_record_send_result",
        lambda _hass, _entry, result: recorded.append(result),
    )

    response = await _handle_webhook(
        hass,
        entry,
        FakeRequest(
            {
                "event": "email.delivered",
                "template_id": "account-created",
                "delivery_id": "delivery-1",
                "status": "delivered",
            }
        ),
    )

    assert response.status == HTTPStatus.OK
    assert entry.runtime_data.last_webhook_event.template_id == "account-created"
    assert recorded[0].delivery_id == "delivery-1"
    assert recorded[0].status == "delivered"
    assert hass.bus.events[0][0] == EVENT_EMAIL
    assert hass.bus.events[0][1]["template_id"] == "account-created"
    assert dispatched == [webhook_event_signal("entry-1")]


async def test_handle_webhook_rejects_non_object_payload() -> None:
    """Only JSON objects are accepted as Skickamejl webhook payloads."""
    response = await _handle_webhook(
        SimpleNamespace(bus=FakeBus()),
        SimpleNamespace(entry_id="entry-1", runtime_data=SimpleNamespace()),
        FakeRequest(["not", "an", "object"]),
    )

    assert response.status == HTTPStatus.BAD_REQUEST


def test_ensure_webhook_id_persists_stable_random_id() -> None:
    """Config entries should get a stable generated webhook ID."""
    config_entries = FakeConfigEntries()
    hass = SimpleNamespace(config_entries=config_entries)
    entry = SimpleNamespace(data={"api_key": "secret"})

    webhook_id = ensure_webhook_id(hass, entry)

    assert webhook_id.startswith("skickamejl_")
    assert config_entries.updated_data["webhook_id"] == webhook_id


def test_ensure_webhook_id_reuses_existing_id() -> None:
    """Existing webhook IDs should not be regenerated."""
    config_entries = FakeConfigEntries()
    hass = SimpleNamespace(config_entries=config_entries)
    entry = SimpleNamespace(data={"webhook_id": "skickamejl_existing"})

    assert ensure_webhook_id(hass, entry) == "skickamejl_existing"
    assert config_entries.updated_data is None
