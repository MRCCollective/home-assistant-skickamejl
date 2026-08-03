"""Config flow for Skickamejl."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SkickamejlApiClient,
    SkickamejlConnectionError,
    SkickamejlError,
    normalize_server_url,
    unique_id_for_config,
)
from .config import config_entry_data
from .const import (
    CONF_API_KEY,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    CONF_SERVER_URL,
    DEFAULT_SERVER_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the config/options form schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SERVER_URL,
                default=defaults.get(CONF_SERVER_URL, DEFAULT_SERVER_URL),
            ): str,
            vol.Required(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): str,
            vol.Required(
                CONF_SENDER_ADDRESS,
                default=defaults.get(CONF_SENDER_ADDRESS, ""),
            ): str,
            vol.Required(
                CONF_RECIPIENT_ADDRESS,
                default=defaults.get(CONF_RECIPIENT_ADDRESS, ""),
            ): str,
        }
    )


STEP_USER_DATA_SCHEMA = _schema()


async def validate_input(
    _hass: HomeAssistant,
    session: ClientSession,
    data: dict[str, str],
) -> dict[str, str]:
    """Validate user input by connecting to Skickamejl."""
    api = SkickamejlApiClient(
        session,
        data[CONF_SERVER_URL],
        data[CONF_API_KEY],
    )
    await api.async_validate_connection()
    return {
        "title": "Skickamejl",
        "unique_id": unique_id_for_config(
            data[CONF_SERVER_URL],
            data[CONF_SENDER_ADDRESS],
            data[CONF_RECIPIENT_ADDRESS],
        ),
    }


class SkickamejlConfigFlow(  # type: ignore[call-arg, unused-ignore]
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Skickamejl."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SkickamejlOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_input = _normalize_user_input(user_input)
            errors.update(_validate_normalized_input(normalized_input))

            if not errors:
                try:
                    info = await validate_input(
                        self.hass,
                        async_get_clientsession(self.hass),
                        normalized_input,
                    )
                except SkickamejlConnectionError:
                    errors["base"] = "cannot_connect"
                except SkickamejlError:
                    _LOGGER.exception("Unexpected Skickamejl validation error")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(info["unique_id"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=info["title"],
                        data=normalized_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class SkickamejlOptionsFlow(config_entries.OptionsFlow):
    """Handle Skickamejl options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage Skickamejl options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_input = _normalize_user_input(user_input)
            errors.update(_validate_normalized_input(normalized_input))

            if not errors:
                try:
                    await validate_input(
                        self.hass,
                        async_get_clientsession(self.hass),
                        normalized_input,
                    )
                except SkickamejlConnectionError:
                    errors["base"] = "cannot_connect"
                except SkickamejlError:
                    _LOGGER.exception("Unexpected Skickamejl options error")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title="",
                        data=normalized_input,
                    )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(config_entry_data(self._config_entry)),
            errors=errors,
        )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Normalize form input."""
    return {
        CONF_SERVER_URL: normalize_server_url(user_input[CONF_SERVER_URL]),
        CONF_API_KEY: str(user_input[CONF_API_KEY]).strip(),
        CONF_SENDER_ADDRESS: str(user_input[CONF_SENDER_ADDRESS]).strip(),
        CONF_RECIPIENT_ADDRESS: str(user_input[CONF_RECIPIENT_ADDRESS]).strip(),
    }


def _validate_normalized_input(data: dict[str, str]) -> dict[str, str]:
    """Validate normalized form input."""
    errors: dict[str, str] = {}
    if not data[CONF_API_KEY]:
        errors[CONF_API_KEY] = "required"
    if not _looks_like_email(data[CONF_SENDER_ADDRESS]):
        errors[CONF_SENDER_ADDRESS] = "invalid_email"
    if not _looks_like_email(data[CONF_RECIPIENT_ADDRESS]):
        errors[CONF_RECIPIENT_ADDRESS] = "invalid_email"
    return errors


def _looks_like_email(value: str) -> bool:
    """Return true when a value is shaped like an email address."""
    local, separator, domain = value.partition("@")
    return bool(local and separator and "." in domain)
