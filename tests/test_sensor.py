"""Tests of the sensor values."""

from homeassistant.const import CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massa_node.api import MassaApiError
from custom_components.massa_node.const import CONF_WALLET_ADDRESS, DOMAIN

from .conftest import HOST, PORT, WALLET, make_address


def _state(hass: HomeAssistant, entity_registry: er.EntityRegistry, platform: str, key: str):
    entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, f"{WALLET}_{key}")
    return hass.states.get(entity_id)


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=WALLET, version=2,
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_WALLET_ADDRESS: WALLET},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_values(hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_node, mock_price) -> None:
    await _setup(hass)
    # 50 MAS + 3 rolls * 100
    assert float(_state(hass, entity_registry, "sensor", "wallet_amount_with_rolls").state) == 350
    assert float(_state(hass, entity_registry, "sensor", "total_amount").state) == 7.0
    assert float(_state(hass, entity_registry, "sensor", "block_miss_rate").state) == 100 / 11
    assert float(_state(hass, entity_registry, "sensor", "total_gain_of_day").state) == 0
    assert _state(hass, entity_registry, "binary_sensor", "status").state == STATE_ON


async def test_buying_a_roll_is_not_a_loss(hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_node, mock_price) -> None:
    mock_node.get_address.return_value = make_address(balance=150, rolls=3)
    entry = await _setup(hass)  # baseline: 150 + 3 * 100 = 450 MAS
    # Buy one roll (-100 MAS on the balance) and receive a 1.5 MAS reward.
    mock_node.get_address.return_value = make_address(balance=51.5, rolls=4)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert float(_state(hass, entity_registry, "sensor", "total_gain_of_day").state) == 1.5


async def test_node_offline(hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_node, mock_price) -> None:
    entry = await _setup(hass)
    mock_node.get_status.side_effect = MassaApiError("down")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, entity_registry, "binary_sensor", "status").state == STATE_OFF
    assert _state(hass, entity_registry, "sensor", "wallet_amount").state == "unavailable"
