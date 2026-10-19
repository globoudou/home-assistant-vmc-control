"""Boutons : démarrer / arrêter un boost temporaire."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import VmcEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl = entry.runtime_data
    async_add_entities(
        [VmcBoostButton(ctrl, entry, "boost"), VmcStopBoostButton(ctrl, entry, "stop_boost")]
    )


class VmcBoostButton(VmcEntity, ButtonEntity):
    _attr_icon = "mdi:fan-plus"

    async def async_press(self) -> None:
        await self.controller.async_start_boost()


class VmcStopBoostButton(VmcEntity, ButtonEntity):
    _attr_icon = "mdi:fan-remove"

    async def async_press(self) -> None:
        await self.controller.async_stop_boost()
