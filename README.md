# E.ON Energy — Home Assistant Integration

Custom HACS integration for [E.ON Energy](https://eonenergy.com) (UK) that surfaces energy consumption data as Home Assistant sensors.

> **Note:** This is E.ON Energy (eonenergy.com), not E.ON Next — different backend.

## Features

- Electricity consumption today & yesterday (kWh)
- Gas consumption today & yesterday (kWh)
- Hourly polling via the E.ON Energy API
- Auth0-based login with automatic token refresh
- Re-authentication flow when credentials expire

## Installation via HACS

1. Add this repo as a custom HACS repository (Integration type)
2. Install **E.ON Energy**
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → E.ON Energy**
5. Enter your eonenergy.com email and password

## Sensors

| Entity | Class | Unit |
|---|---|---|
| E.ON Electricity Today | energy | kWh |
| E.ON Electricity Yesterday | energy | kWh |
| E.ON Gas Today | energy | kWh |
| E.ON Gas Yesterday | energy | kWh |
| E.ON Account Number | diagnostic | — |

## Notes

- The consumption API response schema is inferred from reverse-engineered traffic and may need adjusting on first run. Check HA logs for the raw API response under `DEBUG`.
- Auth0 ROPC grant (`grant_type=password`) must be enabled on the E.ON tenant. If login fails with 401, check the HA log for the Auth0 error detail.
