"""The Multiroom AV integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigType
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .graph import MultiroomGraph

_PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
]
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multiroom AV from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    if entry.data["type"] == "players":
        await hass.data[DOMAIN].async_setup_entry(entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Multiroom AV basic configuration."""
    hass.data[DOMAIN] = MultiroomGraph(hass)
    return True
