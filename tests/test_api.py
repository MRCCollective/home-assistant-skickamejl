"""Tests for the Skickamejl API client."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.skickamejl.api import (
    SkickamejlApiClient,
    SkickamejlAuthError,
    SkickamejlEmailSendResult,
    SkickamejlValidationError,
    normalize_server_url,
    unique_id_for_config,
)


class FakeResponse:
    """Small async context manager that looks like an aiohttp response."""

    def __init__(
        self,
        status: int,
        *,
        json_data: dict[str, Any] | None = None,
        text: str = "",
        content_type: str = "application/json",
    ) -> None:
        """Initialize the fake response."""
        self.status = status
        self._json_data = json_data
        self._text = text
        self.headers = {"Content-Type": content_type}

    async def __aenter__(self) -> FakeResponse:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Exit the async context manager."""

    async def text(self) -> str:
        """Return response text."""
        return self._text

    async def json(self) -> dict[str, Any] | None:
        """Return response JSON."""
        return self._json_data


class FakeSession:
    """Small fake aiohttp session that records requests."""

    def __init__(self, *responses: FakeResponse) -> None:
        """Initialize the fake session."""
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Record and return the next fake response."""
        self.requests.append({"method": method, "url": url, **kwargs})
        return self._responses.pop(0)


def test_normalize_server_url_adds_scheme_and_removes_trailing_slash() -> None:
    """Server URLs are normalized before being stored or used."""
    assert normalize_server_url(" localhost:8080/ ") == "http://localhost:8080"
    assert normalize_server_url("https://api.example.com/") == "https://api.example.com"


def test_unique_id_for_config_is_stable_and_case_insensitive() -> None:
    """Unique IDs should not change because of casing or trailing slash noise."""
    first = unique_id_for_config(
        "https://api.example.com/",
        "Home@Example.com",
        "User@Example.com",
    )
    second = unique_id_for_config(
        "https://API.example.com",
        "home@example.com",
        "user@example.com",
    )

    assert first == second


async def test_check_health_calls_health_endpoint_with_api_key() -> None:
    """Health checks call the backend health endpoint with the configured key."""
    session = FakeSession(FakeResponse(200, content_type="text/plain"))
    client = SkickamejlApiClient(session, "http://localhost:8080", "secret")

    assert await client.async_check_health() is True

    assert session.requests == [
        {
            "method": "GET",
            "url": "http://localhost:8080/health",
            "headers": {"X-Api-Key": "secret", "Accept": "application/json"},
            "json": None,
            "timeout": client._request.__globals__["_REQUEST_TIMEOUT"],
        }
    ]


async def test_send_email_posts_backend_payload_and_parses_result() -> None:
    """Email sends post the Skickamejl payload and parse delivery metadata."""
    response_payload = {
        "emailMessageId": "email-1",
        "deliveryId": "delivery-1",
        "messageId": "message-1",
        "envelopeFrom": "bounce@example.com",
        "status": 0,
        "queuedAtUtc": "2026-08-03T10:00:00Z",
    }
    session = FakeSession(
        FakeResponse(202, json_data=response_payload, text='{"ok":true}')
    )
    client = SkickamejlApiClient(session, "http://localhost:8080", "secret")

    result = await client.async_send_email(
        recipient_address="to@example.com",
        sender_address="from@example.com",
        subject="Subject",
        text_body="Text",
        html_body="<p>Text</p>",
    )

    assert result == SkickamejlEmailSendResult(
        email_message_id="email-1",
        delivery_id="delivery-1",
        message_id="message-1",
        envelope_from="bounce@example.com",
        status=0,
        queued_at_utc="2026-08-03T10:00:00Z",
    )
    assert session.requests[0]["method"] == "POST"
    assert session.requests[0]["url"] == "http://localhost:8080/api/emails"
    assert session.requests[0]["headers"]["X-Api-Key"] == "secret"
    assert session.requests[0]["json"] == {
        "recipientAddress": "to@example.com",
        "senderAddress": "from@example.com",
        "subject": "Subject",
        "textBody": "Text",
        "htmlBody": "<p>Text</p>",
    }


async def test_send_email_rejects_non_json_response() -> None:
    """Unexpected non-JSON send responses are surfaced as validation errors."""
    session = FakeSession(FakeResponse(202, text="accepted", content_type="text/plain"))
    client = SkickamejlApiClient(session, "http://localhost:8080", "secret")

    with pytest.raises(SkickamejlValidationError):
        await client.async_send_email(
            recipient_address="to@example.com",
            sender_address="from@example.com",
            subject="Subject",
            text_body="Text",
        )


async def test_unauthorized_response_raises_auth_error() -> None:
    """Unauthorized backend responses become authentication errors."""
    session = FakeSession(FakeResponse(401))
    client = SkickamejlApiClient(session, "http://localhost:8080", "bad")

    with pytest.raises(SkickamejlAuthError):
        await client.async_check_health()
