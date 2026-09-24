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
//   colours: {temp, rain, off, text, dim}
//   font: "Antonio, sans-serif"
const CONDITION_CODES = {
  "clear-night": "CLEAR", cloudy: "CLOUD", exceptional: "ALERT", fog: "FOG", hail: "HAIL",
  lightning: "STORM", "lightning-rainy": "STORM", partlycloudy: "PCLD", pouring: "POUR", rainy: "RAIN",
  snowy: "SNOW", "snowy-rainy": "SLEET", sunny: "SUN", windy: "WIND", "windy-variant": "WIND",
};

class LcarsForecast extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._unsub && hass.connection && this.isConnected) this._subscribe();
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  _subscribe() {
    this._unsub = this._hass.connection.subscribeMessage(
      (event) => { this._forecast = event.forecast || []; this._render(); },
      {type: "weather/subscribe_forecast", forecast_type: "hourly", entity_id: this._config.entity},
    );
    this._unsub.catch(() => { this._unsub = null; });
  }

  _render() {
    const c = this._config;
    const col = c.colours;
    const now = Date.now() - 3600e3;
    const hours = (this._forecast || []).filter((f) => new Date(f.datetime).getTime() >= now).slice(0, c.hours);
    if (!hours.length) return;
    const temps = hours.map((f) => f.temperature);
    const lo = Math.min(...temps);
    const hi = Math.max(...temps);
    const n = c.segments || 8;
    const cols = hours.map((f) => {
      const d = new Date(f.datetime);
      const lit = Math.max(1, Math.round(((f.temperature - lo) / ((hi - lo) || 1)) * (n - 1)) + 1);
      const segs = [];
      for (let j = n - 1; j >= 0; j--) segs.push(`<i style="background:${j < lit ? col.temp : col.off}"></i>`);
      const rain = f.precipitation || 0;
      return `<div class="col">
          <b>${String(d.getHours()).padStart(2, "0")}</b>
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
        .bar i { display: block; }
      </style>
      <div class="grid">${cols.join("")}</div>`;
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get("lcars-forecast")) customElements.define("lcars-forecast", LcarsForecast);
