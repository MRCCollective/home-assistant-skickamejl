"""Tests for Skickamejl services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.exceptions import ServiceValidationError

from custom_components.skickamejl import async_remove_entry
from custom_components.skickamejl.api import SkickamejlEmailSendResult
from custom_components.skickamejl.const import (
    ATTR_FROM,
    ATTR_HTML_BODY,
    ATTR_SUBJECT,
    ATTR_TEXT_BODY,
    ATTR_TO,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    DOMAIN,
    SERVICE_SEND_EMAIL,
    send_result_signal,
)
from custom_components.skickamejl.services import (
    _entry_id_from_call,
    _field_or_default,
    _looks_like_email,
    _optional_text,
    _required_text,
    async_setup_services,
)


class FakeApi:
    """Fake API that records email sends."""

    def __init__(self) -> None:
        """Initialize the fake API."""
        self.calls: list[dict[str, Any]] = []

    async def async_send_email(self, **kwargs: Any) -> SkickamejlEmailSendResult:
        """Record the send call and return a fake result."""
        self.calls.append(kwargs)
        return SkickamejlEmailSendResult(
            email_message_id="email-1",
            delivery_id="delivery-1",
            message_id="message-1",
            envelope_from="bounce@example.com",
            status=0,
            queued_at_utc="2026-08-03T10:00:00Z",
        )


class FakeServices:
    """Fake Home Assistant service registry."""

    def __init__(self) -> None:
        """Initialize the fake service registry."""
        self.registered: dict[tuple[str, str], Any] = {}

    def has_service(self, domain: str, service: str) -> bool:
        """Return whether a service has been registered."""
        return (domain, service) in self.registered

    def async_register(
        self,
        domain: str,
        service: str,
        handler: Any,
        *,
        schema: Any,
    ) -> None:
        """Register a fake service."""
        self.registered[(domain, service)] = (handler, schema)

    def async_remove(self, domain: str, service: str) -> None:
        """Remove a fake service."""
        self.registered.pop((domain, service), None)


class FakeConfigEntries:
    """Fake config entry manager."""

    def __init__(self, entries: list[Any]) -> None:
        """Initialize the manager."""
        self._entries = entries

    def async_entries(self, domain: str) -> list[Any]:
        """Return entries for the requested domain."""
        return self._entries if domain == DOMAIN else []


def test_service_text_helpers_trim_and_validate_values() -> None:
    """Service helper functions trim optional/default/required text fields."""
    call = SimpleNamespace(
        data={
            ATTR_TO: " user@example.com ",
            ATTR_SUBJECT: " Subject ",
            ATTR_TEXT_BODY: " Body ",
            ATTR_HTML_BODY: "   ",
        }
    )

    assert _field_or_default(call, ATTR_TO, "default@example.com") == "user@example.com"
    assert (
        _field_or_default(call, ATTR_FROM, " home@example.com ") == "home@example.com"
    )
    assert _required_text(call, ATTR_SUBJECT) == "Subject"
    assert _optional_text(call, ATTR_TEXT_BODY) == "Body"
    assert _optional_text(call, ATTR_HTML_BODY) is None


def test_required_text_rejects_empty_values() -> None:
    """Required text fields must not be blank."""
    call = SimpleNamespace(data={ATTR_SUBJECT: " "})

    with pytest.raises(ServiceValidationError):
        _required_text(call, ATTR_SUBJECT)


def test_email_validation_accepts_basic_email_shape() -> None:
    """Service email validation accepts a basic address shape."""
    assert _looks_like_email("user@example.com") is True
    assert _looks_like_email("missing-at.example.com") is False
    assert _looks_like_email("missing-domain@example") is False


async def test_send_email_service_uses_defaults_and_updates_last_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The send_email service uses configured defaults and stores send metadata."""
    api = FakeApi()
    runtime_data = SimpleNamespace(api=api, last_send=None)
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            CONF_RECIPIENT_ADDRESS: "default-to@example.com",
            CONF_SENDER_ADDRESS: "default-from@example.com",
        },
        options={},
        runtime_data=runtime_data,
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"entry-1": runtime_data}},
        services=FakeServices(),
        config_entries=FakeConfigEntries([entry]),
    )
    sent_signals: list[str] = []

    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_dispatcher_send",
        lambda _hass, signal: sent_signals.append(signal),
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_start_delivery_polling",
        lambda _hass, _entry: None,
    )

    await async_setup_services(hass)
    handler, schema = hass.services.registered[(DOMAIN, SERVICE_SEND_EMAIL)]
    call = SimpleNamespace(
        data={
            ATTR_CONFIG_ENTRY_ID: "entry-1",
            ATTR_SUBJECT: "Subject",
            ATTR_TEXT_BODY: "Text",
        }
    )

    schema(call.data)
    await handler(call)

    assert api.calls == [
        {
            "recipient_address": "default-to@example.com",
            "sender_address": "default-from@example.com",
            "subject": "Subject",
            "text_body": "Text",
            "html_body": None,
        }
    ]
    assert runtime_data.last_send.delivery_id == "delivery-1"
    assert sent_signals == [send_result_signal("entry-1")]


async def test_send_email_service_requires_body() -> None:
    """The send_email service rejects calls without text or HTML content."""
    api = FakeApi()
    runtime_data = SimpleNamespace(api=api, last_send=None)
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            CONF_RECIPIENT_ADDRESS: "default-to@example.com",
            CONF_SENDER_ADDRESS: "default-from@example.com",
        },
        options={},
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"entry-1": runtime_data}},
        services=FakeServices(),
        config_entries=FakeConfigEntries([entry]),
    )

    await async_setup_services(hass)
    handler, _schema = hass.services.registered[(DOMAIN, SERVICE_SEND_EMAIL)]

    with pytest.raises(ServiceValidationError):
        await handler(
            SimpleNamespace(
                data={
                    ATTR_CONFIG_ENTRY_ID: "entry-1",
                    ATTR_SUBJECT: "Subject",
                }
            )
        )


async def test_send_email_service_survives_removing_and_readding_last_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing the final entry must not unregister the send action."""
    old_entry = SimpleNamespace(entry_id="entry-1")
    entries = FakeConfigEntries([old_entry])
    hass = SimpleNamespace(
        data={DOMAIN: {}},
        services=FakeServices(),
        config_entries=entries,
    )

    async def remove_cloudhook(_hass: Any, _entry: Any) -> None:
        """Stand in for remote cloudhook cleanup."""

    monkeypatch.setattr(
        "custom_components.skickamejl.async_remove_cloudhook", remove_cloudhook
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_dispatcher_send",
        lambda _hass, _signal: None,
    )
    monkeypatch.setattr(
        "custom_components.skickamejl.runtime.async_start_delivery_polling",
        lambda _hass, _entry: None,
    )

    await async_setup_services(hass)
    handler, _schema = hass.services.registered[(DOMAIN, SERVICE_SEND_EMAIL)]
    entries._entries.clear()
    await async_remove_entry(hass, old_entry)

    assert hass.services.has_service(DOMAIN, SERVICE_SEND_EMAIL)
    with pytest.raises(ServiceValidationError, match="Unknown or unloaded"):
        await handler(SimpleNamespace(data={ATTR_CONFIG_ENTRY_ID: "entry-1"}))

    api = FakeApi()
    runtime_data = SimpleNamespace(api=api, last_send=None)
    entry = SimpleNamespace(
        entry_id="entry-2",
        data={
            CONF_RECIPIENT_ADDRESS: "recipient@example.com",
            CONF_SENDER_ADDRESS: "sender@example.com",
        },
        options={},
        runtime_data=runtime_data,
    )
    entries._entries.append(entry)
    hass.data[DOMAIN][entry.entry_id] = runtime_data

    await handler(
        SimpleNamespace(
            data={
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
                ATTR_SUBJECT: "After re-adding",
                ATTR_TEXT_BODY: "Hello",
            }
        )
    )

    assert len(api.calls) == 1
    assert api.calls[0]["recipient_address"] == "recipient@example.com"


def test_entry_id_from_call_requires_config_entry_id() -> None:
    """Service calls require an explicit config entry selection."""
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": object()}})
    call = SimpleNamespace(data={ATTR_CONFIG_ENTRY_ID: ""})

    with pytest.raises(ServiceValidationError):
        _entry_id_from_call(hass, call)


def test_entry_id_from_call_accepts_explicit_config_entry_id() -> None:
    """Explicit entry IDs are passed through."""
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": object(), "entry-2": object()}})
    call = SimpleNamespace(data={ATTR_CONFIG_ENTRY_ID: "entry-2"})

    assert _entry_id_from_call(hass, call) == "entry-2"
