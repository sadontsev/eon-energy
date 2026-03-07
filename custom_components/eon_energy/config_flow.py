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
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EonEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle E.ON Energy config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    async def _do_login(self, email: str, password: str) -> dict[str, Any]:
        """Attempt login; return token data dict on success."""
        api = EonEnergyApi()
        try:
            account_number = await api.async_validate_credentials(email, password)
            return {
                CONF_EMAIL: email,
                CONF_PASSWORD: password,
                CONF_ACCESS_TOKEN: api._access_token,
                CONF_REFRESH_TOKEN: api._refresh_token,
                CONF_TOKEN_EXPIRY: api._token_expiry,
                CONF_ACCOUNT_NUMBER: account_number,
            }
        finally:
            await api.async_close()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Show email/password form and validate on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]

            try:
                entry_data = await self._do_login(email, password)
            except EonEnergyAuthError:
                errors["base"] = "invalid_auth"
            except EonEnergyApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during E.ON Energy login")
                errors["base"] = "unknown"
            else:
                account_number = entry_data[CONF_ACCOUNT_NUMBER]
                await self.async_set_unique_id(account_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="E.ON Energy", data=entry_data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
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
        """Handle re-auth form."""
        errors: dict[str, str] = {}

        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        existing_email = self._reauth_entry.data.get(CONF_EMAIL, "")

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]

            try:
                entry_data = await self._do_login(email, password)
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
                {
                    vol.Required(CONF_EMAIL, default=existing_email): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )
