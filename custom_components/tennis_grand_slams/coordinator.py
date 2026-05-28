"""Coordinator for Tennis Grand Slams."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ESPNClient, TennisData, TennisGrandSlamError
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

_LOGGER = logging.getLogger(__name__)


class TennisGrandSlamCoordinator(DataUpdateCoordinator[TennisData]):
    """Fetch tennis data with one shared coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        options = {**entry.data, **entry.options}
        self.client = ESPNClient(
            async_get_clientsession(hass),
            region=options.get(CONF_REGION, DEFAULT_REGION),
            language=options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            days_ahead=int(options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD)),
        )
        interval = int(options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
        )

    async def _async_update_data(self) -> TennisData:
        try:
            return await self.client.async_get_data()
        except TennisGrandSlamError as exc:
            raise UpdateFailed(str(exc)) from exc
