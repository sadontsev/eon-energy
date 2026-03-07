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
            _LOGGER.error("Authentication error during E.ON Energy update: %s", err)
            raise ConfigEntryAuthFailed(str(err)) from err
        except EonEnergyApiError as err:
            raise UpdateFailed(f"E.ON Energy API error: {err}") from err

        return self._parse_consumption(raw)

    @staticmethod
    def _parse_consumption(raw: Any) -> dict[str, Any]:
        """Parse the /accounts/meters/consumption response into a flat dict.

        The exact schema is unknown until the first real API response, so we
        use defensive .get() access throughout and store the raw payload too.
        """
        if not isinstance(raw, dict):
            _LOGGER.warning(
                "Unexpected consumption response type: %s — storing raw only",
                type(raw).__name__,
            )
            return {"raw": raw}

        parsed: dict[str, Any] = {"raw": raw}

        # --- Electricity ---
        elec = raw.get("electricity") or raw.get("electricityConsumption") or {}
        if isinstance(elec, dict):
            parsed["electricity_today_kwh"] = _safe_float(
                elec.get("today") or elec.get("todayKwh") or elec.get("consumption")
            )
            parsed["electricity_yesterday_kwh"] = _safe_float(
                elec.get("yesterday") or elec.get("yesterdayKwh")
            )

        # --- Gas ---
        gas = raw.get("gas") or raw.get("gasConsumption") or {}
        if isinstance(gas, dict):
            parsed["gas_today_kwh"] = _safe_float(
                gas.get("today") or gas.get("todayKwh") or gas.get("consumption")
            )
            parsed["gas_yesterday_kwh"] = _safe_float(
                gas.get("yesterday") or gas.get("yesterdayKwh")
            )

        # Handle array-style response (list of meter objects)
        meters = raw.get("meters") or raw.get("data") or []
        if isinstance(meters, list):
            for meter in meters:
                if not isinstance(meter, dict):
                    continue
                fuel = str(meter.get("fuelType") or meter.get("type") or "").lower()
                today_kwh = _safe_float(
                    meter.get("todayConsumption")
                    or meter.get("today")
                    or meter.get("consumption")
                )
                yesterday_kwh = _safe_float(
                    meter.get("yesterdayConsumption") or meter.get("yesterday")
                )
                if "elec" in fuel or "electricity" in fuel:
                    if today_kwh is not None:
                        parsed["electricity_today_kwh"] = today_kwh
                    if yesterday_kwh is not None:
                        parsed["electricity_yesterday_kwh"] = yesterday_kwh
                elif "gas" in fuel:
                    if today_kwh is not None:
                        parsed["gas_today_kwh"] = today_kwh
                    if yesterday_kwh is not None:
                        parsed["gas_yesterday_kwh"] = yesterday_kwh

        _LOGGER.debug("Parsed consumption data: %s", parsed)
        return parsed


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
