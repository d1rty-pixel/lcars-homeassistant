# Integrations

What the components expect from Home Assistant, and how to set up the integrations that feed them.
Any integration that provides the right kind of entity works; these are the ones the framework was
built and tested with.

| Integration | Components | Doc |
|-------------|------------|-----|
| Weather (any `weather.*` with a forecast, e.g. Met.no) and Sun | `rows` with weather attributes, `forecast` | [weather.md](weather.md) |
| Calendars (Google, Local Calendar, CalDAV, holidays, …) | `week`, `month`, `next_event` | [calendars.md](calendars.md) |
| Waste Collection Schedule (HACS) | `timeline`, `rows` with countdown bars | [waste-collection.md](waste-collection.md) |
| Power-metering smart plugs and meters (e.g. Shelly) | `rows` with level bars, `history`, `chart` | [power-metering.md](power-metering.md) |
| Media players (Spotify and others) | `player`, `library` | [spotify.md](spotify.md) |
| DWD radar (no HA integration: DWD's public WMS/WFS) | `radar` | [dwd-radar.md](dwd-radar.md) |

What the dashboard itself needs (LCARdS, kiosk-mode, Time & Date, …) is in [INSTALL.md](../INSTALL.md).
