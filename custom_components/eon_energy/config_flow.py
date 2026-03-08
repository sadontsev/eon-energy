"""Config flow for E.ON Energy integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv

from .api import EonEnergyApi, EonEnergyAuthError
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BEARER_TOKEN,
    CONF_FETCH_DAY,
    CONF_TOKEN_EXPIRY,
    DEFAULT_FETCH_DAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_TOKEN_INPUT = "token_data"


class EonEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        return EonEnergyOptionsFlow(config_entry)

    async def _validate(self, raw: str) -> dict[str, Any]:
        api = EonEnergyApi()
        try:
            account_number = await api.async_validate_token_data(raw)
            return {
                CONF_BEARER_TOKEN: api._bearer_token,
                CONF_TOKEN_EXPIRY: api._token_expiry,
                CONF_ACCOUNT_NUMBER: account_number,
            }
        finally:
            await api.async_close()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                entry_data = await self._validate(user_input[CONF_TOKEN_INPUT])
            except EonEnergyAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during E.ON Energy setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(entry_data[CONF_ACCOUNT_NUMBER])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="E.ON Energy",
                    data=entry_data,
                    options={CONF_FETCH_DAY: user_input[CONF_FETCH_DAY]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_TOKEN_INPUT): cv.string,
                vol.Required(CONF_FETCH_DAY, default=DEFAULT_FETCH_DAY): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=28)
                ),
            }),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        del entry_data
        entry_id = self.context.get("entry_id")
        if not isinstance(entry_id, str):
            return self.async_abort(reason="unknown")
        self._reauth_entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            try:
                entry_data = await self._validate(user_input[CONF_TOKEN_INPUT])
            except EonEnergyAuthError:
                errors["base"] = "invalid_auth"
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
            data_schema=vol.Schema({vol.Required(CONF_TOKEN_INPUT): cv.string}),
            errors=errors,
        )


class EonEnergyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current_day = self._config_entry.options.get(CONF_FETCH_DAY, DEFAULT_FETCH_DAY)

        if user_input is not None:
            return self.async_create_entry(title="", data={
                CONF_FETCH_DAY: user_input[CONF_FETCH_DAY],
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_FETCH_DAY, default=current_day): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=28)
                ),
            }),
        )
