"""DataUpdateCoordinator for E.ON Energy."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EonEnergyApi, EonEnergyAuthError, EonEnergyApiError
from .const import UPDATE_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


class EonEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching E.ON Energy consumption data."""

    def __init__(self, hass, api: EonEnergyApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="E.ON Energy",
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch consumption data from the E.ON Energy API."""
        try:
            raw = await self.api.async_get_consumption()
        except EonEnergyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EonEnergyApiError as err:
            raise UpdateFailed(f"E.ON Energy API error: {err}") from err

        _LOGGER.debug("Raw consumption response: %s", raw)
        return self._parse_consumption(raw)

    @staticmethod
    def _parse_consumption(raw: Any) -> dict[str, Any]:
        """Parse the /accounts/meters/consumption response.

        Response schema:
          {
            "account": "400123723366",
            "consumptionData": [
              {
                "periodStart": "2026-03-01T00:00:00.000",
                "periodEnd":   "2026-03-08T00:00:00.000",
                "meterPointIdentifier": "KBKBERPH5DH4H.01",
                "consumption":       {"amount": 65,   "unit": "kWh"},
                "consumptionCharge": {"amount": 4.95, "unit": "GBP"}
              }, ...
            ]
          }
        Periods are sorted ascending; the last entry is the current (incomplete) period.
        """
        result: dict[str, Any] = {}

        if not isinstance(raw, dict):
            _LOGGER.warning("Unexpected response type %s", type(raw).__name__)
            return result

        periods = raw.get("consumptionData", [])
        if not isinstance(periods, list) or not periods:
            _LOGGER.warning("No consumptionData in response: %s", raw)
            return result

        # Sort ascending by periodStart so the last entry is always current
        try:
            periods = sorted(periods, key=lambda p: p.get("periodStart", ""))
        except Exception:  # pylint: disable=broad-except
            pass

        current = periods[-1]
        result["current_period_start"] = current.get("periodStart")
        result["current_period_end"] = current.get("periodEnd")
        result["current_kwh"] = _safe_float(
            current.get("consumption", {}).get("amount")
        )
        result["current_cost_gbp"] = _safe_float(
            current.get("consumptionCharge", {}).get("amount")
        )

        if len(periods) >= 2:
            previous = periods[-2]
            result["previous_period_start"] = previous.get("periodStart")
            result["previous_period_end"] = previous.get("periodEnd")
            result["previous_kwh"] = _safe_float(
                previous.get("consumption", {}).get("amount")
            )
            result["previous_cost_gbp"] = _safe_float(
                previous.get("consumptionCharge", {}).get("amount")
            )

        _LOGGER.debug("Parsed consumption: %s", result)
        return result


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
