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

Custom Home Assistant integration for [Skickamejl](https://skickamejl.se), focused first on sending email notifications from automations through the Skickamejl email API.

This repository is prepared for HACS as a custom integration. It is not submitted to the default HACS repository yet.

## Features

- UI config flow for Skickamejl backend URL, server API-token, sender address, and default recipient
- Options flow for changing backend URL, server API-token, sender address, and default recipient without deleting the integration
- Native Home Assistant `notify` entity for automation-friendly email notifications
- Home Assistant action `skickamejl.send_email` for dynamic recipients, senders, text bodies, and HTML bodies
- Diagnostic entities for backend availability and the last email sent from Home Assistant
- Delivery-detail polling every 60 seconds after each send until Skickamejl reports a final outcome
- Custom Lovelace card with localized Swedish/English UI, icons, status overview, delivery history, recipient presets, and a test-send form
- Sends `title` as the email subject and `message` as the plain-text email body
- Health-check validation against the configured backend during setup
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

The config flow validates that the backend can be reached through `GET /api/status`. The server API-token is sent as `X-Api-Key` when Home Assistant sends an email through `POST /api/messages`.

Use the **Server API-token** shown on the Skickamejl server settings page. Account API tokens that start with `skm_account_` are for account-management API calls and cannot send messages through `POST /api/messages`.

After setup, open **Settings -> Devices & services -> Skickamejl -> Configure** to update the backend URL, server API-token, sender address, or default recipient without removing and re-adding the integration.

## Notification Entity

The integration creates one notify entity per config entry. Home Assistant commonly names the first one:

```text
notify.skickamejl
```

If Home Assistant assigns a different entity ID, use the entity ID shown under **Settings -> Devices & services -> Entities**.

## Entities

Binary sensor:

- `binary_sensor.skickamejl_backend_available`

Sensors:

- `sensor.skickamejl_last_delivery_status`
- `sensor.skickamejl_last_delivery_id`
- `sensor.skickamejl_last_message_id`
- `sensor.skickamejl_last_queued_at`

The backend availability sensor checks `GET /api/status` every 60 seconds. The last-send sensors update when Home Assistant successfully sends an email through either `notify.send_message` or `skickamejl.send_email`.

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

## Dashboard Card

This repository includes brand assets under `brand/` for HACS and an optional custom Lovelace card under the repository `www/` folder. HACS installs an integration-served copy of the card under `custom_components/skickamejl/www/`.

Register the card resource:

```text
/skickamejl_static/skickamejl-card.js?v=0.3.4
```

Use resource type:

```text
JavaScript Module
```

Then add a manual dashboard card:

```yaml
type: custom:skickamejl-card
```

The card auto-detects the Skickamejl backend availability entity and last-send sensors. It shows backend status, last delivery status, queued time, delivery ID, message ID, delivery history from status events, and an optional test-send form that calls `skickamejl.send_email`.

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
recipient_presets:
  - name: Test user
    email: you@example.com
  - name: Developer inbox
    email: dev@example.com
```

The visual editor supports preferred language (automatic from the Home Assistant user language, Swedish, or English), theme mode, background color, logo visibility, test-form visibility, and entity overrides. Test recipients are configured in YAML and appear as a dropdown that fills the `to` field while still allowing any recipient address. This is only for the optional dashboard test form; normal transactional email recipients are supplied by your automations or `notify` calls. The card uses icon buttons for copying IDs and sending/clearing the test form.

Before the first email has been sent, the card shows a compact empty state instead of empty delivery IDs. After the first send, it switches to the status, IDs, and delivery history view.

When updating the card during development, copy the changed files from `www/` to `custom_components/skickamejl/www/` and reload the browser. If Home Assistant keeps an old cached card, add or change a cache-busting query string on the resource, for example:

```text
/skickamejl_static/skickamejl-card.js?v=dev
```

## Services

### Send an email

Use `skickamejl.send_email` when an automation needs more control than the native notify entity.

```yaml
action: skickamejl.send_email
data:
  to: "family@example.com"
  from: "home@example.com"
  subject: "Dagens husrapport"
  text_body: |
    Temperatur: {{ states('sensor.living_room_temperature') }} °C
    Luftfuktighet: {{ states('sensor.bathroom_humidity') }} %
```

`subject` is required. At least one of `text_body` or `html_body` is required. `to` and `from` are optional; when omitted, the integration uses the default recipient and sender from the config entry.

If you configure multiple Skickamejl entries, include `entry_id` in service calls.

```yaml
action: skickamejl.send_email
data:
  entry_id: "01J..."
  to: "ops@example.com"
  subject: "Vattenläcka"
  text_body: "Vatten upptäcktes vid tvättmaskinen."
```

HTML email is supported by passing `html_body`:

```yaml
action: skickamejl.send_email
data:
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
      message: "Skickamejl could not deliver the last Home Assistant email."
```

## Try It For Real Checklist

1. Confirm `binary_sensor.skickamejl_backend_available` is `on`.
2. Send a test email from the Skickamejl card.
3. Watch `sensor.skickamejl_last_delivery_status` move from `queued` or `processing` to a final state.
4. Open the card and confirm delivery ID, message ID, and delivery history appear.
5. Change one setting from **Settings -> Devices & services -> Skickamejl -> Configure** and confirm the integration reloads cleanly.

## Current Scope

This version supports native notify emails, a richer `skickamejl.send_email` action, backend health, options flow, delivery-detail polling, last-send diagnostics, and a dashboard card with delivery history and recipient presets. Attachments can be added later once the core send and status flows are working smoothly.

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
