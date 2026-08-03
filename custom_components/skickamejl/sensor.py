"""Sensors for Skickamejl."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components import webhook as ha_webhook
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
from homeassistant.helpers.network import NoURLAvailableError

from .api import SkickamejlEmailSendResult
from .config import config_entry_data
from .const import (
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_EMAIL,
    send_result_signal,
    webhook_event_signal,
)
from .events import SkickamejlWebhookEvent

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


@dataclass(frozen=True, kw_only=True)
class SkickamejlWebhookEventSensorDescription(SensorEntityDescription):
    """Describe a Skickamejl webhook event sensor."""

    value_fn: Callable[[SkickamejlWebhookEvent], datetime | int | str | None]


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

WEBHOOK_EVENT_SENSORS: tuple[SkickamejlWebhookEventSensorDescription, ...] = (
    SkickamejlWebhookEventSensorDescription(
        key="last_event_type",
        translation_key="last_event_type",
        icon="mdi:email-sync-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda event: event.event,
    ),
    SkickamejlWebhookEventSensorDescription(
        key="last_template_id",
        translation_key="last_template_id",
        icon="mdi:email-seal-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda event: event.template_id,
    ),
    SkickamejlWebhookEventSensorDescription(
        key="last_webhook_delivery_id",
        translation_key="last_webhook_delivery_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda event: event.delivery_id,
    ),
    SkickamejlWebhookEventSensorDescription(
        key="last_webhook_received_at",
        translation_key="last_webhook_received_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda event: _parse_timestamp(event.received_at_utc),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Skickamejl sensors."""
    async_add_entities(
        [
            *(SkickamejlLastSendSensor(entry, description) for description in SENSORS),
            SkickamejlWebhookUrlSensor(entry),
            *(
                SkickamejlWebhookEventSensor(entry, description)
                for description in WEBHOOK_EVENT_SENSORS
            ),
        ]
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
    def extra_state_attributes(
        self,
    ) -> dict[str, str | int | list[dict[str, object]] | None] | None:
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
            "attempt_count": result.attempt_count,
            "created_at_utc": result.created_at_utc,
            "last_attempt_at_utc": result.last_attempt_at_utc,
            "next_attempt_at_utc": result.next_attempt_at_utc,
            "completed_at_utc": result.completed_at_utc,
            "last_error": result.last_error,
            "attempts": list(result.attempts),
            "status_events": list(result.status_events),
        }


class SkickamejlWebhookUrlSensor(SensorEntity):
    """A Skickamejl webhook URL sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "webhook_url"
    _attr_icon = "mdi:webhook"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_webhook_url"

    @property
    def native_value(self) -> str:
        """Return the native sensor value."""
        return "configured"

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return webhook details users can copy into Skickamejl."""
        webhook_id = config_entry_data(self._entry)[CONF_WEBHOOK_ID]
        try:
            full_url = ha_webhook.async_generate_url(
                self.hass,
                webhook_id,
                allow_internal=True,
                allow_external=True,
                prefer_external=True,
            )
        except NoURLAvailableError:
            full_url = None
        return {
            "event_type": EVENT_EMAIL,
            "webhook_path": ha_webhook.URL_WEBHOOK_PATH.format(webhook_id=webhook_id),
            "webhook_url": full_url,
        }


class SkickamejlWebhookEventSensor(SensorEntity):
    """A Skickamejl latest webhook event sensor."""

    _attr_has_entity_name = True
    entity_description: SkickamejlWebhookEventSensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        description: SkickamejlWebhookEventSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Subscribe to webhook event updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                webhook_event_signal(self._entry.entry_id),
                self._handle_webhook_event,
            )
        )

    def _handle_webhook_event(self) -> None:
        """Update the sensor after Skickamejl sends a webhook."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | int | str | None:
        """Return the native sensor value."""
        event: SkickamejlWebhookEvent | None = (
            self._entry.runtime_data.last_webhook_event
        )
        if event is None:
            return None
        return self.entity_description.value_fn(event)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return webhook event details."""
        event: SkickamejlWebhookEvent | None = (
            self._entry.runtime_data.last_webhook_event
        )
        if event is None:
            return None
        return event.as_event_data()


def _delivery_status(status: int | str | None) -> str | None:
    """Map a Skickamejl numeric delivery status to a readable state."""
    if status is None:
        return None
    if isinstance(status, str):
        normalized = status.strip().lower()
        if normalized.isdigit():
            return DELIVERY_STATUSES.get(int(normalized), normalized)
        return normalized or None
    return DELIVERY_STATUSES.get(status, str(status))


def is_terminal_delivery_status(status: int | str | None) -> bool:
    """Return whether a delivery status is terminal."""
    return _delivery_status(status) in {"delivered", "bounced", "failed"}


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an API timestamp into a Home Assistant timestamp value."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
