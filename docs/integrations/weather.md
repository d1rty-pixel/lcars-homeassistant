# Weather and sun

Used by label columns of weather values and by the `forecast` component.

## Setup

Any `weather.*` entity with a forecast works, e.g. the built-in **Met.no** integration (HA's default
"Home" weather). Set it as the site's `weather` (the default of `forecast` components) and use it in
rows. `sun.sun` (the built-in Sun integration) gives sunrise and sunset.

```yaml
weather: weather.forecast_home
...
- type: rows
  rows:
    - {label: Temperature, entity: weather.forecast_home, value: {attribute: temperature, unit: "°C"},
       bar: {mode: level, attribute: temperature, min: -10, max: 35}}
    - {label: Humidity, entity: weather.forecast_home, value: {attribute: humidity, unit: "%", round: 0},
       bar: {mode: level, attribute: humidity, min: 0, max: 100}}
    - {label: Pressure, entity: weather.forecast_home, value: {attribute: pressure, unit: hPa, round: 0},
       bar: {mode: level, attribute: pressure, min: 970, max: 1050}}
    - label: Wind
      entity: weather.forecast_home
      value: >-
        [[[ const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
        const a = entity.attributes; return Math.round(a.wind_speed) + ' km/h · ' + dirs[Math.round(a.wind_bearing / 22.5) % 16]; ]]]
      bar: {mode: level, attribute: wind_speed, min: 0, max: 60}
    - {label: Daylight, entity: sun.sun, value: {span: [next_rising, next_setting]},
       bar: {mode: span, start: next_rising, end: next_setting}}
- {type: section, title: Forecast, colour: lilac, content: {type: forecast, labels: [violet, lilac]}}
```

The scales and units are yours to choose: attributes come in the units your weather integration uses.

## The forecast

`lcars-forecast.js` subscribes to `weather/subscribe_forecast` like HA's own forecast card (forecasts
aren't attributes any more): hourly (the next 12 hours) or daily (7 days), switched per device by its
Hourly / Daily block. Condition names become short LCARS codes (`CONDITION_CODES` in the card). A
readout of the condition in words:

```yaml
- type: readout
  entity: weather.forecast_home
  label: Condition
  value: {map: {clear-night: Clear night, cloudy: Cloudy, partlycloudy: Partly cloudy, rainy: Rain, sunny: Sunny}}
```
