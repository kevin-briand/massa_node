"""Fixtures for the Massa Node tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.massa_node.api import AddressInfo, CycleInfo, NodeStatus

WALLET = "AU12dG5xP1RDEB5ocdHkymNVvvSJmUL9BgHwCksDowqmGWxfpm93x"
HOST = "192.168.1.10"
PORT = 33035


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in every test."""
    return


def make_address(balance: float = 50.0, rolls: int = 3, ok: int = 10, nok: int = 1) -> AddressInfo:
    return AddressInfo(
        address=WALLET,
        final_balance=balance,
        final_roll_count=rolls,
        candidate_balance=balance,
        candidate_roll_count=rolls,
        deferred_credits=0.0,
        cycle_infos=[CycleInfo(cycle=1, is_final=True, ok_count=ok, nok_count=nok, active_rolls=rolls)],
    )


@pytest.fixture
def mock_node() -> Generator[AsyncMock]:
    """Mock the node API used by the coordinator and the config flow."""
    with (
        patch("custom_components.massa_node.coordinator.NodeApi", autospec=True) as coord_api,
        patch("custom_components.massa_node.config_flow.NodeApi", new=coord_api),
    ):
        api = coord_api.return_value
        api.get_status.return_value = NodeStatus(node_id="N1", version="MAIN.2.5", current_cycle=42)
        api.get_address.return_value = make_address()
        yield api


@pytest.fixture
def mock_price() -> Generator[AsyncMock]:
    """Mock the Bitget API."""
    with patch("custom_components.massa_node.coordinator.BitgetApi", autospec=True) as price_api:
        price_api.return_value.get_massa_price.return_value = 0.02
        yield price_api.return_value
