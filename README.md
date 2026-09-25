# LCARS dashboard for Home Assistant

A full-screen, Star Trek LCARS-style dashboard for Home Assistant, written **as code**. It uses the
Voyager palette and a Titan.DS-style layout. A Python generator builds the whole Lovelace config from
[LCARdS](https://github.com/snootched/lcards) cards plus a set of small custom cards, validates it, and
saves it to Home Assistant through the WebSocket API.

- **One frame on every page.** The header bar is the section menu, the sidebar lists the section's
  sub-views, and the foot bar ends in the local date/time and a stardate.
- **No scrolling, ever.** Every view fills the viewport exactly. Content that doesn't fit a short
  screen is left out rather than cut off (display priorities by viewport height).
- **Tablet-friendly.** Checked at 1920×1080 and 1280×800 (a 10" Android tablet running Fully Kiosk
  Browser). Dense graphics are light custom cards, not hundreds of LCARdS buttons, and every
  animation has a per-device off switch.

It is the dashboard of one real installation, published as a **reference implementation**. The
frame, the primitives, the custom cards and the tooling are generic. The views are built for the
original installation's devices, so expect to adapt `generator/build_dashboard.py` to your own
entities (see [Adapting it](#adapting-it-to-your-home)).

## What's in it

| Section  | Views | Built for | Setup |
|----------|-------|-----------|-------|
| OPS      | Atmosphere, precipitation radar, next 7 days, hourly forecast | a `weather.*` entity, `sun.sun`, DWD radar, calendars | [weather](docs/integrations/weather.md), [DWD radar](docs/integrations/dwd-radar.md), [calendars](docs/integrations/calendars.md) |
| Aquarium | Status, Visual, Light, Dosing, Power, Osmosis | custom aquarium integrations, Shelly plugs, a Chihiros BLE light, an ESPHome camera | [aquarium](docs/integrations/aquarium.md) |
| Laundry  | Laundry unit and power trace | a smart plug with power metering | [power metering](docs/integrations/power-metering.md) |
| Waste    | Collection timeline, next pickup per bin, calendar | Waste Collection Schedule | [waste collection](docs/integrations/waste-collection.md) |
| Calendar | Month calendar, agenda | `calendar.*` entities | [calendars](docs/integrations/calendars.md) |
| Media    | Spotify player and library browser | the built-in Spotify integration | [Spotify](docs/integrations/spotify.md) |

### Custom cards (`ha/www/`)

Plain web components with no build step and no dependencies. They take colours and sizes from the
generator's config, so they can be reused in any dashboard. The config each one takes is documented
at the top of its file.

| Card | What it does |
|------|--------------|
| `lcars-bar` | segment bars: countdown, time window, level, span, state, weekdays |
| `lcars-day-grid` | a timeline grid of days (e.g. waste collections) |
| `lcars-week` | the next days of several calendars, timeline style |
| `lcars-forecast` | hourly weather forecast |
| `lcars-radar` | DWD precipitation radar (Germany) with play/step controls |
| `lcars-power` | power chart over 24 h / 7 d / 28 d from long-term statistics |
| `lcars-transporter` | vertical "transporter console" sliders for `number` entities |
| `lcars-phases` | a light schedule over 24 h, one shape per phase |
| `lcars-log` | a device log from HA's logbook with severity colours |
| `lcars-tank` | a fill level as a vertical segment tank |
| `lcars-player`, `lcars-library` | media player with transport, progress, volume, output devices; media-browser library |
| `lcars-motion.js` | not a card: per-device animation switch (`?lcars_motion=off`), global bar switch |
| `lcards-registry-fix.js` | not a card: works around a load-order race between LCARdS and HA's element registry |

## Requirements

**Home Assistant** (tested with 2026.9):

- [LCARdS](https://github.com/snootched/lcards) (HACS integration; add its config entry)
- [HA-LCARS](https://github.com/th3jesta/ha-lcars) theme (HACS), with the helpers it asks for:
  `input_boolean.lcars_sound`, `input_boolean.lcars_texture`, `input_number.lcars_vertical` and
  `input_number.lcars_horizontal`
- [UIX](https://github.com/Lint-Free-Technology/uix) (HACS integration). **card-mod must not be a
  Lovelace resource at the same time**, since UIX refuses to set up while it is. UIX still honours
  existing `card_mod:` keys.
- [kiosk-mode](https://github.com/NemesisRE/kiosk-mode) (HACS). It hides HA's header and sidebar on this
  dashboard; append `?disable_km` to a URL to get them back.
- The **Time & Date** integration with `sensor.time`, which re-renders the clock and stardate every minute
- A helper **`input_boolean.lcars_bars`** (on), the global switch for the segment bars
- Lovelace resources:
  - the Antonio font: `https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&display=swap` (stylesheet)
  - HA-LCARS' `https://cdn.jsdelivr.net/gh/th3jesta/ha-lcars@js-main/lcars.js` (JavaScript module)
  - every `ha/www/*.js` (created by the deploy script, see below)
- Two cards used by single views are **not part of this repo**: `custom:timed-camera-card` (Aquarium
  Visual) and `custom:global-calendar-card` (the Waste calendar and Calendar views). Replace them with
  standard cards or drop those views.
- The integrations behind the views you keep (see the table above).

**Workstation:**

- Python 3.10+ with `PyYAML` and `jsonschema` (`pip install pyyaml jsonschema`)
- A Home Assistant **long-lived access token** (Profile → Security) in
  `~/.config/homeassistant/token` (mode 600)
- **SSH access to the HA host** with passwordless `sudo`, e.g. the "Advanced SSH & Web Terminal"
  add-on. It is used to copy the `ha/` files to `/config` and to read the light schedule at build
  time. Without it, copy the files by hand and drop the Light view.
- Optional: Node.js for the screenshot tool (`tools/screenshot/`)

## Installation

```bash
git clone https://github.com/d1rty-pixel/lcars-homeassistant.git
cd lcars-homeassistant
cp site.example.yaml site.yaml        # then edit it, see Configuration
mkdir -p ~/.config/homeassistant
echo "<your long-lived token>" > ~/.config/homeassistant/token && chmod 600 ~/.config/homeassistant/token
```

1. Install the HA requirements above and restart HA once for UIX.
2. Create a dashboard in HA (Settings → Dashboards → Add dashboard → "New dashboard from scratch")
   with the URL **`lcars-bridge`**. Dashboard paths must contain a hyphen, and the generator's links
   point to `/lcars-bridge/…` (`BASE` in the generator).
3. Copy the theme and scripts to HA and register the resources:
   ```bash
   tools/deploy_ha_files.sh
   ```
   This writes `ha/themes/lcars_aquarium.yaml` to `/config/themes/` and every `ha/www/*.js` to
   `/config/www/`, reloads the themes, and creates or updates a Lovelace module resource
   `/local/<file>?v=<timestamp>` for each script, so browsers fetch the new version.
4. Adapt the generator to your entities (next section), then build, validate and save the dashboard:
   ```bash
   python3 tools/deploy.py
   ```
5. Open `/lcars-bridge/ops` (or any view) and reload the page once.

## Configuration

### `site.yaml`

Everything that identifies one installation lives in `site.yaml`, which git ignores.
`site.example.yaml` is the template:

| Key | Meaning |
|-----|---------|
| `ha.host`, `ha.port` | HA address for the WebSocket and REST APIs |
| `ha.ssh` | SSH login with passwordless sudo on the HA host |
| `radar.center`, `radar.home`, `radar.width_km` | map centre, home marker (lat, lon) and map width of the radar |
| `devices.pump_plug`, `devices.light`, `devices.light_area` | the device-derived parts of some entity IDs (serials, MACs, area prefix) |
| `calendars` | calendars besides the waste calendars (OPS "Next 7 days", Calendar header) |

The environment variables `HA_HOST`, `HA_PORT` and `HA_SSH` override the file.

### In the generator

The rest of the configuration is code at the top of `generator/build_dashboard.py` and in each
view's `*_content()` function:

- **Entity IDs**, e.g. `WEATHER`, `WASH`, `OSMO`, `BINS`, `POWER_GRID`, `DOSE_CHANNELS`. The Spotify
  player is found at build time (the first `media_player.spotify*`).
- **Sections and views**: `SECTIONS` (menu entries, sub-views, colours, "Classic" link), `NAV_ORDER`,
  `SECTION_TITLES`, `VIEWS`
- **Palette**: hex constants (`ORANGE`, `PEACH`, `LILAC`, …). They are hex on purpose, so LCARdS alert
  modes don't shift them.
- **Display priorities**: `PRIORITY_MIN_H` maps a priority to the minimum viewport height it needs
- **Click sounds**: `CLICK_SOUNDS`. `None` uses LCARdS' built-in scheme.

The Waste and Calendar views copy their calendar cards from two other dashboards at build time
(`foreign_card("dashboard-muell", …)` and `foreign_card("dashboard-termine", …)`). Point these at your
own dashboards or replace them.

### Adapting it to your home

1. Keep the frame and the helpers (`frame()`, `panel()`, `pillar_rows()`, `value_text()`, the bar
   helpers). Remove the sections you don't need from `SECTIONS`, `NAV_ORDER` and `VIEWS`.
2. For a new view, write a `my_content()` function that returns a layout grid of `panel()`s, add it to
   its section's sub-view list in `SECTIONS`, and add a `view(...)` entry to `VIEWS`.
3. For a new section, also add a branch in `section_readouts()` for its header values.
4. Run `python3 tools/deploy.py`, then check the result at your target screen sizes.

[`docs/DESIGN.md`](docs/DESIGN.md) describes the design rules, the page layouts and the generator's
structure in detail. [`docs/NOTES.md`](docs/NOTES.md) lists LCARdS gotchas and their workarounds.
[`docs/integrations/`](docs/integrations/) explains how each integration is set up and what the views
expect from it.

## Usage

```bash
python3 tools/deploy.py                                  # rebuild, validate, back up the live config, save
python3 tools/deploy.py --restore build/backups/X.json   # put a previous config back
tools/deploy_ha_files.sh                                 # after changing anything in ha/
python3 tools/gen_registry_fix.py                        # after every LCARdS update, then deploy_ha_files.sh
```

- `tools/validate.py` checks every LCARdS card against the official LCARdS JSON schema and also
  rejects unknown keys, which the schema alone would let through. `deploy.py` runs it and refuses to
  save a config that fails.
- Before every save, the live dashboard config is written to `build/backups/` (git-ignored).
- **Rebuild** after changing the light schedule or the source dashboards of the copied calendar cards.
  Both are read at build time.

URL parameters:

| Parameter | Effect |
|-----------|--------|
| `?lcars_motion=off\|on\|toggle` | animations off/on **for this browser** (stored in localStorage). The sidebar's "Motion" block toggles it. Recommended on tablets. |
| `?lcars_bars=off\|on\|toggle` | segment bars off/on **for everyone** (sets `input_boolean.lcars_bars`). Never put it in a kiosk start URL. |
| `?disable_km` | show HA's header and sidebar (kiosk-mode), e.g. to edit |

## Kiosk tablets

- Use a non-admin HA user for wall screens. Set the start page in the kiosk browser (for Fully Kiosk:
  Settings → Web Content Settings → Start URL), e.g. `https://<your-ha>/lcars-bridge/ops?lcars_motion=off`.
- Don't give the LCARS theme to a user as their **profile** theme if they also use other dashboards.
  Every view here carries its own view theme ("LCARS Aquarium"), so no profile theme is needed.
- Sounds play only after the first touch. If a tablet stays silent, allow media playback in the kiosk
  browser's settings.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| "Custom element doesn't exist" / configuration errors on every card, especially through a reverse proxy | LCARdS sometimes registers its elements before HA's scoped registry polyfill is installed. `lcards-registry-fix.js` re-registers them. Regenerate it with `tools/gen_registry_fix.py` after an LCARdS update. |
| Standard cards (calendar, weather) look lavender | The HA-LCARS card styles leaked in. The view theme must be "LCARS Aquarium" (`ha/themes/`), which declares its own UIX theme. |
| Content grows past the screen | LCARdS presets set a min-height. The generator's `finalize()` rewrites `Nfr` to `minmax(0,Nfr)` and sets `min_height: 0`. Keep calling it. |
| Page half-rendered after a deploy | Frontend state. Hard-reload the page (Ctrl+Shift+R). |
| Tablet renderer crashes | Turn animations off (`?lcars_motion=off`) and avoid pages with hundreds of LCARdS buttons. Use a light custom card instead. |
| `deploy_ha_files.sh` or the build fails with "Permission denied (publickey)" | The SSH key for `ha.ssh` isn't loaded (`ssh-add`). |

More root causes in [`docs/NOTES.md`](docs/NOTES.md). Operational notes (screenshots, sounds, known
limitations) are in [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Repository layout

```
generator/build_dashboard.py   the whole dashboard as code -> build/lcars_dashboard.json
generator/ha_ws.py             stdlib-only HA WebSocket client
generator/site_config.py       loads site.yaml (host, location, device IDs, calendars)
site.example.yaml              template for site.yaml (git-ignored)
tools/validate.py              LCARdS schema + strict unknown-key check
tools/deploy.py                build -> validate -> back up live config -> save
tools/deploy_ha_files.sh       copy ha/ files to the HA host, reload themes, bump resource versions
tools/bump_resources.py        create/update the Lovelace resources of ha/www/*.js with ?v=<timestamp>
tools/gen_registry_fix.py      regenerate the registry workaround after an LCARdS update
tools/screenshot/              headless screenshots at the target sizes (see docs/OPERATIONS.md)
ha/themes/lcars_aquarium.yaml  the view theme "LCARS Aquarium"
ha/www/*.js                    the custom cards and helper scripts
docs/DESIGN.md                 design rules, page layouts, generator structure
docs/NOTES.md                  root causes and LCARdS gotchas
docs/OPERATIONS.md             screenshots, sounds, known limitations
docs/integrations/             setup notes per integration (Spotify, DWD radar, weather, ...)
```

A git-ignored `CLAUDE.local.md` (or any other ignored file) can hold notes about your own installation.

## Credits

- [LCARdS](https://github.com/snootched/lcards) by snootched: the frame, buttons, elbows, charts and sounds
- [HA-LCARS](https://github.com/th3jesta/ha-lcars) by th3jesta: the theme and `lcars.js`
- Radar data and borders: [Deutscher Wetterdienst](https://www.dwd.de) (GeoServer WMS/WFS)
- The layout is inspired by [Titan.DS](https://www.mewho.com/titan/)

LCARS and Star Trek are trademarks of CBS Studios / Paramount. This is an unofficial fan project with
no affiliation.
