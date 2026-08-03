"""Diagnostics support for Skickamejl."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .config import config_entry_data
from .const import (
    CONF_API_KEY,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    DOMAIN,
)

_TO_REDACT = {
    CONF_API_KEY,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "data": async_redact_data(config_entry_data(entry), _TO_REDACT),
            "options": async_redact_data(dict(entry.options), _TO_REDACT),
        },
        "loaded": entry.entry_id in hass.data.get(DOMAIN, {}),
        "health": _health_summary(entry),
        "last_send": _last_send_summary(entry),
    }


def _health_summary(entry: ConfigEntry) -> dict[str, bool | None]:
    """Return health diagnostics for a config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime_data, "coordinator", None)
    return {
        "backend_available": getattr(coordinator, "data", None),
        "last_update_success": getattr(coordinator, "last_update_success", None),
    }


def _last_send_summary(entry: ConfigEntry) -> dict[str, Any] | None:
    """Return last-send diagnostics for a config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    result = getattr(runtime_data, "last_send", None)
    if result is None:
        return None
    return {
        "email_message_id": result.email_message_id,
        "delivery_id": result.delivery_id,
        "message_id": result.message_id,
        "envelope_from": result.envelope_from,
        "status": result.status,
        "queued_at_utc": result.queued_at_utc,
        "attempt_count": result.attempt_count,
        "created_at_utc": result.created_at_utc,
        "last_attempt_at_utc": result.last_attempt_at_utc,
        "next_attempt_at_utc": result.next_attempt_at_utc,
        "completed_at_utc": result.completed_at_utc,
        "last_error": result.last_error,
        "attempts": list(result.attempts),
        "status_events": list(result.status_events),
    }
