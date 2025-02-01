"""Base classes for Nebula Pad entities."""
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.camera import Camera

from .const import DOMAIN

class NebulaPadBaseMixin(Entity):
    """Mixin class for Nebula Pad entities."""

    def __init__(self, coordinator) -> None:
        """Initialize the entity."""
        super().__init__()
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if not self.coordinator.is_initialized:
            return None
            
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator._host)},
            **self.coordinator.device_info
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.is_initialized

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

class NebulaPadBaseSensor(NebulaPadBaseMixin, SensorEntity):
    """Base class for Nebula Pad sensors."""

class NebulaPadBaseButton(NebulaPadBaseMixin, ButtonEntity):
    """Base class for Nebula Pad buttons."""

class NebulaPadBaseNumber(NebulaPadBaseMixin, NumberEntity):
    """Base class for Nebula Pad numbers."""

class NebulaPadBaseCamera(NebulaPadBaseMixin, Camera):
    """Base class for Nebula Pad camera."""