"""E.ON Energy Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import EonEnergyApi
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BEARER_TOKEN,
    CONF_FETCH_DAY,
    CONF_MONTHLY_SERVICE_CHARGE,
    CONF_STORED_CONSUMPTION,
    CONF_TOKEN_EXPIRY,
    DEFAULT_FETCH_DAY,
    DEFAULT_MONTHLY_SERVICE_CHARGE,
    PLATFORMS,
)
from .coordinator import EonEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up E.ON Energy from a config entry."""

    bearer_token = entry.data.get(CONF_BEARER_TOKEN, "")
    token_expiry = entry.data.get(CONF_TOKEN_EXPIRY, 0.0)
    account_number = entry.data.get(CONF_ACCOUNT_NUMBER, "")
    stored_data = entry.data.get(CONF_STORED_CONSUMPTION, {})
    fetch_day = entry.options.get(CONF_FETCH_DAY, DEFAULT_FETCH_DAY)
    monthly_service_charge = entry.options.get(
        CONF_MONTHLY_SERVICE_CHARGE, DEFAULT_MONTHLY_SERVICE_CHARGE
    )

    api = EonEnergyApi()
    if bearer_token:
        # Restore whatever token we have — coordinator decides whether to use it
        api.restore_tokens(bearer_token, token_expiry, account_number)

    def _persist_data(data: dict) -> None:
        """Write freshly fetched consumption data back to the config entry."""
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_STORED_CONSUMPTION: data}
        )

    coordinator = EonEnergyCoordinator(
        hass,
        api,
        fetch_day=fetch_day,
        monthly_service_charge=monthly_service_charge,
        stored_data=stored_data,
        on_data_persisted=_persist_data,
    )

    # First refresh: returns stored_data immediately if today isn't fetch day,
    # or attempts an API call if it is. Either way it never raises auth errors
    # unless we're actively on the fetch day with an expired token.
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.async_close()
        raise

    entry.runtime_data = coordinator

    # React to options changes (user moves the fetch day)
    entry.async_on_unload(
        entry.add_update_listener(_async_options_updated)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry) -> None:
    """Handle options update — propagate new settings to the coordinator."""
    coordinator: EonEnergyCoordinator = entry.runtime_data
    fetch_day = entry.options.get(CONF_FETCH_DAY, DEFAULT_FETCH_DAY)
    monthly_service_charge = entry.options.get(
        CONF_MONTHLY_SERVICE_CHARGE, DEFAULT_MONTHLY_SERVICE_CHARGE
    )
    coordinator.update_options(fetch_day, monthly_service_charge)
    _LOGGER.debug(
        "E.ON Energy: options updated — fetch_day=%d, monthly_service_charge=%.2f",
        fetch_day,
        monthly_service_charge,
    )


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload an E.ON Energy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: EonEnergyCoordinator = entry.runtime_data
        await coordinator.api.async_close()
    return unload_ok
