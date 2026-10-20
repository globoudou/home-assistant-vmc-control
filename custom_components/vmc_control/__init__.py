"""VMC Control : pilotage on/off d'une VMC depuis Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN, VERSION
from .controller import VmcController

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type VmcConfigEntry = ConfigEntry[VmcController]


_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "frontend" / "vmc-control-card.js"
# Copie servie par la route /local de Home Assistant, disponible dès la première
# seconde du démarrage. Notre propre route n'existe qu'une fois l'intégration
# chargée : un tableau de bord ouvert entre-temps garde l'import en échec jusqu'à
# un rechargement complet (« Custom element doesn't exist »).
LOCAL_SUBDIR = DOMAIN
LOCAL_URL = f"/local/{LOCAL_SUBDIR}/{CARD_FILE.name}"


def _copy_card_to_www(www: str) -> bool:
    """Copie la carte dans config/www ; True si /local sert déjà ce dossier.

    Home Assistant n'enregistre /local que si config/www existe au démarrage : au
    tout premier lancement on garde notre route jusqu'au redémarrage suivant.
    """
    www_path = Path(www)
    served = www_path.is_dir()
    target = www_path / LOCAL_SUBDIR / CARD_FILE.name
    try:
        source = CARD_FILE.read_bytes()
        if not target.is_file() or target.read_bytes() != source:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
    except OSError as err:
        _LOGGER.warning("Copie de la carte impossible vers %s : %s", target, err)
        return False
    return served


async def _async_ensure_dashboard_resource(hass: HomeAssistant, url: str) -> None:
    """Ajoute ou met à jour la carte dans les ressources des tableaux de bord."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        data = hass.data.get(LOVELACE_DATA)
        resources = getattr(data, "resources", None)
        if resources is None or getattr(data, "resource_mode", "") != "storage":
            return
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        ours = {CARD_URL, LOCAL_URL}
        matches = [
            r for r in resources.async_items() if str(r.get("url", "")).split("?")[0] in ours
        ]
        if not matches:
            await resources.async_create_item({"res_type": "module", "url": url})
            return
        first, *duplicates = matches
        if first.get("url") != url or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"res_type": "module", "url": url})
        for dup in duplicates:
            await resources.async_delete_item(dup["id"])
    except Exception:
        _LOGGER.exception("Impossible d'enregistrer la carte VMC comme ressource")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Sert la carte Lovelace et l'ajoute automatiquement au frontend."""
    if hass.http is None:
        return True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), False)]
    )
    local_ready = await hass.async_add_executor_job(
        _copy_card_to_www, hass.config.path("www")
    )
    url = f"{LOCAL_URL if local_ready else CARD_URL}?v={VERSION}"
    add_extra_js_url(hass, url)

    async def _resource(_event: Event | None = None) -> None:
        await _async_ensure_dashboard_resource(hass, url)

    if hass.is_running:
        hass.async_create_task(_resource())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _resource)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: VmcConfigEntry) -> bool:
    controller = VmcController(hass, entry)
    entry.runtime_data = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VmcConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_stop()
    return ok


async def _async_reload(hass: HomeAssistant, entry: VmcConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migration depuis la v1 (clés différentes, paramètres désormais en entités)."""
    if entry.version == 1:
        old = dict(entry.data)
        new = {"vmc_entity": old.get("vmc_switch")}
        for key in ("toilet_light", "humidity_sensor", "temp_inside", "temp_outside"):
            if old.get(key):
                new[key] = old[key]
        hass.config_entries.async_update_entry(entry, data=new, options={}, version=2)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Supprime les réglages persistés quand l'intégration est retirée."""
    from homeassistant.helpers.storage import Store

    from .const import STORAGE_VERSION

    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
