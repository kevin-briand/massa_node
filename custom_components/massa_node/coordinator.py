"""Data update coordinator for the Massa Node integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import BitgetApi, MassaApiError, NodeApi
from .const import (
    CONF_WALLET_ADDRESS,
    DOMAIN,
    PRICE_UPDATE_INTERVAL,
    ROLL_PRICE,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)

type MassaConfigEntry = ConfigEntry[MassaCoordinator]

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class MassaData:
    """Snapshot of everything the entities display."""

    node_id: str | None
    version: str | None
    current_cycle: int | None
    massa_price: float | None
    wallet_amount: float
    rolls: int
    active_rolls: int
    deferred_credits: float
    wallet_amount_with_rolls: float
    total_amount: float | None
    produced_block: int
    missed_block: int
    block_miss_rate: float | None
    total_gain_of_day: float
    day_start: datetime


class MassaCoordinator(DataUpdateCoordinator[MassaData]):
    """Poll the node and the market price."""

    config_entry: MassaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MassaConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        session = async_get_clientsession(hass)
        self.wallet_address: str = entry.data[CONF_WALLET_ADDRESS]
        self.node_api = NodeApi(session, entry.data[CONF_HOST], entry.data[CONF_PORT])
        self.price_api = BitgetApi(session)

        # True when the node answered the last request; read by the connectivity sensor.
        self.node_online = False

        self._price: float | None = None
        self._price_fetched_at: datetime | None = None

        # The daily gain is computed against the wallet value at the start of the day.
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._baseline_day: date | None = None
        self._baseline_value: float | None = None

    async def _async_setup(self) -> None:
        """Restore the daily baseline saved before the last restart."""
        stored = await self._store.async_load()
        if stored:
            try:
                self._baseline_day = date.fromisoformat(stored["day"])
                self._baseline_value = float(stored["value"])
            except (KeyError, TypeError, ValueError):
                _LOGGER.debug("Ignoring invalid stored baseline: %s", stored)

    async def _async_update_price(self) -> float | None:
        now = dt_util.utcnow()
        if self._price_fetched_at and now - self._price_fetched_at < PRICE_UPDATE_INTERVAL:
            return self._price
        try:
            self._price = await self.price_api.get_massa_price()
            self._price_fetched_at = now
        except MassaApiError as err:
            # Keep the last known price, the node data is still worth publishing.
            _LOGGER.debug("Price update failed, keeping last value: %s", err)
        return self._price

    def _daily_gain(self, total: float) -> float:
        today = dt_util.now().date()
        if self._baseline_day != today or self._baseline_value is None:
            self._baseline_day = today
            self._baseline_value = total
            self._store.async_delay_save(
                lambda: {"day": today.isoformat(), "value": total}, 5
            )
        return total - self._baseline_value

    async def _async_update_data(self) -> MassaData:
        try:
            status = await self.node_api.get_status()
            address = await self.node_api.get_address(self.wallet_address)
        except MassaApiError as err:
            self.node_online = False
            raise UpdateFailed(f"Massa node unreachable: {err}") from err
        self.node_online = True

        if address is None:
            raise UpdateFailed(f"Wallet {self.wallet_address} not found on the node")

        price = await self._async_update_price()

        # Value of the wallet independent of roll purchases/sales:
        # buying a roll moves 100 MAS from the balance to the rolls,
        # selling one moves it to the deferred credits.
        with_rolls = (
            address.final_balance
            + address.final_roll_count * ROLL_PRICE
            + address.deferred_credits
        )

        produced = sum(c.ok_count for c in address.cycle_infos)
        missed = sum(c.nok_count for c in address.cycle_infos)
        total_blocks = produced + missed

        active_rolls = address.final_roll_count
        if address.cycle_infos and address.cycle_infos[-1].active_rolls is not None:
            active_rolls = int(address.cycle_infos[-1].active_rolls)

        return MassaData(
            node_id=status.node_id,
            version=status.version,
            current_cycle=status.current_cycle,
            massa_price=price,
            wallet_amount=address.final_balance,
            rolls=address.final_roll_count,
            active_rolls=active_rolls,
            deferred_credits=address.deferred_credits,
            wallet_amount_with_rolls=with_rolls,
            total_amount=with_rolls * price if price is not None else None,
            produced_block=produced,
            missed_block=missed,
            block_miss_rate=(missed / total_blocks * 100) if total_blocks else None,
            total_gain_of_day=self._daily_gain(with_rolls),
            day_start=dt_util.start_of_local_day(),
        )
