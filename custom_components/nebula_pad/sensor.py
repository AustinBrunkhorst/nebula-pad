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
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _maintain_connection(self) -> None:
        """Maintain the WebSocket connection and handle reconnection."""
        while not self._shutdown:
            try:
                await self._connect_and_listen()
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error("WebSocket error: %s", err)
                    await asyncio.sleep(self._reconnect_interval)

    async def _connect_and_listen(self) -> None:
        """Establish WebSocket connection and handle messages."""
        async with self._connect_lock:
            if self._shutdown:
                return
                
            uri = f"ws://{self._host}:{self._port}"
            _LOGGER.debug("Connecting to WebSocket at %s", uri)
            
            async with websockets.connect(uri) as websocket:
                self._ws = websocket
                _LOGGER.info("Connected to Nebula Pad WebSocket server")
                
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
                _LOGGER.debug("Received message: %s", message)
                
                # Handle plaintext "ok" responses from heartbeat
                if message == "ok":
                    _LOGGER.debug("Received heartbeat acknowledgment")
                    continue
                
                # Parse and handle JSON messages
                try:
                    data = json.loads(message)
                    _LOGGER.debug("Parsed message data: %s", data)
                    if "nozzleTemp" in data or "bedTemp0" in data:
                        await self._message_handler(data)
                except json.JSONDecodeError:
                    _LOGGER.error("Received invalid message: %s", message)
                    
            except ConnectionClosed:
                _LOGGER.info("WebSocket connection closed")
                break
            except WebSocketException as err:
                _LOGGER.error("WebSocket error: %s", err)
                break