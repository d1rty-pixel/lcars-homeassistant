// LCARS dashboard: per-device switch for all LCARdS animations (e.g. off on the kiosk tablet).
//
// - ?lcars_motion=off / ?lcars_motion=on in the URL stores the choice in this browser's localStorage,
//   so it can go into the Fully Kiosk start URL.
// - The "Motion" block in the sidebar navigates to the current view with ?lcars_motion=toggle (LCARdS
//   buttons support navigate, not fire-dom-event); that flips the choice and reloads without the param.
// - "off" pauses anime.js' global engine (window.lcards.animejs.engine), which drives every LCARdS
//   animation preset used here (blink, cascade-color). Nothing is animated while it is paused.
(() => {
  const KEY = "lcars-motion";
  const get = () => {
    try { return localStorage.getItem(KEY) === "off" ? "off" : "on"; } catch (e) { return "on"; }
  };
  const set = (v) => {
    try { localStorage.setItem(KEY, v); } catch (e) { /* private mode: stays "on" */ }
  };

  // Handle ?lcars_motion=on|off|toggle; returns true if the page should reload to apply a toggle
  const handleParam = () => {
    const url = new URL(location.href);
    const param = url.searchParams.get("lcars_motion");
    if (param === "off" || param === "on") set(param);
    if (param !== "toggle") return false;
    set(get() === "off" ? "on" : "off");
    url.searchParams.delete("lcars_motion");
    history.replaceState(history.state, "", url.pathname + url.search + url.hash);
    return true;
  };
  handleParam();

  // LCARdS loads via extra_module_url and may finish before or after this resource
  const apply = () => {
    const engine = window.lcards && window.lcards.animejs && window.lcards.animejs.engine;
    if (!engine) return false;
    if (get() === "off") engine.pause(); else engine.resume();
    return true;
  };
  if (!apply()) {
    const timer = setInterval(() => { if (apply()) clearInterval(timer); }, 100);
    setTimeout(() => clearInterval(timer), 30000);
  }

  window.addEventListener("location-changed", () => {
    if (handleParam()) location.reload();
  });
})();
