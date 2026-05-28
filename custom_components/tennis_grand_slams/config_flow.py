"""Config flow for Tennis Grand Slams."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DAYS_AHEAD,
    CONF_LANGUAGE,
    CONF_REGION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_LANGUAGE,
    DEFAULT_REGION,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Tennis Grand Slams"): str,
        vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): str,
        vol.Optional(CONF_DAYS_AHEAD, default=DEFAULT_DAYS_AHEAD): vol.All(vol.Coerce(int), vol.Range(min=30, max=800)),
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=5, max=240)),
    }
)


class TennisGrandSlamsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        title = user_input.pop(CONF_NAME)
        return self.async_create_entry(title=title, data=user_input)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return TennisGrandSlamsOptionsFlow(config_entry)


class TennisGrandSlamsOptionsFlow(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        data = {**self._config_entry.data, **self._config_entry.options}
        schema = vol.Schema(
            {
                vol.Optional(CONF_REGION, default=data.get(CONF_REGION, DEFAULT_REGION)): str,
                vol.Optional(CONF_LANGUAGE, default=data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)): str,
                vol.Optional(CONF_DAYS_AHEAD, default=data.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD)): vol.All(vol.Coerce(int), vol.Range(min=30, max=800)),
                vol.Optional(CONF_UPDATE_INTERVAL, default=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=5, max=240)),
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=schema)
        return self.async_create_entry(title="", data=user_input)
