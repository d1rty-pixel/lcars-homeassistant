"""LCARS pills: buttons that switch an entity or run an action, and numbered pills without a function
between them (docs/DESIGN.md "Mode switches are LCARS buttons")."""
import copy

from ..engine.cards import at, block, grid, phone_pill, pill_shape
from ..engine.palette import GRAY
from ..engine.sizes import DATA_GAP, DATA_ROW, font
from .base import REQUIRED, Component, ConfigError, action, colour, component, slug
from .values import value_js

PILL_FIELDS = {"label", "entity", "on", "off", "colour", "tap", "hold", "decor", "key"}


def mode_button(label, entity, on, off, code, size=20):
    """Rounded LCARS button that switches `entity`: in `on` while on, `off` while off (hold: more-info)."""
    card = block(off, label, code, size=size)
    card.update({"entity": entity, "interactive": True, "tap_action": {"action": "toggle"},
                 "hold_action": {"action": "more-info"}})
    card["style"] = {"card": {"color": {"background": {"on": on, "off": off, "default": GRAY}}}}
    return pill_shape(card)


@component("pills")
class Pills(Component):
    """A grid of LCARS pills (docs/COMPONENTS.md "pills"). Items:

        {label, entity, on, off}         switches the entity (tap), its colour by state (hold: more-info)
        {label, colour, tap, hold, entity}   runs actions (e.g. hold to confirm something on purpose)
        {decor: colour}                  a numbered pill without a function

    columns: pills per row (widths: their CSS widths, default equal); size: label font size; gap: CSS gap.
    phone_layout: how phones show them: {columns, decor (false: leave the numbered ones out), limit (the
    first n pills), rows: data (one data row high each, e.g. level with a label column), narrow (true:
    phone pills without numbers and with smaller insets), gap}."""
    fields = {"items": REQUIRED, "columns": None, "widths": None, "size": 17, "gap": "8px 12px", "phone_layout": None}

    def parse(self):
        self.specs = []
        for i, it in enumerate(self.items):
            w = f"{self.where}.items[{i}]"
            if not isinstance(it, dict):
                raise ConfigError(f"{w}: a pill is a mapping")
            unknown = set(it) - PILL_FIELDS
            if unknown:
                raise ConfigError(f"{w}: unknown field(s) {', '.join(sorted(unknown))}")
            self.specs.append(dict(it, where=w))
        self.columns = int(self.columns or len(self.specs))
        if self.phone_layout is not None and not isinstance(self.phone_layout, dict):
            raise ConfigError(f"{self.where}.phone_layout: a mapping (columns, decor, limit, rows, narrow, gap)")
        self.sensitive = self.phone_layout is not None

    def pill(self, spec, i, ctx):
        w = spec["where"]
        key = spec.get("key") or f"{ctx.key}/{slug(spec.get('label') or spec.get('decor') or i)}"
        from ..engine.codes import lcars_code
        code = lcars_code(key if "decor" not in spec else f"{ctx.key}/deco/{i}")
        if "decor" in spec:
            return pill_shape(block(colour(spec["decor"], f"{w}.decor"), None, code)), True
        label = value_js(spec.get("label"), f"{w}.label")
        if "on" in spec:
            card = mode_button(label, spec["entity"], colour(spec["on"], f"{w}.on"),
                               colour(spec.get("off", "gray"), f"{w}.off"), code)
        else:
            c = colour(spec.get("colour"), f"{w}.colour", GRAY)
            card = mode_button(label, spec.get("entity"), c, c, code)
            card["style"]["card"]["color"]["background"] = c
            card["tap_action"] = action(spec.get("tap", "more-info" if spec.get("entity") else "none"), f"{w}.tap")
            card["hold_action"] = action(spec.get("hold", "none"), f"{w}.hold")
            if not spec.get("entity"):
                card.pop("entity")
        if "tap" in spec and "on" in spec:
            card["tap_action"] = action(spec["tap"], f"{w}.tap")
        if "hold" in spec and "on" in spec:
            card["hold_action"] = action(spec["hold"], f"{w}.hold")
        card["text"]["label"]["font_size"] = font(self.size)
        return card, False

    def render(self, ctx):
        pills = [self.pill(s, i, ctx) for i, s in enumerate(self.specs)]
        cols, gap, row = self.columns, self.gap, "1fr"
        if ctx.phone and self.phone_layout:
            p = self.phone_layout
            if p.get("decor", True) is False:
                pills = [x for x in pills if not x[1]]
            if p.get("limit"):
                pills = pills[:int(p["limit"])]
            if p.get("narrow"):
                pills = [(phone_pill(c), d) for c, d in pills]
            cols = int(p.get("columns", cols))
            gap = p.get("gap", gap)
            if p.get("rows") == "data":
                row = DATA_ROW
                gap = p.get("gap", f"{DATA_GAP}px 0")
        cards = [copy.deepcopy(c) for c, _ in pills]
        names = [chr(97 + i) for i in range(len(cards))]
        n_rows = -(-len(cards) // cols)
        areas = " ".join('"' + " ".join((names[r * cols:(r + 1) * cols] + ["."] * cols)[:cols]) + '"'
                         for r in range(n_rows))
        widths = " ".join(self.widths) if self.widths and not (ctx.phone and self.phone_layout) else \
            " ".join(["1fr"] * cols)
        return grid(areas, widths, " ".join([row] * n_rows), [at(c, n) for c, n in zip(cards, names)], gap=gap)

    def count(self, ctx):
        return -(-len(self.specs) // self.columns)

