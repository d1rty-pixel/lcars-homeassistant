// LCARS segment bar: the waste page's countdown / time-window bars as one lightweight card.
//
// Replaces two LCARdS buttons per segment (a static base plus a blinking overlay) with plain divs:
// no colour transitions, and lit segments blink hard on/off through a CSS animation (steps, no fade).
// The per-device motion switch (localStorage "lcars-motion" = "off", see lcars-motion.js) stops it.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-bar
//   entity: sensor.x
//   mode: countdown          # days until the date in the state ('dd.mm.yyyy' or 'yyyy-mm-dd'),
//                            #   days_per_segment days per lit segment, at least one lit while >= 0
//         window             # 'HH:MM - HH:MM', one segment per hour, the hours of the window lit
//         level              # a number (state, or `attribute`) on a min..max scale
//         span               # one segment per hour, lit between the times of day in the ISO timestamps
//                            #   `start_attr` and `end_attr` (e.g. sun.sun next_rising / next_setting)
//   attribute: temperature   # level: read this attribute instead of the state
//   min: -10, max: 35        # level: scale
//   segments: 14
//   days_per_segment: 2
//   side: right | left       # segment 0 (next to the value / pillar) is on this side
//   colour: "#FFAA90"
//   off: "rgba(...)"         # inactive segment
//   blink: [ms, ms, ...]     # per segment: cycle length, random, fixed at build time
//   off_fraction: 0.025      # share of the cycle a lit segment briefly flashes
//   flash: "#FFFFFF"         # colour of that flash
//   gap: 3
class LcarsBar extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._key = null;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    const now = new Date();
    const key = (st ? st.last_updated : "-") + "|" + now.toDateString();
    if (key !== this._key) {
      this._key = key;
      this._render(st);
    }
  }

  static _days(state) {
    let d = null;
    let m = state.match(/(\d\d)\.(\d\d)\.(\d{4})/);
    if (m) d = new Date(+m[3], +m[2] - 1, +m[1]);
    else if ((m = state.match(/^(\d{4})-(\d\d)-(\d\d)/))) d = new Date(+m[1], +m[2] - 1, +m[3]);
    if (!d) return null;
    const t0 = new Date();
    t0.setHours(0, 0, 0, 0);
    return Math.round((d - t0) / 86400000);
  }

  _lit(st) {
    const c = this._config;
    const state = st ? String(st.state) : "";
    const lit = [];
    if (c.mode === "level") {
      const v = parseFloat(c.attribute ? (st && st.attributes[c.attribute]) : state);
      const f = isNaN(v) ? 0 : Math.min(1, Math.max(0, (v - c.min) / (c.max - c.min)));
      const count = isNaN(v) ? 0 : Math.max(1, Math.round(f * c.segments));
      for (let j = 0; j < c.segments; j++) lit.push(j < count);
    } else if (c.mode === "span") {
      const hour = (iso) => { const d = new Date(iso); return d.getHours() + d.getMinutes() / 60; };
      const a = st && st.attributes[c.start_attr];
      const b = st && st.attributes[c.end_attr];
      for (let h = 0; h < c.segments; h++) lit.push(!!a && !!b && h + 1 > hour(a) && h < hour(b));
    } else if (c.mode === "window") {
      const m = state.match(/(\d+):(\d+)\s*-\s*(\d+):(\d+)/);
      for (let h = 0; h < c.segments; h++) {
        lit.push(!!m && h < +m[3] + m[4] / 60 && h + 1 > +m[1] + m[2] / 60);
      }
    } else {
      const n = LcarsBar._days(state);
      const count = n == null || n < 0 ? 0 : Math.max(1, Math.ceil(n / (c.days_per_segment || 2)));
      for (let j = 0; j < c.segments; j++) lit.push(j < count);
    }
    return lit;
  }

  _render(st) {
    const c = this._config;
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const lit = this._lit(st);
    const segs = lit.map((on, j) => {
      if (!on) return `<div style="background:${c.off}"></div>`;
      const ms = (c.blink && c.blink[j % c.blink.length]) || 1000;
      // mostly in its colour, briefly flashing at the end of each cycle; step-end jumps, no fade
      const anim = motion ? `animation:blink ${ms}ms step-end infinite` : "";
      return `<div style="--c:${c.colour};background:${c.colour};${anim}"></div>`;
    });
    if (c.side === "right") segs.reverse();
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .bar { display: grid; height: 100%; gap: ${c.gap ?? 3}px;
               grid-template-columns: repeat(${c.segments}, minmax(0, 1fr)); }
        /* explicit keyframes: steps() with alternate would hold the start value in both directions */
        @keyframes blink { 0% { background: var(--c); }
                           ${Math.round((1 - (c.off_fraction ?? 0.025)) * 1000) / 10}%, 100% { background: ${c.flash ?? "#FFFFFF"}; } }
      </style>
      <div class="bar">${segs.join("")}</div>`;
  }

  getCardSize() {
    return 1;
  }
}

if (!customElements.get("lcars-bar")) customElements.define("lcars-bar", LcarsBar);
