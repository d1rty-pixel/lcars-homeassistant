# Calendars

Used by `week` (the next days of several calendars), `month` and `next_event` readouts.

## Setup

Any `calendar.*` entities work: Google Calendar, Local Calendar, CalDAV, the Holiday integration, Waste
Collection Schedule's calendars, and so on. List them once for the whole dashboard:

```yaml
calendars:
  - {entity: calendar.family, label: Family}               # label: default its name in HA
  - {entity: calendar.waste_residual, label: Residual, colour: "#AAAACC"}   # colour: default a palette in turn
  - calendar.holidays
titles:                       # event titles to replace (translations, shorter names)
  "Recycling collection": Recycling
```

`week` and `month` show all of them unless given `calendars: [entity IDs]`.

## How the cards read events

- Calendar entities only expose their **next** event in their state. `lcars-week` and `lcars-month`
  therefore fetch events through HA's calendar REST API (`/api/calendars/<entity>?start=…&end=…`) on
  load and every 10 minutes (the month also when you page to another month).
- Before each fetch, they ask HA to refresh the calendars (`homeassistant.update_entity`). Without it,
  new Google Calendar events can take a long time to show up.
- The user viewing the dashboard needs read access to the calendars (every HA user has).
