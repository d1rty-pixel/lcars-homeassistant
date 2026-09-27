"""Components: the building blocks views are composed of (docs/COMPONENTS.md).

A component is declared in the configuration as a mapping with a `type` and its fields. Each type is a
class registered with @component; it parses and checks its fields when the configuration loads and
renders to a card for a context (Ctx): the screen tier, whether it's a phone, the label column's width,
and so on.

Responsive behaviour: a component whose own layout changes with the screen (children shown only from a
tier on, values per tier, shoulders that give way to flat bars) sets `sensitive`. card() then renders it
for every tier and keeps the distinct variants (engine.screen.responsive()); components inside such a
render get a fixed tier and render only that.
"""
import dataclasses
import json
import re

from ..engine import sizes
from ..engine.codes import lcars_code
from ..engine.palette import colour as _colour, colours as _colours
from ..engine.screen import responsive, shown_from
from ..engine.sizes import Len, label_width

TYPES = {}


class ConfigError(ValueError):
    pass


def component(name):
    """Register a component class under its configuration type `name`."""
    def deco(cls):
        cls.type_name = name
        TYPES[name] = cls
        return cls
    return deco


@dataclasses.dataclass(frozen=True)
class Ctx:
    """What a component renders for."""
    site: object
    section: object = None
    view: object = None
    tier: int = 4             # display priority the render is for (engine/screen.py)
    phone: bool = False       # the render for a phone
    fixed: bool = False       # inside a responsive() pass: render only this tier
    label_w: object = sizes.LABEL_W   # the label column's width
    flat: bool = False        # frames give way to flat section bars (short screens)
    key: str = ""             # prefix of the LCARS numbers' keys

    def at(self, **kw):
        if "tier" in kw or "phone" in kw:
            kw.setdefault("fixed", True)
        return dataclasses.replace(self, **kw)

    def code(self, *parts):
        """The LCARS number of a thing under this context's key."""
        return lcars_code("/".join(p for p in (self.key, *parts) if p))


def build(node, where):
    """The component for a configuration node (a mapping with `type`)."""
    if isinstance(node, Component):
        return node
    if not isinstance(node, dict):
        raise ConfigError(f"{where}: expected a component (a mapping with 'type'), got {node!r}")
    t = node.get("type")
    if t not in TYPES:
        raise ConfigError(f"{where}: unknown component type {t!r} (known: {', '.join(sorted(TYPES))})")
    return TYPES[t](node, where)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


class Component:
    """Base class. Subclasses list their fields in `fields` ({name: default}; REQUIRED for required ones)
    and implement render(ctx). Common fields of every component:

    show_from: the lowest tier it is rendered at (hidden on shorter screens, see engine/screen.py)
    phone:     false = not rendered on phones
    pillar:    a pillar of numbered blocks next to it (see with_pillar())
    key:       the key its LCARS numbers derive from (default: from its place in the configuration)
    margin:    CSS margin around it within its cell
    height:    its height in a stack, split or columns (height_spec(): data rows, fill, {timeline: n}, CSS)
    """
    type_name = "?"
    fields = {}
    common = {"type": None, "show_from": 0, "phone": True, "pillar": None, "key": None, "margin": None, "height": None}

    def __init__(self, node, where):
        self.where = where
        self.node = node
        known = {**self.common, **self.fields}
        unknown = sorted(set(node) - set(known))
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(unknown)} for type {self.type_name} "
                              f"(fields: {', '.join(sorted(k for k in known if k != 'type'))})")
        for k, default in known.items():
            if default is REQUIRED and k not in node:
                raise ConfigError(f"{where}: type {self.type_name} needs '{k}'")
            # a field named like a method (height) is kept as <name>_cfg
            attr = f"{k}_cfg" if callable(getattr(type(self), k, None)) else k
            setattr(self, attr, node.get(k, None if default is REQUIRED else copy_default(default)))
        self.show_from = int(self.show_from or 0)
        self.sensitive = False
        self.height_field = height_spec(self.height_cfg, f"{where}.height")
        self.parse()
        if self.pillar is not None:
            self.pillar = PillarSpec(self.pillar, f"{where}.pillar")

    # ── to override ──
    def parse(self):
        """Check and convert the fields (build child components)."""

    def render(self, ctx):
        raise NotImplementedError

    def height(self, ctx):
        """The height it needs (CSS), or None when it takes whatever it gets."""
        return None

    def min_height(self, ctx):
        """The height it needs at least where the page scrolls (CSS), or None."""
        return None

    # ── helpers ──
    def child(self, node, name):
        return build(node, f"{self.where}.{name}")

    def children(self, nodes, name):
        if not isinstance(nodes, list):
            raise ConfigError(f"{self.where}.{name}: expected a list")
        return [build(n, f"{self.where}.{name}[{i}]") for i, n in enumerate(nodes)]

    def visible(self, ctx):
        """Rendered at this context's tier (and on a phone)?"""
        if ctx.phone and self.phone is False:
            return False
        return ctx.tier >= self.show_from

    def own_key(self, ctx, default):
        return ctx.at(key=self.key or (f"{ctx.key}/{default}" if ctx.key else default))

    def card(self, ctx):
        """The card for `ctx`: all tiers' variants where the layout changes, else the one render."""
        if self.sensitive and not ctx.fixed:
            return responsive(lambda c: self._with_pillar(self.render(c), c), ctx)
        return self._with_pillar(self.render(ctx), ctx)

    def _with_pillar(self, card, ctx):
        if self.pillar is not None:
            card = self.pillar.wrap(card, ctx)
        if self.margin:
            from ..engine.cards import at, grid
            card = grid('"v"', "1fr", "1fr", [at(card, "v", margin=self.margin)], gap="0")
        return card


REQUIRED = object()


def height_spec(value, where):
    """A height from a configuration: a number of data rows (a label column's rows and gaps), "fill",
    {timeline: n} (as high as a day timeline of n series with its shoulder), or CSS."""
    if value is None:
        return None
    if value == "fill":
        return "1fr"
    if isinstance(value, (int, float)):
        return sizes.rows_h(value) if float(value).is_integer() else f"calc({sizes.DATA_ROW} * {value:g})"
    if isinstance(value, dict) and "timeline" in value:
        return sizes.chart_height(int(value["timeline"]))
    if isinstance(value, str):
        return css_expr(value, None, where)
    raise ConfigError(f"{where}: expected a height (rows, fill, {{timeline: n}} or CSS), got {value!r}")


def copy_default(v):
    return json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v


def tiered_value(value, tier, where="value"):
    """A value that may differ per tier: {tier: value, ...} means from that tier on (the lowest key
    also below it), anything else is the value everywhere."""
    if isinstance(value, dict) and value and all(isinstance(k, int) or str(k).isdigit() for k in value):
        steps = sorted((int(k), v) for k, v in value.items())
        out = steps[0][1]
        for t, v in steps:
            if tier >= t:
                out = v
        return out
    return value


def is_tiered(value):
    return isinstance(value, dict) and bool(value) and all(isinstance(k, int) or str(k).isdigit() for k in value)


def colour(value, where, default=None):
    return _colour(value, where) if value is not None else default


def colour_map(value, where):
    return _colours(value, where) if value is not None else None


NAMED_WIDTHS = ("label", "decor")


def width(value, ctx=None, where="width", number=label_width):
    """A width from a configuration: "label" (the label column), "decor" (a decorative pillar), a number
    (px at full size, shrinking like a label column; number= converts it), or CSS, in which `{...}` holds
    a fluid expression (css_expr())."""
    if value in (None, "label"):
        return ctx.label_w if ctx else sizes.LABEL_W
    if value == "decor":
        return sizes.DECOR_W
    if isinstance(value, (int, float)):
        return number(value)
    if isinstance(value, str):
        return css_expr(value, ctx, where)
    raise ConfigError(f"{where}: expected a width (label, decor, a number or CSS), got {value!r}")


def css_expr(text, ctx=None, where="size"):
    """CSS with fluid sizes in braces: {fl(140)} (140 px at full size, following the viewport height),
    {label} (the label column's width), {decor} (a decorative pillar's), and + - * / with numbers (px),
    e.g. "calc(clamp({fl(140)}, 11vw, 220px) + {label} + 16px)"."""
    if "{" not in text:
        return text
    names = {"fl": sizes.fl, "label": ctx.label_w if ctx else sizes.LABEL_W, "decor": sizes.DECOR_W,
             "Len": Len, "label_width": label_width}

    def ev(m):
        try:
            return str(Len.of(eval(m.group(1), {"__builtins__": {}}, names)))   # noqa: S307  (names only)
        except Exception as e:
            raise ConfigError(f"{where}: can't evaluate {{{m.group(1)}}}: {e}")
    return re.sub(r"\{([^{}]+)\}", ev, text)


def row_height(value, where="height"):
    """A row height: a number of data rows (1.3 = 1.3 × a data row), "fill", or CSS."""
    if value in (None, 1):
        return sizes.DATA_ROW
    if value == "fill":
        return "1fr"
    if isinstance(value, (int, float)):
        return f"calc({sizes.DATA_ROW} * {value:g})"
    if isinstance(value, str):
        return value
    raise ConfigError(f"{where}: expected a row height (a number of rows, fill, or CSS), got {value!r}")


def action(value, where):
    """A tap/hold action: toggle, more-info, none, navigate:<path>, url:<url>, or an HA action mapping
    (call-service with service / data / target is written as {action: perform-action, ...} too)."""
    if value is None:
        return None
    if isinstance(value, str):
        if value in ("toggle", "more-info", "none"):
            return {"action": value}
        if value.startswith("navigate:"):
            return {"action": "navigate", "navigation_path": value.split(":", 1)[1]}
        if value.startswith("url:"):
            return {"action": "url", "url_path": value.split(":", 1)[1]}
        raise ConfigError(f"{where}: unknown action {value!r} (toggle, more-info, none, navigate:<path>, url:<url>, "
                          "or a mapping)")
    if isinstance(value, dict):
        a = dict(value)
        if "service" in a and "action" not in a:
            a["action"] = "call-service"
        if a.get("action") == "call-service" and "data" in a and "service_data" not in a:
            a["service_data"] = a.pop("data")
        return a
    raise ConfigError(f"{where}: expected an action, got {value!r}")


class PillarSpec:
    """A pillar of numbered blocks without a function next to a component (docs/DESIGN.md "The pillar is
    made of content"): colours (one block each), side (right), filler (a piece in the frame colour that
    runs to the end, e.g. into a shoulder), width (decor), rows (true: blocks one data row high, as part
    of a label column; the filler takes the rest)."""

    def __init__(self, node, where):
        if isinstance(node, list):
            node = {"colours": node}
        if not isinstance(node, dict):
            raise ConfigError(f"{where}: expected a list of colours or a mapping")
        unknown = set(node) - {"colours", "side", "filler", "width", "rows"}
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")
        self.colours = [_colour(c, f"{where}.colours") for c in node.get("colours", [])]
        self.side = node.get("side", "right")
        self.filler = colour(node.get("filler"), f"{where}.filler")
        self.width_spec = node.get("width", "decor")
        self.rows = bool(node.get("rows", False))
        self.where = where

    def wrap(self, content, ctx):
        from .layout import with_pillar
        return with_pillar(content, ctx, self.colours, side=self.side, filler=self.filler,
                           width=width(self.width_spec, ctx, self.where), row=sizes.DATA_ROW if self.rows else None)


def hidden_below(card, comp):
    """A card shown only from the component's show_from tier on (for containers that don't re-render)."""
    return shown_from(card, comp.show_from) if comp.show_from else card


__all__ = ["Component", "Ctx", "component", "build", "ConfigError", "REQUIRED", "tiered_value", "is_tiered",
           "colour", "colour_map", "width", "row_height", "action", "slug", "Len"]
