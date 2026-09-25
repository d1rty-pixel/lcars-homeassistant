# Operations: kiosk tablets, layout checks, sounds, known limitations

## Kiosk tablets (Fully Kiosk Browser)

- There is **no Fully Kiosk integration** in HA. What a tablet shows is Fully's
  on-device **Start URL** (Settings → Web Content Settings → Start URL).
  Recommended: `https://<your-ha>/lcars-bridge/<view>?lcars_motion=off`.
- **Animations off on the tablet**: Fully's renderer crashed with all LCARdS
  animations running. Append `?lcars_motion=off` to the start URL, e.g.
  `…/lcars-bridge/ops?lcars_motion=off`. The choice is stored per
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
mkdir -p "$W" && cp tools/screenshot/{shot.js,package.json} "$W/" && (cd "$W" && cmd.exe /c "npm install")   # npm.cmd can't be run from bash
cd "$W" && export HA_TOKEN=$(cat ~/.config/homeassistant/token) WSLENV=HA_TOKEN:DSF
"/mnt/c/Program Files/nodejs/node.exe" shot.js waste 1280 800 "$(wslpath -w "$W")\\waste-1280.png"
"/mnt/c/Program Files/nodejs/node.exe" shot.js waste 1920 1080 "$(wslpath -w "$W")\\waste-1920.png"
DSF=1.1 "/mnt/c/Program Files/nodejs/node.exe" shot.js ops 1745 982 out.png 900 600 300 200   # 110 %, clipped
```

Check both target sizes (and 1280×720, the tablet with its system bars) after every layout change;
display priorities switch at 760, 880 and 1000 px viewport height, so check around those too. For seams,
clip a region at
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

- **Hold-to-act** on purpose:
  - dosing "refilled": hold a channel's Refill button in "Dosing station" (sets the
    fill level to the bottle size; tap opens more-info)
  - washing-machine supply switch (Supply block or value on the laundry page; tap opens more-info)
- **Toggle on a single tap**, as on the original dashboards (hold opens more-info):
  - aquarium modes: the four LCARS buttons in "Modes" (Status page)
  - CO² coupling and light automation: block or value of their row (Status page); light automation
    also the Automation pill in "Controls" (Light page)
  - the four dosing schedules: the Schedule pill at the top of a channel's frame
  - the RO unit (`switch.osmoseanlage`): block or value of its row
  - light profiles Fire / Chill: their pill in "Controls" (applies once, no toggle; switching Automation
    back on resumes the schedule)
  - light channels: drag a transporter slot (sets a manual override when the finger lifts)
- **Rebuild needed** when the calendars' labels in the source dashboard's
  calendar card change: the labels are read from `dashboard-termine` at build
  time (`calendar_list()`). (Adding HA
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
