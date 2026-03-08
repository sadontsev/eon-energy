# E.ON Energy — Home Assistant Integration

Custom HACS integration for [E.ON Energy](https://eonenergy.com) (UK) heat pump accounts. Surfaces monthly heating energy consumption and cost as Home Assistant sensors.

> **Note:** This is E.ON Energy (eonenergy.com), not E.ON Next — different backend and billing system.

## Features

- Heating energy for the current billing period (kWh)
- Heating cost for the current billing period (GBP)
- Heating energy for the previous billing period (kWh)
- Heating cost for the previous billing period (GBP)
- Monthly data fetch on a user-configured day — no unnecessary API calls or auth errors in between

## How authentication works

E.ON Energy uses Auth0 with PKCE and Cloudflare Turnstile captcha, which makes headless (automated) login impossible. Instead, you paste a short-lived token from your browser once. Because tokens expire in ~10 hours, the integration only contacts the API on one configured day per month — all other days it serves cached data silently without needing a valid token.

## Installation via HACS

1. Add this repo as a custom HACS repository (Integration type)
2. Install **E.ON Energy** and restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → E.ON Energy**
4. Follow the steps below

## Getting a token

You need to provide a token each time HA prompts you to re-authenticate (once per month, on the fetch day):

1. Open **Chrome** and go to [www.eonenergy.com](https://www.eonenergy.com) — log in
2. Open **DevTools** (F12) → **Application** tab → **Local Storage** → `https://www.eonenergy.com`
3. Find the key starting with `@@auth0spajs@@`
4. Copy its full JSON value
5. Paste it into the HA token field

Alternatively, paste just the `id_token` JWT string directly.

## Fetch day

During setup you choose a **day of month** (1–28) on which the integration calls the E.ON API to pull updated consumption data. On all other days it returns the last cached reading without any network calls or authentication checks.

**Recommended:** choose a day 5–10 days after the end of the month, once your billing period has closed and the data is finalised (e.g. day 8). On that day HA will prompt you to re-authenticate if your token has expired — log into eonenergy.com, copy the token, and paste it into the HA re-auth form.

You can change the fetch day at any time: **Settings → Devices & Services → E.ON Energy → Configure**.

## Sensors

| Entity | Description | Unit | State class |
|---|---|---|---|
| `sensor.e_on_heat_this_period` | Heating energy — current billing period | kWh | `total` (resets at period start) |
| `sensor.e_on_heat_this_period_cost` | Heating cost — current billing period | GBP | `total` |
| `sensor.e_on_heat_last_period` | Heating energy — previous billing period | kWh | `measurement` |
| `sensor.e_on_heat_last_period_cost` | Heating cost — previous billing period | GBP | `measurement` |
| `sensor.e_on_account_number` | Account number | — | diagnostic |

All sensors include `period_start` and `period_end` as state attributes.

## Energy Dashboard

`sensor.e_on_heat_this_period` is compatible with the HA Energy Dashboard as a device consumption source. Add it under **Settings → Dashboards → Energy → Add consumption**.

## Debugging

Enable debug logging to see API responses:

```yaml
logger:
  logs:
    custom_components.eon_energy: debug
```
