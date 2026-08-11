"""Base entities for Skickamejl."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import SkickamejlHealthCoordinator


class SkickamejlEntity(CoordinatorEntity[SkickamejlHealthCoordinator]):
    """Base Skickamejl coordinator entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SkickamejlHealthCoordinator,
        entry_id: str,
        server_url: str | None,
        server_name: str = NAME,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._server_url = server_url
        self._server_name = server_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Skickamejl."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._server_name,
            manufacturer="Skickamejl",
            model="Transactional Email API",
            configuration_url=self._server_url,
        )
