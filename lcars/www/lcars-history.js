// LCARS history: a sensor over 24 h, 7 d or 28 d as one lightweight card (e.g. a power meter).
//
// A smooth filled area with dashed, labelled lines at the ticks and no legend, drawn as plain SVG (LCARdS
// charts preload at most 168 h of history). Data comes from HA's long-term statistics
// (recorder/statistics_during_period: the peak of each period by default), refreshed every 5 min. A
// pillar of LCARS buttons picks the range; the choice is stored per device (localStorage). Also
// registered as lcars-power (its name before the framework).
//
// Config (written by the framework from a `history` component, lcars/components/data.py):
//   type: custom:lcars-history
//   entity: sensor.x_power            # a sensor with long-term statistics (a state_class)
//   ranges: [{label: "24h", hours: 24, period: "5minute"}, ...]
//   scale: log | linear               # log (default): log10(1 + value), for values across magnitudes
//   ticks: [1, 10, 100, 1000]         # labelled lines
//   min: 0, max: 2500                 # the scale (min: linear only)
//   unit: "W"                         # default: the entity's unit_of_measurement
//   stat: max | mean | min            # which statistic of each period (default max: peaks stay visible)
//   pillar: {width, gap, side: left | right, blocks: [{colour, code}], active, filler, ink,
//            row: "28px"}             # optional: buttons one row high (like label blocks), the filler below;
//                                     # without it they share the height and the filler is 14 px
//   colours: {line, fill_opacity, grid, axis, text}
//   font: "Antonio, sans-serif"
// Fluid sizes, the same as the framework's (Len, font() in lcars/engine/sizes.py): full size from REF_H
// viewport height up, shrinking linearly below it to a minimum share at MIN_H: sizes to 60 % (sz), fonts to
// 80 % (fz; LCARS numbers to 67 %). len(): a size from the config (a number of px or a CSS length) as CSS.
const REF_H = 720, MIN_H = 400;
const fluid = (px, lo) => {
  const k = px * (1 - lo) / (REF_H - MIN_H), c = px * lo - k * MIN_H, n = (x) => +x.toFixed(3);
  return `clamp(${n(px * lo)}px, calc(${n(k * 100)}dvh ${c < 0 ? "-" : "+"} ${n(Math.abs(c))}px), ${px}px)`;
};
const fz = (px, lo = 0.8) => fluid(px, lo);
const sz = (px) => fluid(px, 0.6);
const scale = () => Math.min(1, Math.max(0.6, 0.6 + 0.4 * (window.innerHeight - MIN_H) / (REF_H - MIN_H)));   // sz(px) = px * scale()
const len = (v) => (typeof v === "number" ? `${v}px` : v);

const RANGE_KEY = "lcars-history-range", OLD_RANGE_KEY = "lcars-power-range";
// LCARdS' click sound (its sound manager honours the sound helpers), as on LCARdS buttons
const lcarsTapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};

class LcarsHistory extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._data = null;
    try { this._range = +(localStorage.getItem(RANGE_KEY) ?? localStorage.getItem(OLD_RANGE_KEY)) || 0; }
    catch (e) { this._range = 0; }
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
        /* phones (PHONE_H in lcars/engine/sizes.py): no LCARS numbers, they are decoration and collide with labels */
        @media (max-height: 520px) { .blk em { display: none; } }
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; font-family: ${c.font}; text-transform: uppercase;
                grid-template-columns: ${p.side === "right" ? `minmax(0, 1fr) ${len(p.width)}` : `${len(p.width)} minmax(0, 1fr)`}; }
        .chart { position: relative; min-height: 0; overflow: hidden; }
        svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        svg text { font-family: ${c.font}; font-size: ${fz(12)}; fill: ${c.colours.text}; }
        .pillar { display: grid; gap: ${len(p.gap)};
                  grid-template-rows: ${p.row ? `repeat(${c.ranges.length}, ${p.row}) minmax(0, 1fr)`
                                              : `repeat(${c.ranges.length}, minmax(0, 1fr)) 14px`}; }
        .blk { position: relative; display: flex; align-items: ${p.row ? "center" : "flex-end"}; justify-content: flex-end;
               padding: 0 8px ${p.row ? 0 : 4}px;
               color: ${p.ink}; font-size: ${fz(17)}; cursor: pointer; user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: ${fz(12, 0.67)}; }
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
        statistic_ids: [c.entity], period: r.period, types: [c.stat || "max"],
      });
      if (range !== this._range) return;   // switched while loading
      this._data = (res[c.entity] || []).map((s) => ({t: s.start, v: s[c.stat || "max"]}));
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
    const st = this._hass && this._hass.states[c.entity];
    const unit = c.unit ?? ((st && st.attributes.unit_of_measurement) || "");
    const lo = c.scale === "linear" ? (c.min ?? 0) : 0;
    const f = c.scale === "linear" ? (v) => (v - lo) / ((c.max - lo) || 1)
                                   : (v) => Math.log10(1 + Math.max(0, v)) / Math.log10(1 + c.max);
    const y = (v) => top + plotH * (1 - Math.min(1, Math.max(0, f(v))));
    const parts = [];
    for (const t of c.ticks) {
      parts.push(`<line x1="0" x2="${w}" y1="${y(t)}" y2="${y(t)}" stroke="${col.grid}" stroke-dasharray="4" opacity="0.6"/>`,
                 `<text x="4" y="${y(t) - 4}">${t}${unit ? " " + unit : ""}</text>`);
    }
    const zero = y(lo);
    if (this._data && this._data.length) {
      const span = this._to - this._from;
      const x = (t) => ((t - this._from) / span) * w;
      const pts = this._data.map((s) => [x(s.t), y(s.v ?? lo)]);
      const line = LcarsHistory._smooth(pts);
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

if (!customElements.get("lcars-history")) customElements.define("lcars-history", LcarsHistory);
if (!customElements.get("lcars-power")) customElements.define("lcars-power", class extends LcarsHistory {});
