"""Number platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
import json
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .coordinator import NebulaPadCoordinator

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

class NebulaPadBaseNumber(NumberEntity):
    """Base class for Nebula Pad number entities."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 300
    _attr_native_step = 1

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity being removed from Home Assistant."""
        await super().async_will_remove_from_hass()

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        raise NotImplementedError

class NebulaPadTargetNozzleTemp(NebulaPadBaseNumber):
    """Representation of a Nebula Pad Target Nozzle Temperature control."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_target_nozzle"
        self._attr_name = "Nebula Pad Target Nozzle Temperature"

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        if self.coordinator.websocket and not self.coordinator.websocket.closed:
            command = {
                "method": "set",
                "params": {
                    "nozzleTempControl": int(value)
                }
            }
            await self.coordinator.websocket.send(json.dumps(command))

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "targetNozzleTemp" in data:
            try:
                self._attr_native_value = float(data["targetNozzleTemp"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid target nozzle temperature value")

class NebulaPadTargetBedTemp(NebulaPadBaseNumber):
    """Representation of a Nebula Pad Target Bed Temperature control."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_target_bed"
        self._attr_name = "Nebula Pad Target Bed Temperature"

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        if self.coordinator.websocket and not self.coordinator.websocket.closed:
            command = {
                "method": "set",
                "params": {
                    "bedTempControl": {
                        "num": 0,
                        "val": int(value)
                    }
                }
            }
            await self.coordinator.websocket.send(json.dumps(command))

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "targetBedTemp0" in data:
            try:
                self._attr_native_value = float(data["targetBedTemp0"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid target bed temperature value")