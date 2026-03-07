"""Sensor platform for the E.ON Energy integration."""

from __future__ import annotations

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

    entities: list[SensorEntity] = [
        EonEnergyElectricityTodaySensor(coordinator, account_number),
        EonEnergyElectricityYesterdaySensor(coordinator, account_number),
        EonEnergyGasTodaySensor(coordinator, account_number),
        EonEnergyGasYesterdaySensor(coordinator, account_number),
        EonEnergyAccountSensor(coordinator, account_number),
    ]
    async_add_entities(entities)


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
            "name": "E.ON Energy",
            "manufacturer": "E.ON Energy",
            "model": "Energy Account",
            "entry_type": "service",
        }


class EonEnergyElectricityTodaySensor(EonEnergySensorBase):
    """Electricity consumption today (kWh)."""

    _attr_name = "E.ON Electricity Today"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_electricity_today"

    @property
    def native_value(self):
        return self._data.get("electricity_today_kwh")


class EonEnergyElectricityYesterdaySensor(EonEnergySensorBase):
    """Electricity consumption yesterday (kWh)."""

    _attr_name = "E.ON Electricity Yesterday"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt-outline"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_electricity_yesterday"

    @property
    def native_value(self):
        return self._data.get("electricity_yesterday_kwh")


class EonEnergyGasTodaySensor(EonEnergySensorBase):
    """Gas consumption today (kWh)."""

    _attr_name = "E.ON Gas Today"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_gas_today"

    @property
    def native_value(self):
        return self._data.get("gas_today_kwh")


class EonEnergyGasYesterdaySensor(EonEnergySensorBase):
    """Gas consumption yesterday (kWh)."""

    _attr_name = "E.ON Gas Yesterday"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fire-off"

    def __init__(self, coordinator, account_number):
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{account_number}__eon_gas_yesterday"

    @property
    def native_value(self):
        return self._data.get("gas_yesterday_kwh")


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
