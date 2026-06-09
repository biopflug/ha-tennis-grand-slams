"""Tennis Grand Slams integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import TennisGrandSlamCoordinator

FRONTEND_PATH = Path(__file__).parent / "frontend"
DATA_FRONTEND_REGISTERED = "frontend_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tennis Grand Slams from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(DATA_FRONTEND_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"/{DOMAIN}/frontend",
                    str(FRONTEND_PATH),
                    True,
                )
            ]
        )
        domain_data[DATA_FRONTEND_REGISTERED] = True
    coordinator = TennisGrandSlamCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
