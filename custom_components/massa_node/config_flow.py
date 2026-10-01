"""Config flow for the Massa Node integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .api import MassaApiError, NodeApi
from .const import CONF_WALLET_ADDRESS, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# User addresses start with "AU" followed by a base58 string.
ADDRESS_RE = re.compile(r"^AU[1-9A-HJ-NP-Za-km-z]{40,60}$")


def _schema(defaults: dict[str, Any], with_wallet: bool = True) -> vol.Schema:
    schema = vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): TextSelector(),
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
                ),
                vol.Coerce(int),
            ),
        }
    )
    if with_wallet:
        schema = schema.extend(
            {
                vol.Required(
                    CONF_WALLET_ADDRESS,
                    default=defaults.get(CONF_WALLET_ADDRESS, vol.UNDEFINED),
                ): TextSelector(),
            }
        )
    return schema


class MassaNodeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration of a Massa node wallet."""

    VERSION = 2

    async def _async_validate(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Return the form errors, empty if the input is valid."""
        user_input[CONF_HOST] = user_input[CONF_HOST].strip()
        user_input[CONF_WALLET_ADDRESS] = user_input[CONF_WALLET_ADDRESS].strip()

        if not ADDRESS_RE.match(user_input[CONF_WALLET_ADDRESS]):
            return {CONF_WALLET_ADDRESS: "invalid_address"}

        api = NodeApi(
            async_get_clientsession(self.hass), user_input[CONF_HOST], user_input[CONF_PORT]
        )
        try:
            await api.get_status()
            address = await api.get_address(user_input[CONF_WALLET_ADDRESS])
        except MassaApiError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error while validating the node")
            return {"base": "unknown"}
        if address is None:
            return {CONF_WALLET_ADDRESS: "address_not_found"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._async_validate(user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_WALLET_ADDRESS])
                self._abort_if_unique_id_configured()
                wallet = user_input[CONF_WALLET_ADDRESS]
                return self.async_create_entry(
                    title=f"Massa Node ({wallet[:6]}…{wallet[-4:]})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the host or port of an existing entry (the wallet identifies the entry)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {**user_input, CONF_WALLET_ADDRESS: entry.data[CONF_WALLET_ADDRESS]}
            errors = await self._async_validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or dict(entry.data), with_wallet=False),
            errors=errors,
        )
