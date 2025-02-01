"""WebSocket coordinator for Creality Nebula Pad integration."""
from __future__ import annotations

import asyncio
import json
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
        self._hostname = None
        self._setup_complete = asyncio.Event()

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return self._device_info

    @property
    def hostname(self) -> str | None:
        """Return the device hostname."""
        return self._hostname

    @property
    def is_initialized(self) -> bool:
        """Return True if device info is available."""
        return self._device_info is not None

    def _handle_device_info(self, data: dict) -> None:
        """Handle device info message and register device."""
        if all(key in data for key in ["hostname", "model", "modelVersion"]):
            self._hostname = data["hostname"]
            if not self._hostname or self._hostname.strip() == "":
                self._hostname = f"Nebula Pad {self._host}"
                
            self._device_info = get_device_info(data, self._host)
            
            # Register device
            device_registry = dr.async_get(self.hass)
            device_registry.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers={(DOMAIN, self._host)},
                **self._device_info,
            )
            
            self._setup_complete.set()
            _LOGGER.info("Device info received: %s", self._device_info)