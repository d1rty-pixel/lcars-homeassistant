// Made-up data for examples/home.yaml, used by demo-mock.js (shot.js with DEMO=...): the README's
// screenshots. Everything is relative to `now`, so the pictures look alike whenever they are taken.
window.__lcarsDemoData = (nowMs) => {
  const H = 3600e3, D = 24 * H;
  const now = new Date(nowMs);
  const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const at = (day, h, m = 0) => midnight + day * D + h * H + m * 60e3;
  const iso = (t) => new Date(t).toISOString();
  const pad = (n) => String(n).padStart(2, "0");
  const ymd = (t) => { const d = new Date(t); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
  const local = (t) => { const d = new Date(t); return `${ymd(t)} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`; };
  const hourOf = (t) => (t - midnight) / H;

  // smooth made-up curves over the time of day
  const solar = (t) => { const h = ((hourOf(t) % 24) + 24) % 24; return h < 6.5 || h > 19.5 ? 0 : Math.round(
    6200 * Math.sin(Math.PI * (h - 6.5) / 13) ** 1.6 * (0.85 + 0.15 * Math.sin(t / 1.7e6))); };
  const house = (t) => { const h = ((hourOf(t) % 24) + 24) % 24; return Math.round(280 + 90 * Math.sin(t / 2.3e6)
    + (h > 6.5 && h < 8 ? 1900 : 0) + (h > 12 && h < 13 ? 2300 : 0) + (h > 18 && h < 20.5 ? 1500 : 0)); };
  const washer = (t) => { const h = ((hourOf(t) % 24) + 24) % 24; return h > 9 && h < 10.5 ? (h < 9.4 ? 2100 : 180 + 60 * Math.sin(t / 3e5))
    : h > 16 && h < 17.2 ? (h < 16.3 ? 2050 : 150 + 50 * Math.sin(t / 3e5)) : 0.4; };
  const dryer = (t) => { const h = ((hourOf(t) % 24) + 24) % 24; return h > 10.6 && h < 12.4 ? 2300 - 900 * (h - 10.6) / 1.8 : 0.3; };
  const curves = {"sensor.pv_power": solar, "sensor.house_power": house, "sensor.washer_power": washer,
                  "sensor.dryer_power": dryer};

  const W = (unit, state, extra = {}) => ({state: String(state), attributes: {unit_of_measurement: unit, ...extra}});
  const waste = {"sensor.waste_residual": [2, 16], "sensor.waste_organic": [5, 12, 19, 26], "sensor.waste_recycling": [8, 22],
                 "sensor.waste_paper": [1, 29]};
  const wasteSensor = (days) => ({state: ymd(at(days[0], 7)),
    attributes: Object.fromEntries(days.map((d) => [ymd(at(d, 7)), "collection"]))});

  // calendars: [calendar, day, start hour, end hour (or null: all day), title]
  const events = [
    ["calendar.family", 0, 18, 19.5, "Book club"], ["calendar.family", 1, 8.5, 9.25, "Dentist"],
    ["calendar.family", 1, 17, 18.5, "Soccer practice"], ["calendar.family", 2, 19, 21, "Parents' evening"],
    ["calendar.family", 3, 12, 13, "Lunch with Sam"], ["calendar.family", 4, 17, 18.5, "Soccer practice"],
    ["calendar.family", 5, 10, 16, "Farmers' market"], ["calendar.family", 6, null, null, "Hiking trip"],
    ["calendar.family", 9, 15, 16, "Car inspection"], ["calendar.family", 11, 17, 18.5, "Soccer practice"],
    ["calendar.family", 13, 20, 23, "Concert"], ["calendar.family", -3, 19, 22, "Game night"],
    ["calendar.family", -6, 9, 10, "Vet"], ["calendar.family", 16, 14, 17, "Birthday party"],
    ["calendar.family", 20, 8, 9, "Blood test"], ["calendar.family", 23, 18, 19.5, "Book club"],
    ["calendar.holidays", 12, null, null, "Autumn break"], ["calendar.holidays", -10, null, null, "Harvest festival"],
    ...Object.entries(waste).flatMap(([id, days]) => days.map((d) => ["calendar.waste_collection", d, null, null,
      {"sensor.waste_residual": "Residual waste", "sensor.waste_organic": "Organic waste",
       "sensor.waste_recycling": "Recycling", "sensor.waste_paper": "Paper"}[id]])),
  ];
  const nextOf = (cal) => events.filter((e) => e[0] === cal && (e[3] === null ? at(e[1] + 1, 0) : at(e[1], e[3])) > nowMs)
    .sort((a, b) => at(a[1], a[2] ?? 0) - at(b[1], b[2] ?? 0))[0];
  const calState = (cal, name) => {
    const e = nextOf(cal);
    return {state: "off", attributes: {friendly_name: name, message: e[4], all_day: e[2] === null,
      start_time: local(at(e[1], e[2] ?? 0)), end_time: local(e[2] === null ? at(e[1] + 1, 0) : at(e[1], e[3]))}};
  };

  const states = {
    "weather.home": {state: "partlycloudy", attributes: {temperature: 17.4, humidity: 64, pressure: 1016,
      wind_speed: 12, wind_bearing: 240, temperature_unit: "°C", friendly_name: "Home"}},
    "sun.sun": {state: "above_horizon", attributes: {next_rising: iso(at(1, 7, 12)), next_setting: iso(at(0, 19, 8))}},
    "sensor.time": {state: `${pad(now.getHours())}:${pad(now.getMinutes())}`, attributes: {}},
    "binary_sensor.water_leak": {state: "off", attributes: {device_class: "moisture"}},
    "sensor.filter_status": {state: "OK", attributes: {days: 0}},
    "calendar.family": calState("calendar.family", "Family"),
    "calendar.holidays": calState("calendar.holidays", "Holidays"),
    "calendar.waste_collection": calState("calendar.waste_collection", "Waste"),

    "sensor.pv_power": W("W", solar(nowMs), {state_class: "measurement"}),
    "sensor.house_power": W("W", house(nowMs), {state_class: "measurement"}),
    "sensor.battery_level": W("%", 78),

    "sensor.wan_down": W("Mb/s", 48.2, {state_class: "measurement"}),
    "sensor.wan_up": W("Mb/s", 6.4, {state_class: "measurement"}),
    "binary_sensor.internet": {state: "on", attributes: {device_class: "connectivity"}},
    "sensor.wan_latency": W("ms", 18, {state_class: "measurement"}),
    "sensor.ap_hall_down": W("Mb/s", 12.7, {state_class: "measurement"}),
    "sensor.ap_hall_up": W("Mb/s", 1.9, {state_class: "measurement"}),
    "sensor.ap_hall_state": {state: "connected", attributes: {}},
    "sensor.ap_hall_clients": W("", 11),
    "sensor.switch_down": W("Mb/s", 31.5, {state_class: "measurement"}),
    "sensor.switch_up": W("Mb/s", 4.2, {state_class: "measurement"}),
    "sensor.desk_pc_down": W("Mb/s", 29.8, {state_class: "measurement"}),
    "sensor.desk_pc_up": W("Mb/s", 3.6, {state_class: "measurement"}),
    "sensor.nas_down": W("Mb/s", 0.4, {state_class: "measurement"}),
    "sensor.nas_up": W("Mb/s", 210, {state_class: "measurement"}),

    "sensor.washer_power": W("W", Math.round(washer(nowMs)), {state_class: "measurement"}),
    "sensor.washer_energy": W("kWh", 412.7, {state_class: "total_increasing"}),
    "switch.washer": {state: "on", attributes: {}},
    "sensor.dryer_power": W("W", Math.round(dryer(nowMs)), {state_class: "measurement"}),
    "sensor.dryer_energy": W("kWh", 268.3, {state_class: "total_increasing"}),
    "switch.dryer": {state: "off", attributes: {}},

    "climate.living_room": {state: "heat", attributes: {current_temperature: 21.5, temperature: 22, hvac_modes: ["off", "heat"]}},
    "climate.bedroom": {state: "heat", attributes: {current_temperature: 18.5, temperature: 18, hvac_modes: ["off", "heat"]}},
    "climate.office": {state: "heat", attributes: {current_temperature: 20.1, temperature: 21, hvac_modes: ["off", "heat"]}},
    "input_boolean.heating": {state: "on", attributes: {}},
    "input_boolean.away": {state: "off", attributes: {}},
    "fan.ventilation": {state: "on", attributes: {}},
    "sensor.co2": W("ppm", 742),
    "sensor.ventilation_humidity": W("%", 52),
    "sensor.boiler_flow_temperature": W("°C", 48.5),
    "sensor.boiler_return_temperature": W("°C", 36.2),
    "sensor.boiler_pressure": W("bar", 1.6),
    "sensor.boiler_next_service": {state: ymd(at(23, 0)), attributes: {}},
    "sensor.cistern_level": W("l", 3420),
    "sensor.cistern_days_left": W("d", 38),
    "sensor.oil_level": W("l", 820),
    "sensor.oil_days_left": W("d", 64),

    "light.living_room": {state: "on", attributes: {brightness: 191}},
    "light.kitchen": {state: "on", attributes: {brightness: 115}},
    "light.desk": {state: "off", attributes: {}},
    "scene.evening": {state: "scening", attributes: {}},
    "scene.movie": {state: "scening", attributes: {}},

    "sensor.waste_next": {state: "Paper", attributes: {date: ymd(at(1, 7))}},
    ...Object.fromEntries(Object.entries(waste).map(([id, days]) => [id, wasteSensor(days)])),

    "media_player.living_room": {state: "playing", attributes: {
      media_title: "Ad Astra per Aspera", media_artist: "The Holodeck Ensemble", media_album_name: "Warp Signatures",
      media_duration: 312, media_position: 124, media_position_updated_at: iso(nowMs), volume_level: 0.42,
      shuffle: false, repeat: "off", source: "Living room", source_list: ["Living room", "Kitchen", "Office", "Garden"],
      supported_features: 0x3ffff, entity_picture: "data:image/svg+xml," + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"><defs><radialGradient id="g" cx=".3" cy=".35" r=".9">
        <stop offset="0" stop-color="#ffcc99"/><stop offset=".35" stop-color="#cc6666"/><stop offset=".7" stop-color="#442266"/>
        <stop offset="1" stop-color="#0b0b1e"/></radialGradient></defs><rect width="300" height="300" fill="url(#g)"/>
        <circle cx="210" cy="90" r="28" fill="#ffe6b3" opacity=".85"/><path d="M0 230 Q150 170 300 230 V300 H0Z" fill="#110b26"/>
        </svg>`)}},
  };

  const forecast = (type) => {
    const conds = ["sunny", "partlycloudy", "partlycloudy", "cloudy", "rainy", "cloudy", "partlycloudy", "sunny"];
    if (type === "daily") {
      return Array.from({length: 7}, (_, i) => ({datetime: iso(at(i, 12)), condition: conds[i % conds.length],
        temperature: [19, 18, 15, 14, 16, 18, 20][i], templow: [9, 10, 8, 7, 8, 9, 11][i],
        precipitation: [0, 0, 2.4, 5.1, 0.6, 0, 0][i]}));
    }
    const h0 = Math.ceil(nowMs / H) * H;
    return Array.from({length: 24}, (_, i) => {
      const t = h0 + i * H, h = ((hourOf(t) % 24) + 24) % 24;
      const rain = h > 14 && h < 18 ? [0.2, 1.4, 2.1, 0.8][Math.floor(h - 14)] : 0;
      return {datetime: iso(t), temperature: Math.round((13.5 + 4.5 * Math.cos(Math.PI * (h - 15) / 12)) * 10) / 10,
        condition: rain ? "rainy" : h < 7 || h > 20 ? "clear-night" : h > 10 && h < 14 ? "sunny" : "partlycloudy",
        precipitation: rain, precipitation_probability: rain ? 70 : 10};
    });
  };

  const series = (id, start, end, step) => {
    const f = curves[id] || (() => 100);
    const out = [];
    for (let t = Math.ceil(start / step) * step; t <= end; t += step) out.push([t, Math.round(f(t))]);
    return out;
  };
  const statistics = (id, start, end, period) => {
    const step = {"5minute": 5 * 60e3, hour: H, day: D, week: 7 * D, month: 30 * D}[period] || H;
    const f = curves[id] || (() => 100);
    const out = [];
    for (let t = Math.ceil(start / step) * step; t < end; t += step) {
      // the period's max and mean, sampled
      let max = 0, sum = 0, n = 0;
      for (let u = t; u < t + step; u += Math.max(step / 24, 60e3)) { const v = f(u); max = Math.max(max, v); sum += v; n++; }
      out.push({start: t, end: t + step, max, mean: sum / n, min: 0});
    }
    return out;
  };

  const calendar = (id, start, end) => events.filter((e) => e[0] === id).map(([, d, h0, h1, title]) => h0 === null
    ? {summary: title, start: {date: ymd(at(d, 0))}, end: {date: ymd(at(d + 1, 0))}}
    : {summary: title, start: {dateTime: iso(at(d, Math.floor(h0), (h0 % 1) * 60))},
       end: {dateTime: iso(at(d, Math.floor(h1), (h1 % 1) * 60))}})
    .filter((e) => Date.parse(e.end.dateTime || e.end.date) >= start && Date.parse(e.start.dateTime || e.start.date) <= end);

  // the device log: switches and sensors changing over the last day, oldest first
  const log = [
    [-22.5, "fan.ventilation", "off"], [-22.4, "fan.ventilation", "on"], [-20, "binary_sensor.water_leak", "on"],
    [-19.8, "binary_sensor.water_leak", "off"], [-16, "switch.dryer", "on"], [-14.5, "switch.washer", "off"],
    [-13.2, "switch.washer", "on"], [-11, "fan.ventilation", "off"], [-10.2, "fan.ventilation", "on"],
    [-8, "switch.dryer", "off"], [-6.5, "switch.dryer", "on"], [-5.1, "switch.dryer", "off"],
    [-3.3, "fan.ventilation", "off"], [-3.2, "fan.ventilation", "on"], [-1.5, "switch.washer", "off"],
    [-1.4, "switch.washer", "on"], [-0.4, "switch.dryer", "on"], [-0.2, "switch.dryer", "off"],
  ];
  const logbook = (ids, start) => log.filter(([h, id]) => ids.includes(id) && nowMs + h * H >= start)
    .map(([h, id, state]) => ({when: iso(nowMs + h * H), entity_id: id, state, name: id}));

  const item = (title, id, play = true) => ({title, media_class: play ? "track" : "directory", media_content_id: id,
    media_content_type: play ? "music" : "library", can_play: play, can_expand: !play, children_media_class: null,
    thumbnail: null});
  const browse = (id) => id
    ? {...item("Library", id, false), children: ["Ad Astra per Aspera", "Nebula Drift", "Subspace Lullaby",
        "Captain's Log", "Tachyon Pulse", "Beyond the Neutral Zone", "Dilithium Dreams", "Starbase Nocturne",
        "Warp Core Hum", "The Long Patrol", "First Contact", "Ten Forward"].map((t, i) => item(t, `demo/track/${i}`))}
    : {...item("Media", "", false), children: [item("Library", "demo/library", false), item("Radio", "demo/radio", false)]};

  const history = (id, start, end) => series(id, start, end, 10 * 60e3);
  return {states, forecast, statistics, history, calendar, logbook, browse};
};
