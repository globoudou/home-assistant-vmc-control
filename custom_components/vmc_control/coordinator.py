from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import logging

from .const import *

_LOGGER = logging.getLogger(__name__)

class VMCCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, update_interval, config: dict):
        super().__init__(hass, _LOGGER, name="VMC Control", update_interval=update_interval)
        self.config = config or {}
        self.last_periodic = datetime.utcnow() - timedelta(hours=5)
        self.data = {}

    async def _async_update_data(self):
        now = datetime.utcnow()

        # Toilet light recently off
        toilet_entity = self.hass.states.get(self.config.get(CONF_TOILET_LIGHT))
        if toilet_entity:
            last_changed = getattr(toilet_entity, "last_changed", now)
            try:
                delay_min = int(self.config.get(CONF_DELAY_TOILET, 15))
            except Exception:
                delay_min = 15
            self.data["toilet_light_recently_off"] = (
                toilet_entity.state == "off" and (now - last_changed) < timedelta(minutes=delay_min)
            )
        else:
            self.data["toilet_light_recently_off"] = False

        # Humidity
        hum_entity = self.hass.states.get(self.config.get(CONF_HUMIDITY_SENSOR))
        try:
            self.data["humidity"] = float(hum_entity.state) if (hum_entity and hum_entity.state not in ("unknown", "unavailable")) else None
        except Exception:
            self.data["humidity"] = None
        try:
            self.data["humidity_threshold"] = int(self.config.get(CONF_HUMIDITY_THRESHOLD, 65))
        except Exception:
            self.data["humidity_threshold"] = 65

        # Summer mode and temperatures
        self.data["summer_mode"] = self.hass.states.is_state(self.config.get(CONF_SUMMER_MODE), "on") if self.config.get(CONF_SUMMER_MODE) else False
        t_in_entity = self.hass.states.get(self.config.get(CONF_TEMP_INSIDE))
        t_out_entity = self.hass.states.get(self.config.get(CONF_TEMP_OUTSIDE))
        try:
            self.data["temp_in"] = float(t_in_entity.state) if (t_in_entity and t_in_entity.state not in ("unknown", "unavailable")) else None
        except Exception:
            self.data["temp_in"] = None
        try:
            self.data["temp_out"] = float(t_out_entity.state) if (t_out_entity and t_out_entity.state not in ("unknown", "unavailable")) else None
        except Exception:
            self.data["temp_out"] = None

        # Periodic trigger: every N hours (use config value)
        try:
            interval_hours = float(self.config.get(CONF_PERIODIC_INTERVAL, 4))
        except Exception:
            interval_hours = 4.0

        self.data["periodic_due"] = (now - self.last_periodic) > timedelta(hours=interval_hours)
        # If periodic_due is true and nothing else triggers, we'll update last_periodic in coordinator or switch when applied.
        return self.data
