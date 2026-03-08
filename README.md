# E.ON Energy — Home Assistant Integration

Custom HACS integration for [E.ON Energy](https://eonenergy.com) (UK) that surfaces energy consumption data as Home Assistant sensors.

> **Note:** This is E.ON Energy (eonenergy.com), not E.ON Next — different backend.

## Features

- Electricity consumption today & yesterday (kWh)
- Gas consumption today & yesterday (kWh)
- Hourly polling via the E.ON Energy API
- Auth0-based refresh token authentication with automatic token renewal

## Installation via HACS

1. Add this repo as a custom HACS repository (Integration type)
2. Install **E.ON Energy**
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → E.ON Energy**
5. Follow the steps below to obtain a refresh token

## Getting a refresh token

E.ON Energy uses Auth0 with PKCE (not username/password). You need to copy a refresh token from your browser after logging in:

1. Open **Chrome** or **Firefox** and navigate to [www.eonenergy.com](https://www.eonenergy.com)
2. Open **DevTools** (F12) and switch to the **Network** tab
3. Log in with your E.ON Energy email and password
4. In the Network tab, filter by `oauth/token`
5. Find the **POST** request to `auth.eonenergy.com` — click it
6. Open the **Response** sub-tab
7. Copy the full value of **`refresh_token`** from the JSON

Paste this value into the HA config flow. The integration will use it to generate access tokens automatically and will persist updated tokens as they rotate.

When the refresh token eventually expires (typically after months of inactivity), HA will prompt you to re-authenticate — just repeat the steps above.

## Sensors

| Entity | Class | Unit |
|---|---|---|
| E.ON Electricity Today | energy | kWh |
| E.ON Electricity Yesterday | energy | kWh |
| E.ON Gas Today | energy | kWh |
| E.ON Gas Yesterday | energy | kWh |
| E.ON Account Number | diagnostic | — |

## Notes

- The consumption API response schema is inferred from reverse-engineered traffic and may need adjusting on first run. Check HA logs for the raw API response under `DEBUG` by adding `logger: logs: custom_components.eon_energy: debug` to your `configuration.yaml`.
- Auth0 PKCE does not return a JWT access_token unless an API audience is registered. The integration automatically falls back to using the `id_token` as Bearer if the access_token is opaque.
