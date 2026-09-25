# Design rules and how to extend the dashboard

Everything here was decided with the user. Keep it unless the user changes it.
**The waste, OPS, laundry and aquarium pages are the reference style**; the calendar
pages still use the older row style and should move towards the reference when they
are reworked.

## General decisions

- **No page scrolling, ever.** Every view is exactly one viewport. Frames are
  sized to their content; whatever is left of the page stays black.
- **Two target screens**: 1920×1080 (desktop) and **1280×800** (Lenovo Tab M10
  Gen 1, Fully Kiosk, landscape). Every page must fit and read well on both;
  check both after layout changes (`tools/screenshot/`, see
  `docs/OPERATIONS.md`). The tablet's real viewport is shorter than 800 (system
  bars), so also check 1280×720.
- **Display priorities** (user decision): content that doesn't fit vertically
  is **not rendered**, rather than cut off or squeezed. `PRIORITY_MIN_H` maps a
  priority to the minimum viewport height it needs (1 always, 2 ≥ 760 px,
  3 ≥ 880 px, 4 ≥ 1000 px). `shown_from(card, p)` hides one card below its
  priority; `tiered({p: card, ...})` picks one of several variants (e.g. a
  frame closed or open at the bottom, 10/9/8 list rows). Both use HA's `screen`
  visibility condition: `hui-card` doesn't create a card that isn't shown, so
  it costs nothing on the tablet. Current uses: header number columns (4th row,
  p4), light page device log (p3, else Controls closes the S), power charts on
  Laundry, Osmosis and Power (p2), Waste and OPS lower frames (closed at p2,
  open at the bottom below; OPS forecast bars 8 → 6), Agenda list (10/9/8 rows
  at p3/p2/p1). The fallback for a frame that no longer fits: drop its bottom
  shoulder first, then leave it out.
- **Voyager palette**, hex constants at the top of `build_dashboard.py`
  (orange, butterscotch, peach, almond, violet, lilac, bluey, peri, ice, rose,
  red, sunflower, gray, and `BONE` for light blocks). Hex on purpose, so LCARdS
  alert modes don't shift them.
- **Colours stay semantic** for states: ice = OK/running, sunflower =
  warning/manual, red = critical, grey = off.
- **All UI text is English.** Sensor states and calendar titles arrive in
  German; bin names are mapped (`BIN_NAMES`, `CAL_LABELS`). Dates use `en-GB`
  ("Fri 25/09 · tomorrow").
- **Menus are part of the frame.** The header frame bar is the section menu
  (**OPS, Aquarium, Laundry, Waste, Calendar**, active item orange with "◂"); the
  sidebar blocks list the active section's sub-views and, at the bottom, the
  per-device **Motion** switch. **Classic** (link to the section's original
  dashboard) is the top piece of the header frame's pillar, above its elbow.
- **Foot bar**: as thick as its text (`FOOT_FONT`; the bar `FOOT_T` and the foot
  row follow from it). It ends in the local date/time (orange, as tall as the
  bar, in a gap of the bar like a panel caption, `clock()`) and a square peach
  **stardate** block (`stardate_block()`). Both re-render every minute through
  `sensor.time`. Stardate: TNG form, 1000 units per year, one decimal (≈ 53 min),
  anchored so that 1987 (TNG's first season, 41xxx) is 41000–41999, so 2026 is
  80000–80999.9.
- **Frame corners**: the mid and foot elbows of the page frame share one outer
  radius (the frame row height); all corners around the content share one inner
  radius.
- **Every numbered thing has its own number**: all codes come from
  `lcars_code(key)` (stable hash of a key, collision-checked). A view's sidebar
  block and its subtitle share one code (same thing). Nothing is hand-numbered.
  Pieces that merge into a shoulder carry **no** number.
- **Performance**: LCARdS is for the frame, blocks, readouts and controls.
  Dense graphics (grids of cells, segment bars, calendars, forecast, radar) are
  small custom cards in `ha/www/` with plain divs/CSS. Hundreds of LCARdS
  buttons crash the tablet's renderer (see `docs/NOTES.md`).

## Reference style (waste, OPS, laundry and aquarium pages)

Inspired by LCARS "exterior overview" / "database" screens (the user's two
reference images): brackets around groups, label blocks as pillars, graphics
next to values, restrained colour.

### Frames (`panel()`)

- Every group sits in its own **bracket**: a pillar on one side with elbow
  **shoulders** at the ends that have a bar. Sizes: bar thickness
  `PANEL_T` 26 px, shoulder `PANEL_CORNER` 46 px, gaps between pillar pieces
  `PANEL_GAP` 4 px.
- **Title** in a gap of the top bar, in the frame colour, font as tall as the
  bar. A frame open at the top carries it in the bottom bar instead.
- **Open or closed is per page, not a rule.** A frame can leave out its bottom
  (or top) bar, e.g. the waste timeline and OPS' top frames are open at the
  bottom, the laundry page's power trace is closed. Decide by what looks right.
- **Neighbouring lower frames face each other**: pillars (and shoulders) meet in
  the middle (e.g. Next per bin | Hazmat, Next 7 days | Forecast).
- **The pillar is made of content**: label blocks (`pillar_rows()`), the
  timeline's bin blocks, or numbered decorative/control blocks
  (`with_decor_pillar()`, the radar's buttons). Plain pillars only where there
  is nothing to put in them.
- **Seams**: the first pillar piece in the frame colour runs into the top
  shoulder without a gap (`join_top`) and has no number; the last one (filler)
  runs into the bottom shoulder. Both overlap by 2 px, otherwise fractional zoom
  (110 %) leaves hairline seams.

### Content

- **Label blocks**: filled block, black label vertically centred and
  right-aligned, auto number top-left. Colour carries meaning (bin colour,
  calendar colour); `BONE` for neutral data (hazmat), frame colour for fillers.
- **Values** next to their block, bold, in peri, aligned towards the block.
- **No half-empty frames**: the space beside a value carries a graphic, usually
  a segment bar (countdown, scale, 24 h window/span). LCARS frames are never
  mostly black inside.
- **Bars** (`lcars-bar.js`): 14 segments (one per 2 days for countdowns, 24 per
  day for time scales), inactive segments static at 18 % peri, lit segments in
  the row colour. They grow away from the pillar. A level at its minimum lights
  nothing. **Status bars** (`state_bar()`, mode `state`) light every segment in
  the state's colour (e.g. ice = on/running) or none. Other modes can take their
  lit colour from the state too (`states`, e.g. the water-change countdown in
  its status colour), a level can turn red below a threshold (`alarm`, dosing
  fill levels), and `days` lights weekdays from a list, optionally with a
  letter in each segment (`labels`, dosing weekdays).
- **Switches have no bar** (user decision): a row that switches something (tap
  its block or value; hold: more-info) shows only its value, e.g. RO unit,
  CO² coupling, light automation, laundry Supply. Bars are for readings.
- **Mode switches are LCARS buttons** (`mode_button()`): rounded pills in a
  frame, in their state colour while on and grey while off (aquarium Modes).
- **Timeline / week grids**: weekday header and day numbers, weekends dimmer,
  today lighter and its labels orange.
- Bin colours appear only in label blocks, filled cells and bars.

### Header (per section, `section_readouts()`)

- Readouts with the key values, then **LCARS number columns** in the free space:
  20 real sensors (power/energy meters first, `number_sensors()`) as 4-digit
  hex codes (value×100), read on page load, with a staggered colour waterfall.
- On screens ≥ 1600 px a **2×2 block of LCARS pills** (auto numbers, no
  function) right of the number columns; the column is 0 px below that (CSS
  `clamp()`, layout cards have no media queries).
- No local time in the header (it sits in the foot bar). Readout values scale with the viewport
  width (theme variable `lcars-readout-size`), titles can differ from the menu
  label (`SECTION_TITLES`, e.g. "Operations" for OPS).

### Animation

- Allowed, on request of the user: lit bar segments **flash white briefly**
  (2.5 % of a random 8–24 s cycle, no fade); number columns run a colour
  waterfall; the radar loops its frames; the title blinks on a critical pump
  alert. Nothing else moves.
- Every animation honours the per-device **motion switch** (`?lcars_motion=off`,
  sidebar "Motion"): LCARdS animations via the paused anime.js engine, the
  custom cards by checking it themselves.

## Pages

- **Waste**: 28-day collection timeline (bin blocks as pillar, open at the
  bottom); below, facing frames "Next per bin" (pillar right, bin colours) and
  "Hazmat collection" (pillar left, bone blocks) with countdown bars and a 24 h
  window scale.
- **OPS** (title "Operations"): "Atmosphere" (temperature −10..35 °C, humidity,
  pressure 970..1050 hPa, wind 0..60 km/h with compass direction, daylight on a
  24 h span) and the **DWD precipitation radar** (−60..+90 min, 10-min frames,
  black map with county/state borders, pillar buttons Play/Pause, Back, Next,
  Now); below, facing frames "Next 7 days" (yellow, pillar right, only calendars
  with events, max 5) and "Forecast" (lilac, pillar left: hour, condition code,
  temperature bar, °C, mm). No tasks, no NINA (user decisions).
- **Laundry**: header readouts Cycle and Power plus number columns. Top frame
  "Laundry unit" (lilac, full width, pillar left: Cycle as a status bar, Power
  on a 0..2000 W level bar, Energy total and Supply without a bar; holding the
  Supply block or value switches the supply). Below, "Power trace" (closed
  frame, chart as high as the waste timeline, less where the page is too short,
  e.g. on the tablet): drawn like the aquarium power
  chart (log scale, smooth filled area, W lines 1–1000, no legend) by
  `lcars-power.js`; its pillar holds the range buttons **24H / 7D / 28D**
  (active one orange with "◂", stored per device), peak per 5 min (24 h) or
  per hour (7 d, 28 d) from HA's long-term statistics. "Running" means above
  3 W. No protection sensors (user decision: no real value).
- **Aquarium** (header: Total power, Circulation, number columns, pills):
  - *Status*: facing frames "Modes" (four LCARS buttons: Auto/Manual mode,
    Maintenance, Feeding with its resume time, Water change) | "Equipment"
    (Pump, Heater, CO² with status bars, CO² coupling), below "Illumination"
    (Automation, Light phase, Next change) | "Water change" (Status with days
    since on a 0..14 d bar, Last change, Next due as a countdown).
  - *Visual*: the camera in "Visual sensor 01" (numbered pillar facing the
    readings), "Readings" (Feed, Circulation, Illumination, Total power) next to it.
  - *Light*: on the left a **double S** of three frames (`s_chain()`,
    `s_joint()`: a frame's bottom shoulder and the next one's top shoulder sit
    on one shared bar that carries the next frame's title). "Phase control"
    (pillar left: Current, Scheduled, Next, Ramp; next to them the day's phases
    as a graph, `lcars-phases.js`: one smooth shape per phase in its colour,
    rising over the ramp-up and falling over the ramp-down, height = its
    brightest channel relative to the brightest phase (at least 30 %), no
    per-channel values; now line with a dot on the curve) runs into "Controls"
    (pillar right: small LCARS pills Automation on/off, Fire, Chill, and
    numbered decorative pills without a function), which runs into "Device
    log" (pillar left, whatever height is left, bottom bar level with the
    Channels frame's). On the right "Channels" (pillar on the outer edge, so
    its top bar meets Phase control's): red/green/blue as vertical
    **transporter controls** (`lcars-transporter.js`; drag a slot, the value is
    sent when the finger lifts). The phases come from
    `/config/aquarium_light_control.yaml`, read over SSH at build time (no
    entity exposes them).
    Device log (`lcars-log.js`): the last 24 h of the light, its plug and their
    sensors from HA's logbook, newest first, only whole lines (time, tag, event,
    a descriptive detail in LCARS wording, e.g. "Illumination cycle nominal ·
    emitter array R 45 · G 35 · B 40" with the schedule's levels, and a
    reference code `REF xxxx-nn · SEQ nnnn` derived from the event, so it stays
    put; below 700 px the code is left out), colour waterfall
    like the header's number columns, new lines flash. Colours by severity:
    peri info (phases, light on/off), ice ok (schedule resumed, back online,
    protection flag cleared), sunflower warning (manual override, automation
    off, firmware update), butterscotch/amber flap (gone and back within
    60 s), red error (offline longer, overtemperature/-load/-voltage/-current,
    plug power off), grey raw BLE notification codes (bursts within 60 s
    collapsed into one line).
  - *Dosing*: frame "Dosing station" with the row labels as its pillar and a
    small frame per channel inside it (thin pillar alternating right / left
    from Nitrate on, open at the bottom, the channel's name in its top bar,
    channel colour; their bodies line up with the label rows, so the
    channels aren't listed twice). Per channel: a Schedule pill (tap to switch
    it) and right of it a Refill button in the channel colour (hold: mark the
    bottle refilled, tap: more-info), the bottle as a vertical 20-segment tank
    (`lcars-tank.js`: scale 500/250/LOW, pointer with ml and % at the level,
    red below 50 ml; tap: more-info), Remaining (days until empty at the
    scheduled rate, and the date), Dose (ml · time), Next (today / tomorrow /
    weekday) and last Weekdays (M–S strip).
  - *Power*: "Power grid" (Total 0..350 W, Pump 0..250, Light 0..100, CO² valve
    0..2 W; the block colours are the chart's legend) and "Power visualization"
    (mirrored 24 h LCARdS chart: zero axis in the middle, total above, consumers
    below, log scale, 10/100 W lines; 1 W lines don't fit on the tablet).
  - *Osmosis*: like Laundry: "RO unit" (unit with auto-off time and pending
    firmware update, Mode, Power 0..40 W, Energy) and the power trace with
    range buttons. Four rows, so the trace keeps its height on the tablet.
- **Calendar pages** (older style): flat dark-tinted rows with a state-coloured
  left stripe, small section headers.

## Light custom cards (`ha/www/`)

| Card | Used for |
|------|----------|
| `lcars-day-grid.js` | waste collection timeline cells |
| `lcars-bar.js` | segment bars: `countdown`, `window`, `level`, `span`, `state`, `days` |
| `lcars-transporter.js` | light channels as vertical transporter-console sliders (drag, sent on release) |
| `lcars-phases.js` | the light schedule over 24 h: a smooth shape per phase with its ramps, now line |
| `lcars-log.js` | device log from HA's logbook: severity colours, flap detection, BLE bursts collapsed, waterfall |
| `lcars-tank.js` | a dosing bottle's fill level as a vertical segment stack with scale and pointer; tap opens more-info |
| `lcars-week.js` | next days of all calendars (refreshes HA's calendars first) |
| `lcars-forecast.js` | hourly forecast (weather/subscribe_forecast) |
| `lcars-radar.js` | DWD radar with its own control pillar |
| `lcars-power.js` | power chart with its own range-button pillar (LCARdS charts stop at 168 h) |
| `lcars-motion.js` | not a card: motion switch, `?lcars_bars=` |

They take their colours and sizes from the generator's config, so the palette
stays in one place. `tools/deploy_ha_files.sh` copies every `ha/www/*.js` and
registers it as a resource with `?v=<timestamp>`.

## Structure of `generator/build_dashboard.py`

| Part | What it is |
|------|------------|
| Palette, entity constants, `lcars_code()` | colours, entity IDs, the number registry |
| `block`, `segments`, `elbow` | frame primitives |
| `clock`, `stardate_block` | foot bar: local date/time, stardate (`FOOT_FONT` sets the bar's size) |
| `header`, `row`, `column` | older content primitives (calendar pages) |
| `panel`, `pillar_rows`, `value_text`, `with_bar`, `with_decor_pillar` | reference-style frames and rows |
| `aq_panel`, `state_row`, `plain_row`, `mode_button` | aquarium rows: status/switch rows, LCARS mode buttons |
| `PRIORITY_MIN_H`, `shown_from`, `tiered` | display priorities: content not rendered below its viewport height |
| `s_joint`, `s_chain` | frames joined into an S (or double S) through shared bars (light page) |
| `transporter_card`, `light_phases`, `phases_card`, `light_log_card` | light page cards; `light_phases()` reads the schedule from the HA host |
| `data_bar`, `countdown_bar`, `window_bar`, `level_bar`, `span_bar`, `state_bar` | segment bar configs (`lcars-bar.js`); `tank_card` (`lcars-tank.js`) |
| `power_card` | power chart with range buttons (`lcars-power.js`) |
| `number_columns`, `number_sensors`, `header_buttons` | header decoration |
| `SECTIONS`, `SECTION_TITLES`, `NAV_ORDER` | sections, sub-views, menu order, titles |
| `section_readouts(section)` | header slots: a card, `(card, n)` spanning n slots, or `(card, "wide")` for ≥ 1600 px only |
| `frame()` / `view()` | the shared page frame around a view's content |
| `*_content()` | one function per view |
| `VIEWS` | `view(section, key, title, path, content, subtitle)`; the code is appended to the subtitle |
| `finalize()` | global post-processing: `minmax(0,Nfr)`, `min_height: 0`, optional `CLICK_SOUNDS` |

### Adding a view to an existing section

1. Write `my_content()` returning a layout grid (reference style: `panel()`s).
2. Add `(key, label, lcars_code("view/<key>"), colour, "<section>-<name>")` to
   that section's sub-view list in `SECTIONS`.
3. Add `view("<section>", key, "LCARS …", "<section>-<name>", my_content(), "Subtitle")`
   to `VIEWS`.
4. Run `python3 tools/deploy.py` (it validates before saving) and check both
   target screens.

### Adding a new section

Do the above, then also add a `SECTIONS` entry, put its key in `NAV_ORDER` and
add a branch in `section_readouts()`.

## URL rules

- HA dashboard paths **must contain a hyphen**; HA rejects `lcars` ("Url path
  needs to contain a hyphen"). Hence `lcars-bridge`.
- A view path is a **single segment** (`/lcars-bridge/<view>`), so views are
  named `<section>-<view>`: `aquarium-power`, `waste-calendar`, `calendar-agenda`.
- A dashboard's path can't be renamed. Moving means creating a new dashboard.
  The old `aquarium-lcars` still exists, hidden from the sidebar as
  "LCARS (alt)", until the user decides to delete it.
- Query parameters: `?lcars_motion=off|on|toggle` (per device),
  `?lcars_bars=off|on|toggle` (global, stored in HA: never in a start URL).
