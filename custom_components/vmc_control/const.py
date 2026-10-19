"""Constantes de l'intégration VMC Control."""

from __future__ import annotations

DOMAIN = "vmc_control"
VERSION = "2.1.1"

# --- Entités sources (config flow / options flow) ---
CONF_VMC = "vmc_entity"
CONF_VMC_INVERTED = "vmc_inverted"
CONF_LIGHT = "toilet_light"
CONF_HUMIDITY = "humidity_sensor"
CONF_TEMP_IN = "temp_inside"
CONF_TEMP_OUT = "temp_outside"

VMC_DOMAINS = ["switch", "fan", "light", "input_boolean"]
LIGHT_DOMAINS = ["light", "switch", "binary_sensor", "input_boolean"]

# --- Mode général ---
MODE_AUTO = "auto"
MODE_ON = "on"
MODE_OFF = "off"
MODES = [MODE_AUTO, MODE_ON, MODE_OFF]

# --- Mode thermique (différentiel de température) ---
THERMAL_OFF = "off"
THERMAL_COOL = "cool"  # rafraîchir : l'extérieur est plus frais
THERMAL_HEAT = "heat"  # réchauffer : l'extérieur est plus chaud
THERMAL_MODES = [THERMAL_OFF, THERMAL_COOL, THERMAL_HEAT]
THERMAL_HYSTERESIS = 0.5  # °C

# --- Clés des réglages (persistés dans le Store) ---
S_MODE = "mode"
S_TOILET_ENABLED = "toilet_enabled"
S_TOILET_DELAY_ON = "toilet_delay_on"  # s avant démarrage, lumière allumée
S_TOILET_RUN_AFTER = "toilet_run_after"  # min de marche après extinction
S_HUMIDITY_ENABLED = "humidity_enabled"
S_HUMIDITY_ON = "humidity_on"  # %
S_HUMIDITY_HYST = "humidity_hysteresis"  # %
S_PERIODIC_ENABLED = "periodic_enabled"
S_PERIODIC_INTERVAL = "periodic_interval"  # h
S_PERIODIC_DURATION = "periodic_duration"  # min
S_THERMAL_MODE = "thermal_mode"
S_THERMAL_TARGET = "thermal_target"  # °C
S_THERMAL_DELTA = "thermal_delta"  # °C
S_BOOST_DURATION = "boost_duration"  # min

DEFAULT_SETTINGS: dict = {
    S_MODE: MODE_AUTO,
    S_TOILET_ENABLED: True,
    S_TOILET_DELAY_ON: 30,
    S_TOILET_RUN_AFTER: 10,
    S_HUMIDITY_ENABLED: True,
    S_HUMIDITY_ON: 70,
    S_HUMIDITY_HYST: 5,
    S_PERIODIC_ENABLED: True,
    S_PERIODIC_INTERVAL: 4,
    S_PERIODIC_DURATION: 15,
    S_THERMAL_MODE: THERMAL_OFF,
    S_THERMAL_TARGET: 22.0,
    S_THERMAL_DELTA: 2.0,
    S_BOOST_DURATION: 30,
}

# --- Raisons de fonctionnement ---
R_FORCED = "forced"
R_BOOST = "boost"
R_TOILET = "toilet"
R_HUMIDITY = "humidity"
R_THERMAL = "thermal"
R_PERIODIC = "periodic"

STORAGE_VERSION = 1
CARD_URL = f"/{DOMAIN}/vmc-control-card.js"
