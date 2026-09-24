# Design rules and how to extend the dashboard

## Design decisions (made by the user, keep them)

- **No page scrolling, ever.** Every view is exactly one viewport. If content is
  too tall, split it into another sub-view rather than letting the page grow.
  An embedded standard card may scroll *inside its own column* as a last resort.
- **Voyager palette** (orange, peach, lavender, violet, blue-violet, ice blue),
  hex constants at the top of `build_dashboard.py`. Hex on purpose, so LCARdS
  alert modes don't shift them.
- **Titan.DS-style finesse** (reference: https://www.mewho.com/titan/, without its
  zoom feature):
  - slim frame (pillar 140 px, bars 10 px)
  - flat dark-tinted rows with a state-coloured left stripe and the value in the
    state colour
  - small section headers (square cap plus thin underline)
  - flat command blocks with black text bottom-right
- **Menus are part of the frame.**
  - The sidebar blocks are the vertical pillar and list the active section's
    sub-views, plus **Classic** (link to the original dashboard).
  - The header frame bar *is* the section menu, in the order **OPS, Aquarium,
    Laundry, Waste, Calendar**. The active item is orange with "◂".
- **No decorative animation**: no blinking lights, no flowing textures, no
  cascading number columns. The only animation left is the title blinking on a
  *critical* pump alert.
- **Leave space.** Controls don't need to stretch to 100 % width. The RGB channels
  and dosing levels are narrow vertical "transporter" columns with black space
  around them.
- RGB channels are vertical segment columns (transporter-control style), and so
  are the dosing fill levels.
- **LCARdS-native wherever possible.** Standard HA cards are embedded only where
  LCARdS has no equivalent: calendar month/agenda, to-do list, rain radar and
  hourly forecast. The view theme restyles them.
- **Colours stay semantic**: ice = OK/running, sunflower = warning/manual, red =
  critical, grey = off.
- **All UI text is English.** Sensor states and calendar event titles arrive in
  German; bin names are mapped (`BIN_NAMES`, `CAL_LABELS`), other event titles
  are shown as they are. Dates use `en-GB` ("Fri 25/09 · tomorrow").
- **Waste page rows** use the bin colour for stripe and background tint, value
  text in peach. Upcoming and next pickup pick the colour at runtime (JS style
  templates, see `docs/NOTES.md`).
- **Aquarium power chart is mirrored**: zero axis in the middle, total above,
  consumers (pump, CO²) below, log scale, filled areas with smooth curves (no
  steps, no bars). Its header has the cap on the right, facing "Power grid".
  No legend inside the chart: the readouts under "Power grid" are the legend
  (colour swatch, label, value in the series colour) and are not buttons.

## Structure of `generator/build_dashboard.py`

| Part | What it is |
|------|------------|
| Palette and entity constants | colours and entity IDs used across views |
| `block`, `segments`, `elbow` | frame primitives |
| `header`, `row`, `pill`, `info`, `action_btn`, `column` | content primitives |
| `SECTIONS` | header sections, each with sidebar sub-views `(key, label, code, colour, path)` and a classic URL |
| `NAV_ORDER` | order of the sections in the header bar |
| `section_readouts(section)` | the 4 header readouts per section |
| `frame()` / `view()` | assemble the shared frame around a view's content |
| `*_content()` | one function per view |
| `VIEWS` | the list of views: `view(section, key, title, path, content, subtitle)` |
| `finalize()` | global post-processing: `minmax(0,Nfr)`, `min_height: 0`, optional `CLICK_SOUNDS` |

### Adding a view to an existing section

1. Write `my_content()` returning a layout grid, usually `cols(column([...]), ...)`.
2. Add `(key, label, code, colour, "<section>-<name>")` to that section's
   sub-view list in `SECTIONS`.
3. Add `view("<section>", key, "LCARS …", "<section>-<name>", my_content(), "subtitle · code")`
   to `VIEWS`.
4. Run `python3 tools/deploy.py`. It validates before saving.

### Adding a new section

Do the above, then also:
- add a `SECTIONS` entry
- put its key in `NAV_ORDER`
- add a branch in `section_readouts()` (exactly 4 readouts)

## URL rules

- HA dashboard paths **must contain a hyphen**; HA rejects `lcars` ("Url path
  needs to contain a hyphen"). Hence `lcars-bridge`.
- A view path is a **single segment** (`/lcars-bridge/<view>`), so views are
  named `<section>-<view>`: `aquarium-power`, `waste-calendar`, `calendar-agenda`.
- A dashboard's path can't be renamed. Moving means creating a new dashboard.
  The old `aquarium-lcars` still exists, hidden from the sidebar as
  "LCARS (alt)", until the user decides to delete it.
