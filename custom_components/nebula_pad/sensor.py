"""Platform for Creality Nebula Pad sensor integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable
from enum import IntEnum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfTime,
)

from .const import DOMAIN
from .coordinator import NebulaPadCoordinator
from .entity import NebulaPadBaseSensor

_LOGGER = logging.getLogger(__name__)

class PrinterState(IntEnum):
    """Enum for printer state."""
    STOPPED = 0
    PRINTING = 1
    COMPLETE = 2
    ABORTED = 4
    PAUSED = 5

@dataclass
class SensorDefinition:
    """Class to define sensor properties and update behavior."""
    key: str  # WebSocket payload key
    name: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT
    native_unit: str | None = None
    value_fn: Callable[[Any], Any] = float  # Default conversion function
    suggested_display_precision: int | None = None
    suggested_unit_of_measurement: str | None = None

def map_printer_state(value: Any) -> str:
    """Map printer state integer to string representation."""
    try:
        state = PrinterState(int(value))
        return state.name
    except (ValueError, TypeError):
        return "UNKNOWN"

def parse_position(position_str: str, axis: str) -> float | None:
    """Parse position string to extract specific axis value."""
    try:
        # Expected format: "X:98.93 Y:103.03 Z:63.95"
        for part in position_str.split():
            if part.startswith(f"{axis}:"):
                return float(part[2:])
        return None
    except (ValueError, AttributeError):
        return None

SENSOR_DEFINITIONS = [
    SensorDefinition(
        key="usedMaterialLength",
        name="Used material length",
        native_unit="mm",
        value_fn=int,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDefinition(
        key="realTimeSpeed",
        name="Print speed",
        native_unit="mm/s",
        value_fn=lambda x: round(float(x), 1),
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="realTimeFlow",
        name="Flow rate",
        native_unit="mm³/s",
        value_fn=lambda x: round(float(x), 1),
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="curPosition_x",
        name="X Position",
        native_unit="mm",
        value_fn=lambda x: parse_position(x, "X"),
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="curPosition_y", 
        name="Y Position",
        native_unit="mm",
        value_fn=lambda x: parse_position(x, "Y"),
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="curPosition_z",
        name="Z Position",
        native_unit="mm",
        value_fn=lambda x: parse_position(x, "Z"),
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="nozzleTemp",
        name="Nozzle temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit=UnitOfTemperature.CELSIUS,
    ),
    SensorDefinition(
        key="bedTemp0",
        name="Bed temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit=UnitOfTemperature.CELSIUS,
    ),
    SensorDefinition(
        key="TotalLayer",
        name="Total layers",
        value_fn=int,
    ),
    SensorDefinition(
        key="layer",
        name="Current layer",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=int,
    ),
    SensorDefinition(
        key="printProgress",
        name="Print progress",
        native_unit=PERCENTAGE,
        suggested_display_precision=0,  # Show as whole numbers
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDefinition(
        key="printJobTime",
        name="Print time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="printLeftTime",
        name="Remaining time",
        device_class=SensorDeviceClass.DURATION,
        native_unit=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
    ),
    SensorDefinition(
        key="state",
        name="State",
        value_fn=map_printer_state,
        state_class=None,  # State doesn't need a state class
    ),
    SensorDefinition(
        key="deviceState",
        name="Device state",
        value_fn=str,  # Keep raw value
        state_class=None,  # State doesn't need a state class
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Creality Nebula Pad Sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        NebulaPadSensor(coordinator, definition)
        for definition in SENSOR_DEFINITIONS
    ]
    
    # Create a single message handler for all sensors
    async def handle_update(data: dict) -> None:
        """Process updates for all sensors."""
        for entity in entities:
            try:
                if entity.definition.key.startswith("curPosition_"):
                    # Handle position sensors which all use the curPosition data
                    if "curPosition" in data:
                        entity._attr_native_value = entity.definition.value_fn(data["curPosition"])
                        entity.async_write_ha_state()
                elif entity.definition.key in data:
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

class NebulaPadSensor(NebulaPadBaseSensor):
    """Representation of a Nebula Pad sensor."""

    def __init__(
        self,
        coordinator: NebulaPadCoordinator,
        definition: SensorDefinition,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.definition = definition
        
        # Set up entity attributes based on definition
        self._attr_unique_id = f"{coordinator._host}_{definition.key}"
        self._attr_name = definition.name
        self._attr_device_class = definition.device_class
        self._attr_state_class = definition.state_class
        self._attr_native_unit_of_measurement = definition.native_unit
        self._attr_suggested_display_precision = definition.suggested_display_precision
        self._attr_suggested_unit_of_measurement = definition.suggested_unit_of_measurement