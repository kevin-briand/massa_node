"""The Massa Node integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import CONF_WALLET_ADDRESS, DOMAIN, PLATFORMS
from .coordinator import MassaConfigEntry, MassaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: MassaConfigEntry) -> bool:
    """Set up Massa Node from a config entry."""
    coordinator = MassaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MassaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: MassaConfigEntry) -> bool:
    """Migrate old config entries.

    Version 1 (single instance): data keys ip/port/wallet_address, entity unique ids
    `massa_node_<key>`, a `status` text sensor.
    Version 2: data keys host/port/wallet_address, unique ids `<wallet>_<key>`,
    connectivity binary sensor, one entry per wallet.
    """
    _LOGGER.debug("Migrating Massa Node entry from version %s", entry.version)

    if entry.version > 2:
        return False

    if entry.version == 1:
        wallet = entry.data[CONF_WALLET_ADDRESS]
        new_data = {
            CONF_HOST: entry.data.get("ip", entry.data.get(CONF_HOST)),
            CONF_PORT: entry.data[CONF_PORT],
            CONF_WALLET_ADDRESS: wallet,
        }

        registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            if not entity.unique_id.startswith("massa_node_"):
                continue
            key = entity.unique_id.removeprefix("massa_node_")
            if key == "status":
                # Replaced by a connectivity binary sensor.
                registry.async_remove(entity.entity_id)
                continue
            # Keep the entity_id so existing dashboards and automations keep working.
            registry.async_update_entity(entity.entity_id, new_unique_id=f"{wallet}_{key}")

        # The old global store is no longer used.
        await Store(hass, 1, "massa-node").async_remove()

        hass.config_entries.async_update_entry(
            entry, data=new_data, unique_id=wallet, version=2
        )

    _LOGGER.info("Massa Node entry migrated to version %s", entry.version)
    return True
