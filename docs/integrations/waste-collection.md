# Waste collection

Used by the `timeline` component (the next weeks' collections as a grid), label columns with countdown
bars, readouts of the next pickup, and the waste calendars in `week` and `month`.

## Setup

Install [Waste Collection Schedule](https://github.com/mampfes/hacs_waste_collection_schedule) from
HACS and configure it for your waste company. The views expect **one sensor per bin** whose state is
the next date as `dd.mm.yyyy`, an overview sensor, and **one calendar per bin**. A YAML setup that
produces this (`waste_collection_schedule: !include waste_collection_schedule.yaml` in
`configuration.yaml`):

```yaml
sources:
  - name: <your_source>            # see the integration's source list
    args: { ... }                  # the source's arguments (address etc.)
    calendar_title: Waste
    customize:
      - type: <type name from the source>
        alias: Residual
        use_dedicated_calendar: true      # one calendar entity per bin
        dedicated_calendar_title: Waste Residual
      # ... one entry per bin

sensors:
  - name: Waste Residual
    types: [Residual]
    value_template: "{{ value.date.strftime('%d.%m.%Y') }}"
    add_days_to: true
  # ... one sensor per bin
  - name: Waste Next Pickup
    value_template: "{{ value.types | join(', ') }} am {{ value.date.strftime('%d.%m.%Y') }}"
    details_format: appointment_types
    add_days_to: true
```

When *every* type uses a dedicated calendar, the combined calendar entity is no longer created. The
views don't need it.

## In lcars.yaml

A sensor of Waste Collection Schedule has an attribute per upcoming date (`yyyy-mm-dd` keys, the default
`details_format: upcoming`), which is what `timeline` reads; its state (`dd.mm.yyyy` with the
`value_template` above) is what a countdown bar and a `{date: state}` value read:

```yaml
- type: split
  colour: orange
  top:
    type: timeline
    days: 28
    series:
      - {label: Residual, entity: sensor.waste_residual, colour: "#AAAACC"}
      - {label: Organic, entity: sensor.waste_organic, colour: almond}
  bottom:
    type: frame
    title: Next per bin
    colour: peach
    bottom: false
    content:
      type: rows
      filler: peach
      rows:
        - {label: Residual, colour: "#AAAACC", entity: sensor.waste_residual, value: {date: state}, bar: countdown}
        - {label: Organic, colour: almond, entity: sensor.waste_organic, value: {date: state}, bar: countdown}
```

The overview sensor's state ("`<bins> am <date>`" with the template above) as a readout of the next bin:

```yaml
- type: readout
  entity: sensor.waste_next_pickup
  label: Next pickup
  value: "[[[ return String(entity.state).split(' am ')[0]; ]]]"
```

A series whose *state* is its date (e.g. a hazardous-waste collection read with a `rest` sensor) takes
`match: state` in the timeline. Give the calendars the bins' colours in the site's `calendars`, and
translate or shorten the event titles with `titles`.
