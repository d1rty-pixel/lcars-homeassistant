// LCARS distribution: the live power of several consumers as EPS conduits, as one lightweight card.
//
// A row per consumer: its label block (a piece of the label column, in the consumer's colour), the value,
// and a conduit of segments growing away from the block, lit on a log scale up to `max`, with the
// consumer's share of the total at the far end. Energy flows through the lit segments: a calm wave of
// brightened segments runs outward, faster the more power the consumer draws (none at 0 W). An optional first row
// is the total: every segment lit, in the consumers' colours by their share, so the load's distribution
// reads at a glance. On first render the lit segments power up one after another. Tap a row: more-info.
// Animations stop with the per-device motion switch (localStorage "lcars-motion" = "off").
//
// Config (written by the framework from a `distribution` component, lcars/components/power.py):
//   type: custom:lcars-distribution
//   consumers: [{entity, label, colour, code}]   # power sensors (W or kW)
//   total: {label, colour, code}   # optional: the total row on top (the sum of the consumers)
//   max: 2500                      # top of the log scale (W)
//   segments: 32                   # per conduit
//   wave: 16                       # segments from one wave to the next
//   speed: [7000, 2400]            # ms a wave takes for `wave` segments at 1 W and at `max`
//   label_w: "130px", value_w: "120px", share_w: "64px"   # CSS lengths
//   row: "28px", gap: 4            # row height (CSS) and gap (px)
//   colours: {off, text, dim, ink, flash}   # flash: what the wave's head is mixed with
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
const len = (v) => (typeof v === "number" ? `${v}px` : v);

const motionOn = () => {
  try { return localStorage.getItem("lcars-motion") !== "off"; } catch (e) { return true; }
};

class LcarsDistribution extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._keys = {};
    this._booted = false;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    this._build();
  }

  static watts(st) {
    if (!st) return null;
    const v = parseFloat(st.state);
    if (isNaN(v)) return null;
    return (st.attributes.unit_of_measurement || "W").toLowerCase() === "kw" ? v * 1000 : v;
  }

  static fmt(w) {
    if (w == null) return "—";
    if (w >= 1000) return (w / 1000).toFixed(w >= 10000 ? 1 : 2) + " kW";
    return (w === 0 ? "0" : w < 10 ? w.toFixed(1) : Math.round(w)) + " W";
  }

  _build() {
    const c = this._config;
    const col = c.colours;
    const n = c.segments || 32;
    const rows = (c.total ? [{...c.total, total: true}] : []).concat(c.consumers);
    this._rows = rows;
    const segs = Array.from({length: n}, () => "<i></i>").join("");
    const html = rows.map((r, i) => `
      <div class="blk" data-i="${i}" style="background:${r.colour}"><em>${r.code || ""}</em><span>${r.label}</span></div>
      <div class="val" data-i="${i}"></div>
      <div class="cond" data-i="${i}">${segs}</div>
      <div class="share" data-i="${i}"></div>`).join("");
    this.shadowRoot.innerHTML = `
      <style>
        @media (max-height: 520px) { .blk em { display: none; } }
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; align-content: start; font-family: ${c.font}; text-transform: uppercase;
                grid-template-columns: ${len(c.label_w)} ${len(c.value_w)} minmax(0, 1fr) ${len(c.share_w)};
                grid-auto-rows: ${len(c.row)}; gap: ${len(c.gap)} 16px; }
        .blk { position: relative; display: flex; align-items: center; justify-content: flex-end; padding: 0 8px;
               color: ${col.ink}; font-size: ${fz(17)}; cursor: pointer; user-select: none; overflow: hidden;
               white-space: nowrap; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: ${fz(12, 0.67)}; }
        .val, .share { display: flex; align-items: center; font-size: var(--lcars-data-size, ${fz(22)});
                       font-weight: bold; color: ${col.text}; white-space: nowrap; cursor: pointer; }
        .share { justify-content: flex-end; color: ${col.dim}; font-weight: normal; }
        .cond { display: grid; grid-template-columns: repeat(${n}, minmax(0, 1fr)); gap: 3px;
                margin: clamp(6px, 1dvh, 10px) 0; cursor: pointer; }
        .cond i { position: relative; background: ${col.off}; }
        .cond i::before { content: ""; position: absolute; inset: 0; background: var(--c, transparent);
                          animation: var(--anim, none); }
        @keyframes flow { 0% { background: var(--head); } ${(100 / (c.wave || 16)).toFixed(2)}% { background: var(--trail); }
                          ${(200 / (c.wave || 16)).toFixed(2)}% { background: var(--c); } }
        @keyframes boot { from { opacity: 0; } to { opacity: 0; } }
      </style>
      <div class="wrap">${html}</div>`;
    this.shadowRoot.querySelectorAll("[data-i]").forEach((el) => el.addEventListener("click", () => {
      const r = this._rows[+el.dataset.i];
      const entity = r.total ? (this._top || c.consumers[0]).entity : r.entity;
      this.dispatchEvent(new CustomEvent("hass-more-info", {detail: {entityId: entity}, bubbles: true, composed: true}));
    }));
    if (this._hass) this._update(true);
  }

  set hass(hass) {
    this._hass = hass;
    this._update(false);
  }

  _update(force) {
    const c = this._config;
    const hass = this._hass;
    let changed = force;
    for (const r of c.consumers) {
      const st = hass.states[r.entity];
      const k = st ? st.state + st.attributes.unit_of_measurement : "-";
      if (this._keys[r.entity] !== k) { this._keys[r.entity] = k; changed = true; }
    }
    if (!changed || !this.shadowRoot.querySelector(".wrap")) return;
    const w = c.consumers.map((r) => LcarsDistribution.watts(hass.states[r.entity]));
    const sum = w.reduce((a, v) => a + (v > 0 ? v : 0), 0);
    let top = null;
    c.consumers.forEach((r, i) => { if (w[i] > 0 && (!top || w[i] > top.w)) top = {entity: r.entity, w: w[i]}; });
    this._top = top;
    const boot = !this._booted && motionOn();
    this._booted = true;
    const values = (c.total ? [sum] : []).concat(w);
    this._rows.forEach((r, i) => {
      const v = values[i];
      const val = this.shadowRoot.querySelector(`.val[data-i="${i}"]`);
      const share = this.shadowRoot.querySelector(`.share[data-i="${i}"]`);
      val.textContent = LcarsDistribution.fmt(v);
      val.style.color = v == null || v <= 0 ? c.colours.dim : c.colours.text;
      if (r.total) share.textContent = `${w.filter((x) => x > 0).length}/${w.length}`;
      else share.textContent = v == null ? "" : sum > 0 ? Math.round((100 * Math.max(0, v)) / sum) + " %" : "0 %";
      this._conduit(i, r, v, sum, w, boot);
    });
  }

  _colours(r, v, sum, w, n) {
    // which colour each segment is lit in (null: off)
    const c = this._config;
    if (r.total) {
      if (!(sum > 0)) return Array(n).fill(null);
      const out = [];
      let acc = 0, k = 0;
      const cum = w.map((x) => (acc += Math.max(0, x || 0)) / sum);
      for (let j = 0; j < n; j++) {
        const mid = (j + 0.5) / n;
        while (k < cum.length - 1 && cum[k] < mid) k++;
        out.push(c.consumers[k].colour);
      }
      return out;
    }
    if (v == null || v <= 0) return Array(n).fill(null);
    const f = Math.log10(1 + v) / Math.log10(1 + (c.max || 2500));
    const lit = Math.max(1, Math.min(n, Math.round(n * f)));
    return Array.from({length: n}, (_, j) => (j < lit ? r.colour : null));
  }

  _conduit(i, r, v, sum, w, boot) {
    const c = this._config;
    const n = c.segments || 32;
    const wave = c.wave || 16;
    const [slow, fast] = c.speed || [7000, 2400];
    const p = r.total ? sum : v;
    const f = p > 0 ? Math.min(1, Math.log10(1 + p) / Math.log10(1 + (c.max || 2500))) : 0;
    // ms per wave, bucketed so small changes don't restart the animation
    const dur = Math.round((slow * Math.pow(fast / slow, f)) / 50) * 50;
    const cols = this._colours(r, v, sum, w, n);
    const motion = motionOn();
    const segs = this.shadowRoot.querySelectorAll(`.cond[data-i="${i}"] i`);
    segs.forEach((s, j) => {
      const lit = cols[j];
      const key = `${lit}|${lit && motion && p > 0 ? dur : 0}`;
      if (s._key === key && !boot) return;
      s._key = key;
      s.style.setProperty("--c", lit || "transparent");
      // the wave's head: the segment's colour brightened, not white, and a fainter step behind it
      s.style.setProperty("--head", lit ? `color-mix(in srgb, ${lit} 50%, ${c.colours.flash || "#FFFFFF"})` : "");
      s.style.setProperty("--trail", lit ? `color-mix(in srgb, ${lit} 78%, ${c.colours.flash || "#FFFFFF"})` : "");
      const anims = [];
      if (boot && lit) anims.push(`boot 1ms step-end ${i * 90 + j * 22}ms backwards`);
      if (lit && motion && p > 0) {
        // phase: segment j flashes (j % wave) / wave of a cycle after segment 0, so the wave runs outward
        const d = -((wave - (j % wave)) % wave) / wave * dur;
        anims.push(`flow ${dur}ms step-end ${d.toFixed(0)}ms infinite`);
      }
      s.style.setProperty("--anim", anims.length ? anims.join(", ") : "none");
    });
  }

  getCardSize() {
    return this._rows ? this._rows.length : 4;
  }
}

if (!customElements.get("lcars-distribution")) customElements.define("lcars-distribution", LcarsDistribution);
