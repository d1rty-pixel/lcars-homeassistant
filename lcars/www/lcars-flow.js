// LCARS flow: cards in columns that wrap into more rows when they don't fit side by side, each row led by
// its own copy of a label column (e.g. four channel frames of a device, 2 x 2 on a phone).
//
// The number of columns is the largest divisor of the card count (4 -> 4, 2, 1) whose columns are at
// least min_w wide, so the rows stay even. It follows the card's own width (ResizeObserver), not the
// device. Every row is at least row_min high; the rows share the height beyond that. The card's
// min-height is what its rows need, so a scrolling page grows by it (lcars/frame.py, scrolling).
//
// Config (the framework writes it from a `matrix` component, lcars/components/layout.py):
//   type: custom:lcars-flow
//   label: {card}                 # the label column, one instance per row
//   cards: [{card}, ...]
//   label_w: "<css length>"       # width of the label column
//   min_w: "<css length>"         # narrowest a column may get
//   row_min: "<css length>"       # lowest a row may get
//   gap: "<css length>"           # between the columns (and the label column)
//   row_gap: "<css length>"       # between the rows
class LcarsFlow extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._cols = 0;
    if (!this.shadowRoot) {
      this.attachShadow({mode: "open"});
      this._resize = new ResizeObserver(() => this._layout());
      this._onWindow = () => this._layout();
    }
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    for (const el of this._els || []) el.hass = hass;
  }

  connectedCallback() {
    this._resize && this._resize.observe(this);
    window.addEventListener("resize", this._onWindow);    // the lengths follow the viewport height too
  }

  disconnectedCallback() {
    this._resize && this._resize.disconnect();
    window.removeEventListener("resize", this._onWindow);
    document.documentElement.style.removeProperty("--lcars-flow-min");     // the next page has none
  }

  async _build() {
    const c = this._config;
    const helpers = await window.loadCardHelpers();
    const make = (cfg) => {
      const el = helpers.createCardElement(cfg);
      if (this._hass) el.hass = this._hass;
      return el;
    };
    this._items = c.cards.map(make);
    this._labels = c.cards.map(() => make(c.label));    // at most one row per card
    this._els = [...this._items, ...this._labels];
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .grid { display: grid; height: 100%; box-sizing: border-box; }
        .grid > * { min-width: 0; min-height: 0; }
        .probe { position: absolute; visibility: hidden; width: 0; height: 0; }
      </style>
      <div class="grid"></div><div class="probe"></div>`;
    this._grid = this.shadowRoot.querySelector(".grid");
    this._probe = this.shadowRoot.querySelector(".probe");
    this._cols = 0;
    this._layout();
  }

  // a CSS length (clamp(), dvh, ...) in px, as it resolves right now
  _px(css) {
    this._probe.style.width = css;
    return this._probe.getBoundingClientRect().width;
  }

  _layout() {
    if (!this._grid) return;
    const c = this._config, n = this._items.length;
    const labelW = this._px(c.label_w), minW = this._px(c.min_w), gap = this._px(c.gap);
    const width = this.getBoundingClientRect().width;
    let cols = 1;
    for (let d = n; d >= 1; d--) {
      if (n % d === 0 && labelW + d * (minW + gap) <= width + 0.5) { cols = d; break; }
    }
    const rows = n / cols;
    // min-height: the rows' share. The page's scrolling row (lcars/frame.py) grows by it through
    // --lcars-flow-min, so the sidebar next to it grows too (one flow card per page)
    this.style.minHeight = `calc(${rows} * ${c.row_min} + ${rows - 1} * ${c.row_gap})`;
    document.documentElement.style.setProperty("--lcars-flow-min", this.style.minHeight);
    if (cols === this._cols) return;
    this._cols = cols;
    const g = this._grid;
    g.style.gridTemplateColumns = `${c.label_w} repeat(${cols}, minmax(0, 1fr))`;
    g.style.gridTemplateRows = `repeat(${rows}, minmax(${c.row_min}, 1fr))`;
    g.style.gap = `${c.row_gap} ${c.gap}`;
    g.replaceChildren();
    for (let r = 0; r < rows; r++) {
      const label = this._labels[r];
      label.style.gridArea = `${r + 1} / 1`;
      g.appendChild(label);
      for (let k = 0; k < cols; k++) {
        const item = this._items[r * cols + k];
        item.style.gridArea = `${r + 1} / ${k + 2}`;
        g.appendChild(item);
      }
    }
  }

  getCardSize() {
    return 6;
  }
}

if (!customElements.get("lcars-flow")) customElements.define("lcars-flow", LcarsFlow);
