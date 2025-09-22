import logging
from datetime import datetime
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import *

_LOGGER = logging.getLogger(__name__)

class VmcControlSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "VMC Control"
        self._attr_unique_id = f"{DOMAIN}_switch_{id(self)}"
        self._last_trigger = None

    @property
    def is_on(self) -> bool:
        relay_entity_id = self.coordinator.config.get(CONF_VMC_SWITCH)
        state = self.hass.states.get(relay_entity_id) if relay_entity_id else None
        return state.state == "on" if state else False

    @property
    def extra_state_attributes(self):
        return {"last_trigger": self._last_trigger}

    async def async_turn_on(self, **kwargs):
        relay_entity_id = self.coordinator.config.get(CONF_VMC_SWITCH)
        if relay_entity_id:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": relay_entity_id})
            self._last_trigger = "Manuel"
            _LOGGER.info("VMC forcée manuellement en ON")
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        relay_entity_id = self.coordinator.config.get(CONF_VMC_SWITCH)
        if relay_entity_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": relay_entity_id})
            self._last_trigger = "Manuel"
            _LOGGER.info("VMC forcée manuellement en OFF")
            self.async_write_ha_state()

    async def async_update(self):
        data = self.coordinator.data or {}
        reason = None
        turn_on = False

        # check toilet light
        if data.get("toilet_light_recently_off"):
            turn_on = True
            reason = "Lumière toilettes éteinte → déclenchement après délai"

        # humidity
        elif data.get("humidity") is not None and data.get("humidity_threshold") is not None:
            try:
                if data["humidity"] > data["humidity_threshold"]:
                    turn_on = True
                    reason = f"Humidité {data['humidity']}% > seuil {data['humidity_threshold']}%"
            except Exception:
                pass

        # summer mode temperature compare
        elif data.get("summer_mode") and data.get("temp_in") is not None and data.get("temp_out") is not None:
            try:
                if data["temp_in"] > data["temp_out"]:
                    turn_on = True
                    reason = f"Mode été : {data['temp_in']}°C int > {data['temp_out']}°C ext"
            except Exception:
                pass

        # periodic
        elif data.get("periodic_due"):
            turn_on = True
            reason = "Déclenchement périodique (toutes les Xh)"

        relay_entity_id = self.coordinator.config.get(CONF_VMC_SWITCH)
        if turn_on:
            # turn on actual relay
            if relay_entity_id:
                await self.hass.services.async_call("switch", "turn_on", {"entity_id": relay_entity_id})
                # update coordinator last_periodic if periodic triggered
                if data.get("periodic_due") and reason and "périodique" in reason:
                    # update coordinator timestamp so periodic resets
                    self.coordinator.last_periodic = datetime.utcnow()
                self._last_trigger = reason
                _LOGGER.info("VMC allumée automatiquement : %s", reason)
                self.async_write_ha_state()
        else:
            # turn off relay if it was not manually forced
            if self._last_trigger != "Manuel" and relay_entity_id:
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": relay_entity_id})
                _LOGGER.info("VMC éteinte automatiquement (aucune condition active)")
                self.async_write_ha_state()
