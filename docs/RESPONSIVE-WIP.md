# Work in progress: responsive layout (branch `responsive-small-screens`)

Status notes for this branch. Read this first when continuing; delete it (and its pointer in `AGENTS.md`)
before merging to `main`. Installation-specific details (test dashboard, how to reach it) are in the
git-ignored `CLAUDE.local.md`.

**Since 2026-09-27 the generator is the framework** (`docs/FRAMEWORK-WIP.md`): what this file calls the
generator's functions lives in `lcars/` now (`Len` etc. in `engine/sizes.py`; `shown_from()`, `tiered()`,
`by_screen()`, `scroll_min_h()` in `engine/screen.py`; `frame()` in `frame.py`; the pages' layouts are
components, and per-tier variants come from `responsive()`). `site.yaml` became the site's `lcars.yaml`.

## Goal and user decisions

- The dashboards must also work on an **iPhone 16 in landscape**, in **Chrome on iOS** (the user's browser;
  also through the HA app).
- **One codebase that adapts automatically, like Bootstrap** (user, explicit). No separate phone layouts or
  designs. Only *placement* may change per screen (through the display priorities). An earlier attempt
  that built every view twice with a compact profile was stopped by the user.
- On small screens **frames and shoulders significantly smaller** (user).
- On small screens **no generated LCARS numbers** (user).
- Earlier (still the `scroll: off` behaviour): on phones the header disappears and the **section menu moves
  into the foot bar**.
- User's verdict on the fluid-only round (before scrolling): "close, but not enough". Reason given for
  scrolling: squeezed complex frames/shoulders never look good enough.

### Decisions of 2026-09-26 (scrolling round)

- **Scrolling, configurable globally**: `site.yaml` `layout.scroll: auto|off`, `layout.scroll_min_h`
  (default `auto`, 520; "may need changing later"). Default is no scrolling; only on screens lower than
  `scroll_min_h` (phones) does the page scroll.
- **What scrolls**: only the sidebar and the content next to it, together. The header stays fixed (user:
  "muss statisch bleiben"), and so do the mid bar and the foot bar.
- **Navigation at the top**: with scrolling the section menu is in the header, not in the foot bar. Because a
  full fixed header would leave only ~85 px of 301 for the content, the phone keeps **only the header's menu
  bar** (with its elbow, as thick as the foot bar); readouts, number columns and page title are not rendered
  there (user agreed). The foot bar keeps weekday/time and the pump alert.
- **Nothing is left out when the page scrolls** (user: OPS' Forecast bottom frame and Next 7 days top frame
  were missing, and the calendar was incomplete): phones show the highest display priority; the scrolling
  area grows by what the content needs.
- **Width problems are solved responsively, not by device convention** (user, on Dosing: "2x2, aber
  responsive, nicht per Konvention"): the channel frames wrap into 2 × 2 when a column would get narrower
  than its title, measured on the card's own width (`lcars-flow.js`).
- **Right frame on small screens** (user idea, globally configurable): drop the right frame/shoulders on
  phones to gain width. **Not implemented yet**: the content of the five pages closed on the right brings
  that pillar itself (Status, Visual, Light, Media, Calendar), so each needs a variant without it.
- User question answered: an own iOS app would not give "all 2556 × 1179 pixels" (the page gets 734 × 337
  CSS px at DPR 3 in Chrome; a native app also works in points). More height without code: the HA app
  (kiosk) or Safari's "Add to Home Screen" (~393 instead of 337).

## Measured target (Chrome on iOS, iPhone 16, landscape)

From the diagnostic view (`tools/diag_view.py`, then open `<dashboard>/diag` on the phone):

| | value |
|---|---|
| window / visual viewport | 734 × 337 (Chrome keeps the page clear of the notch itself) |
| 100vh / 100lvh | 373 (height *without* the browser's toolbar: never use `vh`) |
| 100dvh / 100svh | 337 |
| safe area t/r/b/l | 0 / 0 / 20 / 0 (HA sees the same) |
| DPR | 3 |

So the view is 734 × 301 after HA's bottom inset and the 8 px padding. The HA app (not measured) should be
about 852 × 393 with safe areas 0/59/21/59.

Screenshot at that size: `SAFE=0,0,20,0 … shot.js <view> 734 337 out.png` (see `docs/OPERATIONS.md`).

## What is implemented

### Committed on the branch (before 2026-09-26)

- **Fluid sizes** (`docs/DESIGN.md` "Responsive sizes"): `Len` in the generator (terms with a minimum share
  each, renders `clamp(min, calc(k·dvh + c), max)`, sums as `calc()`, the generator keeps doing arithmetic);
  `fl()`, `font()`, `code_font()`, `css()`. Full size at ≥ `REF_H` 720 px, linear down to the minimum at
  `MIN_H` 400 px. Cards: `fluid()/sz()/fz()/len()/scale()` at the top of every `ha/www/lcars-*.js` (same
  formula; keep them in step with the generator).
- **Minimum shares**: default 0.6; frame pieces much lower (`PILLAR` 0.5, `ELBOW_EXT` / `INNER_CURVE` 0.35,
  `TOP_BAR_T` 0.47, `PANEL_CORNER` 0.5, `PANEL_PILLAR` / `DECOR_PILLAR_W` 0.45, `MAIN_MARGIN` 0.4, `FOOT_T`
  0.8); fonts 0.8, label columns 0.75 (`LABEL_LO`), sidebar labels 0.6, `DATA_ROW` 0.72 (20 px).
- **Everything height-based is `dvh`**, not `vh` (iOS `vh` = height without toolbars: that caused the
  overlapping the user saw first).
### Scrolling round (2026-09-26, not committed yet at the time of writing)

- **Config**: `SCROLL`, `SCROLL_MIN_H` read from `site.yaml` `layout` (documented in `site.example.yaml`).
- **Scroll container**: in `frame()` sidebar and content are one nested grid (`body`) with
  `height: 100%`, for which LCARdS sets `overflow-y: auto` on its `#grid-root`. Its row is
  `minmax(calc(100% + max(0px, SCROLL_MIN_H - 100dvh)), auto)`: as much higher than the visible space as
  the viewport is lower than `SCROLL_MIN_H`, and higher where the content's intrinsic minimum needs it.
  The view's grid areas become `"body body"` instead of `"side main"`.
- **Phone header**: `on_phone(card)` / `NOT_PHONE`; the header row is `only_below(PHONE_H, …)` plus
  `only_under(PHONE_H, FOOT_H)`; the menu is `dashboard_nav(foot=True, tail=LILAC)`, with a right shoulder
  on pages closed on the right.
- **Priorities**: `shown_from()` adds a phone query (`max-height: SCROLL_MIN_H - 0.02`) to the variant of
  `SCROLL_PRIORITY` (the highest, 4); non-phone ranges start at `SCROLL_MIN_H`.
- **`by_screen(other, phone)`**: phone variants that the *width* needs stay on phones either way (Status'
  modes as one column, `phone_pill()` pills, Light's Controls in one row); `tiered()` is for height only.
- **`scroll_min_h(card, height)`**: a variant that needs more height than the phone has; a grid row
  `minmax(only_under(SCROLL_MIN_H, height),1fr)` (LCARdS' `view_layout` passes only `margin`, `*-self`,
  `z-index`, `grid-*`, `overflow*`, no `min-height`). Used by OPS (forecast ≥ `PANEL_T + 6 DATA_ROW`,
  `_ops_height()`): scroll height 425 px.
- **`lcars-flow.js`** (new card, deployed and registered as a resource; not used by the live dashboard yet):
  columns = the largest divisor of the card count whose columns are ≥ `min_w` (`panel_min_w()` of the
  longest channel title), each row with its own instance of the label column, rows ≥ `row_min`; sets its
  own min-height, which grows the scrolling row. Dosing: 4 columns on the tablet, 2 × 2 on the phone
  (scroll height 477 px). `validate.py` also walks a card's `label`.
- **Light on phones** with scrolling: the full Phase control (`single_s(phone=True)`), Controls in one row.
- **`shot.js`**: `SCROLL=<px>|end` scrolls every scrolling element and logs visible/total height.
- **Docs** updated: `DESIGN.md` (scroll rule, priorities, phones, `by_screen`, Dosing, `lcars-flow.js`),
  `README.md`, `AGENTS.md`, `OPERATIONS.md`.
- **Checked** (headless Chrome): all views at 734×337 (scroll heights 363 px, OPS 425, Dosing 477) and at
  1280×720, 1280×800, 1920×1080 ("nothing scrolls"); 1280×720 looks the same as the live dashboard;
  `scroll: off` builds and validates (same placement as before, restructured wrappers).
- **Phone placement** below `PHONE_H` 520 px (`PRIORITY_MIN_H[1]`; priority 0 = always, `tiered()`'s lowest
  variant is the fallback): header not rendered (row 0 px via `only_below()`), menu in the foot bar
  (`dashboard_nav(foot=True)`, `SHORT_LABELS`), weekday + time and the pump alert in the foot bar
  (`clock(phone=True)`), no LCARS numbers (`code_font()`; cards hide `em` in a media query).
- **Per page, phones** (now only with `scroll: off`; with scrolling see the scrolling round): OPS without Next 7 days; Waste timeline only; Status modes as one column of pills;
  Light with 4 phase rows and one row of Controls; Dosing without Weekdays, compact bottle (`lcars-tank.js`
  media query); `phone_pill()` for pills (LCARdS text paddings are px only).
- View height leaves out HA's safe-area insets; `top_bars()` works with `Len` columns.
- Tooling: `LCARS_DASHBOARD` env for `deploy.py`, the build and `shot.js`; `SAFE` in `shot.js` emulates
  safe areas; `tools/diag_view.py`; `validate.py` accepts `clamp()`/`calc()`/`min()` font sizes.
- Verified: 1920×1080 and 1280×800 identical to the live dashboard; 1280×720 identical except the sidebar,
  whose Motion block used to be cut off there (now it fits); 1280×600 scales in between.

## Open issues (last screenshots at 734×337)

- **Scrolling not yet checked on the real iPhone** (only headless Chrome). Next: user looks at `lcars-dev`.
- Sizes still follow the real viewport (phone minimums), so in the extra room fillers and `1fr` pieces
  stretch (Status' and Light's lower parts, Light's Controls pills get tall). Possible next step: lay the
  content out at `SCROLL_MIN_H` sizes (a CSS variable instead of `100dvh` in `Len` and the cards; widths
  that line up with the fixed bars must keep following the real viewport).
- Right frame on phones: see decisions (not started).
- Dosing 2 × 2: the bottle gets only ~3 data rows and still uses its compact phone variant (`lcars-tank.js`
  media query at 520 px: a device convention, could follow the card's size instead).
- `scroll: off` on a phone: Dosing wraps 2 × 2 there too but can't scroll, so it is squeezed/cut.
- Waste: the hazmat collection's location text is wider than its column and cut at the left.
- Media: library titles narrow ("LIKED S…"), transport labels in the mid bar tight.
- Power: the 24 h chart is ~60 px high on the phone, its W labels crowd.
- Calendar: cells show only the event bar's edge, no text (month card's own sizing).
- Media: library titles are narrow; the transport labels in the mid bar are tight.
- Light: the phase graph's label ("DAYLIGHT") is cut at the top; channel labels tight.
- Value font (`--lcars-data-size` in the theme, 16 px minimum) could go lower on phones.
- The HA app's viewport was never measured.

## Workflow

```bash
ssh-add ~/.ssh/id_ed25519
cd <site> && lcars --dashboard lcars-dev deploy         # build + validate + save to the test dashboard
lcars setup                                             # cards (shared with the live dashboard!)
lcars --dashboard lcars-dev diag                        # re-add the diag view after each deploy
```

Card changes go live for the real dashboard too (same files): keep them identical at ≥ 720 px height.

## Before merging

- Deploy to `lcars-bridge`, check all sizes again.
- Remove this file and its pointer in `AGENTS.md`; decide whether the `lcars-dev` dashboard stays.
