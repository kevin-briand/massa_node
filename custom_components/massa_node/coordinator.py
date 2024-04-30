"""Coordinator class"""
import datetime
import logging
from datetime import timedelta

import async_timeout
from homeassistant import exceptions
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.massa_node import NodeApi, DOMAIN
from custom_components.massa_node.api.bitget_api import BitgetApi

_LOGGER = logging.getLogger(__name__)


class Data:
    """Object class of MassaCoordinator data"""

    def __init__(self, status='Offline', massa_price=0, wallet_amount=0, produced_block=0,
                 missed_block=0, active_rolls=0, total_amount=0, wallet_amount_with_rolls=0,
                 last_total_update=datetime.date.today().isoformat(), total_wallet_at_midnight=0, **kwargs):
        """Init object"""
        self.status: str = status
        self.massa_price: float = massa_price
        self.wallet_amount: float = wallet_amount
        self.produced_block: int = produced_block
        self.missed_block: int = missed_block
        self.active_rolls: int = active_rolls
        self.total_amount: float = total_amount
        self.wallet_amount_with_rolls: float = wallet_amount_with_rolls
        self.last_total_update: datetime.date = datetime.date.fromisoformat(last_total_update)
        self.total_wallet_at_midnight: float = total_wallet_at_midnight

    def to_object(self):
        """return an object of the class"""
        return {
            'status': self.status,
            'massa_price': self.massa_price,
            'wallet_amount': self.wallet_amount,
            'produced_block': self.produced_block,
            'missed_block': self.missed_block,
            'active_rolls': self.active_rolls,
            'total_amount': self.total_amount,
            'wallet_amount_with_rolls': self.wallet_amount_with_rolls,
            'last_total_update': self.last_total_update,
            'total_wallet_at_midnight': self.total_wallet_at_midnight
        }


class MassaCoordinator(DataUpdateCoordinator):
    """Massa coordinator."""

    def __init__(self, hass, node_api: NodeApi):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.node_api = node_api
        # init store
        self.store = Store(hass, 1, 'massa-node')

    def recalculate_total_amount(self) -> None:
        """Recalculate total price of the wallet, including rolls"""
        self.data.total_amount = self.recalculate_total_wallet_with_rolls_amount() * self.data.massa_price

    def recalculate_total_wallet_with_rolls_amount(self) -> float:
        """Recalculate total amount of the wallet, including rolls"""
        self.data.wallet_amount_with_rolls = self.data.active_rolls * 100 + self.data.wallet_amount
        return self.data.wallet_amount_with_rolls

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        # if not, initialize data object
        if self.data is None:
            self.data = Data()
            data = await self.store.async_load()
            if data:
                self.data = Data(**data)
        try:
            async with async_timeout.timeout(15):
                # fetch data
                status = await self.node_api.test_connection()
                self.data.status = 'Online' if status else 'Offline'
                if not status:
                    return self.data

                actual_price = await BitgetApi().get_massa_price()
                self.data.massa_price = actual_price

                address_info = await self.node_api.get_address()
                if not address_info:
                    return self.data
                # Update coordinator data object
                self.data.wallet_amount = float(address_info.final_balance)
                self.data.produced_block = sum(cycle.ok_count for cycle in address_info.cycle_infos)
                self.data.missed_block = sum(cycle.nok_count for cycle in address_info.cycle_infos)
                self.data.active_rolls = address_info.candidate_roll_count
                self.recalculate_total_wallet_with_rolls_amount()
                self.recalculate_total_amount()

                if self.data.last_total_update != datetime.date.today():
                    self.data.last_total_update = datetime.date.today()
                    self.data.total_wallet_at_midnight = self.data.wallet_amount

                # store latest data for recovery
                await self.store.async_save(self.data.to_object())
                return self.data
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")


class ApiError(exceptions.HomeAssistantError):
    """Error to indicate that data cannot be retrieved."""
