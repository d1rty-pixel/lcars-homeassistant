// Demo mode for shot.js: runs in the page before HA's frontend and answers everything a dashboard asks HA
// for with made-up data (window.__lcarsDemoData from demo-data.js): the dashboard's configuration, the
// states, statistics, history, forecasts, calendars, the logbook and the media browser. Service calls are
// answered locally and never reach HA, so screenshots neither show nor change the real installation.
//
// Injected by shot.js as: (demo-data.js) + (this file) + __lcarsDemoMock(<dashboard config>, <extra ids>,
// <DEMO_SET>)
window.__lcarsDemoMock = (dashboard, extraIds, set) => {
  const data = window.__lcarsDemoData(Date.now());
  // DEMO_SET: states to change for a shot, e.g. {"binary_sensor.water_leak": "on"}
  for (const [id, state] of Object.entries(set || {})) data.states[id] = {...data.states[id], state};
  // entities the dashboard uses that the demo data doesn't define (e.g. the header's number columns)
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (const id of extraIds) {
    if (!data.states[id] && !/^[a-z_]+\.(lcards|lcars)_/.test(id)) data.states[id] = {state: String(Math.round(rnd() * 5000) / 10), attributes: {}};
  }
  const now = Date.now() / 1000;
  const compressed = () => Object.fromEntries(Object.entries(data.states).map(([id, s]) =>
    [id, {s: s.state, a: s.attributes || {}, c: "demo", lc: now - 600, lu: now - 60}]));
  const full = () => Object.entries(data.states).map(([id, s]) => ({
    entity_id: id, state: s.state, attributes: s.attributes || {}, context: {id: "demo"},
    last_changed: new Date((now - 600) * 1000).toISOString(), last_updated: new Date((now - 60) * 1000).toISOString()}));

  // ── WebSocket: answer the demo's message types, pass the rest (auth, panels, themes, resources) ──
  const Real = window.WebSocket;
  const KEEP = /^[a-z_]+\.(lcards|lcars)_/;
  const LANGUAGE = {language: "en", number_format: "language", time_format: "24", date_format: "language",
                    first_weekday: "monday"};
  class DemoSocket extends EventTarget {
    constructor(url, protocols) {
      super();
      this._ws = new Real(url, protocols);
      this.url = url;
      for (const t of ["open", "close", "error"]) {
        this._ws.addEventListener(t, (e) => this._emit(t, e));
      }
      this._ws.addEventListener("message", (e) => this._incoming(e.data));
    }
    get readyState() { return this._ws.readyState; }
    get protocol() { return this._ws.protocol; }
    get bufferedAmount() { return this._ws.bufferedAmount; }
    set binaryType(v) { this._ws.binaryType = v; }
    get binaryType() { return this._ws.binaryType; }
    close(...a) { this._ws.close(...a); }
    _emit(type, orig) {
      const e = type === "message" ? new MessageEvent("message", {data: orig})
        : type === "close" ? new CloseEvent("close", {code: orig.code, reason: orig.reason, wasClean: orig.wasClean})
        : new Event(type);
      this.dispatchEvent(e);
      const h = this["on" + type];
      if (typeof h === "function") h.call(this, e);
    }
    _reply(msgs) { setTimeout(() => this._emit("message", JSON.stringify(msgs)), 5); }
    _incoming(raw) {
      // states: HA's own helpers of LCARdS and this framework (input_*.lcards_*, lcars_*) stay real, the
      // rest is the demo's
      const msgs = JSON.parse(raw);
      for (const m of Array.isArray(msgs) ? msgs : [msgs]) {
        if (m.type !== "event" || m.id !== this._states) continue;
        for (const k of ["a", "c"]) {
          if (m.event[k]) m.event[k] = Object.fromEntries(Object.entries(m.event[k]).filter(([id]) => KEEP.test(id)));
        }
        if (m.event.r) m.event.r = m.event.r.filter((id) => KEEP.test(id));
        if (!this._sentDemo) { this._sentDemo = true; Object.assign(m.event.a || (m.event.a = {}), compressed()); }
      }
      this._emit("message", JSON.stringify(msgs));
    }
    send(raw) {
      const m = JSON.parse(raw);
      const ok = (result) => this._reply([{id: m.id, type: "result", success: true, result}]);
      const event = (ev) => this._reply([{id: m.id, type: "event", event: ev}]);
      switch (m.type) {
        case "subscribe_entities":
          this._states = m.id;
          break;
        case "get_states":
          return ok(full());
        case "lovelace/config":
          return ok(dashboard);
        case "weather/subscribe_forecast":
          ok(null);
          return event({type: m.forecast_type, forecast: data.forecast(m.forecast_type)});
        case "recorder/statistics_during_period":
          return ok(Object.fromEntries(m.statistic_ids.map((id) =>
            [id, data.statistics(id, Date.parse(m.start_time), Date.parse(m.end_time || new Date()), m.period)])));
        case "history/history_during_period":
          return ok(Object.fromEntries(m.entity_ids.map((id) =>
            [id, data.history(id, Date.parse(m.start_time), Date.parse(m.end_time || new Date()))
              .map(([t, v]) => ({s: String(v), lu: t / 1000}))])));
        case "history/stream": {
          ok(null);
          const start = Date.parse(m.start_time), end = Date.parse(m.end_time || new Date());
          return event({states: Object.fromEntries(m.entity_ids.map((id) =>
            [id, data.history(id, start, end).map(([t, v]) => ({s: String(v), lu: t / 1000}))])),
            start_time: start / 1000, end_time: end / 1000});
        }
        case "media_player/browse_media":
          return ok(data.browse(m.media_content_id));
        case "frontend/get_user_data":
        case "frontend/subscribe_user_data":
          if (m.key !== "language") break;   // English, whatever the token's user has chosen
          ok(m.type === "frontend/get_user_data" ? {value: LANGUAGE} : null);
          if (m.type === "frontend/subscribe_user_data") event({value: LANGUAGE});
          return;
        case "call_service":
        case "execute_script":
          console.log("[demo] blocked", m.type, m.domain || "", m.service || "");
          return ok({context: {id: "demo"}});
        case "subscribe_events":
          if (m.event_type === "state_changed") return ok(null);
          break;
      }
      if (/^(logbook|history|recorder|calendar)\//.test(m.type)) console.log("[demo] unmocked", m.type);
      this._ws.send(raw);
    }
  }
  for (const k of ["CONNECTING", "OPEN", "CLOSING", "CLOSED"]) DemoSocket[k] = DemoSocket.prototype[k] = Real[k];
  window.WebSocket = DemoSocket;

  // ── REST: calendars, logbook, history; everything else goes to HA, POSTs are dropped ──
  const realFetch = window.fetch.bind(window);
  const json = (body) => new Response(JSON.stringify(body), {status: 200, headers: {"Content-Type": "application/json"}});
  window.fetch = (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    const method = ((init && init.method) || (input.method) || "GET").toUpperCase();
    const p = url.pathname;
    let m;
    if ((m = p.match(/^\/api\/calendars\/(.+)$/))) {
      return Promise.resolve(json(data.calendar(decodeURIComponent(m[1]),
        Date.parse(url.searchParams.get("start")), Date.parse(url.searchParams.get("end")))));
    }
    if ((m = p.match(/^\/api\/logbook\/(.+)$/))) {
      const ids = (url.searchParams.get("entity") || "").split(",");
      return Promise.resolve(json(data.logbook(ids, Date.parse(decodeURIComponent(m[1])))));
    }
    if (p.startsWith("/api/history/period")) {
      const ids = (url.searchParams.get("filter_entity_id") || "").split(",");
      const start = Date.parse(decodeURIComponent(p.split("/")[4] || "")) || Date.now() - 86400e3;
      return Promise.resolve(json(ids.map((id) => data.history(id, start, Date.now()).map(([t, v]) =>
        ({entity_id: id, state: String(v), last_changed: new Date(t).toISOString()})))));
    }
    if (p.startsWith("/api/") && method !== "GET") {
      console.log("[demo] blocked", method, p);
      return Promise.resolve(json({}));
    }
    return realFetch(input, init);
  };
};
