// LCARS day grid: the waste page's collection timeline as one lightweight card.
//
// Replaces ~200 LCARdS buttons (one per cell) with a single element and a plain CSS grid, which the
// Fully Kiosk tablet can render. The look matches the former LCARdS version: weekday header, one row
// per series, day numbers underneath, weekends dimmer, today lighter.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-day-grid
//   days: 28
//   rows: ["22px", "28px", ...]     # grid-template-rows: header, one per series, axis
//   gap: "4px 4px"
//   series: [{entity, colour, match: "attribute" | "state"}]
//     attribute: a pickup on day ds when entity.attributes[ds] exists ('yyyy-mm-dd' keys)
//     state:     a pickup on day ds when entity.state === ds
//   colours: {empty, weekend, today, text, text_weekend, text_today}
//   font: "Antonio, sans-serif", font_size: 15
class LcarsDayGrid extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._key = null;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
  }

  set hass(hass) {
    this._hass = hass;
    const today = LcarsDayGrid._iso(new Date());
    const key = today + "|" + this._config.series.map((s) => {
      const st = hass.states[s.entity];
      return st ? st.last_updated : "-";
    }).join("|");
    if (key !== this._key) {
      this._key = key;
      this._render();
    }
  }

  static _iso(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  _render() {
    const c = this._config;
    const col = c.colours;
    const days = [];
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    for (let k = 0; k < c.days; k++) {
      const d = new Date(t);
      d.setDate(t.getDate() + k);
      days.push({ds: LcarsDayGrid._iso(d), d, we: d.getDay() % 6 === 0, today: k === 0});
    }
    const textColour = (day) => (day.today ? col.text_today : day.we ? col.text_weekend : col.text);
    const cells = [];
    for (const day of days) {
      const wd = day.d.toLocaleDateString("en-GB", {weekday: "short"}).toUpperCase();
      cells.push(`<div class="lbl wd" style="color:${textColour(day)}">${wd}</div>`);
    }
    for (const s of c.series) {
      const st = this._hass.states[s.entity];
      for (const day of days) {
        const hit = st && (s.match === "state" ? st.state === day.ds : st.attributes[day.ds] !== undefined);
        const bg = hit ? s.colour : day.today ? col.today : day.we ? col.weekend : col.empty;
        cells.push(`<div class="cell" style="background:${bg}"></div>`);
      }
    }
    for (const day of days) {
      cells.push(`<div class="lbl num" style="color:${textColour(day)}">${day.d.getDate()}</div>`);
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .grid { display: grid; height: 100%; box-sizing: border-box;
                grid-template-columns: repeat(${c.days}, minmax(0, 1fr));
                grid-template-rows: ${c.rows.join(" ")}; gap: ${c.gap};
                font-family: ${c.font}; font-size: ${c.font_size}px; line-height: 1; }
        .lbl { display: flex; justify-content: center; overflow: hidden; white-space: nowrap; }
        .wd { align-items: flex-end; }
        .num { align-items: flex-start; }
      </style>
      <div class="grid">${cells.join("")}</div>`;
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-day-grid")) customElements.define("lcars-day-grid", LcarsDayGrid);
