"""Constants for the Skickamejl integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "skickamejl"
NAME: Final = "Skickamejl"
DEFAULT_SERVER_URL: Final = "https://skickamejl.se"
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

CONF_API_KEY: Final = "api_key"
CONF_RECIPIENT_ADDRESS: Final = "recipient_address"
CONF_SENDER_ADDRESS: Final = "sender_address"
CONF_SERVER_URL: Final = "server_url"
CONF_CLOUDHOOK_URL: Final = "cloudhook_url"
CONF_WEBHOOK_ID: Final = "webhook_id"

ATTR_FROM: Final = "from"
ATTR_HTML_BODY: Final = "html_body"
ATTR_SUBJECT: Final = "subject"
ATTR_TEXT_BODY: Final = "text_body"
ATTR_TO: Final = "to"

DEFAULT_NOTIFICATION_TITLE: Final = "Home Assistant"

PLATFORMS: Final = [Platform.NOTIFY, Platform.SENSOR, Platform.BINARY_SENSOR]

SERVICE_SEND_EMAIL: Final = "send_email"

SIGNAL_SEND_RESULT: Final = f"{DOMAIN}_send_result"
SIGNAL_WEBHOOK_EVENT: Final = f"{DOMAIN}_webhook_event"
EVENT_EMAIL: Final = f"{DOMAIN}_email_event"

MIN_SUPPORTED_ENTRY_VERSION: Final = 1
CURRENT_ENTRY_VERSION: Final = 1


def send_result_signal(entry_id: str) -> str:
    """Return the dispatcher signal for a config entry's send result."""
    return f"{SIGNAL_SEND_RESULT}_{entry_id}"


def webhook_event_signal(entry_id: str) -> str:
    """Return the dispatcher signal for a config entry's webhook event."""
    return f"{SIGNAL_WEBHOOK_EVENT}_{entry_id}"
