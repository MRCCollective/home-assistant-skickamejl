"""Incoming webhook support for Skickamejl."""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from aiohttp import web
from homeassistant.components import webhook as ha_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.network import NoURLAvailableError

from .config import config_entry_data
from .const import (
    CONF_CLOUDHOOK_URL,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_EMAIL,
    NAME,
    webhook_event_signal,
)
from .events import SkickamejlWebhookEvent
from .runtime import async_record_send_result

_LOGGER = logging.getLogger(__name__)


def ensure_webhook_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Ensure the config entry has a stable Home Assistant webhook ID."""
    data = dict(entry.data)
    webhook_id = data.get(CONF_WEBHOOK_ID)
    if isinstance(webhook_id, str) and webhook_id:
        return webhook_id

    webhook_id = f"{DOMAIN}_{uuid4().hex}"
    data[CONF_WEBHOOK_ID] = webhook_id
    hass.config_entries.async_update_entry(entry, data=data)
    return webhook_id


def webhook_url_for_config(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Return the webhook URL for display in the admin-only options flow."""
    data = config_entry_data(entry)
    cloudhook_url = data.get(CONF_CLOUDHOOK_URL)
    if isinstance(cloudhook_url, str) and cloudhook_url:
        return cloudhook_url

    webhook_id = data.get(CONF_WEBHOOK_ID)
    if not isinstance(webhook_id, str) or not webhook_id:
        return None

    try:
        return cast(
            str,
            ha_webhook.async_generate_url(
                hass,
                webhook_id,
                allow_internal=True,
                allow_external=True,
                prefer_external=True,
            ),
        )
    except NoURLAvailableError:
        return None


async def async_setup_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the incoming Skickamejl webhook."""
    webhook_id = config_entry_data(entry)[CONF_WEBHOOK_ID]

    async def _handler(
        handler_hass: HomeAssistant,
        _webhook_id: str,
        request: web.Request,
    ) -> web.Response:
        return await _handle_webhook(handler_hass, entry, request)

    ha_webhook.async_register(
        hass,
        DOMAIN,
        f"{NAME} {entry.title}",
        webhook_id,
        _handler,
        local_only=False,
        allowed_methods=("POST",),
    )
    await async_setup_cloudhook(hass, entry)


async def async_unload_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unregister the incoming Skickamejl webhook."""
    webhook_id = config_entry_data(entry).get(CONF_WEBHOOK_ID)
    if webhook_id:
        ha_webhook.async_unregister(hass, webhook_id)


async def async_setup_cloudhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Create a Home Assistant Cloud URL for the webhook when available."""
    cloud = _cloud_component()
    if cloud is None:
        return

    try:
        if not (
            cloud.async_active_subscription(hass) and cloud.async_is_connected(hass)
        ):
            return

        webhook_id = config_entry_data(entry)[CONF_WEBHOOK_ID]
        cloudhook_url = await cloud.async_get_or_create_cloudhook(hass, webhook_id)
    except Exception as err:
        _LOGGER.debug("Could not create Skickamejl cloudhook URL: %s", err)
        return

    if config_entry_data(entry).get(CONF_CLOUDHOOK_URL) == cloudhook_url:
        return

    hass.config_entries.async_update_entry(
        entry,
        data={**dict(entry.data), CONF_CLOUDHOOK_URL: cloudhook_url},
    )


async def async_remove_cloudhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the Home Assistant Cloud URL for the webhook when possible."""
    cloudhook_url = config_entry_data(entry).get(CONF_CLOUDHOOK_URL)
    if not cloudhook_url:
        return

    cloud = _cloud_component()
    if cloud is None:
        return

    with suppress(Exception):
        await cloud.async_delete_cloudhook(
            hass,
            config_entry_data(entry)[CONF_WEBHOOK_ID],
        )


def _cloud_component() -> Any | None:
    """Return Home Assistant Cloud helpers if available."""
    try:
        from homeassistant.components import cloud  # noqa: PLC0415
    except Exception:
        return None

    return cloud


async def _handle_webhook(
    hass: HomeAssistant,
    entry: ConfigEntry,
    request: web.Request,
) -> web.Response:
    """Handle an incoming Skickamejl event webhook."""
    try:
        payload = await request.json()
    except ValueError:
        return web.json_response({"error": "invalid_json"}, status=400)

    if not isinstance(payload, dict):
        return web.json_response({"error": "invalid_payload"}, status=400)

    event = SkickamejlWebhookEvent.from_payload(
        payload,
        received_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    runtime_data = entry.runtime_data
    runtime_data.last_webhook_event = event

    send_result = event.as_send_result()
    if send_result is not None:
        async_record_send_result(hass, entry, send_result)

    event_data: dict[str, Any] = {
        "entry_id": entry.entry_id,
        **event.as_event_data(),
    }
    hass.bus.async_fire(EVENT_EMAIL, event_data)
    async_dispatcher_send(hass, webhook_event_signal(entry.entry_id))

    _LOGGER.debug(
        "Received Skickamejl webhook event %s for template %s and delivery %s",
        event.event,
        event.template_id,
        event.delivery_id,
    )
    return web.json_response({"ok": True})
