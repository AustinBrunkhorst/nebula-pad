"""Camera platform for Creality Nebula Pad integration."""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import aiohttp
from aiohttp import web

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession, async_aiohttp_proxy_web

from .const import DOMAIN, CONF_HOST, CONF_CAMERA_PORT
from .entity import NebulaPadBaseCamera

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 10
BUFFER_SIZE = 102400

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Camera from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    host = entry.data[CONF_HOST]
    camera_port = entry.data[CONF_CAMERA_PORT]
    
    async_add_entities([NebulaPadCamera(coordinator, host, camera_port)], True)

class NebulaPadCamera(NebulaPadBaseCamera):
    """Representation of a Nebula Pad Camera."""

    def __init__(self, coordinator: NebulaPadCoordinator, host: str, camera_port: int) -> None:
        """Initialize Nebula Pad Camera."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"nebula_pad_{host}_camera"
        self._attr_name = "Nebula Pad Camera"
        self._host = host
        self._port = camera_port
        
        # URLs for camera endpoints
        self._mjpeg_url = f"http://{host}:{camera_port}/?action=stream"
        self._still_url = f"http://{host}:{camera_port}/?action=snapshot"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        websession = async_get_clientsession(self.hass)
        
        try:
            async with asyncio.timeout(TIMEOUT):
                async with websession.get(self._still_url) as response:
                    return await response.read()

        except TimeoutError:
            _LOGGER.error("Timeout getting camera image from %s", self.name)
            return None

        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting camera image from %s: %s", self.name, err)
            return None

    async def stream_source(self) -> str:
        """Return the source of the stream."""
        return self._mjpeg_url

    async def handle_async_mjpeg_stream(self, request: web.Request) -> web.StreamResponse:
        """Generate an HTTP MJPEG stream from the camera."""
        websession = async_get_clientsession(self.hass)
        stream_coro = websession.get(
            self._mjpeg_url,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        )

        return await async_aiohttp_proxy_web(self.hass, request, stream_coro)