"""Tests for Skickamejl dashboard card assets."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_CARD = ROOT / "www" / "skickamejl-card.js"
COMPONENT_CARD = (
    ROOT / "custom_components" / "skickamejl" / "www" / "skickamejl-card.js"
)


def test_card_assets_are_copied_to_component_static_folder() -> None:
    """The integration-served card copy should match the root development copy."""
    assert ROOT_CARD.read_bytes() == COMPONENT_CARD.read_bytes()
    assert (ROOT / "www" / "skickamejl-icon.png").is_file()
    assert (
        ROOT / "custom_components" / "skickamejl" / "www" / "skickamejl-icon.png"
    ).is_file()


def test_card_registers_custom_card_and_editor() -> None:
    """The dashboard card registers its element, editor, and card picker metadata."""
    source = ROOT_CARD.read_text(encoding="utf-8")

    assert 'if (!customElements.get("skickamejl-card"))' in source
    assert 'customElements.define("skickamejl-card", SkickamejlCard)' in source
    assert 'if (!customElements.get("skickamejl-card-editor"))' in source
    assert (
        'customElements.define("skickamejl-card-editor", SkickamejlCardEditor)'
        in source
    )
    assert (
        '!window.customCards.some((card) => card.type === "skickamejl-card")' in source
    )
    assert 'type: "skickamejl-card"' in source
    assert 'type: "custom:skickamejl-card"' in source
    assert "getEntitySuggestion" in source


def test_card_contains_swedish_and_english_localization() -> None:
    """The card should include both Swedish and English UI strings."""
    source = ROOT_CARD.read_text(encoding="utf-8")

    assert "CARD_TRANSLATIONS" in source
    assert "Skickamejl är inte konfigurerat än" in source
    assert "Could not copy" in source
    assert "Kunde inte kopiera" in source
    assert "languageFromHass" in source
    assert "preferred_language" in source
    assert "Delivery history" in source
    assert "Leveranshistorik" in source
    assert "No email sent yet" in source
    assert "Ingen e-post skickad än" in source


def test_card_includes_opt_in_test_send_form() -> None:
    """The card can send a test email through its associated config entry."""
    source = ROOT_CARD.read_text(encoding="utf-8")

    assert "show_test_form: false" in source
    assert "_sendTestEmail" in source
    assert 'callService("skickamejl", "send_email", data)' in source
    assert 'class="test-form"' in source
    assert "config_entry_id" in source
    assert "server_name" in source
    assert "configEntryId" in source


def test_card_auto_detects_swedish_entity_names() -> None:
    """The card should find entities created with Swedish display names."""
    source = ROOT_CARD.read_text(encoding="utf-8")

    assert "normalizeEntityText" in source
    assert "entityFriendlyName" in source
    assert "backend_tillganglig" in source
    assert "senaste_leveransstatus" in source
    assert "senaste_leverans_id" in source
    assert "senaste_meddelande_id" in source
    assert "senast_koad" in source


def test_card_has_clipboard_fallback_for_local_home_assistant() -> None:
    """Local HTTP dashboards may not expose navigator.clipboard."""
    source = ROOT_CARD.read_text(encoding="utf-8")

    assert "_writeClipboard" in source
    assert "_fallbackCopy" in source
    assert "window.isSecureContext" in source
    assert 'document.execCommand("copy")' in source


def test_card_resource_version_matches_docs_and_manifest() -> None:
    """The card version should match README resource docs and manifest version."""
    source = ROOT_CARD.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    manifest = json.loads(
        (ROOT / "custom_components" / "skickamejl" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    version_match = re.search(r'CARD_VERSION = "([^"]+)"', source)
    assert version_match is not None
    version = version_match.group(1)

    assert manifest["version"] == version
    assert f"/skickamejl_static/skickamejl-card.js?v={version}" in readme


def test_integration_registers_card_static_path() -> None:
    """The Home Assistant integration should serve the card from /skickamejl_static."""
    source = (ROOT / "custom_components" / "skickamejl" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert 'FRONTEND_URL = "/skickamejl_static"' in source
    assert 'FRONTEND_PATH = Path(__file__).parent / "www"' in source
    assert "async_register_static_paths" in source
