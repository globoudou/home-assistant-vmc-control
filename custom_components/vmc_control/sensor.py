"""Capteurs : raison de fonctionnement (état complet) et prochain cycle."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import R_BOOST, R_FORCED, R_HUMIDITY, R_PERIODIC, R_THERMAL, R_TOILET
from .entity import VmcEntity

STATUS_OPTIONS = ["idle", R_FORCED, R_BOOST, R_TOILET, R_HUMIDITY, R_THERMAL, R_PERIODIC]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl = entry.runtime_data
    async_add_entities(
        [VmcStatusSensor(ctrl, entry, "status"), VmcNextCycleSensor(ctrl, entry, "next_cycle")]
    )


class VmcStatusSensor(VmcEntity, SensorEntity):
    """Raison principale ; tous les détails sont en attributs (utilisés par la carte)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_icon = "mdi:hvac"
    _unrecorded_attributes = frozenset({"entities", "settings"})

    @property
    def native_value(self) -> str:
        return self.controller.reasons[0] if self.controller.reasons else "idle"

    @property
    def extra_state_attributes(self) -> dict:
        return {"vmc_control": True, **self.controller.snapshot()}


class VmcNextCycleSensor(VmcEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> datetime | None:
        return self.controller.next_cycle
