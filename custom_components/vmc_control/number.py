"""Paramètres numériques réglables depuis l'interface."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    S_BOOST_DURATION,
    S_HUMIDITY_HYST,
    S_HUMIDITY_ON,
    S_PERIODIC_DURATION,
    S_PERIODIC_INTERVAL,
    S_THERMAL_DELTA,
    S_THERMAL_TARGET,
    S_TOILET_DELAY_ON,
    S_TOILET_RUN_AFTER,
)
from .entity import VmcEntity


@dataclass(frozen=True)
class NumDef:
    key: str
    min: float
    max: float
    step: float
    unit: str
    icon: str


NUMBERS = [
    NumDef(S_TOILET_DELAY_ON, 0, 600, 5, UnitOfTime.SECONDS, "mdi:timer-play-outline"),
    NumDef(S_TOILET_RUN_AFTER, 1, 60, 1, UnitOfTime.MINUTES, "mdi:timer-outline"),
    NumDef(S_HUMIDITY_ON, 40, 95, 1, PERCENTAGE, "mdi:water-percent-alert"),
    NumDef(S_HUMIDITY_HYST, 1, 20, 1, PERCENTAGE, "mdi:arrow-collapse-vertical"),
    NumDef(S_PERIODIC_INTERVAL, 1, 24, 0.5, UnitOfTime.HOURS, "mdi:update"),
    NumDef(S_PERIODIC_DURATION, 5, 120, 5, UnitOfTime.MINUTES, "mdi:timer-sand"),
    NumDef(S_THERMAL_TARGET, 15, 30, 0.5, UnitOfTemperature.CELSIUS, "mdi:thermometer"),
    NumDef(S_THERMAL_DELTA, 0.5, 10, 0.5, UnitOfTemperature.CELSIUS, "mdi:delta"),
    NumDef(S_BOOST_DURATION, 5, 240, 5, UnitOfTime.MINUTES, "mdi:fan-plus"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl = entry.runtime_data
    async_add_entities(VmcNumber(ctrl, entry, d) for d in NUMBERS)


class VmcNumber(VmcEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, ctrl, entry, d: NumDef) -> None:
        super().__init__(ctrl, entry, d.key)
        self._attr_native_min_value = d.min
        self._attr_native_max_value = d.max
        self._attr_native_step = d.step
        self._attr_native_unit_of_measurement = d.unit
        self._attr_icon = d.icon

    @property
    def native_value(self) -> float:
        return self.controller.settings[self._key]

    async def async_set_native_value(self, value: float) -> None:
        await self.controller.async_set_setting(self._key, value)
