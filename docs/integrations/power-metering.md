# Power metering

Used by label columns of power readings, `history` (a sensor over 24 h / 7 d / 28 d) and `chart` (several
sensors mirrored around a zero line).

## Setup

Any smart plug or meter that reports power (W) and energy (kWh), e.g. a Shelly plug through the built-in
Shelly integration. A typical appliance page:

```yaml
- type: stack
  items:
    - type: rows
      rows:
        - {label: Cycle, entity: sensor.washer_power, value: {above: 3, then: Running, else: Idle},
           bar: {mode: state, states: {"on": ice}, threshold: 3}}
        - {label: Power, entity: sensor.washer_power, bar: {mode: level, min: 0, max: 2500}}
        - {label: Energy, entity: sensor.washer_energy}
        - {label: Supply, entity: switch.washer, value: {on_off: ["On", "Off"]}, hold: toggle}
    - {type: section, title: Power trace, colour: lilac, height: {timeline: 5},
       content: {type: history, entity: sensor.washer_power, buttons: [violet, lilac, peri], filler: lilac}}
```

## The history chart (`lcars-history`)

- The data comes from HA's **long-term statistics** (`recorder/statistics_during_period`, the maximum
  per period by default): 5-minute periods for 24 h, hourly for 7 d and 28 d. The sensor needs a
  `state_class` (`measurement`), or there are no statistics.
- Log scale with lines at 1, 10, 100 and 1000 by default (`scale: linear` with `min`/`max` for other
  sensors). Range buttons 24H / 7D / 28D continue the label column; the choice is stored per browser.
- LCARdS' own charts preload at most 7 days of history, so the 28-day range needs this card. The
  mirrored `chart` uses LCARdS' chart (24 h).
