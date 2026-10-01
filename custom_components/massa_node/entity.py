"""Base entity for the Massa Node integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MassaCoordinator


class MassaEntity(CoordinatorEntity[MassaCoordinator]):
    """Entity attached to the Massa node device of a wallet."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MassaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        wallet = coordinator.wallet_address
        self._attr_unique_id = f"{wallet}_{key}"
        self._attr_translation_key = key
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, wallet)},
            name="Massa Node",
            manufacturer="Massa Labs",
            model="Massa node",
            sw_version=data.version if data else None,
            serial_number=wallet,
        )
