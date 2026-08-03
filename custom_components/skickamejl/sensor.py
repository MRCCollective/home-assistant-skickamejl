"""Sensors for Skickamejl."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SkickamejlEmailSendResult
from .const import DOMAIN, send_result_signal

DELIVERY_STATUSES = {
    0: "queued",
    1: "processing",
    2: "delivered",
    3: "deferred",
    4: "bounced",
    5: "failed",
}


@dataclass(frozen=True, kw_only=True)
class SkickamejlLastSendSensorDescription(SensorEntityDescription):
    """Describe a Skickamejl last-send sensor."""

    value_fn: Callable[[SkickamejlEmailSendResult], datetime | int | str | None]


SENSORS: tuple[SkickamejlLastSendSensorDescription, ...] = (
    SkickamejlLastSendSensorDescription(
        key="last_delivery_status",
        translation_key="last_delivery_status",
        icon="mdi:email-check-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: _delivery_status(result.status),
    ),
    SkickamejlLastSendSensorDescription(
        key="last_delivery_id",
        translation_key="last_delivery_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.delivery_id,
    ),
    SkickamejlLastSendSensorDescription(
        key="last_message_id",
        translation_key="last_message_id",
        icon="mdi:email-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.message_id,
    ),
    SkickamejlLastSendSensorDescription(
        key="last_queued_at",
        translation_key="last_queued_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: _parse_timestamp(result.queued_at_utc),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Skickamejl sensors."""
    async_add_entities(
        SkickamejlLastSendSensor(entry, description) for description in SENSORS
    )


class SkickamejlLastSendSensor(SensorEntity):
    """A Skickamejl last-send sensor."""

    _attr_has_entity_name = True
    entity_description: SkickamejlLastSendSensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        description: SkickamejlLastSendSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Subscribe to send-result updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                send_result_signal(self._entry.entry_id),
                self._handle_send_result,
            )
        )

    def _handle_send_result(self) -> None:
        """Update the sensor after Skickamejl sends an email."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | int | str | None:
        """Return the native sensor value."""
        result: SkickamejlEmailSendResult | None = self._entry.runtime_data.last_send
        if result is None:
            return None
        return self.entity_description.value_fn(result)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None] | None:
        """Return last-send details."""
        result: SkickamejlEmailSendResult | None = self._entry.runtime_data.last_send
        if result is None:
            return None
        return {
            "email_message_id": result.email_message_id,
            "delivery_id": result.delivery_id,
            "message_id": result.message_id,
            "envelope_from": result.envelope_from,
            "status": result.status,
            "status_name": _delivery_status(result.status),
            "queued_at_utc": result.queued_at_utc,
        }


def _delivery_status(status: int | None) -> str | None:
    """Map a Skickamejl numeric delivery status to a readable state."""
    if status is None:
        return None
    return DELIVERY_STATUSES.get(status, str(status))


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an API timestamp into a Home Assistant timestamp value."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
