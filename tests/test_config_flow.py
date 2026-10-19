"""Tests for Skickamejl config and options helpers."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.skickamejl.api import SkickamejlApiClient, SkickamejlServerInfo
from custom_components.skickamejl.config import config_entry_data
from custom_components.skickamejl.config_flow import (
    SkickamejlOptionsFlow,
    _normalize_user_input,
    _validate_normalized_input,
    validate_input,
)
from custom_components.skickamejl.const import (
    CONF_API_KEY,
    CONF_CLOUDHOOK_URL,
    CONF_RECIPIENT_ADDRESS,
    CONF_SENDER_ADDRESS,
    CONF_SERVER_URL,
    CONF_WEBHOOK_ID,
)


def test_config_entry_data_merges_options_over_initial_data() -> None:
    """Options should override the original setup data."""
    entry = SimpleNamespace(
        data={
            CONF_SERVER_URL: "http://old.example.test",
            CONF_API_KEY: "old-key",
            CONF_SENDER_ADDRESS: "home@example.com",
            CONF_RECIPIENT_ADDRESS: "old@example.com",
        },
        options={
            CONF_SERVER_URL: "http://new.example.test",
            CONF_RECIPIENT_ADDRESS: "new@example.com",
        },
    )

    assert config_entry_data(entry) == {
        CONF_SERVER_URL: "http://new.example.test",
        CONF_API_KEY: "old-key",
        CONF_SENDER_ADDRESS: "home@example.com",
        CONF_RECIPIENT_ADDRESS: "new@example.com",
    }


def test_normalize_user_input_trims_values_and_normalizes_url() -> None:
    """Config and options input should be normalized before validation/storage."""
    assert _normalize_user_input(
        {
            CONF_SERVER_URL: " localhost:8080/ ",
            CONF_API_KEY: " secret ",
            CONF_SENDER_ADDRESS: " home@example.com ",
            CONF_RECIPIENT_ADDRESS: " you@example.com ",
        }
    ) == {
        CONF_SERVER_URL: "http://localhost:8080",
        CONF_API_KEY: "secret",
        CONF_SENDER_ADDRESS: "home@example.com",
        CONF_RECIPIENT_ADDRESS: "you@example.com",
    }


def test_validate_normalized_input_reports_blank_key_and_invalid_emails() -> None:
    """Local form validation catches required and email-shaped fields."""
    errors = _validate_normalized_input(
        {
            CONF_SERVER_URL: "http://localhost:8080",
            CONF_API_KEY: "",
            CONF_SENDER_ADDRESS: "not-an-email",
            CONF_RECIPIENT_ADDRESS: "also-bad",
        }
    )

    assert errors == {
        CONF_API_KEY: "required",
        CONF_SENDER_ADDRESS: "invalid_email",
        CONF_RECIPIENT_ADDRESS: "invalid_email",
    }


async def test_validate_input_uses_authenticated_server_identity(monkeypatch) -> None:
    """The config entry title and unique ID come from the API token's server."""

    async def fake_validate(_client: SkickamejlApiClient) -> SkickamejlServerInfo:
        return SkickamejlServerInfo("SERVER-1", "Produktion")

    monkeypatch.setattr(SkickamejlApiClient, "async_validate_connection", fake_validate)
    data = {
        CONF_SERVER_URL: "https://skickamejl.se",
        CONF_API_KEY: "secret",
        CONF_SENDER_ADDRESS: "home@example.com",
        CONF_RECIPIENT_ADDRESS: "user@example.com",
    }

    info = await validate_input(None, object(), data)

    assert info == {"title": "Produktion", "unique_id": "server-1"}


async def test_options_flow_shows_webhook_url_only_in_configure_dialog() -> None:
    """An admin can copy the secret after installing the integration."""
    entry = SimpleNamespace(
        data={
            CONF_SERVER_URL: "https://skickamejl.se",
            CONF_API_KEY: "secret",
            CONF_SENDER_ADDRESS: "home@example.com",
            CONF_RECIPIENT_ADDRESS: "you@example.com",
            CONF_WEBHOOK_ID: "skickamejl_existing",
            CONF_CLOUDHOOK_URL: "https://hooks.nabu.casa/cloud-hook",
        },
        options={},
    )
    flow = SkickamejlOptionsFlow(entry)
    flow.hass = SimpleNamespace()

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["description_placeholders"]["webhook_url"] == (
        "https://hooks.nabu.casa/cloud-hook"
    )
