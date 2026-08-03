"""The Skickamejl Home Assistant integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SkickamejlApiClient,
    SkickamejlConnectionError,
    SkickamejlEmailSendResult,
    SkickamejlError,
)
from .const import (
    CONF_API_KEY,
    CONF_SERVER_URL,
    CURRENT_ENTRY_VERSION,
    DOMAIN,
    MIN_SUPPORTED_ENTRY_VERSION,
    PLATFORMS,
)
from .coordinator import SkickamejlHealthCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class SkickamejlRuntimeData:
    """Runtime data stored on the config entry."""

    api: SkickamejlApiClient
    coordinator: SkickamejlHealthCoordinator
    last_send: SkickamejlEmailSendResult | None = None


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up Skickamejl."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Skickamejl from a config entry."""
    api = SkickamejlApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_SERVER_URL],
        entry.data[CONF_API_KEY],
    )

    try:
        await api.async_validate_connection()
    except SkickamejlConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err
    except SkickamejlError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = SkickamejlHealthCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SkickamejlRuntimeData(api=api, coordinator=coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a Skickamejl config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return bool(unload_ok)


async def async_remove_entry(hass: HomeAssistant, _entry: ConfigEntry) -> None:
    """Handle removal of a Skickamejl config entry."""
    if not hass.config_entries.async_entries(DOMAIN):
        await async_unload_services(hass)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate old config entries."""
    if entry.version < MIN_SUPPORTED_ENTRY_VERSION:
        _LOGGER.error(
            "Skickamejl config entry version %s is no longer supported",
            entry.version,
        )
        return False

    if entry.version == CURRENT_ENTRY_VERSION:
        return True

    _LOGGER.debug(
        "Migrating Skickamejl config entry from version %s to %s",
        entry.version,
        CURRENT_ENTRY_VERSION,
    )
    hass.config_entries.async_update_entry(entry, version=CURRENT_ENTRY_VERSION)
    return True
