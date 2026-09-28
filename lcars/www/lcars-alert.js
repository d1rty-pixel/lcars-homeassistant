// LCARS alerts: while an alert's entity is in one of its states, the page frame turns the state's colour and
// a dialog shows its heading and text until someone acknowledges it (on any screen: the acknowledgement is
// kept in an HA helper, which every client sees change). The frame pulses while a blinking alert is
// unacknowledged, and stays in the alert's colour after that while the state lasts. A new alert (another
// state, or the same one again later) asks again. The first time a screen shows an alert it plays the
// state's sound through LCARdS' sound manager (its sound helpers apply), and "alert_clear" when the last
// alert ends.
//
// Frame: the framework tags the page frame's LCARdS cards (lcars/frame.py framed()); this card puts a small
// stylesheet into each tagged card's shadow root that overrides the shapes' fill (blocks .button-bg, elbows
// .elbow-bg; text in text-only cards) while the host carries data-lcars-alert. The pulse follows the wall
// clock, so every piece of the frame pulses in step. The per-device motion switch (localStorage
// "lcars-motion" = "off", see lcars-motion.js) stops it.
//
// Config (the framework writes it from the site's `alert`, lcars/frame.py alert_card()):
//   type: custom:lcars-alert
//   alerts:                          # priority in this order: the first active one colours the frame
//     - entity: sensor.x
//       states:
//         Critical: {heading: "'Red alert'", text: "'PUMP OFFLINE ' + a.minutes + ' MIN'",   # JS expressions
//                    colour: "#DD4444", blink: true, sound: alert_red}                         # (s, a, entity)
//   ack: input_text.lcars_alert_ack  # the acknowledged alerts (space-separated keys)
//   frame_tag: lcars-frame, text_tag: lcars-frame-text
//   code: "04-2117"                  # the dialog's LCARS number
//   ink: "#000", text_colour: "#FFCC99", details_colour: "#CC99CC", font: "Antonio, sans-serif"
//
// The card itself takes no space; the dialog is fixed over the page (in document.body, above HA's view).

// Fluid sizes, the same as the framework's (Len, font() in lcars/engine/sizes.py): full size from REF_H
// viewport height up, shrinking linearly below it to a minimum share at MIN_H: sizes to 60 % (sz), fonts to
// 80 % (fz).
const REF_H = 720, MIN_H = 400;
const fluid = (px, lo) => {
  const k = px * (1 - lo) / (REF_H - MIN_H), c = px * lo - k * MIN_H, n = (x) => +x.toFixed(3);
  return `clamp(${n(px * lo)}px, calc(${n(k * 100)}dvh ${c < 0 ? "-" : "+"} ${n(Math.abs(c))}px), ${px}px)`;
};
const fz = (px, lo = 0.8) => fluid(px, lo);
const sz = (px) => fluid(px, 0.6);

const PULSE_MS = 1600;
const LEAVES = /^(LCARDS-(BUTTON|ELBOW|SLIDER|CHART|DATA-GRID|MSD-CARD)|LCARS-(?!ALERT)[A-Z-]+|HA-[A-Z-]+|MWC-[A-Z-]+)$/;
const sounded = new Set();          // keys this page has played a sound for (across views)
let anyShown = false;               // an alert was active while this page was open (for "alert_clear")

const motionOff = () => { try { return localStorage.getItem("lcars-motion") === "off"; } catch (e) { return false; } };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const hash = (s) => {                // FNV-1a, 32 bit: short keys, so many fit into the helper's 255 chars
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193) >>> 0;
  return h.toString(36);
};
const expr = (code, st) => {
  try { return String(new Function("s", "a", "entity", `return (${code});`)(st.state, st.attributes || {}, st)); }
  catch (e) { return ""; }
};

const FRAME_CSS = `
:host([data-lcars-alert=on]) .button-bg, :host([data-lcars-alert=on]) .elbow-bg,
:host([data-lcars-alert=pulse]) .button-bg, :host([data-lcars-alert=pulse]) .elbow-bg { fill: var(--lcars-alert) !important; }
:host([data-lcars-alert=text]) text { fill: var(--lcars-alert) !important; }
:host([data-lcars-alert=pulse]) .button-bg, :host([data-lcars-alert=pulse]) .elbow-bg {
  animation: lcars-alert-pulse ${PULSE_MS}ms ease-in-out infinite; animation-delay: var(--lcars-alert-delay, 0ms); }
@keyframes lcars-alert-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`;

class LcarsAlert extends HTMLElement {
  setConfig(config) {
    if (!Array.isArray(config.alerts)) throw new Error("lcars-alert: alerts missing");
    this._config = config;
    this._frameKey = null;
  }

  getCardSize() { return 0; }

  connectedCallback() {
    this.style.display = "none";
    this._onClosed = () => { if (this._details) { this._details = false; this._render(); } };
    this._onResize = () => this._applyFrame(true);
    document.addEventListener("dialog-closed", this._onClosed);
    window.addEventListener("resize", this._onResize);
    // LCARdS renders its cards after this one: apply again while the view settles
    this._timers = [300, 1000, 2500, 5000].map((ms) => setTimeout(() => this._applyFrame(true), ms));
    if (this._hass) this._update();
  }

  disconnectedCallback() {
    document.removeEventListener("dialog-closed", this._onClosed);
    window.removeEventListener("resize", this._onResize);
    (this._timers || []).forEach(clearTimeout);
    if (this._overlay) { this._overlay.remove(); this._overlay = null; }
  }

  set hass(hass) {
    this._hass = hass;
    if (this.isConnected) this._update();
  }

  // ── state ─────────────────────────────────────────────────────────────────
  _active() {
    const out = [];
    this._config.alerts.forEach((al) => {
      const st = this._hass.states[al.entity];
      const s = st && al.states[st.state];
      if (!s) return;
      out.push({entity: al.entity, key: hash(`${al.entity}|${st.state}|${st.last_changed}`), colour: s.colour,
                blink: s.blink, sound: s.sound, heading: expr(s.heading, st), text: expr(s.text, st)});
    });
    return out;
  }

  _acked() {
    const st = this._hass.states[this._config.ack];
    const keys = new Set(st ? String(st.state).split(/\s+/).filter(Boolean) : []);
    (this._localAck || []).forEach((k) => keys.add(k));
    return keys;
  }

  _update() {
    const active = this._active(), acked = this._acked();
    this._alerts = active;
    this._pending = active.filter((a) => !acked.has(a.key));
    const top = active[0];
    this._frame = top ? {colour: top.colour, pulse: top.blink && !acked.has(top.key) && !motionOff()} : null;
    this._applyFrame(false);
    this._sound();
    this._render();
  }

  _sound() {
    const sm = window.lcards && window.lcards.core && window.lcards.core.soundManager;
    const fresh = this._pending.filter((a) => !sounded.has(a.key));
    fresh.forEach((a) => sounded.add(a.key));
    if (this._alerts.length) anyShown = true;
    if (!sm) return;
    if (fresh.length && fresh[0].sound) sm.play(fresh[0].sound);
    else if (!this._alerts.length && anyShown) { anyShown = false; sm.play("alert_clear"); }
  }

  _acknowledge() {
    const keys = new Set([...this._acked()].filter((k) => this._alerts.some((a) => a.key === k)));
    this._pending.forEach((a) => keys.add(a.key));
    this._localAck = [...keys];        // hides the dialog right away; the helper tells the other screens
    const value = [...keys].join(" ").slice(0, 255);
    if (this._hass.states[this._config.ack]) {
      this._hass.callService("input_text", "set_value", {entity_id: this._config.ack, value});
    }
    this._update();
  }

  _openDetails() {
    const a = this._pending[0] || this._alerts[0];
    if (!a) return;
    this._details = true;               // the dialog steps aside until HA's more-info closes
    this._render();
    this.dispatchEvent(new CustomEvent("hass-more-info", {detail: {entityId: a.entity}, bubbles: true, composed: true}));
  }

  // ── frame ─────────────────────────────────────────────────────────────────
  _viewRoot() {
    let n = this, found = null;
    while (n) {
      if (n.tagName === "HUI-VIEW" || n.tagName === "HUI-PANEL-VIEW") return n;
      if (n.tagName === "LCARDS-LAYOUT-VIEW") found = n;
      n = n.parentNode || n.host;
    }
    return found || this.getRootNode();
  }

  _tagged() {
    const {frame_tag: frameTag = "lcars-frame", text_tag: textTag = "lcars-frame-text"} = this._config;
    const out = [];
    const walk = (root) => {
      for (const el of root.querySelectorAll("*")) {
        const tags = el.config && Array.isArray(el.config.tags) ? el.config.tags : null;
        if (tags && (tags.includes(frameTag) || tags.includes(textTag))) {
          out.push([el, tags.includes(textTag)]);
        } else if (el.shadowRoot && !LEAVES.test(el.tagName)) {
          walk(el.shadowRoot);
        }
      }
    };
    const root = this._viewRoot();
    walk(root.shadowRoot || root);
    if (root.shadowRoot) walk(root);
    return out;
  }

  // Colours (or clears) the frame when the alert changed, or again (force) for cards rendered since
  _applyFrame(force) {
    const f = this._frame, key = f ? `${f.colour}|${f.pulse}` : "";
    if (!force && key === this._frameKey) return;
    if (force && !f && !this._frameKey) return;
    this._frameKey = key;
    const delay = `${-(Date.now() % PULSE_MS)}ms`;
    for (const [el, text] of this._tagged()) {
      if (!f) { el.removeAttribute("data-lcars-alert"); continue; }
      const root = el.shadowRoot;
      if (root && !root.querySelector("style[data-lcars-alert]")) {
        const style = document.createElement("style");
        style.setAttribute("data-lcars-alert", "");
        style.textContent = FRAME_CSS;
        root.appendChild(style);
      }
      const mode = text ? "text" : f.pulse ? "pulse" : "on";
      // a new delay would restart the pulse out of step: set it only where the pulse starts
      if (mode === "pulse" && el.getAttribute("data-lcars-alert") !== "pulse") el.style.setProperty("--lcars-alert-delay", delay);
      el.style.setProperty("--lcars-alert", f.colour);
      el.setAttribute("data-lcars-alert", mode);
    }
  }

  // ── dialog ────────────────────────────────────────────────────────────────
  _render() {
    const pending = this._pending || [];
    if (!pending.length || this._details) {
      if (this._overlay) this._overlay.style.display = "none";
      return;
    }
    if (!this._overlay) {
      this._overlay = document.createElement("div");
      this._overlay.attachShadow({mode: "open"});
      this._overlay.shadowRoot.addEventListener("click", (e) => {
        const b = e.target.closest("[data-act]");
        if (!b) return;
        const sm = window.lcards && window.lcards.core && window.lcards.core.soundManager;
        if (sm) sm.play("card_tap");
        if (b.dataset.act === "ack") this._acknowledge(); else this._openDetails();
      });
      document.body.appendChild(this._overlay);
      this._html = null;
    }
    this._overlay.style.display = "";
    const c = this._config, top = pending[0], col = top.colour;
    const pulse = pending.some((a) => a.blink) && !motionOff();
    const items = pending.map((a, i) => (pending.length > 1 || i > 0
      ? `<div class="item"><div class="h" style="color:${a.colour}">${esc(a.heading)}</div><div class="t">${esc(a.text)}</div></div>`
      : `<div class="item"><div class="t">${esc(a.text)}</div></div>`)).join("");
    const html = `
      <style>
        :host { all: initial; }
        .back { position: fixed; inset: 0; z-index: 6; display: flex; align-items: center; justify-content: center;
                background: rgba(0, 0, 0, 0.72); font-family: ${c.font || "Antonio, sans-serif"};
                padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
        .panel { --c: ${col}; width: min(${sz(760)}, 94vw); max-height: 92dvh; display: grid; background: #000;
                 grid-template-columns: ${sz(120)} 1fr; grid-template-rows: ${sz(44)} minmax(0, 1fr) ${sz(18)};
                 }
        .fr { background: var(--c); }
        .pulse .fr { animation: pulse ${PULSE_MS}ms ease-in-out infinite; animation-delay: ${-(Date.now() % PULSE_MS)}ms; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .tl { grid-area: 1 / 1; border-top-left-radius: ${sz(44)}; }
        .bl { grid-area: 3 / 1; border-bottom-left-radius: ${sz(18)}; }
        .pillar { grid-area: 2 / 1; position: relative; }
        .code { position: absolute; left: ${sz(8)}; top: ${sz(6)}; color: ${c.ink}; font-size: ${fz(12, 0.67)}; }
        .top, .bottom { display: flex; gap: ${sz(8)}; align-items: stretch; min-width: 0; }
        .top { grid-area: 1 / 2; }
        .bottom { grid-area: 3 / 2; }
        .top .a, .bottom .a { width: ${sz(32)}; }
        .top .b, .bottom .b { flex: 1; border-radius: 0 999px 999px 0; }
        .heading { color: var(--c); font-size: ${sz(44)}; line-height: 1; text-transform: uppercase; white-space: nowrap;
                   overflow: hidden; text-overflow: ellipsis; padding: 0 ${sz(6)}; }
        .body { grid-area: 2 / 2; position: relative; overflow: auto; padding: ${sz(22)} ${sz(8)} ${sz(18)} ${sz(22)};
                display: flex; flex-direction: column; gap: ${sz(18)}; }
        .body::before, .body::after { content: ""; position: absolute; left: 0; width: ${sz(24)}; height: ${sz(24)}; }
        .body::before { top: 0; background: radial-gradient(circle at 100% 100%, transparent ${sz(24)}, var(--c) calc(${sz(24)} + 0.5px)); }
        .body::after { bottom: 0; background: radial-gradient(circle at 100% 0%, transparent ${sz(24)}, var(--c) calc(${sz(24)} + 0.5px)); }
        .pulse .body::before, .pulse .body::after { animation: pulse ${PULSE_MS}ms ease-in-out infinite; animation-delay: ${-(Date.now() % PULSE_MS)}ms; }
        .item .h { font-size: ${fz(20)}; text-transform: uppercase; letter-spacing: 0.04em; }
        .item .t { color: ${c.text_colour}; font-size: ${fz(32)}; line-height: 1.15; text-transform: uppercase; }
        .buttons { display: flex; justify-content: flex-end; gap: ${sz(12)}; margin-top: auto; padding-top: ${sz(8)}; }
        .pill { border: 0; cursor: pointer; font: inherit; color: ${c.ink}; font-size: ${fz(20)}; text-transform: uppercase;
                height: ${sz(52)}; min-width: ${sz(170)}; border-radius: 999px; padding: 0 ${sz(22)};
                display: flex; align-items: flex-end; justify-content: flex-end; padding-bottom: ${sz(6)}; }
        .pill.details { background: ${c.details_colour}; }
        .pill.ack { background: var(--c); }
        @media (max-height: 519px) {
          .panel { width: 96vw; grid-template-columns: ${sz(70)} 1fr; }
          .code { display: none; }
        }
      </style>
      <div class="back" role="alertdialog" aria-modal="true" aria-label="${esc(top.heading)}">
        <div class="panel${pulse ? " pulse" : ""}">
          <div class="fr tl"></div>
          <div class="top"><div class="fr a"></div><div class="heading">${esc(top.heading)}</div><div class="fr b"></div></div>
          <div class="fr pillar"><span class="code">${esc(c.code || "")}</span></div>
          <div class="body">${items}
            <div class="buttons">
              <button class="pill details" data-act="details">Details</button>
              <button class="pill ack" data-act="ack">Acknowledge</button>
            </div>
          </div>
          <div class="fr bl"></div>
          <div class="bottom"><div class="fr a"></div><div class="fr b"></div></div>
        </div>
      </div>`;
    if (html.replace(/-?\d+ms/g, "") !== this._html) {      // the pulse offset alone is no reason to redraw
      this._html = html.replace(/-?\d+ms/g, "");
      this._overlay.shadowRoot.innerHTML = html;
    }
  }
}

if (!customElements.get("lcars-alert")) customElements.define("lcars-alert", LcarsAlert);
window.customCards = window.customCards || [];
window.customCards.push({type: "lcars-alert", name: "LCARS alert", description: "Alerts: frame colour and dialog"});
