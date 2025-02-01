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
        AutoHomeZButton(coordinator),
        PausePrintButton(coordinator),
        ResumePrintButton(coordinator),
        StopPrintButton(coordinator),
    ]
    
    async_add_entities(entities, True)

class AutoHomeXYButton(NebulaPadBaseButton):
    """Button to auto-home X and Y axes."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_autohome_xy"
        self._attr_name = "Auto-Home XY"

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
        self._attr_unique_id = f"{coordinator._host}_autohome_z"
        self._attr_name = "Auto-Home Z"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "autohome": "Z"
            }
        }
        await self.coordinator.send_message(command)

class PausePrintButton(NebulaPadBaseButton):
    """Button to pause the current print."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_pause_print"
        self._attr_name = "Pause Print"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "pause": 1
            }
        }
        await self.coordinator.send_message(command)

class ResumePrintButton(NebulaPadBaseButton):
    """Button to resume the paused print."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_resume_print"
        self._attr_name = "Resume Print"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "pause": 0
            }
        }
        await self.coordinator.send_message(command)

class StopPrintButton(NebulaPadBaseButton):
    """Button to stop the current print."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_stop_print"
        self._attr_name = "Stop Print"

    async def async_press(self) -> None:
        """Handle the button press."""
        command = {
            "method": "set",
            "params": {
                "stop": 1
            }
        }
        await self.coordinator.send_message(command)