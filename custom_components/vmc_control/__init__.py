from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from datetime import timedelta
import logging

from .const import DOMAIN, CONF_PERIODIC_INTERVAL
from .coordinator import VMCCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up VMC Control from a config entry."""
    # Initialize storage
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator with update interval (use periodic interval if provided)
    interval_hours = float(entry.data.get(CONF_PERIODIC_INTERVAL, 4))
    update_interval = timedelta(seconds=30)

    coordinator = VMCCoordinator(hass, update_interval=update_interval, config=entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup for platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    _LOGGER.debug("VMC Control setup complete for entry %s", entry.entry_id)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload VMC Control config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["switch"])
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
