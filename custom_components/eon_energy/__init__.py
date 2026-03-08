"""E.ON Energy Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import EonEnergyApi
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BEARER_TOKEN,
    CONF_FETCH_DAY,
    CONF_STORED_CONSUMPTION,
    CONF_TOKEN_EXPIRY,
    DEFAULT_FETCH_DAY,
    PLATFORMS,
)
from .coordinator import EonEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    bearer_token = entry.data.get(CONF_BEARER_TOKEN, "")
    token_expiry = entry.data.get(CONF_TOKEN_EXPIRY, 0.0)
    account_number = entry.data.get(CONF_ACCOUNT_NUMBER, "")
    stored_data = entry.data.get(CONF_STORED_CONSUMPTION, {})
    fetch_day = entry.options.get(CONF_FETCH_DAY, DEFAULT_FETCH_DAY)

    api = EonEnergyApi()
    if bearer_token:
        api.restore_tokens(bearer_token, token_expiry, account_number)

    def _persist_data(data: dict) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_STORED_CONSUMPTION: data}
        )

    coordinator = EonEnergyCoordinator(
        hass, api, fetch_day=fetch_day,
        stored_data=stored_data, on_data_persisted=_persist_data,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.async_close()
        raise

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry) -> None:
    coordinator: EonEnergyCoordinator = entry.runtime_data
    coordinator.update_fetch_day(entry.options.get(CONF_FETCH_DAY, DEFAULT_FETCH_DAY))


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.api.async_close()
    return unload_ok
