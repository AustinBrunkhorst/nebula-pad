"""Platform for Creality Nebula Pad sensor integration."""
from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Any, Callable
from contextlib import suppress

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_HOST, CONF_WS_PORT

_LOGGER = logging.getLogger(__name__)

class WebSocketCoordinator:
    """Manages WebSocket connection and message handling."""

    def __init__(
        self, 
        host: str, 
        port: int, 
        message_handler: Callable[[dict], None],
        reconnect_interval: int = 5
    ) -> None:
        """Initialize the WebSocket coordinator.
        
        Args:
            host: WebSocket server host
            port: WebSocket server port
            message_handler: Callback for handling parsed JSON messages
            reconnect_interval: Seconds to wait between reconnection attempts
        """
        self._host = host
        self._port = port
        self._message_handler = message_handler
        self._reconnect_interval = reconnect_interval
        self._ws = None
        self._shutdown = False
        self._connection_task = None
        self._heartbeat_task = None
        self._connect_lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the WebSocket coordinator."""
        self._shutdown = False
        self._connection_task = asyncio.create_task(self._maintain_connection())
        _LOGGER.info("WebSocket coordinator started for %s:%s", self._host, self._port)

    async def stop(self) -> None:
        """Stop the WebSocket coordinator."""
        self._shutdown = True
        
        # Cancel tasks
        if self._connection_task:
            self._connection_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._connection_task
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._heartbeat_task
        
        # Close connection
        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._ws = None
        
        _LOGGER.info("WebSocket coordinator stopped for %s:%s", self._host, self._port)

    async def _maintain_connection(self) -> None:
        """Maintain the WebSocket connection and handle reconnection."""
        while not self._shutdown:
            try:
                await self._connect_and_listen()
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error(
                        "WebSocket error for %s:%s - %s", 
                        self._host, self._port, err
                    )
                    await asyncio.sleep(self._reconnect_interval)

    async def _connect_and_listen(self) -> None:
        """Establish WebSocket connection and handle messages."""
        async with self._connect_lock:
            if self._shutdown:
                return
                
            uri = f"ws://{self._host}:{self._port}"
            _LOGGER.debug("Attempting to connect to %s", uri)
            
            async with websockets.connect(uri, ping_interval=None) as websocket:
                self._ws = websocket
                _LOGGER.info(
                    "Connected to Nebula Pad WebSocket server at %s:%s",
                    self._host,
                    self._port
                )
                
                # Start heartbeat when connection is established
                self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
                
                try:
                    await self._listen_for_messages()
                finally:
                    # Clean up heartbeat task when connection ends
                    if self._heartbeat_task:
                        self._heartbeat_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await self._heartbeat_task
                        self._heartbeat_task = None

    async def _listen_for_messages(self) -> None:
        """Listen for and process WebSocket messages."""
        while not self._shutdown:
            try:
                message = await self._ws.recv()
                
                # Log heartbeat responses
                if message == "ok":
                    _LOGGER.debug("Received heartbeat response")
                    continue
                
                # Log received message
                _LOGGER.debug("Received message: %s", message)
                
                # Parse and handle JSON messages
                try:
                    data = json.loads(message)
                    _LOGGER.debug("Parsed message data: %s", data)
                    await self._message_handler(data)
                except json.JSONDecodeError:
                    _LOGGER.error(
                        "Invalid JSON message received from %s:%s - %s",
                        self._host,
                        self._port,
                        message
                    )
                    
            except ConnectionClosed as err:
                if not self._shutdown:
                    _LOGGER.info(
                        "WebSocket connection closed for %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break
            except WebSocketException as err:
                if not self._shutdown:
                    _LOGGER.error(
                        "WebSocket error for %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error(
                        "Error processing message from %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )

    async def _send_heartbeats(self) -> None:
        """Send periodic heartbeat messages."""
        while not self._shutdown and self._ws and not self._ws.closed:
            try:
                heartbeat = {
                    "ModeCode": "heart_beat",
                    "msg": datetime.now(timezone.utc).isoformat()
                }
                await self._ws.send(json.dumps(heartbeat))
                _LOGGER.debug("Sent heartbeat: %s", heartbeat)
                await asyncio.sleep(6)
            except ConnectionClosed as err:
                if not self._shutdown:
                    _LOGGER.info(
                        "Connection closed while sending heartbeat to %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error(
                        "Error sending heartbeat to %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Sensor from a config entry."""
    host = entry.data[CONF_HOST]
    ws_port = entry.data[CONF_WS_PORT]
    
    entities = [
        NebulaPadNozzleTempSensor(host, ws_port),
        NebulaPadBedTempSensor(host, ws_port)
    ]
    
    # Create coordinator with message handler
    async def handle_temperature_update(data: dict) -> None:
        """Process temperature updates for all sensors."""
        if not any(key in data for key in ["nozzleTemp", "bedTemp0"]):
            return
            
        for entity in entities:
            await entity.process_update(data)
    
    coordinator = WebSocketCoordinator(
        host=host,
        port=ws_port,
        message_handler=handle_temperature_update
    )
    
    # Set coordinator for all entities
    for entity in entities:
        entity.set_coordinator(coordinator)
    
    async_add_entities(entities, True)

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

    def set_coordinator(self, coordinator: WebSocketCoordinator) -> None:
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