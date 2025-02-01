"""WebSocket coordinator for Creality Nebula Pad integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable
from contextlib import suppress

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)

class NebulaPadCoordinator:
    """Manages WebSocket connection and message handling for Nebula Pad."""

    def __init__(
        self, 
        hass: HomeAssistant,
        entry_id: str,
        host: str, 
        port: int, 
        reconnect_interval: int = 5
    ) -> None:
        """Initialize the WebSocket coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self._host = host
        self._port = port
        self._reconnect_interval = reconnect_interval
        self._ws = None
        self._session = None
        self._shutdown = False
        self._connection_task = None
        self._heartbeat_task = None
        self._connect_lock = asyncio.Lock()
        self._message_handlers: list[Callable[[dict], None]] = []
        self._device_info = None
        self._device_info_received = asyncio.Event()

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return self._device_info

    async def wait_for_device_info(self) -> None:
        """Wait for device info to be received."""
        await self._device_info_received.wait()

    def add_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Add a message handler."""
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Remove a message handler."""
        with suppress(ValueError):
            self._message_handlers.remove(handler)

    async def send_message(self, message: dict) -> None:
        """Send a message through the WebSocket connection."""
        if self._ws is None:
            _LOGGER.error("Cannot send message - no WebSocket connection")
            return

        try:
            await self._ws.send_json(message)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to send message: %s", err)

    async def start(self) -> None:
        """Start the WebSocket coordinator."""
        self._shutdown = False
        self._session = aiohttp.ClientSession()
        self._connection_task = asyncio.create_task(self._maintain_connection())
        _LOGGER.info("WebSocket coordinator started for %s:%s", self._host, self._port)

    async def stop(self) -> None:
        """Stop the WebSocket coordinator."""
        self._shutdown = True
        
        if self._connection_task:
            self._connection_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._connection_task
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._heartbeat_task
        
        if self._ws:
            await self._ws.close()
            self._ws = None
            
        if self._session:
            await self._session.close()
            self._session = None
        
        _LOGGER.info("WebSocket coordinator stopped for %s:%s", self._host, self._port)

    def _handle_device_info(self, data: dict) -> None:
        """Handle device info message and register device."""
        if all(key in data for key in ["hostname", "model", "modelVersion"]):
            self._device_info = get_device_info(data, self._host)
            
            # Register device
            device_registry = dr.async_get(self.hass)
            device_registry.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers={(DOMAIN, self._host)},
                **self._device_info,
            )
            
            self._device_info_received.set()
            _LOGGER.info("Device info received: %s", self._device_info)

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
            
            async with self._session.ws_connect(uri) as websocket:
                self._ws = websocket
                _LOGGER.info(
                    "Connected to Nebula Pad WebSocket server at %s:%s",
                    self._host,
                    self._port
                )
                
                self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
                
                try:
                    await self._listen_for_messages()
                finally:
                    if self._heartbeat_task:
                        self._heartbeat_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await self._heartbeat_task
                        self._heartbeat_task = None
                    self._ws = None

    async def _listen_for_messages(self) -> None:
        """Listen for and process WebSocket messages."""
        while not self._shutdown:
            try:
                msg = await self._ws.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == "ok":
                        _LOGGER.debug("Received heartbeat response")
                        continue
                    
                    _LOGGER.debug("Received message: %s", msg.data)
                    
                    try:
                        data = json.loads(msg.data)
                        _LOGGER.debug("Parsed message data: %s", data)
                        
                        # Handle device info
                        self._handle_device_info(data)
                        
                        # Notify all handlers
                        for handler in self._message_handlers:
                            try:
                                await handler(data)
                            except Exception as err:  # pylint: disable=broad-except
                                _LOGGER.error("Error in message handler: %s", err)
                                
                    except json.JSONDecodeError:
                        _LOGGER.error(
                            "Invalid JSON message received from %s:%s - %s",
                            self._host,
                            self._port,
                            msg.data
                        )
                        
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
                    
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error(
                        "Error processing message from %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break

    async def _send_heartbeats(self) -> None:
        """Send periodic heartbeat messages."""
        while not self._shutdown and self._ws:
            try:
                heartbeat = {
                    "ModeCode": "heart_beat",
                    "msg": datetime.now(timezone.utc).isoformat()
                }
                await self.send_message(heartbeat)
                _LOGGER.debug("Sent heartbeat: %s", heartbeat)
                await asyncio.sleep(6)
            except Exception as err:  # pylint: disable=broad-except
                if not self._shutdown:
                    _LOGGER.error(
                        "Error sending heartbeat to %s:%s - %s",
                        self._host,
                        self._port,
                        err
                    )
                break