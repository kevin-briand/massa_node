"""Diagnostics support for the Massa Node integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_WALLET_ADDRESS
from .coordinator import MassaConfigEntry

TO_REDACT = {CONF_HOST, CONF_WALLET_ADDRESS, "node_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MassaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = asdict(coordinator.data) if coordinator.data else None
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "node_online": coordinator.node_online,
        "last_update_success": coordinator.last_update_success,
        "data": async_redact_data(data, TO_REDACT) if data else None,
    }
