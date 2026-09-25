# Calendars

Used by **OPS → Next 7 days** (`custom:lcars-week`) and the **Calendar** section (month view,
`custom:lcars-month`, and the header readouts).

## Setup

Any `calendar.*` entities work: Google Calendar, Local Calendar, CalDAV, the Holiday integration,
the waste calendars, and so on. List your personal calendars in `site.yaml`:

```yaml
calendars:
  - calendar.personal
  - calendar.birthdays
  - calendar.holidays
```

The generator appends them to the waste calendars (`WASTE_CALS`) to form `ALL_CALS`.
`CAL_LABELS` maps calendar names to the labels shown, and `BIN_NAMES` maps event titles, e.g. from
German to English.

## How the cards read events

- Calendar entities only expose their **next** event in their state. `lcars-week` and `lcars-month`
  therefore fetch events through HA's calendar REST API (`/api/calendars/<entity>?start=…&end=…`) on
  load and every 10 minutes (the month also when you page to another month).
- Before each fetch, it asks HA to refresh the calendars (`homeassistant.update_entity`). Without
  that, new Google Calendar events can take a long time to show up.
- The calendars' labels are read at build time from another dashboard's calendar card
  (`foreign_card("dashboard-termine", "kalender")` in `calendar_list()`); a calendar without one there
  is labelled by its entity ID. Point it at your own dashboard or set the labels in `calendar_list()`.
