"""Classe de base des entités VMC Control."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, VERSION
from .controller import VmcController


class VmcEntity(Entity):
    """Entité rattachée au contrôleur et à l'appareil « VMC »."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, controller: VmcController, entry: ConfigEntry, key: str) -> None:
        self.controller = controller
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="VMC Control",
            model="Pilotage VMC on/off",
            sw_version=VERSION,
        )

    async def async_added_to_hass(self) -> None:
        self.controller.entity_ids[self._key] = self.entity_id
        self.async_on_remove(self.controller.add_listener(self.async_write_ha_state))

    async def async_will_remove_from_hass(self) -> None:
        self.controller.entity_ids.pop(self._key, None)
