// LCARS tank: a dosing bottle's fill level as a vertical stack of segments, as one lightweight card.
//
// Segments fill from the bottom like the liquid in the bottle; lit segments flash white briefly like
// lcars-bar.js (off with the per-device motion switch, localStorage "lcars-motion" = "off"). A scale next
// to the stack marks full, half and the low-level threshold (in the alarm colour); a pointer at the
// current level carries the value in ml and the percentage. Below the threshold the lit segments turn to
// the alarm colour. Tap: more-info of the fill level.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-tank
//   entity: number.x_fill_level        # fill level in ml
//   status: sensor.x_status            # optional: bottle_size_ml / low_level_ml attributes override the config
//   capacity: 500, low: 50             # ml
//   segments: 20
//   colour: "#FFCC99"
//   alarm: "#DD4444"
//   off: "rgba(...)"                   # inactive segment
//   text: "#9999FF", dim: "#666688"    # value and scale text
//   blink: [ms, ...], off_fraction: 0.025, flash: "#FFFFFF"
//   gap: 3
//   font: "Antonio, sans-serif"
class LcarsTank extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._key = null;
    if (!this.shadowRoot) {
      this.attachShadow({mode: "open"});
      this.addEventListener("click", () => this.dispatchEvent(new CustomEvent("hass-more-info", {
        bubbles: true, composed: true, detail: {entityId: this._config.entity}})));
    }
  }

  set hass(hass) {
    const c = this._config;
    const st = hass.states[c.entity];
    const status = c.status && hass.states[c.status];
    const key = (st ? st.last_updated : "-") + "|" + (status ? status.last_updated : "-");
    if (key !== this._key) {
      this._key = key;
      this._render(st, status);
    }
  }

  _render(st, status) {
    const c = this._config;
    const a = (status && status.attributes) || {};
    const cap = +a.bottle_size_ml || c.capacity;
    const low = a.low_level_ml != null ? +a.low_level_ml : c.low;
    const v = st ? parseFloat(st.state) : NaN;
    const f = isNaN(v) ? 0 : Math.min(1, Math.max(0, v / cap));
    const count = isNaN(v) || f <= 0 ? 0 : Math.max(1, Math.round(f * c.segments));   // nothing lit when empty
    const colour = !isNaN(v) && v < low ? c.alarm : c.colour;
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }

    // top segment first: the stack is drawn top to bottom, segment j counts from the bottom
    const segs = [];
    for (let j = c.segments - 1; j >= 0; j--) {
      if (j >= count) { segs.push(`<div style="background:${c.off}"></div>`); continue; }
      const ms = (c.blink && c.blink[j % c.blink.length]) || 1000;
      const anim = motion ? `animation:blink ${ms}ms step-end infinite` : "";
      segs.push(`<div style="--c:${colour};background:${colour};${anim}"></div>`);
    }
    const pct = (x) => `${Math.round(x * 1000) / 10}%`;
    const tick = (at, label, col) =>
      `<div class="tick" style="bottom:${pct(at)};color:${col};transform:translateY(${at >= 1 ? 100 : at <= 0 ? 0 : 50}%)"><i style="background:${col}"></i>${label}</div>`;
    const ticks = [tick(1, cap, c.dim), tick(0.5, cap / 2, c.dim)];   // empty needs no label, LOW sits near it
    if (low > 0 && low < cap) ticks.push(tick(low / cap, "LOW", c.alarm));
    const value = isNaN(v)
      ? `<div class="ptr"><b>–</b></div>`
      : `<div class="ptr"><b style="color:${colour === c.alarm ? c.alarm : c.text}">` +
        `${Math.round(v)}<small> ML</small></b><span>${Math.round(f * 100)} %</span></div>`;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; cursor: pointer; }
        .tank { display: grid; height: 100%; grid-template-columns: minmax(40px, 36%) 44px minmax(0, 1fr);
                gap: 0 8px; font-family: ${c.font}; text-transform: uppercase; line-height: 1; }
        .stack { display: grid; gap: ${c.gap ?? 3}px; grid-template-rows: repeat(${c.segments}, minmax(0, 1fr)); }
        .scale, .read { position: relative; }
        .tick { position: absolute; left: 0; right: 0; display: flex; align-items: center; gap: 4px;
                font-size: 13px; white-space: nowrap; }
        .tick i { flex: none; width: 10px; height: 2px; }
        /* centred on the level (set after layout), kept inside the card at full / empty */
        .ptr { position: absolute; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; gap: 3px;
               transform: translateY(50%); color: ${c.text}; font-weight: bold; white-space: nowrap; }
        .ptr b { font-size: var(--lcars-data-size, 24px); }
        .ptr small { font-size: 0.6em; }
        .ptr span { font-size: calc(var(--lcars-data-size, 24px) * 0.7); color: ${c.dim}; }
        @keyframes blink { 0% { background: var(--c); }
                           ${Math.round((1 - (c.off_fraction ?? 0.025)) * 1000) / 10}%, 100% { background: ${c.flash ?? "#FFFFFF"}; } }
      </style>
      <div class="tank">
        <div class="stack">${segs.join("")}</div>
        <div class="scale">${ticks.join("")}</div>
        <div class="read">${value}</div>
      </div>`;
    // keep the pointer inside the card near full / empty
    const ptr = this.shadowRoot.querySelector(".ptr");
    const read = this.shadowRoot.querySelector(".read");
    requestAnimationFrame(() => {
      if (!ptr || !read) return;
      const h = read.clientHeight, p = ptr.offsetHeight;
      const bottom = count / c.segments * h;
      const clamped = Math.min(Math.max(bottom, p / 2), h - p / 2);
      ptr.style.bottom = `${clamped}px`;
    });
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-tank")) customElements.define("lcars-tank", LcarsTank);
