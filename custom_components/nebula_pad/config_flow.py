from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import websockets
import json
from datetime import datetime, timezone

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_HOST, CONF_PORT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): int,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    try:
        uri = f"ws://{data[CONF_HOST]}:{data[CONF_PORT]}"
        async with websockets.connect(uri) as websocket:
            # Send initial heartbeat
            heartbeat = {
                "ModeCode": "heart_beat",
                "msg": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(heartbeat))
            # Wait for a response
            response = await websocket.recv()
            
    except Exception as err:
        raise CannotConnect from err

    return {"title": f"Nebula Pad {data[CONF_HOST]}:{data[CONF_PORT]}"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Creality Nebula Pad."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""