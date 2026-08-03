"""Notify platform for Skickamejl."""

from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import (
    SkickamejlAuthError,
    SkickamejlConnectionError,
    SkickamejlError,
)
from .const import (
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    DEFAULT_NOTIFICATION_TITLE,
    DOMAIN,
    NAME,
    send_result_signal,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Skickamejl notify entities."""
    async_add_entities([SkickamejlNotifyEntity(entry)])


class SkickamejlNotifyEntity(NotifyEntity):
    """Skickamejl email notification entity."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:email-fast-outline"
    _attr_name = None
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_notify"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Skickamejl."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=NAME,
            manufacturer="Skickamejl",
            model="Transactional Email API",
            configuration_url=self._entry.data.get("server_url"),
        )

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a message through Skickamejl."""
        runtime_data = self._entry.runtime_data
        subject = title.strip() if title else DEFAULT_NOTIFICATION_TITLE
        recipient_address = self._entry.data[CONF_RECIPIENT_ADDRESS]
        sender_address = self._entry.data[CONF_SENDER_ADDRESS]

        try:
            result = await runtime_data.api.async_send_email(
                recipient_address=recipient_address,
                sender_address=sender_address,
                subject=subject,
                text_body=message,
            )
        except SkickamejlAuthError as err:
            raise HomeAssistantError("Invalid Skickamejl API key") from err
        except SkickamejlConnectionError as err:
            raise HomeAssistantError("Could not connect to Skickamejl") from err
        except SkickamejlError as err:
            raise HomeAssistantError(f"Skickamejl email send failed: {err}") from err

        runtime_data.last_send = result
        async_dispatcher_send(self.hass, send_result_signal(self._entry.entry_id))

        _LOGGER.debug(
            "Sent Skickamejl notification to %s with delivery id %s",
            recipient_address,
            result.delivery_id,
        )
