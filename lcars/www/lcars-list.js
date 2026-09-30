// LCARS list: the entries of an entity attribute that holds a list of objects (e.g. parcels on their way,
// open tasks), one line each, as one lightweight card.
//
// A line is time, tag, text and a detail, like the device log's (lcars-log.js), coloured by one of the
// entry's fields. As many whole lines as fit are shown, in the attribute's order. A brightening wave runs
// down the lines (colour waterfall) and a changed line flashes once; both stop with the per-device motion
// switch (localStorage "lcars-motion" = "off"). The card re-renders when the entity changes.
//
// Config (written by the framework from a `list` component, lcars/components/data.py):
//   type: custom:lcars-list
//   entity: sensor.x, attribute: items          # a list of objects
//   id: id                                       # the field that tells entries apart (changed ones flash)
//   time: updated                                # an ISO time field: HH:MM today, else the date (optional)
//   tag: carrier                                 # a short field in the tag column (optional)
//   text: kind                                   # the main field
//   detail: [title, status]                      # fields joined with " · ", empty ones left out (optional)
//   labels: {value: shown text}                  # values of any field are shown as mapped
//   colour: kind, colours: {value: "#hex", default: "#hex"}   # the line's colour by that field's value
//   empty: "No entries", max_lines: 40
//   colours_ui: {time, bright}                   # time column; the colour the waterfall brightens to
//   cascade_ms: 5400, stagger_ms: 90
//   font: "Antonio, sans-serif", font_size: 15
// Fluid sizes, the same as the framework's (font() in lcars/engine/sizes.py): full size from REF_H viewport
// height up, shrinking linearly below it to a minimum share at MIN_H: fonts to 80 %.
const REF_H = 720, MIN_H = 400;
const fluid = (px, lo) => {
  const k = px * (1 - lo) / (REF_H - MIN_H), c = px * lo - k * MIN_H, n = (x) => +x.toFixed(3);
  return `clamp(${n(px * lo)}px, calc(${n(k * 100)}dvh ${c < 0 ? "-" : "+"} ${n(Math.abs(c))}px), ${px}px)`;
};
const fz = (px, lo = 0.8) => fluid(px, lo);

class LcarsList extends HTMLElement {
  setConfig(config) {
    if (!config.entity || !config.attribute || !config.text) throw new Error("lcars-list: entity, attribute and text");
    this._config = config;
    this._stamp = null;
    this._seen = null;               // entry key -> its line's content (changed ones flash)
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    const st = hass.states[this._config.entity];
    const stamp = st ? st.last_updated : "missing";
    if (stamp === this._stamp) return;
    this._stamp = stamp;
    const items = st && Array.isArray(st.attributes[this._config.attribute]) ? st.attributes[this._config.attribute] : [];
    this._render(items);
  }

  static _esc(s) {
    return String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
  }

  _show(value) {
    if (value == null || value === "") return "";
    const labels = this._config.labels || {};
    return String(value) in labels ? labels[String(value)] : String(value);
  }

  _time(value) {
    if (!value) return "";
    const d = new Date(value);
    if (isNaN(d)) return "";
    return d.toDateString() === new Date().toDateString()
      ? d.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"})
      : d.toLocaleDateString("en-GB", {day: "2-digit", month: "2-digit"});
  }

  _render(items) {
    const c = this._config;
    const esc = LcarsList._esc;
    const ui = c.colours_ui || {};
    const colours = c.colours || {};
    let motion = true;
    try { motion = localStorage.getItem("lcars-motion") !== "off"; } catch (e) { /* default on */ }
    const detailFields = Array.isArray(c.detail) ? c.detail : c.detail ? [c.detail] : [];
    const first = this._seen == null;
    const seen = new Map();
    const rows = items.slice(0, c.max_lines || 40).map((it, i) => {
      const colour = (c.colour && colours[String(it[c.colour])]) || colours.default || ui.time;
      const cells = [this._time(c.time && it[c.time]), this._show(c.tag && it[c.tag]), this._show(it[c.text]),
                     detailFields.map((f) => this._show(it[f])).filter((s) => s).join(" · ")];
      const id = c.id && it[c.id] != null ? String(it[c.id]) : String(i);
      const content = cells.join("|");
      seen.set(id, content);
      const fresh = !first && this._seen.get(id) !== content;
      const anim = !motion ? "" : fresh ? "animation: flash 1.2s step-end 3;" :
        `animation: wave ${c.cascade_ms || 5400}ms linear ${i * (c.stagger_ms || 90)}ms infinite;`;
      return `<div class="line" style="--c:${colour};${anim}"><span class="time">${esc(cells[0])}</span>` +
             `<span class="tag">${esc(cells[1])}</span><span class="text">${esc(cells[2])}</span>` +
             `<span class="detail">${esc(cells[3])}</span></div>`;
    });
    this._seen = seen;
    if (!rows.length) rows.push(`<div class="line" style="--c:${ui.time}"><span class="empty">${esc(c.empty || "No entries")}</span></div>`);
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .list { height: 100%; overflow: hidden; font-family: ${c.font}; text-transform: uppercase; line-height: 1.25;
                font-size: ${fz(c.font_size || 15)}; container-type: inline-size; }
        .line { display: grid; gap: 0 12px; color: var(--c);
                grid-template-columns: 3.4em 4.6em minmax(6em, 10em) minmax(0, 1fr); white-space: nowrap; }
        .time { color: ${ui.time}; }
        .text, .detail { overflow: hidden; text-overflow: ellipsis; }
        .detail { opacity: 0.8; }
        .empty { grid-column: 1 / -1; }
        /* narrow (phone): the detail matters more than the tag */
        @container (max-width: 560px) {
          .line { grid-template-columns: 3.4em minmax(5em, 7em) minmax(0, 1fr); }
          .tag { display: none; }
        }
        /* waterfall: each line brightens briefly, one after the other from the top */
        @keyframes wave { 0%, 12%, 100% { color: var(--c); } 5% { color: ${ui.bright}; } }
        @keyframes flash { 0% { color: ${ui.bright}; } 50% { color: var(--c); } }
      </style>
      <div class="list">${rows.join("")}</div>`;
    this._fit();
  }

  // hide lines that would be cut off at the bottom (only whole lines are shown); again on resize
  _fit() {
    const list = this.shadowRoot.querySelector(".list");
    if (!list) return;
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._fit());
      this._ro.observe(this);
    }
    const bottom = list.getBoundingClientRect().bottom;
    for (const line of list.children) {
      line.style.visibility = "";
      if (line.getBoundingClientRect().bottom > bottom + 0.5) line.style.visibility = "hidden";
    }
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get("lcars-list")) customElements.define("lcars-list", LcarsList);
