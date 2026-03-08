"""Config flow for E.ON Energy integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv

from .api import EonEnergyApi, EonEnergyAuthError, EonEnergyApiError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_NUMBER,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_REFRESH_TOKEN_INPUT = "refresh_token"


class EonEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle E.ON Energy config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    async def _validate_token(self, refresh_token: str) -> dict[str, Any]:
        """Validate the refresh token; return entry data dict on success."""
        api = EonEnergyApi()
        try:
            account_number = await api.async_validate_refresh_token(refresh_token)
            return {
                CONF_REFRESH_TOKEN: api._refresh_token,  # may be rotated
                CONF_ACCESS_TOKEN: api._access_token,
                CONF_TOKEN_EXPIRY: api._token_expiry,
                CONF_ACCOUNT_NUMBER: account_number,
            }
        finally:
            await api.async_close()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Show the refresh-token entry form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN_INPUT].strip()
            try:
                entry_data = await self._validate_token(refresh_token)
            except EonEnergyAuthError:
                errors["base"] = "invalid_auth"
            except EonEnergyApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during E.ON Energy setup")
                errors["base"] = "unknown"
            else:
                account_number = entry_data[CONF_ACCOUNT_NUMBER]
                await self.async_set_unique_id(account_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="E.ON Energy", data=entry_data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_REFRESH_TOKEN_INPUT): cv.string}
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        """Initiate re-auth flow."""
        del entry_data
        entry_id = self.context.get("entry_id")
        if not isinstance(entry_id, str):
            return self.async_abort(reason="unknown")
        self._reauth_entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle re-auth form (paste a new refresh token)."""
        errors: dict[str, str] = {}

        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN_INPUT].strip()
            try:
                entry_data = await self._validate_token(refresh_token)
            except EonEnergyAuthError:
                errors["base"] = "invalid_auth"
            except EonEnergyApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during E.ON Energy re-auth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates=entry_data,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_REFRESH_TOKEN_INPUT): cv.string}
            ),
            errors=errors,
        )
