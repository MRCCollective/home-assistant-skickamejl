"""Binary sensors for Skickamejl."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config import config_entry_data
from .const import CONF_SERVER_URL, DOMAIN
from .coordinator import SkickamejlHealthCoordinator
from .entity import SkickamejlEntity


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Skickamejl binary sensors."""
    coordinator: SkickamejlHealthCoordinator = entry.runtime_data.coordinator
    data = config_entry_data(entry)
    async_add_entities(
        [
            SkickamejlBackendAvailableBinarySensor(
                coordinator,
                entry.entry_id,
                data.get(CONF_SERVER_URL),
            )
        ]
    )


class SkickamejlBackendAvailableBinarySensor(SkickamejlEntity, BinarySensorEntity):
    """A Skickamejl backend availability binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "backend_available"

    def __init__(
        self,
        coordinator: SkickamejlHealthCoordinator,
        entry_id: str,
        server_url: str | None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, server_url)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_backend_available"

    @property
    def is_on(self) -> bool:
        """Return true when Skickamejl is reachable."""
        return bool(self.coordinator.data)
