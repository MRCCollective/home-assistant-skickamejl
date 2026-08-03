"""Config entry helpers for Skickamejl."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry


def config_entry_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return config entry data with options overriding initial setup data."""
    return {
        **dict(getattr(entry, "data", {})),
        **dict(getattr(entry, "options", {})),
    }
