# Operations: HA-side state, changes made, known limitations

## Changes made on the HA host while building this (2026-09-24)

| What | Detail | Reversible via |
|------|--------|----------------|
| LCARdS config entry | Created (the integration was only downloaded). Log level `warn`; it was temporarily `debug` while debugging. | integration options |
| Time & Date | Config entry with `sensor.time` | integration |
| HA-LCARS helpers | `input_boolean.lcars_sound`, `input_boolean.lcars_texture`, `input_number.lcars_vertical`, `input_number.lcars_horizontal` | helpers UI |
| LCARdS sound helpers | `input_boolean.lcards_sound_enabled/_cards/_ui/_alerts`, `input_number.lcards_sound_volume`, `input_select.lcards_sound_scheme` | helpers UI |
| Lovelace resources | Antonio font (css), HA-LCARS `lcars.js`, `/local/lcards-registry-fix.js?v=2` | dashboards → resources |
| HA-LCARS 4.0.2 → 4.1.3 | Via HACS. Theme file is now `themes/lcars/lcars.yaml`. | HACS |
| UIX 8.3.1 | Installed and set up. **HA was restarted once for it.** | HACS / integration |
| card-mod | **Removed** (HACS). Required by UIX and broken by HA 2026.x. The Müll dashboard's `card_mod:` keys still work through UIX (checked before and after). | reinstall via HACS |
| Old theme copies | Stale 2024 manual copy moved to `/config/themes_backup/lcars-2024-manual-copy.yaml`; 4.0.2 version with appended profiles in `/config/themes_backup/lcars-4.0.2-with-lcards-profiles.yaml`; plus `/config/themes/lcars.yaml.bak-20260924` (ignored by HA, not `.yaml`) | copy back |
| View theme | `/config/themes/lcars_aquarium.yaml` ("LCARS Aquarium") | delete file, reload themes |
| Registry workaround | `/config/www/lcards-registry-fix.js` | remove resource + file |
| Sounds | `/media/lcars/thelcars_beep1..4.mp3` (thelcars.com, no licence stated, so **not** in git) | delete files |
| Dashboards | `lcars-bridge` (live). `aquarium-lcars` hidden as "LCARS (alt)". | dashboards UI |
| Profile theme | Admin user's profile theme was set to "LCARS Default", **reset to default** the same day: profile themes are stored per user (synced to all devices) and restyled every classic dashboard. The LCARS dashboard doesn't need it (view theme + kiosk mode). | profile |

Dashboard config backups are written by `tools/deploy.py` to `build/backups/`
(git-ignored). Restore one with `tools/deploy.py --restore <file>`.

## Users and devices

- `admin` (admin): default HA look on classic dashboards, LCARS via the sidebar.
- `kiosk`, `lcars` (non-admin): meant for LCARS screens. Nothing per-user is
  needed for LCARdS to work; the dashboard isn't admin-only and every view
  carries its own theme. Pick the start page per device: the profile's
  default dashboard (set while logged in as that user) or the kiosk browser's
  Start URL, e.g. `https://ha.example.org/lcars-bridge/aquarium-status`.
- Do **not** set an LCARS profile theme for a user who also uses classic dashboards.
- The old `aquarium` user was deleted.

## Kiosk tablets (Fully Kiosk Browser)

- There is **no Fully Kiosk integration** in HA. What a tablet shows is Fully's
  on-device **Start URL** (Settings → Web Content Settings → Start URL), on the
  LAN also `http://homeassistant.local:8123/lcars-bridge/aquarium-status`.
- Kiosk mode and the view theme apply to every user.
- Sounds play after the first touch. If the tablet stays silent, allow media
  playback in Fully's web content settings.
- The layout was tuned on a 2560×1271 desktop viewport. Row heights and most
  fonts scale with viewport height. Check the tablet and fine-tune if needed.

## Sounds

- LCARdS' built-in scheme `lcards_default` is active. Its `tap.mp3` is
  byte-identical to thelcars.com `beep1.mp3`; `beep2.mp3` equals `key_ok_3` /
  `toggle_on`. `beep3` and `beep4` have no LCARdS counterpart.
- The UI category is **off** on purpose. Menu clicks would otherwise play the tap
  sound plus the page-navigation sound.
- Audition or override sounds in **LCARdS Config → Sound**, per event, using
  bundled assets or "Browse HA Media" for the `/media/lcars` files.
- To bake the thelcars.com beeps into the dashboard, set `CLICK_SOUNDS` in the
  generator and deploy.

## Known limitations (by design or data)

- **Agenda "Next per calendar"** shows only the *next* event of each calendar,
  because HA calendar entities expose just one upcoming event in their state.
  The full list comes from the embedded calendar card next to it.
- **Osmose**: the original dashboard's RO-controller card and picture-elements
  image were dropped. The RO card's `binary_sensor.osmose_*` entities no longer
  exist.
- **Hold-to-act** on purpose:
  - dosing "refilled" (sets fill level to bottle size)
  - washing-machine supply switch (tap opens more-info)
- **Toggle on a single tap**, as on the original dashboards:
  - aquarium auto/maintenance/feeding/water-change modes
  - CO² coupling
  - light automation
  - the four dosing schedules
  - the RO unit (`switch.osmoseanlage`)
- **Rebuild needed** when the source dashboards' calendar cards change. They are
  copied from `dashboard-muell` / `dashboard-termine` at build time.
- **LCARdS updates**: run `tools/gen_registry_fix.py`, then
  `tools/deploy_ha_files.sh`, and bump the resource `?v=`. Otherwise new LCARdS
  elements hit the load race again.
- **HA-LCARS updates** rewrite `themes/lcars/lcars.yaml`. That's harmless now,
  since nothing of ours lives in it.
