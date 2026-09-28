"""Power components: the live load of several consumers (lcars-distribution.js) and their energy per day or
month (lcars-energy.js). Both take the same list of consumers, so a view can share it (e.g. through `vars`):
entity (the power sensor), energy (the energy sensor), label, colour."""
from ..engine.codes import lcars_code
from ..engine.palette import ACTIVE, BONE, DIM, GRAY, INK, ORANGE, ORANGE_FAMILY, PERI, WHITE, rgba
from ..engine.sizes import DATA_GAP, DATA_ROW, TL_GAP, TL_ROW, Len, rows_h
from .base import REQUIRED, Component, ConfigError, colour, component
from .data import FONT

CONSUMER_FIELDS = {"entity", "energy", "label", "colour"}


def consumers(items, where, need):
    """The consumers as dicts with the colour resolved; `need`: the sensor field each must have."""
    if not isinstance(items, list) or not items:
        raise ConfigError(f"{where}: a list of consumers ({{entity, energy, label, colour}})")
    out = []
    for i, c in enumerate(items):
        w = f"{where}[{i}]"
        if not isinstance(c, dict) or "label" not in c:
            raise ConfigError(f"{w}: a consumer is a mapping with a label ({', '.join(sorted(CONSUMER_FIELDS))})")
        unknown = set(c) - CONSUMER_FIELDS
        if unknown:
            raise ConfigError(f"{w}: unknown field(s) {', '.join(sorted(unknown))}")
        if not c.get(need):
            raise ConfigError(f"{w}: needs `{need}`")
        out.append({**c, "colour": colour(c.get("colour"), f"{w}.colour", ORANGE_FAMILY[i % len(ORANGE_FAMILY)])})
    return out


@component("distribution")
class Distribution(Component):
    """The live power of several consumers as EPS conduits (lcars-distribution.js): a row per consumer (its
    label block as part of the label column, the value, a conduit of segments on a log scale up to `max`
    with a wave of energy running through it, faster the higher the load, and its share of the total),
    below a total row whose segments show the load's distribution in the consumers' colours.
    consumers: [{entity, label, colour}]; total: the total row's label (null: no total row);
    total_colour: its block's colour."""
    fields = {"consumers": REQUIRED, "total": "Total", "total_colour": "bone", "max": 2500, "segments": 32}

    def parse(self):
        self.items = consumers(self.consumers, f"{self.where}.consumers", "entity")

    def count(self):
        return len(self.items) + (1 if self.total else 0)

    def render(self, ctx):
        card = {"type": "custom:lcars-distribution",
                "consumers": [{"entity": c["entity"], "label": c["label"], "colour": c["colour"],
                               "code": ctx.code("consumer", c["label"])} for c in self.items],
                "max": self.max, "segments": int(self.segments), "wave": 16, "speed": [7000, 2400],
                "label_w": str(Len.of(ctx.label_w)), "value_w": "clamp(84px, 8vw, 150px)",
                "share_w": "clamp(44px, 4vw, 72px)", "row": TL_ROW, "gap": TL_GAP,
                "colours": {"off": rgba(PERI, 0.18), "text": PERI, "dim": GRAY, "ink": INK, "flash": WHITE},
                "font": FONT}
        if self.total:
            card["total"] = {"label": self.total, "colour": colour(self.total_colour, f"{self.where}.total_colour", BONE),
                             "code": ctx.code("consumer", "total")}
        return card

    def height(self, ctx):
        # timeline rows (a little lower than data rows), so the energy chart below keeps room on tablets
        n = self.count()
        return f"calc({n} * {TL_ROW} + {Len.of((n - 1) * TL_GAP)})"

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" else None


RANGES = [{"label": "7D", "days": 7}, {"label": "28D", "days": 28}, {"label": "12M", "months": 12}]


@component("energy")
class Energy(Component):
    """The energy of several consumers per day or month as stacked columns (lcars-energy.js), from HA's
    long-term statistics: the running period's top piece lights up now and then, the line above reads the
    range's total and mean (tap a column: its breakdown). A toggle block (toggle: its colour; null: none)
    below the range buttons switches to a graph: the mean load in W per hour (per day for months), each
    consumer an area on a log scale above a zero line, their total (total: its colour) mirrored below it
    (tap: the breakdown at that time). Its range buttons (buttons: their colours) are blocks of the
    label column, the filler below them. series: [{energy (or entity), label, colour}], e.g. the same list
    as a `distribution`; ranges: [{label, days | months}]; unit: kWh (HA converts)."""
    fields = {"series": REQUIRED, "ranges": None, "buttons": ["violet", "lilac", "peri"], "filler": "lilac",
              "toggle": "bluey", "total": "bone", "unit": "kWh", "min_rows": 7}

    def parse(self):
        series = self.series
        if isinstance(series, list):     # a consumer's `entity` is its energy sensor where it has no `energy`
            series = [{**s, "energy": s.get("energy") or s.get("entity")} if isinstance(s, dict) else s for s in series]
        self.items = consumers(series, f"{self.where}.series", "energy")
        self.range_list = self.ranges or RANGES
        for i, r in enumerate(self.range_list):
            if not isinstance(r, dict) or "label" not in r or not (r.get("days") or r.get("months")):
                raise ConfigError(f"{self.where}.ranges[{i}]: {{label, days}} or {{label, months}}")
        if len(self.buttons) < len(self.range_list):
            raise ConfigError(f"{self.where}.buttons: a colour per range ({len(self.range_list)})")

    def render(self, ctx):
        key = ctx.key
        return {"type": "custom:lcars-energy",
                "series": [{"entity": c["energy"], "label": c["label"], "colour": c["colour"]} for c in self.items],
                "ranges": [{k: r[k] for k in ("label", "days", "months") if r.get(k)} for r in self.range_list],
                "unit": self.unit,
                "pillar": {"width": ctx.label_w, "gap": DATA_GAP, "row": DATA_ROW, "side": "left", "active": ACTIVE,
                           "filler": colour(self.filler, f"{self.where}.filler"), "ink": INK,
                           "blocks": [{"colour": colour(c, f"{self.where}.buttons"),
                                       "code": lcars_code(f"{key}/range/{r['label']}")}
                                      for c, r in zip(self.buttons, self.range_list)],
                           **({"toggle": {"colour": colour(self.toggle, f"{self.where}.toggle"),
                                          "code": lcars_code(f"{key}/view")}} if self.toggle else {})},
                "colours": {"grid": GRAY, "axis": DIM, "text": PERI, "dim": DIM, "today": ORANGE, "flash": WHITE,
                            "total": colour(self.total, f"{self.where}.total")},
                "font": FONT}

    def min_height(self, ctx):
        return rows_h(self.min_rows)

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" else None
