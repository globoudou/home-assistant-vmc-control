"""Sélecteurs : mode général et mode thermique."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODES, S_MODE, S_THERMAL_MODE, THERMAL_MODES
from .entity import VmcEntity

SELECTS = {
    S_MODE: (MODES, "mdi:fan-auto"),
    S_THERMAL_MODE: (THERMAL_MODES, "mdi:thermometer-lines"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl = entry.runtime_data
    async_add_entities(
        VmcSelect(ctrl, entry, key, opts, icon) for key, (opts, icon) in SELECTS.items()
    )


class VmcSelect(VmcEntity, SelectEntity):
    def __init__(self, ctrl, entry, key, options, icon) -> None:
        super().__init__(ctrl, entry, key)
        self._attr_options = options
        self._attr_icon = icon

    @property
    def current_option(self) -> str:
        return self.controller.settings[self._key]

    async def async_select_option(self, option: str) -> None:
        await self.controller.async_set_setting(self._key, option)
