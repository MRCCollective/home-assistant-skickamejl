"""Runtime helpers for Skickamejl."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import (
    SkickamejlConnectionError,
    SkickamejlEmailSendResult,
    SkickamejlError,
    SkickamejlNotFoundError,
)
from .const import DEFAULT_SCAN_INTERVAL, send_result_signal
from .sensor import is_terminal_delivery_status

_LOGGER = logging.getLogger(__name__)


def async_record_send_result(
    hass: HomeAssistant,
    entry: ConfigEntry,
    result: SkickamejlEmailSendResult,
) -> None:
    """Store a send result, notify entities, and start follow-up polling."""
    runtime_data = entry.runtime_data
    runtime_data.last_send = result
    async_dispatcher_send(hass, send_result_signal(entry.entry_id))
    async_start_delivery_polling(hass, entry)


def async_start_delivery_polling(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Start delivery-detail polling for the latest non-terminal send."""
    runtime_data = entry.runtime_data
    delivery_id = getattr(runtime_data.last_send, "delivery_id", None)
    if not delivery_id or is_terminal_delivery_status(runtime_data.last_send.status):
        return

    existing_task = getattr(runtime_data, "delivery_poll_task", None)
    if existing_task is not None and not existing_task.done():
        existing_task.cancel()

    runtime_data.delivery_poll_task = hass.async_create_task(
        _async_poll_delivery(entry, delivery_id),
        name=f"skickamejl_delivery_poll_{entry.entry_id}",
    )


async def async_stop_delivery_polling(entry: ConfigEntry) -> None:
    """Stop delivery-detail polling for a config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is None:
        return
    task: asyncio.Task[None] | None = getattr(runtime_data, "delivery_poll_task", None)
    if task is None:
        return

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    runtime_data.delivery_poll_task = None


async def _async_poll_delivery(entry: ConfigEntry, delivery_id: str) -> None:
    """Poll delivery details until the backend reports a terminal status."""
    runtime_data = entry.runtime_data

    while True:
        await asyncio.sleep(DEFAULT_SCAN_INTERVAL.total_seconds())

        current_delivery_id = getattr(runtime_data.last_send, "delivery_id", None)
        if current_delivery_id != delivery_id:
            return

        try:
            detail = await runtime_data.api.async_get_email_detail(delivery_id)
        except SkickamejlNotFoundError:
            _LOGGER.debug("Skickamejl delivery %s was not found", delivery_id)
            return
        except SkickamejlConnectionError as err:
            _LOGGER.debug("Skickamejl delivery poll failed: %s", err)
            continue
        except SkickamejlError as err:
            _LOGGER.warning("Skickamejl delivery poll failed: %s", err)
            continue

        runtime_data.last_send = detail
        hass = _runtime_hass(runtime_data)
        if hass is not None:
            async_dispatcher_send(hass, send_result_signal(entry.entry_id))

        if is_terminal_delivery_status(detail.status):
            return


def _runtime_hass(runtime_data: Any) -> HomeAssistant | None:
    """Return Home Assistant from runtime data when available."""
    return getattr(runtime_data, "hass", None)
