# Notes: root causes and LCARdS gotchas

All of this was verified live against HA 2026.9.3, LCARdS 2026.9.0,
HA-LCARS 4.1.3 and UIX 8.3.1 in Chrome.

## "Konfigurationsfehler" everywhere: registry load-order race

Symptom: every LCARdS card (or a whole `lcards-layout-view`) shows HA's
"Custom element doesn't exist" error. It happens intermittently locally and
almost always through the external reverse-proxied URL.

Root cause:
1. HA's `app.js` installs `@webcomponents/scoped-custom-element-registry`, which
   replaces `window.customElements`.
2. LCARdS is loaded via `extra_module_url`, and on fast loads it finishes
   `customElements.define(...)` *before* that polyfill exists.
3. The elements then live only in the native registry.
   `document.createElement('lcards-button')` yields a real `LCARdSButton`, but the
   polyfill's `get()`/`whenDefined()` return nothing, so HA renders error cards.

Workaround: `ha/www/lcards-registry-fix.js`, a Lovelace resource. HA loads those
after `app.js`. The script re-defines each natively defined LCARdS class with the
polyfill. The polyfill's `define()` skips the native define when the tag already
exists, so this is safe. The script needs the explicit tag list, so regenerate
it with `tools/gen_registry_fix.py` after LCARdS updates.

This is not reported upstream yet.

## Why a separate view theme ("LCARS Aquarium")

- HA-LCARS injects card styles through UIX. They paint every standard card
  lavender (quaternary background), so the embedded calendar, to-do, weather and
  radar cards looked wrong.
- A per-card `uix: style:` is ignored for cards created inside
  `lcards-layout-card`. The `uix-node` only carries the theme styles.
- The view theme is therefore standalone and declares its own (empty) UIX theme.
  UIX then stops applying HA-LCARS card styles, and standard cards render black in
  the Voyager palette.
- The theme must define `--lcars-font` and friends. LCARdS text uses
  `var(--lcars-font), …`, and one undefined var invalidates the whole
  `font-family` declaration.
- The theme lives in its own file because HACS rewrites `themes/lcars/lcars.yaml`
  on every HA-LCARS update.

## LCARdS config gotchas

- Preset text fields (`label`, `name`, `state`) default to `show: false`, so set
  `show: true` explicitly.
- `elbow.segment.color` must be a map (`{default: "#hex"}`). A plain string is
  spread into the theme defaults and silently ignored, although the docs allow it.
- Elbow `bar_height` must be at least 10.
- `border.width` as an object needs all four sides. Missing sides fall back to
  the theme width and draw an outline.
- Grid `1fr` tracks are `minmax(auto, 1fr)`: card min-heights (presets set a
  theme `min_height`) inflate rows past the viewport. The generator rewrites every
  `Nfr` to `minmax(0,Nfr)` and sets `min_height: 0` on LCARdS cards.
- Jinja `{% %}` blocks render as `[object Object]`, and `{{ }}` is flaky. Use
  `[[[ JS ]]]` or `{entity.state}` tokens. The token already includes the unit.
- The `gauge` slider does not render vertically, so use vertical `pills-basic`
  with `control.locked: true` for read-only level columns.
- The `text-reveal` animation made the text disappear for good, so it is not used.
- The official `lcards-schema.json` has generator bugs: `$ref` where lists belong,
  `enum: []` for text `position` and slider `preset`, and no
  `additionalProperties: false`. `tools/validate.py` works around all three. Also,
  `sounds` is declared only on the slider, although every card reads it (from
  `LCARdSCard`), so the validator copies it onto the other cards.
- Charts: `data_sources: {x: {entity, history: {hours: 24}}}`, then
  `sources: [{datasource, buffer: main, name}]`. Also set `style.yaxis.decimals`
  and `style.formatters`, or the axis shows float noise.
- Chart sizing: lcards-chart gives ApexCharts the container's pixel size once and
  never resizes, so charts rendered during layout settling came out too narrow.
  `FLUID` sets width/height to 100 % and turns the animation off, because ApexCharts
  ignores parent resizes while it animates. Frame charts with `overflow: hidden`:
  the Apex canvas sticks out ~24 px below the SVG, and the scrollbars from
  `overflow: auto` shrink the container.
- Chart legend names come from the `data_sources` key on live updates
  (`series_names` only applies to the first render), so key sources by display name.
- ApexCharts' log y-axis rejects negatives. The mirrored power chart maps values
  with an `expression` processor (`sign * log10(1 + W)`, applied to history too)
  and draws W ticks as `chart_options.annotations`. The schema declares only
  `type`/`from` on processors, so `tools/validate.py` adds `expression`/`sources`.

## Testing caveat

Screenshots from an automated, backgrounded Chrome tab often show stale or
half-rendered frames, because rAF is throttled. Query the DOM or wait inside the
page before capturing. Missing cards in a screenshot are usually not real.
