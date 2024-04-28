"""sensor class"""
import logging

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.massa_node import DOMAIN
from custom_components.massa_node.coordinator import MassaCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config, async_add_entities):
    """Initialize and register sensors"""
    # Init massa node api and coordinator
    node_api = hass.data.setdefault(DOMAIN, {})[config.entry_id]
    coordinator = MassaCoordinator(hass, node_api)
    # refresh datas from api
    await coordinator.async_config_entry_first_refresh()
    # register sensors
    async_add_entities([
        NodeEntity(coordinator, 'status'),
        NodeEntity(coordinator, 'massa_price', 'USDT'),
        NodeEntity(coordinator, 'wallet_amount', 'MAS'),
        NodeEntity(coordinator, 'produced_block'),
        NodeEntity(coordinator, 'missed_block'),
        NodeEntity(coordinator, 'active_rolls'),
        NodeEntity(coordinator, 'total_amount', 'USDT'),
        NodeEntity(coordinator, 'wallet_amount_with_rolls', 'MAS'),
        TotalOfDayEntity(coordinator)
    ])
    return True

class BaseEntity(CoordinatorEntity, Entity):
    def __init__(self, coordinator: MassaCoordinator, name: str, unit: str = None):
        """Node sensor"""
        super().__init__(coordinator=coordinator)
        self.entity_id = f'sensor.massa_node_{name}'
        self._attr_unique_id = f'massa_node_{name}'
        self._name = name
        self._attr_unit_of_measurement = unit

    @property
    def state(self):
        """return the actual state of the sensor"""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return
        self._state = getattr(self.coordinator.data, self._name)
        self.async_write_ha_state()

class NodeEntity(BaseEntity):
    def __init__(self, coordinator: MassaCoordinator, name: str, unit: str = None):
        """Node sensor"""
        super().__init__(coordinator, name, unit)
        self._state =  getattr(self.coordinator.data, self._name)


class TotalOfDayEntity(BaseEntity):
    def __init__(self, coordinator: MassaCoordinator):
        super().__init__(coordinator, 'total_gain_of_day', 'MAS')
        self._state =  self.coordinator.data.wallet_amount - self.coordinator.data.total_wallet_at_midnight

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return
        self._state = self.coordinator.data.wallet_amount - self.coordinator.data.total_wallet_at_midnight
        self.async_write_ha_state()
