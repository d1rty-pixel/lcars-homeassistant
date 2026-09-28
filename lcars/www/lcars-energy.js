// LCARS energy: the energy of several consumers per day or month as stacked columns, as one lightweight
// card.
//
// A column per day (or month), stacked in the consumers' colours (the label column's blocks elsewhere on
// the page are the legend), a black gap between the pieces, the column's total above it, dashed lines at
// round kWh values. Today's column is the running one: its top piece lights up now and then. Or, switched
// by a toggle block below the range buttons, a graph: the consumers' mean load in W per hour (7D, 28D) or
// per day (12M) as smooth areas on a log scale above a zero line, their total mirrored below it. Data comes from HA's
// long-term statistics (recorder/statistics_during_period, the `change` of each energy sensor per period),
// refreshed every 5 min. A pillar of LCARS buttons picks the range (stored per device, localStorage). The
// line at the top reads the range's total and mean; tap a column for its breakdown. On load and on a
// range switch the columns rise one after another (the graph is revealed from the left). Animations stop with the motion switch
// (localStorage "lcars-motion" = "off").
//
// Config (written by the framework from an `energy` component, lcars/components/power.py):
//   type: custom:lcars-energy
//   series: [{entity, label, colour}]  # energy sensors with long-term statistics (total_increasing)
//   ranges: [{label: "7D", days: 7}, {label: "28D", days: 28}, {label: "12M", months: 12}]
//   unit: "kWh"
//   pillar: {width, gap, side: left | right, blocks: [{colour, code}], active, filler, ink,
//            row: "28px",                # as lcars-history's: buttons one row high, the filler below
//            toggle: {colour, code}}     # optional: the Columns / Graph block under the range buttons
//   colours: {grid, axis, text, dim, today, flash, total}   # total: the graph's total below the line
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

const RANGE_KEY = "lcars-energy-range", VIEW_KEY = "lcars-energy-view";
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
    try { this._view = config.pillar.toggle && localStorage.getItem(VIEW_KEY) === "graph" ? "graph" : "columns"; }
    catch (e) { this._view = "columns"; }
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
    const tog = p.toggle ? `<div class="blk tog" data-view="1"><em>${p.toggle.code}</em><span></span></div>` : "";
    const nb = c.ranges.length + (p.toggle ? 1 : 0);
    const pillar = `<div class="pillar">${blocks}${tog}<div style="background:${p.filler}"></div></div>`;
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
        svg .graph { cursor: pointer; }
        svg .reveal { animation: reveal 1400ms cubic-bezier(.3, .7, .3, 1) backwards; }
        @keyframes rise { from { transform: scaleY(0); } }
        @keyframes reveal { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
        @keyframes flash { 0% { fill: color-mix(in srgb, var(--c) 55%, ${col.flash}); } 4% { fill: var(--c); } }
        .pillar { display: grid; gap: ${len(p.gap)};
                  grid-template-rows: ${p.row ? `repeat(${nb}, ${p.row}) minmax(0, 1fr)`
                                              : `repeat(${nb}, minmax(0, 1fr)) 14px`}; }
        .blk { position: relative; display: flex; align-items: ${p.row ? "center" : "flex-end"}; justify-content: flex-end;
               padding: 0 8px ${p.row ? 0 : 4}px;
               color: ${p.ink}; font-size: ${fz(17)}; cursor: pointer; user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: ${fz(12, 0.67)}; }
        .blk:active { filter: brightness(1.3); }
      </style>
      <div class="wrap">${p.side === "right" ? chart + pillar : pillar + chart}</div>`;
    this.shadowRoot.querySelectorAll(".blk").forEach((el) => el.addEventListener("click", () => {
      lcarsTapSound();
      if (el.dataset.view) {
        this._view = this._view === "graph" ? "columns" : "graph";
        try { localStorage.setItem(VIEW_KEY, this._view); } catch (e) { /* this page only */ }
      } else {
        this._range = +el.dataset.i;
        try { localStorage.setItem(RANGE_KEY, String(this._range)); } catch (e) { /* this page only */ }
      }
      this._data = null;
      this._pick = null;
      this._animate = true;
      this._updateButtons();
      this._draw();
      this._load();
    }));
    this.shadowRoot.querySelector("svg").addEventListener("click", (ev) => {
      let i;
      if (this._view === "graph") {
        const d = this._data;
        if (!d || !d.times || !this._x) return;
        const box = ev.currentTarget.getBoundingClientRect();
        const t = this._x.inv(ev.clientX - box.left);
        i = d.times.reduce((b, tt, k) => (Math.abs(tt - t) < Math.abs(d.times[b] - t) ? k : b), 0);
      } else {
        const g = ev.target.closest(".col");
        if (!g) return;
        i = +g.dataset.i;
      }
      lcarsTapSound();
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
    const tog = this.shadowRoot.querySelector(".tog");
    if (tog) {
      tog.style.background = p.toggle.colour;
      tog.querySelector("span").textContent = this._view === "graph" ? "Graph" : "Columns";
    }
    this.shadowRoot.querySelectorAll(".blk:not(.tog)").forEach((el, i) => {
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
    if (this._view === "graph") return this._loadGraph();
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
      if (range !== this._range || this._view !== "columns") return;   // switched while loading
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

  async _loadGraph() {
    // mean load in W per hour (per day for month ranges) from the energy statistics
    const c = this._config;
    const range = this._range;
    const r = c.ranges[range];
    const now = new Date();
    const start = r.months ? new Date(now.getFullYear(), now.getMonth() - r.months + 1, 1)
                           : new Date(now.getTime() - r.days * 86400e3);
    start.setMinutes(0, 0, 0);
    const period = r.months ? "day" : "hour";
    const hours = r.months ? 24 : 1;
    const ids = c.series.map((s) => s.entity);
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period", start_time: start.toISOString(), end_time: now.toISOString(),
        statistic_ids: ids, period, types: ["change"], units: {energy: "kWh"},
      });
      if (range !== this._range || this._view !== "graph") return;
      const ms = (t) => (typeof t === "number" ? t : Date.parse(t));
      const times = [...new Set(ids.flatMap((id) => (res[id] || []).map((x) => ms(x.start))))].sort((a, b) => a - b);
      const index = new Map(times.map((t, i) => [t, i]));
      const values = ids.map((id) => {
        const row = new Array(times.length).fill(0);
        for (const x of res[id] || []) if (x.change > 0) row[index.get(ms(x.start))] = (x.change * 1000) / hours;
        return row;
      });
      const changed = JSON.stringify(values) !== JSON.stringify(this._data && this._data.values);
      this._data = {graph: true, times, values, from: start.getTime(), to: now.getTime(), hours, months: !!r.months};
      if (changed) this._draw();
    } catch (e) { /* keep what is shown; next refresh retries */ }
  }

  static _smooth(pts, move = "M") {
    // monotone cubic (Fritsch-Carlson), as in lcars-history.js: no overshoot below zero
    const n = pts.length;
    const f = (v) => v.toFixed(1);
    if (n < 3) return pts.map((p, i) => (i ? "L" : move) + f(p[0]) + " " + f(p[1])).join("");
    const d = [], m = [];
    for (let i = 0; i < n - 1; i++) d.push((pts[i + 1][1] - pts[i][1]) / ((pts[i + 1][0] - pts[i][0]) || 1));
    m.push(d[0]);
    for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2);
    m.push(d[n - 2]);
    for (let i = 0; i < n - 1; i++) {
      if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
      const a = m[i] / d[i], b = m[i + 1] / d[i], q = a * a + b * b;
      if (q > 9) { const t = 3 / Math.sqrt(q); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
    }
    let path = `${move}${f(pts[0][0])} ${f(pts[0][1])}`;
    for (let i = 0; i < n - 1; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], h = (x1 - x0) / 3;
      path += `C${f(x0 + h)} ${f(y0 + m[i] * h)} ${f(x1 - h)} ${f(y1 - m[i + 1] * h)} ${f(x1)} ${f(y1)}`;
    }
    return path;
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
    if (this._data.graph) return this._infoGraph(info);
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

  _infoGraph(info) {
    const c = this._config;
    const {times, values, hours, months} = this._data;
    const w = (v) => (v >= 1000 ? (v / 1000).toFixed(2) + " kW" : Math.round(v) + " W");
    if (this._pick != null && times[this._pick] != null) {
      const i = this._pick;
      const d = new Date(times[i]);
      const when = d.toLocaleDateString("en-GB", {weekday: "short", day: "2-digit", month: "2-digit"})
        + (months ? "" : " · " + d.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"}));
      const parts = c.series.map((s, k) => ({s, v: values[k][i]})).filter((x) => x.v >= 0.5).sort((a, b) => b.v - a.v);
      const tot = parts.reduce((a, x) => a + x.v, 0);
      info.innerHTML = `<span><b>${esc(when)} · ${w(tot)}</b></span>` + parts.map((x) =>
        `<span><i style="background:${x.s.colour}"></i>${esc(x.s.label)} ${w(x.v)}</span>`).join("");
      return;
    }
    const totals = times.map((_, i) => values.reduce((a, row) => a + row[i], 0));
    const kwh = totals.reduce((a, v) => a + (v * hours) / 1000, 0);
    const mean = totals.length ? totals.reduce((a, v) => a + v, 0) / totals.length : 0;
    const peak = Math.max(0, ...totals);
    const r = c.ranges[this._range];
    info.innerHTML = `<span><b>${r.months ? r.months + " months" : r.days + " days"} · ${LcarsEnergy._num(kwh)} ${c.unit || "kWh"}</b></span>`
      + `<span>Mean load ${w(mean)}</span><span>Peak ${w(peak)} / ${months ? "day" : "hour"}</span>`;
  }

  _drawGraph(svg, w, h) {
    const c = this._config;
    const col = c.colours;
    const {times, values, from, to, months} = this._data;
    const k = scale();
    const axisH = Math.round(20 * k), top = Math.round(12 * k), left = Math.round(44 * k);
    const plotH = h - axisH - top, plotW = w - left;
    const n = times.length;
    const totals = times.map((_, i) => values.reduce((a, row) => a + row[i], 0));
    // mirrored around a zero line in the middle, log scale: the consumers above, their total below
    const max = Math.max(10, ...totals) * 1.15;   // just above the peak; lines at the powers of ten below it
    const mid = top + plotH / 2;
    const f = (v) => Math.log10(1 + Math.max(0, v)) / Math.log10(1 + max);
    const y = (v, sign = 1) => mid - sign * (plotH / 2) * Math.min(1, f(v));
    const span = to - from || 1;
    const x = (t) => left + ((t - from) / span) * plotW;
    this._x = {inv: (px) => from + ((px - left) / plotW) * span};
    const parts = [];
    for (let t = 10; t <= max; t *= 10) {
      for (const sign of [1, -1]) {
        const yt = y(t, sign);
        parts.push(`<line x1="${left}" x2="${w}" y1="${yt}" y2="${yt}" stroke="${col.grid}" stroke-dasharray="4" opacity="0.6"/>`,
                   `<text x="${left - 6}" y="${yt + 4}" text-anchor="end">${t >= 1000 ? t / 1000 + "k" : t}</text>`);
      }
    }
    parts.push(`<text x="${left - 6}" y="${mid + 4}" text-anchor="end">W</text>`);
    const areas = [];
    if (n > 1) {
      // points in the middle of each period; each consumer an area of its own (log scales don't stack),
      // the largest drawn first so the small ones stay visible; the total mirrored below the line
      const half = (this._data.hours * 3600e3) / 2;
      const xs = times.map((t) => x(Math.min(to, t + half)));
      const area = (row, sign, colour, opacity) => {
        const line = LcarsEnergy._smooth(xs.map((xx, i) => [xx, y(row[i], sign)]));
        areas.push(`<path d="${line}L${xs[n - 1].toFixed(1)} ${mid}L${xs[0].toFixed(1)} ${mid}Z" fill="${colour}" `
                   + `fill-opacity="${opacity}"/>`,
                   `<path d="${line}" fill="none" stroke="${colour}" stroke-width="1.5"/>`);
      };
      area(totals, -1, col.total, 0.35);
      values.map((row, s) => ({row, s, sum: row.reduce((a, v) => a + v, 0)})).filter((r) => r.sum > 0)
        .sort((a, b) => b.sum - a.sum).forEach((r) => area(r.row, 1, c.series[r.s].colour, 0.3));
    }
    const animate = this._animate && motionOn();
    parts.push(`<g class="graph${animate ? " reveal" : ""}">`
      + `<rect x="${left}" y="${top}" width="${plotW}" height="${plotH}" fill="transparent"/>${areas.join("")}</g>`);
    if (this._pick != null && times[this._pick] != null) {
      const px = x(times[this._pick] + (this._data.hours * 3600e3) / 2);
      parts.push(`<line x1="${px}" x2="${px}" y1="${top}" y2="${top + plotH}" stroke="${col.text}" stroke-width="1.5" opacity="0.9"/>`);
    }
    // time axis: about 7 labels, dates (months: month names)
    const dayMs = 86400e3;
    const stepDays = months ? 0 : Math.max(1, Math.ceil(span / dayMs / 7));
    const first = new Date(from);
    if (months) first.setMonth(first.getMonth() + 1, 1); else first.setDate(first.getDate() + 1);
    first.setHours(0, 0, 0, 0);
    for (let d = new Date(first); d.getTime() < to;
         months ? d.setMonth(d.getMonth() + 1) : d.setDate(d.getDate() + stepDays)) {
      const xt = x(d.getTime());
      if (xt < left + 16 || xt > w - 16) continue;
      const label = months ? d.toLocaleDateString("en-GB", {month: "short"})
        : span <= 8 * dayMs ? d.toLocaleDateString("en-GB", {weekday: "short"}) + " " + d.getDate()
        : d.toLocaleDateString("en-GB", {day: "2-digit", month: "2-digit"});
      parts.push(`<line x1="${xt}" x2="${xt}" y1="${mid - 4}" y2="${mid + 4}" stroke="${col.axis}"/>`,
                 `<text x="${xt}" y="${h - 5}" text-anchor="middle">${esc(label)}</text>`);
    }
    parts.push(`<line x1="${left}" x2="${w}" y1="${mid}" y2="${mid}" stroke="${col.axis}" stroke-width="2" opacity="0.9"/>`);
    svg.innerHTML = parts.join("");
    this._animate = false;
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
    if (this._data.graph) return this._drawGraph(svg, w, h);
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
        if (now && last && motionOn()) anims.push("flash 9000ms step-end infinite");
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
