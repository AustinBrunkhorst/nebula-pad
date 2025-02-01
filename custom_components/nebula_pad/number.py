"""Number platform for Creality Nebula Pad integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .coordinator import NebulaPadCoordinator
from .entity import NebulaPadBaseNumber

_LOGGER = logging.getLogger(__name__)

@dataclass
class NumberDefinition:
    """Class to define number control properties and update behavior."""
    key: str  # WebSocket payload key for updates
    name: str
    command_method: str  # Command method for setting value
    command_key: str    # Key in params for setting value
    native_min_value: float = 0
    native_max_value: float = 300
    native_step: float = 1
    mode: NumberMode = NumberMode.BOX
    native_unit: str | None = None
    value_fn: Callable[[Any], float] = float  # Default conversion function
    suggested_display_precision: int | None = 0

    def create_command(self, value: float) -> dict[str, Any]:
        """Create command dictionary for setting value."""
        if self.key == "targetBedTemp0":
            # Special case for bed temperature
            return {
                "method": self.command_method,
                "params": {
                    self.command_key: {
                        "num": 0,
                        "val": int(value)
                    }
                }
            }
        return {
            "method": self.command_method,
            "params": {
                self.command_key: int(value)
            }
        }

TEMPERATURE_DEFINITIONS = [
    NumberDefinition(
        key="targetNozzleTemp",
        name="Nozzle target",
        command_method="set",
        command_key="nozzleTempControl",
        native_unit=UnitOfTemperature.CELSIUS,
    ),
    NumberDefinition(
        key="targetBedTemp0",
        name="Bed target",
        command_method="set",
        command_key="bedTempControl",
        native_unit=UnitOfTemperature.CELSIUS,
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        NebulaPadNumber(coordinator, definition)
        for definition in TEMPERATURE_DEFINITIONS
    ]
    
    async def handle_update(data: dict) -> None:
        """Process updates for all number entities."""
        for entity in entities:
            if entity.definition.key in data:
                try:
                    entity._attr_native_value = entity.definition.value_fn(data[entity.definition.key])
                    entity.async_write_ha_state()
                except (ValueError, TypeError) as err:
                    _LOGGER.error(
                        "Invalid value for %s: %s",
                        entity.definition.name,
                        err
                    )
    
    coordinator.add_message_handler(handle_update)
    async_add_entities(entities, True)

class NebulaPadNumber(NebulaPadBaseNumber):
    """Representation of a Nebula Pad number control."""

    def __init__(
        self,
        coordinator: NebulaPadCoordinator,
        definition: NumberDefinition,
    ) -> None:
        """Initialize the number control."""
        super().__init__(coordinator)
        self.definition = definition
        
        # Set up entity attributes based on definition
        self._attr_unique_id = f"{coordinator._host}_{definition.key}"
        self._attr_name = definition.name
        self._attr_native_unit_of_measurement = definition.native_unit
        self._attr_native_min_value = definition.native_min_value
        self._attr_native_max_value = definition.native_max_value
        self._attr_native_step = definition.native_step
        self._attr_mode = definition.mode
        self._attr_suggested_display_precision = definition.suggested_display_precision

    async def async_set_native_value(self, value: float) -> None:
        """Set new target value."""
        command = self.definition.create_command(value)
        await self.coordinator.send_message(command)