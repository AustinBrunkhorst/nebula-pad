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
        self.coordinator = coordinator
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
    def entity_id(self) -> str:
        """Return the entity ID."""
        if not hasattr(self, '_attr_unique_id'):
            return None
            
        unique_parts = self._attr_unique_id.split('_')
        host_part = '_'.join(unique_parts[2:-1]).replace('.', '_')
        name_part = unique_parts[-1]
        
        if isinstance(self, SensorEntity):
            platform = "sensor"
        elif isinstance(self, ButtonEntity):
            platform = "button"
        elif isinstance(self, NumberEntity):
            platform = "number"
        elif isinstance(self, Camera):
            platform = "camera"
        else:
            platform = "unknown"
            
        return f"{platform}.nebula_pad_{host_part}_{name_part}"

class NebulaPadBaseSensor(NebulaPadBaseMixin, SensorEntity):
    """Base class for Nebula Pad sensors."""

class NebulaPadBaseButton(NebulaPadBaseMixin, ButtonEntity):
    """Base class for Nebula Pad buttons."""

class NebulaPadBaseNumber(NebulaPadBaseMixin, NumberEntity):
    """Base class for Nebula Pad numbers."""

class NebulaPadBaseCamera(NebulaPadBaseMixin, Camera):
    """Base class for Nebula Pad camera."""