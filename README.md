# LCARS dashboard for Home Assistant

A full-screen LCARS dashboard (Voyager palette, Titan.DS-style layout) built from
[LCARdS](https://lcards.unimatrix01.ca) cards. It lives in the HA dashboard
`lcars-bridge` (sidebar title **LCARS**), e.g. `/lcars-bridge/aquarium-power`.

- **Header row** switches sections: Aquarium, Home, Waschen, Müll, Kalender.
- **Sidebar** lists the active section's sub-views plus **Classic**, a link to the original dashboard.

| Section  | Sub-views |
|----------|-----------|
| Aquarium | Status, Visual, Light, Dosing, Power, Osmose |
| Home     | Home |
| Waschen  | Waschen |
| Müll     | Übersicht, Kalender |
| Kalender | Kalender, Agenda |

Every view fills the viewport exactly, so pages never scroll. Header readouts
change per section. On every page, a pump failure in the aquarium replaces the
title with the alert.

## Layout

```
generator/build_dashboard.py   the whole dashboard as code -> build/lcars_dashboard.json
generator/ha_ws.py             stdlib-only HA WebSocket client
tools/validate.py              LCARdS schema + strict unknown-key check
tools/deploy.py                build -> validate -> back up live config -> save
tools/deploy_ha_files.sh       copy ha/ files to the HA host, reload themes
tools/gen_registry_fix.py      regenerate the registry workaround after an LCARdS update
ha/themes/lcars_aquarium.yaml  view theme "LCARS Aquarium"
ha/www/lcards-registry-fix.js  workaround for the LCARdS/HA load-order race
docs/NOTES.md                  why things are the way they are (gotchas, root causes)
```

## Usage

```bash
python3 tools/deploy.py                              # rebuild + validate + save
python3 tools/deploy.py --restore build/backups/X.json
tools/deploy_ha_files.sh                             # after editing anything in ha/
```

Credentials: `~/.config/homeassistant/token` (long-lived access token) and SSH
as `hassio@homeassistant.local`. Neither is stored in this repo. Override the host with
`HA_HOST` / `HA_SSH`.

**Rebuild after changing the source dashboards.** The Müll and Kalender calendar
cards are copied from the live `dashboard-muell` / `dashboard-termine` configs at
build time.

## Prerequisites on the HA side (state 2026-09-24)

- **LCARdS** 2026.9.0: HACS integration, config entry added. Log level is set in its options.
- **HA-LCARS** 4.1.3 theme (HACS) in `themes/lcars/lcars.yaml`. The profile theme is "LCARS Default".
- **UIX** 8.3.1 (HACS integration, config entry). **card-mod was removed**, because
  HA 2026.x broke it and UIX refuses setup while `card-mod.js` is a resource.
  UIX still honours existing `card_mod:` keys.
- **Helpers**: `input_boolean.lcars_sound`, `input_boolean.lcars_texture`,
  `input_number.lcars_vertical` (26–60), `input_number.lcars_horizontal` (6–60),
  and Time & Date (`sensor.time`).
- **Lovelace resources**:
  - Antonio font (Google Fonts, css)
  - `https://cdn.jsdelivr.net/gh/th3jesta/ha-lcars@js-main/lcars.js` (js)
  - `/local/lcards-registry-fix.js?v=2` (module)
- **kiosk-mode** hides the HA header and sidebar on this dashboard. Append
  `?disable_km` to the URL to reach edit mode.
- The view theme `LCARS Aquarium` (from `ha/themes/`) must be installed.
