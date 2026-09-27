"""Data components: values, bars and the light custom cards (lcars/www/*.js) that draw dense graphics
with plain HTML instead of hundreds of LCARdS buttons."""
import json
import math
import urllib.parse
import urllib.request

from ..engine import sizes
from ..engine.cards import at, block, grid, label_block, value_text
from ..engine.codes import blink, lcars_code
from ..engine.palette import (ACTIVE, ALMOND, BAR_OFF, BONE, BRIGHT, BUTTERSCOTCH, DIM, GRAY, ICE, INK, LILAC, ORANGE,
                              PEACH, PERI, RED, SUNFLOWER, WHITE, rgba)
from ..engine.sizes import (DATA_GAP, DATA_ROW, DECOR_W, PANEL_GAP, TL_AXIS, TL_GAP, TL_HEAD, TL_ROW, Len, css,
                            timeline_height)
from ..frame import BARS_VISIBLE
from .base import REQUIRED, Component, ConfigError, action, colour, colour_map, component, is_tiered, tiered_value
from .rows import bar_card
from .values import value_js

FONT = "Antonio, sans-serif"
CASCADE_MS = 1800   # one colour cycle of the number columns (and the log's waterfall, three times as long)
# Days, weekends and today in every calendar-like grid
GRID_COLOURS = {"empty": rgba(PERI, 0.1), "weekend": rgba(PERI, 0.05), "today": rgba(PERI, 0.22),
                "text": PERI, "text_weekend": GRAY, "text_today": ORANGE}


@component("value")
class Value(Component):
    """A single value (e.g. a cell of a matrix): entity, value (components/values.py), colour (a colour or
    a state map), align (left, right, center), triggers (other entities it reads), tap / hold."""
    fields = {"entity": None, "value": None, "colour": None, "align": "center", "triggers": None, "tap": None,
              "hold": None}

    def render(self, ctx):
        c = self.colour
        col = {"default": PERI, **colour_map(c, f"{self.where}.colour")} if isinstance(c, dict) else \
            colour(c, f"{self.where}.colour", PERI)
        align = self.align
        card = value_text(value_js(self.value, f"{self.where}.value"), self.entity,
                          "left" if align == "center" else align, col)
        if align == "center":
            card["text"]["value"].update({"position": "center", "padding": {}})
        if self.triggers:
            card["triggers_update"] = list(self.triggers)
        for k in ("tap", "hold"):
            a = action(getattr(self, k), f"{self.where}.{k}")
            if a:
                card[f"{k}_action"] = a
                card["interactive"] = True
        return card


@component("bar")
class Bar(Component):
    """A segment bar on its own (lcars-bar.js): entity plus the bar fields (docs/COMPONENTS.md "Bars")."""
    fields = {"entity": REQUIRED, "mode": REQUIRED, "segments": None, "colour": None, "attribute": None, "min": None,
              "max": None, "states": None, "threshold": None, "days_per_segment": None, "start": None, "end": None,
              "labels": None, "alarm": None, "side": "left"}

    def render(self, ctx):
        spec = {k: getattr(self, k) for k in ("mode", "segments", "colour", "attribute", "min", "max", "states",
                                              "threshold", "days_per_segment", "start", "end", "labels", "alarm")
                if getattr(self, k) is not None}
        return bar_card(spec, self.entity, PERI, self.side, ctx.key or self.where, self.where)


@component("timeline")
class Timeline(Component):
    """A day timeline (lcars-day-grid.js): a label block per series (the frame's pillar), the next `days`
    days as a grid, a cell lit on each day with an event. series: [{label, entity, colour, match}], match:
    "attribute" (the entity has an attribute per date, 'yyyy-mm-dd': Waste Collection Schedule) or "state"
    (its state is the date). head / axis: the colours of the pillar's top piece and the "Day" block."""
    fields = {"series": REQUIRED, "days": 28, "head": "orange", "axis": "orange", "axis_label": "Day"}

    def parse(self):
        self.series_specs = []
        for i, s in enumerate(self.series):
            w = f"{self.where}.series[{i}]"
            self.series_specs.append((s["label"], s["entity"], colour(s.get("colour"), f"{w}.colour", PEACH),
                                      s.get("match", "attribute")))

    def render(self, ctx):
        series = self.series_specs
        track_rows = [TL_HEAD] + [TL_ROW] * len(series) + [TL_AXIS]
        gap = f"{Len.of(TL_GAP)} 4px"
        day_grid = {"type": "custom:lcars-day-grid", "days": self.days, "rows": track_rows, "gap": gap,
                    "series": [{"entity": e, "colour": c, "match": m} for _, e, c, m in series],
                    "colours": dict(GRID_COLOURS), "font": FONT, "font_size": 15}
        areas = ['"lw days"'] + [f'"l{i} days"' for i in range(len(series))] + ['"lx days"']
        cards = [at(block(colour(self.head, self.where)), "lw")]   # pillar piece above the series, part of the shoulder
        cards += [at(label_block(c, label, ctx.code(label)), f"l{i}") for i, (label, _, c, _) in enumerate(series)]
        cards.append(at(label_block(colour(self.axis, self.where), self.axis_label, ctx.code("day")), "lx"))
        cards.append(at(day_grid, "days"))
        # the day grid repeats these row tracks internally, so its rows line up with the label blocks
        return grid(" ".join(areas), f"{Len.of(ctx.label_w)} 1fr", " ".join(track_rows), cards, gap=gap)

    def height(self, ctx):
        return timeline_height(len(self.series_specs))

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" else None


def calendar_list(site, entities=None):
    """The calendars (site `calendars`) with label, colour and LCARS number; `entities`: only these. A
    calendar without a label gets its name in HA."""
    cals = site.calendars
    if entities:
        cals = [c for c in cals if c["entity"] in entities]
    out = []
    for c in cals:
        c = dict(c)
        if not c.get("label"):
            c["label"] = site.friendly_name(c["entity"])
        out.append(c)
    return out


@component("week")
class Week(Component):
    """The next days of several calendars (lcars-week.js): a label block per calendar with events (the
    pillar), a column per day, event titles in the calendar's colour. calendars: entity IDs (default: all
    of the site's `calendars`); rows: how many calendars at most (a number, or per tier); filler: the
    colour of the label column's head piece and filler."""
    fields = {"calendars": None, "days": 7, "rows": 5, "filler": "peri", "side": "left"}

    def parse(self):
        self.sensitive = is_tiered(self.rows)

    def render(self, ctx):
        rows = tiered_value(self.rows, ctx.tier)
        return {"type": "custom:lcars-week", "days": self.days, "calendars": calendar_list(ctx.site, self.calendars),
                "titles": ctx.site.titles, "max_rows": rows, "label_w": ctx.label_w, "side": self.side,
                "pillar": colour(self.filler, self.where), "head": TL_HEAD, "row": DATA_ROW, "gap": PANEL_GAP,
                "font": FONT, "colours": {**GRID_COLOURS, "ink": INK}}

    def height(self, ctx):
        rows = tiered_value(self.rows, ctx.tier)
        return f"calc({TL_HEAD} + {rows} * {DATA_ROW} + {Len.of((rows + 1) * PANEL_GAP + 8)})"

    def edge(self, side, ctx):
        return ctx.label_w if side == self.side else None


@component("month")
class Month(Component):
    """A month of several calendars (lcars-month.js): week blocks as the label column, a 6 × 7 day grid with
    the events as bars in their calendar's colour, the calendars as a legend on the right edge (the frame's
    right side). mode: controls = only the Back / Today / Next buttons (e.g. in the mid bar), linked to
    the month by `group`."""
    fields = {"calendars": None, "mode": None, "group": "calendar", "legend": "almond", "weeks": None}

    def render(self, ctx):
        weeks = [colour(c, self.where) for c in (self.weeks or ["peach", "almond", "butterscotch"])]
        card = {"type": "custom:lcars-month", "group": self.group,
                "calendars": calendar_list(ctx.site, self.calendars),
                "titles": ctx.site.titles, "label_w": ctx.label_w, "legend_w": ctx.label_w,
                "legend_filler": colour(self.legend, self.where),
                "legend_row": f"calc({DATA_ROW} * 1.25)", "head": DATA_ROW, "gap": DATA_GAP, "font": FONT,
                "weeks": {"colours": weeks, "head": ORANGE, "prefix": "Wk",
                          "codes": [lcars_code(f"calendar/week/{i}") for i in range(6)]},
                "controls": [{"colour": c, "code": lcars_code(f"calendar/controls/{i}")}
                             for i, c in enumerate([PEACH, ALMOND, PEACH])],
                "colours": {"empty": rgba(PERI, 0.1), "weekend": rgba(PERI, 0.05), "today": rgba(PERI, 0.25),
                            "other": rgba(PERI, 0.03), "text": PERI, "text_weekend": GRAY, "text_today": ORANGE,
                            "dim": rgba(PERI, 0.3), "ink": INK}}
        if self.mode:
            card["mode"] = self.mode
        return card

    def edge(self, side, ctx):
        return ctx.label_w


def forecast_card(entity, **extra):
    return {"type": "custom:lcars-forecast", "entity": entity, "hours": 12, "segments": 8, "font": FONT,
            "colours": {"temp": PEACH, "rain": ICE, "off": BAR_OFF, "text": PERI, "dim": GRAY, "flash": WHITE},
            "blink": [8000, 24000], "off_fraction": 0.025, **extra}


@component("forecast")
class Forecast(Component):
    """The weather forecast (lcars-forecast.js): hourly or daily columns (hour or weekday, condition code, a
    temperature bar, °C, precipitation). labels: colours of label blocks "Time" and "Temp · Rain" beside
    the card's two rows, as part of the label column, with the Hourly / Daily switch (toggle colour) below
    them; without labels the plain card. min_rows: the data rows it needs at least where the page scrolls."""
    fields = {"entity": None, "labels": None, "toggle": "peri", "min_rows": None}

    def render(self, ctx):
        entity = self.entity or ctx.site.weather
        if not self.labels:
            return forecast_card(entity)
        names = ["Time", "Temp · Rain"]
        cards = [at(label_block(colour(c, self.where), name, ctx.code(name)), f"l{i}")
                 for i, (name, c) in enumerate(zip(names, self.labels))]
        toggle = forecast_card(entity, mode="toggle", toggle={"colour": colour(self.toggle, self.where),
                                                              "code": ctx.code("type"), "ink": INK})
        cards += [at(toggle, "l2"),
                  at(forecast_card(entity, layout="rows", rows={"time": DATA_ROW, "rain": None}, gap=DATA_GAP), "c")]
        return grid('"l0 c" "l1 c" "l2 c"', f"{Len.of(ctx.label_w)} 1fr", f"{DATA_ROW} 1fr {DATA_ROW}", cards,
                    gap=f"{Len.of(DATA_GAP)} 16px")

    def min_height(self, ctx):
        return f"calc({self.min_rows} * {DATA_ROW})" if self.min_rows else None

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" and self.labels else None


DWD_WFS = "https://maps.dwd.de/geoserver/dwd/ows"
_BORDERS = {}


def dwd_border_path(center, layer, digits=3, margin=(0.9, 1.4)):
    """SVG path (x = lon, y = -lat) of a DWD WFS polygon layer's outlines, clipped to the radar area plus a
    margin (paths break where they leave it) and rounded to `digits` decimals (3 ~ 100 m). Fetched once per
    build (the WMS forbids custom styles, so the card draws the borders itself)."""
    k = (center, layer, digits)
    if k in _BORDERS:
        return _BORDERS[k]
    lat, lon = center
    inside = lambda x, y: abs(y - lat) <= margin[0] and abs(x - lon) <= margin[1]   # noqa: E731
    bbox = f"{lat - margin[0]},{lon - margin[1]},{lat + margin[0]},{lon + margin[1]},urn:ogc:def:crs:EPSG::4326"
    q = urllib.parse.urlencode({"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer,
                                "outputFormat": "application/json", "srsName": "EPSG:4326", "bbox": bbox})
    feats = json.load(urllib.request.urlopen(f"{DWD_WFS}?{q}", timeout=60))["features"]
    parts = []
    for f in feats:
        g = f["geometry"]
        rings = g["coordinates"] if g["type"] == "Polygon" else [r for poly in g["coordinates"] for r in poly]
        for ring in rings:
            runs, pts, last = [], [], None
            for x, y in ring:
                if not inside(x, y):
                    if len(pts) > 1:
                        runs.append(pts)
                    pts, last = [], None
                    continue
                p = (round(x, digits), round(-y, digits))
                if p != last:
                    pts.append(p)
                    last = p
            if len(pts) > 1:
                runs.append(pts)
            parts += ["M" + "L".join(f"{x:g} {y:g}" for x, y in run) for run in runs]
    _BORDERS[k] = "".join(parts)
    return _BORDERS[k]


@component("radar")
class Radar(Component):
    """The precipitation radar (lcars-radar.js; provider DWD: Germany): the map with its home marker
    (site `radar`). controls: pillar (the map with its own button pillar), none (the map only) or row
    (only the Play / Back / Next / Now buttons, e.g. in the mid bar); "none" and "row" cards on the same
    view are linked. filler: the pillar's filler colour."""
    fields = {"controls": "pillar", "filler": "almond", "buttons": ["orange", "peach", "peach", "butterscotch"]}

    def render(self, ctx):
        r = ctx.site.radar
        if not r:
            raise ConfigError(f"{self.where}: a radar needs the site's `radar` settings (home, width_km)")
        center = tuple(r.get("center", r["home"]))
        controls = self.controls
        view_key = ctx.view.key if ctx.view else "radar"
        return {"type": "custom:lcars-radar", "controls": controls, "group": view_key,
                "center": list(center), "home": list(r["home"]),
                "width_km": r["width_km"], "layer": "dwd:Radar_wn-product_1x1km_ger",
                "past_min": 60, "future_min": 90, "step_min": 10, "lag_min": 10, "frame_ms": 500, "hold_ms": 1600,
                "borders": [] if controls == "row" else [   # the button-only card draws no map
                    {"d": dwd_border_path(center, "dwd:Warngebiete_Kreise"), "colour": PERI, "width": 1, "opacity": 0.35},
                    {"d": dwd_border_path(center, "dwd:Laender", digits=2), "colour": LILAC, "width": 1.5, "opacity": 0.8}],
                "pillar": {"width": DECOR_W, "gap": 6 if controls == "row" else PANEL_GAP,
                           "filler": colour(self.filler, self.where),
                           "ink": INK, "blocks": [{"colour": colour(c, self.where), "code": lcars_code(f"{view_key}/radar/{i}")}
                                                  for i, c in enumerate(self.buttons)]},   # play, back, next, now
                "colours": {"past": PERI, "now": ORANGE, "future": LILAC, "text": PERI, "dim": GRAY, "home": ORANGE},
                "font": FONT}


@component("history")
class History(Component):
    """A sensor over 24 h / 7 d / 28 d from HA's long-term statistics (lcars-history.js): a smooth filled area
    with labelled lines, no legend. Its range buttons (buttons: their colours) are blocks of the label
    column (one data row high each, the active one near-white), or, with column: false, a pillar of their
    own. scale: log (default, for values across magnitudes, e.g. power) or linear; ticks, min, max, unit
    (default: the entity's), stat: max (default), mean or min of each period."""
    fields = {"entity": REQUIRED, "buttons": ["almond", "peach", "bone"], "filler": "orange", "column": True,
              "scale": "log", "ticks": [1, 10, 100, 1000], "min": None, "max": 2500, "unit": None, "stat": "max",
              "colour": "almond"}

    def render(self, ctx):
        ranges = [("24h", 24, "5minute"), ("7d", 168, "hour"), ("28d", 672, "hour")]
        colours_ = [colour(c, self.where) for c in self.buttons]
        filler = colour(self.filler, self.where)
        key = ctx.key
        pillar = {"width": ctx.label_w if self.column else DECOR_W, "gap": PANEL_GAP, "side": "left",
                  "active": ACTIVE if self.column else ORANGE, "filler": filler, "ink": INK,
                  "blocks": [{"colour": c, "code": lcars_code(f"{key}/range/{label}")}
                             for c, (label, _, _) in zip(colours_, ranges)]}
        if self.column:
            pillar.update({"gap": DATA_GAP, "row": DATA_ROW})
        card = {"type": "custom:lcars-history", "entity": self.entity,
                "ranges": [{"label": label, "hours": hours, "period": period} for label, hours, period in ranges],
                "ticks": list(self.ticks), "max": self.max, "pillar": pillar,
                "colours": {"line": colour(self.colour, self.where), "fill_opacity": 0.35, "grid": GRAY, "axis": DIM,
                            "text": DIM},
                "font": FONT}
        if self.scale != "log":
            card["scale"] = self.scale
        for k in ("min", "unit"):
            if getattr(self, k) is not None:
                card[k] = getattr(self, k)
        if self.stat != "max":
            card["stat"] = self.stat
        return card

    def edge(self, side, ctx):
        return ctx.label_w if side == "left" and self.column else (DECOR_W if side == "left" else None)


# lcards-chart hands ApexCharts the container's pixel size at first render and never resizes; percentages
# let ApexCharts' own parent-resize observer redraw at full size. That observer ignores resizes while the
# draw-in animation runs (the layout settles exactly then), so animations stay off.
FLUID = {"width": "100%", "height": "100%", "animations": {"enabled": False}}


@component("chart")
class Chart(Component):
    """Several sensors over the last hours as an LCARdS area chart, mirrored around a zero axis: series with
    sign 1 above, -1 below (e.g. a total above, its consumers below), on a log scale with labelled lines
    (ticks, unit). series: [{entity, name, colour, sign}]."""
    fields = {"series": REQUIRED, "ticks": [1, 10, 100], "top": 2.5, "hours": 24, "unit": "W"}

    def render(self, ctx):
        series = [(s["entity"], s["name"], colour(s.get("colour"), f"{self.where}.series"), int(s.get("sign", 1)))
                  for s in self.series]

        def lg(w):
            return math.log10(1 + w)

        # ApexCharts' log scale rejects negatives, so each series is mapped to sign * log10(1 + value) by an
        # expression processor. Axis labels would show those log values, so they are hidden and the ticks
        # are drawn as labelled annotation lines instead; the tooltip is off for the same reason.
        lines = [{"y": 0, "borderColor": DIM, "borderWidth": 2, "strokeDashArray": 0, "opacity": 0.9}]
        for w in self.ticks:
            for s in (1, -1):
                lines.append({"y": s * lg(w), "borderColor": GRAY, "strokeDashArray": 4, "opacity": 0.6,
                              "label": {"text": f"{w} {self.unit}", "position": "left", "textAnchor": "start",
                                        "borderWidth": 0, "offsetX": 4,
                                        "style": {"color": DIM, "background": "transparent", "fontSize": "12px"}}})
        return {"type": "custom:lcards-chart", "chart_type": "area", "xaxis_type": "datetime",
                # keyed by display name: live updates label the legend with the key, not series_names
                "data_sources": {n: {"entity": e, "history": {"hours": self.hours}, "processing": {"log": {
                    "type": "expression",
                    "expression": f"v == null ? null : {sign} * Math.log10(1 + Math.max(0, v))"}}}
                                 for e, n, _, sign in series},
                "sources": [{"datasource": n, "buffer": "log", "name": n} for _, n, _, _ in series],
                "series_names": [n for _, n, _, _ in series],
                "style": {"colors": {"series": [c for _, _, c, _ in series]},
                          "stroke": {"curve": "monotoneCubic", "width": 2}, "fill": {"type": "solid", "opacity": 0.35},
                          "legend": {"show": False}, "grid": {"show": False},
                          "yaxis": {"labels": {"show": False}},
                          "display": {"tooltip": {"show": False}},
                          "formatters": {"xaxis_label": "HH:mm"},
                          "chart_options": {"chart": FLUID, "yaxis": {"min": -self.top, "max": self.top},
                                            "annotations": {"yaxis": lines}}}}


@component("sliders")
class Sliders(Component):
    """Vertical sliders like the TNG transporter console (lcars-transporter.js): drag or tap a slot, the value
    is sent when the finger lifts. channels: [{entity, label, colour}]: number or input_number entities (min,
    max, step: their range), or lights (their brightness in %, 0 turns them off)."""
    fields = {"channels": REQUIRED, "min": 0, "max": 100, "step": 1, "segments": 20}

    def render(self, ctx):
        return {"type": "custom:lcars-transporter", "min": self.min, "max": self.max, "step": self.step,
                "segments": self.segments,
                "channels": [{"entity": c["entity"], "label": c["label"],
                              "colour": colour(c.get("colour"), f"{self.where}.channels", PEACH),
                              "code": ctx.code("channel", c["label"])} for c in self.channels],
                "off": BAR_OFF, "slot": rgba(PERI, 0.08), "handle": BONE, "text": PERI, "dim": GRAY, "ink": INK,
                "label_h": f"calc({DATA_ROW} * 1.4)", "col_w": "clamp(70px, 7vw, 130px)",
                "blink": blink(ctx.key + "/sliders", self.segments),
                "off_fraction": 0.025, "flash": WHITE, "gap": 3, "font": FONT}


def minutes(t):
    """Minutes of the day from "HH:MM[:SS]" ("24:00" = end of the day, 23:59)."""
    t = str(t).strip()
    if t in ("24:00", "24:00:00"):
        return 1439
    h, m = (t.split(":") + ["0"])[:2]
    return int(h) % 24 * 60 + int(m)


@component("schedule")
class Schedule(Component):
    """A day's schedule of phases over 24 h (lcars-schedule.js), e.g. a light's day and night phases or heating
    periods: one smooth shape per phase that rises over its ramp-up and falls over its ramp-down, its
    height the phase's level; a line at the time now. phases: [{name, start, end ("HH:MM"),
    ramp_up_minutes, ramp_down_minutes, level or levels: {channel: value}, colour}] (inline, or from a file
    on the HA host through the site's `data`); colours: {phase name: colour} for phases without one;
    min_share: the lowest a phase's shape is drawn, as a share of the graph's height."""
    fields = {"phases": REQUIRED, "colours": None, "min_share": 0.3}

    def parse(self):
        if not isinstance(self.phases, list):
            raise ConfigError(f"{self.where}.phases: a list of phases")
        self.colour_map = colour_map(self.colours, f"{self.where}.colours") or {}

    def render(self, ctx):
        phases = []
        for p in self.phases:
            ph = {"name": p["name"], "start": minutes(p["start"]), "end": minutes(p["end"]),
                  "up": int(p.get("ramp_up_minutes", p.get("up", 0))), "down": int(p.get("ramp_down_minutes", p.get("down", 0))),
                  "levels": {str(k): v for k, v in (p.get("levels") or {}).items()},
                  "colour": colour(p.get("colour"), f"{self.where}.phases") or self.colour_map.get(p["name"], PERI)}
            if "level" in p:
                ph["level"] = p["level"]
            phases.append(ph)
        return {"type": "custom:lcars-schedule", "phases": phases, "min_height": self.min_share,
                "colours": {"grid": rgba(PERI, 0.15), "text": GRAY, "now": ORANGE}, "font": FONT}


@component("log")
class Log(Component):
    """A device log from HA's logbook (lcars-log.js): newest first, one line per event (time, tag, text, a
    detail, a reference code), coloured by level. sources: [{entity, tag, states: {state: [text, level,
    detail]}, default, details, burst}] (see lcars-log.js); levels: {level: colour}."""
    fields = {"sources": REQUIRED, "levels": None, "hours": 24, "refresh_s": 60, "flap_s": 60, "burst_s": 60,
              "max_lines": 40}

    def render(self, ctx):
        levels = colour_map(self.levels, f"{self.where}.levels") or {
            "info": PERI, "ok": ICE, "warn": SUNFLOWER, "flap": BUTTERSCOTCH, "error": RED, "ble": GRAY}
        return {"type": "custom:lcars-log", "sources": self.sources, "hours": self.hours, "refresh_s": self.refresh_s,
                "flap_s": self.flap_s, "burst_s": self.burst_s, "max_lines": self.max_lines, "levels": levels,
                "colours": {"time": rgba(PERI, 0.55), "bright": BRIGHT},
                "cascade_ms": 3 * CASCADE_MS, "stagger_ms": 90, "font": FONT, "font_size": 15}


@component("tank")
class Tank(Component):
    """A fill level (a tank, a bottle, a battery) as a vertical stack of segments with a scale and a pointer
    (lcars-tank.js): entity (the level), capacity and low (in its unit), unit (default: the entity's),
    colour; red below `low`. status / status_attributes: an entity whose attributes override capacity and
    low, e.g. {capacity: size_ml, low: low_ml}. Tap: more-info."""
    fields = {"entity": REQUIRED, "capacity": REQUIRED, "low": 0, "unit": None, "status": None,
              "status_attributes": None, "colour": "peach", "segments": 20}

    def render(self, ctx):
        card = {"type": "custom:lcars-tank", "entity": self.entity, "status": self.status, "capacity": self.capacity,
                "low": self.low, "segments": self.segments, "colour": colour(self.colour, self.where), "alarm": RED,
                "off": BAR_OFF, "text": PERI, "dim": GRAY, "blink": blink(ctx.key + "/tank", self.segments),
                "off_fraction": 0.025, "flash": WHITE, "gap": 3, "font": FONT}
        if self.unit is not None:
            card["unit"] = self.unit
        if self.status_attributes:
            card["status_attributes"] = dict(self.status_attributes)
        return card


@component("player")
class Player(Component):
    """A media player (lcars-player.js). part: now (cover, track, progress, volume), devices (the output
    devices as a button column), transport (only Play/Pause, Back, Next, Shuffle, Repeat, e.g. in the mid
    bar), or full (now playing with its own transport pillar and device pills). entity: a media_player
    (a pattern like media_player.spotify_* takes the first match when the dashboard is built); name: the
    service's name in status texts ("Spotify refused · Repeat"; default "Player")."""
    fields = {"entity": REQUIRED, "part": "full", "name": None}

    def render(self, ctx):
        transport = {"now": "none", "devices": "none", "transport": "row", "full": "pillar"}[self.part]
        card = {"type": "custom:lcars-player", "entity": ctx.site.resolve(self.entity), "transport": transport,
                "pillar": {"width": DECOR_W, "gap": 6 if self.part == "transport" else PANEL_GAP, "ink": INK,
                           "filler": ORANGE,
                           "blocks": [{"colour": c, "code": lcars_code(f"media/transport/{i}")}
                                      for i, c in enumerate([ORANGE, PEACH, PEACH, ICE, ICE])]},
                "segments": {"progress": 40, "volume": 20},
                "colours": {"accent": ORANGE, "text": PERI, "value": PEACH, "dim": DIM, "off": BAR_OFF,
                            "on": ICE, "playing": ICE, "paused": SUNFLOWER, "idle": GRAY, "active": ACTIVE,
                            "error": RED, "source": ALMOND, "volume": PEACH, "art": ORANGE, "ink": INK},
                "blink": blink("media/player", 40), "off_fraction": 0.025,
                "flash": WHITE, "gap": 3, "font": FONT}
        if self.part == "now":
            card["sources"] = "none"
        if self.part == "devices":
            card.update({"sources": "column", "source_row": 64})
        if self.name:
            card["name"] = self.name
        return card


@component("library")
class Library(Component):
    """A media library from HA's media browser (lcars-library in lcars-player.js): a pillar of categories
    (the frame's right side), rows that play on tap. categories: [{match (the end of a root entry's
    media_content_id), label, colour, pinned: [ids listed first]}]; name: as for a player."""
    fields = {"entity": REQUIRED, "categories": REQUIRED, "filler": "almond", "paging": "butterscotch", "name": None}

    def render(self, ctx):
        return {"type": "custom:lcars-library", "entity": ctx.site.resolve(self.entity),
                **({"name": self.name} if self.name else {}),
                "categories": [{"match": c["match"], "label": c["label"],
                                "colour": colour(c.get("colour"), f"{self.where}.categories", PEACH),
                                "code": lcars_code(f"media/library/{c['match']}"),
                                **({"pinned": c["pinned"]} if c.get("pinned") else {})}
                               for c in self.categories],
                "pillar": {"width": ctx.label_w, "gap": PANEL_GAP, "ink": INK, "filler": colour(self.filler, self.where),
                           "active": ACTIVE,
                           "up": {"colour": colour(self.paging, self.where), "code": lcars_code("media/library/up")},
                           "down": {"colour": colour(self.paging, self.where), "code": lcars_code("media/library/down")}},
                "row": 40, "row_gap": PANEL_GAP,
                "colours": {"text": PERI, "dim": DIM, "ink": INK, "rows": [PEACH, ALMOND, BUTTERSCOTCH]},
                "font": FONT}

    def edge(self, side, ctx):
        return ctx.label_w if side == "right" else None


__all__ = ["BARS_VISIBLE", "css", "sizes", "json"]
