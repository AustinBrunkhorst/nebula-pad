"""The Creality Nebula Pad integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_HOST, CONF_WS_PORT
from .coordinator import NebulaPadCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.CAMERA,
    Platform.NUMBER,
]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Creality Nebula Pad from a config entry."""
    # Initialize the coordinator
    coordinator = NebulaPadCoordinator(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_WS_PORT],
    )

    # Store coordinator and entry data in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry.data,
    }

    # Start the coordinator
    await coordinator.start()

    # Forward the setup to all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms first
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Stop the coordinator if platforms were unloaded successfully
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.stop()
        
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok