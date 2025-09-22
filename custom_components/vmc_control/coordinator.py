from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import logging

from .const import *

_LOGGER = logging.getLogger(__name__)

class VMCCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict):
        super().__init__(
            hass,
            _LOGGER,
            name="VMC Control",
            update_interval=timedelta(seconds=30),
        )
        self.config = config
        self.last_periodic = None

    async def _async_update_data(self):
        now = dt_util.utcnow()   # ✅ timezone-aware
        data = {
            "toilet_light_recently_off": False,
            "humidity": None,
            "humidity_threshold": None,
            "summer_mode": False,
            "temp_in": None,
            "temp_out": None,
            "periodic_due": False,
        }

        # --- Toilet light ---
        try:
            entity_id = self.config.get(CONF_TOILET_LIGHT)
            delay_min = int(self.config.get(CONF_DELAY_TOILET, 15))
            if entity_id:
                toilet_entity = self.hass.states.get(entity_id)
                if toilet_entity and toilet_entity.state == "off":
                    last_changed = toilet_entity.last_changed
                    if (now - last_changed) < timedelta(minutes=delay_min):
                        data["toilet_light_recently_off"] = True
        except Exception as exc:
            _LOGGER.debug("Error checking toilet light: %s", exc)

        # --- Humidity ---
        try:
            entity_id = self.config.get(CONF_HUMIDITY_SENSOR)
            if entity_id:
                entity = self.hass.states.get(entity_id)
                if entity and entity.state not in ("unknown", "unavailable"):
                    data["humidity"] = float(entity.state)
                    data["humidity_threshold"] = int(self.config.get(CONF_HUMIDITY_THRESHOLD, 65))
        except Exception as exc:
            _LOGGER.debug("Error checking humidity: %s", exc)

        # --- Summer mode ---
        try:
            summer_entity = self.config.get(CONF_SUMMER_MODE)
            if summer_entity and self.hass.states.is_state(summer_entity, "on"):
                data["summer_mode"] = True
            t_in_e = self.hass.states.get(self.config.get(CONF_TEMP_INSIDE))
            t_out_e = self.hass.states.get(self.config.get(CONF_TEMP_OUTSIDE))
            if t_in_e and t_in_e.state not in ("unknown", "unavailable"):
                data["temp_in"] = float(t_in_e.state)
            if t_out_e and t_out_e.state not in ("unknown", "unavailable"):
                data["temp_out"] = float(t_out_e.state)
        except Exception as exc:
            _LOGGER.debug("Error checking summer mode temps: %s", exc)

        # --- Periodic ---
        try:
            interval_hours = float(self.config.get(CONF_PERIODIC_INTERVAL, 4))
            if (
                self.last_periodic is None
                or (now - self.last_periodic).total_seconds() > interval_hours * 3600
            ):
                data["periodic_due"] = True
        except Exception as exc:
            _LOGGER.debug("Error checking periodic trigger: %s", exc)

        return data
