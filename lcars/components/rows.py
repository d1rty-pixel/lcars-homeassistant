"""Rows of a label column: label blocks that stack up as a frame's pillar, each with its value (and a
segment bar or a control) beside it (docs/DESIGN.md "Content")."""
from ..engine import sizes
from ..engine.cards import at, block, grid, label_block, value_text
from ..engine.codes import blink
from ..engine.palette import BAR_OFF, GRAY, INK, ORANGE_FAMILY, PERI, WHITE
from ..engine.sizes import DATA_GAP, DATA_ROW, VALUE_W, Len
from ..frame import BARS_VISIBLE
from .base import REQUIRED, Component, ConfigError, action, colour, colour_map, component, slug, width
from .values import value_js

BAR_SEGMENTS = 14    # one segment per 2 days for countdowns (0-28 days, like a 28-day timeline), 14 on scales
BAR_MODES = {        # mode -> default segments
    "countdown": BAR_SEGMENTS, "window": 24, "level": BAR_SEGMENTS, "span": 24, "state": BAR_SEGMENTS, "days": 7,
}
BAR_FIELDS = {"mode", "segments", "colour", "attribute", "min", "max", "states", "threshold", "days_per_segment",
              "start", "end", "labels", "alarm"}


def data_bar(entity, colour_, mode, segments, side, key, **extra):
    """Segment bar as one light custom card (lcars-bar.js): segment 0 sits next to the value (towards the
    pillar on `side`); lit segments flash white briefly at random rates fixed per bar."""
    bar = {"type": "custom:lcars-bar", "entity": entity, "mode": mode, "segments": segments,
           "days_per_segment": 28 // BAR_SEGMENTS, "side": side, "colour": colour_, "off": BAR_OFF,
           # cycle 8-24 s per segment, flashing white for 2.5 % of it (0.2-0.6 s)
           "blink": blink(key, segments), "off_fraction": 0.025, "flash": WHITE, "gap": 3, **extra}
    bar["visibility"] = BARS_VISIBLE
    return bar


def bar_card(spec, entity, default_colour, side, key, where):
    """A segment bar from a configuration mapping (see BAR_FIELDS and docs/COMPONENTS.md "Bars")."""
    if isinstance(spec, str):
        spec = {"mode": spec}
    if not isinstance(spec, dict) or spec.get("mode") not in BAR_MODES:
        raise ConfigError(f"{where}: a bar needs a mode ({', '.join(BAR_MODES)})")
    unknown = set(spec) - BAR_FIELDS - {"entity"}
    if unknown:
        raise ConfigError(f"{where}: unknown bar field(s) {', '.join(sorted(unknown))}")
    mode = spec["mode"]
    extra = {}
    for k in ("attribute", "min", "max", "threshold", "days_per_segment", "labels"):
        if k in spec:
            extra[k] = spec[k]
    if "start" in spec:
        extra["start_attr"] = spec["start"]
    if "end" in spec:
        extra["end_attr"] = spec["end"]
    if "states" in spec:
        extra["states"] = colour_map(spec["states"], f"{where}.states")
    if "alarm" in spec:      # level: {below: 50, colour: red}: lit segments in that colour below the value
        a = spec["alarm"]
        if not isinstance(a, dict) or "below" not in a:
            raise ConfigError(f"{where}.alarm: {{below: <value>, colour: <colour>}}")
        extra["alarm"] = {"below": a["below"], "colour": colour(a.get("colour", "red"), f"{where}.alarm.colour")}
    if mode == "days":
        extra.update({"ink": INK, "label_colour": GRAY, "font": "Antonio, sans-serif"} if "labels" in spec else {})
    c = colour(spec.get("colour"), f"{where}.colour", PERI if mode == "state" else default_colour)
    return data_bar(spec.get("entity", entity), c, mode, int(spec.get("segments", BAR_MODES[mode])), side, key, **extra)


def with_bar(value, bar, side, width_=VALUE_W):
    """Value next to the pillar, its bar filling the rest of the row."""
    if side == "right":
        return grid('"b v"', f"1fr {width_}", "1fr", [at(bar, "b", margin="clamp(6px, 1dvh, 10px) 0"),
                                                      at(value, "v")], gap="0 14px")
    return grid('"v b"', f"{width_} 1fr", "1fr", [at(value, "v"), at(bar, "b", margin="clamp(6px, 1dvh, 10px) 0")],
                gap="0 14px")


def pillar_rows(items, side="left", filler=None, label_w=sizes.DATA_LABEL_W):
    """Rows of (label card, value card): the label blocks stack up as the frame's pillar on `side`, each
    value sits next to its block. A filler colour continues the pillar below the last row down to the
    shoulder."""
    areas, cards = [], []
    for i, (lbl, value) in enumerate(items):
        areas.append(f'"v{i} l{i}"' if side == "right" else f'"l{i} v{i}"')
        cards += [at(lbl, f"l{i}"), at(value, f"v{i}")]
    rows = [DATA_ROW] * len(items)
    if filler:
        areas.append('". f"' if side == "right" else '"f ."')
        cards.append(at(block(filler), "f"))
        rows.append("1fr")
    widths = f"1fr {Len.of(label_w)}" if side == "right" else f"{Len.of(label_w)} 1fr"
    return grid(" ".join(areas), widths, " ".join(rows), cards, gap=f"{Len.of(DATA_GAP)} 16px")


ROW_FIELDS = {"label", "colour", "entity", "value", "value_colour", "bar", "tap", "hold", "triggers", "content", "key",
              "show_from"}


@component("rows")
class Rows(Component):
    """Rows of a label column (docs/COMPONENTS.md "rows"). Each row: label, colour, entity, value (see
    components/values.py), value_colour (a colour or a state map), bar (a segment bar next to the value),
    tap / hold (actions of the label block and the value, e.g. tap: toggle for a switch), triggers (other
    entities the value reads), content (a component instead of value and bar), show_from.

    side: where the label blocks are (the frame's pillar); filler: a colour that continues the pillar
    below the last row; label_width: the column's width (default: the page's label column)."""
    fields = {"rows": REQUIRED, "side": "left", "filler": None, "label_width": None}

    def parse(self):
        if not isinstance(self.rows, list) or not self.rows:
            raise ConfigError(f"{self.where}.rows: a list of rows")
        self.specs = []
        for i, r in enumerate(self.rows):
            w = f"{self.where}.rows[{i}]"
            if not isinstance(r, dict):
                raise ConfigError(f"{w}: a row is a mapping (label, entity, value, ...)")
            unknown = set(r) - ROW_FIELDS
            if unknown:
                raise ConfigError(f"{w}: unknown field(s) {', '.join(sorted(unknown))} (row fields: "
                                  f"{', '.join(sorted(ROW_FIELDS))})")
            spec = dict(r)
            spec["where"] = w
            spec["colour"] = colour(r.get("colour"), f"{w}.colour", ORANGE_FAMILY[i % len(ORANGE_FAMILY)])
            spec["show_from"] = int(r.get("show_from", 0))
            if "content" in r:
                from .base import build
                spec["content"] = build(r["content"], f"{w}.content")
            self.specs.append(spec)
        self.filler = colour(self.filler, f"{self.where}.filler")
        self.sensitive = any(s["show_from"] for s in self.specs)

    def label_w(self, ctx):
        return width(self.label_width, ctx, f"{self.where}.label_width") if self.label_width else ctx.label_w

    def visible_rows(self, ctx):
        return [s for s in self.specs if ctx.tier >= s["show_from"]]

    def count(self, ctx):
        return len(self.visible_rows(ctx))

    def row_cards(self, spec, ctx):
        w = spec["where"]
        align = "right" if self.side == "right" else "left"
        key = spec.get("key") or f"{ctx.key}/{slug(spec.get('label', ''))}"
        from ..engine.codes import lcars_code
        code = lcars_code(key)
        lbl = label_block(spec["colour"], spec.get("label", ""), code)
        tap, hold = action(spec.get("tap"), f"{w}.tap"), action(spec.get("hold"), f"{w}.hold")
        entity = spec.get("entity")
        if "content" in spec:
            value = spec["content"].card(ctx.at(key=key))
        else:
            vc = spec.get("value_colour")
            if isinstance(vc, dict):
                vcol = {"default": PERI, **colour_map(vc, f"{w}.value_colour")}
            else:
                vcol = colour(vc, f"{w}.value_colour", PERI)
            value = value_text(value_js(spec.get("value"), f"{w}.value"), entity, align, vcol)
            if spec.get("triggers"):
                value["triggers_update"] = list(spec["triggers"])
            if spec.get("bar") is not None and not (tap and tap.get("action") == "toggle"):
                value = with_bar(value, bar_card(spec["bar"], entity, spec["colour"], self.side, key, f"{w}.bar"),
                                 self.side)
        if tap or hold:
            # a row that acts: its block and its value both do (the value keeps more-info on tap unless set)
            lbl.update({"interactive": True, "entity": entity})
            if tap:
                lbl["tap_action"] = tap
            if hold:
                lbl["hold_action"] = hold
            if "content" not in spec:
                target = value if value.get("type") == "custom:lcards-button" else None
                if target is not None:
                    target["interactive"] = True
                    if tap:
                        target["tap_action"] = tap
                    if hold:
                        target["hold_action"] = hold
        return lbl, value

    def render(self, ctx):
        rows = [self.row_cards(s, ctx) for s in self.visible_rows(ctx)]
        return pillar_rows(rows, side=self.side, filler=self.filler, label_w=self.label_w(ctx))

    def height(self, ctx):
        if self.height_field:
            return self.height_field
        if self.filler:
            return None
        return sizes.rows_h(self.count(ctx))

    def edge(self, side, ctx):
        return self.label_w(ctx) if side == self.side else None
