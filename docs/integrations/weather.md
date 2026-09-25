# Weather and sun

Used by **OPS → Atmosphere** and **OPS → Forecast**, and by the Outside and Condition readouts in the
OPS header.

## Setup

Any `weather.*` entity that offers an **hourly forecast** works. The original installation uses the
built-in **Met.no** integration (the default "Home" weather, `weather.forecast_home`). Set `WEATHER`
in the generator to your entity. `sun.sun` (the built-in Sun integration) provides the Daylight row.

## What is used

| Row | Source | Scale |
|-----|--------|-------|
| Temperature | `temperature` attribute | −10 … 35 °C |
| Humidity | `humidity` | 0 … 100 % |
| Pressure | `pressure` | 970 … 1050 hPa |
| Wind | `wind_speed`, `wind_bearing` (as a compass point) | 0 … 60 km/h |
| Daylight | `sun.sun` `next_rising` / `next_setting` | 24 h span |
| Forecast | `weather/subscribe_forecast` (hourly), the next 12 h: condition, temperature, precipitation | temperature bar scaled to the shown hours |

The labels assume °C, hPa and km/h. With other units, change the scales in `_home()` and the unit
suffixes in the value templates. Condition names are translated to short LCARS codes
(`CONDITION_CODES` in `lcars-forecast.js`, `WEATHER_NAMES` in the generator).
