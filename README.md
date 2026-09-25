# LCARS dashboard for Home Assistant

A full-screen LCARS dashboard (Voyager palette, Titan.DS-style layout) built from
[LCARdS](https://lcards.unimatrix01.ca) cards. It lives in the HA dashboard
`lcars-bridge` (sidebar title **LCARS**), e.g. `/lcars-bridge/aquarium-power`.

- The **header frame bar is the section menu**: OPS, Aquarium, Laundry, Waste, Calendar, Media.
- **Sidebar** lists the active section's sub-views. **Classic**, a link to the original dashboard,
  sits on top of the header frame's pillar.
- The **foot frame bar** ends in the local date/time and a **stardate** block.

| Section  | Sub-views |
|----------|-----------|
| Aquarium | Status, Visual, Light, Dosing, Power, Osmosis |
| OPS      | OPS (atmosphere, DWD radar, next 7 days, forecast) |
| Laundry  | Laundry (power trace 24 h / 7 d / 28 d, unit) |
| Waste    | Overview, Calendar |
| Calendar | Calendar, Agenda |
| Media    | Player (Spotify: now playing, transport, volume, output devices, library) |

Every view fills the viewport exactly, so pages never scroll. Header readouts
change per section. On every page, a pump failure in the aquarium replaces the
title with the alert.

## Layout

```
generator/build_dashboard.py   the whole dashboard as code -> build/lcars_dashboard.json
generator/ha_ws.py             stdlib-only HA WebSocket client
generator/site_config.py       loads site.yaml (host, location, device IDs, calendars)
site.example.yaml              template for site.yaml (git-ignored)
tools/validate.py              LCARdS schema + strict unknown-key check
tools/deploy.py                build -> validate -> back up live config -> save
tools/deploy_ha_files.sh       copy ha/ files to the HA host, reload themes, ?v=<timestamp> on the scripts
tools/gen_registry_fix.py      regenerate the registry workaround after an LCARdS update
tools/bump_resources.py        create/update the Lovelace resources of ha/www/*.js with ?v=<timestamp>
tools/screenshot/              headless screenshots at the target sizes (see docs/OPERATIONS.md)
ha/themes/lcars_aquarium.yaml  view theme "LCARS Aquarium"
ha/www/lcards-registry-fix.js  workaround for the LCARdS/HA load-order race
ha/www/lcars-motion.js         per-device animation switch (?lcars_motion=off, sidebar "Motion"),
                               global segment-bar switch (?lcars_bars=off)
ha/www/lcars-day-grid.js       the waste timeline's day grid as one light card (was ~200 LCARdS buttons)
ha/www/lcars-bar.js            segment bars (countdown, time window, level, span, status, weekdays) as light cards, CSS blink
ha/www/lcars-transporter.js    light channels as vertical transporter-console sliders (Light)
ha/www/lcars-phases.js         the light schedule over 24 h, a shape per phase with its ramps (Light)
ha/www/lcars-log.js            device log from HA's logbook with severity colours and a waterfall (Light)
ha/www/lcars-tank.js           a dosing bottle's fill level as a vertical segment tank (Dosing)
ha/www/lcars-week.js           next days of several calendars, timeline style (OPS)
ha/www/lcars-forecast.js       hourly forecast, LCARS style (OPS)
ha/www/lcars-radar.js          DWD precipitation radar with LCARS controls (OPS)
ha/www/lcars-player.js        Spotify player and library browser (Media)
ha/www/lcars-power.js          power chart over 24 h / 7 d / 28 d with range buttons (Laundry, Osmosis)
docs/DESIGN.md                 design rules (user decisions), generator structure, how to extend, URL rules
docs/OPERATIONS.md             changes made on the HA host, backups, tablet, sounds, known limitations
docs/NOTES.md                  root causes and LCARdS gotchas
```

**Read `docs/DESIGN.md` before changing the look.** It records decisions the
user already made and the reference style of the waste, OPS, laundry and aquarium pages (frames,
pillars, graphics next to values, restrained animation, both target screens).

## Usage

```bash
python3 tools/deploy.py                              # rebuild + validate + save
python3 tools/deploy.py --restore build/backups/X.json
tools/deploy_ha_files.sh                             # after editing anything in ha/
```

**Site settings** live in `site.yaml` (git-ignored): HA host and SSH login, the radar's location, the
device-derived parts of entity IDs, the personal calendars. Start from `cp site.example.yaml site.yaml`.
`HA_HOST` / `HA_PORT` / `HA_SSH` in the environment override it.

Credentials: `~/.config/homeassistant/token` (long-lived access token) and an SSH key for the login in
`site.yaml` (sudo without password on the host). Neither is stored in this repo.

**Rebuild after changing the source dashboards or the light schedule.** The Waste and
Calendar calendar cards are copied from the live `dashboard-muell` / `dashboard-termine`
configs at build time, and the light page's phase graph reads
`/config/aquarium_light_control.yaml` over SSH (needs PyYAML).

## Prerequisites on the HA side (state 2026-09-24)

- **LCARdS** 2026.9.0: HACS integration, config entry added. Log level is set in its options.
- **HA-LCARS** 4.1.3 theme (HACS) in `themes/lcars/lcars.yaml`. The profile theme is "LCARS Default".
- **UIX** 8.3.1 (HACS integration, config entry). **card-mod was removed**, because
  HA 2026.x broke it and UIX refuses setup while `card-mod.js` is a resource.
  UIX still honours existing `card_mod:` keys.
- **Helpers**: `input_boolean.lcars_bars` (segment bars on/off), `input_boolean.lcars_sound`, `input_boolean.lcars_texture`,
  `input_number.lcars_vertical` (26–60), `input_number.lcars_horizontal` (6–60),
  and Time & Date (`sensor.time`).
- **Lovelace resources**:
  - Antonio font (Google Fonts, css)
  - `https://cdn.jsdelivr.net/gh/th3jesta/ha-lcars@js-main/lcars.js` (js)
  - every `ha/www/*.js` as `/local/<file>?v=<timestamp>` (module; created/updated by `tools/deploy_ha_files.sh`)
- **kiosk-mode** hides the HA header and sidebar on this dashboard. Append
  `?disable_km` to the URL to reach edit mode.
- The view theme `LCARS Aquarium` (from `ha/themes/`) must be installed.
- **Sounds**: LCARdS helpers `input_boolean.lcards_sound_enabled` (master),
  `_cards` (on), `_ui` (off, so menu clicks don't double-beep), `_alerts` (on),
  `input_number.lcards_sound_volume` (0–1) and `input_select.lcards_sound_scheme`.
  The thelcars.com beeps live in HA's media library under `/media/lcars/`, not in
  this repo (no licence stated). `CLICK_SOUNDS` in the generator switches to them.
