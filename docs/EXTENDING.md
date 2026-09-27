# Extending the framework

## How it is built

```
lcars.yaml ──► config.py ──► components (a tree) ──► frame.py + build.py ──► Lovelace JSON ──► HA
              expand ${{ }},    each renders to           the page frame,          lcars deploy
              repeat, data      LCARdS / light cards      finalize()
```

| Module | What it is |
|--------|------------|
| `lcars/cli.py` | the `lcars` command |
| `lcars/config.py` | loads `lcars.yaml`: interpolation, `repeat`, `data`, `plugins`; the model (`Site`, `Section`, `View`, `Alert`) |
| `lcars/build.py` | a Site → the dashboard's configuration; `finalize()`; entity checks |
| `lcars/frame.py` | the page frame: header (readouts, title, section menu), sidebar, mid bar (`top_bars()`), foot bar, alert |
| `lcars/components/` | the component types: `base.py` (Component, Ctx, registry, sizes and colours from the configuration), `layout.py`, `rows.py`, `controls.py`, `data.py`, `header.py`, `values.py` |
| `lcars/engine/` | `sizes.py` (fluid sizes, `Len`), `screen.py` (tiers, `responsive()`, `tiered()`, `by_screen()`), `palette.py`, `codes.py` (LCARS numbers), `cards.py` (grids, blocks, pills, elbows, titles) |
| `lcars/setup.py` | `lcars setup` / `doctor` / `init` |
| `lcars/ha.py`, `lcars/host.py` | HA's WebSocket API; file access to the HA host |
| `lcars/validate.py` | the check against LCARdS' JSON schema |
| `lcars/www/`, `lcars/themes/` | the light cards ([CARDS.md](CARDS.md)) and the view theme |

## A component of your own (plugin)

A plugin is a Python file next to `lcars.yaml`, listed under `plugins`. It registers component types:

```python
from lcars.components.base import REQUIRED, Component, colour, component
from lcars.engine.cards import text_card
from lcars.engine.sizes import DATA_ROW, font


@component("note")
class Note(Component):
    """A line of text in a colour, one data row high."""
    fields = {"text": REQUIRED, "colour": "peri"}          # every field it takes, with its default

    def render(self, ctx):                                   # -> a card (a dict)
        return text_card(self.text, "center-left", font(22), colour(self.colour, f"{self.where}.colour"))

    def height(self, ctx):                                   # what it needs in a stack (None: flexible)
        return DATA_ROW
```

```yaml
plugins: [plugins/note.py]
...
content: {type: stack, items: [{type: note, text: All decks report ready, colour: ice}, ...]}
```

[`examples/plugins/note.py`](../examples/plugins/note.py) is this example.

The pieces a component works with:

- **Fields** are checked when the configuration loads: unknown ones and missing `REQUIRED` ones are
  errors. They become attributes (`self.text`); a field named like a method (`height`) is kept as
  `<name>_cfg`. `parse()` converts them (build children with `self.child(node, "name")` /
  `self.children(list, "name")`, colours with `colour()`).
- **`render(ctx)`** returns the card. `ctx` carries the screen tier (`ctx.tier`, 0..4), `ctx.phone`, the
  page's label column width (`ctx.label_w`), `ctx.flat` (frames should be flat section bars) and
  `ctx.key`; `ctx.code("part")` gives a stable LCARS number. Render children with `child.card(ctx)`.
- **Sizes**: use `Len` / `fl()` / `font()` and the constants in `engine/sizes.py` (`DATA_ROW`,
  `PANEL_T`, …), never plain px, so the component follows the viewport height like everything else.
- **`height(ctx)`**, **`min_height(ctx)`** (the height it needs where the page scrolls) and
  **`edge(side, ctx)`** (the width of a pillar it brings on that side, so a frame around it uses it) are
  optional.
- **Responsive**: set `self.sensitive = True` in `parse()` when your render depends on `ctx.tier` or
  `ctx.phone`. `card()` then renders every tier and keeps the distinct variants (`engine/screen.py`);
  inside that pass, components render only the tier they are given.
- The primitives in `engine/cards.py` (`grid`, `at`, `block`, `label_block`, `pill_shape`, `elbow`,
  `title_text`, `titled_bar`, `value_text`) and the layout helpers in `components/layout.py` (`panel`,
  `section`, `with_pillar`, `bottom_shoulder`, `s_joint`) are what the framework's components use.

## Adding to the framework itself

A component that others can use belongs in `lcars/components/` (it registers when the package loads).
Document it in [COMPONENTS.md](COMPONENTS.md), use it in [`examples/home.yaml`](../examples/home.yaml),
and follow [DESIGN.md](DESIGN.md). Dense graphics become a light card in `lcars/www/`: a web component
without dependencies, its configuration documented at the top of the file, sizes through the shared
`fluid()` helpers, animations off with the motion switch, defined only if not defined yet. `lcars setup`
picks up new files in `lcars/www/` by itself.

## Checking a change

```bash
lcars build && python3 -m lcars.validate build/lcars_dashboard.json   # the schema check deploy runs
lcars --dashboard lcars-dev deploy                                     # a hidden test copy first
```

Then look at the result at the sizes that matter: **1280×720, 1280×800, 1920×1080 and a phone in
landscape (734×337 with a 20 px bottom inset)**. [OPERATIONS.md](OPERATIONS.md#checking-layouts)
describes the screenshot tool. No page may scroll except on phones; content that doesn't fit isn't
rendered (display priorities), and shoulders go first.

Refactoring the engine or a component: build a configuration before and after and compare the JSON
(the LCARS numbers and blink rates may change when keys change; everything else shouldn't).
