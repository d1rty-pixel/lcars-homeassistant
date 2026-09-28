// LCARS rotate hint: a phone held upright (portrait) is too narrow for the page frame, so while it is, an LCARS
// panel covers the page and asks to turn the device. Pure CSS: the panel is always in the page and shown by
// the media query alone, so turning the device shows or hides it without a redraw. The icon turns once a
// cycle unless the per-device motion switch (localStorage "lcars-motion" = "off", see lcars-motion.js) stops it.
//
// Config (the framework adds it to every view, lcars/frame.py rotate_card()):
//   type: custom:lcars-rotate
//   query: "(orientation: portrait) and (max-width: 520px)"   # when the hint shows
//   code: "04-2117"                                           # the panel's LCARS number
//   frame_colour: "#FF9900", accent_colour: "#CC99CC", text_colour: "#FFCC99", ink: "#000"
//   font: "Antonio, sans-serif"
//
// The card itself takes no space; the panel is fixed over the page (in document.body, above HA's view).

const QUERY = "(orientation: portrait) and (max-width: 520px)";   // a phone (max-height 520 px) turned upright

const motionOff = () => { try { return localStorage.getItem("lcars-motion") === "off"; } catch (e) { return false; } };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

class LcarsRotate extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  getCardSize() { return 0; }

  set hass(hass) {}

  connectedCallback() {
    this.style.display = "none";
    if (!this._overlay) this._render();
  }

  disconnectedCallback() {
    if (this._overlay) { this._overlay.remove(); this._overlay = null; }
  }

  _render() {
    const c = this._config;
    const frame = c.frame_colour || "#FF9900", accent = c.accent_colour || "#CC99CC";
    this._overlay = document.createElement("div");
    this._overlay.attachShadow({mode: "open"});
    this._overlay.shadowRoot.innerHTML = `
      <style>
        :host { all: initial; }
        .back { display: none; }
        @media ${c.query || QUERY} {
          .back { position: fixed; inset: 0; z-index: 7; display: flex; align-items: center; justify-content: center;
                  background: #000; font-family: ${c.font || "Antonio, sans-serif"};
                  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
        }
        .panel { width: min(360px, 88vw); display: grid; grid-template-columns: 64px 1fr; grid-template-rows: 32px auto 16px; }
        .fr { background: ${frame}; }
        .tl { grid-area: 1 / 1; border-top-left-radius: 32px; }
        .bl { grid-area: 3 / 1; border-bottom-left-radius: 16px; }
        .pillar { grid-area: 2 / 1; position: relative; }
        .code { position: absolute; left: 8px; top: 6px; color: ${c.ink || "#000"}; font-size: 12px; }
        .top, .bottom { display: flex; gap: 6px; align-items: stretch; min-width: 0; }
        .top { grid-area: 1 / 2; }
        .bottom { grid-area: 3 / 2; }
        .top .a, .bottom .a { width: 24px; }
        .top .b, .bottom .b { flex: 1; border-radius: 0 999px 999px 0; }
        .heading { color: ${frame}; font-size: 32px; line-height: 1; text-transform: uppercase; white-space: nowrap;
                   padding: 0 6px; }
        .body { grid-area: 2 / 2; position: relative; padding: 28px 8px 24px 22px; display: flex; flex-direction: column;
                align-items: center; gap: 24px; }
        .body::before, .body::after { content: ""; position: absolute; left: 0; width: 20px; height: 20px; }
        .body::before { top: 0; background: radial-gradient(circle at 100% 100%, transparent 20px, ${frame} 20.5px); }
        .body::after { bottom: 0; background: radial-gradient(circle at 100% 0%, transparent 20px, ${frame} 20.5px); }
        .device { width: 56px; height: 96px; border: 5px solid ${accent}; border-radius: 12px; box-sizing: border-box;
                  animation: turn 3s ease-in-out infinite; }
        .still .device { animation: none; transform: rotate(-90deg); }
        @keyframes turn { 0%, 25% { transform: rotate(0deg); } 55%, 85% { transform: rotate(-90deg); } 100% { transform: rotate(0deg); } }
        .text { color: ${c.text_colour || "#FFCC99"}; font-size: 22px; line-height: 1.2; text-transform: uppercase;
                text-align: center; letter-spacing: 0.03em; }
      </style>
      <div class="back${motionOff() ? " still" : ""}" role="alert" aria-label="Rotate device">
        <div class="panel">
          <div class="fr tl"></div>
          <div class="top"><div class="fr a"></div><div class="heading">Rotate device</div><div class="fr b"></div></div>
          <div class="fr pillar"><span class="code">${esc(c.code || "")}</span></div>
          <div class="body">
            <div class="device"></div>
            <div class="text">This display requires<br>landscape orientation</div>
          </div>
          <div class="fr bl"></div>
          <div class="bottom"><div class="fr a"></div><div class="fr b"></div></div>
        </div>
      </div>`;
    document.body.appendChild(this._overlay);
  }
}

if (!customElements.get("lcars-rotate")) customElements.define("lcars-rotate", LcarsRotate);
window.customCards = window.customCards || [];
window.customCards.push({type: "lcars-rotate", name: "LCARS rotate hint", description: "Asks to turn a phone held upright"});
