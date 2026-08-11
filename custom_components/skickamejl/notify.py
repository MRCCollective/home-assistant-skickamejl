"""Notify platform for Skickamejl."""

from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import (
    SkickamejlAuthError,
    SkickamejlConnectionError,
    SkickamejlError,
)
from .config import config_entry_data
from .const import (
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    DEFAULT_NOTIFICATION_TITLE,
    DOMAIN,
)
from .runtime import async_record_send_result

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
        data = config_entry_data(self._entry)
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.runtime_data.server_info.server_name,
            manufacturer="Skickamejl",
            model="Transactional Email API",
            configuration_url=data.get("server_url"),
        )

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a message through Skickamejl."""
        runtime_data = self._entry.runtime_data
        data = config_entry_data(self._entry)
        subject = title.strip() if title else DEFAULT_NOTIFICATION_TITLE
        recipient_address = data[CONF_RECIPIENT_ADDRESS]
        sender_address = data[CONF_SENDER_ADDRESS]

        try:
            result = await runtime_data.api.async_send_email(
                recipient_address=recipient_address,
                sender_address=sender_address,
                subject=subject,
                text_body=message,
            )
        except SkickamejlAuthError as err:
            raise HomeAssistantError("Invalid Skickamejl server API token") from err
        except SkickamejlConnectionError as err:
            raise HomeAssistantError("Could not connect to Skickamejl") from err
        except SkickamejlError as err:
            raise HomeAssistantError(f"Skickamejl email send failed: {err}") from err

        async_record_send_result(self.hass, self._entry, result)

        _LOGGER.debug(
            "Sent Skickamejl notification to %s with delivery id %s",
            recipient_address,
            result.delivery_id,
        )
