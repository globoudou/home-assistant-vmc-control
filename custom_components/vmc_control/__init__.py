from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

DOMAIN = "vmc_control"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up VMC Control from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload VMC Control config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["switch"])
