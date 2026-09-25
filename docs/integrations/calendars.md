# Calendars

Used by **OPS → Next 7 days** (`custom:lcars-week`), the **Calendar** section (month view, agenda,
header readouts), and the Waste calendar view.

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

- Calendar entities only expose their **next** event in their state. `lcars-week` therefore fetches
  events through HA's calendar REST API (`/api/calendars/<entity>?start=…&end=…`) on load and every
  10 minutes.
- Before each fetch, it asks HA to refresh the calendars (`homeassistant.update_entity`). Without
  that, new Google Calendar events can take a long time to show up.
- The agenda's "Next per calendar" list uses the entities' states, so it shows one event per
  calendar.
- The month view and the agenda embed `custom:global-calendar-card`, which is **not part of this
  repo**. The generator copies its config from another dashboard (`foreign_card("dashboard-termine",
  "kalender")`). Replace it with the standard `calendar` card or another calendar card. With the
  standard card, `entities` takes plain entity ID strings only.
