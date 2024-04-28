"""The Detailed Hello World Push integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, IP, PORT, WALLET_ADDRESS
from custom_components.massa_node.api.node_api import NodeApi

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = NodeApi(hass, entry.data[IP], entry.data[PORT], entry.data[WALLET_ADDRESS])
    await hass.config_entries.async_forward_entry_setups(entry, ['sensor'])
    return True

async def async_unload_entry(hass, entry):
    """Supprimer les entités lors de la désinstallation de l'intégration."""
    # Récupérer les entités ajoutées par cette intégration
    entities = hass.data[DOMAIN].pop("sensor", [])

    # Supprimer les entités de Home Assistant
    unload_tasks = [entity.async_remove() for entity in entities]
    await asyncio.gather(*unload_tasks)
    return True
