// LCARS power chart: a power sensor over 24 h, 7 d or 28 d as one lightweight card.
//
// Looks like the aquarium power chart (smooth filled area on a log scale, dashed W lines with labels,
// no legend), but draws plain SVG: LCARdS charts preload at most 168 h of history. Data comes from HA's
// long-term statistics (recorder/statistics_during_period, the peak of each period), refreshed every
// 5 min. A pillar of LCARS buttons picks the range; the choice is stored per device (localStorage).
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-power
//   entity: sensor.x_power
//   ranges: [{label: "24h", hours: 24, period: "5minute"}, ...]
//   ticks: [1, 10, 100, 1000]         # W lines
//   max: 2500                         # W at the top of the (log) scale
//   pillar: {width, gap, side: left | right, blocks: [{colour, code}], active, filler, ink}
//   colours: {line, fill_opacity, grid, axis, text}
//   font: "Antonio, sans-serif"
const RANGE_KEY = "lcars-power-range";
// LCARdS' click sound (its sound manager honours the sound helpers), as on LCARdS buttons
const lcarsTapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};

class LcarsPower extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._data = null;
    try { this._range = +localStorage.getItem(RANGE_KEY) || 0; } catch (e) { this._range = 0; }
    if (this._range >= config.ranges.length) this._range = 0;
    if (!this.shadowRoot) this._build();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
  }

  connectedCallback() {
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._draw());
      this._ro.observe(this);
    }
    clearInterval(this._timer);
    this._timer = setInterval(() => this._load(), 5 * 60e3);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _build() {
    const c = this._config;
    const p = c.pillar;
    this.attachShadow({mode: "open"});
    const blocks = c.ranges.map((r, i) =>
      `<div class="blk" data-i="${i}"><em>${p.blocks[i].code}</em><span></span></div>`).join("");
    const pillar = `<div class="pillar">${blocks}<div style="background:${p.filler}"></div></div>`;
    const chart = `<div class="chart"><svg></svg></div>`;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; font-family: ${c.font}; text-transform: uppercase;
                grid-template-columns: ${p.side === "right" ? `minmax(0, 1fr) ${p.width}px` : `${p.width}px minmax(0, 1fr)`}; }
        .chart { position: relative; min-height: 0; overflow: hidden; }
        svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        svg text { font-family: ${c.font}; font-size: 12px; fill: ${c.colours.text}; }
        .pillar { display: grid; gap: ${p.gap}px; grid-template-rows: repeat(${c.ranges.length}, minmax(0, 1fr)) 14px; }
        .blk { position: relative; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 4px;
               color: ${p.ink}; font-size: 17px; cursor: pointer; user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk:active { filter: brightness(1.3); }
      </style>
      <div class="wrap">${p.side === "right" ? chart + pillar : pillar + chart}</div>`;
    this.shadowRoot.querySelectorAll(".blk").forEach((el) => el.addEventListener("click", () => {
      lcarsTapSound();
      this._range = +el.dataset.i;
      try { localStorage.setItem(RANGE_KEY, String(this._range)); } catch (e) { /* this page only */ }
      this._data = null;
      this._updateButtons();
      this._draw();
      this._load();
    }));
    this._updateButtons();
  }

  _updateButtons() {
    const c = this._config;
    const p = c.pillar;
    this.shadowRoot.querySelectorAll(".blk").forEach((el, i) => {
      const on = i === this._range;
      el.style.background = on ? p.active : p.blocks[i].colour;
      el.querySelector("span").textContent = c.ranges[i].label + (on ? " ◂" : "");
    });
  }

  async _load() {
    if (!this._hass) return;
    const c = this._config;
    const range = this._range;
    const r = c.ranges[range];
    const end = new Date();
    const start = new Date(end.getTime() - r.hours * 3600e3);
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
        statistic_ids: [c.entity], period: r.period, types: ["max"],
      });
      if (range !== this._range) return;   // switched while loading
      this._data = (res[c.entity] || []).map((s) => ({t: s.start, v: s.max}));
      this._from = start.getTime();
      this._to = end.getTime();
      this._draw();
    } catch (e) { /* keep what is shown; next refresh retries */ }
  }

  static _smooth(pts) {
    // monotone cubic (Fritsch-Carlson), like ApexCharts' monotoneCubic: no overshoot below zero
    const n = pts.length;
    if (n < 3) return pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
    const d = [], m = [];
    for (let i = 0; i < n - 1; i++) d.push((pts[i + 1][1] - pts[i][1]) / ((pts[i + 1][0] - pts[i][0]) || 1));
    m.push(d[0]);
    for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2);
    m.push(d[n - 2]);
    for (let i = 0; i < n - 1; i++) {
      if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
      const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
      if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
    }
    let path = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < n - 1; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], h = (x1 - x0) / 3;
      path += `C${(x0 + h).toFixed(1)} ${(y0 + m[i] * h).toFixed(1)} ${(x1 - h).toFixed(1)} ${(y1 - m[i + 1] * h).toFixed(1)} `
            + `${x1.toFixed(1)} ${y1.toFixed(1)}`;
    }
    return path;
  }

  _draw() {
    const c = this._config;
    const col = c.colours;
    const svg = this.shadowRoot.querySelector("svg");
    const box = svg.getBoundingClientRect();
    const w = Math.round(box.width), h = Math.round(box.height);
    if (!w || !h) return;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    const axisH = 22, top = 8, plotH = h - axisH - top;
    const lg = (v) => Math.log10(1 + Math.max(0, v));
    const y = (v) => top + plotH * (1 - lg(v) / lg(c.max));
    const parts = [];
    for (const t of c.ticks) {
      parts.push(`<line x1="0" x2="${w}" y1="${y(t)}" y2="${y(t)}" stroke="${col.grid}" stroke-dasharray="4" opacity="0.6"/>`,
                 `<text x="4" y="${y(t) - 4}">${t} W</text>`);
    }
    const zero = y(0);
    if (this._data && this._data.length) {
      const span = this._to - this._from;
      const x = (t) => ((t - this._from) / span) * w;
      const pts = this._data.map((s) => [x(s.t), y(s.v ?? 0)]);
      const line = LcarsPower._smooth(pts);
      const x0 = pts[0][0].toFixed(1), x1 = pts[pts.length - 1][0].toFixed(1);
      parts.push(`<path d="${line}L${x1} ${zero}L${x0} ${zero}Z" fill="${col.line}" opacity="${col.fill_opacity}"/>`,
                 `<path d="${line}" fill="none" stroke="${col.line}" stroke-width="2"/>`);
      // time axis: about 7 labels, times for a day, dates for longer ranges
      const days = span > 36 * 3600e3;
      const step = days ? Math.ceil(span / 86400e3 / 7) * 86400e3 : 3 * 3600e3;
      const first = new Date(this._from);
      if (days) first.setHours(24, 0, 0, 0); else first.setHours(Math.ceil((first.getHours() + 1) / 3) * 3, 0, 0, 0);
      for (let t = first.getTime(); t < this._to; t += step) {
        const d = new Date(t);
        const label = days ? d.toLocaleDateString("en-GB", {day: "2-digit", month: "2-digit"})
                           : d.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"});
        const xt = x(t);
        if (xt < 20 || xt > w - 20) continue;
        parts.push(`<line x1="${xt}" x2="${xt}" y1="${zero}" y2="${zero + 5}" stroke="${col.axis}"/>`,
                   `<text x="${xt}" y="${h - 4}" text-anchor="middle">${label}</text>`);
      }
    }
    parts.push(`<line x1="0" x2="${w}" y1="${zero}" y2="${zero}" stroke="${col.axis}" stroke-width="2" opacity="0.9"/>`);
    svg.innerHTML = parts.join("");
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-power")) customElements.define("lcars-power", LcarsPower);
