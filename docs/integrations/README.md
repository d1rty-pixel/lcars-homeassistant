# Integrations

What each view expects from Home Assistant, and how the original installation set it up. Entity IDs
are the generator's defaults. Change the constants in `generator/build_dashboard.py` (or `site.yaml`
where noted) to match yours.

| Integration | Used by | Doc |
|-------------|---------|-----|
| Spotify (built-in) | Media → Player | [spotify.md](spotify.md) |
| DWD radar (no HA integration, direct WMS/WFS) | OPS → Precipitation radar | [dwd-radar.md](dwd-radar.md) |
| Weather (any `weather.*`, e.g. Met.no) and Sun | OPS → Atmosphere, Forecast | [weather.md](weather.md) |
| Calendars (Google, local, holidays, …) | OPS → Next 7 days, Calendar section | [calendars.md](calendars.md) |
| Waste Collection Schedule (HACS) | Waste section | [waste-collection.md](waste-collection.md) |
| Power-metering smart plugs (e.g. Shelly) | Laundry, Aquarium → Power / Osmosis | [power-metering.md](power-metering.md) |
| Aquarium integrations, Chihiros light, ESPHome camera | Aquarium section | [aquarium.md](aquarium.md) |

Base requirements (LCARdS, HA-LCARS, UIX, kiosk-mode, Time & Date) are in the main
[README](../../README.md#requirements).
