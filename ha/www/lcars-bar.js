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
//         days               # one segment per weekday (Mon first), lit for the weekdays listed in
//                            #   `attribute` (0 = Monday, e.g. a dosing schedule's weekdays)
//         state              # a status: every segment lit in states[state] (e.g. {on: ice}), none if
//                            #   the state isn't listed; with `threshold`, a number above it is "on",
//                            #   else "off"
//   attribute: temperature   # level, countdown: read this attribute instead of the state; days: the list
//   min: -10, max: 35        # level: scale
//   states: {on: "#99CCFF"}  # state: colour per state; other modes: lit colour per state (else colour)
//   alarm: {below: 50, colour: "#DD4444"}   # level: lit colour while the value is below `below`
//   threshold: 3             # state: numeric state -> "on" / "off"
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
    const attr = c.attribute ? st && st.attributes[c.attribute] : undefined;
    if (c.mode === "days") {
      const days = Array.isArray(attr) ? attr : [];
      for (let j = 0; j < c.segments; j++) lit.push(days.includes(j));
    } else if (c.mode === "state") {
      let s = state;
      if (c.threshold != null) s = parseFloat(state) > c.threshold ? "on" : "off";
      const colour = c.states && c.states[s];
      for (let j = 0; j < c.segments; j++) lit.push(colour || false);
    } else if (c.mode === "level") {
      const v = parseFloat(c.attribute ? attr : state);
      const f = isNaN(v) ? 0 : Math.min(1, Math.max(0, (v - c.min) / (c.max - c.min)));
      const count = isNaN(v) || f <= 0 ? 0 : Math.max(1, Math.round(f * c.segments));   // nothing lit at min
      const colour = c.alarm && v < c.alarm.below ? c.alarm.colour : true;
      for (let j = 0; j < c.segments; j++) lit.push(j < count && colour);
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
      const n = LcarsBar._days(c.attribute ? String(attr ?? "") : state);
      const count = n == null || n < 0 ? 0 : Math.max(1, Math.ceil(n / (c.days_per_segment || 2)));
      for (let j = 0; j < c.segments; j++) lit.push(j < count);
    }
    // lit colour per state (e.g. a water-change countdown in the status colour)
    const byState = c.mode !== "state" && c.states && c.states[state];
    return byState ? lit.map((on) => on === true ? byState : on) : lit;
  }

  _render(st) {
    const c = this._config;
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const lit = this._lit(st);
    const segs = lit.map((on, j) => {
      if (!on) return `<div style="background:${c.off}"></div>`;
      const ms = (c.blink && c.blink[j % c.blink.length]) || 1000;
      const colour = typeof on === "string" ? on : c.colour;   // state mode: the state's colour
      // mostly in its colour, briefly flashing at the end of each cycle; step-end jumps, no fade
      const anim = motion ? `animation:blink ${ms}ms step-end infinite` : "";
      return `<div style="--c:${colour};background:${colour};${anim}"></div>`;
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
