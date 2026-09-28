// LCARS energy: the energy of several consumers per day or month as stacked columns, as one lightweight
// card.
//
// A column per day (or month), stacked in the consumers' colours (the label column's blocks elsewhere on
// the page are the legend), a black gap between the pieces, the column's total above it, dashed lines at
// round kWh values. Today's column is the running one: its top piece flashes. Data comes from HA's
// long-term statistics (recorder/statistics_during_period, the `change` of each energy sensor per period),
// refreshed every 5 min. A pillar of LCARS buttons picks the range (stored per device, localStorage). The
// line at the top reads the range's total and mean; tap a column for its breakdown. On load and on a
// range switch the columns rise one after another. Animations stop with the motion switch
// (localStorage "lcars-motion" = "off").
//
// Config (written by the framework from an `energy` component, lcars/components/power.py):
//   type: custom:lcars-energy
//   series: [{entity, label, colour}]  # energy sensors with long-term statistics (total_increasing)
//   ranges: [{label: "7D", days: 7}, {label: "28D", days: 28}, {label: "12M", months: 12}]
//   unit: "kWh"
//   pillar: {width, gap, side: left | right, blocks: [{colour, code}], active, filler, ink,
//            row: "28px"}                # as lcars-history's: buttons one row high, the filler below
//   colours: {grid, axis, text, dim, today, flash}
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
const scale = () => Math.min(1, Math.max(0.6, 0.6 + 0.4 * (window.innerHeight - MIN_H) / (REF_H - MIN_H)));   // sz(px) = px * scale()
const len = (v) => (typeof v === "number" ? `${v}px` : v);

const RANGE_KEY = "lcars-energy-range";
const lcarsTapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};
const motionOn = () => {
  try { return localStorage.getItem("lcars-motion") !== "off"; } catch (e) { return true; }
};
const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));

class LcarsEnergy extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._data = null;
    try { this._range = +localStorage.getItem(RANGE_KEY) || 0; } catch (e) { this._range = 0; }
    if (this._range >= config.ranges.length) this._range = 0;
    this._animate = true;
    this._pick = null;
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
    clearTimeout(this._pickTimer);
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _build() {
    const c = this._config;
    const p = c.pillar;
    const col = c.colours;
    this.attachShadow({mode: "open"});
    const blocks = c.ranges.map((r, i) =>
      `<div class="blk" data-i="${i}"><em>${p.blocks[i].code}</em><span></span></div>`).join("");
    const pillar = `<div class="pillar">${blocks}<div style="background:${p.filler}"></div></div>`;
    const chart = `<div class="chart"><div class="info"></div><svg></svg></div>`;
    this.shadowRoot.innerHTML = `
      <style>
        @media (max-height: 520px) { .blk em { display: none; } }
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; font-family: ${c.font}; text-transform: uppercase;
                grid-template-columns: ${p.side === "right" ? `minmax(0, 1fr) ${len(p.width)}` : `${len(p.width)} minmax(0, 1fr)`}; }
        .chart { position: relative; min-height: 0; overflow: hidden; display: grid; grid-template-rows: auto 1fr; }
        .info { font-size: ${fz(15)}; color: ${col.dim}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                line-height: 1.3; min-height: 1.3em; }
        .info b { color: ${col.text}; font-weight: bold; }
        .info span { margin-right: 0.9em; }
        .info i { display: inline-block; width: 0.7em; height: 0.7em; margin-right: 0.3em; font-style: normal; }
        svg { width: 100%; height: 100%; display: block; min-height: 0; }
        svg text { font-family: ${c.font}; font-size: ${fz(12)}; fill: ${col.dim}; }
        svg text.tot { fill: ${col.text}; font-size: ${fz(13)}; }
        svg text.today { fill: ${col.today}; }
        svg .col { cursor: pointer; }
        svg .piece { transform-box: fill-box; transform-origin: 50% 100%; }
        svg .picked rect.hit { fill: ${col.text}; opacity: 0.08; }
        @keyframes rise { from { transform: scaleY(0); } }
        @keyframes flash { 0% { fill: ${col.flash}; } 3% { fill: var(--c); } }
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
      this._pick = null;
      this._animate = true;
      this._updateButtons();
      this._draw();
      this._load();
    }));
    this.shadowRoot.querySelector("svg").addEventListener("click", (ev) => {
      const g = ev.target.closest(".col");
      if (!g) return;
      lcarsTapSound();
      const i = +g.dataset.i;
      this._pick = this._pick === i ? null : i;
      clearTimeout(this._pickTimer);
      if (this._pick != null) this._pickTimer = setTimeout(() => { this._pick = null; this._draw(); }, 10e3);
      this._draw();
    });
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

  _buckets(r) {
    // the periods' local start times, oldest first; the last one is running
    const out = [];
    const now = new Date();
    if (r.months) {
      for (let k = r.months - 1; k >= 0; k--) out.push(new Date(now.getFullYear(), now.getMonth() - k, 1));
    } else {
      for (let k = r.days - 1; k >= 0; k--) out.push(new Date(now.getFullYear(), now.getMonth(), now.getDate() - k));
    }
    return out;
  }

  async _load() {
    if (!this._hass) return;
    const c = this._config;
    const range = this._range;
    const r = c.ranges[range];
    const buckets = this._buckets(r);
    const ids = c.series.map((s) => s.entity);
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period", start_time: buckets[0].toISOString(),
        end_time: new Date().toISOString(), statistic_ids: ids, period: r.months ? "month" : "day",
        types: ["change"], units: {energy: c.unit || "kWh"},
      });
      if (range !== this._range) return;   // switched while loading
      const key = (t) => {
        const d = new Date(typeof t === "number" ? t : Date.parse(t));
        return r.months ? `${d.getFullYear()}-${d.getMonth()}` : d.toDateString();
      };
      const index = new Map(buckets.map((b, i) => [key(b.getTime()), i]));
      const values = ids.map((id) => {
        const row = new Array(buckets.length).fill(0);
        for (const s of res[id] || []) {
          const i = index.get(key(s.start));
          if (i != null && s.change > 0) row[i] += s.change;
        }
        return row;
      });
      const changed = JSON.stringify(values) !== JSON.stringify(this._data && this._data.values);
      this._data = {buckets, values, months: !!r.months};
      if (changed) this._draw();
    } catch (e) { /* keep what is shown; next refresh retries */ }
  }

  static _step(max) {
    // a round step giving 3-5 lines up to max
    const raw = max / 4;
    const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
    for (const m of [1, 2, 2.5, 5, 10]) if (m * mag >= raw) return m * mag;
    return 10 * mag;
  }

  static _num(v) {
    return v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2);
  }

  _label(d, months, n) {
    if (months) return d.toLocaleDateString("en-GB", {month: "short"});
    if (n <= 10) return d.toLocaleDateString("en-GB", {weekday: "short"}) + " " + d.getDate();
    return d.toLocaleDateString("en-GB", {day: "2-digit", month: "2-digit"});
  }

  _info() {
    const c = this._config;
    const info = this.shadowRoot.querySelector(".info");
    const unit = c.unit || "kWh";
    if (!this._data) { info.innerHTML = "Retrieving telemetry…"; return; }
    const {buckets, values, months} = this._data;
    if (this._pick != null) {
      const i = this._pick;
      const d = buckets[i];
      const when = months ? d.toLocaleDateString("en-GB", {month: "long", year: "numeric"})
                          : d.toLocaleDateString("en-GB", {weekday: "short", day: "2-digit", month: "2-digit"});
      const parts = c.series.map((s, k) => ({s, v: values[k][i]})).filter((x) => x.v > 0.005).sort((a, b) => b.v - a.v);
      const tot = parts.reduce((a, x) => a + x.v, 0);
      info.innerHTML = `<span><b>${esc(when)} · ${LcarsEnergy._num(tot)} ${unit}</b></span>` + parts.map((x) =>
        `<span><i style="background:${x.s.colour}"></i>${esc(x.s.label)} ${LcarsEnergy._num(x.v)}</span>`).join("");
      return;
    }
    const totals = buckets.map((_, i) => values.reduce((a, row) => a + row[i], 0));
    const all = totals.reduce((a, v) => a + v, 0);
    const done = totals.slice(0, -1);   // the running period would pull the mean down
    const mean = done.length ? done.reduce((a, v) => a + v, 0) / done.length : all;
    const n = buckets.length;
    info.innerHTML = `<span><b>${n} ${months ? "months" : "days"} · ${LcarsEnergy._num(all)} ${unit}</b></span>`
      + `<span>Mean ${LcarsEnergy._num(mean)} ${unit} / ${months ? "month" : "day"}</span>`
      + `<span>${months ? "This month" : "Today"} ${LcarsEnergy._num(totals[n - 1])} ${unit}</span>`;
  }

  _draw() {
    const c = this._config;
    const col = c.colours;
    this._info();
    const svg = this.shadowRoot.querySelector("svg");
    const box = svg.getBoundingClientRect();
    const w = Math.round(box.width), h = Math.round(box.height);
    if (!w || !h) return;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    if (!this._data) { svg.innerHTML = ""; return; }
    const {buckets, values, months} = this._data;
    const n = buckets.length;
    const k = scale();
    const axisH = Math.round(20 * k), top = Math.round(16 * k), left = Math.round(44 * k);
    const plotH = h - axisH - top, plotW = w - left;
    const totals = buckets.map((_, i) => values.reduce((a, row) => a + row[i], 0));
    const step = LcarsEnergy._step(Math.max(...totals, 0.1));
    const max = Math.max(step * Math.ceil(Math.max(...totals, 0.1) / step), step);
    const y = (v) => top + plotH * (1 - v / max);
    const parts = [];
    for (let t = step; t <= max + 1e-9; t += step) {
      parts.push(`<line x1="${left}" x2="${w}" y1="${y(t)}" y2="${y(t)}" stroke="${col.grid}" stroke-dasharray="4" opacity="0.6"/>`,
                 `<text x="${left - 6}" y="${y(t) + 4}" text-anchor="end">${+t.toFixed(2)}</text>`);
    }
    parts.push(`<text x="${left - 6}" y="${y(0) + 4}" text-anchor="end">${c.unit || "kWh"}</text>`);
    const slot = plotW / n;
    const bw = Math.max(3, slot * (n > 14 ? 0.7 : 0.58));
    const gap = Math.max(1, Math.round(2 * k));
    const animate = this._animate && motionOn();
    const labelEvery = Math.ceil(n / Math.max(1, Math.floor(plotW / (48 * k))));
    for (let i = 0; i < n; i++) {
      const x = left + slot * i + (slot - bw) / 2;
      const now = i === n - 1;
      const delay = animate ? i * Math.min(60, 900 / n) : 0;
      const g = [`<g class="col${this._pick === i ? " picked" : ""}" data-i="${i}">`,
                 `<rect class="hit" x="${left + slot * i}" y="${top}" width="${slot}" height="${plotH}" fill="transparent"/>`];
      let base = 0;
      const pieces = values.map((row, s) => ({s, v: row[i]})).filter((p) => p.v > 0);
      pieces.forEach((p, idx) => {
        const y0 = y(base), y1 = y(base + p.v);
        base += p.v;
        const hgt = y0 - y1 - (idx < pieces.length - 1 ? gap : 0);
        if (hgt < 0.5) return;
        const colour = c.series[p.s].colour;
        const last = idx === pieces.length - 1;
        const anims = [];
        if (animate) anims.push(`rise 700ms cubic-bezier(.2, .8, .2, 1) ${delay}ms backwards`);
        if (now && last && motionOn()) anims.push("flash 4000ms step-end infinite");
        const style = `--c:${colour};${anims.length ? `animation:${anims.join(", ")}` : ""}`;
        g.push(`<rect class="piece" style="${style}" x="${x.toFixed(1)}" y="${y1.toFixed(1)}" width="${bw.toFixed(1)}" `
               + `height="${hgt.toFixed(1)}" fill="${colour}"/>`);
      });
      const tot = totals[i];
      if (tot > 0 && (n <= 14 || this._pick === i)) {
        g.push(`<text class="tot${now ? " today" : ""}" x="${x + bw / 2}" y="${y(tot) - 5}" text-anchor="middle">`
               + `${LcarsEnergy._num(tot)}</text>`);
      }
      if (i % labelEvery === (n - 1) % labelEvery) {
        g.push(`<text class="${now ? "today" : ""}" x="${x + bw / 2}" y="${h - 5}" text-anchor="middle">`
               + `${esc(this._label(buckets[i], months, n))}</text>`);
      }
      g.push("</g>");
      parts.push(g.join(""));
    }
    parts.push(`<line x1="${left}" x2="${w}" y1="${y(0)}" y2="${y(0)}" stroke="${col.axis}" stroke-width="2" opacity="0.9"/>`);
    svg.innerHTML = parts.join("");
    this._animate = false;
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-energy")) customElements.define("lcars-energy", LcarsEnergy);
