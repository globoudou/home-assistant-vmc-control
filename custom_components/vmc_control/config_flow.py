import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.const import CONF_NAME

from .const import *

class VMCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            title = user_input.get(CONF_NAME) or "VMC Control"
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema({
            vol.Optional(CONF_NAME, default="VMC Control"): str,
            vol.Required(CONF_VMC_SWITCH, default="switch.vmc"): selector.EntitySelector({"domain": "switch"}),
            vol.Required(CONF_TOILET_LIGHT, default="light.toilet"): selector.EntitySelector({"domain": "light"}),
            vol.Required(CONF_HUMIDITY_SENSOR, default="sensor.bathroom_humidity"): selector.EntitySelector({"domain": "sensor"}),
            vol.Required(CONF_TEMP_INSIDE, default="sensor.temp_inside"): selector.EntitySelector({"domain": "sensor"}),
            vol.Required(CONF_TEMP_OUTSIDE, default="sensor.temp_outside"): selector.EntitySelector({"domain": "sensor"}),
            vol.Required(CONF_SUMMER_MODE, default="input_boolean.summer_mode"): selector.EntitySelector({"domain": "input_boolean"}),
            vol.Required(CONF_DELAY_TOILET, default=15): vol.All(int, vol.Range(min=1, max=60)),
            vol.Required(CONF_HUMIDITY_THRESHOLD, default=65): vol.All(int, vol.Range(min=30, max=100)),
            vol.Required(CONF_PERIODIC_INTERVAL, default=4): vol.All(int, vol.Range(min=1, max=168)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
