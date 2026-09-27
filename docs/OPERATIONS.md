# Operations: checking layouts, sounds, known limitations

Kiosk tablets, updates and troubleshooting are in [INSTALL.md](INSTALL.md).

## Checking layouts

Check every page after a layout change at **1280×720, 1280×800, 1920×1080 and a phone in landscape
(734×337 with a 20 px bottom inset: an iPhone 16 in Chrome, measured)**. Tiers switch at 520, 760, 880
and 1000 px viewport height, so look around those too. No page may scroll except on phones.

`tools/screenshot/shot.js` renders a view in headless Chrome, logged in with the token:

```bash
cd tools/screenshot && npm install        # once (puppeteer-core)
HA_TOKEN=$(cat ~/.config/homeassistant/token) HA_URL=http://homeassistant.local:8123 \
  node shot.js <view-path> 1280 800 out.png
```

| Environment | Meaning |
|-------------|---------|
| `HA_URL`, `HA_TOKEN` | HA and a long-lived token |
| `LCARS_DASHBOARD` | the dashboard (default `lcars-bridge`), e.g. a test copy |
| `CHROME` | Chrome's executable (default: the Windows path) |
| `SAFE=top,right,bottom,left` | safe-area insets in px, as HA pads its views by them: `0,0,20,0` for the phone above, `0,59,21,59` for an iPhone's HA app |
| `DSF` | device scale factor, e.g. `1.1` for 110 % zoom (hairline seams show there) |
| `SCROLL=<px>\|end` | scrolls every scrolling element before the shot and logs visible/total heights, to check a phone's scrolled part or confirm "nothing scrolls" |

Extra arguments `clip-x clip-y clip-w clip-h` clip the shot. Each run uses its own browser profile, so
several can run at once.

**From WSL**, run it with Windows' `node.exe` from a Windows folder (puppeteer can't drive Windows'
Chrome across the WSL boundary), and pass the environment through `WSLENV`:

```bash
W=$(wslpath "$(cmd.exe /c echo %TEMP% | tr -d '\r')")/lcars-shot
mkdir -p "$W" && cp tools/screenshot/{shot.js,package.json} "$W/" && (cd "$W" && cmd.exe /c "npm install")
cd "$W" && export HA_TOKEN=$(cat ~/.config/homeassistant/token) HA_URL=http://homeassistant.local:8123 \
  WSLENV=HA_TOKEN:HA_URL:LCARS_DASHBOARD:SAFE:DSF:SCROLL
"/mnt/c/Program Files/nodejs/node.exe" shot.js ops 1280 800 "$(wslpath -w "$W")\\ops-1280.png"
```

`lcars diag` adds a view that shows what a device's browser reports (window and visual viewport,
`100vh`/`dvh`/`svh`/`lvh`, safe-area insets as the browser and as HA see them): open `<dashboard>/diag`
on the device. Run it again after each deploy (a deploy replaces the whole configuration).

## Sounds

- LCARdS plays its built-in scheme (`lcards_default`) once its sound helpers exist and are on (LCARdS
  config panel → Helpers, then Sound). The light cards' buttons play LCARdS' tap sound too.
- LCARdS is loaded on every dashboard, so its UI sounds (navigation, dialogs) play on HA's other pages
  too. Keeping the UI category off avoids a menu click playing the tap and the navigation sound.
- Override sounds per event in LCARdS' config panel, or bake them into this dashboard with the site's
  `sounds` (e.g. `{card_tap: "media-source://media_source/local/lcars/beep1.mp3"}`).
- Browsers play sounds only after the first touch; allow media playback in a kiosk browser.

## Known limitations

- **Hold-to-act** on purpose where a tap would be too easy to trigger: actions configured with `hold`
  (e.g. marking a tank refilled, switching a supply). A tap opens more-info there.
- **Rebuild needed** after changes to what is read at build time: `data` sources, the radar's location
  (its borders), entity patterns (`media_player.spotify_*`), the sensors of the number columns.
- **Calendars**: new events show up in the week and month within 10 minutes (or on reload); the cards
  ask HA to refresh the calendars before each fetch, because HA's Google calendar sync alone lags.
- **Radar**: DWD's composite covers Germany; elsewhere the map stays empty. Other providers would be a
  new option of the radar card.
- **LCARdS updates**: run `lcars files` afterwards (the registry workaround needs the new version's
  element names). Browsers refetch changed cards by their `?v=`.
- **Missing entities** show their value templates as raw text (`[[[ … ]]]`); `lcars build` lists them.
- **History charts** need long-term statistics: the sensor must have a `state_class`.
