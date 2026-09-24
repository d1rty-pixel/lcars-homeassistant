# Operations: HA-side state, changes made, known limitations

## Changes made on the HA host while building this (2026-09-24)

| What | Detail | Reversible via |
|------|--------|----------------|
| LCARdS config entry | Created (the integration was only downloaded). Log level `warn`; it was temporarily `debug` while debugging. | integration options |
| Time & Date | Config entry with `sensor.time` (re-renders the foot bar's clock and stardate every minute, and the Calendar readouts) | integration |
| HA-LCARS helpers | `input_boolean.lcars_sound`, `input_boolean.lcars_texture`, `input_number.lcars_vertical`, `input_number.lcars_horizontal` | helpers UI |
| LCARdS sound helpers | `input_boolean.lcards_sound_enabled/_cards/_ui/_alerts`, `input_number.lcards_sound_volume`, `input_select.lcards_sound_scheme` | helpers UI |
| Lovelace resources | Antonio font (css), HA-LCARS `lcars.js`, `/local/lcards-registry-fix.js?v=<timestamp>` | dashboards → resources |
| HA-LCARS 4.0.2 → 4.1.3 | Via HACS. Theme file is now `themes/lcars/lcars.yaml`. | HACS |
| UIX 8.3.1 | Installed and set up. **HA was restarted once for it.** | HACS / integration |
| card-mod | **Removed** (HACS). Required by UIX and broken by HA 2026.x. The Müll dashboard's `card_mod:` keys still work through UIX (checked before and after). | reinstall via HACS |
| Old theme copies | Stale 2024 manual copy moved to `/config/themes_backup/lcars-2024-manual-copy.yaml`; 4.0.2 version with appended profiles in `/config/themes_backup/lcars-4.0.2-with-lcards-profiles.yaml`; plus `/config/themes/lcars.yaml.bak-20260924` (ignored by HA, not `.yaml`) | copy back |
| View theme | `/config/themes/lcars_aquarium.yaml` ("LCARS Aquarium") | delete file, reload themes |
| Our scripts | every `ha/www/*.js` in `/config/www/`, each a Lovelace module resource `/local/<file>?v=<unix timestamp>`: registry workaround, motion switch, day grid, bar, week, forecast, radar and power-chart cards. `tools/deploy_ha_files.sh` copies them and creates/updates the resources (`tools/bump_resources.py`). | remove resources + files |
| Bars helper | `input_boolean.lcars_bars` ("LCARS bars", on): segment bars visible (global emergency switch) | helpers UI |
| Sounds | `/media/lcars/thelcars_beep1..4.mp3` (thelcars.com, no licence stated, so **not** in git) | delete files |
| Dashboards | `lcars-bridge` (live). `aquarium-lcars` hidden as "LCARS (alt)". | dashboards UI |
| Profile theme | Admin user's profile theme was set to "LCARS Default", **reset to default** the same day: profile themes are stored per user (synced to all devices) and restyled every classic dashboard. The LCARS dashboard doesn't need it (view theme + kiosk mode). | profile |

Dashboard config backups are written by `tools/deploy.py` to `build/backups/`
(git-ignored). Restore one with `tools/deploy.py --restore <file>`.

## Users and devices

- The personal user (`admin`) keeps the default HA look. LCARS is opened from
  the HA sidebar ("LCARS") on any device.
- `kiosk` (non-admin): meant for LCARS screens. Nothing per-user is
  needed for LCARdS to work; the dashboard isn't admin-only and every view
  carries its own theme. Pick the start page per device: the profile's
  default dashboard (set while logged in as that user) or the kiosk browser's
  Start URL, e.g. `https://ha.example.org/lcars-bridge/aquarium-status`.
- Do **not** set an LCARS profile theme for a user who also uses classic dashboards.
- The old `aquarium`, a short-lived `lcars` and `phone-user` users were deleted.

## Kiosk tablets (Fully Kiosk Browser)

- There is **no Fully Kiosk integration** in HA. What a tablet shows is Fully's
  on-device **Start URL** (Settings → Web Content Settings → Start URL).
  Recommended: `https://ha.example.org/lcars-bridge/aquarium-status?lcars_motion=off`
  (on the LAN also `http://homeassistant.local:8123/…`).
- **Animations off on the tablet**: Fully's renderer crashed with all LCARdS
  animations running. Append `?lcars_motion=off` to the start URL, e.g.
  `…/lcars-bridge/aquarium-status?lcars_motion=off`. The choice is stored per
  browser (localStorage) and pauses anime.js' global engine. The "Motion" block
  at the bottom of every sidebar toggles it on any device.
- **Segment bars off for everyone** (emergency switch): `input_boolean.lcars_bars`,
  also via `?lcars_bars=off|on|toggle`. It is *stored* in HA, so don't put the
  parameter in a start URL: Fully reloads it and switches the bars off for all.
- Kiosk mode and the view theme apply to every user.
- Sounds play after the first touch. If the tablet stays silent, allow media
  playback in Fully's web content settings.
- Layouts are checked at 1920×1080 (desktop) and 1280×800 (Lenovo Tab M10
  Gen 1 in landscape). Row heights and most fonts scale with viewport height,
  header readouts with its width (theme variable `lcars-readout-size`).
- The waste page used to crash Fully with ~450 LCARdS buttons; dense graphics
  are now light custom cards (≈60 LCARdS buttons left on that page).

## Checking layouts

`tools/screenshot/shot.js` renders a view in headless Chrome, logged in with the
token. From WSL, run it with Windows' `node.exe` from a Windows folder (install
once with `npm install` there), because puppeteer can't drive Windows Chrome
across the WSL boundary:

```bash
W=$(wslpath "$(cmd.exe /c echo %TEMP% | tr -d '\r')")/lcars-shot
mkdir -p "$W" && cp tools/screenshot/{shot.js,package.json} "$W/" && (cd "$W" && "/mnt/c/Program Files/nodejs/npm.cmd" install)
cd "$W" && export HA_TOKEN=$(cat ~/.config/homeassistant/token) WSLENV=HA_TOKEN:DSF
"/mnt/c/Program Files/nodejs/node.exe" shot.js waste 1280 800 "$(wslpath -w "$W")\\waste-1280.png"
"/mnt/c/Program Files/nodejs/node.exe" shot.js waste 1920 1080 "$(wslpath -w "$W")\\waste-1920.png"
DSF=1.1 "/mnt/c/Program Files/nodejs/node.exe" shot.js ops 1745 982 out.png 900 600 300 200   # 110 %, clipped
```

Check both target sizes after every layout change; for seams, clip a region at
`DSF=1` and `DSF=1.1` (110 % zoom).

## Sounds

- LCARdS' built-in scheme `lcards_default` is active. Its `tap.mp3` is
  byte-identical to thelcars.com `beep1.mp3`; `beep2.mp3` equals `key_ok_3` /
  `toggle_on`. `beep3` and `beep4` have no LCARdS counterpart.
- The UI category is **off** on purpose. Menu clicks would otherwise play the tap
  sound plus the page-navigation sound. It also applies to **every** dashboard
  (LCARdS is loaded globally), so turning it on makes the classic pages beep too.
  Card sounds only fire on LCARdS cards.
- Audition or override sounds in **LCARdS Config → Sound**, per event, using
  bundled assets or "Browse HA Media" for the `/media/lcars` files.
- To bake the thelcars.com beeps into the dashboard, set `CLICK_SOUNDS` in the
  generator and deploy.

## Known limitations (by design or data)

- **Agenda "Next per calendar"** shows only the *next* event of each calendar,
  because HA calendar entities expose just one upcoming event in their state.
  The full list comes from the embedded calendar card next to it.
- **Osmosis**: the original dashboard's RO-controller card and picture-elements
  image were dropped. The RO card's `binary_sensor.osmose_*` entities no longer
  exist.
- **Hold-to-act** on purpose:
  - dosing "refilled": hold a channel's block or value in "Fill level" (sets the
    fill level to the bottle size; tap opens more-info)
  - washing-machine supply switch (Supply block or value on the laundry page; tap opens more-info)
- **Toggle on a single tap**, as on the original dashboards (hold opens more-info):
  - aquarium modes: the four LCARS buttons in "Modes" (Status page)
  - CO² coupling and light automation: block or value of their row
  - the four dosing schedules: a channel's block in "Schedule"
  - the RO unit (`switch.osmoseanlage`): block or value of its row
  - light profiles Fire / Chill / Resume: their block (applies once, no toggle)
- **Calendar card text is German.** `/local/global-calendar-card.js` (not in
  this repo, shared with the classic dashboards) hardcodes its UI text
  ("Heute", "Keine Termine …"). Only its calendar labels are translated.
- **Renamed URLs (2026-09-24)**: `waschen` → `laundry`, `muell` → `waste`,
  `muell-kalender` → `waste-calendar`, `kalender` → `calendar`,
  `kalender-agenda` → `calendar-agenda`, `aquarium-osmose` → `aquarium-osmosis`.
  Old bookmarks break; the tablet start URL `aquarium-status` is unchanged.
- **Rebuild needed** when the source dashboards' calendar cards change. They are
  copied from `dashboard-muell` / `dashboard-termine` at build time. (Adding HA
  users needs no rebuild: the segment bars are shown to everyone.)
- **New calendar events** show up in "Next 7 days" within 10 minutes (or on
  reload): the card asks HA to refresh the calendars before each fetch, because
  HA's Google calendar sync alone lagged behind.
- **Radar** covers Germany (DWD composite); abroad the map stays empty. Borders
  are fetched from the DWD WFS at build time.
- **LCARdS updates**: run `tools/gen_registry_fix.py`, then
  `tools/deploy_ha_files.sh` (it sets a fresh `?v=` on the resources). Otherwise
  new LCARdS elements hit the load race again.
- **HA-LCARS updates** rewrite `themes/lcars/lcars.yaml`. That's harmless now,
  since nothing of ours lives in it.
