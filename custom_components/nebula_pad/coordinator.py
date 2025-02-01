"""Coordinator for Creality Nebula Pad integration."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import WebSocketException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)

class NebulaPadCoordinator:
    """Class to manage WebSocket connection and coordinate updates."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry_id: str,
        host: str, 
        port: int,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self._host = host
        self._port = port
        self._websocket = None
        self._is_initialized = False
        self._device_info = None
        self._hostname = None
        self._message_handlers = []
        self._reconnect_task = None
        self._shutdown = False

    @property
    def hostname(self) -> str | None:
        """Return the hostname of the device."""
        return self._hostname

    @property
    def is_initialized(self) -> bool:
        """Return if the coordinator is initialized."""
        return self._is_initialized

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info."""
        return self._device_info

    def add_message_handler(
        self, 
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """Add a message handler."""
        self._message_handlers.append(handler)

    async def setup(self) -> None:
        """Set up the coordinator."""
        await self._connect()
        self._reconnect_task = asyncio.create_task(self._reconnection_manager())

    async def stop(self) -> None:
        """Stop the coordinator."""
        self._shutdown = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reconnect_task
        await self._disconnect()

    async def send_message(self, message: dict) -> None:
        """Send a message through the WebSocket connection."""
        if not self._websocket:
            _LOGGER.error("Cannot send message - WebSocket not connected")
            return

        try:
            await self._websocket.send(json.dumps(message))
        except WebSocketException as err:
            _LOGGER.error("Error sending message: %s", err)
            await self._handle_disconnect()

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            uri = f"ws://{self._host}:{self._port}/ws"
            self._websocket = await websockets.connect(uri)
            
            # Wait for initial device info message
            message = await self._websocket.recv()
            data = json.loads(message)
            
            if not isinstance(data, dict):
                raise ValueError("Invalid initial message format")
                
            # Process device info
            self._device_info = get_device_info(data, self._host)
            self._hostname = self._device_info["name"]
            self._is_initialized = True
            
            # Start message handler
            self.hass.loop.create_task(self._message_handler())
            
        except (WebSocketException, ValueError) as err:
            _LOGGER.error("Failed to connect to %s: %s", self._host, err)
            await self._handle_disconnect()
            raise

    async def _disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        self._is_initialized = False

    async def _handle_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        self._is_initialized = False
        await self._disconnect()

    async def _reconnection_manager(self) -> None:
        """Manage WebSocket reconnection."""
        while not self._shutdown:
            if not self._websocket:
                try:
                    await self._connect()
                except Exception as err:
                    _LOGGER.error("Reconnection failed: %s", err)
                    await asyncio.sleep(30)  # Wait before retry
            await asyncio.sleep(1)

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        if not self._websocket:
            return

        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict):
                        continue
                        
                    # Process message with all handlers
                    for handler in self._message_handlers:
                        try:
                            await handler(data)
                        except Exception as err:
                            _LOGGER.error("Error in message handler: %s", err)
                            
                except json.JSONDecodeError:
                    _LOGGER.error("Failed to decode message: %s", message)
                    
        except WebSocketException as err:
            _LOGGER.error("WebSocket error: %s", err)
            await self._handle_disconnect()