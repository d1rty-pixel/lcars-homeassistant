// LCARS light phases: the light schedule over 24 h as one lightweight card.
//
// One smooth shape per phase in the phase's colour: it rises over the ramp-up, holds, and falls over the
// ramp-down, computed like aquarium_light_control's scheduler (phases in config order, first match wins,
// ramp from 0 up at the start and back to 0 at the end, uncovered time is off). A phase's height is its
// brightest channel relative to the brightest phase, at least `min_height` so dim phases stay visible.
// A "now" line marks the time, with a dot where it meets the curve. Re-renders every minute.
//
// Config (written by generator/build_dashboard.py from /config/aquarium_light_control.yaml):
//   type: custom:lcars-phases
//   phases: [{name, start, end, up, down, levels: {red: 45, ...}, colour}]   # start/end in minutes
//   min_height: 0.3
//   colours: {grid, text, now}
//   font: "Antonio, sans-serif"
class LcarsPhases extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._key = null;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    const now = new Date();
    const key = `${now.getHours()}:${now.getMinutes()}`;
    if (key !== this._key) {
      this._key = key;
      this._render(now);
    }
  }

  // the scheduler's state at minute m of the day: {phase, frac, dir} or null (off)
  _at(m) {
    for (const p of this._config.phases) {
      const s = p.start, e = p.end > p.start ? p.end : p.end + 1440;
      for (const off of [0, -1440, 1440]) {
        const n = m + off;
        if (s <= n && n < e) {
          const el = n - s, rem = e - n;
          if (p.up > 0 && el < p.up) return {phase: p, frac: el / p.up, dir: "up"};
          if (p.down > 0 && rem < p.down) return {phase: p, frac: rem / p.down, dir: "down"};
          return {phase: p, frac: 1, dir: null};
        }
      }
    }
    return null;
  }

  static _esc(s) {
    return String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
  }

  _render(now) {
    const c = this._config;
    const col = c.colours;
    const esc = LcarsPhases._esc;
    const peak = (p) => Math.max(0, ...Object.values(p.levels));
    const top = Math.max(1, ...c.phases.map(peak));
    const height = (p) => Math.max(c.min_height ?? 0.3, peak(p) / top);
    const ease = (f) => f * f * (3 - 2 * f);                  // smooth ramps
    const y = (v) => 100 - v * 92;                              // a little headroom above the tallest phase
    const states = Array.from({length: 1441}, (_, m) => this._at(m % 1440));

    // runs of minutes in the same phase, each drawn as one closed shape
    const runs = [];
    states.forEach((s, m) => {
      const last = runs[runs.length - 1];
      if (s && last && last.p === s.phase && last.end === m) last.end = m + 1;
      else if (s) runs.push({p: s.phase, start: m, end: m + 1});
    });
    const shapes = runs.map((r) => {
      const pts = [];
      for (let m = r.start; m < r.end; m++) pts.push(`${m},${y(height(r.p) * ease(states[m].frac)).toFixed(2)}`);
      pts.push(`${r.end},${y(0)}`);
      const line = `M${r.start},${y(0)} L${pts.join(" L")}`;
      return `<path d="${line} Z" fill="${r.p.colour}" fill-opacity="0.22" stroke="none"/>` +
             `<path d="${line}" fill="none" stroke="${r.p.colour}" stroke-width="2" ` +
             `vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`;
    });
    const labels = runs.filter((r) => r.end - r.start >= 150).map((r) =>
      `<span class="name" style="left:${((r.start + r.p.up) / 1440) * 100}%;top:${y(height(r.p))}%;` +
      `color:${r.p.colour}">${esc(r.p.name)}</span>`);
    const hours = [];
    for (let h = 0; h <= 24; h += 3) {
      hours.push(`<line x1="${h * 60}" x2="${h * 60}" y1="0" y2="100" stroke="${col.grid}" stroke-width="1" vector-effect="non-scaling-stroke"/>`);
    }
    const axis = Array.from({length: 9}, (_, k) => k * 3).map((h) =>
      `<span style="left:${(h / 24) * 100}%;transform:translateX(${h === 0 ? 0 : h === 24 ? -100 : -50}%)">${String(h).padStart(2, "0")}</span>`);

    const nm = now.getHours() * 60 + now.getMinutes();
    const s = states[nm];
    const dot = s ? `<i class="dot" style="left:${(nm / 1440) * 100}%;top:${y(height(s.phase) * ease(s.frac))}%;` +
                    `background:${s.phase.colour}"></i>` : "";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .card { display: grid; height: 100%; gap: 6px; grid-template-rows: minmax(0, 1fr) 14px;
                font-family: ${c.font}; text-transform: uppercase; line-height: 1; color: ${col.text}; }
        .plot, .axis { position: relative; }
        .plot svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
        .axis span { position: absolute; font-size: 12px; white-space: nowrap; }
        .name { position: absolute; transform: translate(4px, calc(-100% - 4px)); font-size: 14px; white-space: nowrap; }
        .now { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: ${col.now}; }
        .dot { position: absolute; width: 9px; height: 9px; border-radius: 50%; transform: translate(-50%, -50%);
               box-shadow: 0 0 0 2px #000; }
      </style>
      <div class="card">
        <div class="plot">
          <svg viewBox="0 0 1440 100" preserveAspectRatio="none">${hours.join("")}
            <line x1="0" x2="1440" y1="${y(0)}" y2="${y(0)}" stroke="${col.grid}" stroke-width="1" vector-effect="non-scaling-stroke"/>
            ${shapes.join("")}</svg>
          ${labels.join("")}
          <div class="now" style="left:${(nm / 1440) * 100}%"></div>${dot}
        </div>
        <div class="axis">${axis.join("")}</div>
      </div>`;
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get("lcars-phases")) customElements.define("lcars-phases", LcarsPhases);
