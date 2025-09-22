import voluptuous as vol
from homeassistant import config_entries

from .const import *
from homeassistant.const import CONF_NAME

class VMCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Save the provided options as the config entry data
            return self.async_create_entry(title="VMC Control", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_VMC_SWITCH, default="switch.vmc"): str,
            vol.Required(CONF_TOILET_LIGHT, default="light.toilet"): str,
            vol.Required(CONF_HUMIDITY_SENSOR, default="sensor.bathroom_humidity"): str,
            vol.Required(CONF_TEMP_INSIDE, default="sensor.temp_inside"): str,
            vol.Required(CONF_TEMP_OUTSIDE, default="sensor.temp_outside"): str,
            vol.Required(CONF_SUMMER_MODE, default="input_boolean.summer_mode"): str,
            vol.Required(CONF_DELAY_TOILET, default=15): int,
            vol.Required(CONF_HUMIDITY_THRESHOLD, default=65): int,
            vol.Required(CONF_PERIODIC_INTERVAL, default=4): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
