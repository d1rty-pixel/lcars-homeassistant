// LCARS media player: a Spotify (or any) media_player as two lightweight cards.
//
// custom:lcars-player  - now playing: cover art, track / artist / album / device, a segmented progress bar
//                        (tap to seek) with elapsed and remaining time, a segmented volume slider (drag, sent
//                        when the finger lifts, like lcars-transporter.js) and the output devices (Spotify
//                        Connect: the entity's source_list) as pills. Its own pillar of LCARS buttons holds
//                        the transport: Play/Pause, Back, Next, Shuffle, Repeat.
// custom:lcars-library - the media library from HA's media browser (media_player/browse_media): a pillar of
//                        category buttons (Playlists, Albums, ...) and as many whole rows as fit, paged with
//                        the Up/Down buttons. Tapping a row plays it (media_player.play_media); a row that can
//                        only be expanded (e.g. an artist) opens it, "Back" returns.
//
// Neither card scrolls. Lit progress segments flash white briefly like lcars-bar.js (off with the per-device
// motion switch, localStorage "lcars-motion" = "off"). Clicks play LCARdS' tap sound.
//
// Config (written by generator/build_dashboard.py):
//   type: custom:lcars-player
//   entity: media_player.spotify_x
//   pillar: {width, gap, ink, filler, blocks: [{colour, code}] x5}   # play, back, next, shuffle, repeat
//   segments: {progress: 40, volume: 20}
//   colours: {accent, text, value, dim, off, on, playing, paused, idle, active, source, art, ink}
//   blink: [ms, ...], off_fraction: 0.025, flash: "#FFFFFF", gap: 3
//   font: "Antonio, sans-serif"
//
//   type: custom:lcars-library
//   entity: media_player.spotify_x
//   categories: [{match: "current_user_playlists", label: "Playlists", colour, code,
//                 pinned: ["current_user_saved_tracks"]}]
//                                    # match: end of a root child's media_content_id or media_content_type;
//                                    # pinned: other root children listed first as one playable row each
//                                    # (e.g. Spotify's Liked songs, which isn't a playlist)
//   pillar: {width, gap, ink, filler, active, up: {colour, code}, down: {colour, code}}
//   row: 44, row_gap: 4              # px
//   colours: {text, dim, rows: [colour, ...], ink}
//   font: "Antonio, sans-serif"
const lcarsTapSound = () => {
  try { window.lcards.core.soundManager.play("card_tap"); } catch (e) { /* LCARdS not loaded: silent */ }
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
const motionOn = () => {
  try { return localStorage.getItem("lcars-motion") !== "off"; } catch (e) { return true; }
};
const mmss = (s) => {
  if (!isFinite(s) || s < 0) return "--:--";
  s = Math.floor(s);
  const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, p = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${p(m)}:${p(s % 60)}` : `${p(m)}:${p(s % 60)}`;
};
// Stable 4-digit number for a thing that only exists at runtime (a library row), like lcars-log's REF codes
const code4 = (s) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return String((h >>> 0) % 10000).padStart(4, "0");
};
// media_player supported_features bits
const F = {PAUSE: 1, SEEK: 2, VOLUME_SET: 4, PREVIOUS: 16, NEXT: 32, SELECT_SOURCE: 2048, PLAY: 16384,
           SHUFFLE: 32768, REPEAT: 262144};

class LcarsPlayer extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._vol = null;         // volume while it is being dragged
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    if (st === this._st) return;
    this._st = st;
    this._render();
  }

  connectedCallback() {
    clearInterval(this._timer);
    this._timer = setInterval(() => this._progress(), 1000);
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._fitArt());
      this._ro.observe(this.shadowRoot.querySelector(".info"));
    }
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _fitArt() {
    const info = this.shadowRoot.querySelector(".info");
    const r = info.getBoundingClientRect();
    info.style.gridTemplateColumns = `${Math.floor(Math.min(r.height, r.width * 0.45))}px minmax(0, 1fr)`;
  }

  _build() {
    const c = this._config, p = c.pillar, k = c.colours;
    const names = ["Play", "Back", "Next", "Shuffle", "Repeat"];
    const blocks = names.map((n, i) =>
      `<div class="blk" data-b="${n.toLowerCase()}" style="--c:${p.blocks[i].colour}">` +
      `<em>${esc(p.blocks[i].code)}</em><span>${n}</span></div>`).join("");
    const segs = (n, cls) => Array.from({length: n}, (_, j) => {
      const ms = (c.blink && c.blink[j % c.blink.length]) || 1000;
      return `<div class="seg ${cls}" data-j="${j}" style="--ms:${ms}ms"></div>`;
    }).join("");
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; font-family: ${c.font}; text-transform: uppercase;
                line-height: 1; grid-template-columns: ${p.width}px minmax(0, 1fr); }
        .pillar { display: grid; gap: ${p.gap}px; grid-template-rows: repeat(5, minmax(0, 1fr)) 14px; }
        .blk { position: relative; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 4px;
               background: var(--c); color: ${p.ink}; font-size: 17px; cursor: pointer; user-select: none;
               -webkit-user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk:active { filter: brightness(1.3); }
        .blk.na { background: ${k.off} !important; color: ${k.dim}; cursor: default; }
        .body { display: grid; min-height: 0; gap: clamp(8px, 1.6vh, 18px) 0;
                grid-template-rows: minmax(0, 1fr) auto auto auto; }
        /* the cover is square: as wide as the info area is high, at most 45 % of its width (_fitArt) */
        .info { display: grid; min-height: 0; gap: 0 clamp(14px, 1.6vw, 28px);
                grid-template-columns: 0 minmax(0, 1fr); }
        .art { min-height: 0; position: relative;
               background: ${k.off}; border-left: 10px solid ${k.art}; box-sizing: border-box; overflow: hidden; }
        .art img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
        .art span { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
                    color: ${k.dim}; font-size: 18px; letter-spacing: 2px; }
        .meta { display: grid; min-height: 0; align-content: center; gap: clamp(4px, 1vh, 12px) 0; overflow: hidden; }
        .lbl { color: ${k.dim}; font-size: clamp(12px, 1.5vh, 16px); letter-spacing: 1px; }
        .val { color: ${k.value}; font-weight: bold; font-size: var(--lcars-data-size, 24px); white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; padding-bottom: 2px; }
        .val.title { color: ${k.accent}; font-size: clamp(26px, 5vh, 56px); }
        .val.status { font-size: clamp(16px, 2.2vh, 24px); }
        .line { display: grid; align-items: center; gap: 0 14px; grid-template-columns: 110px minmax(0, 1fr) 110px; }
        .line .t { color: ${k.text}; font-weight: bold; font-size: clamp(16px, 2.4vh, 26px); }
        .line .t.r { text-align: right; }
        .segs { display: grid; gap: ${c.gap ?? 3}px; height: clamp(18px, 3vh, 30px); cursor: pointer;
                touch-action: none; user-select: none; -webkit-user-select: none; }
        .prog { grid-template-columns: repeat(${c.segments.progress}, minmax(0, 1fr)); }
        .vol { grid-template-columns: repeat(${c.segments.volume}, minmax(0, 1fr)); }
        .seg { background: ${k.off}; }
        .prog .seg.lit { background: ${k.accent}; }
        .vol .seg.lit { background: ${k.text}; }
        .seg.lit.anim { animation: blink var(--ms) step-end infinite; }
        .na .segs { cursor: default; }
        .srcs { display: flex; gap: 10px; overflow: hidden; height: clamp(28px, 4vh, 40px); }
        .src { flex: 0 1 auto; min-width: 0; display: flex; align-items: center; padding: 0 20px; border-radius: 40px;
               background: ${k.source}; color: ${k.ink}; font-size: 17px; white-space: nowrap; overflow: hidden;
               text-overflow: ellipsis; cursor: pointer; user-select: none; }
        .src.on { background: ${k.active}; }
        .src:active { filter: brightness(1.3); }
        .none { color: ${k.dim}; font-size: 17px; align-self: center; }
        @keyframes blink { 0% { background: ${k.accent}; }
                           ${Math.round((1 - (c.off_fraction ?? 0.025)) * 1000) / 10}%, 100% { background: ${c.flash ?? "#FFFFFF"}; } }
      </style>
      <div class="wrap">
        <div class="pillar">${blocks}<div style="background:${p.filler}"></div></div>
        <div class="body">
          <div class="info">
            <div class="art"><span>No visual</span></div>
            <div class="meta">
              <div><div class="lbl">Now playing</div><div class="val title" id="title">–</div></div>
              <div><div class="lbl">Artist</div><div class="val" id="artist">–</div></div>
              <div><div class="lbl">Album</div><div class="val" id="album">–</div></div>
              <div><div class="lbl">Status</div><div class="val status" id="status">–</div></div>
            </div>
          </div>
          <div class="line" id="pline"><div class="t" id="pos">--:--</div><div class="segs prog">${segs(c.segments.progress, "p")}</div><div class="t r" id="dur">--:--</div></div>
          <div class="line" id="vline"><div class="t">Volume</div><div class="segs vol">${segs(c.segments.volume, "v")}</div><div class="t r" id="volv">–</div></div>
          <div class="srcs" id="srcs"></div>
        </div>
      </div>`;
    const root = this.shadowRoot;
    root.querySelectorAll(".blk").forEach((el) => el.addEventListener("click", () => this._button(el)));
    const prog = root.querySelector(".prog");
    prog.addEventListener("click", (e) => {
      const st = this._st;
      if (!st || !(st.attributes.supported_features & F.SEEK) || !st.attributes.media_duration) return;
      const r = prog.getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      lcarsTapSound();
      this._call("media_seek", {seek_position: Math.round(f * st.attributes.media_duration)});
    });
    this._bindVolume(root.querySelector(".vol"));
    root.getElementById("srcs").addEventListener("click", (e) => {
      const el = e.target.closest(".src");
      if (!el || el.classList.contains("on")) return;
      lcarsTapSound();
      this._call("select_source", {source: el.dataset.s});
    });
  }

  _call(service, data = {}) {
    if (this._hass) this._hass.callService("media_player", service, {entity_id: this._config.entity, ...data});
  }

  _button(el) {
    const st = this._st;
    if (!st || el.classList.contains("na")) return;
    lcarsTapSound();
    const a = st.attributes;
    switch (el.dataset.b) {
      case "play": return this._call("media_play_pause");
      case "back": return this._call("media_previous_track");
      case "next": return this._call("media_next_track");
      case "shuffle": return this._call("shuffle_set", {shuffle: !a.shuffle});
      case "repeat": return this._call("repeat_set",
        {repeat: {off: "all", all: "one", one: "off"}[a.repeat] || "off"});
    }
  }

  _bindVolume(bar) {
    const valueAt = (e) => {
      const r = bar.getBoundingClientRect();
      return Math.round(Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * 100) / 100;
    };
    const can = () => this._st && (this._st.attributes.supported_features & F.VOLUME_SET) && this._st.state !== "off";
    bar.addEventListener("pointerdown", (e) => {
      if (!can()) return;
      bar.setPointerCapture(e.pointerId);
      this._vol = valueAt(e);
      this._showVolume(this._vol);
    });
    bar.addEventListener("pointermove", (e) => {
      if (this._vol === null) return;
      this._vol = valueAt(e);
      this._showVolume(this._vol);
    });
    bar.addEventListener("pointerup", () => {
      if (this._vol === null) return;
      const v = this._vol;
      this._vol = null;
      lcarsTapSound();
      this._call("volume_set", {volume_level: v});
    });
    bar.addEventListener("pointercancel", () => {
      this._vol = null;
      this._render();
    });
  }

  _render() {
    const c = this._config, k = c.colours, root = this.shadowRoot, st = this._st;
    const set = (id, text) => { root.getElementById(id).textContent = text; };
    const a = st ? st.attributes : {};
    const feat = a.supported_features || 0;
    const state = st ? st.state : "unavailable";
    const active = state === "playing" || state === "paused" || state === "buffering";
    set("title", !st ? "No signal" : active ? (a.media_title || "–") : "Standing by");
    set("artist", active ? (a.media_artist || a.media_series_title || "–") : "–");
    set("album", active ? (a.media_album_name || a.media_channel || "–") : "–");
    const statusText = !st ? `${c.entity} not found` :
      state === "playing" ? "Playing" : state === "paused" ? "Paused" : state === "buffering" ? "Buffering" :
      state === "unavailable" ? "Offline" : "Idle";
    const statusEl = root.getElementById("status");
    statusEl.textContent = statusText + (a.source ? ` · ${a.source}` : "");
    statusEl.style.color = state === "playing" ? k.playing : state === "paused" ? k.paused : k.idle;

    // cover art: HA proxies it (entity_picture is a relative /api/media_player_proxy URL with a token)
    const art = root.querySelector(".art");
    const pic = active ? a.entity_picture : null;
    if (pic !== this._pic) {
      this._pic = pic;
      art.innerHTML = pic ? `<img src="${esc(pic)}" alt="">` : "<span>No visual</span>";
    }

    // transport pillar: Play/Pause in its state colour, shuffle/repeat on/off like mode buttons
    const blk = (b) => root.querySelector(`.blk[data-b="${b}"]`);
    const can = (bit) => !!st && state !== "unavailable" && !!(feat & bit);
    const play = blk("play");
    play.querySelector("span").textContent = state === "playing" ? "Pause" : "Play";
    play.style.background = state === "playing" ? k.playing : "";
    play.classList.toggle("na", !can(F.PLAY | F.PAUSE));
    blk("back").classList.toggle("na", !can(F.PREVIOUS));
    blk("next").classList.toggle("na", !can(F.NEXT));
    const shuffle = blk("shuffle"), repeat = blk("repeat");
    shuffle.classList.toggle("na", !can(F.SHUFFLE));
    shuffle.style.background = a.shuffle ? k.on : k.off;
    shuffle.style.color = a.shuffle ? "" : k.dim;
    repeat.classList.toggle("na", !can(F.REPEAT));
    repeat.querySelector("span").textContent = a.repeat === "one" ? "Repeat 1" : "Repeat";
    repeat.style.background = a.repeat && a.repeat !== "off" ? k.on : k.off;
    repeat.style.color = a.repeat && a.repeat !== "off" ? "" : k.dim;

    root.getElementById("pline").classList.toggle("na", !can(F.SEEK));
    root.getElementById("vline").classList.toggle("na", !can(F.VOLUME_SET));
    if (this._vol === null) this._showVolume(a.volume_level);

    // output devices (Spotify Connect)
    const srcs = a.source_list || [];
    const key = JSON.stringify([srcs, a.source, can(F.SELECT_SOURCE)]);
    if (key !== this._srcKey) {
      this._srcKey = key;
      root.getElementById("srcs").innerHTML = !srcs.length || !can(F.SELECT_SOURCE)
        ? `<div class="none">No output devices${st ? " · open Spotify on a device" : ""}</div>`
        : srcs.map((s) => `<div class="src${s === a.source ? " on" : ""}" data-s="${esc(s)}">` +
                          `${esc(s)}${s === a.source ? " ◂" : ""}</div>`).join("");
    }
    this._progress();
  }

  _progress() {
    const c = this._config, root = this.shadowRoot, st = this._st;
    if (!root) return;
    const a = st ? st.attributes : {};
    const dur = a.media_duration;
    let pos = a.media_position;
    if (st && st.state === "playing" && isFinite(pos) && a.media_position_updated_at) {
      pos += (Date.now() - new Date(a.media_position_updated_at).getTime()) / 1000;
    }
    const known = st && isFinite(dur) && dur > 0 && isFinite(pos);
    if (known) pos = Math.min(pos, dur);
    root.getElementById("pos").textContent = known ? mmss(pos) : "--:--";
    root.getElementById("dur").textContent = known ? "−" + mmss(dur - pos) : "--:--";
    const n = c.segments.progress;
    const count = known ? Math.round((pos / dur) * n) : 0;
    const motion = motionOn() && st && st.state === "playing";
    root.querySelectorAll(".seg.p").forEach((seg) => {
      const lit = +seg.dataset.j < count;
      seg.classList.toggle("lit", lit);
      seg.classList.toggle("anim", lit && motion);
    });
  }

  _showVolume(v) {
    const root = this.shadowRoot, n = this._config.segments.volume;
    const ok = isFinite(v) && v !== null;
    const count = ok && v > 0 ? Math.max(1, Math.round(v * n)) : 0;
    root.querySelectorAll(".seg.v").forEach((seg) => seg.classList.toggle("lit", +seg.dataset.j < count));
    root.getElementById("volv").textContent = ok ? `${Math.round(v * 100)} %` : "–";
  }

  getCardSize() {
    return 8;
  }
}

class LcarsLibrary extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._cat = 0;
    this._page = 0;
    this._stack = [];          // expanded items (e.g. an artist) on top of the category
    this._items = null;
    this._root = null;         // the entity's browse root (children = categories)
    this._rows = 1;
    if (!this.shadowRoot) this._build();
  }

  set hass(hass) {
    const had = this._hass && this._hass.states[this._config.entity];
    this._hass = hass;
    if (!had && hass.states[this._config.entity]) this._load();
    if (!hass.states[this._config.entity]) this._message("Library offline · media player not found");
  }

  connectedCallback() {
    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._fit());
      this._ro.observe(this);
    }
  }

  disconnectedCallback() {
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  _build() {
    const c = this._config, p = c.pillar, k = c.colours;
    this.attachShadow({mode: "open"});
    const cats = c.categories.map((cat, i) =>
      `<div class="blk cat" data-i="${i}" style="--c:${cat.colour}"><em>${esc(cat.code)}</em><span></span></div>`).join("");
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        .wrap { display: grid; height: 100%; gap: 0 16px; font-family: ${c.font}; text-transform: uppercase;
                line-height: 1; grid-template-columns: minmax(0, 1fr) ${p.width}px; }
        .pillar { display: grid; gap: ${p.gap}px;
                  grid-template-rows: repeat(${c.categories.length}, minmax(0, 1fr)) minmax(0, 0.8fr) minmax(0, 0.8fr) 14px; }
        .blk { position: relative; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 4px;
               background: var(--c); color: ${p.ink}; font-size: 17px; cursor: pointer; user-select: none;
               -webkit-user-select: none; }
        .blk em { position: absolute; left: 6px; top: 3px; font-style: normal; font-size: 12px; }
        .blk:active { filter: brightness(1.3); }
        .blk.na { opacity: 0.35; cursor: default; }
        .list { display: grid; align-content: start; min-height: 0; overflow: hidden; gap: ${c.row_gap}px 0; }
        .row { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 0 14px; height: ${c.row}px;
               cursor: pointer; user-select: none; -webkit-user-select: none; }
        .row:active { filter: brightness(1.3); }
        .row b { display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 8px 3px; color: ${k.ink};
                 font-weight: normal; font-size: 13px; }
        .row span { display: flex; align-items: center; justify-content: flex-start; color: ${k.text}; font-weight: bold;
                    font-size: clamp(16px, 2.3vh, 24px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                    padding-right: 2px; }
        .row span i { font-style: normal; color: ${k.dim}; font-weight: normal; margin-right: 10px; }
        .row.head span { color: ${k.dim}; font-weight: normal; }
        .msg { color: ${k.dim}; font-size: 18px; padding: 8px 2px; }
      </style>
      <div class="wrap">
        <div class="list"></div>
        <div class="pillar">${cats}
          <div class="blk" data-nav="up" style="--c:${p.up.colour}"><em>${esc(p.up.code)}</em><span>Up</span></div>
          <div class="blk" data-nav="down" style="--c:${p.down.colour}"><em>${esc(p.down.code)}</em><span>Down</span></div>
          <div style="background:${p.filler}"></div>
        </div>
      </div>`;
    const root = this.shadowRoot;
    root.querySelectorAll(".blk.cat").forEach((el) => el.addEventListener("click", () => {
      lcarsTapSound();
      this._cat = +el.dataset.i;
      this._stack = [];
      this._page = 0;
      this._items = null;
      this._updateButtons();
      this._load();
    }));
    root.querySelectorAll(".blk[data-nav]").forEach((el) => el.addEventListener("click", () => {
      if (el.classList.contains("na")) return;
      lcarsTapSound();
      this._page += el.dataset.nav === "down" ? 1 : -1;
      this._draw();
    }));
    root.querySelector(".list").addEventListener("click", (e) => {
      const el = e.target.closest(".row");
      if (!el) return;
      lcarsTapSound();
      if (el.dataset.back) {
        this._stack.pop();
        this._page = 0;
        return this._load();
      }
      const item = this._items[+el.dataset.i];
      if (item.can_play) {
        this._hass.callService("media_player", "play_media", {entity_id: c.entity,
          media_content_id: item.media_content_id, media_content_type: item.media_content_type});
      } else if (item.can_expand) {
        this._stack.push(item);
        this._page = 0;
        this._load();
      }
    });
    this._updateButtons();
  }

  _updateButtons() {
    const c = this._config;
    this.shadowRoot.querySelectorAll(".blk.cat").forEach((el, i) => {
      const on = i === this._cat;
      el.style.background = on ? c.pillar.active : "";
      el.querySelector("span").textContent = c.categories[i].label + (on ? " ◂" : "");
    });
  }

  _message(text) {
    this._items = null;
    this.shadowRoot.querySelector(".list").innerHTML = `<div class="msg">${esc(text)}</div>`;
  }

  async _browse(id, type) {
    const msg = {type: "media_player/browse_media", entity_id: this._config.entity};
    if (id) Object.assign(msg, {media_content_id: id, media_content_type: type});
    return this._hass.callWS(msg);
  }

  async _load() {
    if (!this._hass || !this._hass.states[this._config.entity]) return;
    const cat = this._config.categories[this._cat];
    const token = (this._token = {});
    this._message("Accessing library…");
    try {
      if (!this._root) this._root = await this._browse();
      let node = this._stack[this._stack.length - 1];
      if (!node) {
        node = (this._root.children || []).find((ch) =>
          String(ch.media_content_id).endsWith(cat.match) || String(ch.media_content_type).endsWith(cat.match));
        if (!node) return this._message(`${cat.label} · not offered by this media player`);
      }
      const res = await this._browse(node.media_content_id, node.media_content_type);
      // pinned root children (top level of a category only): browsed for their own can_play, listed first
      const pinned = [];
      if (!this._stack.length) {
        for (const m of cat.pinned || []) {
          const p = (this._root.children || []).find((ch) =>
            String(ch.media_content_id).endsWith(m) || String(ch.media_content_type).endsWith(m));
          if (!p) continue;
          const pr = await this._browse(p.media_content_id, p.media_content_type);
          pinned.push({title: pr.title, media_content_id: pr.media_content_id,
                       media_content_type: pr.media_content_type, can_play: pr.can_play, can_expand: false,
                       pinned: true});
        }
      }
      if (token !== this._token) return;       // another category was picked meanwhile
      this._items = [...pinned, ...(res.children || [])];
      this._title = res.title;
      this._draw();
    } catch (e) {
      if (token === this._token) this._message("Library unavailable · " + (e.message || e.code || "error"));
    }
  }

  _fit() {
    const c = this._config, list = this.shadowRoot.querySelector(".list");
    const h = list.getBoundingClientRect().height;
    const rows = Math.max(1, Math.floor((h + c.row_gap) / (c.row + c.row_gap)));
    if (rows !== this._rows) {
      this._rows = rows;
      this._draw();
    }
  }

  _draw() {
    if (!this._items) return;
    const c = this._config, k = c.colours;
    const back = this._stack.length > 0;
    const per = Math.max(1, this._rows - (back ? 1 : 0));
    const pages = Math.max(1, Math.ceil(this._items.length / per));
    this._page = Math.min(Math.max(0, this._page), pages - 1);
    const start = this._page * per;
    const rows = [];
    if (back) {
      rows.push(`<div class="row head" data-back="1"><b style="background:${k.dim}">Back</b>` +
                `<span>${esc(this._title)} · ${this._page + 1}/${pages}</span></div>`);
    }
    this._items.slice(start, start + per).forEach((item, j) => {
      const i = start + j, colour = k.rows[i % k.rows.length];
      const sub = item.pinned ? "<i>♥</i>" : item.can_play ? "" : "<i>▸</i>";
      rows.push(`<div class="row" data-i="${i}"><b style="background:${colour}">` +
                `${String(i + 1).padStart(2, "0")}-${code4(item.media_content_id || item.title || "")}</b>` +
                `<span>${sub}${esc(item.title)}</span></div>`);
    });
    if (!this._items.length) rows.push(`<div class="msg">No entries</div>`);
    this.shadowRoot.querySelector(".list").innerHTML = rows.join("");
    const up = this.shadowRoot.querySelector('[data-nav="up"]');
    const down = this.shadowRoot.querySelector('[data-nav="down"]');
    up.classList.toggle("na", this._page <= 0);
    down.classList.toggle("na", this._page >= pages - 1);
  }

  getCardSize() {
    return 8;
  }
}

if (!customElements.get("lcars-player")) customElements.define("lcars-player", LcarsPlayer);
if (!customElements.get("lcars-library")) customElements.define("lcars-library", LcarsLibrary);
