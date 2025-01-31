"""WebSocket coordinator for Creality Nebula Pad integration."""
from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Any, Callable
from contextlib import suppress

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

_LOGGER = logging.getLogger(__name__)

class NebulaPadCoordinator:
    """Manages WebSocket connection and message handling for Nebula Pad."""

    def __init__(
        self, 
        host: str, 
        port: int, 
        reconnect_interval: int = 5
    ) -> None:
        """Initialize the WebSocket coordinator.
        
        Args:
            host: WebSocket server host
            port: WebSocket server port
            reconnect_interval: Seconds to wait between reconnection attempts
        """
        self._host = host
        self._port = port
        self._reconnect_interval = reconnect_interval
        self._ws = None
        self._shutdown = False
        self._connection_task = None
        self._heartbeat_task = None
        self._connect_lock = asyncio.Lock()
        self._message_handlers: list[Callable[[dict], None]] = []

    @property
    def websocket(self):
        """Return the current websocket connection."""
        return self._ws

    def add_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Add a message handler."""
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Remove a message handler."""
        with suppress(ValueError):
            self._message_handlers.remove(handler)

    async def start(self) -> None:
        """Start the WebSocket coordinator."""
        self._shutdown = False
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
                
                self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
                
                try:
                    await self._listen_for_messages()
                finally:
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
                
                if message == "ok":
                    _LOGGER.debug("Received heartbeat response")
                    continue
                
                _LOGGER.debug("Received message: %s", message)
                
                try:
                    data = json.loads(message)
                    _LOGGER.debug("Parsed message data: %s", data)
                    
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