"""Tests of setup, unload and migration."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massa_node.const import CONF_WALLET_ADDRESS, DOMAIN

from .conftest import HOST, PORT, WALLET


async def test_setup_and_unload(hass: HomeAssistant, mock_node, mock_price) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=WALLET,
        version=2,
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_WALLET_ADDRESS: WALLET},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_migration_v1(hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_node, mock_price) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"ip": HOST, CONF_PORT: PORT, CONF_WALLET_ADDRESS: WALLET},
    )
    entry.add_to_hass(hass)
    old_price = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "massa_node_massa_price", config_entry=entry,
        suggested_object_id="massa_node_massa_price",
    )
    old_status = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "massa_node_status", config_entry=entry,
        suggested_object_id="massa_node_status",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.unique_id == WALLET
    assert entry.data[CONF_HOST] == HOST
    migrated = entity_registry.async_get(old_price.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{WALLET}_massa_price"
    assert entity_registry.async_get(old_status.entity_id) is None
