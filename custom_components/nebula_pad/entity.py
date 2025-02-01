"""Base classes for Nebula Pad entities."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.camera import Camera

from .const import DOMAIN

class NebulaPadBaseMixin:
    """Mixin class for Nebula Pad entities."""

    def __init__(self, coordinator) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator._host)},
            # The rest will be populated from the coordinator's device_info
            **self.coordinator.device_info
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        # Wait for device info to be available before proceeding
        await self.coordinator.wait_for_device_info()

class NebulaPadBaseSensor(NebulaPadBaseMixin, SensorEntity):
    """Base class for Nebula Pad sensors."""

class NebulaPadBaseButton(NebulaPadBaseMixin, ButtonEntity):
    """Base class for Nebula Pad buttons."""

class NebulaPadBaseNumber(NebulaPadBaseMixin, NumberEntity):
    """Base class for Nebula Pad numbers."""

class NebulaPadBaseCamera(NebulaPadBaseMixin, Camera):
    """Base class for Nebula Pad camera."""