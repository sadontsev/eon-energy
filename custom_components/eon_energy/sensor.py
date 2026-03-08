"""Sensor platform for the E.ON Energy integration."""

from __future__ import annotations

import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import EonEnergyCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EonEnergyCoordinator = config_entry.runtime_data
    acct = config_entry.data.get("account_number", "")

    async_add_entities([
        EonHeatTotalConsumptionSensor(coordinator, acct),
        EonHeatTotalChargeSensor(coordinator, acct),
        EonHeatCurrentKwhSensor(coordinator, acct),
        EonHeatCurrentChargeSensor(coordinator, acct),
        EonHeatPreviousKwhSensor(coordinator, acct),
        EonHeatPreviousChargeSensor(coordinator, acct),
        EonEnergyAccountSensor(coordinator, acct),
    ])


class _EonBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: EonEnergyCoordinator, acct: str) -> None:
        super().__init__(coordinator)
        self._acct = acct

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._acct)},
            "name": "E.ON Heat",
            "manufacturer": "E.ON Energy",
            "model": "Heat Pump Account",
            "entry_type": "service",
        }

    def _period_attrs(self, prefix: str) -> dict[str, Any]:
        return {
            "period_start": self._data.get(f"{prefix}_period_start"),
            "period_end": self._data.get(f"{prefix}_period_end"),
        }

    def _last_reset(self, prefix: str) -> datetime.datetime | None:
        raw = self._data.get(f"{prefix}_period_start")
        if not raw:
            return None
        try:
            return dt_util.parse_datetime(raw) or None
        except Exception:  # pylint: disable=broad-except
            return None


# ---------------------------------------------------------------------------
# Cumulative totals (sum of all periods returned by the API)
# ---------------------------------------------------------------------------

class EonHeatTotalConsumptionSensor(_EonBase):
    """Total heating energy across all billing periods from the API (kWh).

    Suitable for the Energy Dashboard — monotonically increases as new
    periods are added each month.
    """
    _attr_name = "E.ON Heat Consumption"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_total_kwh"

    @property
    def native_value(self):
        return self._data.get("total_kwh")

    @property
    def extra_state_attributes(self):
        return {
            "data_from": self._data.get("data_from"),
            "data_to": self._data.get("data_to"),
        }


class EonHeatTotalChargeSensor(_EonBase):
    """Total heating charge across all billing periods from the API (GBP)."""

    _attr_name = "E.ON Heat Total Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_total_charge"

    @property
    def native_value(self):
        return self._data.get("total_charge_gbp")

    @property
    def extra_state_attributes(self):
        return {
            "data_from": self._data.get("data_from"),
            "data_to": self._data.get("data_to"),
        }


# ---------------------------------------------------------------------------
# Current period
# ---------------------------------------------------------------------------

class EonHeatCurrentKwhSensor(_EonBase):
    _attr_name = "E.ON Heat This Period"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_current_kwh"

    @property
    def native_value(self):
        return self._data.get("current_kwh")

    @property
    def last_reset(self):
        return self._last_reset("current")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("current")


class EonHeatCurrentChargeSensor(_EonBase):
    _attr_name = "E.ON Heat This Period Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_current_charge"

    @property
    def native_value(self):
        return self._data.get("current_charge_gbp")

    @property
    def last_reset(self):
        return self._last_reset("current")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("current")


# ---------------------------------------------------------------------------
# Previous period
# ---------------------------------------------------------------------------

class EonHeatPreviousKwhSensor(_EonBase):
    _attr_name = "E.ON Heat Last Period"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_previous_kwh"

    @property
    def native_value(self):
        return self._data.get("previous_kwh")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("previous")


class EonHeatPreviousChargeSensor(_EonBase):
    _attr_name = "E.ON Heat Last Period Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_previous_charge"

    @property
    def native_value(self):
        return self._data.get("previous_charge_gbp")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("previous")


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------

class EonEnergyAccountSensor(_EonBase):
    _attr_name = "E.ON Account Number"
    _attr_icon = "mdi:account-circle-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_account_number"

    @property
    def native_value(self):
        return self._acct
