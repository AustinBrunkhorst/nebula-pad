"""Camera platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
import asyncio
from typing import Any
import aiohttp

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_HOST, CONF_CAMERA_PORT

_LOGGER = logging.getLogger(__name__)

DEFAULT_RESOLUTION = (1920, 1080)  # Common resolution for printer cameras

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Camera from a config entry."""
    host = entry.data[CONF_HOST]
    camera_port = entry.data[CONF_CAMERA_PORT]
    
    async_add_entities([NebulaPadCamera(hass, host, camera_port)], True)

class NebulaPadCamera(Camera):
    """Representation of a Nebula Pad Camera."""

    def __init__(self, hass: HomeAssistant, host: str, camera_port: int) -> None:
        """Initialize Nebula Pad Camera."""
        super().__init__()
        
        self.hass = hass
        self._attr_unique_id = f"nebula_pad_camera_{host}_{camera_port}"
        self._attr_name = "Nebula Pad Camera"
        self._attr_frame_interval = 0.1
        self._mjpeg_url = f"http://{host}:{camera_port}/?action=stream"
        self._still_image_url = f"http://{host}:{camera_port}/?action=snapshot"
        self._session = async_get_clientsession(hass)
        self._width = DEFAULT_RESOLUTION[0]
        self._height = DEFAULT_RESOLUTION[1]

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the camera."""
        try:
            async with self._session.get(self._still_image_url) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "Error getting camera image: %s - %s",
                        resp.status,
                        self._still_image_url,
                    )
                    return None
                
                image = await resp.read()
                return image
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Error getting camera image: %s", err)
            return None

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return CameraEntityFeature.STREAM

    @property
    def frame_interval(self) -> float:
        """Return the interval between frames of the MJPEG stream."""
        return self._attr_frame_interval

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self._mjpeg_url
        
    @property
    def is_streaming(self) -> bool:
        """Return true if the device is streaming."""
        return True
        
    @property
    def motion_detection_enabled(self) -> bool:
        """Return the camera motion detection status."""
        return False
        
    @property
    def brand(self) -> str:
        """Return the camera brand."""
        return "Creality"
        
    @property
    def model(self) -> str:
        """Return the camera model."""
        return "Nebula Pad"
        
    @property
    def frontend_stream_type(self) -> str | None:
        """Return the type of stream supported by the camera for use in the frontend."""
        return "hls"  # Use HLS streaming in frontend