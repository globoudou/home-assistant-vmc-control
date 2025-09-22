import logging
from datetime import timedelta
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTO_OFF_DELAY = timedelta(minutes=15)
PERIODIC_INTERVAL = timedelta(hours=4)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the VMC Control switch."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VmcControlSwitch(coordinator)], True)


class VmcControlSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of the VMC Control switch."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "VMC Control"
        self._attr_unique_id = f"{DOMAIN}_switch"
        self._is_on = False
        self._last_trigger = None

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Manually turn on the VMC."""
        self._is_on = True
        self._last_trigger = "Manuel"
        _LOGGER.info("VMC forcée manuellement en ON")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Manually turn off the VMC."""
        self._is_on = False
        self._last_trigger = "Manuel"
        _LOGGER.info("VMC forcée manuellement en OFF")
        self.async_write_ha_state()

    async def async_update(self):
        """Update VMC state based on coordinator data."""
        data = self.coordinator.data
        if not data:
            return

        reason = None
        turn_on = False

        # --- Lumière toilettes ---
        if data.get("toilet_light_recently_off"):
            turn_on = True
            reason = f"Lumière toilettes éteinte → déclenchement après 15 min"

        # --- Humidité salle de bain ---
        elif data.get("humidity") is not None and data.get("humidity_threshold") is not None:
            if data["humidity"] > data["humidity_threshold"]:
                turn_on = True
                reason = f"Humidité {data['humidity']}% > seuil {data['humidity_threshold']}%"

        # --- Mode été ---
        elif data.get("summer_mode") and data.get("temp_in") and data.get("temp_out"):
            if data["temp_in"] > data["temp_out"]:
                turn_on = True
                reason = f"Mode été : {data['temp_in']}°C int > {data['temp_out']}°C ext"

        # --- Déclenchement périodique ---
        elif data.get("periodic_due"):
            turn_on = True
            reason = "Déclenchement périodique (toutes les 4h)"

        # Appliquer l'état
        if turn_on and not self._is_on:
            self._is_on = True
            self._last_trigger = reason
            _LOGGER.info("VMC allumée automatiquement : %s", reason)
            self.async_write_ha_state()

        elif not turn_on and self._is_on and self._last_trigger != "Manuel":
            self._is_on = False
            _LOGGER.info("VMC éteinte automatiquement (aucune condition active)")
            self.async_write_ha_state()
