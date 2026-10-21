<h1 align="center">Skickamejl for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/MRCCollective/home-assistant-skickamejl/releases">
    <img src="https://img.shields.io/github/v/release/MRCCollective/home-assistant-skickamejl?style=for-the-badge" alt="Release">
  </a>
  <a href="https://github.com/MRCCollective/home-assistant-skickamejl/actions/workflows/hacs.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/MRCCollective/home-assistant-skickamejl/hacs.yml?branch=main&label=HACS&style=for-the-badge" alt="HACS Validation">
  </a>
  <a href="https://github.com/MRCCollective/home-assistant-skickamejl/actions/workflows/hassfest.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/MRCCollective/home-assistant-skickamejl/hassfest.yml?branch=main&label=hassfest&style=for-the-badge" alt="Home Assistant Validation">
  </a>
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS Custom">
  </a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/MRCCollective/home-assistant-skickamejl/main/custom_components/skickamejl/brand/logo_readme.png" alt="Skickamejl logo" width="720">
</p>

Custom Home Assistant integration for [Skickamejl](https://skickamejl.se), focused on monitoring transactional email activity in Home Assistant and optionally sending email notifications from automations.

This repository can be installed as a HACS custom repository and has been submitted for inclusion in the default HACS repository.

## Features

- UI config flow for backend URL, server API-token, sender address, and default recipient, with automatic server identity and name detection
- Options flow for changing backend URL, server API-token, sender address, and default recipient without deleting the integration
- Native Home Assistant `notify` entity for automation-friendly email notifications
- Home Assistant action `skickamejl.send_email` for dynamic recipients, senders, text bodies, and HTML bodies
- Incoming webhook for Skickamejl email events, including template IDs
- Home Assistant event `skickamejl_email_event` for automations triggered by Skickamejl activity
- Diagnostic entities for backend availability, the latest delivery, and the latest webhook event
- Delivery-detail polling every 60 seconds after each HA send or webhook event with a delivery ID until Skickamejl reports a final outcome
- Multiple Skickamejl servers as separate config entries, each with its own API token, notify entity, diagnostics, webhook, and card routing
- Custom Lovelace card with localized Swedish/English UI, server name, status overview, delivery history, and an optional test-email form
- Sends `title` as the email subject and `message` as the plain-text email body
- Authenticated server identity and connection validation during setup
- Diagnostics with server API-token and email addresses redacted
- HACS, Ruff, MyPy, HACS validation, and hassfest workflow files
- Skickamejl brand assets included for HACS and the integration directory

## Installation Through HACS Custom Repository

1. Open HACS in Home Assistant.
2. Go to **Integrations** / **Integrationer**.
3. Choose **Custom repositories** / **Anpassade arkiv** from the menu.
4. Add:

   ```text
   https://github.com/MRCCollective/home-assistant-skickamejl
   ```

5. Select category **Integration** / **Integration**.
6. Install **Skickamejl**.
7. Restart Home Assistant.
8. In Home Assistant, add the **Skickamejl** integration from **Settings -> Devices & services -> Add integration**.

## Add Skickamejl

In Home Assistant, go to **Settings -> Devices & services -> Add integration** and search for **Skickamejl**.

Enter:

- Backend URL, for example `https://skickamejl.se`
- Server API-token from the selected Skickamejl server
- Sender email address, for example `home@example.com`
- Default recipient email address, for example `you@example.com`

The config flow sends the token to `GET /api/server`. Skickamejl returns the stable server ID and current server name associated with that token. Home Assistant uses the ID to prevent duplicate setup and uses the name for the config entry, device, entities, action selector, and dashboard card. The API token is never shown in entity state.

After setup, `GET /api/status` is used for the recurring availability check. The server API-token is sent as `X-Api-Key` when Home Assistant sends an email through `POST /api/messages`.

Use the **Server API-token** shown on the Skickamejl server settings page. Account API tokens that start with `skm_account_` are for account-management API calls and cannot send messages through `POST /api/messages`.

After setup, open **Settings -> Devices & services -> Skickamejl -> Configure** to update the backend URL, server API-token, sender address, or default recipient without removing and re-adding the integration.

### Multiple Skickamejl servers

Add the integration once for every Skickamejl server/API token. Home Assistant automatically gives each entry the name returned by Skickamejl. A setup can therefore contain entries such as **Production**, **Development**, and **Customer A** even when all of them use `https://skickamejl.se`.

Each entry is isolated: sends, default addresses, delivery sensors, webhook events, and test emails use that entry's API token. Advanced send actions require an explicit server selection, so adding another entry cannot silently change an existing automation's destination.

## Notification Entity

The integration creates one notify entity per configured Skickamejl server. Home Assistant commonly names the first one:

```text
notify.skickamejl
```

If Home Assistant assigns a different entity ID, use the entity ID shown under **Settings -> Devices & services -> Entities**.

With multiple servers, select the corresponding notify entity in each automation, for example `notify.production` or `notify.development`. Entity IDs are assigned by Home Assistant and may differ from these examples.

## Entities

Binary sensor:

- `binary_sensor.skickamejl_backend_available`

Sensors:

- `sensor.skickamejl_last_delivery_status`
- `sensor.skickamejl_last_delivery_id`
- `sensor.skickamejl_last_message_id`
- `sensor.skickamejl_last_queued_at`
- `sensor.skickamejl_last_event_type`
- `sensor.skickamejl_last_template_id`
- `sensor.skickamejl_last_webhook_delivery_id`
- `sensor.skickamejl_last_webhook_received_at`

The backend availability sensor checks `GET /api/status` every 60 seconds. The latest delivery sensors update when Home Assistant sends an email through either `notify.send_message` or `skickamejl.send_email`, and also when Skickamejl posts an incoming webhook event with delivery metadata. The webhook URL is shown only in the integration's administrator-only **Configure** dialog, not in an entity state or attributes.

When a send response includes a `deliveryId`, the integration stores it and polls the Skickamejl detail endpoint every 60 seconds:

```text
GET /api/messages/{deliveryId}
```

Polling stops when the status becomes `delivered`, `bounced`, or `failed`, or when a newer email replaces the last delivery ID. Detail responses can add attributes such as attempt count, last error, attempts, and status events to the last-send sensors.

Delivery status values follow the Skickamejl backend response:

- `queued`
- `processing`
- `delivered`
- `deferred`
- `bounced`
- `failed`

## Incoming Skickamejl Webhooks

Use this when another app or skickamejl.se sends transactional email and Home Assistant should react to it.

1. Add the Skickamejl integration.
2. As a Home Assistant administrator, open **Settings -> Devices & services -> Skickamejl -> Configure** for the server you added.
3. Copy the webhook URL shown in that dialog into Skickamejl's webhook/event callback settings. You can reopen **Configure** whenever you need the URL again.

When Home Assistant Cloud/Nabu Casa is active, the integration creates a cloudhook and shows that public URL in **Configure**. Otherwise it shows Home Assistant's configured URL, which may be local and work only from the same network. If no URL is available, configure an internal or external Home Assistant URL first. The webhook URL contains a long random ID and should be treated like a secret. Do not put it in dashboards, entity states, or automation traces.

Skickamejl should send a JSON `POST` to that URL. The integration accepts both camelCase and snake_case fields:

```json
{
  "event": "email.sent",
  "templateId": "account-created",
  "deliveryId": "delivery_123",
  "emailMessageId": "email_123",
  "messageId": "message_123",
  "to": "new.user@example.com",
  "from": "noreply@example.com",
  "status": "queued",
  "occurredAtUtc": "2026-08-03T13:00:00Z"
}
```

Each accepted webhook fires a Home Assistant event:

```text
skickamejl_email_event
```

The event data includes normalized fields such as `event`, `template_id`, `delivery_id`, `message_id`, `recipient_address`, `sender_address`, `status`, `occurred_at_utc`, and `received_at_utc`. The original payload is also available as `payload`.

Trigger on a specific transactional template:

```yaml
alias: When account-created email is sent
triggers:
  - trigger: event
    event_type: skickamejl_email_event
conditions:
  - condition: template
    value_template: >
      {{ trigger.event.data.template_id == 'account-created'
         and trigger.event.data.event == 'email.sent' }}
actions:
  - action: persistent_notification.create
    data:
      title: "Skickamejl"
      message: "Account-created email was sent to {{ trigger.event.data.recipient_address }}."
```

## Dashboard Card

This repository includes brand assets under `brand/` for HACS and an optional custom Lovelace card under the repository `www/` folder. HACS installs an integration-served copy of the card under `custom_components/skickamejl/www/`.

Register the card resource:

```text
/skickamejl_static/skickamejl-card.js?v=0.5.2
```

Use resource type:

```text
JavaScript Module
```

Then add a manual dashboard card:

```yaml
type: custom:skickamejl-card
```

The card auto-detects the Skickamejl backend availability entity and latest delivery sensors. It shows the API-detected server name, backend status, last delivery status, queued time, delivery ID, message ID, and delivery history from status events. When multiple servers exist, automatic detection pins all status entities and test sends to the same config entry as the selected backend entity.

You can also pin exact entity IDs:

```yaml
type: custom:skickamejl-card
backend_entity: binary_sensor.skickamejl_backend_available
status_entity: sensor.skickamejl_last_delivery_status
delivery_id_entity: sensor.skickamejl_last_delivery_id
message_id_entity: sensor.skickamejl_last_message_id
queued_at_entity: sensor.skickamejl_last_queued_at
preferred_language: auto
theme_mode: auto
show_logo: true
show_test_form: true
```

The visual editor supports preferred language (automatic from the Home Assistant user language, Swedish, or English), theme mode, background color, logo visibility, entity overrides, and an optional test-email form. Enable **Show test email form** in the card editor, or set `show_test_form: true` in YAML.

The test form provides recipient, subject, and plain-text message fields. Leave the recipient blank to use the configured default recipient. The button is disabled while sending and the card displays queued/error feedback. It always sends through the config entry associated with the selected backend entity; no API token is stored in the card configuration.

Before the first delivery has been recorded, the card shows a compact empty state instead of empty delivery IDs. After the first webhook or HA-initiated send, it switches to the status, IDs, and delivery history view.

When updating the card during development, copy the changed files from `www/` to `custom_components/skickamejl/www/` and reload the browser. If Home Assistant keeps an old cached card, add or change a cache-busting query string on the resource, for example:

```text
/skickamejl_static/skickamejl-card.js?v=dev
```

## Services

### Send an email

Use `skickamejl.send_email` when an automation needs more control than the native notify entity.

In the visual automation editor, choose **Skickamejl: Send email** and select the server by its Skickamejl name. The selector stores Home Assistant's config-entry ID in YAML.

```yaml
action: skickamejl.send_email
data:
  config_entry_id: "01J..."
  to: "family@example.com"
  from: "home@example.com"
  subject: "Dagens husrapport"
  text_body: |
    Temperatur: {{ states('sensor.living_room_temperature') }} °C
    Luftfuktighet: {{ states('sensor.bathroom_humidity') }} %
```

`subject` is required. At least one of `text_body` or `html_body` is required. `to` and `from` are optional; when omitted, the integration uses the default recipient and sender from the config entry.

`config_entry_id` is required. Select it through the visual action editor whenever possible; the opaque values in these examples are placeholders. Requiring the server means adding another Skickamejl entry can never silently change where an email is sent.

```yaml
action: skickamejl.send_email
data:
  config_entry_id: "01J..."
  to: "ops@example.com"
  subject: "Vattenläcka"
  text_body: "Vatten upptäcktes vid tvättmaskinen."
```

HTML email is supported by passing `html_body`:

```yaml
action: skickamejl.send_email
data:
  config_entry_id: "01J..."
  subject: "Kvällsrapport"
  text_body: "Ytterdörren är låst och alla lampor är släckta."
  html_body: "<p>Ytterdörren är <strong>låst</strong> och alla lampor är släckta.</p>"
```

## Automation Examples

Send an alarm email when a binary sensor turns on:

```yaml
alias: Email when hallway motion is detected
triggers:
  - trigger: state
    entity_id: binary_sensor.hallway_motion
    to: "on"
actions:
  - action: notify.send_message
    target:
      entity_id: notify.skickamejl
    data:
      title: "Larm utlöst"
      message: "Rörelse upptäcktes i hallen."
```

Send a daily house summary:

```yaml
alias: Daily house email
triggers:
  - trigger: time
    at: "07:30:00"
actions:
  - action: notify.send_message
    target:
      entity_id: notify.skickamejl
    data:
      title: "Dagens husrapport"
      message: |
        Temperatur: {{ states('sensor.living_room_temperature') }} °C
        Luftfuktighet: {{ states('sensor.bathroom_humidity') }} %
        Ytterdörr: {{ states('binary_sensor.front_door') }}
```

Notify your phone if the latest Skickamejl delivery fails:

```yaml
alias: Notify when Skickamejl email failed
triggers:
  - trigger: state
    entity_id: sensor.skickamejl_last_delivery_status
    to: "failed"
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Skickamejl could not deliver the latest tracked email."
```

## Try It For Real Checklist

1. Confirm `binary_sensor.skickamejl_backend_available` is `on`.
2. As an administrator, open **Settings -> Devices & services -> Skickamejl -> Configure** and copy the webhook URL into Skickamejl webhook settings.
3. Trigger a transactional email from your app or skickamejl.se.
4. Watch `sensor.skickamejl_last_template_id` and `sensor.skickamejl_last_delivery_status` update.
5. Open the card and confirm delivery ID, message ID, and delivery history appear.
6. Enable **Show test email form** in the card editor, send a test, and confirm that queued/error feedback appears.
7. If multiple servers are configured, add one card for each backend entity and confirm every card shows the correct server name and delivery information.
8. Build a `skickamejl.send_email` action in the visual editor and confirm the server appears as a named selector rather than a raw text field.
9. Change one setting from **Settings -> Devices & services -> Skickamejl -> Configure** and confirm the integration reloads cleanly.

## Current Scope

This version supports automatic server identity/name discovery, multiple isolated Skickamejl servers, incoming webhooks, Home Assistant event triggers, native notify emails, a server-selectable `skickamejl.send_email` action, backend health, options flow, delivery-detail polling, last-delivery diagnostics, and a dashboard card with delivery history and optional test sends. Attachments are not currently supported.

## Development

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run local checks:

```bash
ruff check .
ruff format --check .
mypy custom_components/skickamejl
pytest
node --check www/skickamejl-card.js
```

Home Assistant and HACS validation run in GitHub Actions using hassfest and `hacs/action`. The test workflow runs Ruff, MyPy, and pytest.
