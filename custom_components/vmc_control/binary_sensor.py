"""Capteur binaire : ventilation demandée par l'automatisme."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import VmcEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([VmcDemandSensor(entry.runtime_data, entry, "demand")])


class VmcDemandSensor(VmcEntity, BinarySensorEntity):
    _attr_icon = "mdi:fan"

    @property
    def is_on(self) -> bool:
        return self.controller.demand
