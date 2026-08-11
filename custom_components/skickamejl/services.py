"""Services for the Skickamejl integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.selector import ConfigEntrySelector

from .api import SkickamejlError
from .config import config_entry_data
from .const import (
    ATTR_FROM,
    ATTR_HTML_BODY,
    ATTR_SUBJECT,
    ATTR_TEXT_BODY,
    ATTR_TO,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    DOMAIN,
    SERVICE_SEND_EMAIL,
)
from .runtime import async_record_send_result

_LOGGER = logging.getLogger(__name__)

SEND_EMAIL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_TO): cv.string,
        vol.Optional(ATTR_FROM): cv.string,
        vol.Required(ATTR_SUBJECT): cv.string,
        vol.Optional(ATTR_TEXT_BODY): cv.string,
        vol.Optional(ATTR_HTML_BODY): cv.string,
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Skickamejl services."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_EMAIL):
        return

    async def send_email(call: ServiceCall) -> None:
        runtime_data, entry_data = _runtime_from_call(hass, call)
        recipient_address = _field_or_default(
            call,
            ATTR_TO,
            entry_data[CONF_RECIPIENT_ADDRESS],
        )
        sender_address = _field_or_default(
            call,
            ATTR_FROM,
            entry_data[CONF_SENDER_ADDRESS],
        )
        subject = _required_text(call, ATTR_SUBJECT)
        text_body = _optional_text(call, ATTR_TEXT_BODY)
        html_body = _optional_text(call, ATTR_HTML_BODY)

        if not _looks_like_email(recipient_address):
            raise ServiceValidationError("to must be a valid email address")
        if not _looks_like_email(sender_address):
            raise ServiceValidationError("from must be a valid email address")
        if text_body is None and html_body is None:
            raise ServiceValidationError("text_body or html_body is required")

        try:
            result = await runtime_data.api.async_send_email(
                recipient_address=recipient_address,
                sender_address=sender_address,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        except SkickamejlError as err:
            _LOGGER.warning("Skickamejl send_email service call failed: %s", err)
            raise HomeAssistantError(str(err)) from err

        entry = _entry_from_call(hass, call)
        async_record_send_result(hass, entry, result)

        _LOGGER.debug(
            "Sent Skickamejl service email to %s with delivery id %s",
            recipient_address,
            result.delivery_id,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_EMAIL,
        send_email,
        schema=SEND_EMAIL_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Skickamejl services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND_EMAIL)


def _runtime_from_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> tuple[Any, dict[str, Any]]:
    """Return runtime and config data for a service call."""
    domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
    entry_id = str(call.data[ATTR_CONFIG_ENTRY_ID])
    runtime_data = domain_data.get(entry_id)
    entry = _entry_by_id(hass, entry_id)
    if runtime_data is None or entry is None:
        raise ServiceValidationError(
            f"Unknown or unloaded Skickamejl config_entry_id: {entry_id}"
        )
    return runtime_data, config_entry_data(entry)


def _entry_id_from_call(_hass: HomeAssistant, call: ServiceCall) -> str:
    """Return the config entry ID selected by a service call."""
    entry_id = str(call.data[ATTR_CONFIG_ENTRY_ID]).strip()
    if not entry_id:
        raise ServiceValidationError("config_entry_id must not be empty")
    return entry_id


def _entry_from_call(hass: HomeAssistant, call: ServiceCall) -> Any:
    """Return the config entry selected by a service call."""
    entry_id = _entry_id_from_call(hass, call)
    entry = _entry_by_id(hass, entry_id)
    if entry is None:
        raise ServiceValidationError(f"Unknown Skickamejl config_entry_id: {entry_id}")
    return entry


def _entry_by_id(hass: HomeAssistant, entry_id: str) -> Any | None:
    """Return a Skickamejl config entry by ID."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == entry_id:
            return entry
    return None


def _field_or_default(call: ServiceCall, field: str, default: Any) -> str:
    """Return a stripped service field value or a configured default."""
    return str(call.data.get(field, default)).strip()


def _required_text(call: ServiceCall, field: str) -> str:
    """Return a required non-empty text value."""
    value = str(call.data[field]).strip()
    if not value:
        raise ServiceValidationError(f"{field} must not be empty")
    return value


def _optional_text(call: ServiceCall, field: str) -> str | None:
    """Return an optional non-empty text value."""
    if field not in call.data:
        return None
    value = str(call.data[field]).strip()
    return value or None


def _looks_like_email(value: str) -> bool:
    """Return true when a value is shaped like an email address."""
    local, separator, domain = value.partition("@")
    return bool(local and separator and "." in domain)
