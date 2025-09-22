from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VMCSwitch(coordinator)], True)

class VMCSwitch(SwitchEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "VMC Control"
        self._attr_unique_id = "vmc_control_main"
        self._forced_state = None

    @property
    def is_on(self):
        # if user forced state via UI, respect it; otherwise use coordinator decision
        if self._forced_state is not None:
            return self._forced_state
        return bool(self.coordinator.data)

    async def async_turn_on(self, **kwargs):
        # User turned switch on: force on until user turns off
        self._forced_state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        # User turned switch off: clear forced state and let coordinator control
        self._forced_state = False
        self.async_write_ha_state()
