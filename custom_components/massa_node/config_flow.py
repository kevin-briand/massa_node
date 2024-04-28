"""Config flow for massa node integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import DOMAIN, IP, PORT, WALLET_ADDRESS  # pylint:disable=unused-import
from custom_components.massa_node.api.node_api import NodeApi

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(IP): str,
    vol.Required(PORT, default=33035): int,
    vol.Required(WALLET_ADDRESS): str
})


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    _LOGGER.info(data[PORT])
    if not 0 < data[PORT] < 65535:
        raise InvalidPort()
    if len(data[WALLET_ADDRESS]) != 53:
        raise InvalidWalletAddress()

    node_api = NodeApi(hass, data[IP], data[PORT], data[WALLET_ADDRESS])

    try:
        result = await node_api.test_connection()
        if not result:
            raise CannotConnect
    except:
        raise CannotConnect

    return {
        IP: data[IP],
        PORT: data[PORT],
        WALLET_ADDRESS: data[WALLET_ADDRESS]
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        # Only a single instance of the integration
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(title="Massa Node", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidPort:
                errors[PORT] = 'invalid_port'
            except InvalidWalletAddress:
                errors[WALLET_ADDRESS] = 'invalid_address'
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors,
        )

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidPort(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid port."""

class InvalidWalletAddress(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid wallet address."""
