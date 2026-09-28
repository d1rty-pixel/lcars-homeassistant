# The light custom cards

Dense graphics (grids of cells, segment bars, calendars, charts, the radar) are small web components in
[`lcars/www/`](../lcars/www/) instead of hundreds of LCARdS buttons, which kiosk tablets' renderers
can't cope with. They are plain JavaScript without a build step or dependencies, take their colours
and sizes from their configuration, and honour the per-device motion switch. The framework writes
their configuration from the components ([COMPONENTS.md](COMPONENTS.md)); the complete configuration
each card takes is documented at the top of its file, so they work in any dashboard too, once
`lcars setup` (or `lcars files`) has installed them.

| Card | Component | What it draws |
|------|-----------|---------------|
| `lcars-bar` | a row's `bar`, `bar` | segment bars: countdown, time window, level, span, state, weekdays |
| `lcars-day-grid` | `timeline` | the next days as a grid, a row per series |
| `lcars-week` | `week` | the next days of several calendars |
| `lcars-month` | `month` | a month of several calendars with a legend; `mode: controls`: its buttons |
| `lcars-forecast` | `forecast` | an hourly or daily forecast; `mode: toggle`: the Hourly / Daily block |
| `lcars-radar` | `radar` | the DWD precipitation radar (Germany) with play / step controls |
| `lcars-history` | `history` | a sensor over 24 h / 7 d / 28 d from long-term statistics (also registered as `lcars-power`) |
| `lcars-distribution` | `distribution` | live power of several consumers as conduits with a wave, a total row by share |
| `lcars-energy` | `energy` | energy of several consumers per day or month as stacked columns |
| `lcars-schedule` | `schedule` | a day's schedule of phases over 24 h (also registered as `lcars-phases`) |
| `lcars-transporter` | `sliders` | vertical sliders for number, input_number and light entities |
| `lcars-log` | `log` | a device log from HA's logbook |
| `lcars-tank` | `tank` | a fill level as a stack of segments |
| `lcars-flow` | `matrix` | cards in columns that wrap into rows by their own width, each row with a label column |
| `lcars-player`, `lcars-library` | `player`, `library` | a media player and its library |
| `lcars-alert` | site `alert` | not drawn in the page: colours the page frame and shows the alert dialog |
| `lcars-motion.js` | (always) | not a card: the per-device motion switch (`?lcars_motion=`) and `?lcars_bars=` |
| `lcards-registry-fix.js` | (always) | not a card: works around a load-order race between LCARdS and HA ([NOTES.md](NOTES.md)) |

Using one by hand, e.g. in a standard dashboard:

```yaml
type: custom:lcars-bar
entity: sensor.temperature
mode: level
min: -10
max: 35
segments: 14
side: left
colour: "#FFCC99"
off: "rgba(153, 153, 255, 0.18)"
```

Conventions all cards share:

- **Sizes** follow the viewport height like the framework's (full size from 720 px, down to a minimum
  share at 400 px); the helpers `fluid()`, `sz()`, `fz()` at the top of each file are the same formula
  as `lcars/engine/sizes.py`. Keep them in step.
- **Phones** (below 520 px viewport height, a media query) hide the LCARS numbers; where a card must
  adapt to its own size (a tank, the flow), it uses a container query or a ResizeObserver instead.
- **Motion**: animations stop while `localStorage["lcars-motion"] === "off"`.
- **Sounds**: buttons in the cards play LCARdS' tap sound (`window.lcards.core.soundManager`), so the
  sound settings apply to them too.
- **Linked instances**: a card with local state (the radar's frame, the month shown) can be placed twice,
  once as buttons only (e.g. in the mid bar), linked through a `group` and window events.
- Each defines its element only if it isn't defined yet, so two copies of a card never break a page.
