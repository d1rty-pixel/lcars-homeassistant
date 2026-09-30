"""Network components: a network's links and the data flowing through them (lcars-topology.js)."""
from ..engine.palette import GRAY, INK, ORANGE_FAMILY, PERI, RED, WHITE, rgba
from ..engine.sizes import TL_GAP, TL_ROW, Len
from .base import REQUIRED, Component, ConfigError, colour, component
from .data import FONT

NODE_FIELDS = {"label", "colour", "level", "down", "up", "status", "ok", "info", "info_unit", "info_round", "max", "tap"}


@component("topology")
class Topology(Component):
    """A network's links as conduits (lcars-topology.js): a row per node (its label block part of the label
    column; red while its `status` isn't one of its `ok` states), the rate towards it, two lanes (towards
    it: a wave running outward; back: a wave running inward, both on a log scale up to `max` and faster the
    higher the rate), the rate back and an `info` value (clients, latency). Children (`level` 1, 2) hang
    from the node above them: a narrower block behind a stub in the parent's colour.
    nodes: [{label, colour, level, down, up, status, ok, info, info_unit, info_round, max, tap}];
    unit: shown after the rates (the sensors' unit, e.g. Mb/s)."""
    fields = {"nodes": REQUIRED, "max": 1000, "unit": "Mb/s", "segments": 32, "info_width": 90,
              "down_colour": "red"}

    def parse(self):
        if not isinstance(self.nodes, list) or not self.nodes:
            raise ConfigError(f"{self.where}.nodes: a list of nodes ({{label, down, up, ...}})")
        self.items, parents = [], []
        for i, n in enumerate(self.nodes):
            w = f"{self.where}.nodes[{i}]"
            if not isinstance(n, dict) or "label" not in n:
                raise ConfigError(f"{w}: a node is a mapping with a label ({', '.join(sorted(NODE_FIELDS))})")
            unknown = set(n) - NODE_FIELDS
            if unknown:
                raise ConfigError(f"{w}: unknown field(s) {', '.join(sorted(unknown))}")
            level = int(n.get("level", 0))
            if level < 0 or level > len(parents):
                raise ConfigError(f"{w}.level: {level}, but the node above is at level {len(parents) - 1}")
            node = {**n, "level": level,
                    "colour": colour(n.get("colour"), f"{w}.colour", ORANGE_FAMILY[i % len(ORANGE_FAMILY)])}
            parents = parents[:level]
            node["stubs"] = [p["colour"] for p in parents]
            parents.append(node)
            self.items.append(node)

    def render(self, ctx):
        keep = ("label", "colour", "level", "down", "up", "status", "ok", "info", "info_unit", "info_round", "max",
                "tap", "stubs")
        return {"type": "custom:lcars-topology",
                "nodes": [{**{k: n[k] for k in keep if n.get(k) not in (None, [])},
                           "code": ctx.code("node", n["label"])} for n in self.items],
                "max": self.max, "unit": self.unit, "segments": int(self.segments), "wave": 16,
                "speed": [7000, 2400], "indent": 14,
                "label_w": str(Len.of(ctx.label_w)), "value_w": "clamp(84px, 8vw, 150px)",
                "info_w": str(Len.of(self.info_width)), "row": TL_ROW, "gap": TL_GAP,
                "colours": {"off": rgba(PERI, 0.18), "text": PERI, "dim": GRAY, "ink": INK, "flash": WHITE,
                            "down": colour(self.down_colour, f"{self.where}.down_colour", RED), "unknown": GRAY},
                "font": FONT}

    def height(self, ctx):
        n = len(self.items)
        return f"calc({n} * {TL_ROW} + {Len.of((n - 1) * TL_GAP)})"

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" else None
