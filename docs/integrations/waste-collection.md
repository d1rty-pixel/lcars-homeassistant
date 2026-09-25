# Waste collection

Used by the **Waste** section: the 28-day collection timeline, "Next per bin", the hazmat frame, the
header readouts, and the waste calendars in OPS and the Calendar section.

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

## In the generator

- `BINS`: (label, sensor, colour) per bin. The timeline, "Next per bin" and the countdown bars
  (2 days per segment, 28 days) follow it.
- `WASTE_CALS`: the per-bin calendars (and the hazmat one).
- `NEXT_PICKUP`: the overview sensor. `JS_NEXT_BIN` parses its "`<bin> am <date>`" state, so keep that
  format or adapt the parser.
- `BIN_NAMES`: bin names as they appear in states and event titles, mapped to short labels.
- `HAZMAT`: an optional **hazardous-waste collection** frame fed by three separate sensors: a date
  (`yyyy-mm-dd`), a time window (`HH:MM - HH:MM`) and a location. The original installation reads
  them with a `rest` sensor from the waste company's API. Remove the frame from `_waste()` if you
  have no such data.
