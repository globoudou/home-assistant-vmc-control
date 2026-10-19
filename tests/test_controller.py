"""Tests de bout en bout du contrôleur VMC."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.vmc_control.const import DOMAIN

VMC = "input_boolean.vmc"
LIGHT = "input_boolean.wc"
HUM = "sensor.sdb_humidity"
TIN = "sensor.t_in"
TOUT = "sensor.t_out"


async def _setup(hass: HomeAssistant, **data):
    await async_setup_component(hass, "input_boolean", {"input_boolean": {"vmc": {}, "wc": {}}})
    hass.states.async_set(HUM, "50", {"device_class": "humidity"})
    hass.states.async_set(TIN, "23", {"device_class": "temperature"})
    hass.states.async_set(TOUT, "23", {"device_class": "temperature"})
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, title="VMC",
        data={"vmc_entity": VMC, "toilet_light": LIGHT, "humidity_sensor": HUM,
              "temp_inside": TIN, "temp_outside": TOUT, **data},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Pas de cycle périodique pendant les tests par défaut
    await _svc(hass, "switch", "turn_off", "switch.vmc_periodic_airing")
    return entry


async def _svc(hass, domain, service, entity_id, **kw):
    await hass.services.async_call(domain, service, {"entity_id": entity_id, **kw}, blocking=True)
    await hass.async_block_till_done()


def _on(hass) -> bool:
    return hass.states.get(VMC).state == "on"


async def _advance(hass, freezer, **delta):
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_entities_created(hass):
    await _setup(hass)
    for eid in ("select.vmc_mode", "select.vmc_thermal_mode", "switch.vmc_toilet_trigger",
                "number.vmc_humidity_start_threshold", "button.vmc_boost",
                "sensor.vmc_status", "sensor.vmc_next_airing",
                "binary_sensor.vmc_ventilation_requested"):
        assert hass.states.get(eid) is not None, eid
    attrs = hass.states.get("sensor.vmc_status").attributes
    assert attrs["entities"]["mode"] == "select.vmc_mode"


async def test_toilet(hass, freezer: FrozenDateTimeFactory):
    await _setup(hass)
    # passage bref (< 30 s) : rien
    await _svc(hass, "input_boolean", "turn_on", LIGHT)
    await _advance(hass, freezer, seconds=10)
    await _svc(hass, "input_boolean", "turn_off", LIGHT)
    await _advance(hass, freezer, seconds=5)
    assert not _on(hass)
    # passage long : démarre après 30 s puis tourne 10 min après extinction
    await _svc(hass, "input_boolean", "turn_on", LIGHT)
    await _advance(hass, freezer, seconds=35)
    assert _on(hass)
    assert hass.states.get("sensor.vmc_status").state == "toilet"
    await _svc(hass, "input_boolean", "turn_off", LIGHT)
    await _advance(hass, freezer, minutes=9)
    assert _on(hass)
    await _advance(hass, freezer, minutes=2)
    assert not _on(hass)


async def test_humidity_hysteresis(hass, freezer):
    await _setup(hass)
    hass.states.async_set(HUM, "71", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert _on(hass)
    hass.states.async_set(HUM, "67", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert _on(hass)  # 67 > 70 - 5
    hass.states.async_set(HUM, "64", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert not _on(hass)


async def test_thermal_cool(hass):
    await _setup(hass)
    await _svc(hass, "select", "select_option", "select.vmc_thermal_mode", option="cool")
    hass.states.async_set(TIN, "25", {"device_class": "temperature"})
    hass.states.async_set(TOUT, "24", {"device_class": "temperature"})
    await hass.async_block_till_done()
    assert not _on(hass)  # écart 1 < 2
    hass.states.async_set(TOUT, "20", {"device_class": "temperature"})
    await hass.async_block_till_done()
    assert _on(hass)
    hass.states.async_set(TIN, "21.7", {"device_class": "temperature"})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.vmc_status").state == "thermal"  # hystérésis 0,5 °C
    hass.states.async_set(TIN, "21", {"device_class": "temperature"})
    await hass.async_block_till_done()
    assert not _on(hass)  # consigne 22 atteinte


async def test_periodic(hass, freezer):
    await _setup(hass)
    await _svc(hass, "switch", "turn_on", "switch.vmc_periodic_airing")
    await _advance(hass, freezer, hours=3, minutes=59)
    assert not _on(hass)
    await _advance(hass, freezer, minutes=2)
    assert _on(hass)
    assert hass.states.get("sensor.vmc_status").state == "periodic"
    await _advance(hass, freezer, minutes=16)
    assert not _on(hass)
    # le compteur repart de la fin du cycle
    await _advance(hass, freezer, hours=3, minutes=50)
    assert not _on(hass)
    await _advance(hass, freezer, minutes=15)
    assert _on(hass)


async def test_modes_and_boost(hass, freezer):
    await _setup(hass)
    await _svc(hass, "select", "select_option", "select.vmc_mode", option="on")
    assert _on(hass)
    await _svc(hass, "select", "select_option", "select.vmc_mode", option="off")
    hass.states.async_set(HUM, "90", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert not _on(hass)  # arrêt forcé l'emporte
    await _svc(hass, "select", "select_option", "select.vmc_mode", option="auto")
    assert _on(hass)
    hass.states.async_set(HUM, "50", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert not _on(hass)
    await _svc(hass, "button", "press", "button.vmc_boost")
    assert _on(hass)
    await _advance(hass, freezer, minutes=31)
    assert not _on(hass)


async def test_settings_persist(hass, hass_storage):
    entry = await _setup(hass)
    await _svc(hass, "number", "set_value", "number.vmc_humidity_start_threshold", value=80)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get("number.vmc_humidity_start_threshold").state) == 80


async def test_config_flow(hass):
    await async_setup_component(hass, "input_boolean", {"input_boolean": {"vmc": {}}})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "VMC", "vmc_entity": VMC}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {"vmc_entity": VMC, "vmc_inverted": False}


async def test_long_run_resets_periodic(hass, freezer):
    await _setup(hass)
    await _svc(hass, "switch", "turn_on", "switch.vmc_periodic_airing")
    await _advance(hass, freezer, hours=3)
    hass.states.async_set(HUM, "80", {"device_class": "humidity"})
    await hass.async_block_till_done()
    await _advance(hass, freezer, minutes=20)
    hass.states.async_set(HUM, "50", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert not _on(hass)
    # 20 min d'humidité valent un renouvellement : pas de cycle à 4 h
    await _advance(hass, freezer, hours=1, minutes=30)
    assert not _on(hass)


async def test_migration_v1(hass):
    await async_setup_component(hass, "input_boolean", {"input_boolean": {"vmc": {}}})
    entry = MockConfigEntry(domain=DOMAIN, version=1, title="VMC Control", data={
        "vmc_switch": VMC, "toilet_light": LIGHT, "humidity_sensor": HUM,
        "summer_mode": "input_boolean.ete", "delay_toilet": 15,
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.version == 2
    assert entry.data == {"vmc_entity": VMC, "toilet_light": LIGHT, "humidity_sensor": HUM}


async def test_inverted_logic(hass):
    await _setup(hass, vmc_inverted=True)
    # Au repos, la VMC doit être arrêtée => entité à « on »
    assert _on(hass)
    hass.states.async_set(HUM, "80", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert not _on(hass)  # en marche => entité à « off »
    attrs = hass.states.get("sensor.vmc_status").attributes
    assert attrs["vmc_running"] is True and attrs["vmc_inverted"] is True
    hass.states.async_set(HUM, "50", {"device_class": "humidity"})
    await hass.async_block_till_done()
    assert _on(hass)
