"""Tests of the config flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.massa_node.api import MassaApiError
from custom_components.massa_node.const import CONF_WALLET_ADDRESS, DOMAIN

from .conftest import HOST, PORT, WALLET

USER_INPUT = {CONF_HOST: HOST, CONF_PORT: PORT, CONF_WALLET_ADDRESS: WALLET}


async def test_user_flow(hass: HomeAssistant, mock_node, mock_price) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == WALLET


async def test_invalid_address(hass: HomeAssistant, mock_node) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_WALLET_ADDRESS: "not-an-address"}
    )
    assert result["errors"] == {CONF_WALLET_ADDRESS: "invalid_address"}


async def test_cannot_connect(hass: HomeAssistant, mock_node) -> None:
    mock_node.get_status.side_effect = MassaApiError("boom")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured(hass: HomeAssistant, mock_node) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=WALLET, data=USER_INPUT, version=2).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
