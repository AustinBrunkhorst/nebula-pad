"""Button platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NebulaPadCoordinator
from .entity import NebulaPadBaseButton

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Button entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        AutoHomeXYButton(coordinator),
        AutoHomeZButton(coordinator)
    ]
    
    async_add_entities(entities, True)

class AutoHomeXYButton(NebulaPadBaseButton):
    """Button to auto-home X and Y axes."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_{coordinator._host}_autohome_xy"
        self._attr_name = "Nebula Pad Auto-Home XY"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "autohome": "X Y"
            }
        }
        await self.coordinator.send_message(command)

class AutoHomeZButton(NebulaPadBaseButton):
    """Button to auto-home Z axis."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_{coordinator._host}_autohome_z"
        self._attr_name = "Nebula Pad Auto-Home Z"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "autohome": "Z"
            }
        }
        await self.coordinator.send_message(command)