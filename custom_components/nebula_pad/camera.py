"""Camera platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
import asyncio
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_HOST, CONF_CAMERA_PORT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Camera from a config entry."""
    host = entry.data[CONF_HOST]
    camera_port = entry.data[CONF_CAMERA_PORT]
    
    async_add_entities([NebulaPadCamera(host, camera_port)], True)

class NebulaPadCamera(Camera):
    """Representation of a Nebula Pad Camera."""

    def __init__(self, host: str, camera_port: int) -> None:
        """Initialize Nebula Pad Camera."""
        super().__init__()
        
        self._attr_unique_id = f"nebula_pad_camera_{host}_{camera_port}"
        self._attr_name = "Nebula Pad Camera"
        self._attr_frame_interval = 0.5
        self._mjpeg_url = f"http://{host}:{camera_port}/?action=stream"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        # This method is not needed for MJPEG streams
        return None

    @property
    def is_streaming(self) -> bool:
        """Return true if the device is streaming."""
        return True

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return CameraEntityFeature.STREAM

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self._mjpeg_url