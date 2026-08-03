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
)
from custom_components.skickamejl.sensor import (
    SENSORS,
    SkickamejlLastSendSensor,
    _delivery_status,
    _parse_timestamp,
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
    assert _delivery_status(99) == "99"
    assert _delivery_status(None) is None


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


def test_diagnostics_helpers_summarize_health_and_last_send() -> None:
    """Diagnostics expose health and last-send metadata without secrets."""
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data=True, last_update_success=True),
            last_send=_send_result(),
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
    }
