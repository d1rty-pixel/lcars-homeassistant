// LCARS radar: DWD precipitation radar (composite + nowcast) as one lightweight card.
//
// Frames come from the DWD WMS (maps.dwd.de, layer Radar_wn-product_1x1km_ger, EPSG:4326) as plain
// images for the card's own bounding box; borders are SVG paths precomputed by the generator (the WMS
// forbids custom styles). LCARS buttons play/pause and step through the frames: in the card's own pillar,
// or in a second card that shows only the buttons (e.g. embedded in a frame bar), linked by `group`: the
// buttons send commands, the map answers with its state (window events "lcars-radar").
// The per-device motion switch (localStorage "lcars-motion" = "off") stops autoplay; buttons still work.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-radar
//   center: [lat, lon], width_km: 160, home: [lat, lon]   # map centre, map width, home marker
//   layer: "dwd:Radar_wn-product_1x1km_ger"
//   past_min: 60, future_min: 90, step_min: 10, lag_min: 10   # frames relative to the latest analysis
//   frame_ms: 500, hold_ms: 1600                              # loop speed, pause on "now" and at the end
//   borders: [{d: "M lon -lat L ...", colour, width, opacity}]
//   pillar: {width, gap, blocks: [{colour, code}], filler, ink}   # blocks: play/pause, back, next, now
//   controls: "pillar"               # "pillar" (map + its pillar, default), "none" (map only), "row" (only the
//                                    # buttons, side by side); "none" and "row" cards talk through `group`
//   group: "ops"
//   colours: {past, now, future, text, dim, home}
//   font: "Antonio, sans-serif"
const WMS = "https://maps.dwd.de/geoserver/dwd/wms";
const EVENT = "lcars-radar";   // detail: {group, cmd: "toggle" | "step" | "now" | "query", d} or {group, playing}

// LCARdS' click sound (its sound manager honours the sound helpers), as on LCARdS buttons
const lcarsTapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};

class LcarsRadar extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) this._build();
  }

  set hass(hass) {
    this._hass = hass;
  }

  connectedCallback() {
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._resize());
      this._ro.observe(this);
    }
    if (this._mode !== "row") this._refreshTimer = setInterval(() => this._loadFrames(), 5 * 60e3);
    if (!this._onEvent) {
      this._onEvent = (e) => this._event(e.detail || {});
      window.addEventListener(EVENT, this._onEvent);
    }
    if (this._mode === "row") this._send({cmd: "query"});     // the map may already be running
    else this._broadcast();
  }

  disconnectedCallback() {
    clearInterval(this._refreshTimer);
    clearTimeout(this._playTimer);
    if (this._onEvent) { window.removeEventListener(EVENT, this._onEvent); this._onEvent = null; }
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _motion() {
    try { return localStorage.getItem("lcars-motion") !== "off"; } catch (e) { return true; }
  }

  _send(detail) {
    window.dispatchEvent(new CustomEvent(EVENT, {detail: {group: this._config.group, ...detail}}));
  }

  // the map tells its buttons whether it plays
  _broadcast() {
    if (this._mode === "none") this._send({playing: this._playing});
  }

  _event(e) {
    if (e.group !== this._config.group) return;
    if (this._mode === "row") {
      if ("playing" in e) { this._playing = e.playing; this._updateButtons(); }
      return;
    }
    if (this._mode !== "none") return;
    if (e.cmd === "toggle") this._toggle();
    else if (e.cmd === "step") this._step(e.d);
    else if (e.cmd === "now") this._jumpNow();
    else if (e.cmd === "query") this._broadcast();
  }

  _build() {
    const c = this._config;
    const p = c.pillar;
    const col = c.colours;
    this._mode = c.controls || "pillar";
    this.attachShadow({mode: "open"});
    const blocks = p.blocks.map((b, i) =>
      `<div class="blk" data-i="${i}" style="background:${b.colour}"><em>${b.code}</em><span></span></div>`).join("");
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; grid-template-columns: minmax(0, 1fr) ${p.width}px; gap: 0 16px;
                font-family: ${c.font}; text-transform: uppercase; }
        .map { position: relative; overflow: hidden; background: #000; min-height: 0; }
        .map img, .map svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        .imgs img { visibility: hidden; }
        .imgs img.on { visibility: visible; }
        .label { position: absolute; left: 10px; top: 8px; font-size: 20px; color: ${col.text}; text-shadow: 0 0 4px #000; }
        .label b { font-weight: normal; color: ${col.now}; }
        .frames { position: absolute; left: 10px; right: 10px; bottom: 8px; height: 8px; display: grid; gap: 3px; }
        .frames i { display: block; opacity: 0.35; }
        .frames i.on { opacity: 1; }
        .pillar { display: grid; gap: ${p.gap}px; grid-template-rows: repeat(${p.blocks.length}, minmax(0, 1fr)) 14px; }
        .blk { position: relative; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 4px;
               color: ${p.ink}; font-size: 17px; cursor: pointer; user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk:active { filter: brightness(1.3); }
        .wrap.c-none { grid-template-columns: minmax(0, 1fr); }
        .wrap.c-none .pillar, .wrap.c-row .map, .wrap.c-row .pillar > .fill { display: none; }
        .wrap.c-row { grid-template-columns: minmax(0, 1fr); }
        .wrap.c-row .pillar { grid-template-rows: minmax(0, 1fr); grid-template-columns: repeat(${p.blocks.length}, minmax(0, 1fr)); }
        .wrap.c-row .blk { font-size: 16px; padding: 0 8px 3px; }
        .wrap.c-row .blk em { font-size: 10px; top: 2px; }
      </style>
      <div class="wrap c-${this._mode}">
        <div class="map"><svg class="borders" preserveAspectRatio="none"></svg>
          <div class="label"></div><div class="frames"></div></div>
        <div class="pillar">${blocks}<div class="fill" style="background:${p.filler}"></div></div>
      </div>`;
    const actions = this._mode === "row"
      ? [() => this._send({cmd: "toggle"}), () => this._send({cmd: "step", d: -1}), () => this._send({cmd: "step", d: 1}),
         () => this._send({cmd: "now"})]
      : [() => this._toggle(), () => this._step(-1), () => this._step(1), () => this._jumpNow()];
    this.shadowRoot.querySelectorAll(".blk").forEach((el) =>
      el.addEventListener("click", () => { lcarsTapSound(); if (actions[+el.dataset.i]) actions[+el.dataset.i](); }));
    this._playing = this._motion();
    this._updateButtons();
  }

  _updateButtons() {
    const labels = [this._playing ? "Pause" : "Play", "Back", "Next", "Now"];
    this.shadowRoot.querySelectorAll(".blk span").forEach((el, i) => { el.textContent = labels[i] || ""; });
  }

  // bounding box for the map element's aspect ratio (EPSG:4326, degrees)
  _bbox(w, h) {
    const c = this._config;
    const [lat, lon] = c.center;
    const dlon = c.width_km / (111.32 * Math.cos(lat * Math.PI / 180));
    const dlat = (c.width_km * h / w) / 111.32;
    return {s: lat - dlat / 2, n: lat + dlat / 2, w: lon - dlon / 2, e: lon + dlon / 2};
  }

  _resize() {
    if (this._mode === "row") return;
    const map = this.shadowRoot.querySelector(".map");
    const w = Math.round(map.clientWidth / 10) * 10;
    const h = Math.round(map.clientHeight / 10) * 10;
    if (!w || !h || (w === this._w && h === this._h)) return;
    this._w = w;
    this._h = h;
    const c = this._config;
    const b = this._bbox(w, h);
    this._bb = b;
    const svg = this.shadowRoot.querySelector(".borders");
    svg.setAttribute("viewBox", `${b.w} ${-b.n} ${b.e - b.w} ${b.n - b.s}`);
    // The viewBox is in degrees and stretched to the map's km proportions (a degree of longitude is
    // cos(lat) as long as one of latitude), so x and y scale differently: strokes keep their pixel width
    // (non-scaling-stroke) and the home marker is sized per axis.
    const px = (b.e - b.w) / w, py = (b.n - b.s) / h;   // degrees per pixel
    const [hl, hn] = c.home;
    svg.innerHTML = c.borders.map((l) =>
      `<path d="${l.d}" fill="none" stroke="${l.colour}" stroke-opacity="${l.opacity}" stroke-width="${l.width}" ` +
      `vector-effect="non-scaling-stroke"/>`).join("") +
      `<path d="M${hn - 6 * px} ${-hl}h${12 * px}M${hn} ${-hl - 6 * py}v${12 * py}" stroke="${c.colours.home}" ` +
      `stroke-width="2" vector-effect="non-scaling-stroke"/>`;
    this._loadFrames();
  }

  _loadFrames() {
    if (!this._bb) return;
    const c = this._config;
    const step = c.step_min * 60e3;
    const t0 = Math.floor((Date.now() - c.lag_min * 60e3) / 300e3) * 300e3;   // latest analysis, 5-min grid
    const b = this._bb;
    const base = `${WMS}?service=WMS&version=1.3.0&request=GetMap&crs=EPSG:4326&format=image/png&transparent=true` +
      `&styles=&layers=${encodeURIComponent(c.layer)}&width=${this._w}&height=${this._h}` +
      `&bbox=${b.s.toFixed(4)},${b.w.toFixed(4)},${b.n.toFixed(4)},${b.e.toFixed(4)}`;
    // One <img> per frame, preloaded; showing a frame only switches which one is visible, and a frame
    // that hasn't loaded yet is skipped (the last one shown stays), so the map never flashes empty.
    // A new batch (every 5 min) loads behind the old one, which goes once a new frame is shown.
    const map = this.shadowRoot.querySelector(".map");
    const batch = document.createElement("div");
    batch.className = "imgs";
    map.insertBefore(batch, map.querySelector(".borders"));
    const frames = [];
    for (let t = t0 - c.past_min * 60e3; t <= t0 + c.future_min * 60e3; t += step) {
      const img = document.createElement("img");
      img.alt = "";
      const f = {t, rel: Math.round((t - t0) / 60e3), img, ready: false};
      img.onload = () => (img.decode ? img.decode() : Promise.resolve()).catch(() => {}).then(() => {
        f.ready = true;
        if (this._frames === frames && this._frames[this._index] === f) this._show();
      });
      img.src = `${base}&time=${new Date(t).toISOString().replace(".000", "")}`;
      batch.appendChild(img);
      frames.push(f);
    }
    this._frames = frames;
    this._now = this._frames.findIndex((f) => f.rel === 0);
    if (this._index == null || this._index >= this._frames.length) this._index = this._now;
    const bar = this.shadowRoot.querySelector(".frames");
    bar.style.gridTemplateColumns = `repeat(${this._frames.length}, minmax(0, 1fr))`;
    const col = c.colours;
    bar.innerHTML = this._frames.map((f) =>
      `<i style="background:${f.rel < 0 ? col.past : f.rel === 0 ? col.now : col.future}"></i>`).join("");
    this._show();
    if (this._playing) this._schedule();
  }

  _show() {
    const f = this._frames && this._frames[this._index];
    if (!f || !f.ready) return;
    if (this._shownImg !== f.img) {
      f.img.classList.add("on");
      if (this._shownImg) this._shownImg.classList.remove("on");
      this._shownImg = f.img;
      this.shadowRoot.querySelectorAll(".imgs").forEach((el) => { if (el !== f.img.parentNode) el.remove(); });
    }
    const hhmm = new Date(f.t).toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"});
    const rel = f.rel === 0 ? "<b>Now</b>" : f.rel < 0 ? `${f.rel} min` : `+${f.rel} min · forecast`;
    this.shadowRoot.querySelector(".label").innerHTML = `${hhmm} · ${rel}`;
    this.shadowRoot.querySelectorAll(".frames i").forEach((el, i) => el.classList.toggle("on", i === this._index));
  }

  _schedule() {
    clearTimeout(this._playTimer);
    const c = this._config;
    const hold = this._index === this._now || this._index === this._frames.length - 1;
    this._playTimer = setTimeout(() => {
      this._index = (this._index + 1) % this._frames.length;
      this._show();
      if (this._playing) this._schedule();
    }, hold ? c.hold_ms : c.frame_ms);
  }

  _toggle() {
    this._playing = !this._playing;
    this._updateButtons();
    this._broadcast();
    if (this._playing) this._schedule(); else clearTimeout(this._playTimer);
  }

  _jumpNow() {
    if (!this._frames) return;
    if (this._playing) this._toggle();
    this._index = this._now;
    this._show();
  }

  _step(d) {
    if (!this._frames) return;
    if (this._playing) this._toggle();
    this._index = (this._index + d + this._frames.length) % this._frames.length;
    this._show();
  }

  getCardSize() {
    return 4;
  }
}

if (!customElements.get("lcars-radar")) customElements.define("lcars-radar", LcarsRadar);
