"""What a section shows in the header next to the page title (a section's `readouts`): readouts of key
values, LCARS number columns in the free space, and a block of decorative pills on wide screens."""
import json

from ..engine.cards import readout
from ..engine.palette import BRIGHT, ICE, PEACH
from ..engine.screen import tiered
from ..engine.sizes import font
from ..frame import header_buttons
from .base import REQUIRED, Component, ConfigError, colour, colour_map, component
from .data import CASCADE_MS
from .values import REL, value_js

HEX_ROWS, HEX_COLS = 4, 5


class HeaderItem(Component):
    """A header entry: header_item(ctx) gives the card and how many slots it spans."""
    span = 1

    def render(self, ctx):
        return self.header_item(ctx)[0]


@component("readout")
class Readout(HeaderItem):
    """A header readout: label over a large value. entity, label, value (components/values.py), colour (the
    value's: a colour or a state map), span (readout slots it takes, of four)."""
    fields = {"entity": REQUIRED, "label": REQUIRED, "value": None, "colour": None, "span": 1, "triggers": None}

    def header_item(self, ctx):
        c = self.colour
        col = colour_map(c, f"{self.where}.colour") if isinstance(c, dict) else colour(c, f"{self.where}.colour", PEACH)
        card = readout(ctx.site.resolve(self.entity), self.label, value_js(self.value, f"{self.where}.value"), col)
        if self.triggers:
            card["triggers_update"] = list(self.triggers)
        return (card, int(self.span)) if int(self.span) != 1 else card


@component("next_event")
class NextEvent(HeaderItem):
    """A header readout of the calendars' next event (the site's `calendars`, or `calendars`): show: title
    (the event's title, through the site's `titles`), when (its date, relative), today (how many today)."""
    fields = {"label": REQUIRED, "show": "title", "calendars": None, "colour": "orange"}

    def header_item(self, ctx):
        cals = self.calendars or [c["entity"] for c in ctx.site.calendars]
        prelude = ("const ids = " + json.dumps(cals) + "; "
                   "const ev = ids.map((id) => states[id]).filter((x) => x && x.attributes.start_time)"
                   ".map((x) => ({d: new Date(x.attributes.start_time.replace(' ', 'T')), m: x.attributes.message || '?', "
                   "all: x.attributes.all_day})).filter((e) => !isNaN(e.d)).sort((a, b) => a.d - b.d); ")
        if self.show == "title":
            js = ("[[[ " + prelude + "const e = ev[0]; if (!e) return '—'; const n = "
                  + json.dumps(ctx.site.titles, ensure_ascii=False) + "; return n[e.m] || e.m; ]]]")
        elif self.show == "when":
            js = "[[[ " + prelude + "const e = ev[0]; if (!e) return '—'; const d = e.d; " + REL + "return dm + ' · ' + rel; ]]]"
        elif self.show == "today":
            js = ("[[[ " + prelude + "const t = new Date().toDateString(); "
                  "return ev.filter((e) => e.d.toDateString() === t).length; ]]]")
        else:
            raise ConfigError(f"{self.where}.show: title, when or today")
        card = readout("sensor.time", self.label, js, colour(self.colour, self.where))
        card["triggers_update"] = cals
        return card


def number_sensors(site, n, seed=47174):
    """n sensors for the number columns, read live at build time: power/energy meters first, topped up with a
    fixed-seed random pick of other sensors whose value is a non-zero number (zeros would all show as
    0000). The site's numbers.exclude (parts of entity IDs) leaves sensors out, numbers.sensors names them."""
    import random
    cfg = site.numbers
    if cfg.get("sensors"):
        picks = list(cfg["sensors"])
        return (picks * (n // max(1, len(picks)) + 1))[:n]
    exclude = [str(x) for x in cfg.get("exclude", [])]
    power, other = [], []
    for st in site.states():
        eid, attrs = st["entity_id"], st["attributes"]
        if not eid.startswith("sensor.") or any(x in eid for x in exclude):
            continue
        try:
            value = float(st["state"])
        except ValueError:
            continue
        if (attrs.get("device_class") in ("power", "energy") or attrs.get("unit_of_measurement") in
                ("W", "kW", "Wh", "kWh")):
            power.append(eid)
        elif value != 0:
            other.append(eid)
    rng = random.Random(seed)
    picks = rng.sample(sorted(power), min(n, len(power)))
    picks += rng.sample(sorted(other), min(n - len(picks), len(other)))
    rng.shuffle(picks)
    return (picks + ["sensor.time"] * n)[:n]


def js_hex(entity):
    """JS: the sensor's value (x100) as a 4-digit hex code, e.g. 11.6 -> 0488."""
    return ("[[[ const v = parseFloat((states['" + entity + "'] || {}).state); if (isNaN(v)) return '----'; "
            "return (Math.round(Math.abs(v) * 100) % 65536).toString(16).toUpperCase().padStart(4, '0'); ]]]")


@component("numbers")
class Numbers(HeaderItem):
    """LCARS number columns from real sensors (see number_sensors()), each a hex code read when the page
    loads, with a staggered colour waterfall running over them. The last row has priority 4: below its
    viewport height one row fewer is rendered instead of a cut-off one."""
    fields = {"colours": None}

    def header_item(self, ctx):
        start, text, end = [colour(c, self.where) for c in (self.colours or [ICE, "#223366", BRIGHT])]
        picks = number_sensors(ctx.site, HEX_ROWS * HEX_COLS)

        def number_grid(n_rows):
            rows = [[js_hex(e) for e in picks[r * HEX_COLS:(r + 1) * HEX_COLS]] for r in range(n_rows)]
            return {"type": "custom:lcards-data-grid", "data_mode": "data", "rows": rows,
                    "grid": {"grid-template-columns": f"repeat({HEX_COLS}, auto)",
                             "grid-template-rows": f"repeat({n_rows}, 1fr)", "gap": "0 14px", "justify-content": "start"},
                    "style": {"font_size": font(15), "font_weight": "bold", "color": start, "align": "left"},
                    "animations": [{"trigger": "on_load", "preset": "cascade-color",
                                    "params": {"duration": CASCADE_MS, "colors": [start, text, end],
                                               "stagger_from": "first", "stagger_delay": 70}}]}
        return tiered({4: number_grid(HEX_ROWS), 1: number_grid(HEX_ROWS - 1)})


@component("decor")
class Decor(HeaderItem):
    """A 2 × 2 block of numbered LCARS pills without a function, on screens at least 1600 px wide."""

    def header_item(self, ctx):
        return header_buttons(ctx.section), "wide"


@component("empty")
class Empty(HeaderItem):
    """An empty readout slot."""

    def header_item(self, ctx):
        return None


__all__ = ["PEACH"]
