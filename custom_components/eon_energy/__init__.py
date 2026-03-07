"""E.ON Energy Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import EonEnergyApi, EonEnergyApiError, EonEnergyAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_NUMBER,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    PLATFORMS,
)
from .coordinator import EonEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up E.ON Energy from a config entry."""
    api = EonEnergyApi()

    def _on_tokens_updated(
        access_token: str | None,
        refresh_token: str | None,
        token_expiry: float,
        account_number: str | None,
    ) -> None:
        """Persist refreshed tokens to the config entry."""
        updates: dict = {}
        if access_token and access_token != entry.data.get(CONF_ACCESS_TOKEN):
            updates[CONF_ACCESS_TOKEN] = access_token
        if refresh_token and refresh_token != entry.data.get(CONF_REFRESH_TOKEN):
            updates[CONF_REFRESH_TOKEN] = refresh_token
        if token_expiry != entry.data.get(CONF_TOKEN_EXPIRY):
            updates[CONF_TOKEN_EXPIRY] = token_expiry
        if updates:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, **updates}
            )

    api.set_token_update_callback(_on_tokens_updated)

    # Restore stored tokens if available; fall back to password login
    stored_access = entry.data.get(CONF_ACCESS_TOKEN)
    stored_refresh = entry.data.get(CONF_REFRESH_TOKEN)
    stored_expiry = entry.data.get(CONF_TOKEN_EXPIRY, 0.0)
    stored_account = entry.data.get(CONF_ACCOUNT_NUMBER, "")

    if stored_access and stored_refresh:
        api.restore_tokens(stored_access, stored_refresh, stored_expiry, stored_account)
        # Attempt a token refresh to validate / extend the session
        try:
            await api.async_refresh_token()
            _LOGGER.debug("E.ON Energy: session restored via stored refresh token")
        except EonEnergyAuthError:
            _LOGGER.debug(
                "E.ON Energy: stored refresh token invalid — falling back to credentials"
            )
            # Clear tokens so the password path runs
            api._access_token = None
            api._refresh_token = None
        except EonEnergyApiError as err:
            await api.async_close()
            raise ConfigEntryNotReady(f"E.ON Energy API unreachable: {err}") from err

    if not api._access_token:
        email = entry.data.get(CONF_EMAIL, "")
        password = entry.data.get(CONF_PASSWORD, "")
        try:
            await api.async_login(email, password)
        except EonEnergyAuthError as err:
            await api.async_close()
            raise ConfigEntryAuthFailed(str(err)) from err
        except EonEnergyApiError as err:
            await api.async_close()
            raise ConfigEntryNotReady(f"E.ON Energy API unreachable: {err}") from err

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
