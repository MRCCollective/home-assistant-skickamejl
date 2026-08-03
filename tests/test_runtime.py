"""Tests for Skickamejl runtime delivery polling."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from custom_components.skickamejl.api import SkickamejlEmailSendResult
from custom_components.skickamejl.const import send_result_signal
from custom_components.skickamejl.runtime import (
    _async_poll_delivery,
    async_record_send_result,
    async_start_delivery_polling,
)


class DetailApi:
    """Fake API returning a terminal delivery detail."""

    async def async_get_email_detail(
        self,
        delivery_id: str,
    ) -> SkickamejlEmailSendResult:
        """Return delivered detail for the requested delivery."""
        return SkickamejlEmailSendResult(
            email_message_id="email-1",
            delivery_id=delivery_id,
            message_id="message-1",
            envelope_from="bounce@example.com",
            status="Delivered",
            queued_at_utc="2026-08-03T10:00:00Z",
            attempt_count=1,
            completed_at_utc="2026-08-03T10:01:00Z",
            status_events=(
                {
                    "status": "Delivered",
                    "occurredAtUtc": "2026-08-03T10:01:00Z",
                },
            ),
        )


def test_record_send_result_stores_result_dispatches_and_starts_polling(
    monkeypatch: Any,
) -> None:
    """Recording a send result updates runtime state and starts follow-up polling."""
    dispatched: list[tuple[Any, str]] = []
    started: list[tuple[Any, Any]] = []
    entry = SimpleNamespace(entry_id="entry-1", runtime_data=SimpleNamespace())
    hass = object()
    result = SkickamejlEmailSendResult(
        email_message_id="email-1",
        delivery_id="delivery-1",
        message_id="message-1",
        envelope_from="bounce@example.com",
        status=0,
        queued_at_utc="2026-08-03T10:00:00Z",
    )

    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_dispatcher_send",
        lambda hass_arg, signal: dispatched.append((hass_arg, signal)),
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_start_delivery_polling",
        lambda hass_arg, entry_arg: started.append((hass_arg, entry_arg)),
    )

    async_record_send_result(hass, entry, result)

    assert entry.runtime_data.last_send is result
    assert dispatched == [(hass, send_result_signal("entry-1"))]
    assert started == [(hass, entry)]


def test_start_delivery_polling_ignores_terminal_status() -> None:
    """Already-final deliveries should not create a polling task."""
    hass = SimpleNamespace(async_create_task=lambda *_args, **_kwargs: None)
    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(
            last_send=SkickamejlEmailSendResult(
                email_message_id="email-1",
                delivery_id="delivery-1",
                message_id="message-1",
                envelope_from="bounce@example.com",
                status="delivered",
                queued_at_utc="2026-08-03T10:00:00Z",
            ),
            delivery_poll_task=None,
        ),
    )

    async_start_delivery_polling(hass, entry)

    assert entry.runtime_data.delivery_poll_task is None


async def test_poll_delivery_updates_last_send_and_dispatches(monkeypatch: Any) -> None:
    """Polling replaces the initial queued result with detailed delivery status."""
    dispatched: list[tuple[Any, str]] = []
    hass = object()
    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(
            hass=hass,
            api=DetailApi(),
            last_send=SkickamejlEmailSendResult(
                email_message_id="email-1",
                delivery_id="delivery-1",
                message_id="message-1",
                envelope_from="bounce@example.com",
                status=0,
                queued_at_utc="2026-08-03T10:00:00Z",
            ),
        ),
    )

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.asyncio.sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_dispatcher_send",
        lambda hass_arg, signal: dispatched.append((hass_arg, signal)),
    )

    await _async_poll_delivery(entry, "delivery-1")

    assert entry.runtime_data.last_send.status == "Delivered"
    assert entry.runtime_data.last_send.attempt_count == 1
    assert entry.runtime_data.last_send.status_events == (
        {
            "status": "Delivered",
            "occurredAtUtc": "2026-08-03T10:01:00Z",
        },
    )
    assert dispatched == [(hass, send_result_signal("entry-1"))]
