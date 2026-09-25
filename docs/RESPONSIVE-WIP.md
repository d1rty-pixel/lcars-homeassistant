# Work in progress: responsive layout (branch `responsive-small-screens`)

Status notes for this branch. Read this first when continuing; delete it (and its pointer in `AGENTS.md`)
before merging to `main`. Installation-specific details (test dashboard, how to reach it) are in the
git-ignored `CLAUDE.local.md`.

## Goal and user decisions

- The dashboards must also work on an **iPhone 16 in landscape**, in **Chrome on iOS** (the user's browser;
  also through the HA app).
- **One codebase that adapts automatically, like Bootstrap** (user, explicit). No separate phone layouts or
  designs. Only *placement* may change per screen (through the display priorities). An earlier attempt
  that built every view twice with a compact profile was stopped by the user.
- On small screens **frames and shoulders significantly smaller** (user).
- On small screens **no generated LCARS numbers** (user).
- Accepted: on phones the header disappears and the **section menu moves into the foot bar**.
- User's verdict after the last round: "close, but not enough". Next session: ask what exactly still looks
  wrong (screenshots from the phone), or go through the pages at the real size below.

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

## What is implemented (committed on the branch)

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
- **Phone placement** below `PHONE_H` 520 px (`PRIORITY_MIN_H[1]`; priority 0 = always, `tiered()`'s lowest
  variant is the fallback): header not rendered (row 0 px via `only_below()`), menu in the foot bar
  (`dashboard_nav(foot=True)`, `SHORT_LABELS`), weekday + time and the pump alert in the foot bar
  (`clock(phone=True)`), no LCARS numbers (`code_font()`; cards hide `em` in a media query).
- **Per page, phones**: OPS without Next 7 days; Waste timeline only; Status modes as one column of pills;
  Light with 4 phase rows and one row of Controls; Dosing without Weekdays, compact bottle (`lcars-tank.js`
  media query); `phone_pill()` for pills (LCARdS text paddings are px only).
- View height leaves out HA's safe-area insets; `top_bars()` works with `Len` columns.
- Tooling: `LCARS_DASHBOARD` env for `deploy.py`, the build and `shot.js`; `SAFE` in `shot.js` emulates
  safe areas; `tools/diag_view.py`; `validate.py` accepts `clamp()`/`calc()`/`min()` font sizes.
- Verified: 1920×1080 and 1280×800 identical to the live dashboard; 1280×720 identical except the sidebar,
  whose Motion block used to be cut off there (now it fits); 1280×600 scales in between.

## Open issues (last screenshots at 734×337)

- Dosing: the "Next" value ("4 ml at 15:00 · tomorrow") is wider than a channel column and spills over.
  Proposed (not yet agreed): show only the day there, dose and time are in the row above.
- Power: the 24 h chart is ~60 px high on the phone, its W labels crowd.
- Calendar: cells show only the event bar's edge, no text (month card's own sizing).
- Media: library titles are narrow; the transport labels in the mid bar are tight.
- Light: the phase graph's label ("DAYLIGHT") is cut at the top; channel labels tight.
- Value font (`--lcars-data-size` in the theme, 16 px minimum) could go lower on phones.
- Not yet checked on the real phone after the last three rounds (dvh, slimmer frames, no numbers).
- The HA app's viewport was never measured.

## Workflow

```bash
ssh-add ~/.ssh/id_ed25519
LCARS_DASHBOARD=lcars-dev python3 tools/deploy.py        # build + validate + save to the test dashboard
bash tools/deploy_ha_files.sh                            # cards (shared with the live dashboard!)
LCARS_DASHBOARD=lcars-dev python3 tools/diag_view.py     # re-add the diag view after each deploy
```

Card changes go live for the real dashboard too (same files): keep them identical at ≥ 720 px height.

## Before merging

- Deploy to `lcars-bridge`, check all sizes again.
- Remove this file and its pointer in `AGENTS.md`; decide whether the `lcars-dev` dashboard stays.
