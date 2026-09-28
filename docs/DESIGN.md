# Design rules

The rules every page follows. They were worked out with the project's owner on a real installation
and are built into the frame and the components; keep to them when you configure views or add
components, and change them only on purpose. [COMPONENTS.md](COMPONENTS.md) shows how each rule
appears in the configuration.

## General decisions

- **No page scrolling, except on phones.** Every view is exactly one viewport; frames are sized to
  their content, whatever is left of the page stays black. With `layout.scroll: auto` (the default), on
  a viewport lower than `scroll_min_h` (520 px, i.e. phones in landscape) the **sidebar and the content
  scroll together** between the fixed header (only its menu bar), mid bar and foot bar: their row is as
  much higher than the space they get as the viewport is lower than `scroll_min_h`, so the frame keeps
  its pieces instead of squeezing them. With `scroll: off` nothing ever scrolls, and phones get the
  reduced placement described under "Phones".
- **One layout for every screen**, like a responsive web framework: no separate phone design. Sizes
  follow the viewport height (see "Responsive sizes"); only placement changes, at a few breakpoints,
  through the display priorities.
- **Target screens**: 1920×1080 (desktop), 1280×800 (a 10" tablet in landscape; its real viewport is
  shorter because of system bars, so also 1280×720) and **phones in landscape** (an iPhone 16 gives the
  page 734×337 in Chrome with a 20 px home-indicator inset). Every page must fit and read well on all of
  them; check them after layout changes ([OPERATIONS.md](OPERATIONS.md#checking-layouts)).
- **Display priorities**: content that doesn't fit vertically is **not rendered**, rather than cut off
  or squeezed. A tier maps to the minimum viewport height it needs (0 always, 1 ≥ 520 px, i.e.
  everywhere but on phones, 2 ≥ 760 px, 3 ≥ 880 px, 4 ≥ 1000 px; `engine/screen.py`). With scrolling, a
  phone shows what the highest tier shows, whatever its height: the page scrolls, so nothing is left
  out. A component that needs more height than the phone has declares it (`min_height()`), and the
  scrolling row grows by it (a grid row minimum that is 0 on screens that don't scroll; LCARdS passes no
  `min-height`). Variants use HA's `screen` visibility condition: `hui-card` doesn't create a card that
  isn't shown, so a variant costs nothing on the device. The fallback for a frame that no longer fits:
  drop its shoulders first, then leave it out.
- **Voyager palette** (`engine/palette.py`): orange, butterscotch, peach, almond, violet, lilac, bluey,
  peri, ice, rose, red, sunflower, gray, earth (muted orange for large fillers) and bone (light blocks).
  Hex on purpose, so LCARdS alert modes don't shift them.
- **Colours stay semantic** for states: ice = OK/running, sunflower = warning/manual, red = critical,
  grey = off.
- **Alerts colour the page frame** (site `alert`, `lcars-alert.js`): every piece of the page frame
  (elbows, bars, sidebar blocks, the header's link block and menu, the titles and the clock in the bars'
  gaps) takes the alert's colour, the one exception to the colour families; the active item stays
  near-white. The content and the page title stay as they are; what happened is said in a dialog over
  the page: an LCARS frame in the alert's colour (heading in the top bar's gap, as tall as the bar), the
  text, and the pills Details and Acknowledge. The dialog is the only thing that ever covers the page.
- **One colour family per frame** (after Voyager screens and the Voyager theme on thelcars.com, probably
  Okuda's own design language). Every piece that sits in a frame (elbows, pillar blocks, bar segments,
  LCARS buttons in a bar or pillar) keeps that frame's family: e.g. the upper frame in blues, the lower
  one in oranges. Colours are never shuffled across a frame. **Where two frames meet** (the bars
  between them), colours may mix and run into each other. **Exceptions**: states that must stand out
  (alerts, warnings); colours that carry data (calendar colours, channel colours, chart legend blocks);
  state colours on buttons (Play/Pause ice while playing). The **active item** (menu, sidebar,
  categories, output devices) is near-white with "◂" instead of orange, so it stands out in every
  family. The header frame is in the header family (blues and lilacs, the section menu too), everything
  below in the orange family (sidebar blocks in turn, earth filler, Motion, foot bar, right side); only
  the mid bar's plain segments on pages without titles mix (a meeting point).
- **All UI text is English.** Sensor states and event titles in other languages are mapped (`map`
  values, the site's `titles`). Dates use `en-GB` ("Fri 25/09 · tomorrow").
- **Menus are part of the frame.** The header frame's bar is the section menu; the sidebar blocks list
  the section's views and, at the bottom, the per-device **Motion** switch. **The sidebar is context
  navigation and nothing else, on every page** (no controls in it). A section's link (e.g. "Classic",
  to another dashboard) is the top piece of the header frame's pillar, above its elbow.
- **Foot bar**: as thick as its text (`FOOT_FONT`; the bar `FOOT_T` and the foot row follow from it).
  It ends in the local date/time (orange, as tall as the bar, in a gap of the bar like a caption) and a
  square peach **stardate** block. Both re-render every minute through `sensor.time`. Stardate: TNG form,
  1000 units per year, one decimal (≈ 53 min), anchored so that 1987 (TNG's first season, 41xxx) is
  41000–41999, so 2026 is 80000–80999.9.
- **Frame corners**: all corners around the content share one inner radius (`INNER_CURVE`). A mid
  elbow's outer radius is its row height (bar plus inner radius); the foot elbows use `FRAME_H`.
- **Every numbered thing has its own number**: all codes come from `lcars_code(key)` (a stable hash of
  a key, collision-checked). A view's sidebar block and its subtitle share one code (same thing).
  Nothing is hand-numbered. Pieces that merge into a shoulder carry **no** number.
- **Performance**: LCARdS is for the frame, blocks, readouts and controls. Dense graphics (grids of
  cells, segment bars, calendars, forecast, radar) are the light custom cards ([CARDS.md](CARDS.md))
  with plain HTML/CSS. Hundreds of LCARdS buttons crash a tablet's renderer ([NOTES.md](NOTES.md)).

## Responsive sizes

- **Fluid sizes** (`Len`, `fl()`, `font()` in `engine/sizes.py`; `sz()`, `fz()`, `len()` in the cards):
  every size is written at its full value, which it keeps from 720 px viewport height up, so tablets
  and desktops look the same. Below that it shrinks linearly with the height to its minimum share,
  reached at 400 px: 60 % by default, fonts 80 %, LCARS numbers in blocks 67 %, label columns 75 % (so
  their labels keep fitting), sidebar labels 60 %.
- **The frame shrinks much more than the content**: small screens get slim frames and shoulders.
  Sidebar/pillar width to 50 % (140 → 70 px), the mid bar and its titles to 47 % (43 → 20), inner
  curves and elbow extensions to 35 %, panel shoulders 50 %, panel pillars and decorative pillars 45 %,
  the main margin 40 %, the foot bar 80 % (it carries the phone's menu). Rows that grow with `dvh` keep
  doing so above 720 px and shrink below it (a data row: 28 px at 720, 20 px on a phone).
- A `Len` renders as CSS (`clamp(84px, calc(17.5dvh + 14px), 140px)`, sums as `calc()`), and the
  framework keeps doing its arithmetic with it (corners, title widths, the mid bar's pieces), so bar and
  content stay aligned at every height. LCARdS elbows take such CSS lengths and redraw on resize; LCARdS
  text paddings take px only, hence the phone variant of pills.
- **Phones** (viewport below 520 px; placement, not design): of the header only its **menu bar** is
  rendered (with scrolling: the navigation stays at the top), as thick as the foot bar, with its elbow
  (and the right shoulder on pages closed on the right); readouts, number columns and the page title
  are not. With `scroll: off` the header isn't rendered at all and the **section menu moves into the
  foot bar**. Either way the menu has short labels (a section's `short`), no numbers, the active section
  near-white without "◂", and it starts with the section's link (e.g. "Classic"), whose block on top of
  the header's pillar isn't rendered. The foot bar ends in weekday and time instead of date/time and
  stardate.
- **No LCARS numbers on phones**: they are decoration and would collide with the labels. LCARdS blocks
  get their number's font size as `code_font()` (0 below 520 px), the cards hide them in a media query.
- What a phone's **width** needs (narrow pills) is chosen for phones whether they scroll or not
  (`by_screen()`); what only its **height** needs goes by tier (dropped when the page scrolls). Frames
  narrower than their title rather wrap (the `matrix`) than clip it; a tank drops its scale by its own
  size (a container query), not the device's.
- HA pads the view by the safe areas (notch, home indicator); the view's height leaves them out.
- Heights are `dvh` (the visible height): on iOS `vh` is the height without the browser's toolbars.

## Page frame

The frame every page sits in (`frame.py`): header with the section menu, sidebar, mid bar, foot bar,
optionally a right side.

- **The content's top bar is the page frame's mid bar.** The columns below have no top bar of their
  own. Per content column the mid bar carries its **title** and its **context buttons**: controls that
  act on that column (a player's transport, a radar's play and step buttons, a month's Back / Today /
  Next). Context buttons are LCARS blocks (number top-left, label bottom-right), in their state colour
  where they have one.
- **Bar and content split at the same x.** A bar piece ends where its content column ends, with the
  same gap (`FRAME_GAP`, 6 px). `top_bars()` takes the top row's column widths (the view's `columns`)
  and writes each piece's width as CSS `calc()`, so bar and content stay aligned at any width. A piece
  may span several columns.
- **Titles in bars** (`title_text()`, `titled_bar()`): font size = bar thickness, always. The title sits
  on its alphabetic baseline, `(1 − 0.86) / 2 × size` above the bottom edge, so the capitals are centred
  (Antonio's cap height is 0.86 em). LCARdS' default baseline (`middle`) centres the font's em box and
  pushes the capitals against the top edge. A title sits next to the shoulder on its side, after (left)
  or before (right) a 14 px cap segment, in the column's colour.
- **Thickness**: the mid bar is 43 px when it carries titles and buttons; the header's menu bar 43 px on
  every page.
- **The header follows the page's right side**: on a page closed on the right, the menu bar ends in a
  shoulder that rises into a numbered block on the header's right edge, mirroring the link block and the
  elbow on the left, exactly as wide as the page's right side below. On a page open on the right the
  menu bar runs to the edge.
- **Context buttons of a card with local state** (the radar: playing, current frame) are a second
  instance of the same card showing only its buttons, linked to the other through a `group` and window
  events. Cards whose state is in HA (the player) need no link: every instance reads the entity.
- **A column whose pillar is the sidebar has no bracket of its own** (a player's "Now playing"). Other
  columns bring their pillar as content (label blocks, a library's categories).
- **Right side, per page**: either the frame is **closed on the right** (a shoulder runs down from the
  mid bar and one up from the foot bar, and the content supplies the pillar between them as its right
  edge, exactly that wide), or it is **open** and both bars run to the right edge. Both are valid. A
  column never gets its own bottom shoulder next to the foot bar (it looked wrong); it merges into the
  foot bar through the right frame instead.
- **The foot bar is the same on every page**: date/time and stardate stay at its end, just before the
  right shoulder on pages closed on the right.
- **One label column**: where a page has several sections of label blocks (the "database" style), all
  of them form one column next to the sidebar: every block the same width (the view's
  `label_width`), one under the other, through all sections. The first section's title is in the mid
  bar; each further section starts with a **section bar** (a bar that grows out of the column: a block
  as wide as the column, the title as tall as the bar, the rest of the bar), so the mid bar's title
  never reads as the title of the whole column. Flat bars rather than shoulders where height is tight:
  two shoulders cost a tablet 40 px, a calendar row. No bottom bars: a section ends at the next
  section's bar or the foot bar.
- **Inner frames where they make sense**: a section may be a small frame of its own inside the page
  frame, with a top shoulder and its title in the bar. Its pillar is the label column itself, the
  shoulder exactly as wide, so **the vertical frame pieces stay aligned** down the page. A section right
  above such a shoulder closes with a **thin bottom bar and a shoulder of the same outer radius** (a
  `split`), the two shoulders a frame gap apart. That bar runs to the right edge, under whatever stands
  beside the section. Where the page is too short, the shoulders go first.
- **A numbered pillar can be the frame's right side** (a camera's, sliders', a library's categories).
- **Two frames side by side face outwards** (a `pair`): pillars on the outer edges, their top bars meet
  in the middle as one line from shoulder to shoulder. A pillar in the middle of the page looks cut
  off. Between them, a column of numbered blocks without a function hanging from that line (the spine)
  gives the frames room; colours may mix there, where the frames meet.
- **A section is a frame** with a colour family of its own.
- **Button columns between content columns** (a player's output devices): LCARS blocks, numbered, each
  at most a fixed height, the active one near-white with "◂", **no filler** below (the rest stays black).
- Tried and rejected: controls in the sidebar (the sidebar stays navigation); a transport row under the
  player (buttons belong in the bar); a column's own bottom shoulder under a right pillar.

## Reference style

Inspired by LCARS "exterior overview" / "database" screens: brackets around groups, label blocks as
pillars, graphics next to values, restrained colour.

### Frames

- Every group sits in its own **bracket**: a pillar on one side with elbow **shoulders** at the ends
  that have a bar. Sizes: bar thickness `PANEL_T` 26 px, shoulder `PANEL_CORNER` 46 px, gaps between
  pillar pieces `PANEL_GAP` 4 px.
- **Title** in a gap of the top bar, in the frame colour, font as tall as the bar. A frame open at the
  top carries it in the bottom bar instead.
- **Open or closed is per page, not a rule.** A frame can leave out its bottom (or top) bar. Decide by
  what looks right.
- **Neighbouring lower frames face each other**: pillars (and shoulders) meet in the middle.
- **The pillar is made of content**: label blocks, a timeline's series blocks, or numbered decorative or
  control blocks (a `pillar`, the radar's buttons). Plain pillars only where there is nothing to put in
  them.
- **Seams**: the first pillar piece in the frame colour runs into the top shoulder without a gap and has
  no number; the last one (filler) runs into the bottom shoulder. Both overlap by 2 px, otherwise
  fractional zoom (110 %) leaves hairline seams.
- **Frames joined into an S** (a `chain`): a frame's bottom shoulder and the next one's top shoulder sit
  on one shared bar that carries the next frame's title.

### Content

- **Label blocks**: filled block, black label vertically centred and right-aligned, number top-left.
  Colour carries meaning where it can (a calendar's colour); bone for neutral data, the frame colour for
  fillers.
- **Values** next to their block, bold, in peri, aligned towards the block.
- **No half-empty frames**: the space beside a value carries a graphic, usually a segment bar
  (countdown, scale, 24 h window/span). LCARS frames are never mostly black inside.
- **Bars** (`lcars-bar.js`): 14 segments (one per 2 days for countdowns, 24 per day for time scales),
  inactive segments static at 18 % peri, lit segments in the row colour. They grow away from the pillar.
  A level at its minimum lights nothing. **Status bars** light every segment in the state's colour or
  none. Other modes can take their lit colour from the state too, a level can turn red below a
  threshold, and `days` lights weekdays from a list, optionally with a letter in each segment.
- **Switches have no bar**: a row that switches something (tap its block or value; hold: more-info)
  shows only its value. Bars are for readings.
- **Mode switches are LCARS buttons** (pills): rounded, in their state colour while on and grey while
  off. Actions that are hard to undo (marking something refilled or done) act on **hold**, on purpose.
- **Every pill goes through `pill_shape()`**: radius 40, label bottom right and number top left inset by
  18 px from the side and 5 px from the edge, so the rounded ends never cover them. Only the font size
  varies.
- **Timeline / week grids**: weekday header and day numbers, weekends dimmer, today lighter and its
  labels orange.

### Header

- Readouts with a section's key values, then **LCARS number columns** in the free space: 20 real
  sensors (power/energy meters first) as 4-digit hex codes (value × 100), read on page load, with a
  staggered colour waterfall. The fourth row only from tier 4.
- On screens at least 1600 px wide a **2 × 2 block of LCARS pills** (numbers, no function) right of the
  number columns; its column is 0 px below that (CSS `clamp()`: layout cards have no media queries).
- No local time in the header (it sits in the foot bar). Readout values scale with the viewport width
  (theme variable `lcars-readout-size`); the page title can differ from the menu label (a section's
  `title`).

### Animation

- Allowed: lit bar segments **flash white briefly** (2.5 % of a random 8–24 s cycle, no fade); number
  columns and logs run a colour waterfall; the radar loops its frames; the page frame pulses
  (1.6 s, in step) while an alert set to blink is unacknowledged. Nothing else moves.
- Every animation honours the per-device **motion switch** (`?lcars_motion=off`, the sidebar's
  "Motion"): LCARdS animations through the paused anime.js engine, the light cards by checking it
  themselves.

## URL rules

- HA dashboard paths **must contain a hyphen**; HA rejects `lcars` ("Url path needs to contain a
  hyphen"). Hence the default `lcars-bridge`.
- A view path is a **single segment** (`/lcars-bridge/<view>`), so views of a section with several are
  named `<section>-<view>` by default.
- A dashboard's path can't be renamed. Moving means creating a new dashboard.
- Query parameters: `?lcars_motion=off|on|toggle` (per device), `?lcars_bars=off|on|toggle` (for
  everyone, stored in HA: never in a start URL), `?disable_km` (kiosk-mode off).
