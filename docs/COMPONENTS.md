# Components

A view's `content` is a tree of components: layout components arrange frames and columns, data
components show values, charts and controls. Each is a mapping with a `type`. Unknown fields are
errors, so typos show up when you build.

Contents: [common fields](#fields-every-component-has) · [responsive behaviour](#responsive-behaviour) ·
layout: [rows](#rows) [stack](#stack) [columns](#columns) [section](#section) [frame](#frame)
[split](#split) [pair](#pair) [chain](#chain) [matrix](#matrix) [grid](#grid) [card](#card)
[blank](#blank) · data: [value](#value) [bar](#bar) [pills](#pills) [timeline](#timeline) [week](#week)
[month](#month) [forecast](#forecast) [radar](#radar) [history](#history) [chart](#chart)
[sliders](#sliders) [schedule](#schedule) [log](#log) [tank](#tank) [player](#player)
[library](#library) · [header](#header)

The look follows the design rules in [DESIGN.md](DESIGN.md): one label column per page, titles in
bars, frames that face outwards, one colour family per frame. The components apply them;
[`examples/home.yaml`](../examples/home.yaml) combines every one of them.

## Fields every component has

| Field | Meaning |
|-------|---------|
| `show_from` | the lowest screen tier it is rendered at (below) |
| `phone` | `false`: not rendered on phones |
| `height` | its height where it sits in a `stack`, `split` or `columns`: data rows, `fill`, `{timeline: n}` or CSS ([sizes](CONFIGURATION.md#sizes)) |
| `pillar` | a pillar of numbered blocks without a function beside it: `{colours: [...], side: right, filler: <colour>, width: decor, rows: false}`; `rows: true` makes the blocks one data row high (part of a label column), the filler takes the rest. A frame around it uses it as its pillar |
| `margin` | CSS margin within its cell |
| `key` | the key its LCARS numbers derive from (default: from where it is); the same key gives the same number everywhere |

## Responsive behaviour

The same configuration serves every screen. Sizes follow the viewport height by themselves; what
changes by screen is *placement*, by **tiers** (display priorities):

| Tier | Viewport height | Typically |
|------|-----------------|-----------|
| 0 | any (the fallback) | phones, with `layout.scroll: off` |
| 1 | ≥ 520 px | tablets in landscape with system bars, small laptops |
| 2 | ≥ 760 px | a 1280×800 tablet |
| 3 | ≥ 880 px | |
| 4 | ≥ 1000 px | desktops (1920×1080); **phones with `scroll: auto`**: they scroll, so they get everything |

- `show_from: 3` renders a component only from tier 3 up. Content that doesn't fit is not rendered,
  rather than cut off or squeezed.
- Numbers can differ by tier: `rows: {1: 1, 3: 2, 4: 3}` (from tier 1: 1, from 3: 2, from 4: 3; the
  lowest also below).
- `split` and `pair` draw their shoulders from tier 2 (`shoulders_from`); below it, frames give way to
  flat section bars, which cost less height.
- Phones (below 520 px) also get what their *width* needs: `pills` with `phone_layout`, `tank`s drop
  their scale when small, LCARS numbers are hidden.

A component renders every tier it needs and only the distinct variants end up in the dashboard; HA
doesn't create the cards of a variant that isn't shown, so variants cost nothing on the device.

## Layout

### rows

A label column: a label block per row (the frame's pillar), the value beside it, and beside that a
segment bar or nothing.

```yaml
type: rows
side: left            # where the labels are (right: a pillar on the right edge)
filler: peach         # continues the pillar below the last row (to a frame's shoulder)
label_width: 130      # default: the view's label_width
rows:
  - label: Temperature
    colour: peach                       # default: peach, almond, butterscotch in turn
    entity: weather.home
    value: {attribute: temperature, unit: "°C"}
    value_colour: {Warning: sunflower}  # a colour or a state map (default peri)
    bar: {mode: level, attribute: temperature, min: -10, max: 35}
  - {label: Supply, entity: switch.washer, value: {on_off: ["On", "Off"]}, hold: toggle}
  - {label: Record, content: {type: pills, items: [...]}}   # a component instead of value and bar
```

Row fields: `label`, `colour`, `entity`, `value` ([values](CONFIGURATION.md#values)), `value_colour`,
`bar` (below), `tap` / `hold` (actions of the block and the value: `toggle`, `more-info`, `none`,
`navigate:/path`, `url:https://...`, or an action mapping such as
`{service: script.turn_on, target: {entity_id: script.x}}`), `triggers` (other entities the value
reads, so it re-renders), `content`, `key`, `show_from`.

A switch (a row with `tap: toggle`) gets no bar: bars are for readings.

**Bars** (`bar:` of a row, or the `bar` component) are segment bars (`lcars-bar.js`), lit segments
briefly flashing white. `bar: countdown` is short for `{mode: countdown}`.

| Mode | Lights | Fields |
|------|--------|--------|
| `level` | a number on a scale | `min`, `max`, `attribute`, `alarm: {below, colour}` |
| `countdown` | days until a date (state or `attribute`), 2 days per segment | `days_per_segment` |
| `window` | the hours of a `HH:MM - HH:MM` state on a 24 h scale | |
| `span` | the hours between two timestamps (`start`, `end` attributes), e.g. daylight | `start`, `end` |
| `state` | every segment in the state's colour (`states: {on: ice}`), none for other states | `states`, `threshold` (a number above it is `on`) |
| `days` | weekdays listed in `attribute` (0 = Monday) | `labels: [M, T, W, T, F, S, S]` |

All modes: `segments` (default 14; 24 for window/span, 7 for days), `colour` (default the row's),
`states` (lit colour per state). Everyone can switch the bars off with `?lcars_bars=off` (they are
drawn only while `input_boolean.lcars_bars` is on).

### stack

Children one under the other, each as high as it needs (or its `height`), the ones without a height
or with `height: fill` sharing the rest. When all have a fixed height, the rest stays black. `gap`: `section` (default, the gap
between sections of a label column), `frame`, `none`, or CSS.

```yaml
type: stack
items:
  - {type: rows, rows: [...]}
  - {type: section, title: Power trace, height: {timeline: 5}, content: {type: history, entity: sensor.x_power}}
```

### columns

Children side by side. `widths`: CSS tracks, px, `label` or `decor` (default: the view's `columns` when
the counts match, else equal). A child that needs less height than the row stands at the top and the
rest stays black. As the view's content, the columns line up with the mid bar's pieces.

### section

A section of the page's label column: a bar that grows out of the column carrying the title, then the
content. `title`, `colour`, `side`, `content`. Use sections to continue one label column down the page
(one colour family each).

### frame

Content in its own LCARS bracket (an inner frame): a pillar on `side` with shoulders at the ends that
have a bar, the title in the top bar.

```yaml
type: frame
title: Next 7 days
colour: bluey
side: left
bottom: false       # open at the bottom (top: false also moves the title to the bottom bar)
content: {type: week}
```

The pillar is the content's own where it brings one on that side (a label column, a `pillar`, a week's
calendar blocks), exactly as wide; otherwise a thin plain one. `rows`: its height in data rows (for
`chain`s; may be per tier). `caption: false` drops a bottom title; `join_top: true` runs the content's
first pillar piece into the top shoulder.

### split

A top part closed below by a thin bar with a shoulder, and a bottom part (usually a frame, or a `pair`)
whose top shoulder faces it, a frame gap apart. `colour`: the closing bar's (default the top part's
colour). Below `shoulders_from` (default tier 2) the closing bar becomes a section gap and the frames
below flat section bars. A bottom part not shown (`show_from`) leaves the top alone, closed below if it
has a height of its own.

```yaml
type: split
colour: lilac
top: {type: stack, items: [...]}
bottom: {type: frame, title: Next 7 days, colour: bluey, bottom: false, show_from: 1, content: {type: week}}
```

### pair

Two frames side by side that face outwards: pillars on the outer edges, their top bars meeting as one
line, a *spine* of numbered blocks between them (one per data row; a pillar in the middle of a page
looks cut off).

```yaml
type: pair
spine: [peach, bone, almond, bone]      # colours in turn
left:  {type: frame, title: Next per bin, colour: peach, content: {type: rows, rows: [...]}}
right: {type: frame, title: Hazmat collection, colour: red, side: right,
        content: {type: rows, side: right, rows: [...]}}
```

With `top: {left, right, colour, spine}` a row of two parts (e.g. a label column and a block of pills)
stands above the frames, closed below by thin bars with shoulders on both sides, and the spine runs
through the whole page. `close_left: true` closes the left frame below into the spine. The frames are
open at the bottom unless they say `bottom: true`. `link`: the colour of the spine's piece in the
shared line.

### chain

Frames joined into an S (or a double S): each frame's bottom shoulder and the next one's top shoulder
sit on one bar that carries the next frame's title. Give the frames alternating `side`s. The first
frame's title belongs in the mid bar. Every frame but the last needs `rows`; the last takes the rest
(open above the foot bar), or with `rows` is closed below. A frame that isn't shown (`show_from`, `phone:
false`) ends the chain at the one before it.

```yaml
type: chain
items:
  - {type: frame, title: Phase control, colour: sunflower, rows: {0: 4, 1: 5}, content: ...}
  - {type: frame, title: Controls, colour: rose, side: right, rows: 2, content: ...}
  - {type: frame, title: Device log, colour: lilac, show_from: 3, phone: false, content: ...}
```

### matrix

A frame per column (a device's channels, several tanks, …) whose cells line up with one label column of
row names beside them. The frames sit side by side while each gets its whole title and wrap into even
rows (2 × 2, …) otherwise, each row with its own label column (`lcars-flow.js`, by its own width).

```yaml
type: matrix
rows:
  - {key: level, label: Level, colour: almond, height: fill}   # data rows or fill
  - {key: days, label: Remaining, colour: butterscotch, show_from: 1}
columns:
  - title: Rain water
    colour: ice                   # side alternates right/left unless given
    cells:
      level: {type: tank, entity: sensor.cistern_level, capacity: 5000, unit: l}
      days: {type: value, entity: sensor.cistern_days_left}
head: orange   # the label column's top piece
foot: earth    # its filler
min_rows: 3    # the fill rows get at least this many data rows once the frames wrap
```

### grid

A CSS grid for arrangements the others don't cover: `areas` (a string or a list of rows), `columns`,
`rows` (lists take widths / heights), `gap`, `items` (components with an `area`).

### card

Any other Lovelace card, e.g. a camera: `{type: card, card: {type: picture-entity, entity: camera.x}}`.
It gets a black, borderless style through UIX where UIX is installed (`plain: true` leaves it alone).

### blank

Black space.

## Data

### value

A single value (e.g. a matrix cell): `entity`, `value`, `colour` (a colour or a state map), `align`
(`center`, `left`, `right`), `triggers`, `tap`, `hold`.

### bar

A segment bar on its own: `entity` and the bar fields above, `side`.

### pills

LCARS pills in a grid.

```yaml
type: pills
columns: 3
size: 14                                  # label font size (px at full size)
items:
  - {label: Heating, entity: input_boolean.heating, "on": ice, "off": gray}     # a switch, coloured by state
  - {label: Evening, colour: butterscotch, tap: {service: scene.turn_on, target: {entity_id: scene.evening}}}
  - {label: Refill, colour: peach, entity: number.x, hold: {service: number.set_value,
     target: {entity_id: number.x}, data: {value: 500}}}                 # hold, on purpose
  - {decor: peach}                        # a numbered pill without a function
phone_layout: {columns: 1, decor: false, rows: data}   # on phones: one column, no decor pills, data-row high
```

`phone_layout` fields: `columns`, `decor: false`, `limit` (the first n pills), `rows: data`, `narrow:
true` (no numbers, smaller insets), `gap`. `widths`: the columns' CSS widths. A label may be a template
(`"[[[ return entity.state === 'on' ? 'Auto' : 'Manual'; ]]]"`).

### timeline

The next `days` days (default 28) as a grid, a row per series with a cell lit on each day with an
event, its label blocks as the frame's pillar (`lcars-day-grid.js`).

```yaml
type: timeline
series:
  - {label: Residual, entity: sensor.waste_residual, colour: "#AAAACC"}           # match: attribute
  - {label: Hazmat, entity: sensor.hazmat_date, colour: red, match: state}
```

`match: attribute` (default): the entity has an attribute per date (`yyyy-mm-dd` keys, as Waste
Collection Schedule's sensors have by default, `details_format: upcoming`); `match: state`: its state is
the date. `head`,
`axis`, `axis_label`: the pillar's top and bottom pieces.

### week

The next days of several calendars (`lcars-week.js`): a label block per calendar with events, a column
per day, events in the calendar's colour. `calendars` (default all of the site's), `days` (7), `rows`
(most calendars shown; per tier), `filler` (the column's colour), `side`. Before each fetch it asks HA
to refresh the calendars (Google calendars lag otherwise).

### month

A month of several calendars (`lcars-month.js`): ISO week blocks as the label column, a 6 × 7 grid,
events as bars, a legend of calendars as the frame's right side (close the view on the right with
`width: label`). `mode: controls` shows only Back / Today / Next (in the mid bar:
`buttons: {type: month, mode: controls}`), linked by `group`. `legend`, `weeks` (colours).
On phones the week column is narrow (64 px: the month and "WK 36" only), the rows are 72 px high (the
page scrolls) and events take up to two lines in small text, as many as fit, "+n" for the rest.

### forecast

A weather forecast (`lcars-forecast.js`): hourly or daily columns with condition, a temperature bar, °C
and precipitation. `entity` (default the site's `weather`); `labels: [colour, colour]` puts "Time" and
"Temp · Rain" blocks beside its rows as part of the label column, with an Hourly / Daily switch
(`toggle` colour) below them, stored per device; `min_rows`: data rows it needs where the page scrolls.

### radar

The DWD precipitation radar (`lcars-radar.js`; **Germany only**): 60 min back to 90 min ahead, looped,
borders drawn from DWD's WFS when the dashboard is built. Needs the site's `radar`. `controls`:
`pillar` (the map with its own buttons), `none` (the map only) or `row` (only Play / Back / Next / Now,
e.g. `buttons` in the mid bar; `none` and `row` on one view are linked). `filler`, `buttons` (colours).

### history

A sensor over 24 h / 7 d / 28 d from HA's long-term statistics (`lcars-history.js`), so the sensor
needs a `state_class`. Its range buttons continue the label column (`column: true`, default; put it in
a `section`) or form a pillar of their own. `scale`: `log` (default, for values across magnitudes like
power) or `linear` (`min`, `max`); `ticks`, `unit` (default the entity's), `stat` (`max`, `mean`,
`min`), `buttons`, `filler`, `colour`.

### chart

Several sensors over the last hours as an LCARdS chart, mirrored around a zero line: `sign: 1` above,
`-1` below (a total above, its parts below), on a log scale with labelled lines.

```yaml
type: chart
ticks: [10, 100]
unit: W
hours: 24
series:
  - {entity: sensor.house_power, name: House, colour: orange, sign: 1}
  - {entity: sensor.heat_pump_power, name: Heat pump, colour: ice, sign: -1}
```

### distribution

The live power of several consumers as EPS conduits (`lcars-distribution.js`): a row per consumer, its
label block part of the label column, the value, a conduit of `segments` (32) lit on a log scale up to
`max` (2500 W), with a calm wave of brightened segments running outward, faster the higher the load, and the
consumer's share of the total at the far end. A `total` row (its label, default `Total`; `null`: none;
`total_colour`, default bone) on top lights every segment in the consumers' colours by their share,
and counts the consumers drawing power. Tap a row: more-info.

```yaml
type: distribution
consumers:                   # entity: the power sensor (W or kW); energy: used by `energy`
  - {entity: sensor.desk_power, energy: sensor.desk_energy, label: Desk, colour: orange}
  - {entity: sensor.fridge_power, energy: sensor.fridge_energy, label: Fridge, colour: ice}
```

### energy

The energy of several consumers per day or month as stacked columns in their colours (`lcars-energy.js`),
from HA's long-term statistics (the sensors need a `state_class`). `series`: the same list as a
`distribution` (each consumer's `energy`, else its `entity`). The line above the columns reads the
range's total, the mean of the finished periods and the running one; tap a column for its breakdown.
The running period's top piece lights up now and then; the columns rise when the range changes. A
toggle block below the range buttons (`toggle`: its colour, default bluey; `null`: none) switches to a
**graph**: the mean load in W per hour (per day for months), each consumer a smooth area on a log scale
above a zero line, their total mirrored below it (`total`: its colour, default bone), revealed from the
left; tap it for the breakdown at that time. The choice of range and view is stored per device. Its
range buttons continue the label column (put it in a `section`): `ranges` (default `7D`, `28D` as days,
`12M` as months: `[{label, days | months}]`), `buttons` (a colour per range), `filler`, `unit` (kWh),
`min_rows` (its height where the page scrolls, in data rows; 7).

### sliders

Vertical sliders like the TNG transporter console (`lcars-transporter.js`): drag or tap, sent when the
finger lifts. `channels: [{entity, label, colour}]` of `number`, `input_number` or `light` entities
(lights: brightness in %, 0 turns off); `min`, `max`, `step`, `segments`.

### schedule

A day's schedule of phases over 24 h (`lcars-schedule.js`), e.g. a light's day and night or heating
periods: a smooth shape per phase rising over its ramp-up and falling over its ramp-down, a line at the
time now.

```yaml
type: schedule
phases:
  - {name: Day, start: "07:00", end: "21:00", ramp_up_minutes: 30, ramp_down_minutes: 60, level: 100, colour: sunflower}
  - {name: Night, start: "21:00", end: "23:30", levels: {red: 10, blue: 20}, colour: bluey}
```

The phases may come from a file on the HA host (`phases: "${{ data.x.phases }}"`, see `data` in
[CONFIGURATION.md](CONFIGURATION.md)). `colours: {phase: colour}` for phases without one; `min_share`:
the lowest a phase is drawn.

### log

A device log from HA's logbook (`lcars-log.js`): newest first, as many lines as fit, coloured by level,
availability flaps collapsed, a colour waterfall.

```yaml
type: log
levels: {info: peri, ok: ice, warn: sunflower, error: red}
sources:
  - entity: switch.pump
    tag: Pump
    states:
      "on": [Running, ok, Circulation nominal]
      "off": [Stopped, error, Circulation offline]
    details: {flap: Link interruption, offline: Link lost, online: "Link restored after {d}"}
  - {entity: sensor.ble_notification, tag: BLE, burst: true, default: [null, info, Frames received]}
```

`hours`, `refresh_s`, `flap_s`, `burst_s`, `max_lines`, `dates` (`past`: the date only on lines before today, default; `always`).

### tank

A fill level as a stack of segments with a scale and a pointer (`lcars-tank.js`): `entity`,
`capacity`, `low` (red below), `unit` (default the entity's), `colour`, `segments`; `status` +
`status_attributes: {capacity: attr, low: attr}` take capacity and low from another entity. Small
tanks (by their own size) drop the scale.

### player

A media player (`lcars-player.js`). `part`: `now` (cover, track, progress, volume), `devices` (the
output devices as a button column), `transport` (Play/Pause, Back, Next, Shuffle, Repeat, e.g. in the
mid bar), `full` (all in one). `entity` may be a pattern (`media_player.spotify_*`, the first match when
building). `name`: the service's name in status texts ("Spotify refused · Repeat"). Players that need
an active output device first (Spotify Connect) are woken on Play.

### library

The player's media library (`lcars-library`): categories as a pillar on the right (the frame's right
side), rows that play on tap. `categories: [{match, label, colour, pinned}]`: `match` is the end of a
root entry's `media_content_id` (`""` matches the first), `pinned` lists other root entries shown first
as one playable row (Spotify's Liked songs). `name` as for the player.

## Header

A section's `readouts` (up to four slots next to the page title):

| Type | Shows | Fields |
|------|-------|--------|
| `readout` | a label over a large value | `entity`, `label`, `value`, `colour` (colour or state map), `span`, `triggers`, `width` |
| `next_event` | the calendars' next event; `when`: today, tomorrow, weekday and date within a week, else the date | `label`, `show: title / when / today`, `calendars`, `colour`, `width` (default 1.6 / 1.2 / 0.5) |
| `numbers` | LCARS number columns: real sensors as hex codes with a colour waterfall | `colours` (site `numbers` picks the sensors) |
| `decor` | a 2 × 2 block of numbered pills, on screens ≥ 1600 px wide | |
| `empty` | an empty slot | |

`width`: the slot's share of the header's width (a slot is 1). A value too long for its slot is cut at
the slot's edge rather than running into the next one.
