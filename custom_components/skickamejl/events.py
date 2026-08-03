"""Event helpers for Skickamejl webhooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .api import SkickamejlEmailSendResult


@dataclass(slots=True, frozen=True)
class SkickamejlWebhookEvent:
    """A Skickamejl event received by Home Assistant."""

    event: str
    template_id: str | None
    delivery_id: str | None
    email_message_id: str | None
    message_id: str | None
    recipient_address: str | None
    sender_address: str | None
    status: int | str | None
    occurred_at_utc: str | None
    received_at_utc: str
    payload: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        received_at_utc: str,
    ) -> SkickamejlWebhookEvent:
        """Build an event from a Skickamejl webhook payload."""
        event = _as_optional_str(
            _value(payload, "event", "eventType", "EventType", "type", "Type")
        )
        event = event or "email.event"
        status = _value(payload, "status", "Status", "deliveryStatus", "DeliveryStatus")
        return cls(
            event=event,
            template_id=_as_optional_str(
                _value(payload, "templateId", "TemplateId", "template_id")
            ),
            delivery_id=_as_optional_str(
                _value(payload, "deliveryId", "DeliveryId", "delivery_id")
            ),
            email_message_id=_as_optional_str(
                _value(payload, "emailMessageId", "EmailMessageId", "email_message_id")
            ),
            message_id=_as_optional_str(
                _value(payload, "messageId", "MessageId", "message_id")
            ),
            recipient_address=_as_optional_str(
                _value(
                    payload,
                    "to",
                    "recipient",
                    "recipientAddress",
                    "RecipientAddress",
                    "recipient_address",
                )
            ),
            sender_address=_as_optional_str(
                _value(
                    payload,
                    "from",
                    "sender",
                    "senderAddress",
                    "SenderAddress",
                    "sender_address",
                )
            ),
            status=_normalize_status(status, event),
            occurred_at_utc=_as_optional_str(
                _value(
                    payload,
                    "occurredAtUtc",
                    "OccurredAtUtc",
                    "queuedAtUtc",
                    "QueuedAtUtc",
                    "createdAtUtc",
                    "CreatedAtUtc",
                    "occurred_at_utc",
                )
            ),
            received_at_utc=received_at_utc,
            payload=dict(payload),
        )

    def as_event_data(self) -> dict[str, Any]:
        """Return Home Assistant event data."""
        data: dict[str, Any] = {
            "event": self.event,
            "template_id": self.template_id,
            "delivery_id": self.delivery_id,
            "email_message_id": self.email_message_id,
            "message_id": self.message_id,
            "recipient_address": self.recipient_address,
            "sender_address": self.sender_address,
            "status": self.status,
            "occurred_at_utc": self.occurred_at_utc,
            "received_at_utc": self.received_at_utc,
            "payload": self.payload,
        }
        return {key: value for key, value in data.items() if value is not None}

    def as_send_result(self) -> SkickamejlEmailSendResult | None:
        """Return a send-result shaped object when delivery metadata is present."""
        if not any(
            (
                self.delivery_id,
                self.email_message_id,
                self.message_id,
                self.status is not None,
            )
        ):
            return None
        return SkickamejlEmailSendResult(
            email_message_id=self.email_message_id,
            delivery_id=self.delivery_id,
            message_id=self.message_id,
            envelope_from=self.sender_address,
            status=self.status,
            queued_at_utc=self.occurred_at_utc or self.received_at_utc,
        )


def _value(payload: dict[str, Any], *keys: str) -> Any:
    """Return the first present payload value."""
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _as_optional_str(value: Any) -> str | None:
    """Return a stripped string or None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: Any, event: str) -> int | str | None:
    """Normalize explicit or event-derived delivery status."""
    if value is not None:
        text = str(value).strip()
        return int(text) if text.isdigit() else text or None

    normalized_event = event.strip().lower().replace("_", ".")
    event_statuses = {
        "queued": "queued",
        "sent": "queued",
        "processing": "processing",
        "delivered": "delivered",
        "deferred": "deferred",
        "bounced": "bounced",
        "failed": "failed",
    }
    for suffix, status in event_statuses.items():
        if normalized_event.endswith(suffix):
            return status
    return None
