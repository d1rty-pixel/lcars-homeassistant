// LCARS transporter controls: vertical sliders like the TNG transporter console, as one lightweight card.
//
// One column per channel: its value on top, a tall slot of segments lit from the bottom up to the value
// with a bright handle at the level, and a label block (auto number, name) below. Drag (or tap) a slot to
// set the value; it is sent when the finger lifts, so a drag is one command: number / input_number:
// set_value; light: its brightness in % (min/max 0..100; 0 turns it off). Lit
// segments flash white briefly like lcars-bar.js (off with the per-device motion switch, localStorage
// "lcars-motion" = "off").
//
// Config (written by the framework from a `sliders` component, lcars/components/data.py):
//   type: custom:lcars-transporter
//   channels: [{entity, label, colour, code}]   # number, input_number or light entities
//   min: 0, max: 100, step: 1
//   segments: 20
//   off: "rgba(...)"                 # inactive segment
//   slot: "rgba(...)"                # the slot behind the segments
//   handle: "#EEE4CC"
//   text: "#9999FF", dim: "#666688", ink: "#000000"   # value, scale, label text
//   label_h: "34px"                  # height of the label blocks
//   col_w: "clamp(70px, 7vw, 130px)" # width of a slot (narrower when the card is)
//   blink: [ms, ...], off_fraction: 0.025, flash: "#FFFFFF"
//   gap: 3
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

class LcarsTransporter extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._drag = null;       // {i, value} while a slot is being dragged
    this._values = [];
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    this._config.channels.forEach((ch, i) => {
      if (this._drag && this._drag.i === i) return;       // the finger wins until it lifts
      const v = LcarsTransporter._read(hass.states[ch.entity]);
      if (v !== this._values[i]) this._show(i, v);
    });
  }

  _build() {
    const c = this._config;
    const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const cols = c.channels.map((ch, i) => {
      const segs = [];
      for (let j = c.segments - 1; j >= 0; j--) {       // top first; j counts from the bottom
        const ms = (c.blink && c.blink[j % c.blink.length]) || 1000;
        segs.push(`<div class="seg" data-j="${j}" style="--ms:${ms}ms"></div>`);
      }
      return `
        <div class="col" style="--c:${ch.colour};--col:${i + 2}">
          <div class="val" id="v${i}">–</div>
          <div class="slot" data-i="${i}">
            <div class="segs">${segs.join("")}</div>
            <div class="handle" id="h${i}"></div>
          </div>
          <div class="blk"><em>${esc(ch.code || "")}</em><span>${esc(ch.label)}</span></div>
        </div>`;
    });
    const ticks = [1, 0.75, 0.5, 0.25, 0].map((f) =>
      `<div class="tick" style="bottom:${f * 100}%;transform:translateY(${f >= 1 ? 100 : f <= 0 ? 0 : 50}%)">` +
      `${Math.round(c.min + f * (c.max - c.min))}<i></i></div>`);
    this.shadowRoot.innerHTML = `
      <style>
        /* phones (PHONE_H in lcars/engine/sizes.py): no LCARS numbers, they are decoration and collide with labels */
        @media (max-height: 520px) { .blk em { display: none; } }
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; justify-content: center; gap: 0 clamp(12px, 2.6vw, 48px);
                padding: 0 14px; box-sizing: border-box;
                grid-template-columns: ${sz(36)} repeat(${c.channels.length}, minmax(0, ${c.col_w}));
                grid-template-rows: auto minmax(0, 1fr) ${c.label_h};
                font-family: ${c.font}; text-transform: uppercase; line-height: 1; }
        .col { display: contents; }
        .val, .slot, .blk { grid-column: var(--col); }
        .val { grid-row: 1; padding-bottom: ${sz(10)}; text-align: center; white-space: nowrap; color: ${c.text}; font-weight: bold;
               font-size: var(--lcars-data-size, 24px); }
        .slot { grid-row: 2; position: relative; background: ${c.slot}; border-radius: 12px; padding: 10px 8px;
                cursor: ns-resize; touch-action: none; user-select: none; -webkit-user-select: none; }
        .segs { display: grid; height: 100%; gap: ${len(c.gap ?? 3)};
                grid-template-rows: repeat(${c.segments}, minmax(0, 1fr)); }
        .seg { background: ${c.off}; }
        .seg.lit { background: var(--c); }
        .seg.lit.anim { animation: blink var(--ms) step-end infinite; }
        /* the handle spans the slot and a little beyond, centred on the level */
        .handle { position: absolute; left: -6px; right: -6px; height: 6px; bottom: 10px; border-radius: 3px;
                  background: ${c.handle}; transform: translateY(50%); pointer-events: none; }
        /* label at the bottom, number top-left: both fit a narrow slot */
        .blk { grid-row: 3; position: relative; display: flex; align-items: flex-end; justify-content: flex-end;
               margin-top: ${sz(8)}; padding: 0 ${sz(8)} 3px; background: var(--c); color: ${c.ink}; font-size: ${fz(17)};
               white-space: nowrap; overflow: hidden; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: ${fz(12, 0.67)}; }
        .scale { grid-row: 2; grid-column: 1; position: relative; margin: 10px 0; }
        .tick { position: absolute; right: 0; display: flex; align-items: center; gap: 4px; color: ${c.dim};
                font-size: ${fz(13)}; }
        .tick i { width: 10px; height: 2px; background: ${c.dim}; }
        @keyframes blink { 0% { background: var(--c); }
                           ${Math.round((1 - (c.off_fraction ?? 0.025)) * 1000) / 10}%, 100% { background: ${c.flash ?? "#FFFFFF"}; } }
      </style>
      <div class="wrap">
        <div class="scale">${ticks.join("")}</div>
        ${cols.join("")}
      </div>`;
    this._motion = motion;
    this.shadowRoot.querySelectorAll(".slot").forEach((slot) => this._bind(slot, +slot.dataset.i));
  }

  _bind(slot, i) {
    const c = this._config;
    const valueAt = (e) => {
      const segs = slot.querySelector(".segs").getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (segs.bottom - e.clientY) / segs.height));
      const step = c.step || 1;
      return Math.round((c.min + f * (c.max - c.min)) / step) * step;
    };
    slot.addEventListener("pointerdown", (e) => {
      slot.setPointerCapture(e.pointerId);
      this._drag = {i, value: valueAt(e)};
      this._show(i, this._drag.value);
    });
    slot.addEventListener("pointermove", (e) => {
      if (!this._drag || this._drag.i !== i) return;
      this._drag.value = valueAt(e);
      this._show(i, this._drag.value);
    });
    const end = (send) => () => {
      if (!this._drag || this._drag.i !== i) return;
      const st = this._hass && this._hass.states[c.channels[i].entity];
      const value = send ? this._drag.value : LcarsTransporter._read(st);   // cancelled: back to HA's
      this._drag = null;
      this._show(i, value);       // lit segments flash again
      if (send && this._hass) LcarsTransporter._write(this._hass, c.channels[i].entity, value);
    };
    slot.addEventListener("pointerup", end(true));
    slot.addEventListener("pointercancel", end(false));
  }

  // a channel's value: a number's state, a light's brightness in % (0 while off)
  static _read(st) {
    if (!st) return NaN;
    if (st.entity_id.startsWith("light.")) {
      return st.state === "on" ? Math.round((st.attributes.brightness ?? 255) / 2.55) : st.state === "off" ? 0 : NaN;
    }
    return parseFloat(st.state);
  }

  static _write(hass, entity, value) {
    const domain = entity.split(".")[0];
    if (domain === "light") {
      if (value <= 0) return hass.callService("light", "turn_off", {entity_id: entity});
      return hass.callService("light", "turn_on", {entity_id: entity, brightness_pct: Math.round(value)});
    }
    return hass.callService(domain, "set_value", {entity_id: entity, value});
  }

  _show(i, v) {
    const c = this._config;
    this._values[i] = v;
    const root = this.shadowRoot;
    const f = isNaN(v) ? 0 : Math.min(1, Math.max(0, (v - c.min) / (c.max - c.min)));
    const count = f <= 0 ? 0 : Math.max(1, Math.round(f * c.segments));     // nothing lit at min
    root.querySelectorAll(`.slot[data-i="${i}"] .seg`).forEach((seg) => {
      const lit = +seg.dataset.j < count;
      seg.classList.toggle("lit", lit);
      seg.classList.toggle("anim", lit && this._motion && !this._drag);
    });
    root.getElementById(`v${i}`).textContent = isNaN(v) ? "–" : `${Math.round(v)} %`;
    // the handle sits on the level within the segment area (the slot's padding is 10 px top and bottom)
    root.getElementById(`h${i}`).style.bottom = `calc(10px + ${f} * (100% - 20px))`;
  }

  getCardSize() {
    return 6;
  }
}

if (!customElements.get("lcars-transporter")) customElements.define("lcars-transporter", LcarsTransporter);
