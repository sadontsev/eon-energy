"""Sensor platform for the E.ON Energy integration."""

from __future__ import annotations

from typing import Any

import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import EonEnergyCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up E.ON Energy sensors from a config entry."""
    coordinator: EonEnergyCoordinator = config_entry.runtime_data
    account_number: str = config_entry.data.get("account_number", "")

    async_add_entities([
        EonHeatCurrentPeriodSensor(coordinator, account_number),
        EonHeatCurrentCostSensor(coordinator, account_number),
        EonHeatPreviousPeriodSensor(coordinator, account_number),
        EonHeatPreviousCostSensor(coordinator, account_number),
        EonEnergyAccountSensor(coordinator, account_number),
    ])


class EonEnergySensorBase(CoordinatorEntity, SensorEntity):
    """Base class for E.ON Energy sensors."""

    def __init__(self, coordinator: EonEnergyCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._account_number)},
            "name": "E.ON Heat",
            "manufacturer": "E.ON Energy",
            "model": "Heat Pump Account",
            "entry_type": "service",
        }


class EonHeatCurrentPeriodSensor(EonEnergySensorBase):
    """Energy consumption for the current billing period (kWh)."""

    _attr_name = "E.ON Heat This Period"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_heat_current_kwh"

    @property
    def native_value(self):
        return self._data.get("current_kwh")

    @property
    def last_reset(self) -> datetime.datetime | None:
        """Return the start of the current billing period as last_reset."""
        raw = self._data.get("current_period_start")
        if not raw:
            return None
        try:
            return dt_util.parse_datetime(raw) or None
        except Exception:  # pylint: disable=broad-except
            return None

    @property
    def extra_state_attributes(self):
        return {
            "period_start": self._data.get("current_period_start"),
            "period_end": self._data.get("current_period_end"),
        }


class EonHeatCurrentCostSensor(EonEnergySensorBase):
    """Cost for the current billing period (GBP)."""

    _attr_name = "E.ON Heat This Period Cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_heat_current_cost"

    @property
    def native_value(self):
        return self._data.get("current_cost_gbp")

    @property
    def last_reset(self) -> datetime.datetime | None:
        raw = self._data.get("current_period_start")
        if not raw:
            return None
        try:
            return dt_util.parse_datetime(raw) or None
        except Exception:  # pylint: disable=broad-except
            return None

    @property
    def extra_state_attributes(self):
        return {
            "period_start": self._data.get("current_period_start"),
            "period_end": self._data.get("current_period_end"),
        }


class EonHeatPreviousPeriodSensor(EonEnergySensorBase):
    """Energy consumption for the previous billing period (kWh)."""

    _attr_name = "E.ON Heat Last Period"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_heat_previous_kwh"

    @property
    def native_value(self):
        return self._data.get("previous_kwh")

    @property
    def extra_state_attributes(self):
        return {
            "period_start": self._data.get("previous_period_start"),
            "period_end": self._data.get("previous_period_end"),
        }


class EonHeatPreviousCostSensor(EonEnergySensorBase):
    """Cost for the previous billing period (GBP)."""

    _attr_name = "E.ON Heat Last Period Cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash-minus"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_heat_previous_cost"

    @property
    def native_value(self):
        return self._data.get("previous_cost_gbp")

    @property
    def extra_state_attributes(self):
        return {
            "period_start": self._data.get("previous_period_start"),
            "period_end": self._data.get("previous_period_end"),
        }


class EonEnergyAccountSensor(EonEnergySensorBase):
    """Diagnostic sensor showing the account number."""

    _attr_name = "E.ON Account Number"
    _attr_icon = "mdi:account-circle-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_account_number"

    @property
    def native_value(self):
        return self._account_number
