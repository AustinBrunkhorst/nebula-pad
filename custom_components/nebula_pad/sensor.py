"""Platform for Creality Nebula Pad sensor integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    """Set up Creality Nebula Pad Sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        NebulaPadNozzleTempSensor(coordinator),
        NebulaPadBedTempSensor(coordinator)
    ]
    
    async def handle_temperature_update(data: dict) -> None:
        """Process temperature updates for all sensors."""
        if not any(key in data for key in ["nozzleTemp", "bedTemp0"]):
            return
            
        for entity in entities:
            await entity.process_update(data)
    
    coordinator.add_message_handler(handle_temperature_update)
    async_add_entities(entities, True)

class NebulaPadBaseSensor(SensorEntity):
    """Base class for Nebula Pad sensors."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_should_poll = False

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the sensor."""
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

class NebulaPadNozzleTempSensor(NebulaPadBaseSensor):
    """Representation of a Nebula Pad Nozzle Temperature Sensor."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_nozzle"
        self._attr_name = "Nebula Pad Nozzle Temperature"

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "nozzleTemp" in data:
            try:
                self._attr_native_value = float(data["nozzleTemp"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid nozzle temperature value")

class NebulaPadBedTempSensor(NebulaPadBaseSensor):
    """Representation of a Nebula Pad Bed Temperature Sensor."""

    def __init__(self, coordinator: NebulaPadCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"nebula_pad_bed"
        self._attr_name = "Nebula Pad Bed Temperature"

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "bedTemp0" in data:
            try:
                self._attr_native_value = float(data["bedTemp0"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid bed temperature value")