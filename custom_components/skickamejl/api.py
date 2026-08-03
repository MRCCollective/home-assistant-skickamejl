"""Async client for the Skickamejl email API."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from urllib.parse import urljoin

from aiohttp import (
    ClientConnectionError,
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
)

_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT = ClientTimeout(total=20)
_RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}


class SkickamejlError(Exception):
    """Base Skickamejl API error."""


class SkickamejlAuthError(SkickamejlError):
    """Authentication failed."""


class SkickamejlConnectionError(SkickamejlError):
    """Could not connect to Skickamejl."""


class SkickamejlServerError(SkickamejlError):
    """Skickamejl returned a retryable server-side error."""


class SkickamejlValidationError(SkickamejlError):
    """Skickamejl rejected the request."""


@dataclass(slots=True, frozen=True)
class SkickamejlEmailSendResult:
    """A Skickamejl email send response."""

    email_message_id: str | None
    delivery_id: str | None
    message_id: str | None
    envelope_from: str | None
    status: int | None
    queued_at_utc: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SkickamejlEmailSendResult:
        """Build a send result from API data."""
        return cls(
            email_message_id=_as_optional_str(data.get("emailMessageId")),
            delivery_id=_as_optional_str(data.get("deliveryId")),
            message_id=_as_optional_str(data.get("messageId")),
            envelope_from=_as_optional_str(data.get("envelopeFrom")),
            status=_as_optional_int(data.get("status")),
            queued_at_utc=_as_optional_str(data.get("queuedAtUtc")),
        )


class SkickamejlApiClient:
    """Skickamejl REST API client."""

    def __init__(
        self,
        session: ClientSession,
        server_url: str,
        api_key: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self.server_url = normalize_server_url(server_url)
        self._api_key = api_key

    @property
    def api_key_fingerprint(self) -> str:
        """Return a non-secret fingerprint of the configured API key."""
        return hashlib.sha256(self._api_key.encode()).hexdigest()[:12]

    async def async_validate_connection(self) -> None:
        """Validate that the configured Skickamejl backend is reachable."""
        await self._request("GET", "/health", expect_json=False)

    async def async_check_health(self) -> bool:
        """Return whether the Skickamejl backend health endpoint is reachable."""
        await self._request("GET", "/health", expect_json=False)
        return True

    async def async_send_email(
        self,
        *,
        recipient_address: str,
        sender_address: str,
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
    ) -> SkickamejlEmailSendResult:
        """Send a plain-text email through Skickamejl."""
        data = await self._request(
            "POST",
            "/api/emails",
            json={
                "recipientAddress": recipient_address,
                "senderAddress": sender_address,
                "subject": subject,
                "textBody": text_body,
                "htmlBody": html_body,
            },
        )
        if not isinstance(data, dict):
            raise SkickamejlValidationError("Unexpected send response from API")
        return SkickamejlEmailSendResult.from_api(data)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        """Make an API request with retries for transient failures."""
        url = urljoin(f"{self.server_url}/", path.lstrip("/"))
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers={
                        "X-Api-Key": self._api_key,
                        "Accept": "application/json",
                    },
                    json=json,
                    timeout=_REQUEST_TIMEOUT,
                ) as response:
                    return await self._handle_response(
                        response,
                        expect_json=expect_json,
                    )
            except (ClientConnectionError, TimeoutError) as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise SkickamejlConnectionError(
                        "Could not connect to Skickamejl"
                    ) from err
            except SkickamejlServerError as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            except ClientError as err:
                raise SkickamejlConnectionError(
                    "Could not communicate with Skickamejl"
                ) from err

            await asyncio.sleep(0.5 * 2**attempt)

        raise SkickamejlConnectionError("Skickamejl request failed") from last_error

    async def _handle_response(
        self,
        response: ClientResponse,
        *,
        expect_json: bool,
    ) -> Any:
        """Convert an HTTP response into content or an integration exception."""
        await self._raise_for_status(response)

        if not expect_json or response.status == HTTPStatus.NO_CONTENT:
            return None

        content_type = response.headers.get("Content-Type", "")
        text = await response.text()
        if not text:
            return None
        if "application/json" not in content_type.lower():
            raise SkickamejlValidationError(
                f"Unexpected Skickamejl response content type: {content_type}"
            )
        return await response.json()

    async def _raise_for_status(self, response: ClientResponse) -> None:
        """Raise a typed integration exception for unsuccessful responses."""
        if response.status == HTTPStatus.UNAUTHORIZED:
            raise SkickamejlAuthError("Invalid Skickamejl API key")
        if response.status == HTTPStatus.FORBIDDEN:
            raise SkickamejlAuthError("Skickamejl API key is not allowed")

        if response.status in _RETRYABLE_STATUSES:
            text = await response.text()
            raise SkickamejlServerError(
                f"Skickamejl returned {response.status}: {text}"
            )

        if response.status >= HTTPStatus.BAD_REQUEST:
            text = await response.text()
            raise SkickamejlValidationError(
                f"Skickamejl returned {response.status}: {text}"
            )


def normalize_server_url(server_url: str) -> str:
    """Normalize a Skickamejl server URL."""
    normalized = server_url.strip().rstrip("/")
    if "://" not in normalized:
        normalized = f"http://{normalized}"
    return normalized


def unique_id_for_config(
    server_url: str,
    sender_address: str,
    recipient_address: str,
) -> str:
    """Build a stable non-secret unique ID for a config entry."""
    material = "|".join(
        (
            normalize_server_url(server_url).lower(),
            sender_address.strip().lower(),
            recipient_address.strip().lower(),
        )
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _as_optional_int(value: Any) -> int | None:
    """Convert API value to optional int."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_str(value: Any) -> str | None:
    """Convert API value to optional string."""
    if value is None:
        return None
    text = str(value)
    return text if text else None
