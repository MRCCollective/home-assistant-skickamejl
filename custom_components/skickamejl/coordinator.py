"""Skickamejl data update coordinator."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import SkickamejlApiClient, SkickamejlError
from .const import DEFAULT_SCAN_INTERVAL, NAME

_LOGGER = logging.getLogger(__name__)


class SkickamejlHealthCoordinator(DataUpdateCoordinator[bool]):
    """Coordinate Skickamejl backend health updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SkickamejlApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> bool:
        """Fetch backend health from Skickamejl."""
        try:
            return await self.api.async_check_health()
        except SkickamejlError as err:
            _LOGGER.debug("Skickamejl health check failed: %s", err)
            return False
