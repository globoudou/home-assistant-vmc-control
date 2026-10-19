"""Interrupteurs d'activation de chaque déclencheur."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import S_HUMIDITY_ENABLED, S_PERIODIC_ENABLED, S_TOILET_ENABLED
from .entity import VmcEntity

SWITCHES = {
    S_TOILET_ENABLED: "mdi:toilet",
    S_HUMIDITY_ENABLED: "mdi:water-percent",
    S_PERIODIC_ENABLED: "mdi:timer-sync-outline",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl = entry.runtime_data
    async_add_entities(VmcSwitch(ctrl, entry, k, i) for k, i in SWITCHES.items())


class VmcSwitch(VmcEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, ctrl, entry, key, icon) -> None:
        super().__init__(ctrl, entry, key)
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(self.controller.settings[self._key])

    async def async_turn_on(self, **kwargs) -> None:
        await self.controller.async_set_setting(self._key, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.controller.async_set_setting(self._key, False)
