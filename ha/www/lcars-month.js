// LCARS month: a month of several calendars as one lightweight card.
//
// A label column of week blocks (the ISO week, a code) next to a 6 x 7 day grid, Monday first: the day's
// number, and as many events as fit as bars in the calendar's colour ("+n" for the rest). Today is lit,
// days of the neighbouring months dimmed. On the right a legend: a numbered block per calendar in its
// colour, as the frame's pillar. Events come from HA's calendar REST API (calendar entities only expose
// their next event), refreshed every 10 min and when the month changes.
//
// Back / Today / Next: a second card with mode "controls" shows only those buttons (e.g. in a frame bar);
// it and the month card talk through window events ("lcars-month"), linked by `group`.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-month
//   calendars: [{entity, label, colour, code}]
//   titles: {"Biotonne": "Organic", ...}     # event titles to replace
//   weeks: {colours: [...], head: "#FF9900", code_prefix: "WK"}   # the week label column
//   label_w: 150, legend_w: 150, legend_filler: "#FFAA90", head: "28px", gap: 4
//   colours: {empty, weekend, today, other, text, text_weekend, text_today, dim, ink}
//   font: "Antonio, sans-serif"
//   mode: "controls", group: "calendar", controls: [{colour, code}] x3   # back, today, next
const EVENT = "lcars-month";
const DAY = 86400e3;
const tapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
const day0 = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
// ISO 8601 week number
const isoWeek = (d) => {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  return Math.ceil(((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / DAY + 1) / 7);
};

class LcarsMonth extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._offset = 0;          // months from the current one
    this._events = null;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    if (config.mode === "controls") this._buildControls();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config.mode === "controls") return;
    const stale = !this._fetchedAt || Date.now() - this._fetchedAt > 10 * 60e3;
    if (stale && !this._fetching) this._fetch();
  }

  connectedCallback() {
    if (!this._onEvent) {
      this._onEvent = (e) => this._event(e.detail || {});
      window.addEventListener(EVENT, this._onEvent);
    }
    if (this._config.mode !== "controls" && !this._ro) {
      this._ro = new ResizeObserver(() => this._fit());
      this._ro.observe(this);
    }
  }

  disconnectedCallback() {
    if (this._onEvent) { window.removeEventListener(EVENT, this._onEvent); this._onEvent = null; }
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _event(e) {
    if (e.group !== this._config.group || this._config.mode === "controls" || !e.cmd) return;
    this._offset = e.cmd === "today" ? 0 : this._offset + (e.cmd === "next" ? 1 : -1);
    this._events = null;
    this._render();
    this._fetch();
  }

  // Back / Today / Next as LCARS blocks side by side
  _buildControls() {
    const c = this._config;
    const names = [["Back", "back"], ["Today", "today"], ["Next", "next"]];
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .row { display: grid; height: 100%; gap: 6px; grid-template-columns: repeat(3, minmax(0, 1fr));
               font-family: ${c.font}; text-transform: uppercase; }
        .blk { position: relative; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 3px;
               color: ${(c.colours || {}).ink || "#000"}; font-size: 16px; cursor: pointer; user-select: none;
               -webkit-user-select: none; }
        .blk em { position: absolute; left: 6px; top: 2px; font-style: normal; font-size: 10px; }
        .blk:active { filter: brightness(1.3); }
      </style>
      <div class="row">${names.map(([label, cmd], i) =>
        `<div class="blk" data-cmd="${cmd}" style="background:${c.controls[i].colour}"><em>${esc(c.controls[i].code)}</em>` +
        `<span>${label}</span></div>`).join("")}</div>`;
    this.shadowRoot.querySelectorAll(".blk").forEach((el) => el.addEventListener("click", () => {
      tapSound();
      window.dispatchEvent(new CustomEvent(EVENT, {detail: {group: c.group, cmd: el.dataset.cmd}}));
    }));
  }

  // the 42 days shown: from the Monday on or before the 1st of the month
  _range() {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth() + this._offset, 1);
    const start = day0(first);
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    return {first, start, end: new Date(start.getTime() + 42 * DAY + 3600e3)};   // +1 h: DST
  }

  async _fetch() {
    if (!this._hass) return;
    const c = this._config;
    const {start, end} = this._range();
    const q = `?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`;
    const token = (this._token = {});
    this._fetching = true;
    try {
      const events = await Promise.all(c.calendars.map((cal) =>
        this._hass.callApi("GET", `calendars/${cal.entity}${q}`).catch(() => [])));
      if (token !== this._token) return;          // the month changed meanwhile
      this._events = events;
      this._fetchedAt = Date.now();
      this._render();
    } finally {
      this._fetching = false;
    }
  }

  // day index 0..41 -> [{title, colour, at}]
  _byDay(start) {
    const c = this._config;
    const days = Array.from({length: 42}, () => []);
    const t0 = start.getTime();
    (this._events || []).forEach((events, k) => {
      const cal = c.calendars[k];
      for (const ev of events) {
        const allDay = !!ev.start.date;
        const s = allDay ? new Date(ev.start.date + "T00:00:00") : new Date(ev.start.dateTime);
        const e = allDay ? new Date(ev.end.date + "T00:00:00") : new Date(ev.end.dateTime);
        const first = Math.max(0, Math.round((day0(s) - t0) / DAY));
        const lastMs = allDay ? e.getTime() - 1 : Math.max(s.getTime(), e.getTime() - 1);
        const last = Math.min(41, Math.round((day0(new Date(lastMs)) - t0) / DAY));
        for (let i = first; i <= last; i++) {
          const time = !allDay && i === first ? s.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"}) + " " : "";
          const summary = ev.summary || "?";
          days[i].push({title: time + ((c.titles || {})[summary] || summary), colour: cal.colour,
                        at: allDay ? s.getTime() - 1 : s.getTime()});
        }
      }
    });
    days.forEach((d) => d.sort((a, b) => a.at - b.at));
    return days;
  }

  // Event bars grow with the day cells: the text is about a quarter of a cell's height (15..22 px), a bar
  // 1.4 times that; as many bars as fit below the day's number. Where only one fits, it may take two lines
  _fit() {
    const cell = this.shadowRoot.querySelector(".cell");
    if (!cell) return;
    const h = cell.getBoundingClientRect().height;
    const font = Math.round(Math.min(22, Math.max(15, h / 4.4)));
    const bar = Math.round(font * 1.4), num = font + 4;
    const fits = Math.max(1, Math.floor((h - num - 8) / (bar + 3)));
    const two = fits === 1 && h - num - 8 >= font * 2.5;   // room for a single event on two lines
    this.style.setProperty("--ev-font", `${font}px`);
    this.style.setProperty("--ev-bar", `${bar}px`);
    this.style.setProperty("--ev-num", `${num}px`);
    if (fits !== this._fits || two !== this._two) {
      this._fits = fits;
      this._two = two;
      this._render();
    }
  }

  _render() {
    const c = this._config, col = c.colours, wk = c.weeks;
    const {first, start} = this._range();
    const days = this._byDay(start);
    const today = day0(new Date()).getTime();
    const fits = this._fits || 3;
    const heads = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) =>
      `<div class="head" style="color:${i > 4 ? col.text_weekend : col.text}">${d}</div>`).join("");
    const month = first.toLocaleDateString("en-GB", {month: "short", year: "numeric"});
    const cells = [];
    for (let w = 0; w < 6; w++) {
      const monday = new Date(start.getTime() + w * 7 * DAY + 3600e3);
      const wcol = wk.colours[w % wk.colours.length];
      cells.push(`<div class="blk" style="background:${wcol}"><em>${esc(wk.codes[w])}</em>` +
                 `<span>${wk.prefix || "WK"} ${isoWeek(monday)}</span></div>`);
      for (let d = 0; d < 7; d++) {
        const i = w * 7 + d;
        const date = day0(new Date(start.getTime() + i * DAY + 3600e3));
        const isToday = date.getTime() === today, other = date.getMonth() !== first.getMonth(), we = d > 4;
        const evs = days[i];
        const shown = evs.length > fits ? fits - 1 : evs.length;
        const bars = evs.slice(0, shown).map((e) =>
          `<i style="background:${e.colour}">${esc(e.title)}</i>`).join("") +
          (evs.length > shown ? `<u>+${evs.length - shown}</u>` : "");
        const bg = isToday ? col.today : other ? col.other : we ? col.weekend : col.empty;
        const num = isToday ? col.text_today : other ? col.dim : we ? col.text_weekend : col.text;
        cells.push(`<div class="cell${this._two ? " one" : ""}" style="background:${bg}"><b style="color:${num}">` +
                   `${date.getDate()}</b>${bars}</div>`);
      }
    }
    const legend = c.calendars.map((cal) =>
      `<div class="blk" style="background:${cal.colour}"><em>${esc(cal.code)}</em><span>${esc(cal.label)}</span></div>`)
      .join("") + `<div style="background:${c.legend_filler}"></div>`;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; grid-template-columns: minmax(0, 1fr) ${c.legend_w}px;
                font-family: ${c.font}; text-transform: uppercase; line-height: 1; }
        .grid { display: grid; min-height: 0; gap: ${c.gap}px;
                grid-template-columns: ${c.label_w}px repeat(7, minmax(0, 1fr));
                grid-template-rows: ${c.head} repeat(6, minmax(0, 1fr)); }
        .legend { display: grid; min-height: 0; gap: ${c.gap}px;
                  grid-template-rows: repeat(${c.calendars.length}, ${c.legend_row || c.head}) minmax(0, 1fr); }
        .head { display: flex; align-items: flex-end; justify-content: center; font-size: 15px; padding-bottom: 2px; }
        .blk { position: relative; display: flex; align-items: center; justify-content: flex-end; padding: 0 8px;
               color: ${col.ink}; font-size: 17px; overflow: hidden; white-space: nowrap; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk span { overflow: hidden; text-overflow: ellipsis; }
        /* legend: the label at the bottom, clear of the code at the top, so long names fit */
        .legend .blk { font-size: 15px; align-items: flex-end; padding-bottom: 3px; }
        .cell { display: flex; flex-direction: column; gap: 3px; min-width: 0; min-height: 0; overflow: hidden;
                padding: 4px 5px; box-sizing: border-box; }
        .cell b { font-weight: normal; font-size: var(--ev-num, 18px); height: var(--ev-num, 18px); flex: none; }
        .cell i { display: block; flex: none; height: var(--ev-bar, 20px); line-height: var(--ev-bar, 20px);
                  padding: 0 6px; font-style: normal; font-size: var(--ev-font, 14px); color: ${col.ink};
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .cell u { text-decoration: none; font-size: var(--ev-font, 14px); color: ${col.text}; }
        .cell.one i { height: auto; max-height: calc(var(--ev-font, 14px) * 2.5); line-height: 1.15; padding: 2px 6px;
                      white-space: normal; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
      </style>
      <div class="wrap">
        <div class="grid"><div class="blk" style="background:${wk.head}"><span>${esc(month)}</span></div>${heads}${cells.join("")}</div>
        <div class="legend">${legend}</div>
      </div>`;
    if (!this._fits) requestAnimationFrame(() => this._fit());
  }

  getCardSize() {
    return 8;
  }
}

if (!customElements.get("lcars-month")) customElements.define("lcars-month", LcarsMonth);
