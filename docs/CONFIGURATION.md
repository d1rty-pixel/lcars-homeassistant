# Configuration (`lcars.yaml`)

One YAML file describes a whole dashboard: how to reach Home Assistant, the sections of the menu, and
every view as a tree of components. `lcars init` writes a starting point from what your HA has;
[`examples/lcars.example.yaml`](../examples/lcars.example.yaml) has every setting, commented, and
[`examples/`](../examples/) a minimal and a complete configuration. The components themselves are described
in [COMPONENTS.md](COMPONENTS.md).

```yaml
homeassistant: {url: http://homeassistant.local:8123, files: {method: ssh, login: root@homeassistant.local}}
weather: weather.home
sections:
  - key: home
    label: Home
    readouts: [{type: readout, entity: weather.home, label: Outside, value: {attribute: temperature, unit: "°C"}}]
    views:
      - key: home
        label: Home
        bar: [{title: Atmosphere, colour: orange}]
        content:
          type: rows
          rows:
            - {label: Temperature, entity: weather.home, value: {attribute: temperature, unit: "°C"},
               bar: {mode: level, attribute: temperature, min: -10, max: 35}}
```

Mistakes are reported with their place in the file (`sections[0].views[1].content.items[2]: unknown
field(s) colr for type rows (fields: …)`), before anything is sent to HA.

## Top level

| Key | Meaning |
|-----|---------|
| `homeassistant` | how to reach HA (below) |
| `dashboard` | the dashboard's URL path, title, theme, sidebar entry (below) |
| `layout` | scrolling on phones (below) |
| `sections` | the section menu and its views (below); required |
| `alert` | alerts: the page frame turns the alert's colour and a dialog asks to acknowledge it (below) |
| `weather` | the default `weather.*` entity of `forecast` components (default `weather.home`) |
| `radar` | `home: [lat, lon]`, `width_km`, optional `center: [lat, lon]` for `radar` components (DWD: Germany) |
| `calendars` | the calendars of `week`, `month` and `next_event`: `[{entity, label, colour}]` or entity IDs; a calendar without a label gets its name in HA, one without a colour the next of a palette |
| `titles` | event titles to replace in calendars, e.g. `{"Recycling collection": "Recycling"}` |
| `numbers` | the header's number columns: `exclude: [parts of entity IDs]` or `sensors: [entity IDs]` |
| `sounds` | click sounds on every interactive LCARdS card, e.g. `{card_tap: <media URL>}`; default: LCARdS' own |
| `vars` | values to use elsewhere with `${{ vars.name }}` |
| `data` | data read when the dashboard is built (below) |
| `plugins` | Python files with component types of your own ([EXTENDING.md](EXTENDING.md)) |
| `header_code` | the text on the header's elbow (default `LCARS 47174`) |

### `homeassistant`

```yaml
homeassistant:
  url: http://homeassistant.local:8123      # or https://...; env HA_URL overrides it
  token_file: ~/.config/homeassistant/token # a long-lived access token; env HA_TOKEN overrides it
  files:                                    # how `lcars setup` copies the cards and the theme to HA
    method: ssh                             # ssh, local or none
    login: root@homeassistant.local         # ssh: user@host (env HA_SSH overrides it)
    options: ["-p", "22"]                   # ssh: extra options
    sudo: true                              # ssh: run cat/tee through sudo (default true)
    # config_dir: /config                   # where HA's configuration is on that host (local, ssh)
```

`files` is only needed for `lcars setup` / `lcars files` and for `data` read from the HA host.
[INSTALL.md](INSTALL.md#file-access) explains the three methods.

### `dashboard`

| Key | Default | Meaning |
|-----|---------|---------|
| `url_path` | `lcars-bridge` | the dashboard's path; HA needs a hyphen in it. `--dashboard` / env `LCARS_DASHBOARD` build for another one (e.g. a test copy) |
| `title` | `LCARS` | its title in HA's sidebar |
| `icon` | `mdi:star-four-points` | its icon there |
| `show_in_sidebar` | `true` | |
| `require_admin` | `false` | |
| `kiosk` | `true` | hide HA's header and sidebar (kiosk-mode; `?disable_km` in the URL shows them) |
| `theme` | `LCARS Bridge` | the view theme every view carries (`lcars setup` installs it under this name) |

`title`, `icon`, `show_in_sidebar` and `require_admin` apply when `lcars setup` creates the dashboard.

### `layout`

| Key | Default | Meaning |
|-----|---------|---------|
| `scroll` | `auto` | `auto`: on a viewport lower than `scroll_min_h` (a phone in landscape) the sidebar and the content scroll between the fixed header menu, mid bar and foot bar, and nothing is left out. `off`: no page ever scrolls; phones get a reduced placement (no header, the menu in the foot bar, content from lower tiers) |
| `scroll_min_h` | `520` | px of viewport height below which pages scroll |

Everything else about screen sizes is automatic: see "Responsive behaviour" in [COMPONENTS.md](COMPONENTS.md).

### `alert`

While an alert's `entity` is in one of its listed states, on every page:

- the page frame (elbows, bars, sidebar, foot bar, and the titles and clock in their gaps) turns the
  state's colour; the active menu item stays light, the content and the page title don't change;
- a dialog over the page shows the state's `heading` and `text`, with **Acknowledge** and **Details**
  (HA's more-info of the entity). Acknowledging closes it on every screen (the helper
  `input_text.lcars_alert_ack`, which `lcars setup` creates); another state, or the same state again
  later, asks again;
- the frame pulses while a state with `blink: true` is unacknowledged, and stays in its colour after
  that while the state lasts;
- each screen plays the state's `sound` once when it first shows the alert, and `alert_clear` when the
  last alert ends (LCARdS' sound scheme; its sound helpers switch it on or off).

```yaml
alert:
  - entity: binary_sensor.water_leak
    states:
      "on": {heading: Red alert, text: Water leak in the basement, colour: red, blink: true}
  - entity: sensor.filter_status
    states:
      Due: {text: "js:'Filter change due for ' + a.days + ' days'", colour: sunflower}
```

`alert` is a list (one alert may be given as a mapping). Several alerts can be active at once: the dialog
lists every unacknowledged one, the first active alert in the list colours the frame. Per state:

| Field | Default | |
|-------|---------|---|
| `heading` | by colour: `Red alert`, `Yellow alert` (sunflower), `Blue alert` (bluey, peri, ice), else `Alert` | the dialog's title |
| `text` | none | what happened |
| `colour` | `red` | frame and dialog |
| `blink` | `false` | the frame pulses until acknowledged |
| `sound` | by colour: `red`, `yellow` (sunflower), `blue` (bluey, peri, ice), `gray`, else `yellow` | LCARdS' `alert_<sound>`; `none`: silent |

`heading` and `text` may be JavaScript: `text: "js:'PUMP OFFLINE · ' + a.minutes + ' MIN'"` (`a` are
the entity's attributes, `s` its state). They are evaluated on every update, so they may count. Quote
states YAML would read as booleans (`"on"`, `"off"`). The former names `title` (now `text`) and `short`
(now `heading`) still work.

### `data`: values read when the dashboard is built

Some things no entity exposes, e.g. a schedule in a YAML file on the HA host. `data` names sources;
`${{ data.name... }}` uses them:

```yaml
data:
  light: {ha_file: /config/light_schedule.yaml}   # through homeassistant.files
  rooms: {file: rooms.yaml}                        # next to lcars.yaml
  api: {url: https://example.com/list.json, key: items}   # key: a part of it
  fixed: {value: [1, 2, 3]}
...
content: {type: schedule, phases: "${{ data.light.phases }}"}
```

A source is read once per build, and only when something uses it. Rebuild after it changes.

## Sections

A section is an entry of the section menu (the header's bar), with its views in the sidebar.

| Key | Default | Meaning |
|-----|---------|---------|
| `key` | required | its ID (also in its views' paths) |
| `label` | the key | its menu label |
| `short` | the label | its label in the phone's menu (short: phones have little room) |
| `title` | the label | the page title on its views |
| `colour` | the header's blues and lilacs in turn | its menu block |
| `link` | none | the header's top-left block links here, e.g. `{label: Classic, url: /lovelace/home}` (or just a URL); on phones the first block of the menu bar |
| `readouts` | none | up to four header entries next to the title: `readout`, `next_event`, `numbers`, `decor`, `empty` ([COMPONENTS.md](COMPONENTS.md#header)); a bare `numbers` means `{type: numbers}` |
| `views` | required | its views |

The menu shows the sections in their order; a menu entry opens the section's first view.

## Views

| Key | Default | Meaning |
|-----|---------|---------|
| `key` | required | its ID (unique over all sections) |
| `path` | the key (a section with one view), else `<section>-<key>` | the URL: `/<url_path>/<path>` |
| `label` | from the key | its sidebar block |
| `title` | `LCARS <label>` | the browser tab's title |
| `subtitle` | the label | under the page title, with the view's LCARS number |
| `label_width` | `150` | the page's label column in px at full size (every row, section bar and frame pillar of the page lines up with it) |
| `columns` | `[1fr]` | the top row's columns: CSS tracks (`1.5fr`), px (`160`), `label` or `decor`; the mid bar and a top-level `columns` component share them |
| `bar` | one piece titled with the subtitle | the mid bar's pieces over those columns (below) |
| `right` | open | closes the page frame on the right (below) |
| `content` | required | the component tree |

### The mid bar (`bar`)

The content's titles sit in the page frame's mid bar, a piece per column of the top row, split exactly
where the columns split at any width:

```yaml
columns: [1.1fr, 160, 1fr]
bar:
  - {title: Now playing, colour: orange, span: 2,                    # covers two columns
     buttons: {type: player, entity: media_player.x, part: transport}}   # a component in the bar
  - {title: Library, colour: almond, side: right}                    # title next to the right shoulder
```

`buttons_max: 330` keeps the buttons at most that wide (the bar runs on behind them). A piece without a
title and buttons is a plain piece of bar (e.g. over a spine column); with `drop: true` it reaches down
through the frame's inner curve to the content, so a spine below hangs from it.

### Closed on the right (`right`)

```yaml
right: {colour: almond, width: label, foot: ice}
```

A shoulder runs down from the mid bar and one up from the foot bar (`foot`: its colour, default
`colour`); the content brings the pillar between them at its right edge, exactly `width` wide
(`label`, `decor` or px): a right-hand label column, a component's `pillar`, a library's categories, a
month's legend. The header closes on the right to match.

## Values

A value (a row's `value`, a readout's, a `value` component's) is an LCARdS template, passed on as it is
(`{entity.state}`, or JavaScript in `[[[ ... ]]]` with `entity`, `states`, `hass`), or one of:

| Mapping | Shows |
|---------|-------|
| `{attribute: temperature, unit: "°C", round: 0}` | an attribute, rounded to `round` decimals if given |
| `{state: true, unit: W}` | the state with a unit |
| `{map: {on: Online, off: Offline}}` | the state (or `attribute`) through a map, others as they are |
| `{on_off: [Open, Closed]}` | `on` → the first, anything else → the second |
| `{above: 3, then: Running, else: Idle}` | a number compared with a threshold |
| `{date: state}` / `{date: next_due}` | a date (`yyyy-mm-dd…` or `dd.mm.yyyy`) as "Fri 25/09 · tomorrow"; `weekday: false` drops the weekday |
| `{time: next_setting}` | a timestamp as `hh:mm` |
| `{span: [next_rising, next_setting]}` | two timestamps as `hh:mm – hh:mm` |
| `{js: "return entity.state;"}` | JavaScript statements |

Without a value a row shows `{entity.state}` (LCARdS adds the unit).

## Colours

The Voyager palette by name: `orange`, `butterscotch`, `peach`, `almond`, `violet`, `lilac`, `bluey`,
`peri`, `ice`, `rose`, `red`, `sunflower`, `gray`, `green`, `earth`, `bone`, `ink`/`black`, `white`,
`dim`, `active`; or any CSS colour (`"#AAAACC"`, `rgba(...)`, `var(...)`). Where a colour carries a
state, give a map: `{Running: ice, Warning: sunflower, default: gray}`. Keep to one colour family per
frame ([DESIGN.md](DESIGN.md)); components that aren't given colours pick them from the orange family.

## Sizes

- **Widths** (`label_width`, `columns`, `widths`, `right.width`, `pillar.width`): `label` (the page's
  label column), `decor` (a decorative pillar), a number of px at full size, or CSS. In CSS, `{...}`
  holds a fluid size: `{fl(140)}` (140 px at full size, following the viewport height), `{label}`,
  `{decor}`, e.g. `"calc(clamp({fl(140)}, 11vw, 220px) + {label} + 16px)"`.
- **Heights** (`height` of any component, a matrix row's `height`): a number of data rows, `fill` (the
  rest), `{timeline: n}` (as high as a day timeline of n series with its shoulder, so charts and
  timelines line up across pages), or CSS.

Every size follows the viewport height: full size from 720 px up, smaller below (see
[DESIGN.md](DESIGN.md#responsive-sizes)). Write sizes this way, not as fixed px in CSS.

## `${{ ... }}` and `repeat`

Before the components are built, the file is expanded:

- `${{ path }}` in any string is replaced: `vars.name`, `env.NAME`, `data.name...`, or a `repeat`
  variable. A string that is only `${{ ... }}` becomes the value itself (a list, a mapping, a number).
  Paths index with `.key` or `[key]`; `[name=Daylight]` picks the list item whose `name` is Daylight;
  `| default` gives a value where the path doesn't exist: `${{ data.light.phases[name=Night].levels.red | 0 }}`.
- A list item `{repeat: {as: x, in: [...]}, item: {...}}` becomes one item per value, with
  `${{ x... }}` in the item replaced. It works in any list: rows, a matrix's columns, even views:

```yaml
vars:
  appliances: [{key: washer, name: Washer, power: sensor.washer_power}, {key: dryer, name: Dryer, power: sensor.dryer_power}]
...
views:
  - repeat: {as: a, in: "${{ vars.appliances }}"}
    item:
      key: ${{ a.key }}
      label: ${{ a.name }}
      content: {type: history, entity: "${{ a.power }}"}
```

## Commands and files

| Command | Does |
|---------|------|
| `lcars init [dir] --url URL` | writes a starting `lcars.yaml` from what HA has |
| `lcars doctor` | checks HA and the configuration (entities included), changes nothing |
| `lcars setup [--yes]` | installs and sets up what the dashboard needs ([INSTALL.md](INSTALL.md)) |
| `lcars files` | copies the cards and the theme again (after an update of the package or of LCARdS) |
| `lcars build` | writes `build/lcars_dashboard.json` next to `lcars.yaml`, lists entities HA doesn't have |
| `lcars deploy` | builds, validates against LCARdS' schema, backs the live dashboard up to `build/backups/`, saves |
| `lcars restore FILE` | saves a backup (or any built configuration) as the dashboard |
| `lcars diag` | adds a view that shows what a device's browser reports about its screen |

Options: `-c FILE` (default `./lcars.yaml`, or env `LCARS_CONFIG`), `--dashboard PATH` (work on another
dashboard, e.g. a hidden test copy). `LCARS_DEBUG=1` shows tracebacks.
