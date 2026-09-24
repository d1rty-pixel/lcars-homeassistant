// LCARS week: upcoming events of several calendars over the next days, as one lightweight card.
//
// Styled like the waste page's collection timeline: a label block per calendar (the frame's pillar),
// a column per day with weekday and date, and each day with events filled in the calendar's colour with
// the event title. Only calendars with events in the window get a row (at most max_rows, soonest first).
// Calendar entities only expose their next event, so events come from HA's calendar REST API. Before
// each fetch (on load, then every 10 min) the card asks HA to refresh the calendars
// (homeassistant.update_entity): HA's Google calendar sync otherwise lags behind new events.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-week
//   days: 7
//   calendars: [{entity, label, colour, code}]
//   titles: {"Biotonne": "Organic", ...}   # event titles to replace (the waste calendars' German names)
//   max_rows: 5
//   label_w: 150                     # pillar width (px)
//   side: left | right               # which side the label pillar is on
//   pillar: "#8899FF"                # frame colour: header piece and filler below the rows
//   head: "28px", row: "30px", gap: 4
//   colours: {empty, weekend, today, text, text_weekend, text_today, ink}
//   font: "Antonio, sans-serif"
class LcarsWeek extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._events = null;
    this._fetchedDay = null;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    this._hass = hass;
    const today = new Date().toDateString();
    const stale = !this._fetchedAt || Date.now() - this._fetchedAt > 10 * 60e3 || this._fetchedDay !== today;
    if (stale && !this._fetching) this._fetch(today);
  }

  static _day0(offset = 0) {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + offset);
    return d;
  }

  async _fetch(today) {
    const c = this._config;
    this._fetching = true;
    const start = LcarsWeek._day0();
    const end = LcarsWeek._day0(c.days);
    const q = `?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`;
    try {
      try {
        await this._hass.callService("homeassistant", "update_entity",
                                     {entity_id: c.calendars.map((cal) => cal.entity)});
      } catch (e) { /* not allowed or failed: use what HA has */ }
      this._events = await Promise.all(c.calendars.map((cal) =>
        this._hass.callApi("GET", `calendars/${cal.entity}${q}`).catch(() => [])));
      this._fetchedAt = Date.now();
      this._fetchedDay = today;
      this._render();
    } finally {
      this._fetching = false;
    }
  }

  // day index (0..days-1) -> events on that day, for one calendar's event list
  _byDay(events) {
    const c = this._config;
    const days = Array.from({length: c.days}, () => []);
    const t0 = LcarsWeek._day0().getTime();
    for (const ev of events) {
      const allDay = !!ev.start.date;
      const s = allDay ? new Date(ev.start.date + "T00:00:00") : new Date(ev.start.dateTime);
      const e = allDay ? new Date(ev.end.date + "T00:00:00") : new Date(ev.end.dateTime);
      const first = Math.max(0, Math.floor((new Date(s).setHours(0, 0, 0, 0) - t0) / 86400e3));
      const lastMs = allDay ? e.getTime() - 1 : Math.max(s.getTime(), e.getTime() - 1);
      const last = Math.min(c.days - 1, Math.floor((new Date(lastMs).setHours(0, 0, 0, 0) - t0) / 86400e3));
      for (let i = first; i <= last; i++) {
        const time = !allDay && i === first ? s.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"}) + " " : "";
        const summary = ev.summary || "?";
        days[i].push({title: time + ((c.titles || {})[summary] || summary), at: s.getTime()});
      }
    }
    days.forEach((d) => d.sort((a, b) => a.at - b.at));
    return days;
  }

  static _esc(s) {
    return String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
  }

  _render() {
    const c = this._config;
    const col = c.colours;
    const esc = LcarsWeek._esc;
    const days = Array.from({length: c.days}, (_, k) => {
      const d = LcarsWeek._day0(k);
      return {d, we: d.getDay() % 6 === 0, today: k === 0};
    });
    const rows = c.calendars
      .map((cal, i) => ({cal, days: this._byDay(this._events[i] || [])}))
      .filter((r) => r.days.some((d) => d.length))
      .map((r) => ({...r, first: Math.min(...r.days.flat().map((e) => e.at))}))
      .sort((a, b) => a.first - b.first)
      .slice(0, c.max_rows);

    // one grid row: the pillar cell and the day cells, pillar on the configured side
    const right = c.side === "right";
    const cells = [];
    const line = (pillarCell, dayCells) => cells.push(...(right ? [...dayCells, pillarCell] : [pillarCell, ...dayCells]));
    const tc = (day) => (day.today ? col.text_today : day.we ? col.text_weekend : col.text);
    line(`<div class="blk" style="background:${c.pillar}"></div>`, days.map((day) => {
      const wd = day.d.toLocaleDateString("en-GB", {weekday: "short"}).toUpperCase();
      return `<div class="head" style="color:${tc(day)}">${wd} ${day.d.getDate()}</div>`;
    }));
    for (const r of rows) {
      const dayCells = [];
      r.days.forEach((evs, k) => {
        const day = days[k];
        if (!evs.length) {
          dayCells.push(`<div class="cell" style="background:${day.today ? col.today : day.we ? col.weekend : col.empty}"></div>`);
        } else {
          const more = evs.length > 1 ? ` +${evs.length - 1}` : "";
          dayCells.push(`<div class="cell ev" style="background:${r.cal.colour}" title="${esc(evs.map((e) => e.title).join("\n"))}">` +
                        `<span>${esc(evs[0].title)}</span><b>${more}</b></div>`);
        }
      });
      line(`<div class="blk" style="background:${r.cal.colour}"><em>${esc(r.cal.code)}</em>` +
           `<span>${esc(r.cal.label)}</span></div>`, dayCells);
    }
    if (!rows.length) {
      line(`<div class="blk" style="background:${c.pillar}"></div>`,
           [`<div class="none" style="grid-column: span ${c.days}">No events in the next ${c.days} days</div>`]);
    }
    line(`<div class="blk" style="background:${c.pillar}"></div>`, Array.from({length: c.days}, () => "<div></div>"));
    const n = rows.length || 1;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .grid { display: grid; height: 100%; gap: ${c.gap}px ${c.gap}px;
                grid-template-columns: ${right ? `repeat(${c.days}, minmax(0, 1fr)) ${c.label_w}px`
                                                : `${c.label_w}px repeat(${c.days}, minmax(0, 1fr))`};
                grid-template-rows: ${c.head} repeat(${n}, ${c.row}) minmax(0, 1fr);
                font-family: ${c.font}; text-transform: uppercase; line-height: 1; }
        .head { display: flex; align-items: flex-end; justify-content: center; font-size: 15px; white-space: nowrap; }
        .blk { position: relative; display: flex; align-items: center; justify-content: flex-end;
               padding: 0 8px; color: ${col.ink}; font-size: 17px; overflow: hidden; white-space: nowrap; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .cell { display: flex; align-items: center; min-width: 0; padding: 0 6px; overflow: hidden;
                color: ${col.ink}; font-size: 14px; white-space: nowrap; }
        .cell span { overflow: hidden; text-overflow: ellipsis; flex: 1 1 auto; min-width: 0; }
        .cell b { flex: none; padding-left: 4px; }
        .none { display: flex; align-items: center; padding-left: 12px; color: ${col.text_weekend}; font-size: 15px; }
      </style>
      <div class="grid">${cells.join("")}</div>`;
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-week")) customElements.define("lcars-week", LcarsWeek);
