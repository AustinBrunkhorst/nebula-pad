"""Platform for Creality Nebula Pad sensor integration."""
from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Any

import websockets

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN, CONF_HOST, CONF_PORT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Sensor from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    
    entities = [
        NebulaPadNozzleTempSensor(host, port),
        NebulaPadBedTempSensor(host, port)
    ]
    
    coordinator = NebulaPadCoordinator(host, port, entities)
    for entity in entities:
        entity.set_coordinator(coordinator)
    
    async_add_entities(entities, True)

class NebulaPadCoordinator:
    """Class to coordinate shared websocket connection between sensors."""
    
    def __init__(self, host: str, port: int, entities: list) -> None:
        """Initialize the coordinator."""
        self._host = host
        self._port = port
        self._entities = entities
        self._websocket = None
        self._task = None
        self._heartbeat_task = None

    async def start(self) -> None:
        """Start the coordinator."""
        self._task = asyncio.create_task(self._async_listen())
        self._heartbeat_task = asyncio.create_task(self._async_heartbeat())

    async def stop(self) -> None:
        """Stop the coordinator."""
        if self._task:
            self._task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._websocket:
            await self._websocket.close()

    async def _async_heartbeat(self) -> None:
        """Send periodic heartbeats."""
        while True:
            try:
                if self._websocket:
                    heartbeat = {
                        "ModeCode": "heart_beat",
                        "msg": datetime.now(timezone.utc).isoformat()
                    }
                    await self._websocket.send(json.dumps(heartbeat))
            except Exception as err:
                _LOGGER.error("Error sending heartbeat: %s", err)
            
            await asyncio.sleep(6)  # Send heartbeat every 6 seconds

    async def _async_listen(self) -> None:
        """Listen to the websocket for updates."""
        uri = f"ws://{self._host}:{self._port}"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    self._websocket = websocket
                    _LOGGER.info("Connected to Nebula Pad WebSocket server")
                    
                    while True:
                        try:
                            message = await websocket.recv()
                            try:
                                data = json.loads(message)
                                if "nozzleTemp" in data or "bedTemp0" in data:
                                    for entity in self._entities:
                                        await entity.process_update(data)
                            except json.JSONDecodeError:
                                _LOGGER.error("Received invalid JSON")
                        except websockets.ConnectionClosed:
                            break
                            
            except Exception as err:
                _LOGGER.error("Error connecting to WebSocket server: %s", err)
                await asyncio.sleep(5)  # Wait before retrying

class NebulaPadBaseSensor(SensorEntity):
    """Base class for Nebula Pad sensors."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_should_poll = False

    def __init__(self, host: str, port: int) -> None:
        """Initialize the sensor."""
        self._host = host
        self._port = port
        self._coordinator = None

    def set_coordinator(self, coordinator: NebulaPadCoordinator) -> None:
        """Set the coordinator for this sensor."""
        self._coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        if self._coordinator:
            await self._coordinator.start()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity being removed from Home Assistant."""
        if self._coordinator:
            await self._coordinator.stop()

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        raise NotImplementedError

class NebulaPadNozzleTempSensor(NebulaPadBaseSensor):
    """Representation of a Nebula Pad Nozzle Temperature Sensor."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the sensor."""
        super().__init__(host, port)
        self._attr_unique_id = f"nebula_pad_nozzle_{host}_{port}"
        self._attr_name = f"Nebula Pad Nozzle Temperature"

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

    def __init__(self, host: str, port: int) -> None:
        """Initialize the sensor."""
        super().__init__(host, port)
        self._attr_unique_id = f"nebula_pad_bed_{host}_{port}"
        self._attr_name = f"Nebula Pad Bed Temperature"

    async def process_update(self, data: dict) -> None:
        """Process update from websocket."""
        if "bedTemp0" in data:
            try:
                self._attr_native_value = float(data["bedTemp0"])
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Invalid bed temperature value")