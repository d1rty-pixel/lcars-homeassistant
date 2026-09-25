// LCARS forecast: the next hours of a weather entity's hourly forecast as one lightweight card.
//
// HA no longer puts forecasts into weather attributes; like the standard forecast card this subscribes
// to weather/subscribe_forecast. One column per hour, top to bottom: hour, condition code, a vertical
// temperature bar (scaled to the shown hours), temperature, precipitation.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-forecast
//   entity: weather.forecast_home
//   hours: 12
//   segments: 8                      # temperature bar
//   colours: {temp, rain, off, text, dim, flash}
//   blink: [min_ms, max_ms], off_fraction: 0.025   # lit segments flash briefly, like lcars-bar.js
//   layout: "rows"                   # optional: three rows of fixed/fluid height, to line up with label
//   forecast_type: "hourly"          # the default; a toggle card switches hourly / daily per device
//   days: 7                          # columns in the daily forecast
//   mode: "toggle"                   # optional: only an LCARS block that switches hourly / daily (for a label
//   toggle: {colour, code, ink}      # column); it and the forecast talk through window events and share the
//                                    # choice in localStorage
//   rows: {time: "28px", rain: "28px"}, gap: 4      # blocks beside the card: time (hour + condition),
//                                    # temperature (bar + °C, the rest of the height), rain; rain: null
//                                    # puts the mm under the °C instead (two rows)
//   font: "Antonio, sans-serif"
const CONDITION_CODES = {
  "clear-night": "CLEAR", cloudy: "CLOUD", exceptional: "ALERT", fog: "FOG", hail: "HAIL",
  lightning: "STORM", "lightning-rainy": "STORM", partlycloudy: "PCLD", pouring: "POUR", rainy: "RAIN",
  snowy: "SNOW", "snowy-rainy": "SLEET", sunny: "SUN", windy: "WIND", "windy-variant": "WIND",
};

const TYPE_KEY = "lcars-forecast-type";     // hourly | daily, per device
const TYPE_EVENT = "lcars-forecast-type";
const storedType = (fallback) => {
  try { return localStorage.getItem(TYPE_KEY) || fallback; } catch (e) { return fallback; }
};
const tapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};

class LcarsForecast extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._type = storedType(config.forecast_type || "hourly");
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    if (config.mode === "toggle") this._buildToggle();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config.mode === "toggle") return;
    if (!this._unsub && hass.connection && this.isConnected) this._subscribe();
  }

  connectedCallback() {
    if (!this._onType) {
      this._onType = (e) => this._setType(e.detail);
      window.addEventListener(TYPE_EVENT, this._onType);
    }
    if (this._config.mode !== "toggle" && this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    if (this._onType) { window.removeEventListener(TYPE_EVENT, this._onType); this._onType = null; }
    this._unsubscribe();
  }

  _unsubscribe() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  _subscribe() {
    this._unsub = this._hass.connection.subscribeMessage(
      (event) => { this._forecast = event.forecast || []; this._render(); },
      {type: "weather/subscribe_forecast", forecast_type: this._type, entity_id: this._config.entity},
    );
    this._unsub.catch(() => { this._unsub = null; });
  }

  _setType(type) {
    if (!type || type === this._type) return;
    this._type = type;
    if (this._config.mode === "toggle") return this._drawToggle();
    this._unsubscribe();
    this._forecast = null;
    if (this._hass && this.isConnected) this._subscribe();
  }

  // the toggle: one LCARS block showing the current choice; a tap switches it for this device
  _buildToggle() {
    const c = this._config, g = c.toggle || {};
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .blk { position: relative; height: 100%; box-sizing: border-box; display: flex; align-items: center;
               justify-content: flex-end; padding: 0 8px; background: ${g.colour}; color: ${g.ink || "#000"};
               font-family: ${c.font}; font-size: 17px; text-transform: uppercase; cursor: pointer;
               user-select: none; -webkit-user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk:active { filter: brightness(1.3); }
      </style>
      <div class="blk"><em>${g.code || ""}</em><span></span></div>`;
    this.shadowRoot.querySelector(".blk").addEventListener("click", () => {
      tapSound();
      const next = this._type === "daily" ? "hourly" : "daily";
      try { localStorage.setItem(TYPE_KEY, next); } catch (e) { /* this page only */ }
      window.dispatchEvent(new CustomEvent(TYPE_EVENT, {detail: next}));
    });
    this._drawToggle();
  }

  _drawToggle() {
    this.shadowRoot.querySelector("span").textContent = this._type === "daily" ? "Daily ◂" : "Hourly ◂";
  }

  _render() {
    const c = this._config;
    const col = c.colours;
    if (c.mode === "toggle") return;
    const daily = this._type === "daily";
    const day0 = new Date();
    day0.setHours(0, 0, 0, 0);
    const now = daily ? day0.getTime() : Date.now() - 3600e3;
    const hours = (this._forecast || []).filter((f) => new Date(f.datetime).getTime() >= now)
      .slice(0, daily ? (c.days || 7) : c.hours);
    if (!hours.length) return;
    const temps = hours.map((f) => f.temperature);
    const lo = Math.min(...temps);
    const hi = Math.max(...temps);
    const n = c.segments || 8;
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const [bmin, bmax] = c.blink || [8000, 24000];
    // stable pseudo-random cycle per segment (same after every re-render)
    const cycle = (i, j) => bmin + ((i * 7919 + j * 104729) % 1000) / 1000 * (bmax - bmin);
    const rowsLayout = c.layout === "rows";
    const cols = hours.map((f, i) => {
      const d = new Date(f.datetime);
      const lit = Math.max(1, Math.round(((f.temperature - lo) / ((hi - lo) || 1)) * (n - 1)) + 1);
      const segs = [];
      for (let j = n - 1; j >= 0; j--) {
        if (j >= lit) { segs.push(`<i style="background:${col.off}"></i>`); continue; }
        const anim = motion ? `;animation:blink ${Math.round(cycle(i, j))}ms step-end infinite` : "";
        segs.push(`<i style="background:${col.temp}${anim}"></i>`);
      }
      const rain = f.precipitation || 0;
      if (rowsLayout) {
        const mm = `<span class="r" style="color:${rain > 0 ? col.rain : col.dim}">${rain.toFixed(1)}</span>`;
        const own = (c.rows || {}).rain !== null;       // rain in a row of its own
        return `<div class="col">
          <div class="time"><b>${daily ? d.toLocaleDateString("en-GB", {weekday: "short"}) : String(d.getHours()).padStart(2, "0")}</b><span class="cond">${CONDITION_CODES[f.condition] || "----"}</span></div>
          <div class="temp"><div class="bar">${segs.join("")}</div><span class="t">${Math.round(f.temperature)}°</span>${own ? "" : mm}</div>
          ${own ? mm : ""}
        </div>`;
      }
      return `<div class="col">
          <b>${daily ? d.toLocaleDateString("en-GB", {weekday: "short"}) : String(d.getHours()).padStart(2, "0")}</b>
          <span class="cond">${CONDITION_CODES[f.condition] || "----"}</span>
          <div class="bar">${segs.join("")}</div>
          <span class="t">${Math.round(f.temperature)}°</span>
          <span class="r" style="color:${rain > 0 ? col.rain : col.dim}">${rain.toFixed(1)}</span>
        </div>`;
    });
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .grid { display: grid; height: 100%; gap: 0 6px; grid-template-columns: repeat(${hours.length}, minmax(0, 1fr));
                font-family: ${c.font}; color: ${col.text}; text-transform: uppercase; line-height: 1.15; }
        .col { display: grid; grid-template-rows: auto auto minmax(0, 1fr) auto auto; justify-items: center;
               gap: 3px; min-height: 0; }
        b { font-weight: normal; font-size: 15px; color: ${col.text}; }
        .cond { font-size: 12px; color: ${col.dim}; }
        .t { font-size: 17px; font-weight: bold; color: ${col.temp}; }
        .r { font-size: 12px; }
        .bar { display: grid; width: 60%; min-height: 0; gap: 2px; grid-template-rows: repeat(${n}, minmax(0, 1fr)); }
        .bar i { display: block; --c: ${col.temp}; }
        .rows .col { grid-template-rows: ${(c.rows || {}).time || "28px"} minmax(0, 1fr)${(c.rows || {}).rain === null ? "" : ` ${(c.rows || {}).rain || "28px"}`};
                     gap: ${c.gap ?? 4}px; }
        .rows .time { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; line-height: 1; }
        .rows .temp { display: flex; flex-direction: column; align-items: center; min-height: 0; gap: 3px;
                      justify-self: stretch; }   /* full column width, so the bar's 60 % match the default layout */
        .rows .temp .bar { flex: 1 1 auto; }
        .rows .r { align-self: center; font-size: 14px; }
        .rows .temp .r { align-self: auto; font-size: 12px; }
        @keyframes blink { 0% { background: var(--c); }
                           ${Math.round((1 - (c.off_fraction ?? 0.025)) * 1000) / 10}%, 100% { background: ${col.flash || "#FFFFFF"}; } }
      </style>
      <div class="grid${rowsLayout ? " rows" : ""}">${cols.join("")}</div>`;
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get("lcars-forecast")) customElements.define("lcars-forecast", LcarsForecast);
