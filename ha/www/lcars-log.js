// LCARS device log: recent events of a device's entities from HA's logbook, as one lightweight card.
//
// Newest first, one event per line (time, tag, text, a descriptive detail, a reference code), coloured by
// severity. As many whole lines as fit are shown; below 700 px the reference code is left out. The reference code (REF xxxx-nn · SEQ nnnn) is derived
// from the event's time and tag, so it looks random but stays put between refreshes. A brightening wave runs down the lines like the header's number columns (colour waterfall) and a
// new line flashes once; both stop with the per-device motion switch (localStorage "lcars-motion" = "off").
//
// Events are derived from state changes (logbook/<start>?entity=a,b,...), refetched every `refresh_s`:
//   - an entity going `unavailable` and back within `flap_s` is one "flap" line; longer is an "error"
//     line when it goes and an "ok" line when it returns
//   - rules map an entity's new state to text, level and detail: {entity, tag,
//     states: {state: [text, level, detail]}, default: [text or null (= the state), level, detail]}; a state
//     missing from `states` with no `default` is skipped
//   - `burst: true` (e.g. raw BLE notification codes): consecutive events within `burst_s` collapse into one
//     line listing the distinct values and the count
//   - details for availability lines: `details: {flap, offline, online}`, `{d}` = the duration
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-log
//   sources: [{entity, tag, states, default, burst, details}]
//   hours: 24, refresh_s: 60, flap_s: 60, burst_s: 60, max_lines: 40
//   levels: {info: "#9999FF", ok: ..., warn: ..., flap: ..., error: ..., ble: ...}
//   colours: {time, bright}          # time column; the colour the waterfall brightens to
//   cascade_ms: 5400, stagger_ms: 90
//   font: "Antonio, sans-serif", font_size: 15
class LcarsLog extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._lines = null;
    this._seen = null;               // keys of the lines already shown (new ones flash)
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    this._hass = hass;
    const c = this._config;
    if (!this._fetching && (!this._fetchedAt || Date.now() - this._fetchedAt > (c.refresh_s || 60) * 1000)) {
      this._fetch();
    }
  }

  async _fetch() {
    const c = this._config;
    this._fetching = true;
    try {
      const start = new Date(Date.now() - (c.hours || 24) * 3600e3).toISOString();
      const ids = c.sources.map((s) => s.entity).join(",");
      const entries = await this._hass.callApi("GET", `logbook/${encodeURIComponent(start)}?entity=${ids}`);
      this._fetchedAt = Date.now();
      this._render(this._events(entries || []));
    } catch (e) {
      this._fetchedAt = Date.now();  // try again next refresh
    } finally {
      this._fetching = false;
    }
  }

  // logbook entries (oldest first) -> lines {t, tag, text, level}, newest first
  _events(entries) {
    const c = this._config;
    const bySource = Object.fromEntries(c.sources.map((s) => [s.entity, s]));
    const lines = [];
    const gone = {};                 // entity -> time it went unavailable
    const bursts = {};               // entity -> the open burst line
    const flapMs = (c.flap_s || 60) * 1000, burstMs = (c.burst_s || 60) * 1000;
    for (const e of entries) {
      const src = bySource[e.entity_id];
      if (!src || e.state == null) continue;
      const t = new Date(e.when).getTime();
      const state = String(e.state);
      if (state === "unavailable" || state === "unknown") {
        if (!(e.entity_id in gone)) gone[e.entity_id] = t;
        continue;
      }
      if (e.entity_id in gone) {
        const since = gone[e.entity_id];
        delete gone[e.entity_id];
        const s = Math.round((t - since) / 1000);
        const det = (k) => ((src.details || {})[k] || "").replace("{d}", LcarsLog._dur(s));
        if (t - since <= flapMs) {
          lines.push({t, tag: src.tag, text: `Flap · back in ${s} s`, level: "flap", detail: det("flap")});
        } else {
          lines.push({t: since, tag: src.tag, text: "Offline", level: "error", detail: det("offline")});
          lines.push({t, tag: src.tag, text: `Online · after ${LcarsLog._dur(s)}`, level: "ok", detail: det("online")});
        }
        if (!src.burst) continue;    // the state it came back with is not news
      }
      if (src.burst) {
        const open = bursts[e.entity_id];
        if (open && t - open.last <= burstMs) {
          open.last = t;
          open.count += 1;
          if (!open.values.includes(state)) open.values.push(state);
          open.text = `${open.values.slice(0, 4).join(" ")}${open.values.length > 4 ? " …" : ""} ×${open.count}`;
          continue;
        }
        const line = {t, tag: src.tag, text: state, level: (src.default || [null, "ble"])[1],
                      detail: (src.default || [])[2] || "", last: t, count: 1, values: [state]};
        bursts[e.entity_id] = line;
        lines.push(line);
        continue;
      }
      const rule = (src.states && src.states[state]) || src.default;
      if (!rule) continue;
      lines.push({t, tag: src.tag, text: rule[0] == null ? state : rule[0], level: rule[1], detail: rule[2] || ""});
    }
    // still gone: offline since then (or flapping, if it just went)
    for (const [entity, since] of Object.entries(gone)) {
      const recent = Date.now() - since <= flapMs;
      lines.push({t: since, tag: bySource[entity].tag, text: "Offline", level: recent ? "flap" : "error",
                  detail: ((bySource[entity].details || {}).offline || "").replace("{d}", "")});
    }
    lines.sort((a, b) => b.t - a.t);
    return lines.slice(0, c.max_lines || 40);
  }

  static _dur(s) {
    if (s < 90) return `${s} s`;
    if (s < 5400) return `${Math.round(s / 60)} min`;
    return `${Math.round(s / 3600)} h`;
  }

  // stable pseudo-random reference code for an event: "REF 4A7F-22 · SEQ 0412"
  static _ref(l) {
    let h = 2166136261;
    for (const ch of `${l.t}|${l.tag}`) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
    const hex = (h & 0xffff).toString(16).toUpperCase().padStart(4, "0");
    return `REF ${hex}-${String((h >>> 16) % 100).padStart(2, "0")} · SEQ ${String((h >>> 8) % 10000).padStart(4, "0")}`;
  }

  static _esc(s) {
    return String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
  }

  _render(lines) {
    const c = this._config;
    const esc = LcarsLog._esc;
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const today = new Date().toDateString();
    const key = (l) => `${l.t}|${l.tag}|${l.text}`;
    const first = this._seen == null;
    const seen = new Set(lines.map(key));
    const rows = lines.map((l, i) => {
      const d = new Date(l.t);
      const hms = d.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
      const day = d.toDateString() === today ? "" :
        `<em>${d.toLocaleDateString("en-GB", {day: "2-digit", month: "2-digit"})}</em>`;
      const colour = c.levels[l.level] || c.levels.info;
      const fresh = !first && !this._seen.has(key(l));
      const anim = !motion ? "" : fresh ? "animation: flash 1.2s step-end 3;" :
        `animation: wave ${c.cascade_ms}ms linear ${i * c.stagger_ms}ms infinite;`;
      return `<div class="line" style="--c:${colour};${anim}"><span class="time">${day}${hms}</span>` +
             `<span class="tag">${esc(l.tag)}</span><span class="text">${esc(l.text)}</span>` +
             `<span class="detail">${esc(l.detail || "")}</span><span class="ref">${LcarsLog._ref(l)}</span></div>`;
    });
    this._seen = seen;
    if (!rows.length) rows.push(`<div class="line" style="--c:${c.colours.time}">No events in the last ${c.hours || 24} h</div>`);
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .log { height: 100%; overflow: hidden; font-family: ${c.font}; text-transform: uppercase; line-height: 1.25;
               font-size: ${c.font_size || 15}px; }
        .line { display: grid; gap: 0 12px; color: var(--c);
                grid-template-columns: 7.2em 4.6em minmax(6em, 9em) minmax(0, 1fr) 10.5em;
                white-space: nowrap; }
        .time { color: ${c.colours.time}; }
        .time em { font-style: normal; margin-right: 6px; opacity: 0.7; }
        .text, .detail { overflow: hidden; text-overflow: ellipsis; }
        .detail { opacity: 0.72; }
        .ref { color: ${c.colours.time}; text-align: right; }
        /* narrow (tablet): the descriptive detail matters more than the reference code */
        .log { container-type: inline-size; }
        @container (max-width: 700px) {
          .line { grid-template-columns: 5em 4em minmax(5em, 7em) minmax(0, 1fr); }
          .ref { display: none; }
        }
        /* waterfall: each line brightens briefly, one after the other from the top */
        @keyframes wave { 0%, 12%, 100% { color: var(--c); } 5% { color: ${c.colours.bright}; } }
        @keyframes flash { 0% { color: ${c.colours.bright}; } 50% { color: var(--c); } }
      </style>
      <div class="log">${rows.join("")}</div>`;
    this._fit();
  }

  // hide lines that would be cut off at the bottom (only whole lines are shown); again on resize
  _fit() {
    const log = this.shadowRoot.querySelector(".log");
    if (!log) return;
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._fit());
      this._ro.observe(this);
    }
    const bottom = log.getBoundingClientRect().bottom;
    for (const line of log.children) {
      line.style.visibility = "";
      if (line.getBoundingClientRect().bottom > bottom + 0.5) line.style.visibility = "hidden";
    }
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get("lcars-log")) customElements.define("lcars-log", LcarsLog);
