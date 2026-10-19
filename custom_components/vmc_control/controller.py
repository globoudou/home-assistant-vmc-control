"""Logique de pilotage de la VMC.

Le contrôleur est événementiel : il réagit aux changements d'état des entités
sources (lumière, humidité, températures, VMC) et se réveille aux échéances
calculées (fin de temporisation, prochain cycle périodique, fin de boost).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HUMIDITY,
    CONF_LIGHT,
    CONF_TEMP_IN,
    CONF_TEMP_OUT,
    CONF_VMC,
    DEFAULT_SETTINGS,
    DOMAIN,
    MODE_OFF,
    MODE_ON,
    R_BOOST,
    R_FORCED,
    R_HUMIDITY,
    R_PERIODIC,
    R_THERMAL,
    R_TOILET,
    S_BOOST_DURATION,
    S_HUMIDITY_ENABLED,
    S_HUMIDITY_HYST,
    S_HUMIDITY_ON,
    S_MODE,
    S_PERIODIC_DURATION,
    S_PERIODIC_ENABLED,
    S_PERIODIC_INTERVAL,
    S_THERMAL_DELTA,
    S_THERMAL_MODE,
    S_THERMAL_TARGET,
    S_TOILET_DELAY_ON,
    S_TOILET_ENABLED,
    S_TOILET_RUN_AFTER,
    STORAGE_VERSION,
    THERMAL_COOL,
    THERMAL_HEAT,
    THERMAL_HYSTERESIS,
)

_LOGGER = logging.getLogger(__name__)

_INVALID = (None, STATE_UNKNOWN, STATE_UNAVAILABLE)


class VmcController:
    """Cerveau de l'intégration : un par entrée de configuration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._wakeup_unsub: CALLBACK_TYPE | None = None
        self._started = False

        # État d'exécution
        self.light_on_since: datetime | None = None
        self.light_off_at: datetime | None = None
        self.vmc_on_since: datetime | None = None
        self.last_cycle_end: datetime | None = None
        self.periodic_until: datetime | None = None
        self.boost_until: datetime | None = None
        self.active: dict[str, bool] = {
            R_TOILET: False,
            R_HUMIDITY: False,
            R_THERMAL: False,
            R_PERIODIC: False,
            R_BOOST: False,
        }
        self.reasons: list[str] = []
        self.demand = False
        self.entity_ids: dict[str, str] = {}

    # ------------------------------------------------------------------ config
    @property
    def conf(self) -> dict[str, Any]:
        """Entités sources : les options (si présentes) remplacent les données."""
        return dict(self.entry.options or self.entry.data)

    def _src(self, key: str) -> str | None:
        return self.conf.get(key) or None

    # --------------------------------------------------------------- lifecycle
    async def async_start(self) -> None:
        stored = await self._store.async_load() or {}
        for key, value in (stored.get("settings") or {}).items():
            if key in DEFAULT_SETTINGS:
                self.settings[key] = value
        if ts := stored.get("last_cycle_end"):
            self.last_cycle_end = dt_util.parse_datetime(ts)

        now = dt_util.utcnow()
        if self.last_cycle_end is None:
            # Première installation : le compteur périodique démarre maintenant.
            self.last_cycle_end = now

        light = self._src(CONF_LIGHT)
        if light and (st := self.hass.states.get(light)) and st.state == STATE_ON:
            self.light_on_since = st.last_changed
        vmc = self._src(CONF_VMC)
        if vmc and (st := self.hass.states.get(vmc)) and st.state == STATE_ON:
            self.vmc_on_since = st.last_changed

        tracked = [e for e in (self._src(k) for k in (
            CONF_VMC, CONF_LIGHT, CONF_HUMIDITY, CONF_TEMP_IN, CONF_TEMP_OUT
        )) if e]
        self._unsubs.append(
            async_track_state_change_event(self.hass, tracked, self._on_state_change)
        )
        self._unsubs.append(async_at_started(self.hass, self._on_started))

    async def _on_started(self, _hass: HomeAssistant) -> None:
        self._started = True
        await self.async_evaluate()

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._wakeup_unsub:
            self._wakeup_unsub()
            self._wakeup_unsub = None
        await self._async_save_now()

    # ---------------------------------------------------------- listeners/UI
    @callback
    def add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    # ---------------------------------------------------------------- storage
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "settings": self.settings,
            "last_cycle_end": self.last_cycle_end.isoformat()
            if self.last_cycle_end
            else None,
        }

    async def _async_save_now(self) -> None:
        await self._store.async_save(self._data_to_save())

    # ---------------------------------------------------------------- actions
    async def async_set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self._store.async_delay_save(self._data_to_save, 2)
        await self.async_evaluate()

    async def async_start_boost(self) -> None:
        minutes = float(self.settings[S_BOOST_DURATION])
        self.boost_until = dt_util.utcnow() + timedelta(minutes=minutes)
        await self.async_evaluate()

    async def async_stop_boost(self) -> None:
        self.boost_until = None
        await self.async_evaluate()

    # ------------------------------------------------------------ evenements
    async def _on_state_change(self, event: Event) -> None:
        entity_id = event.data["entity_id"]
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        new_s = new.state if new else None
        old_s = old.state if old else None
        # Horodatage réel de la transition (indépendant du délai de traitement).
        now = new.last_changed if new else dt_util.utcnow()

        if entity_id == self._src(CONF_LIGHT) and new_s != old_s:
            if new_s == STATE_ON:
                self.light_on_since = now
                self.light_off_at = None
            elif old_s == STATE_ON:
                delay = timedelta(seconds=float(self.settings[S_TOILET_DELAY_ON]))
                # Un passage plus court que le délai ne déclenche rien.
                if self.light_on_since and now - self.light_on_since >= delay:
                    self.light_off_at = now
                self.light_on_since = None

        if entity_id == self._src(CONF_VMC) and new_s != old_s:
            if new_s == STATE_ON:
                self.vmc_on_since = now
            elif old_s == STATE_ON:
                self._close_cycle(now)
                self.vmc_on_since = None

        await self.async_evaluate()

    def _close_cycle(self, now: datetime) -> None:
        """Un fonctionnement assez long compte comme un renouvellement d'air."""
        if self.vmc_on_since is None:
            return
        needed = timedelta(minutes=float(self.settings[S_PERIODIC_DURATION]))
        if now - self.vmc_on_since >= needed:
            self.last_cycle_end = now
            self._store.async_delay_save(self._data_to_save, 2)

    # ----------------------------------------------------------- évaluation
    def _float_state(self, key: str) -> float | None:
        entity_id = self._src(key)
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in _INVALID:
            return None
        try:
            return float(st.state)
        except ValueError:
            return None

    def _eval_toilet(self, now: datetime, wake: list[datetime]) -> bool:
        if not self.settings[S_TOILET_ENABLED] or not self._src(CONF_LIGHT):
            return False
        if self.light_on_since:
            start = self.light_on_since + timedelta(
                seconds=float(self.settings[S_TOILET_DELAY_ON])
            )
            if now >= start:
                return True
            wake.append(start)
            return False
        if self.light_off_at:
            end = self.light_off_at + timedelta(
                minutes=float(self.settings[S_TOILET_RUN_AFTER])
            )
            if now < end:
                wake.append(end)
                return True
            self.light_off_at = None
        return False

    def _eval_humidity(self) -> bool:
        if not self.settings[S_HUMIDITY_ENABLED]:
            return False
        hum = self._float_state(CONF_HUMIDITY)
        if hum is None:
            return False
        on = float(self.settings[S_HUMIDITY_ON])
        if self.active[R_HUMIDITY]:
            return hum > on - float(self.settings[S_HUMIDITY_HYST])
        return hum >= on

    def _eval_thermal(self) -> bool:
        mode = self.settings[S_THERMAL_MODE]
        if mode not in (THERMAL_COOL, THERMAL_HEAT):
            return False
        t_in = self._float_state(CONF_TEMP_IN)
        t_out = self._float_state(CONF_TEMP_OUT)
        if t_in is None or t_out is None:
            return False
        target = float(self.settings[S_THERMAL_TARGET])
        delta = float(self.settings[S_THERMAL_DELTA])
        h = THERMAL_HYSTERESIS if self.active[R_THERMAL] else 0.0
        if mode == THERMAL_COOL:
            return t_in > target - h and (t_in - t_out) >= delta - h
        return t_in < target + h and (t_out - t_in) >= delta - h

    def _eval_periodic(self, now: datetime, vmc_on: bool, wake: list[datetime]) -> bool:
        if not self.settings[S_PERIODIC_ENABLED]:
            self.periodic_until = None
            return False
        if self.periodic_until:
            if now < self.periodic_until:
                wake.append(self.periodic_until)
                return True
            self.periodic_until = None
            self.last_cycle_end = now
            self._store.async_delay_save(self._data_to_save, 2)
        if vmc_on:
            # Déjà en marche pour une autre raison : on vérifie s'il a assez tourné.
            needed = timedelta(minutes=float(self.settings[S_PERIODIC_DURATION]))
            if self.vmc_on_since and now - self.vmc_on_since >= needed:
                self.last_cycle_end = now
            elif self.vmc_on_since:
                wake.append(self.vmc_on_since + needed)
            return False
        due = self.next_cycle
        if due and now >= due:
            self.periodic_until = now + timedelta(
                minutes=float(self.settings[S_PERIODIC_DURATION])
            )
            wake.append(self.periodic_until)
            return True
        if due:
            wake.append(due)
        return False

    @property
    def next_cycle(self) -> datetime | None:
        if not self.settings[S_PERIODIC_ENABLED] or self.last_cycle_end is None:
            return None
        if self.periodic_until:
            return self.periodic_until
        return self.last_cycle_end + timedelta(
            hours=float(self.settings[S_PERIODIC_INTERVAL])
        )

    @property
    def vmc_is_on(self) -> bool:
        vmc = self._src(CONF_VMC)
        st = self.hass.states.get(vmc) if vmc else None
        return bool(st and st.state == STATE_ON)

    async def async_evaluate(self) -> None:
        now = dt_util.utcnow()
        wake: list[datetime] = []
        vmc_on = self.vmc_is_on

        if self.boost_until and now >= self.boost_until:
            self.boost_until = None
        if self.boost_until:
            wake.append(self.boost_until)

        self.active[R_BOOST] = self.boost_until is not None
        self.active[R_TOILET] = self._eval_toilet(now, wake)
        self.active[R_HUMIDITY] = self._eval_humidity()
        self.active[R_THERMAL] = self._eval_thermal()
        self.active[R_PERIODIC] = self._eval_periodic(now, vmc_on, wake)

        mode = self.settings[S_MODE]
        if mode == MODE_ON:
            reasons = [R_FORCED]
        elif mode == MODE_OFF:
            reasons = []
        else:
            reasons = [
                r
                for r in (R_BOOST, R_TOILET, R_HUMIDITY, R_THERMAL, R_PERIODIC)
                if self.active[r]
            ]
        self.reasons = reasons
        self.demand = bool(reasons)

        if self._started:
            await self._async_apply(vmc_on)
        self._schedule_wakeup(wake)
        self._notify()

    async def _async_apply(self, vmc_on: bool) -> None:
        vmc = self._src(CONF_VMC)
        if not vmc:
            return
        st = self.hass.states.get(vmc)
        if st is None or st.state in _INVALID:
            return
        if self.demand == vmc_on:
            return
        domain = vmc.split(".", 1)[0]
        service = "turn_on" if self.demand else "turn_off"
        _LOGGER.debug("VMC %s (%s) raisons=%s", service, vmc, self.reasons)
        await self.hass.services.async_call(
            domain, service, {"entity_id": vmc}, blocking=False
        )

    @callback
    def _schedule_wakeup(self, wake: list[datetime]) -> None:
        if self._wakeup_unsub:
            self._wakeup_unsub()
            self._wakeup_unsub = None
        now = dt_util.utcnow()
        future = [w for w in wake if w > now]
        # Filet de sécurité : réévaluation au moins toutes les 5 minutes.
        target = min(future + [now + timedelta(minutes=5)])
        self._wakeup_unsub = async_track_point_in_utc_time(
            self.hass, self._on_wakeup, target + timedelta(seconds=1)
        )

    async def _on_wakeup(self, _now: datetime) -> None:
        self._wakeup_unsub = None
        await self.async_evaluate()

    # ------------------------------------------------------------- exposés
    def snapshot(self) -> dict[str, Any]:
        """Attributs exposés à la carte et aux automatisations."""

        def _state(key: str) -> str | None:
            e = self._src(key)
            st = self.hass.states.get(e) if e else None
            return st.state if st else None

        return {
            "vmc_entity": self._src(CONF_VMC),
            "vmc_state": _state(CONF_VMC),
            "light_entity": self._src(CONF_LIGHT),
            "light_state": _state(CONF_LIGHT),
            "humidity_entity": self._src(CONF_HUMIDITY),
            "humidity": self._float_state(CONF_HUMIDITY),
            "temp_inside_entity": self._src(CONF_TEMP_IN),
            "temp_inside": self._float_state(CONF_TEMP_IN),
            "temp_outside_entity": self._src(CONF_TEMP_OUT),
            "temp_outside": self._float_state(CONF_TEMP_OUT),
            "reasons": list(self.reasons),
            "demand": self.demand,
            "active": dict(self.active),
            "boost_until": self.boost_until.isoformat() if self.boost_until else None,
            "next_cycle": self.next_cycle.isoformat() if self.next_cycle else None,
            "settings": dict(self.settings),
            "entities": dict(self.entity_ids),
        }
