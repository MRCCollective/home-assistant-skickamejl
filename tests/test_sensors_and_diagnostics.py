"""Tests for Skickamejl sensors, health, and diagnostics helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.skickamejl.api import (
    SkickamejlConnectionError,
    SkickamejlEmailSendResult,
)
from custom_components.skickamejl.coordinator import SkickamejlHealthCoordinator
from custom_components.skickamejl.diagnostics import (
    _health_summary,
    _last_send_summary,
    _last_webhook_event_summary,
)
from custom_components.skickamejl.events import SkickamejlWebhookEvent
from custom_components.skickamejl.sensor import (
    SENSORS,
    WEBHOOK_EVENT_SENSORS,
    SkickamejlLastSendSensor,
    SkickamejlWebhookEventSensor,
    _delivery_status,
    _parse_timestamp,
    is_terminal_delivery_status,
)


class HealthyApi:
    """Fake healthy API."""

    async def async_check_health(self) -> bool:
        """Return healthy."""
        return True


class FailingApi:
    """Fake unhealthy API."""

    async def async_check_health(self) -> bool:
        """Raise a Skickamejl connection error."""
        raise SkickamejlConnectionError("offline")


def _send_result() -> SkickamejlEmailSendResult:
    """Return a representative send result."""
    return SkickamejlEmailSendResult(
        email_message_id="email-1",
        delivery_id="delivery-1",
        message_id="message-1",
        envelope_from="bounce@example.com",
        status=2,
        queued_at_utc="2026-08-03T10:00:00Z",
    )


def _webhook_event() -> SkickamejlWebhookEvent:
    """Return a representative webhook event."""
    return SkickamejlWebhookEvent.from_payload(
        {
            "event": "email.sent",
            "templateId": "account-created",
            "deliveryId": "delivery-1",
            "to": "new.user@example.com",
            "from": "noreply@example.com",
        },
        received_at_utc="2026-08-03T13:00:00Z",
    )


async def test_health_coordinator_returns_true_when_backend_is_available() -> None:
    """The health coordinator reports a reachable backend as available."""
    coordinator = SkickamejlHealthCoordinator.__new__(SkickamejlHealthCoordinator)
    coordinator.api = HealthyApi()

    assert await coordinator._async_update_data() is True


async def test_health_coordinator_returns_false_when_backend_fails() -> None:
    """The health coordinator reports backend failures as unavailable."""
    coordinator = SkickamejlHealthCoordinator.__new__(SkickamejlHealthCoordinator)
    coordinator.api = FailingApi()

    assert await coordinator._async_update_data() is False


def test_delivery_status_mapping() -> None:
    """Numeric delivery statuses become readable sensor states."""
    assert _delivery_status(0) == "queued"
    assert _delivery_status(1) == "processing"
    assert _delivery_status(2) == "delivered"
    assert _delivery_status(3) == "deferred"
    assert _delivery_status(4) == "bounced"
    assert _delivery_status(5) == "failed"
    assert _delivery_status("2") == "delivered"
    assert _delivery_status("Delivered") == "delivered"
    assert _delivery_status(99) == "99"
    assert _delivery_status(None) is None


def test_terminal_delivery_status_mapping() -> None:
    """Only final delivery statuses stop follow-up polling."""
    assert is_terminal_delivery_status(2) is True
    assert is_terminal_delivery_status("Delivered") is True
    assert is_terminal_delivery_status("bounced") is True
    assert is_terminal_delivery_status("failed") is True
    assert is_terminal_delivery_status(0) is False
    assert is_terminal_delivery_status("processing") is False
    assert is_terminal_delivery_status(None) is False


def test_parse_timestamp_handles_zulu_and_invalid_values() -> None:
    """Timestamp sensors parse valid backend timestamps and ignore invalid ones."""
    assert _parse_timestamp("2026-08-03T10:00:00Z") == datetime(
        2026,
        8,
        3,
        10,
        0,
        tzinfo=UTC,
    )
    assert _parse_timestamp("not-a-date") is None
    assert _parse_timestamp(None) is None


def test_last_send_sensor_values_and_attributes() -> None:
    """Last-send sensors read values and attributes from runtime data."""
    entry = SimpleNamespace(entry_id="entry-1", runtime_data=SimpleNamespace())
    entry.runtime_data.last_send = _send_result()

    status_description = next(
        description
        for description in SENSORS
        if description.key == "last_delivery_status"
    )
    queued_at_description = next(
        description for description in SENSORS if description.key == "last_queued_at"
    )

    status_sensor = SkickamejlLastSendSensor(entry, status_description)
    queued_at_sensor = SkickamejlLastSendSensor(entry, queued_at_description)

    assert status_sensor.native_value == "delivered"
    assert queued_at_sensor.native_value == datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
    assert status_sensor.extra_state_attributes == {
        "email_message_id": "email-1",
        "delivery_id": "delivery-1",
        "message_id": "message-1",
        "envelope_from": "bounce@example.com",
        "status": 2,
        "status_name": "delivered",
        "queued_at_utc": "2026-08-03T10:00:00Z",
        "attempt_count": None,
        "created_at_utc": None,
        "last_attempt_at_utc": None,
        "next_attempt_at_utc": None,
        "completed_at_utc": None,
        "last_error": None,
        "attempts": [],
        "status_events": [],
    }


def test_last_send_sensor_is_empty_before_first_send() -> None:
    """Last-send sensors are empty before Home Assistant sends an email."""
    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(last_send=None),
    )
    sensor = SkickamejlLastSendSensor(entry, SENSORS[0])

    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None


def test_webhook_event_sensor_values_and_attributes() -> None:
    """Webhook event sensors read values and attributes from runtime data."""
    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(last_webhook_event=_webhook_event()),
    )
    template_description = next(
        description
        for description in WEBHOOK_EVENT_SENSORS
        if description.key == "last_template_id"
    )
    received_description = next(
        description
        for description in WEBHOOK_EVENT_SENSORS
        if description.key == "last_webhook_received_at"
    )

    template_sensor = SkickamejlWebhookEventSensor(entry, template_description)
    received_sensor = SkickamejlWebhookEventSensor(entry, received_description)

    assert template_sensor.native_value == "account-created"
    assert received_sensor.native_value == datetime(2026, 8, 3, 13, 0, tzinfo=UTC)
    assert template_sensor.extra_state_attributes["event"] == "email.sent"
    assert template_sensor.extra_state_attributes["template_id"] == "account-created"


def test_diagnostics_helpers_summarize_health_and_last_send() -> None:
    """Diagnostics expose health and last-send metadata without secrets."""
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data=True, last_update_success=True),
            last_send=_send_result(),
            last_webhook_event=_webhook_event(),
        )
    )

    assert _health_summary(entry) == {
        "backend_available": True,
        "last_update_success": True,
    }
    assert _last_send_summary(entry) == {
        "email_message_id": "email-1",
        "delivery_id": "delivery-1",
        "message_id": "message-1",
        "envelope_from": "bounce@example.com",
        "status": 2,
        "queued_at_utc": "2026-08-03T10:00:00Z",
        "attempt_count": None,
        "created_at_utc": None,
        "last_attempt_at_utc": None,
        "next_attempt_at_utc": None,
        "completed_at_utc": None,
        "last_error": None,
        "attempts": [],
        "status_events": [],
    }
    assert _last_webhook_event_summary(entry) == {
        "event": "email.sent",
        "template_id": "account-created",
        "delivery_id": "delivery-1",
        "recipient_address": "**REDACTED**",
        "sender_address": "**REDACTED**",
        "status": "queued",
        "received_at_utc": "2026-08-03T13:00:00Z",
        "payload": {
            "event": "email.sent",
            "templateId": "account-created",
            "deliveryId": "delivery-1",
            "to": "**REDACTED**",
            "from": "**REDACTED**",
        },
    }
