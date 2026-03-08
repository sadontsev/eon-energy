"""DataUpdateCoordinator for E.ON Energy."""

from __future__ import annotations

import calendar
import datetime
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EonEnergyApi, EonEnergyAuthError, EonEnergyApiError

_LOGGER = logging.getLogger(__name__)

# Check once every 6 hours so we don't miss the fetch day by more than half a day
_CHECK_INTERVAL = timedelta(hours=6)


class EonEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator for E.ON Energy — fetches on a user-configured day each month."""

    def __init__(
        self,
        hass,
        api: EonEnergyApi,
        fetch_day: int,
        monthly_service_charge: float,
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
        self._monthly_service_charge = monthly_service_charge
        self._stored_data = stored_data
        self._on_data_persisted = on_data_persisted

    # ------------------------------------------------------------------
    # Core update logic
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        today = dt_util.now().day
        is_fetch_day = today == self._fetch_day

        if not is_fetch_day and self._stored_data:
            # Normal non-fetch day: return cached data, no network call
            _LOGGER.debug(
                "E.ON Energy: not fetch day (today=%d, fetch_day=%d) — using stored data",
                today,
                self._fetch_day,
            )
            return self._stored_data

        if not is_fetch_day and not self._stored_data:
            # No cached data yet (fresh install or config migration) — attempt a
            # one-time bootstrap fetch. If the token is expired, log and stay empty;
            # do NOT raise ConfigEntryAuthFailed (the fetch day hasn't arrived yet).
            _LOGGER.debug("E.ON Energy: no stored data — attempting bootstrap fetch")
            try:
                raw = await self.api.async_get_consumption()
                parsed = _parse_consumption(raw, self._monthly_service_charge)
                self._stored_data = parsed
                self._on_data_persisted(parsed)
                return parsed
            except (EonEnergyAuthError, EonEnergyApiError) as err:
                _LOGGER.debug(
                    "E.ON Energy: bootstrap fetch failed (token may be expired, "
                    "data will populate on fetch day %d): %s",
                    self._fetch_day,
                    err,
                )
                return {}

        # It is the fetch day — try to fetch and prompt re-auth if token expired
        _LOGGER.debug("E.ON Energy: fetch day %d — calling API", self._fetch_day)
        try:
            raw = await self.api.async_get_consumption()
        except EonEnergyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EonEnergyApiError as err:
            raise UpdateFailed(f"E.ON Energy API error: {err}") from err

        _LOGGER.debug("E.ON Energy raw response: %s", raw)
        parsed = _parse_consumption(raw, self._monthly_service_charge)
        self._stored_data = parsed
        self._on_data_persisted(parsed)
        return parsed

    # ------------------------------------------------------------------
    # Options update (called from __init__ when options change)
    # ------------------------------------------------------------------

    def update_options(self, fetch_day: int, monthly_service_charge: float) -> None:
        self._fetch_day = fetch_day
        self._monthly_service_charge = monthly_service_charge


# ------------------------------------------------------------------
# Parser (standalone so it can be tested independently)
# ------------------------------------------------------------------

def _parse_consumption(raw: Any, monthly_service_charge: float = 0.0) -> dict[str, Any]:
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
    Periods are sorted ascending; the last entry is the current (incomplete) period.
    Service charge is prorated: monthly_fee × (period_days / days_in_start_month).
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

    def _enrich(period: dict, prefix: str) -> None:
        start_str = period.get("periodStart")
        end_str = period.get("periodEnd")
        consumption_charge = _safe_float(period.get("consumptionCharge", {}).get("amount"))

        result[f"{prefix}_period_start"] = start_str
        result[f"{prefix}_period_end"] = end_str
        result[f"{prefix}_kwh"] = _safe_float(period.get("consumption", {}).get("amount"))
        result[f"{prefix}_consumption_charge_gbp"] = consumption_charge

        # Prorate the monthly service charge by actual days in this period
        service_charge: float | None = None
        if monthly_service_charge and start_str and end_str:
            try:
                start_dt = datetime.date.fromisoformat(start_str[:10])
                end_dt = datetime.date.fromisoformat(end_str[:10])
                period_days = (end_dt - start_dt).days
                month_days = calendar.monthrange(start_dt.year, start_dt.month)[1]
                service_charge = round(
                    monthly_service_charge * period_days / month_days, 2
                )
            except (ValueError, TypeError):
                pass

        result[f"{prefix}_service_charge_gbp"] = service_charge

        # Total = consumption charge + service charge
        if consumption_charge is not None and service_charge is not None:
            result[f"{prefix}_total_cost_gbp"] = round(
                consumption_charge + service_charge, 2
            )
        else:
            result[f"{prefix}_total_cost_gbp"] = consumption_charge  # best effort

    _enrich(periods[-1], "current")
    if len(periods) >= 2:
        _enrich(periods[-2], "previous")

    _LOGGER.debug("Parsed consumption: %s", result)
    return result


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
