// LCARS topology: a network's links and the data flowing through them, as one lightweight card.
//
// A row per node (a router's uplink, a switch, an access point, a server): its label block (a piece of the
// label column, in the node's colour, red while its status entity says it's down, grey while unknown), the
// rate towards it, a conduit of two lanes growing away from the block, the rate away from it, and an info
// value (clients, latency). The upper lane carries the data towards the node: a calm wave runs outward,
// away from the block; the lower lane carries the data coming back: its wave runs inward. Both are lit on
// a log scale up to the node's `max`, and their waves run faster the higher the rate (none at 0).
// A node's children (level 1, 2) hang from it: their block is narrower, a stub in the parent's colour in
// front of it, so the stubs of consecutive children read as a branch of the label column.
// On first render the lit segments power up one after another. Tap a row: more-info (its `tap` entity,
// else its down entity). Animations stop with the per-device motion switch (localStorage "lcars-motion").
//
// Config (written by the framework from a `topology` component, lcars/components/network.py):
//   type: custom:lcars-topology
//   nodes: [{label, colour, code, level, down, up, status, ok: [states], info, info_unit, info_round,
//            max, tap}]          # down/up: rate sensors; status: an entity whose `ok` states mean "up"
//   max: 1000                    # top of the log scale (in the sensors' unit)
//   unit: "Mb/s"                 # shown after the rates
//   segments: 32                 # per lane
//   wave: 16                     # segments from one wave to the next
//   speed: [7000, 2400]          # ms a wave takes for `wave` segments at the lowest rate and at `max`
//   label_w, value_w, info_w: CSS lengths; indent: px (a child's stub and gap per level)
//   row: "28px", gap: 4          # row height (CSS) and gap (px)
//   colours: {off, text, dim, ink, flash, down, unknown}   # down: a node that's down; unknown: no status
//   font: "Antonio, sans-serif"
// Fluid sizes, the same as the framework's (Len, font() in lcars/engine/sizes.py): full size from REF_H
// viewport height up, shrinking linearly below it to a minimum share at MIN_H: sizes to 60 % (sz), fonts to
// 80 % (fz; LCARS numbers to 67 %). len(): a size from the config (a number of px or a CSS length) as CSS.
const REF_H = 720, MIN_H = 400;
const fluid = (px, lo) => {
  const k = px * (1 - lo) / (REF_H - MIN_H), c = px * lo - k * MIN_H, n = (x) => +x.toFixed(3);
  return `clamp(${n(px * lo)}px, calc(${n(k * 100)}dvh ${c < 0 ? "-" : "+"} ${n(Math.abs(c))}px), ${px}px)`;
};
const sz = (px, lo = 0.6) => fluid(px, lo);
const fz = (px, lo = 0.8) => fluid(px, lo);
const len = (v) => (typeof v === "number" ? `${v}px` : v);

const motionOn = () => {
  try { return localStorage.getItem("lcars-motion") !== "off"; } catch (e) { return true; }
};

class LcarsTopology extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._keys = {};
    this._booted = false;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    this._build();
  }

  static num(st) {
    if (!st) return null;
    const v = parseFloat(st.state);
    return isNaN(v) ? null : v;
  }

  static fmt(v) {
    if (v == null) return "—";
    if (v === 0) return "0";
    return v >= 100 ? Math.round(v).toString() : v >= 10 ? v.toFixed(1) : v >= 0.01 ? v.toFixed(2) : "<0.01";
  }

  _build() {
    const c = this._config;
    const col = c.colours;
    const n = c.segments || 32;
    const segs = Array.from({length: n}, () => "<i></i>").join("");
    const indent = c.indent || 14;
    const html = c.nodes.map((r, i) => {
      const lv = r.level || 0;
      // a child's stubs: one per level, in the colours of the nodes above it
      const stubs = (r.stubs || []).map((s) => `<b style="background:${s}"></b>`).join("");
      return `
      <div class="lbl" data-i="${i}" style="--lv:${lv}">${stubs}<div class="blk" data-b="${i}"><em>${r.code || ""}</em><span>${r.label}</span></div></div>
      <div class="val down" data-i="${i}"></div>
      <div class="cond" data-i="${i}"><div class="lane" data-l="down">${segs}</div><div class="lane" data-l="up">${segs}</div></div>
      <div class="val up" data-i="${i}"></div>
      <div class="info" data-i="${i}"></div>`;
    }).join("");
    this.shadowRoot.innerHTML = `
      <style>
        @media (max-height: 520px) { .blk em { display: none; } }
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; align-content: start; font-family: ${c.font}; text-transform: uppercase;
                grid-template-columns: ${len(c.label_w)} ${len(c.value_w)} minmax(0, 1fr) ${len(c.value_w)} ${len(c.info_w)};
                grid-auto-rows: ${len(c.row)}; gap: ${len(c.gap)} ${sz(16)}; }
        .lbl { display: flex; gap: ${len(c.gap)}; cursor: pointer; user-select: none; min-width: 0; }
        .lbl b { flex: 0 0 ${sz(indent)}; }
        .blk { position: relative; flex: 1; display: flex; align-items: center; justify-content: flex-end; padding: 0 8px;
               color: ${col.ink}; font-size: ${fz(17)}; overflow: hidden; white-space: nowrap; min-width: 0; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: ${fz(12, 0.67)}; }
        .val, .info { display: flex; align-items: center; font-size: var(--lcars-data-size, ${fz(22)});
                      font-weight: bold; color: ${col.text}; white-space: nowrap; cursor: pointer; overflow: hidden; }
        .val.down { justify-content: flex-start; }
        .val.up { justify-content: flex-end; }
        .val small { font-size: 0.6em; font-weight: normal; color: ${col.dim}; margin-left: 0.3em; }
        .info { justify-content: flex-end; color: ${col.dim}; font-weight: normal; }
        .cond { display: grid; grid-template-rows: 1fr 1fr; gap: 3px; margin: clamp(5px, 0.9dvh, 9px) 0; cursor: pointer; }
        .lane { display: grid; grid-template-columns: repeat(${n}, minmax(0, 1fr)); gap: 3px; }
        .lane i { position: relative; background: ${col.off}; }
        .lane i::before { content: ""; position: absolute; inset: 0; background: var(--c, transparent);
                          animation: var(--anim, none); }
        @keyframes flow { 0% { background: var(--head); } ${(100 / (c.wave || 16)).toFixed(2)}% { background: var(--trail); }
                          ${(200 / (c.wave || 16)).toFixed(2)}% { background: var(--c); } }
        @keyframes boot { from { opacity: 0; } to { opacity: 0; } }
      </style>
      <div class="wrap">${html}</div>`;
    this.shadowRoot.querySelectorAll("[data-i]").forEach((el) => el.addEventListener("click", () => {
      const r = c.nodes[+el.dataset.i];
      const entity = r.tap || r.down || r.status || r.info;
      if (entity) this.dispatchEvent(new CustomEvent("hass-more-info", {detail: {entityId: entity}, bubbles: true, composed: true}));
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
    for (const r of c.nodes) {
      for (const e of [r.down, r.up, r.status, r.info]) {
        if (!e) continue;
        const st = hass.states[e];
        const k = st ? st.state : "-";
        if (this._keys[e] !== k) { this._keys[e] = k; changed = true; }
      }
    }
    if (!changed || !this.shadowRoot.querySelector(".wrap")) return;
    const boot = !this._booted && motionOn();
    this._booted = true;
    const unit = c.unit ? `<small>${c.unit}</small>` : "";
    c.nodes.forEach((r, i) => {
      const q = (s) => this.shadowRoot.querySelector(`${s}[data-i="${i}"]`);
      const down = LcarsTopology.num(hass.states[r.down]);
      const up = LcarsTopology.num(hass.states[r.up]);
      const st = r.status ? hass.states[r.status] : null;
      const ok = r.ok || ["on", "home", "connected"];
      const state = !r.status ? "ok" : !st || st.state === "unavailable" || st.state === "unknown" ? "unknown"
        : ok.includes(st.state) ? "ok" : "down";
      const blkCol = state === "ok" ? r.colour : state === "down" ? c.colours.down : c.colours.unknown;
      this.shadowRoot.querySelector(`.blk[data-b="${i}"]`).style.background = blkCol;
      const dv = q(".val.down"), uv = q(".val.up");
      if (r.down) dv.innerHTML = LcarsTopology.fmt(down) + unit;
      if (r.up) uv.innerHTML = LcarsTopology.fmt(up) + unit;
      dv.style.color = down > 0 ? c.colours.text : c.colours.dim;
      uv.style.color = up > 0 ? c.colours.text : c.colours.dim;
      const info = q(".info");
      if (r.info) {
        const v = hass.states[r.info];
        const x = v ? parseFloat(v.state) : NaN;
        const s = !v ? "—" : isNaN(x) ? v.state : r.info_round != null ? x.toFixed(r.info_round) : String(x);
        info.textContent = s + (r.info_unit ? " " + r.info_unit : "");
      }
      const lit = state === "down" ? null : r.colour;
      this._lane(i, "down", down, r, lit, boot, false);
      this._lane(i, "up", up, r, lit, boot, true);
    });
  }

  _lane(i, lane, v, r, colour, boot, inward) {
    const c = this._config;
    const n = c.segments || 32;
    const wave = c.wave || 16;
    const [slow, fast] = c.speed || [7000, 2400];
    const max = r.max || c.max || 1000;
    // log scale from 0.01 (one segment) to max, so a link idling at a few kbit/s still shows a spark
    const f = v > 0 ? Math.min(1, Math.max(0, Math.log10(v / 0.01)) / Math.log10(max / 0.01)) : 0;
    const count = v > 0 ? Math.max(1, Math.round(n * f)) : 0;
    const dur = Math.round((slow * Math.pow(fast / slow, f)) / 50) * 50;
    const motion = motionOn();
    const segs = this.shadowRoot.querySelectorAll(`.cond[data-i="${i}"] .lane[data-l="${lane}"] i`);
    const flash = c.colours.flash || "#FFFFFF";
    segs.forEach((s, j) => {
      const lit = colour && j < count ? colour : null;
      const run = lit && motion && v > 0;
      const key = `${lit}|${run ? dur : 0}`;
      if (s._key === key && !boot) return;
      s._key = key;
      s.style.setProperty("--c", lit || "transparent");
      s.style.setProperty("--head", lit ? `color-mix(in srgb, ${lit} 50%, ${flash})` : "");
      s.style.setProperty("--trail", lit ? `color-mix(in srgb, ${lit} 78%, ${flash})` : "");
      const anims = [];
      if (boot && lit) anims.push(`boot 1ms step-end ${i * 90 + j * 22}ms backwards`);
      if (run) {
        // outward: segment j flashes (j % wave) / wave of a cycle after segment 0; inward: the other way round
        const k = inward ? (wave - 1 - (j % wave)) : (j % wave);
        const d = -((wave - k) % wave) / wave * dur;
        anims.push(`flow ${dur}ms step-end ${d.toFixed(0)}ms infinite`);
      }
      s.style.setProperty("--anim", anims.length ? anims.join(", ") : "none");
    });
  }

  getCardSize() {
    return this._config ? this._config.nodes.length : 4;
  }
}

if (!customElements.get("lcars-topology")) customElements.define("lcars-topology", LcarsTopology);
