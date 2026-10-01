"""Sensors of the Massa Node integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MASSA_UNIT, PRICE_CURRENCY
from .coordinator import MassaConfigEntry, MassaCoordinator, MassaData
from .entity import MassaEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MassaSensorDescription(SensorEntityDescription):
    """Describe a Massa sensor."""

    value_fn: Callable[[MassaData], float | int | str | None]
    last_reset_fn: Callable[[MassaData], datetime | None] | None = None


SENSORS: tuple[MassaSensorDescription, ...] = (
    MassaSensorDescription(
        key="massa_price",
        native_unit_of_measurement=PRICE_CURRENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda d: d.massa_price,
    ),
    MassaSensorDescription(
        key="wallet_amount",
        native_unit_of_measurement=MASSA_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.wallet_amount,
    ),
    MassaSensorDescription(
        key="wallet_amount_with_rolls",
        native_unit_of_measurement=MASSA_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.wallet_amount_with_rolls,
    ),
    MassaSensorDescription(
        key="total_amount",
        native_unit_of_measurement=PRICE_CURRENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.total_amount,
    ),
    MassaSensorDescription(
        key="total_gain_of_day",
        native_unit_of_measurement=MASSA_UNIT,
        # TOTAL + last_reset: the recorder keeps the value at the end of each day,
        # which the card uses to draw the daily history.
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda d: d.total_gain_of_day,
        last_reset_fn=lambda d: d.day_start,
    ),
    MassaSensorDescription(
        key="active_rolls",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.active_rolls,
    ),
    MassaSensorDescription(
        key="produced_block",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.produced_block,
    ),
    MassaSensorDescription(
        key="missed_block",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.missed_block,
    ),
    MassaSensorDescription(
        key="block_miss_rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.block_miss_rate,
    ),
    MassaSensorDescription(
        key="current_cycle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.current_cycle,
    ),
    MassaSensorDescription(
        key="node_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MassaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(MassaSensor(coordinator, description) for description in SENSORS)


class MassaSensor(MassaEntity, SensorEntity):
    """A value read from the coordinator."""

    entity_description: MassaSensorDescription

    def __init__(self, coordinator: MassaCoordinator, description: MassaSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def last_reset(self) -> datetime | None:
        if self.entity_description.last_reset_fn is None:
            return None
        return self.entity_description.last_reset_fn(self.coordinator.data)
