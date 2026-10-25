/*
 * VMC Control card — carte de contrôle et de paramétrage.
 * Servie automatiquement par l'intégration (aucune ressource à déclarer).
 *
 *   type: custom:vmc-control-card
 *   entity: sensor.vmc_etat        # capteur « État » de l'intégration
 *   title: VMC                     # facultatif
 */

// Toute valeur dynamique (titre, états, noms, identifiants) passe par esc()
// avant d'être insérée dans innerHTML.
const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);

const FR = {
  running: "En marche", stopped: "Arrêtée", unavailable: "Indisponible",
  auto: "Auto", on: "Marche", off: "Arrêt",
  boost: "Boost", stopBoost: "Arrêter",
  remaining: (m) => `reste ${m} min`,
  triggers: "Déclencheurs", settings: "Paramètres",
  toilet: "Toilettes", humidity: "Humidité", thermal: "Différentiel de température",
  periodic: "Renouvellement périodique",
  lightOn: "Lumière allumée", lightOff: "Lumière éteinte",
  threshold: "seuil", inside: "Int", outside: "Ext",
  next: "Prochain", disabled: "Désactivé", cool: "Rafraîchir", heat: "Réchauffer",
  reasons: {
    forced: "marche forcée", boost: "boost", toilet: "toilettes", humidity: "humidité",
    thermal: "différentiel de température", periodic: "renouvellement périodique",
  },
  params: {
    toilet_delay_on: "Délai avant démarrage",
    toilet_run_after: "Marche après extinction",
    humidity_on: "Seuil de démarrage",
    humidity_hysteresis: "Hystérésis",
    periodic_interval: "Intervalle",
    periodic_duration: "Durée",
    thermal_target: "Consigne intérieure",
    thermal_delta: "Écart minimal int/ext",
    boost_duration: "Durée du boost",
  },
  notFound: "Entité VMC Control introuvable. Indiquez le capteur « État » dans « entity ».",
};

const PARAM_GROUPS = [
  ["toilet", "mdi:toilet", ["toilet_delay_on", "toilet_run_after"]],
  ["humidity", "mdi:water-percent", ["humidity_on", "humidity_hysteresis"]],
  ["periodic", "mdi:timer-sync-outline", ["periodic_interval", "periodic_duration"]],
  ["thermal", "mdi:thermometer-lines", ["thermal_target", "thermal_delta"]],
  ["boost", "mdi:fan-plus", ["boost_duration"]],
];

class VmcControlCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity requis (capteur « État » de VMC Control)");
    this._config = config;
    this._open = false;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  static getStubConfig(hass) {
    const e = Object.values(hass.states).find((s) => s.attributes && s.attributes.vmc_control);
    return { entity: e ? e.entity_id : "sensor.vmc_etat" };
  }

  getCardSize() { return 6; }

  connectedCallback() {
    this._tick = setInterval(() => this._render(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._tick);
  }

  set hass(hass) {
    this._hass = hass;
    // Ne pas écraser un champ en cours de saisie.
    const active = this.shadowRoot && this.shadowRoot.activeElement;
    if (active && active.tagName === "INPUT") return;
    this._render();
  }

  // ---------------------------------------------------------------- helpers
  _st(id) { return id ? this._hass.states[id] : undefined; }

  _call(domain, service, entity_id, data = {}) {
    this._hass.callService(domain, service, { entity_id, ...data });
  }

  _fmt(v, unit, digits = 1) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return `${Number(v).toFixed(digits).replace(/\.0$/, "")}${unit}`;
  }

  _time(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    const today = new Date().toDateString() === d.toDateString();
    const t = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return today ? t : `${d.toLocaleDateString([], { weekday: "short" })} ${t}`;
  }

  // ----------------------------------------------------------------- render
  _render() {
    if (!this._hass || !this._config) return;
    const root = this.shadowRoot;
    const status = this._st(this._config.entity);
    if (!status || !status.attributes.entities) {
      root.innerHTML = `<ha-card><div class="warn">${esc(FR.notFound)}</div></ha-card>`;
      return;
    }
    const a = status.attributes;
    const ent = a.entities;
    const s = a.settings || {};
    const act = a.active || {};
    const vmcOn = a.vmc_running !== undefined ? a.vmc_running : a.vmc_state === "on";
    const vmcKnown = a.vmc_state === "on" || a.vmc_state === "off";
    const mode = s.mode;

    let statusLine = vmcKnown ? (vmcOn ? FR.running : FR.stopped) : FR.unavailable;
    if (a.reasons && a.reasons.length) {
      statusLine += " · " + a.reasons.map((r) => FR.reasons[r] || r).join(", ");
    }

    let boostHtml;
    if (a.boost_until) {
      const min = Math.max(0, Math.ceil((new Date(a.boost_until) - Date.now()) / 60000));
      boostHtml = `<button class="chip on" data-press="${esc(ent.stop_boost)}">
        <ha-icon icon="mdi:fan-remove"></ha-icon>${esc(FR.boost)} · ${esc(FR.remaining(min))}</button>`;
    } else {
      boostHtml = `<button class="chip" data-press="${esc(ent.boost)}">
        <ha-icon icon="mdi:fan-plus"></ha-icon>${esc(FR.boost)} ${esc(this._fmt(s.boost_duration, " min", 0))}</button>`;
    }

    const seg = (entityId, current, options) => `<div class="seg">${options
      .map(([v, label]) => `<button class="${current === v ? "sel" : ""}"
          data-select="${esc(entityId)}" data-option="${esc(v)}">${esc(label)}</button>`)
      .join("")}</div>`;

    const toggle = (key) => {
      const id = ent[key];
      const on = this._st(id) && this._st(id).state === "on";
      return `<ha-switch data-toggle="${esc(id)}" ${on ? "checked" : ""}></ha-switch>`;
    };

    const row = (icon, label, detail, active, control) => `
      <div class="row ${active ? "active" : ""}">
        <ha-icon icon="${esc(icon)}"></ha-icon>
        <div class="txt"><div class="label">${esc(label)}</div><div class="detail">${esc(detail)}</div></div>
        ${control /* HTML built above from escaped values */}
      </div>`;

    const rows = [];
    if (a.light_entity) {
      rows.push(row("mdi:toilet", FR.toilet,
        `${a.light_state === "on" ? FR.lightOn : FR.lightOff} · +${this._fmt(s.toilet_run_after, " min", 0)}`,
        act.toilet, toggle("toilet_enabled")));
    }
    if (a.humidity_entity) {
      rows.push(row("mdi:water-percent", FR.humidity,
        `${this._fmt(a.humidity, " %")} · ${FR.threshold} ${this._fmt(s.humidity_on, " %", 0)}`,
        act.humidity, toggle("humidity_enabled")));
    }
    rows.push(row("mdi:timer-sync-outline", FR.periodic,
      `${this._fmt(s.periodic_duration, " min", 0)} / ${this._fmt(s.periodic_interval, " h")} · ${FR.next} ${this._time(a.next_cycle)}`,
      act.periodic, toggle("periodic_enabled")));
    if (a.temp_inside_entity && a.temp_outside_entity) {
      rows.push(row("mdi:thermometer-lines", FR.thermal,
        `${FR.inside} ${this._fmt(a.temp_inside, " °C")} · ${FR.outside} ${this._fmt(a.temp_outside, " °C")}`,
        act.thermal, ""));
      rows.push(`<div class="subseg">${seg(ent.thermal_mode, s.thermal_mode,
        [["off", FR.disabled], ["cool", FR.cool], ["heat", FR.heat]])}</div>`);
    }

    const params = PARAM_GROUPS.map(([group, icon, keys]) => {
      if (group === "toilet" && !a.light_entity) return "";
      if (group === "humidity" && !a.humidity_entity) return "";
      if (group === "thermal" && !(a.temp_inside_entity && a.temp_outside_entity)) return "";
      return `<div class="pgroup"><div class="ptitle"><ha-icon icon="${esc(icon)}"></ha-icon>${esc(FR[group])}</div>
        ${keys.map((k) => {
          const st = this._st(ent[k]);
          if (!st) return "";
          const at = st.attributes;
          return `<label class="param"><span>${esc(FR.params[k])}</span>
            <span class="inp"><input type="number" data-number="${esc(ent[k])}"
              min="${esc(at.min)}" max="${esc(at.max)}" step="${esc(at.step)}" value="${esc(st.state)}">
            <em>${esc(at.unit_of_measurement)}</em></span></label>`;
        }).join("")}</div>`;
    }).join("");

    root.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="head">
          <div class="fan ${vmcOn ? "spin" : ""}"><ha-icon icon="mdi:fan"></ha-icon></div>
          <div class="txt">
            <div class="title">${esc(this._config.title || "VMC")}</div>
            <div class="detail">${esc(statusLine)}</div>
          </div>
        </div>
        <div class="controls">
          ${seg(ent.mode, mode, [["auto", FR.auto], ["on", FR.on], ["off", FR.off]])}
          ${boostHtml}
        </div>
        <div class="section ${mode !== "auto" ? "dim" : ""}">
          <div class="stitle">${esc(FR.triggers)}</div>
          ${rows.join("")}
        </div>
        <details ${this._open ? "open" : ""}>
          <summary>${esc(FR.settings)}</summary>
          <div class="params">${params}</div>
        </details>
      </ha-card>`;

    this._bind();
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-select]").forEach((el) =>
      el.addEventListener("click", () =>
        this._call("select", "select_option", el.dataset.select, { option: el.dataset.option })));
    root.querySelectorAll("[data-press]").forEach((el) =>
      el.addEventListener("click", () => this._call("button", "press", el.dataset.press)));
    root.querySelectorAll("[data-toggle]").forEach((el) =>
      el.addEventListener("change", () => this._call("switch", "toggle", el.dataset.toggle)));
    root.querySelectorAll("[data-number]").forEach((el) =>
      el.addEventListener("change", () => {
        const v = parseFloat(el.value);
        if (!isNaN(v)) this._call("number", "set_value", el.dataset.number, { value: v });
        el.blur();
      }));
    const det = root.querySelector("details");
    if (det) det.addEventListener("toggle", () => { this._open = det.open; });
  }
}

const STYLE = `
  ha-card { padding: 16px; }
  .warn { color: var(--error-color); }
  .head { display: flex; align-items: center; gap: 14px; }
  .fan { width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center;
    background: var(--secondary-background-color); color: var(--secondary-text-color); flex: none; }
  .fan.spin { background: rgba(var(--rgb-primary-color, 3,169,244), 0.15); color: var(--primary-color); }
  .fan.spin ha-icon { animation: spin 1.4s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .fan.spin ha-icon { animation: none; } }
  .txt { flex: 1; min-width: 0; }
  .title { font-size: 1.15em; font-weight: 500; }
  .detail { color: var(--secondary-text-color); font-size: 0.9em; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 8px; align-items: center; }
  .seg { display: inline-flex; border-radius: 18px; overflow: hidden;
    border: 1px solid var(--divider-color); }
  .seg button { border: 0; background: none; padding: 8px 14px; font: inherit; cursor: pointer;
    color: var(--primary-text-color); }
  .seg button + button { border-left: 1px solid var(--divider-color); }
  .seg button.sel { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .chip { display: inline-flex; align-items: center; gap: 6px; border-radius: 18px; padding: 7px 14px;
    border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color);
    font: inherit; cursor: pointer; }
  .chip ha-icon { --mdc-icon-size: 18px; }
  .chip.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  .section { margin-top: 8px; }
  .section.dim .row { opacity: 0.55; }
  .stitle { font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--secondary-text-color); margin: 12px 0 4px; }
  .row { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
  .row > ha-icon { color: var(--secondary-text-color); }
  .row.active > ha-icon { color: var(--primary-color); }
  .row.active .label::after { content: "●"; color: var(--primary-color); margin-left: 6px; font-size: 0.7em;
    vertical-align: middle; }
  .subseg { padding: 0 0 8px 36px; }
  .subseg .seg button { padding: 6px 12px; font-size: 0.9em; }
  details { margin-top: 8px; border-top: 1px solid var(--divider-color); padding-top: 8px; }
  summary { cursor: pointer; padding: 6px 0; font-weight: 500; }
  .pgroup { margin: 8px 0 12px; }
  .ptitle { display: flex; align-items: center; gap: 8px; font-size: 0.9em; color: var(--secondary-text-color);
    margin-bottom: 4px; }
  .ptitle ha-icon { --mdc-icon-size: 18px; }
  .param { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 4px 0 4px 26px; }
  .inp { display: inline-flex; align-items: center; gap: 6px; }
  .inp em { font-style: normal; color: var(--secondary-text-color); min-width: 24px; font-size: 0.9em; }
  input[type=number] { width: 70px; padding: 6px 8px; border-radius: 8px; font: inherit; text-align: right;
    border: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--primary-text-color); }
`;

const CARD_TAG = "vmc-control-card";

// Le frontend de Home Assistant peut remplacer window.customElements après le
// chargement de ce script (registre « scoped »). Une carte définie trop tôt
// reste alors invisible : le sélecteur de cartes attend indéfiniment.
// On (re)définit donc la carte dans le registre actif tant que nécessaire.
function defineCard() {
  const registry = window.customElements;
  if (registry.get(CARD_TAG)) return true;
  try {
    // Une sous-classe neuve évite l'erreur « constructor already used ».
    registry.define(CARD_TAG, class extends VmcControlCard {});
  } catch (err) {
    console.warn("vmc-control-card:", err);
  }
  return !!registry.get(CARD_TAG);
}

defineCard();
let tries = 0;
const watcher = setInterval(() => {
  defineCard();
  if (++tries >= 60) clearInterval(watcher); // surveille 30 s
}, 500);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: "VMC Control",
    description: "Contrôle et paramétrage de la VMC (mode, boost, déclencheurs, seuils).",
    preview: true,
  });
}
