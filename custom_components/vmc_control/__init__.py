from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import VMCCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up VMC Control from a config entry."""

    # Crée le coordinator avec entry.data seulement
    coordinator = VMCCoordinator(hass, entry.data)

    # Sauvegarde dans hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Démarre le premier refresh
    await coordinator.async_config_entry_first_refresh()

    # Forward vers le switch
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload VMC Control config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["switch"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
