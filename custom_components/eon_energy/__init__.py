"""E.ON Energy Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import EonEnergyApi, EonEnergyAuthError
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BEARER_TOKEN,
    CONF_TOKEN_EXPIRY,
    PLATFORMS,
)
from .coordinator import EonEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up E.ON Energy from a config entry."""
    bearer_token = entry.data.get(CONF_BEARER_TOKEN, "")
    token_expiry = entry.data.get(CONF_TOKEN_EXPIRY, 0.0)
    account_number = entry.data.get(CONF_ACCOUNT_NUMBER, "")

    if not bearer_token:
        raise ConfigEntryAuthFailed("No token stored — please re-authenticate")

    api = EonEnergyApi()
    api.restore_tokens(bearer_token, token_expiry, account_number)

    # Validate the token is still usable before first coordinator run
    try:
        await api.async_get_token()
    except EonEnergyAuthError as err:
        await api.async_close()
        raise ConfigEntryAuthFailed(str(err)) from err

    coordinator = EonEnergyCoordinator(hass, api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.async_close()
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload an E.ON Energy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: EonEnergyCoordinator = entry.runtime_data
        await coordinator.api.async_close()
    return unload_ok
