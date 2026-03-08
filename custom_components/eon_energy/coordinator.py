"""DataUpdateCoordinator for E.ON Energy."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EonEnergyApi, EonEnergyAuthError, EonEnergyApiError

_LOGGER = logging.getLogger(__name__)

_CHECK_INTERVAL = timedelta(hours=6)


class EonEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator for E.ON Energy — fetches on a user-configured day each month."""

    def __init__(
        self,
        hass,
        api: EonEnergyApi,
        fetch_day: int,
        stored_data: dict[str, Any],
        on_data_persisted: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="E.ON Energy",
            update_interval=_CHECK_INTERVAL,
        )
        self.api = api
        self._fetch_day = fetch_day
        self._stored_data = stored_data
        self._on_data_persisted = on_data_persisted

    async def _async_update_data(self) -> dict[str, Any]:
        today = dt_util.now().day
        is_fetch_day = today == self._fetch_day

        if not is_fetch_day and self._stored_data:
            _LOGGER.debug(
                "E.ON Energy: not fetch day (today=%d, fetch_day=%d) — using stored data",
                today, self._fetch_day,
            )
            return self._stored_data

        if not is_fetch_day and not self._stored_data:
            _LOGGER.debug("E.ON Energy: no stored data — attempting bootstrap fetch")
            try:
                raw = await self.api.async_get_consumption()
                parsed = _parse_consumption(raw)
                self._stored_data = parsed
                self._on_data_persisted(parsed)
                return parsed
            except (EonEnergyAuthError, EonEnergyApiError) as err:
                _LOGGER.debug(
                    "E.ON Energy: bootstrap fetch failed (token may be expired, "
                    "data will populate on fetch day %d): %s", self._fetch_day, err,
                )
                return {}

        _LOGGER.debug("E.ON Energy: fetch day %d — calling API", self._fetch_day)
        try:
            raw = await self.api.async_get_consumption()
        except EonEnergyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EonEnergyApiError as err:
            raise UpdateFailed(f"E.ON Energy API error: {err}") from err

        _LOGGER.debug("E.ON Energy raw response: %s", raw)
        parsed = _parse_consumption(raw)
        self._stored_data = parsed
        self._on_data_persisted(parsed)
        return parsed

    def update_fetch_day(self, fetch_day: int) -> None:
        self._fetch_day = fetch_day


def _parse_consumption(raw: Any) -> dict[str, Any]:
    """Parse /accounts/meters/consumption into a flat dict.

    Response shape:
      {
        "account": "400123723366",
        "consumptionData": [
          {
            "periodStart": "2026-03-01T00:00:00.000",
            "periodEnd":   "2026-04-01T00:00:00.000",
            "meterPointIdentifier": "KBKBERPH5DH4H.01",
            "consumption":       {"amount": 521, "unit": "kWh"},
            "consumptionCharge": {"amount": 39.70, "unit": "GBP"}
          }, ...
        ]
      }
    Periods sorted ascending; the last entry is the current (incomplete) period.
    """
    result: dict[str, Any] = {}

    if not isinstance(raw, dict):
        _LOGGER.warning("Unexpected response type %s", type(raw).__name__)
        return result

    periods = raw.get("consumptionData", [])
    if not isinstance(periods, list) or not periods:
        _LOGGER.warning("No consumptionData in response: %s", raw)
        return result

    try:
        periods = sorted(periods, key=lambda p: p.get("periodStart", ""))
    except Exception:  # pylint: disable=broad-except
        pass

    def _extract(period: dict, prefix: str) -> None:
        result[f"{prefix}_period_start"] = period.get("periodStart")
        result[f"{prefix}_period_end"] = period.get("periodEnd")
        result[f"{prefix}_kwh"] = _safe_float(
            period.get("consumption", {}).get("amount")
        )
        result[f"{prefix}_charge_gbp"] = _safe_float(
            period.get("consumptionCharge", {}).get("amount")
        )

    _extract(periods[-1], "current")
    if len(periods) >= 2:
        _extract(periods[-2], "previous")

    # Cumulative totals across all periods returned by the API
    total_kwh = sum(
        f for p in periods
        if (f := _safe_float(p.get("consumption", {}).get("amount"))) is not None
    )
    total_charge = sum(
        f for p in periods
        if (f := _safe_float(p.get("consumptionCharge", {}).get("amount"))) is not None
    )
    result["total_kwh"] = round(total_kwh, 3)
    result["total_charge_gbp"] = round(total_charge, 2)
    result["data_from"] = periods[0].get("periodStart")
    result["data_to"] = periods[-1].get("periodEnd")

    _LOGGER.debug("Parsed consumption: %s", result)
    return result


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
