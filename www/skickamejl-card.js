const CARD_VERSION = "0.3.0";
const CARD_RESOURCE_URL = `/skickamejl_static/skickamejl-card.js?v=${CARD_VERSION}`;
const ICON_SRC = `/skickamejl_static/skickamejl-icon.png?v=${CARD_VERSION}-icon`;
const DEFAULT_BACKGROUND = "#f7fbff";
const LANGUAGE_MODES = ["auto", "sv", "en"];
const THEME_MODES = ["auto", "light", "dark"];
const DEFAULT_LANGUAGE = "en";

const CARD_TRANSLATIONS = {
  en: {
    backend: "Backend",
    backendAvailable: "Online",
    backendUnavailable: "Offline",
    backendUnknown: "Unknown",
    backendEntity: "Backend entity",
    background: "Background",
    clear: "Clear",
    copied: "Copied",
    copy: "Copy",
    deliveryId: "Delivery ID",
    deliveryIdEntity: "Delivery ID entity",
    deliveryHistory: "Delivery history",
    emailBody: "Message",
    entityUnavailable: "Entity unavailable",
    from: "From",
    language: "Language",
    languageAuto: "Automatic",
    languageEnglish: "English",
    languageSwedish: "Swedish",
    attempts: "Attempts",
    lastQueuedAt: "Queued",
    lastQueuedAtEntity: "Queued entity",
    lastError: "Last error",
    lastSend: "Last email",
    messageId: "Message ID",
    messageIdEntity: "Message ID entity",
    noEmailYet: "No email sent yet",
    noEmailYetDetail: "Send a test email or trigger an automation to start tracking delivery.",
    noValue: "Not available",
    recipientPreset: "Recipient preset",
    recipientPresetNone: "Custom recipient",
    requiresSetup: "Skickamejl is not configured yet",
    send: "Send",
    sendFailed: "Email could not be sent",
    sendSucceeded: "Email queued",
    showLogo: "Show logo",
    showTestForm: "Show test form",
    status: "Status",
    statusBounced: "Bounced",
    statusDelivered: "Delivered",
    statusDeferred: "Deferred",
    statusEntity: "Status entity",
    statusFailed: "Failed",
    statusProcessing: "Processing",
    statusQueued: "Queued",
    statusUnknown: "Unknown",
    subject: "Subject",
    testEmail: "Test email",
    theme: "Theme",
    themeAuto: "Automatic",
    themeDark: "Dark",
    themeLight: "Light",
    to: "To",
  },
  sv: {
    backend: "Backend",
    backendAvailable: "Online",
    backendUnavailable: "Offline",
    backendUnknown: "Okänd",
    backendEntity: "Backend-entitet",
    background: "Bakgrund",
    clear: "Rensa",
    copied: "Kopierad",
    copy: "Kopiera",
    deliveryId: "Leverans-ID",
    deliveryIdEntity: "Leverans-ID-entitet",
    deliveryHistory: "Leveranshistorik",
    emailBody: "Meddelande",
    entityUnavailable: "Entitet saknas",
    from: "Från",
    language: "Språk",
    languageAuto: "Automatiskt",
    languageEnglish: "English",
    languageSwedish: "Svenska",
    attempts: "Försök",
    lastQueuedAt: "Köad",
    lastQueuedAtEntity: "Köad-entitet",
    lastError: "Senaste fel",
    lastSend: "Senaste e-post",
    messageId: "Meddelande-ID",
    messageIdEntity: "Meddelande-ID-entitet",
    noEmailYet: "Ingen e-post skickad än",
    noEmailYetDetail: "Skicka ett testmejl eller kör en automation för att börja följa leveransen.",
    noValue: "Saknas",
    recipientPreset: "Mottagarförval",
    recipientPresetNone: "Egen mottagare",
    requiresSetup: "Skickamejl är inte konfigurerat än",
    send: "Skicka",
    sendFailed: "E-post kunde inte skickas",
    sendSucceeded: "E-post köad",
    showLogo: "Visa logotyp",
    showTestForm: "Visa testformulär",
    status: "Status",
    statusBounced: "Studsad",
    statusDelivered: "Levererad",
    statusDeferred: "Fördröjd",
    statusEntity: "Statusentitet",
    statusFailed: "Misslyckad",
    statusProcessing: "Bearbetas",
    statusQueued: "Köad",
    statusUnknown: "Okänd",
    subject: "Ämne",
    testEmail: "Testa e-post",
    theme: "Tema",
    themeAuto: "Automatiskt",
    themeDark: "Mörkt",
    themeLight: "Ljust",
    to: "Till",
  },
};

const STATUS_META = {
  queued: { icon: "mdi:clock-outline", tone: "neutral", key: "statusQueued" },
  processing: { icon: "mdi:progress-clock", tone: "neutral", key: "statusProcessing" },
  delivered: { icon: "mdi:check-circle-outline", tone: "good", key: "statusDelivered" },
  deferred: { icon: "mdi:timer-sand", tone: "warn", key: "statusDeferred" },
  bounced: { icon: "mdi:email-remove-outline", tone: "bad", key: "statusBounced" },
  failed: { icon: "mdi:alert-circle-outline", tone: "bad", key: "statusFailed" },
};

function normalizeLanguageMode(languageMode) {
  return LANGUAGE_MODES.includes(languageMode) ? languageMode : "auto";
}

function normalizeThemeMode(themeMode, darkMode) {
  if (THEME_MODES.includes(themeMode)) {
    return themeMode;
  }
  return darkMode === true ? "dark" : "auto";
}

function languageFromHass(hass, preferredLanguage) {
  const languageMode = normalizeLanguageMode(preferredLanguage);
  if (languageMode !== "auto") {
    return languageMode;
  }
  const hassLanguage = String(hass?.locale?.language ?? hass?.language ?? "").toLowerCase();
  if (hassLanguage.startsWith("sv")) {
    return "sv";
  }
  if (hassLanguage.startsWith("en")) {
    return "en";
  }
  return DEFAULT_LANGUAGE;
}

function localize(language, key) {
  return CARD_TRANSLATIONS[language]?.[key] ?? CARD_TRANSLATIONS[DEFAULT_LANGUAGE][key] ?? key;
}

function isSkickamejlEntity(hass, entityId) {
  return Boolean(entityId && hass?.states?.[entityId] && entityId.includes("skickamejl"));
}

function findEntity(hass, preferredEntityId, suffix, domainPrefix) {
  if (isSkickamejlEntity(hass, preferredEntityId)) {
    return preferredEntityId;
  }
  return Object.keys(hass?.states ?? {}).find(
    (entityId) =>
      entityId.startsWith(domainPrefix) &&
      entityId.includes("skickamejl") &&
      entityId.includes(suffix),
  );
}

function findSkickamejlEntities(hass, config = {}) {
  return {
    backend: findEntity(hass, config.backend_entity, "backend_available", "binary_sensor."),
    status: findEntity(hass, config.status_entity, "last_delivery_status", "sensor."),
    deliveryId: findEntity(hass, config.delivery_id_entity, "last_delivery_id", "sensor."),
    messageId: findEntity(hass, config.message_id_entity, "last_message_id", "sensor."),
    queuedAt: findEntity(hass, config.queued_at_entity, "last_queued_at", "sensor."),
  };
}

function normalizeRecipientPresets(presets) {
  if (!Array.isArray(presets)) {
    return [];
  }
  return presets
    .map((preset) => ({
      name: String(preset?.name ?? preset?.label ?? preset?.email ?? "").trim(),
      email: String(preset?.email ?? preset?.address ?? "").trim(),
    }))
    .filter((preset) => preset.name && preset.email);
}

class SkickamejlCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("skickamejl-card-editor");
  }

  static getStubConfig(hass) {
    const entities = findSkickamejlEntities(hass);
    return {
      type: "custom:skickamejl-card",
      backend_entity: entities.backend,
      status_entity: entities.status,
      delivery_id_entity: entities.deliveryId,
      message_id_entity: entities.messageId,
      queued_at_entity: entities.queuedAt,
      preferred_language: "auto",
      theme_mode: "auto",
      background_color: DEFAULT_BACKGROUND,
      show_logo: true,
      show_test_form: true,
      recipient_presets: [],
    };
  }

  setConfig(config) {
    this._config = {
      preferred_language: "auto",
      theme_mode: "auto",
      background_color: DEFAULT_BACKGROUND,
      show_logo: true,
      show_test_form: true,
      recipient_presets: [],
      ...config,
      preferred_language: normalizeLanguageMode(config.preferred_language),
      theme_mode: normalizeThemeMode(config.theme_mode, config.dark_mode),
      recipient_presets: normalizeRecipientPresets(config.recipient_presets),
    };
    delete this._config.dark_mode;
    this._busy = false;
    this._notice = undefined;
    this._lastSignature = "";
    this._form = {
      to: "",
      from: "",
      subject: "",
      body: "",
    };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    const signature = this._signature();
    if (signature !== this._lastSignature) {
      this._lastSignature = signature;
      this._render();
    }
  }

  getCardSize() {
    return this._config?.show_test_form ? 5 : 3;
  }

  _entities() {
    return findSkickamejlEntities(this._hass, this._config);
  }

  _state(entityId) {
    return entityId ? this._hass?.states?.[entityId] : undefined;
  }

  _language() {
    return languageFromHass(this._hass, this._config.preferred_language);
  }

  _t(key) {
    return localize(this._language(), key);
  }

  _recipientPresets() {
    return normalizeRecipientPresets(this._config.recipient_presets);
  }

  _isDarkMode() {
    const themeMode = normalizeThemeMode(this._config.theme_mode, this._config.dark_mode);
    if (themeMode === "dark") {
      return true;
    }
    if (themeMode === "light") {
      return false;
    }
    if (typeof this._hass?.themes?.darkMode === "boolean") {
      return this._hass.themes.darkMode;
    }
    return Boolean(this._hass?.selectedTheme?.dark);
  }

  _signature() {
    const entities = this._entities();
    return JSON.stringify({
      language: this._language(),
      dark: this._isDarkMode(),
      config: this._config,
      notice: this._notice,
      busy: this._busy,
      states: Object.values(entities).map((entityId) => {
        const state = this._state(entityId);
        return {
          entityId,
          state: state?.state,
          attributes: state?.attributes,
        };
      }),
    });
  }

  async _sendTestEmail() {
    const subject = this._form.subject.trim();
    const textBody = this._form.body.trim();
    if (!this._hass || !subject || !textBody || this._busy) {
      return;
    }

    const payload = {
      subject,
      text_body: textBody,
    };
    if (this._form.to.trim()) {
      payload.to = this._form.to.trim();
    }
    if (this._form.from.trim()) {
      payload.from = this._form.from.trim();
    }

    this._busy = true;
    this._notice = undefined;
    this._render();
    try {
      await this._hass.callService("skickamejl", "send_email", payload);
      this._notice = { type: "success", text: this._t("sendSucceeded") };
      this._form.subject = "";
      this._form.body = "";
    } catch (_err) {
      this._notice = { type: "error", text: this._t("sendFailed") };
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _copy(value) {
    const text = String(value ?? "").trim();
    if (!text || text === "unknown" || text === "unavailable") {
      return;
    }
    try {
      await navigator.clipboard?.writeText(text);
      this._notice = { type: "success", text: this._t("copied") };
      this._render();
    } catch (_err) {
      // Clipboard permissions vary between dashboard contexts.
    }
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this._config) {
      return;
    }

    const entities = this._entities();
    const backend = this._state(entities.backend);
    const status = this._state(entities.status);
    const deliveryId = this._state(entities.deliveryId);
    const messageId = this._state(entities.messageId);
    const queuedAt = this._state(entities.queuedAt);
    const backendState = backend?.state;
    const statusState = status?.state;
    const dark = this._isDarkMode() ? "dark" : "";
    const background = this._escapeCssColor(this._config.background_color || DEFAULT_BACKGROUND);
    const hasIntegrationEntity = Boolean(backend || status || deliveryId || messageId || queuedAt);
    const hasLastSend = [statusState, deliveryId?.state, messageId?.state, queuedAt?.state].some(
      (value) => this._hasRealValue(value),
    );

    this.shadowRoot.innerHTML = `
      <ha-card class="${dark}" style="--skickamejl-card-bg: ${background}">
        <div class="card">
          ${this._headerTemplate(backendState)}
          ${
            hasIntegrationEntity
              ? hasLastSend
                ? `
                  <div class="summary">
                    ${this._statusTile(statusState)}
                    ${this._valueTile("mdi:clock-outline", this._t("lastQueuedAt"), this._formatTimestamp(queuedAt?.state), queuedAt?.entity_id)}
                  </div>
                  <div class="details">
                    ${this._copyRow("mdi:identifier", this._t("deliveryId"), deliveryId?.state, deliveryId?.entity_id)}
                    ${this._copyRow("mdi:email-outline", this._t("messageId"), messageId?.state, messageId?.entity_id)}
                  </div>
                  ${this._historyTemplate(status?.attributes)}
                  ${this._config.show_test_form ? this._testFormTemplate() : ""}
                `
                : `
                  ${this._emptyStateTemplate()}
                  ${this._config.show_test_form ? this._testFormTemplate() : ""}
                `
              : this._setupTemplate()
          }
          ${this._noticeTemplate()}
        </div>
      </ha-card>
      ${this._styleTemplate()}
    `;

    this._bindEvents();
  }

  _headerTemplate(backendState) {
    const backendInfo = this._backendInfo(backendState);
    return `
      <div class="header">
        <div class="brand">
          ${
            this._config.show_logo
              ? `<img class="logo" src="${ICON_SRC}" alt="Skickamejl">`
              : `<ha-icon class="fallback-logo" icon="mdi:email-fast-outline"></ha-icon>`
          }
          <div class="brand-copy">
            <div class="brand-name">Skickamejl</div>
            <div class="brand-subtitle">${this._escape(this._t("lastSend"))}</div>
          </div>
        </div>
        <div class="backend ${backendInfo.tone}" title="${this._escape(this._t("backend"))}">
          <ha-icon icon="${backendInfo.icon}"></ha-icon>
          <span>${this._escape(backendInfo.label)}</span>
        </div>
      </div>
    `;
  }

  _statusTile(statusState) {
    const meta = this._statusInfo(statusState);
    return `
      <div class="tile ${meta.tone}">
        <ha-icon icon="${meta.icon}"></ha-icon>
        <div>
          <div class="tile-label">${this._escape(this._t("status"))}</div>
          <div class="tile-value">${this._escape(meta.label)}</div>
        </div>
      </div>
    `;
  }

  _valueTile(icon, label, value, entityId) {
    const display = this._displayValue(value);
    return `
      <div class="tile">
        <ha-icon icon="${icon}"></ha-icon>
        <div>
          <div class="tile-label">${this._escape(label)}</div>
          <div class="tile-value" title="${this._escape(entityId ?? "")}">${this._escape(display)}</div>
        </div>
      </div>
    `;
  }

  _copyRow(icon, label, value, entityId) {
    const display = this._displayValue(value);
    const disabled = this._hasRealValue(value) ? "" : "disabled";
    return `
      <div class="copy-row">
        <ha-icon icon="${icon}"></ha-icon>
        <div class="copy-copy">
          <div class="row-label">${this._escape(label)}</div>
          <div class="row-value" title="${this._escape(entityId ?? "")}">${this._escape(display)}</div>
        </div>
        <button class="icon-button" data-copy="${this._escape(value ?? "")}" title="${this._escape(this._t("copy"))}" ${disabled}>
          <ha-icon icon="mdi:content-copy"></ha-icon>
        </button>
      </div>
    `;
  }

  _historyTemplate(attributes = {}) {
    const events = Array.isArray(attributes.status_events)
      ? attributes.status_events.slice(-4).reverse()
      : [];
    const attemptCount = attributes.attempt_count;
    const lastError = attributes.last_error;
    const hasAttemptCount = this._hasRealValue(attemptCount);
    const hasLastError = this._hasRealValue(lastError);
    if (!events.length && !hasAttemptCount && !hasLastError) {
      return "";
    }

    return `
      <div class="history">
        <div class="history-header">
          <ha-icon icon="mdi:timeline-clock-outline"></ha-icon>
          <span>${this._escape(this._t("deliveryHistory"))}</span>
        </div>
        ${
          hasAttemptCount || hasLastError
            ? `
              <div class="history-meta">
                ${
                  hasAttemptCount
                    ? `<span>${this._escape(this._t("attempts"))}: ${this._escape(attemptCount)}</span>`
                    : ""
                }
                ${
                  hasLastError
                    ? `<span title="${this._escape(lastError)}">${this._escape(this._t("lastError"))}: ${this._escape(lastError)}</span>`
                    : ""
                }
              </div>
            `
            : ""
        }
        ${events.length ? `<div class="timeline">${events.map((event) => this._eventTemplate(event)).join("")}</div>` : ""}
      </div>
    `;
  }

  _eventTemplate(event) {
    const status = this._statusInfo(event.status ?? event.Status);
    const detail =
      event.detail ??
      event.Detail ??
      event.smtpResponse ??
      event.SmtpResponse ??
      event.message ??
      event.Message;
    const timestamp = this._formatTimestamp(event.occurredAtUtc ?? event.OccurredAtUtc);
    return `
      <div class="timeline-event ${status.tone}">
        <ha-icon icon="${status.icon}"></ha-icon>
        <div class="timeline-copy">
          <div class="timeline-title">
            <span>${this._escape(status.label)}</span>
            ${timestamp ? `<time>${this._escape(timestamp)}</time>` : ""}
          </div>
          ${this._hasRealValue(detail) ? `<div class="timeline-detail">${this._escape(detail)}</div>` : ""}
        </div>
      </div>
    `;
  }

  _emptyStateTemplate() {
    return `
      <div class="empty-state">
        <ha-icon icon="mdi:email-fast-outline"></ha-icon>
        <div>
          <div class="empty-title">${this._escape(this._t("noEmailYet"))}</div>
          <div class="empty-text">${this._escape(this._t("noEmailYetDetail"))}</div>
        </div>
      </div>
    `;
  }

  _testFormTemplate() {
    const disabled = this._busy ? "disabled" : "";
    const sendDisabled = this._busy || !this._form.subject.trim() || !this._form.body.trim() ? "disabled" : "";
    const recipientPresets = this._recipientPresets();
    return `
      <form class="test-form">
        <div class="form-header">
          <ha-icon icon="mdi:email-edit-outline"></ha-icon>
          <span>${this._escape(this._t("testEmail"))}</span>
        </div>
        ${
          recipientPresets.length
            ? `
              <label>
                <span>${this._escape(this._t("recipientPreset"))}</span>
                <select class="recipient-preset" ${disabled}>
                  <option value="">${this._escape(this._t("recipientPresetNone"))}</option>
                  ${recipientPresets
                    .map(
                      (preset) => `
                        <option value="${this._escape(preset.email)}" ${this._form.to === preset.email ? "selected" : ""}>
                          ${this._escape(preset.name)}
                        </option>
                      `,
                    )
                    .join("")}
                </select>
              </label>
            `
            : ""
        }
        <div class="field-grid">
          <label>
            <span>${this._escape(this._t("to"))}</span>
            <input class="form-to" type="email" autocomplete="email" value="${this._escape(this._form.to)}" ${disabled}>
          </label>
          <label>
            <span>${this._escape(this._t("from"))}</span>
            <input class="form-from" type="email" value="${this._escape(this._form.from)}" ${disabled}>
          </label>
        </div>
        <label>
          <span>${this._escape(this._t("subject"))}</span>
          <input class="form-subject" value="${this._escape(this._form.subject)}" ${disabled}>
        </label>
        <label>
          <span>${this._escape(this._t("emailBody"))}</span>
          <textarea class="form-body" rows="4" ${disabled}>${this._escape(this._form.body)}</textarea>
        </label>
        <div class="form-actions">
          <button class="secondary clear" type="button" title="${this._escape(this._t("clear"))}" ${disabled}>
            <ha-icon icon="mdi:eraser"></ha-icon>
          </button>
          <button class="primary send" type="submit" ${sendDisabled}>
            <ha-icon icon="${this._busy ? "mdi:loading" : "mdi:send"}"></ha-icon>
            <span>${this._escape(this._t("send"))}</span>
          </button>
        </div>
      </form>
    `;
  }

  _setupTemplate() {
    return `
      <div class="setup">
        <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
        <div>
          <div class="setup-title">${this._escape(this._t("requiresSetup"))}</div>
          <div class="setup-text">${this._escape(CARD_RESOURCE_URL)}</div>
        </div>
      </div>
    `;
  }

  _noticeTemplate() {
    if (!this._notice) {
      return "";
    }
    const icon = this._notice.type === "success" ? "mdi:check-circle-outline" : "mdi:alert-circle-outline";
    return `
      <div class="notice ${this._notice.type}">
        <ha-icon icon="${icon}"></ha-icon>
        <span>${this._escape(this._notice.text)}</span>
      </div>
    `;
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", () => this._copy(button.dataset.copy));
    });
    this.shadowRoot.querySelector(".test-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      this._sendTestEmail();
    });
    this.shadowRoot.querySelector(".clear")?.addEventListener("click", () => {
      this._form = { to: "", from: "", subject: "", body: "" };
      this._notice = undefined;
      this._render();
    });
    this.shadowRoot.querySelector(".recipient-preset")?.addEventListener("change", (event) => {
      this._form.to = event.target.value;
      this._render();
    });
    this.shadowRoot.querySelector(".form-to")?.addEventListener("input", (event) => {
      this._form.to = event.target.value;
    });
    this.shadowRoot.querySelector(".form-from")?.addEventListener("input", (event) => {
      this._form.from = event.target.value;
    });
    this.shadowRoot.querySelector(".form-subject")?.addEventListener("input", (event) => {
      this._form.subject = event.target.value;
      this._render();
    });
    this.shadowRoot.querySelector(".form-body")?.addEventListener("input", (event) => {
      this._form.body = event.target.value;
      this._render();
    });
  }

  _backendInfo(state) {
    if (state === "on") {
      return { icon: "mdi:cloud-check-outline", tone: "good", label: this._t("backendAvailable") };
    }
    if (state === "off") {
      return { icon: "mdi:cloud-alert-outline", tone: "bad", label: this._t("backendUnavailable") };
    }
    return { icon: "mdi:cloud-question-outline", tone: "neutral", label: this._t("backendUnknown") };
  }

  _statusInfo(status) {
    const normalized = String(status ?? "").toLowerCase();
    const meta = STATUS_META[normalized];
    if (meta) {
      return {
        icon: meta.icon,
        tone: meta.tone,
        label: this._t(meta.key),
      };
    }
    return {
      icon: "mdi:email-search-outline",
      tone: "neutral",
      label: this._t("statusUnknown"),
    };
  }

  _formatTimestamp(value) {
    if (!this._hasRealValue(value)) {
      return undefined;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    const locale = this._language() === "sv" ? "sv-SE" : "en";
    return new Intl.DateTimeFormat(locale, {
      dateStyle: "short",
      timeStyle: "short",
    }).format(date);
  }

  _displayValue(value) {
    return this._hasRealValue(value) ? value : this._t("noValue");
  }

  _hasRealValue(value) {
    const text = String(value ?? "").trim().toLowerCase();
    return Boolean(text && !["unknown", "unavailable", "none", "null"].includes(text));
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _escapeCssColor(value) {
    const color = String(value ?? "").trim();
    return /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(color) ? color : DEFAULT_BACKGROUND;
  }

  _styleTemplate() {
    return `
      <style>
        ha-card {
          --skickamejl-good: #12805c;
          --skickamejl-warn: #a15c00;
          --skickamejl-bad: #b42318;
          --skickamejl-line: color-mix(in srgb, var(--divider-color) 72%, transparent);
          --skickamejl-muted: var(--secondary-text-color);
          background: var(--skickamejl-card-bg);
          border-radius: 8px;
          color: var(--primary-text-color);
          overflow: hidden;
        }
        ha-card.dark {
          --skickamejl-line: color-mix(in srgb, var(--divider-color) 55%, transparent);
          background: var(--card-background-color);
        }
        .card {
          display: grid;
          gap: 14px;
          padding: 16px;
        }
        .header,
        .brand,
        .backend,
        .tile,
        .copy-row,
        .form-header,
        .form-actions,
        .notice,
        .empty-state,
        .setup {
          align-items: center;
          display: flex;
        }
        .header {
          justify-content: space-between;
          gap: 12px;
        }
        .brand {
          min-width: 0;
          gap: 10px;
        }
        .logo,
        .fallback-logo {
          flex: 0 0 38px;
          height: 38px;
          width: 38px;
        }
        .logo {
          object-fit: contain;
        }
        .fallback-logo {
          color: #0078b8;
        }
        .brand-copy {
          min-width: 0;
        }
        .brand-name {
          font-size: 18px;
          font-weight: 800;
          line-height: 1.15;
        }
        .brand-subtitle,
        .tile-label,
        .row-label,
        label span,
        .setup-text {
          color: var(--skickamejl-muted);
          font-size: 12px;
        }
        .backend {
          border: 1px solid var(--skickamejl-line);
          border-radius: 8px;
          flex: 0 0 auto;
          gap: 6px;
          min-height: 34px;
          padding: 0 10px;
        }
        .backend.good,
        .tile.good {
          color: var(--skickamejl-good);
        }
        .backend.bad,
        .tile.bad {
          color: var(--skickamejl-bad);
        }
        .backend.neutral,
        .tile.neutral {
          color: var(--skickamejl-muted);
        }
        .summary {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .tile {
          border: 1px solid var(--skickamejl-line);
          border-radius: 8px;
          gap: 10px;
          min-height: 64px;
          min-width: 0;
          padding: 10px;
        }
        .tile ha-icon {
          flex: 0 0 auto;
        }
        .tile-value,
        .row-value {
          color: var(--primary-text-color);
          line-height: 1.3;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .tile-value {
          font-size: 15px;
          font-weight: 700;
        }
        .details,
        .history,
        .test-form {
          display: grid;
          gap: 8px;
        }
        .copy-row {
          border-top: 1px solid var(--skickamejl-line);
          gap: 10px;
          min-height: 42px;
          padding-top: 8px;
        }
        .copy-copy {
          min-width: 0;
        }
        .empty-state {
          border: 1px solid var(--skickamejl-line);
          border-radius: 8px;
          gap: 10px;
          padding: 12px;
        }
        .empty-state ha-icon {
          color: #0078b8;
          flex: 0 0 auto;
        }
        .empty-title {
          font-weight: 800;
        }
        .empty-text {
          color: var(--skickamejl-muted);
          font-size: 12px;
          line-height: 1.35;
        }
        .history {
          border-top: 1px solid var(--skickamejl-line);
          padding-top: 10px;
        }
        .history-header,
        .history-meta,
        .timeline-event,
        .timeline-title {
          align-items: center;
          display: flex;
        }
        .history-header {
          gap: 8px;
          font-weight: 800;
        }
        .history-meta {
          color: var(--skickamejl-muted);
          flex-wrap: wrap;
          font-size: 12px;
          gap: 6px 12px;
          min-width: 0;
        }
        .history-meta span {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .timeline {
          display: grid;
          gap: 6px;
        }
        .timeline-event {
          gap: 8px;
          min-width: 0;
        }
        .timeline-event.good {
          color: var(--skickamejl-good);
        }
        .timeline-event.warn {
          color: var(--skickamejl-warn);
        }
        .timeline-event.bad {
          color: var(--skickamejl-bad);
        }
        .timeline-event.neutral {
          color: var(--skickamejl-muted);
        }
        .timeline-event ha-icon {
          flex: 0 0 auto;
          --mdc-icon-size: 20px;
        }
        .timeline-copy {
          min-width: 0;
          width: 100%;
        }
        .timeline-title {
          color: var(--primary-text-color);
          gap: 8px;
          justify-content: space-between;
          min-width: 0;
        }
        .timeline-title span,
        .timeline-title time,
        .timeline-detail {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .timeline-title span {
          font-weight: 700;
        }
        .timeline-title time,
        .timeline-detail {
          color: var(--skickamejl-muted);
          font-size: 12px;
        }
        button {
          align-items: center;
          background: transparent;
          border: 0;
          border-radius: 8px;
          color: inherit;
          cursor: pointer;
          display: inline-flex;
          font: inherit;
          justify-content: center;
          min-height: 36px;
        }
        button:disabled {
          cursor: default;
          opacity: 0.48;
        }
        .icon-button {
          flex: 0 0 36px;
          margin-left: auto;
          width: 36px;
        }
        .icon-button:not(:disabled):hover,
        .secondary:not(:disabled):hover {
          background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
        }
        .test-form {
          border-top: 1px solid var(--skickamejl-line);
          padding-top: 10px;
        }
        .form-header {
          gap: 8px;
          font-weight: 800;
        }
        .field-grid {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        label {
          display: grid;
          gap: 4px;
          min-width: 0;
        }
        input,
        textarea,
        select {
          background: var(--card-background-color);
          border: 1px solid var(--skickamejl-line);
          border-radius: 8px;
          box-sizing: border-box;
          color: var(--primary-text-color);
          font: inherit;
          min-height: 38px;
          padding: 8px 10px;
          width: 100%;
        }
        textarea {
          min-height: 96px;
          resize: vertical;
        }
        .form-actions {
          justify-content: flex-end;
          gap: 8px;
        }
        .secondary {
          border: 1px solid var(--skickamejl-line);
          width: 38px;
        }
        .primary {
          background: #0078b8;
          color: #fff;
          gap: 8px;
          min-width: 108px;
          padding: 0 14px;
        }
        .primary ha-icon[icon="mdi:loading"] {
          animation: skickamejl-spin 1s linear infinite;
        }
        .notice {
          border-radius: 8px;
          gap: 8px;
          min-height: 36px;
          padding: 0 10px;
        }
        .notice.success {
          background: color-mix(in srgb, var(--skickamejl-good) 12%, transparent);
          color: var(--skickamejl-good);
        }
        .notice.error {
          background: color-mix(in srgb, var(--skickamejl-bad) 12%, transparent);
          color: var(--skickamejl-bad);
        }
        .setup {
          border: 1px solid var(--skickamejl-line);
          border-radius: 8px;
          gap: 10px;
          padding: 12px;
        }
        .setup ha-icon {
          color: var(--skickamejl-warn);
          flex: 0 0 auto;
        }
        .setup-title {
          font-weight: 800;
        }
        @media (max-width: 420px) {
          .summary,
          .field-grid {
            grid-template-columns: 1fr;
          }
          .backend span {
            display: none;
          }
        }
        @keyframes skickamejl-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      </style>
    `;
  }
}

class SkickamejlCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      preferred_language: "auto",
      theme_mode: "auto",
      background_color: DEFAULT_BACKGROUND,
      show_logo: true,
      show_test_form: true,
      recipient_presets: [],
      ...config,
      preferred_language: normalizeLanguageMode(config.preferred_language),
      theme_mode: normalizeThemeMode(config.theme_mode, config.dark_mode),
      recipient_presets: normalizeRecipientPresets(config.recipient_presets),
    };
    delete this._config.dark_mode;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _language() {
    return languageFromHass(this._hass, this._config?.preferred_language);
  }

  _t(key) {
    return localize(this._language(), key);
  }

  _updateConfig(patch) {
    this._config = { ...this._config, ...patch };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
    this._render();
  }

  _render() {
    if (!this.shadowRoot || !this._config) {
      return;
    }
    const entities = findSkickamejlEntities(this._hass, this._config);
    const languageMode = normalizeLanguageMode(this._config.preferred_language);
    const themeMode = normalizeThemeMode(this._config.theme_mode, this._config.dark_mode);
    this.shadowRoot.innerHTML = `
      <div class="editor">
        ${this._entityInput("backend_entity", this._t("backendEntity"), entities.backend)}
        ${this._entityInput("status_entity", this._t("statusEntity"), entities.status)}
        ${this._entityInput("delivery_id_entity", this._t("deliveryIdEntity"), entities.deliveryId)}
        ${this._entityInput("message_id_entity", this._t("messageIdEntity"), entities.messageId)}
        ${this._entityInput("queued_at_entity", this._t("lastQueuedAtEntity"), entities.queuedAt)}
        <label>
          <span>${this._escape(this._t("background"))}</span>
          <input class="background" type="color" value="${this._escape(this._config.background_color ?? DEFAULT_BACKGROUND)}">
        </label>
        <label>
          <span>${this._escape(this._t("language"))}</span>
          <select class="preferred-language">
            <option value="auto" ${languageMode === "auto" ? "selected" : ""}>${this._escape(this._t("languageAuto"))}</option>
            <option value="sv" ${languageMode === "sv" ? "selected" : ""}>${this._escape(this._t("languageSwedish"))}</option>
            <option value="en" ${languageMode === "en" ? "selected" : ""}>${this._escape(this._t("languageEnglish"))}</option>
          </select>
        </label>
        <fieldset>
          <legend>${this._escape(this._t("theme"))}</legend>
          ${THEME_MODES.map(
            (mode) => `
              <label class="radio">
                <input class="theme-mode" type="radio" name="theme-mode" value="${mode}" ${themeMode === mode ? "checked" : ""}>
                <span>${this._escape(this._t(`theme${mode[0].toUpperCase()}${mode.slice(1)}`))}</span>
              </label>
            `,
          ).join("")}
        </fieldset>
        <label class="toggle">
          <span>${this._escape(this._t("showLogo"))}</span>
          <input class="show-logo" type="checkbox" ${this._config.show_logo ? "checked" : ""}>
        </label>
        <label class="toggle">
          <span>${this._escape(this._t("showTestForm"))}</span>
          <input class="show-test-form" type="checkbox" ${this._config.show_test_form ? "checked" : ""}>
        </label>
      </div>
      <style>
        .editor {
          display: grid;
          gap: 12px;
          padding: 12px;
        }
        label {
          display: grid;
          gap: 5px;
          min-width: 0;
        }
        .toggle,
        .radio {
          align-items: center;
          display: flex;
          gap: 8px;
          justify-content: space-between;
        }
        .radio {
          justify-content: flex-start;
        }
        span,
        legend {
          color: var(--secondary-text-color);
          font-size: 12px;
        }
        fieldset {
          border: 0;
          display: grid;
          gap: 8px;
          margin: 0;
          padding: 0;
        }
        input,
        select {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          color: var(--primary-text-color);
          font: inherit;
          min-height: 36px;
          padding: 0 8px;
        }
        input[type="color"],
        input[type="checkbox"],
        input[type="radio"] {
          min-height: auto;
          padding: 0;
        }
      </style>
    `;
    this._bindEvents();
  }

  _entityInput(configKey, label, detectedEntity) {
    const value = this._config[configKey] ?? detectedEntity ?? "";
    return `
      <label>
        <span>${this._escape(label)}</span>
        <input data-config-key="${configKey}" value="${this._escape(value)}">
      </label>
    `;
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll("[data-config-key]").forEach((input) => {
      input.addEventListener("change", (event) => {
        const key = event.target.dataset.configKey;
        this._updateConfig({ [key]: event.target.value.trim() || undefined });
      });
    });
    this.shadowRoot.querySelector(".background")?.addEventListener("input", (event) => {
      this._updateConfig({ background_color: event.target.value });
    });
    this.shadowRoot.querySelector(".preferred-language")?.addEventListener("change", (event) => {
      this._updateConfig({ preferred_language: normalizeLanguageMode(event.target.value) });
    });
    this.shadowRoot.querySelectorAll(".theme-mode").forEach((input) => {
      input.addEventListener("change", (event) => {
        if (event.target.checked) {
          this._updateConfig({ theme_mode: event.target.value });
        }
      });
    });
    this.shadowRoot.querySelector(".show-logo")?.addEventListener("change", (event) => {
      this._updateConfig({ show_logo: event.target.checked });
    });
    this.shadowRoot.querySelector(".show-test-form")?.addEventListener("change", (event) => {
      this._updateConfig({ show_test_form: event.target.checked });
    });
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
}

customElements.define("skickamejl-card", SkickamejlCard);
customElements.define("skickamejl-card-editor", SkickamejlCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "skickamejl-card",
  name: "Skickamejl Card",
  description: "Show Skickamejl backend status and last email delivery details.",
  documentationURL: "https://github.com/MRCCollective/home-assistant-skickamejl",
  image: ICON_SRC,
  logo: ICON_SRC,
  preview: true,
  getEntitySuggestion: (hass, entityId) => {
    if (!isSkickamejlEntity(hass, entityId)) {
      return null;
    }
    return {
      config: SkickamejlCard.getStubConfig(hass),
    };
  },
});
