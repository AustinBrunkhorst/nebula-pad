"""Number platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .coordinator import NebulaPadCoordinator
from .entity import NebulaPadBaseNumber

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        NebulaPadTargetNozzleTemp(coordinator),
        NebulaPadTargetBedTemp(coordinator)
    ]
    
    async def handle_target_update(data: dict) -> None:
        """Process target temperature updates."""
        if not any(key in data for key in ["targetNozzleTemp", "targetBedTemp0"]):
            return
            
        for entity in entities:
            await entity.process_update(data)
    
    coordinator.add_message_handler(handle_target_update)
    async_add_entities(entities, True)

class NebulaPadTempNumber(NebulaPadBaseNumber):
    """Base class for Nebula Pad temperature number entities."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 300
    _attr_native_step = 1

class NebulaPadTargetNozzleTemp(NebulaPadTempNumber):
    """Representation of a Nebula Pad Target Nozzle Temperature control."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_target_nozzle"
        self._attr_name = "Target Nozzle Temperature"

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        command = {
            "method": "set",
            "params": {
                "nozzleTempControl": int(value)
            }
        }
        await self.coordinator.send_message(command)

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "targetNozzleTemp" in data:
            try:
                self._attr_native_value = float(data["targetNozzleTemp"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid target nozzle temperature value")

class NebulaPadTargetBedTemp(NebulaPadTempNumber):
    """Representation of a Nebula Pad Target Bed Temperature control."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._host}_target_bed"
        self._attr_name = "Target Bed Temperature"

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        command = {
            "method": "set",
            "params": {
                "bedTempControl": {
                    "num": 0,
                    "val": int(value)
                }
            }
        }
        await self.coordinator.send_message(command)

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "targetBedTemp0" in data:
            try:
                self._attr_native_value = float(data["targetBedTemp0"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid target bed temperature value")