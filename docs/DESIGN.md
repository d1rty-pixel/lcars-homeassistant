# Design rules and how to extend the dashboard

Everything here was decided with the user. Keep it unless the user changes it.
**Every page uses the page frame** (see "Page frame"; Media and OPS were the first). **The
waste, OPS, laundry and aquarium pages are the reference for frames and content inside the
page.** The migration plan below records how the pages got there.

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
  p4), light page device log (p3, else Controls closes the S), the shoulders of
  the small lower frames on OPS, Waste and Aquarium Status (p2; flat section bars
  below), OPS calendar rows (1/1/2/3 at p1..p4). The fallback for a frame that no longer fits: drop its shoulders
  first, then leave it out.
- **Voyager palette**, hex constants at the top of `build_dashboard.py`
  (orange, butterscotch, peach, almond, violet, lilac, bluey, peri, ice, rose,
  red, sunflower, gray, `EARTH` (muted orange for large fillers) and `BONE` for light blocks). Hex on purpose, so LCARdS
  alert modes don't shift them.
- **Colours stay semantic** for states: ice = OK/running, sunflower =
  warning/manual, red = critical, grey = off.
- **One colour family per frame** (user decision, after Voyager screens and the
  Voyager theme on thelcars.com, probably Okuda's own design language). Every
  piece that sits in a frame (elbows, pillar blocks, bar segments, LCARS
  buttons in a bar or pillar) keeps that frame's family: e.g. the upper frame
  in blues, the lower one in oranges. Colours are never shuffled across a frame.
  **Where two frames meet** (the bars between them), colours may mix and run
  into each other. **Exceptions**: states that must stand out, e.g. red alert,
  warnings, notifications; colours that carry data (bin, calendar and
  light-channel colours, chart legend blocks); state colours on buttons
  (e.g. Play/Pause ice while playing, Shuffle/Repeat ice while on). The
  **active item** (nav, sidebar, categories, output devices) is to be marked
  near-white (`ACTIVE`) with "◂" instead of orange, so it stands out in every
  family. In the generator: `HEADER_FAMILY` (header frame: Classic, elbow,
  decorative pills), the orange family for everything below (`SIDEBAR_COLOURS`
  for the sub-view blocks in turn, `EARTH` sidebar filler, Motion, foot bar,
  right side); the nav bar's section buttons are in the header family too (the
  section colours in `SECTIONS`), and only the mid bar's plain segments on pages
  without a titled mid bar mix (meeting point).
- **All UI text is English.** Sensor states and calendar titles arrive in
  German; bin names are mapped (`BIN_NAMES`, `CAL_LABELS`). Dates use `en-GB`
  ("Fri 25/09 · tomorrow").
- **Menus are part of the frame.** The header frame bar is the section menu
  (**OPS, Aquarium, Laundry, Waste, Calendar, Media**, active item orange with "◂"); the
  sidebar blocks list the active section's sub-views and, at the bottom, the
  per-device **Motion** switch. **The sidebar is context navigation and nothing
  else, on every page** (user decision: no controls in it). **Classic** (link to
  the section's original dashboard) is the top piece of the header frame's
  pillar, above its elbow.
- **Foot bar**: as thick as its text (`FOOT_FONT`; the bar `FOOT_T` and the foot
  row follow from it). It ends in the local date/time (orange, as tall as the
  bar, in a gap of the bar like a panel caption, `clock()`) and a square peach
  **stardate** block (`stardate_block()`). Both re-render every minute through
  `sensor.time`. Stardate: TNG form, 1000 units per year, one decimal (≈ 53 min),
  anchored so that 1987 (TNG's first season, 41xxx) is 41000–41999, so 2026 is
  80000–80999.9.
- **Frame corners**: all corners around the content share one inner radius
  (`INNER_CURVE`). A mid elbow's outer radius is its row height (bar plus inner
  radius); the foot elbows use `FRAME_H`. On pages with the previous frame the
  mid row is `FRAME_H` high, so mid and foot match there.
- **Every numbered thing has its own number**: all codes come from
  `lcars_code(key)` (stable hash of a key, collision-checked). A view's sidebar
  block and its subtitle share one code (same thing). Nothing is hand-numbered.
  Pieces that merge into a shoulder carry **no** number.
- **Performance**: LCARdS is for the frame, blocks, readouts and controls.
  Dense graphics (grids of cells, segment bars, calendars, forecast, radar) are
  small custom cards in `ha/www/` with plain divs/CSS. Hundreds of LCARdS
  buttons crash the tablet's renderer (see `docs/NOTES.md`).

## Page frame (reference: Media)

The frame every page sits in: header with the section menu, sidebar, mid bar,
foot bar, optionally a right side. Built by `frame()` / `view()`.

- **The content's top bar is the page frame's mid bar** (`frame(mid_bars=...,
  mid_t=...)`). The columns below have no top bar of their own. Per content
  column the mid bar carries its **title** and its **context buttons**: controls
  that act on that column (Media: the player's transport, Play/Pause, Back,
  Next, Shuffle, Repeat). Context buttons are LCARS blocks (number top-left,
  label bottom-right), in their state colour where they have one.
- **Bar and content split at the same x.** A bar piece ends where its content
  column ends, with the same gap (`FRAME_GAP`, 6 px). `top_bars(columns,
  pieces, right_w)` takes the top row's column widths (the same list the
  content grid uses) and writes each piece's width as CSS `calc()`, so bar and
  content stay aligned at any width. A bar piece may span several columns (Media: Now playing's piece also
  covers the output device column, so the transport has room).
- **Titles in bars** (`title_text()`, `titled_bar()`): font size = bar thickness,
  always; there is no size parameter. The title sits on its alphabetic baseline,
  `(1 − ANTONIO_CAP) / 2 × size` above the bottom edge, so the capitals are
  centred with equal space above and below (Antonio's cap height is 0.86 em:
  37 px capitals in a 43 px bar, 3 px each side). LCARdS' default baseline
  (`middle`) centres the font's em box and pushes the capitals against the top
  edge. A title sits next to the shoulder on its side, after (left) or before
  (right) a 14 px cap segment, in the column's colour.
- **Thickness**: the mid bar is `TOP_BAR_T` 43 px when it carries titles and
  buttons; the header's nav bar is `NAV_H` 43 px on every page.
- **The header follows the page's right side** (user decision): on a page closed
  on the right (`frame(right=...)`) the nav bar ends in a shoulder that rises into
  a numbered block on the header's right edge, mirroring Classic and the elbow on
  the left, exactly as wide as the page's right side below it (Media, Status:
  150 px; Visual, Light: 90 px). On a page open on the right the nav bar runs to
  the edge.
- **Context buttons of a card with local state** (the radar: playing, current
  frame) are a second instance of the same card showing only its buttons
  (`controls: "row"`), linked to the map instance (`controls: "none"`) through
  a `group` and window events. Cards whose state is in HA (the player) need no
  link: every instance reads the entity.
- **A column whose pillar is the sidebar has no bracket of its own** (Media: Now
  playing). Other columns bring their pillar as content (label blocks, the
  library's categories).
- **Right side, per page**: either the frame is **closed on the right**
  (`frame(right=(colour, width))`: a shoulder runs down from the mid bar and one
  up from the foot bar, and the content supplies the pillar between them as its
  right edge, exactly `width` px wide; Media: the library's category pillar), or
  it is **open** and both bars run to the right edge as before. Both are valid.
  A column never gets its own bottom shoulder next to the foot bar (user
  decision: it looked wrong); it merges into the foot bar through the right
  frame instead.
- **The foot bar is the same on every page**: date/time and stardate stay at
  its end. With a right frame they sit just before the right shoulder, i.e.
  about 200 px further left than on pages without one.
- **One label column** (user decision, OPS): where a page has several sections
  of label blocks (the "database" style), all of them form one column next to
  the sidebar: every block the same width (`ATMOS_LABEL_W`), one under the
  other, through all sections. The first section's title is in the mid bar; each
  further section starts with a **section bar** (`section_bar()`, `section()`):
  a bar `PANEL_T` thick that grows out of the column (a block as wide as the
  column, the title as tall as the bar, the rest of the bar), so the mid bar's
  title never reads as the title of the whole column. Flat bars rather than
  shoulders: two shoulders would cost the tablet 40 px, i.e. a calendar row.
  No bottom bars: a section ends at the next section's bar or the foot bar.
- **Inner frames where they make sense** (user decision): a section may be a
  small frame of its own inside the page frame, with a top shoulder and its
  title in the bar (`panel(pillar=...)`, OPS: Next 7 days; the Aquarium status
  page's frames). Its pillar is the label column itself, the shoulder exactly
  as wide, so **the vertical frame pieces stay aligned** down the page. A
  section right above such a shoulder closes with a **thin bottom bar and a
  shoulder of the same outer radius** (`bottom_shoulder()`, `FC_BOTTOM_T`), the two
  shoulders a frame gap (`FRAME_GAP`) apart. That bar runs to the right edge, under
  whatever stands beside the section (OPS: the radar ends level with the forecast). Where the page is too short, the
  shoulders go first (flat section bars instead, as the display priorities
  rule says). Not every section needs one (Laundry: flat section bar only).
- **A numbered pillar can be the frame's right side** (Visual: the camera's, Light:
  the channels'; Media: the library's categories): `frame(right=...)` with the
  pillar at the content's right edge, exactly that wide.
- **Two frames side by side face outwards** (Waste, Aquarium Status; `outward_pair()`): pillars on the outer edges, their
  top bars meet in the middle as one line from shoulder to shoulder. A pillar in the
  middle of the page looks cut off. Between them, a column of numbered blocks without
  a function hanging from that line gives the frames room (colours may mix there,
  where the frames meet).
- **A section is a frame** with a colour family of its own (user decision
  after comparing with an all-orange variant; OPS: Atmosphere orange, Forecast
  lilacs `OPS_FORECAST`, Next 7 days blues `OPS_WEEK`).
- **Button columns between content columns** (Media: output devices): LCARS
  blocks, numbered, each at most `source_row` px high, the active one
  near-white with "◂", **no filler** below (the rest stays black).
- Tried and rejected (2026-09-25): transport buttons in the sidebar (the sidebar
  must stay navigation, and Aquarium has six sub-views); transport as a row
  under the player (buttons belong in the bar); a column's own bottom shoulder
  under a right pillar.

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
- **Every pill goes through `pill_shape()`**: radius `PILL_RADIUS`, label bottom
  right and number top left inset by `PILL_INSET` (18 px from the side, 5 px from
  the edge), so the rounded ends never cover them. Only the font size varies
  (`small_pill()`, the Modes grid's 14 px); no pill sets its own paddings.
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

- **Waste** (page frame, `waste_view()`; one view, the separate waste calendar view was dropped): the
  28-day collection timeline under the mid bar (title there, orange; its bin blocks are the label
  column), closed below by a thin bar with a shoulder across the full width. Below, two small frames
  with top shoulders that **face outwards**: "Next per bin" (peach; its pillar continues the label
  column, same width, bin colours, date and countdown bar per bin) and "Hazmat collection" (red, pillar
  on the page's right edge, bone blocks: date with a countdown bar, time window on a 24 h scale,
  location; values and bars aligned towards its pillar). Between them a column of numbered blocks
  without a function (`WASTE_DECOR`), one per data row, hanging from a piece of the shared top line:
  it keeps the two frames' bars apart. Below 760 px flat section bars instead.
- **OPS** (title "Operations"; page frame, `ops_view()`): top row `OPS_COLUMNS`
  1.5 : 1. On the left one label column (see "One label column") through three
  sections: **Atmosphere** (title in the mid bar, orange: temperature −10..35 °C,
  humidity, pressure 970..1050 hPa, wind 0..60 km/h with compass direction,
  daylight on a 24 h span, each with a bar in its block's colour), **Forecast**
  (section bar and a thin bottom shoulder; blocks Time and Temp · Rain beside the
  card's two rows: hour or weekday and condition code; temperature bar, °C and mm
  under it; `lcars-forecast.js` with `layout: "rows"`, `rows.rain: null`; below
  Temp · Rain, within the card's height, the **Hourly / Daily** switch: a toggle
  instance of the same card, one block of the label column, the choice stored per
  device; daily shows 7 days with the day's high and precipitation) and **Next 7
  days** (a frame of its own with a top shoulder facing the forecast's, across
  the full width under the radar; exactly as high as its calendar rows: 1 below
  880 px, 2 below 1000 px, else 3; the forecast and the radar get the rest).
  Below 760 px both shoulders give way to flat section bars. On the right the **Radar** (almond piece of the
  mid bar with the buttons Play/Pause, Back, Next, Now; the title is short so
  they fit at 1280 px): the DWD precipitation radar (−60..+90 min, 10-min
  frames, black map with county/state borders), over Atmosphere and Forecast.
  Right side open. No tasks, no NINA (user decisions).
- **Laundry** (page frame, `laundry_view()`; header readouts Cycle and Power plus number columns):
  one label column (`DATA_LABEL_W`) like OPS. "Laundry unit" (title in the mid bar, orange: Cycle as a
  status bar, Power on a 0..2000 W level bar, Energy total and Supply without a bar; holding the Supply
  block or value switches the supply). Below, the section "Power trace" (lilacs, `LAUNDRY_TRACE`; as
  high as the waste timeline, less where the page is too short): drawn like the aquarium power chart
  (log scale, smooth filled area, W lines 1–1000, no legend) by `lcars-power.js`; its range buttons
  **24H / 7D / 28D** continue the label column (one row high, active one near-white with "◂", stored
  per device, `power_card(column=...)`), peak per 5 min (24 h) or per hour (7 d, 28 d) from HA's
  long-term statistics. "Running" means above 3 W. No protection sensors (user decision: no real
  value). Shown on every screen height now (the frame's shoulders are gone).
- **Aquarium** (header: Total power, Circulation, number columns, pills):
  - *Status* (`status_view()`): top row Equipment (label column: Pump, Heater,
    CO² with status bars, CO² coupling) | Modes (3 × 3 small LCARS pills: the four
    modes Auto/Manual mode, Maintenance, Feeding with its resume time ("Feed ·
    hh:mm"), Water change spread diagonally, numbered pills without a function in
    between; label 14 px so "Water change" fits at 1280 px; a numbered pillar on
    the right edge), both titles in
    the mid bar, closed below by a thin bar with a shoulder on either side. Below,
    two small frames facing outwards: "Illumination" (Automation, Light phase, Next
    change; **closed below**: a bottom shoulder, a bar and a shoulder up into the
    block column, which is its right side there) | "Water change" (pillar on the
    right edge, running into the foot bar's shoulder: Status with days since on a
    0..14 d bar, Last change, Next due as a countdown, Record: two numbered pills
    without a function and the pill "Change done", hold to log a water change now, `aquarium_water_change_control.
    set_last_change` without a date; tap: more-info). **One block column runs
    through the middle of the page** (`status_grid()`): blocks beside the rows, a
    piece where the thin bar and the lower frames' top line meet it (both end at
    it), its lower end in Illumination's colour running into Illumination's
    bottom-right shoulder. The frame is closed on the right: the Modes pillar
    hangs from the mid bar's right shoulder, Water change's runs into the foot
    bar's (`frame(right=(colour, width, foot colour))`). Below 760 px flat section
    bars, no shoulders.
  - *Visual* (`visual_view()`): "Readings" (Feed, Circulation, Illumination,
    Total power) as the label column | the camera, "Visual sensor 01"; the
    camera's numbered pillar is the frame's right side (closed on the right).
  - *Light*: on the left a **double S** of three frames (`s_chain()`,
    `s_joint()`: a frame's bottom shoulder and the next one's top shoulder sit
    on one shared bar that carries the next frame's title). "Phase control"
    (title in the mid bar; pillar left: Current, Scheduled, Next, Ramp; next to them the day's phases
    as a graph, `lcars-phases.js`: one smooth shape per phase in its colour,
    rising over the ramp-up and falling over the ramp-down, height = its
    brightest channel relative to the brightest phase (at least 30 %), no
    per-channel values; now line with a dot on the curve) runs into "Controls"
    (pillar right: small LCARS pills Automation on/off, Fire, Chill, and
    numbered decorative pills without a function), which runs into "Device
    log" (pillar left, as wide as Phase control's, whatever height is left, open
    at the bottom above the foot bar). On the right "Channels" (title in the mid
    bar; its pillar is the frame's right side, closed on the right, into the foot
    bar): red/green/blue as vertical
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
  - *Dosing* (`dosing_view()`): "Dosing station" (title in the mid bar) with the
    row labels as the label column (orange family) and a small frame per channel
    beside it (thin pillar alternating right / left
    from Nitrate on, open at the bottom, the channel's name in its top bar,
    channel colour; their bodies line up with the label rows, so the
    channels aren't listed twice). Per channel: a Schedule pill (tap to switch
    it) and right of it a Refill button in the channel colour (hold: mark the
    bottle refilled, tap: more-info), the bottle as a vertical 20-segment tank
    (`lcars-tank.js`: scale 500/250/LOW, pointer with ml and % at the level,
    red below 50 ml; tap: more-info), Remaining (days until empty at the
    scheduled rate, and the date), Dose (ml · time), Next (today / tomorrow /
    weekday) and last Weekdays (M–S strip).
  - *Power* (`power_view()`): "Power grid" (title in the mid bar; label column: Total
    0..350 W, Pump 0..250, Light 0..100, CO² valve 0..2 W; the block colours are
    the chart's legend) and the section "Power visualization · 24 h" (lilacs,
    `POWER_CHART`; mirrored 24 h LCARdS chart: zero axis in the middle, total
    above, consumers below, log scale, 10/100 W lines; its numbered blocks continue
    the label column, one row high each).
  - *Osmosis* (`osmosis_view()`): like Laundry: "RO unit" (title in the mid bar;
    unit with auto-off time and pending firmware update, Mode, Power 0..40 W,
    Energy) and the section Power trace (lilacs, `OSMOSIS_TRACE`) whose range
    buttons continue the label column.
- **Media** (header: Audio state, Output device; the reference for the page frame, `media_view()`):
  three columns under the mid bar, all in the main frame's orange family. **Now playing** (orange, no
  bracket: the sidebar is its pillar):
  square cover art (never cropped), title/artist/album/status (long values end in "…"), a 40-segment
  progress bar (tap to seek), a 20-segment volume slider (drag, sent on release). Its piece of the mid
  bar carries the title and the transport: Play/Pause (ice while playing), Back, Next, Shuffle and
  Repeat (ice while on, grey off; Repeat → Repeat 1 → off). Shuffle is on/off only: HA's Spotify entity
  and the Spotify Web API have no Smart Shuffle. Spotify refuses some commands in some contexts (e.g.
  Repeat: 403 "Restriction violated"; HA doesn't expose Spotify's "disallows", so the buttons can't be
  greyed in advance): the button flashes red and the status shows "Spotify refused · Repeat" for 5 s,
  instead of HA's generic error toast. **Output devices** (Spotify Connect): a column of
  LCARS buttons (almond), active one near-white with "◂". **Library** (`MEDIA_LIBRARY`, almond): rows
  that play on tap, artists open
  first ("Back" row returns); its category pillar (Playlists with Liked songs pinned first, Albums,
  Artists, Recent, Top tracks, then Up/Down paging) is the frame's right side. Widths: Now playing :
  Library = `MEDIA_NOW_FR` : 1, devices `MEDIA_SOURCES_W`. Every part is `lcars-player.js`: one
  `lcars-player` card per part (`transport: "row"` in the bar, `transport: "none"` + `sources: "none"`
  for the body, `sources: "column"` for the devices) plus `lcars-library`. An idle Spotify is woken on
  Play or a library tap (last device used in this browser). The entity is `media_player.spotify_*`,
  looked up live at build time (`spotify_entity()`), so relinking Spotify under another account only
  needs a rebuild. Classic opens HA's media browser.
- **Calendar** (one view, the month; the agenda view was dropped; `calendar_view()`, `lcars-month.js`):
  title and the buttons Back / Today / Next in the mid bar (a controls instance of the month card,
  linked by `group`). The label column is a block per week ("Wk 39", ISO weeks) under a head block
  with the month; beside it a 6 × 7 day grid, Monday first: the day's number, as many events as fit
  as bars in their calendar's colour ("+n" for the rest), today lit, the neighbouring months' days
  dimmed. The event text grows with the cells (about a quarter of a cell's height, 15..22 px); where
  only one event fits and the cell has room, it may take two lines. The frame is closed on the right by the legend, a numbered block per calendar in its colour
  (label at the bottom, clear of the code). Colours, labels and codes come from `calendar_list()`,
  shared with OPS' Next 7 days.

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
| `lcars-month.js` | a month of all calendars: week blocks, day grid, legend; `mode: "controls"`: Back / Today / Next, linked by `group` |
| `lcars-forecast.js` | hourly or daily forecast (weather/subscribe_forecast); `mode: "toggle"`: just the Hourly / Daily block, linked by window events and localStorage |
| `lcars-radar.js` | DWD radar; `controls`: `pillar` (own button pillar), `none` (map only), `row` (buttons only, linked to the map by `group`) |
| `lcars-player.js` | Spotify: `lcars-player` (now playing; `transport`: `pillar` / `bottom` / `none` / `row` = buttons only; `sources`: `pills` / `none` / `column` = device buttons only) and `lcars-library` (library browser with category pillar) |
| `lcars-power.js` | power chart with its range buttons: own pillar, or (`pillar.row`) one row high each as part of a label column (LCARdS charts stop at 168 h) |
| `lcars-motion.js` | not a card: motion switch, `?lcars_bars=` |

They take their colours and sizes from the generator's config, so the palette
stays in one place. `tools/deploy_ha_files.sh` copies every `ha/www/*.js` and
registers it as a resource with `?v=<timestamp>`.

## Structure of `generator/build_dashboard.py`

| Part | What it is |
|------|------------|
| Palette, entity constants, `lcars_code()` | colours, entity IDs, the number registry |
| `block`, `segments`, `elbow` | frame primitives |
| `pill_shape`, `small_pill`, `deco_pill`, `mode_button` | LCARS pills: shape and text insets, smaller text, without a function, switching an entity |
| `clock`, `stardate_block` | foot bar: local date/time, stardate (`FOOT_FONT` sets the bar's size) |
| `panel`, `pillar_rows`, `value_text`, `with_bar`, `with_decor_pillar` | reference-style frames and rows |
| `state_row`, `plain_row`, `mode_button` | aquarium rows: status/switch rows, LCARS mode buttons |
| `PRIORITY_MIN_H`, `shown_from`, `tiered` | display priorities: content not rendered below its viewport height |
| `s_joint`, `s_chain` | frames joined into an S (or double S) through shared bars (light page) |
| `transporter_card`, `light_phases`, `phases_card`, `light_log_card` | light page cards; `light_phases()` reads the schedule from the HA host |
| `data_bar`, `countdown_bar`, `window_bar`, `level_bar`, `span_bar`, `state_bar` | segment bar configs (`lcars-bar.js`); `tank_card` (`lcars-tank.js`) |
| `power_card` | power chart with range buttons (`lcars-power.js`) |
| `number_columns`, `number_sensors`, `header_buttons` | header decoration |
| `SECTIONS`, `SECTION_TITLES`, `NAV_ORDER` | sections, sub-views, menu order, titles |
| `section_readouts(section)` | header slots: a card, `(card, n)` spanning n slots, or `(card, "wide")` for ≥ 1600 px only |
| `frame()` / `view()` | the shared page frame around a view's content; options `mid_bars`, `mid_t`, `nav_h`, `right`, `main_margin` (see "Page frame") |
| `frame_elbow` | an elbow of the page frame in any colour/width (right shoulders) |
| `title_text`, `titled_bar`, `ANTONIO_CAP` | a title in a bar (size = bar thickness, capitals centred); a bar piece with title and optional buttons |
| `top_bars`, `FRAME_GAP`, `TOP_BAR_T` | the mid bar's pieces over the top row, aligned with its columns |
| `section`, `section_bar`, `SECTION_GAP` | a section of the label column with its bar (OPS) |
| `outward_pair`, `closed_top`, `bottom_shoulder`, `rows_h` | two small frames facing outwards with a block column between them; a top row closed by a thin bar above them |
| `media_view`, `MEDIA_*`, `ops_view`, `OPS_*` | migrated pages: content plus frame options |
| `*_view()` | one function per view: `dict(content=..., mid_bars=..., mid_t=..., nav_h=..., right=...)` for `view()` (the Calendar section still uses `*_content()` with the previous frame) |
| `VIEWS` | `view(section, key, title, path, content, subtitle, **frame options)`; the code is appended to the subtitle |
| `finalize()` | global post-processing: `minmax(0,Nfr)`, `min_height: 0`, optional `CLICK_SOUNDS` |

### Adding a view to an existing section

1. Write `my_view()` returning the content grid and the frame options: the top row's titles and
   context buttons in the mid bar (`top_bars()`, `titled_bar()`), a label column next to the sidebar,
   further sections with `section()` or small frames (`panel(pillar=...)`, `outward_pair()`); see
   "Page frame" and `ops_view()` / `status_view()` as examples.
2. Add `(key, label, lcars_code("view/<key>"), colour, "<section>-<name>")` to
   that section's sub-view list in `SECTIONS`.
3. Add `view("<section>", key, "LCARS …", "<section>-<name>", subtitle="Subtitle", **my_view())`
   to `VIEWS`.
4. Run `python3 tools/deploy.py` (it validates before saving) and check both
   target screens.

### Adding a new section

Do the above, then also add a `SECTIONS` entry, put its key in `NAV_ORDER` and
add a branch in `section_readouts()`.

## Migration plan (proposal, not decided)

Next step: move the other pages to the page frame. Nothing below is decided yet;
each row is a starting point to try and screenshot, as with the Media concepts.

**Groundwork first**

1. **One column spec for bar and content.** Done: `top_bars()` (Media and OPS;
   Media's widths are unchanged).
2. **Thickness everywhere.** Done: the nav bar is `NAV_H` 43 px on every page,
   the Calendar section included.
3. **Titles in inner frames.** Put `panel()` and `s_joint()` titles through
   `title_text()` too, so every title in a bar is centred the same way.
4. **Inner frames stay.** Only the top row of a page merges into the mid bar.
   Frames further down keep their own brackets (`panel()`, facing frames, S
   joints) and the existing rules.
5. **Mid and foot corners.** With a thicker mid bar the mid and foot elbows no
   longer share their outer radius. Decide whether the foot follows.
6. **Colour families** (rule "One colour family per frame"). Done for the
   shared frame on every page (header blue/lilac, main frame orange, active
   item near-white) and for Media's content. Still to do, page by page: the
   inner frames, each in one family of its own (e.g. Aquarium Status' Equipment
   frame mixes ice, butterscotch, lilac and peri label blocks). The power
   trace's range buttons still mark the active range orange where the trace
   isn't migrated yet (Osmosis).

**Per page**

| Page | Titles in the mid bar | Context buttons in the bar | Right side | Notes |
|------|------|------|------|------|
| OPS | **done** (see Pages) | the radar's buttons | open | |
| Aquarium (all six pages) | **done** (see Pages) | | Visual, Light closed; the others open | |
| Laundry | **done** (see Pages) | none (Supply stays a switch row) | open | |
| Waste | **done** (see Pages) | none | open | |
| Calendar | **done** (see Pages): one view, own month card; agenda dropped | Back / Today / Next | closed (the legend) | |

## URL rules

- HA dashboard paths **must contain a hyphen**; HA rejects `lcars` ("Url path
  needs to contain a hyphen"). Hence `lcars-bridge`.
- A view path is a **single segment** (`/lcars-bridge/<view>`), so views are
  named `<section>-<view>`: `aquarium-power`, `aquarium-osmosis`.
- A dashboard's path can't be renamed. Moving means creating a new dashboard.
  The old `aquarium-lcars` still exists, hidden from the sidebar as
  "LCARS (alt)", until the user decides to delete it.
- Query parameters: `?lcars_motion=off|on|toggle` (per device),
  `?lcars_bars=off|on|toggle` (global, stored in HA: never in a start URL).
