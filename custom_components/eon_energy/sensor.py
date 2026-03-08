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
    """Set up E.ON Energy sensors from a config entry."""
    coordinator: EonEnergyCoordinator = config_entry.runtime_data
    acct = config_entry.data.get("account_number", "")

    async_add_entities([
        # Current period
        EonHeatCurrentKwhSensor(coordinator, acct),
        EonHeatCurrentConsumptionChargeSensor(coordinator, acct),
        EonHeatCurrentServiceChargeSensor(coordinator, acct),
        EonHeatCurrentTotalCostSensor(coordinator, acct),
        # Previous period
        EonHeatPreviousKwhSensor(coordinator, acct),
        EonHeatPreviousConsumptionChargeSensor(coordinator, acct),
        EonHeatPreviousServiceChargeSensor(coordinator, acct),
        EonHeatPreviousTotalCostSensor(coordinator, acct),
        # Diagnostic
        EonEnergyAccountSensor(coordinator, acct),
    ])


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class _EonBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: EonEnergyCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._acct = account_number

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


class EonHeatCurrentConsumptionChargeSensor(_EonBase):
    _attr_name = "E.ON Heat This Period Consumption Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_current_consumption_charge"

    @property
    def native_value(self):
        return self._data.get("current_consumption_charge_gbp")

    @property
    def last_reset(self):
        return self._last_reset("current")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("current")


class EonHeatCurrentServiceChargeSensor(_EonBase):
    _attr_name = "E.ON Heat This Period Service Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:calendar-month"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_current_service_charge"

    @property
    def native_value(self):
        return self._data.get("current_service_charge_gbp")

    @property
    def last_reset(self):
        return self._last_reset("current")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("current")


class EonHeatCurrentTotalCostSensor(_EonBase):
    _attr_name = "E.ON Heat This Period Total"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_current_total"

    @property
    def native_value(self):
        return self._data.get("current_total_cost_gbp")

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


class EonHeatPreviousConsumptionChargeSensor(_EonBase):
    _attr_name = "E.ON Heat Last Period Consumption Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_previous_consumption_charge"

    @property
    def native_value(self):
        return self._data.get("previous_consumption_charge_gbp")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("previous")


class EonHeatPreviousServiceChargeSensor(_EonBase):
    _attr_name = "E.ON Heat Last Period Service Charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-month"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_previous_service_charge"

    @property
    def native_value(self):
        return self._data.get("previous_service_charge_gbp")

    @property
    def extra_state_attributes(self):
        return self._period_attrs("previous")


class EonHeatPreviousTotalCostSensor(_EonBase):
    _attr_name = "E.ON Heat Last Period Total"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator, acct):
        super().__init__(coordinator, acct)
        self._attr_unique_id = f"{acct}__eon_heat_previous_total"

    @property
    def native_value(self):
        return self._data.get("previous_total_cost_gbp")

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
