from datetime import timedelta, datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
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
        # config is the saved config entry data (entities and thresholds)
        self.config = config
        self.last_periodic = None

    async def _async_update_data(self):
        now = datetime.utcnow()
        vmc_on = False

        # 1. Toilet light -> run for delay minutes after it turned off
        try:
            entity_id = self.config.get(CONF_TOILET_LIGHT)
            if entity_id:
                entity = self.hass.states.get(entity_id)
                if entity and entity.state == "off":
                    # last_changed is in UTC
                    if (now - entity.last_changed).total_seconds() < int(self.config.get(CONF_DELAY_TOILET, 15)) * 60:
                        vmc_on = True
        except Exception as exc:
            _LOGGER.debug("Error checking toilet light: %s", exc)

        # 2. Humidity threshold
        try:
            entity_id = self.config.get(CONF_HUMIDITY_SENSOR)
            if entity_id:
                entity = self.hass.states.get(entity_id)
                if entity:
                    humidity = float(entity.state)
                    if humidity > float(self.config.get(CONF_HUMIDITY_THRESHOLD, 65)):
                        vmc_on = True
        except Exception as exc:
            _LOGGER.debug("Error checking humidity: %s", exc)

        # 3. Summer mode and temp comparison
        try:
            summer_entity = self.config.get(CONF_SUMMER_MODE)
            if summer_entity and self.hass.states.is_state(summer_entity, "on"):
                t_in_e = self.hass.states.get(self.config.get(CONF_TEMP_INSIDE))
                t_out_e = self.hass.states.get(self.config.get(CONF_TEMP_OUTSIDE))
                if t_in_e and t_out_e:
                    t_in = float(t_in_e.state)
                    t_out = float(t_out_e.state)
                    if t_in > t_out:
                        vmc_on = True
        except Exception as exc:
            _LOGGER.debug("Error checking summer mode temps: %s", exc)

        # 4. Periodic trigger: ensure at least one run every N hours if nothing else triggered
        try:
            interval_hours = float(self.config.get(CONF_PERIODIC_INTERVAL, 4))
            if self.last_periodic is None or (now - self.last_periodic).total_seconds() > interval_hours * 3600:
                # Only set periodic trigger if nothing else has recently triggered
                # We still allow periodic to set vmc_on = True
                vmc_on = True if not vmc_on else vmc_on
                self.last_periodic = now
        except Exception as exc:
            _LOGGER.debug("Error checking periodic trigger: %s", exc)

        return vmc_on
