"""Build the LCARS dashboard (HA dashboard url_path: lcars-bridge, sidebar title "LCARS").

Usage:  python3 build_dashboard.py            -> writes ../build/lcars_dashboard.json
        python3 ../tools/deploy.py            -> validates and saves it to Home Assistant

Voyager palette, Titan.DS-style layout, no page scrolling.

Every view shares one full-viewport frame (no scrolling), built with the
custom:lcards-layout-view view type:

    top   : header elbow (footer-left) + readouts + title, segmented bar
    mid   : main-frame elbow (header-left), segmented bar
    side  : stacked navigation blocks (shared across views, active one highlighted)
    main  : the view's own content
    foot  : footer elbow, segmented bar as thick as its text, local date/time, stardate block
"""
import json
import math
import os
import random
import urllib.parse
import urllib.request
import re
import functools
import subprocess
import sys
import zlib

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ha_ws  # noqa: E402  (raw websocket client, token from ~/.config/homeassistant/token)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "build", "lcars_dashboard.json")
_FOREIGN = {}


def number_sensors(n, seed=47174):
    """n sensors for the number columns, read live at build time: power/energy meters first (without
    the always-zero feed-in counters), topped up with a fixed-seed random pick of other sensors whose
    value is a non-zero number (zeros would all show as 0000)."""
    power, other = [], []
    for st in ha_ws.Client().call({"type": "get_states"})["result"]:
        eid, attrs = st["entity_id"], st["attributes"]
        if not eid.startswith("sensor."):
            continue
        try:
            value = float(st["state"])
        except ValueError:
            continue
        if (attrs.get("device_class") in ("power", "energy") or attrs.get("unit_of_measurement") in
                ("W", "kW", "Wh", "kWh")):
            if "einspeisung" not in eid:
                power.append(eid)
        elif value != 0:
            other.append(eid)
    rng = random.Random(seed)
    picks = rng.sample(sorted(power), min(n, len(power)))
    picks += rng.sample(sorted(other), n - len(picks))
    rng.shuffle(picks)
    return picks


def foreign_card(url_path, view_path, index=0):
    """First card(s) of a view on another dashboard, fetched live (used for the calendar cards)."""
    if url_path not in _FOREIGN:
        _FOREIGN[url_path] = ha_ws.Client().call({"type": "lovelace/config", "url_path": url_path})["result"]
    view = next(v for v in _FOREIGN[url_path]["views"] if v.get("path") == view_path)
    return view.get("cards", [])[index]

# ── Voyager-era palette (hex on purpose: stays put when LCARdS alert modes shift vars) ──
_CODES = {}


def lcars_code(key):
    """Stable, unique LCARS number (NN-NNNN) for a thing, derived from its key. The same key (the same
    thing, e.g. a sidebar block shown on several views) always gets the same number, and no two keys
    share one."""
    if key not in _CODES:
        h = zlib.crc32(key.encode())
        taken = set(_CODES.values())
        while f"{10 + h % 90:02d}-{h // 90 % 10000:04d}" in taken:
            h += 1
        _CODES[key] = f"{10 + h % 90:02d}-{h // 90 % 10000:04d}"
    return _CODES[key]


ORANGE = "#FF9900"
BUTTERSCOTCH = "#FF9966"
PEACH = "#FFCC99"
ALMOND = "#FFAA90"
VIOLET = "#CC99FF"
LILAC = "#CC99CC"
BLUEY = "#8899FF"
PERI = "#9999FF"
ICE = "#99CCFF"
ROSE = "#CC6699"
RED = "#DD4444"
SUNFLOWER = "#FFCC66"
GRAY = "#666688"
BONE = "#EEE4CC"     # light LCARS block (the "LCARS" / "LCARS VERSION" blocks of the database screens)
INK = "#000000"

OK, WARN, CRIT, OFF, INFO = ICE, SUNFLOWER, RED, GRAY, VIOLET

PILLAR = 140        # width of the vertical frame bars / sidebar
BAR = 10            # thickness of the horizontal frame bars
ELBOW_W = PILLAR + 44

THEME = "LCARS Aquarium"

PUMP = "sensor.switch_shellyplugsg3_000000000000_switch_0_status"
HEATER = "binary_sensor.switch_shellyplugsg3_000000000000_switch_0_heater"
CO2 = "sensor.switch_co2_anlage_status"
CO2_COUPLING = "switch.switch_co2_anlage_automatic_coupling"
LIGHT_AUTO = "switch.chihiros_wrgb2_slim_90_ble_xxxxxxxxxxxxxxxxxx_rgb_automatic_schedule"
PHASE = "sensor.chihiros_wrgb2_slim_90_ble_xxxxxxxxxxxxxxxxxx_rgb_current_phase"
CHANNEL = "number.chihiros_wrgb2_slim_90_ble_xxxxxxxxxxxxxxxxxx_rgb_{}_channel"
WC = "sensor.aquarium_water_change_status"
POWER = "sensor.aquarium_total_power"
PUMP_POWER = "sensor.shellyplugsg3_000000000000_switch_0_power"
CO2_POWER = "sensor.co2_anlage_leistung"
CAMERA = "camera.esphome_esp32_aquarium_webcam_aquarium_webcam"

DOSE_CHANNELS = [  # (label, slug, bottle_ml)
    ("Nitrate", "nitrat", 500), ("Phosphate", "phosphat", 500),
    ("Iron", "eisen", 500), ("GH Boost N", "gh_boost_n", 500),
]

PHASE_STATES = {
    "Daylight": ("Daylight", "mdi:white-balance-sunny", SUNFLOWER),
    "Daylight (ramping up)": ("Ramp up", "mdi:weather-sunset-up", BUTTERSCOTCH),
    "Daylight (ramping down)": ("Ramp down", "mdi:weather-sunset-down", BUTTERSCOTCH),
    "Moonlight": ("Moonlight", "mdi:weather-night", BLUEY),
    "Manual Override": ("Override", "mdi:hand-back-right", WARN),
    "Off": ("Off", "mdi:power-off", OFF),
}
PUMP_STATES = {
    "Critical": ("Critical", "mdi:alert-octagon", CRIT), "Warning": ("Warning", "mdi:alert-outline", WARN),
    "Running": ("Running", "mdi:pump", OK), "Off": ("Off", "mdi:power-off", OFF),
}
CO2_STATES = {
    "Safety Cutoff": ("Cutoff", "mdi:alert-octagon", CRIT), "Manual": ("Manual", "mdi:hand-back-right", WARN),
    "Running": ("Running", "mdi:gas-cylinder", OK), "Idle": ("Idle", "mdi:pause-circle-outline", OFF),
}


def js_map(states, fallback="entity.state"):
    names = {k: v[0] for k, v in states.items()}
    return (f"[[[ const m = {json.dumps(names, ensure_ascii=False)}; "
            f"return (entity.state in m) ? m[entity.state] : {fallback}; ]]]")


def at(card, area, **extra):
    card = dict(card)
    card["view_layout"] = {"grid-area": area, **extra}
    return card


def grid(areas, columns, rows, cards, gap="6px", **layout):
    return {"type": "custom:lcards-layout-card",
            "layout": {"grid-template-areas": areas, "grid-template-columns": columns,
                       "grid-template-rows": rows, "grid-gap": gap, **layout},
            "cards": cards}


# ── Frame primitives ────────────────────────────────────────────────────────────
def block(color, label=None, code=None, path=None, align="bottom-right", size=21):
    text = {}
    if label:
        pad = {"right": 8} if align.startswith("center") else {"right": 8, "bottom": 3}
        text["label"] = {"show": True, "content": label, "position": align, "font_size": size,
                         "color": INK, "text_transform": "uppercase", "padding": pad}
    if code:
        text["code"] = {"content": code, "position": "top-left", "font_size": 12, "color": INK,
                        "padding": {"left": 6, "top": 3}}
    card = {"type": "custom:lcards-button", "preset": "barrel", "show_icon": False,
            "interactive": bool(path), "style": {"card": {"color": {"background": color}}}, "text": text,
            "tap_action": {"action": "navigate", "navigation_path": path} if path else {"action": "none"}}
    return card


def segments(colors_fr, position):
    """Segmented horizontal bar. position: 'top' or 'bottom' (bar sits on that edge)."""
    cols = " ".join(f"{fr}fr" for _, fr in colors_fr)
    names = [f"s{i}" for i in range(len(colors_fr))]
    row = '"' + " ".join(names) + '"'
    blank = '"' + " ".join("." for _ in names) + '"'
    areas = f"{row} {blank}" if position == "top" else f"{blank} {row}"
    rows = f"{BAR}px 1fr" if position == "top" else f"1fr {BAR}px"
    return grid(areas, cols, rows, [at(block(c), n) for (c, _), n in zip(colors_fr, names)], gap="0 6px")


FRAME_H = 34        # height of the frame row above the sidebar/content (the foot row: FOOT_H)
INNER_CURVE = FRAME_H - BAR   # one inner radius for every corner around the content


def elbow(kind, color, text=None, bar_height=BAR, outer_curve=FRAME_H):
    """outer_curve defaults to the frame-row height: LCARdS would clamp 'auto' (PILLAR/2) to the card
    height anyway, and explicit values keep the mid and foot elbows identical."""
    card = {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": PILLAR, "bar_height": bar_height, "outer_curve": outer_curve,
                                  "inner_curve": INNER_CURVE, "color": {"default": color}}}}
    if text:
        card["text"] = text
    return card


def readout(entity, label, value, colors=None, label_color=LILAC):
    return {"type": "custom:lcards-button", "entity": entity, "preset": "text-only", "show_icon": False,
            "text": {"lbl": {"content": label, "position": "top-left", "font_size": 17, "color": label_color,
                             "text_transform": "uppercase"},
                     "val": {"content": value, "position": "bottom-left", "font_size": "var(--lcars-readout-size)",
                             "font_weight": "bold",
                             "color": colors or PEACH, "text_transform": "uppercase"}},
            "tap_action": {"action": "more-info"}}


# Display priorities: content that doesn't fit a shorter screen is not rendered there, instead of being
# cut off. HA's hui-card, which wraps every child of a layout card, doesn't create a card whose visibility
# conditions fail, so a variant that isn't shown costs nothing (better performance on the tablet too).
# Priority -> minimum viewport height in px; priority 1 is always shown.
PRIORITY_MIN_H = {1: 0, 2: 760, 3: 880, 4: 1000}


def shown_from(card, priority, below=None):
    """`card` only while the viewport is at least as high as `priority` needs (and lower than what
    priority `below` needs, if given)."""
    q = [f"(min-height: {PRIORITY_MIN_H[priority]}px)"] if PRIORITY_MIN_H[priority] else []
    if below:
        q.append(f"(max-height: {PRIORITY_MIN_H[below] - 0.02}px)")
    return dict(card, visibility=card.get("visibility", []) +
                [{"condition": "screen", "media_query": " and ".join(q) or "all"}])


def tiered(variants):
    """One of several variants of the same content by viewport height: {priority: card}; the variant with
    the highest priority that fits is rendered, the others aren't. Needs a variant for priority 1."""
    prios = sorted(variants, reverse=True)
    cards = [at(shown_from(variants[p], p, prios[i - 1] if i else None), "v") for i, p in enumerate(prios)]
    return grid('"v"', "1fr", "1fr", cards, gap="0")


CASCADE_MS = 1800   # one colour cycle of the number columns
HEX_ROWS, HEX_COLS = 4, 5


def js_hex(entity):
    """JS: the sensor's value (x100) as a 4-digit hex code, e.g. 11.6 -> 0488."""
    return ("[[[ const v = parseFloat((states['" + entity + "'] || {}).state); if (isNaN(v)) return '----'; "
            "return (Math.round(Math.abs(v) * 100) % 65536).toString(16).toUpperCase().padStart(4, '0'); ]]]")


def number_columns(color_start=ICE, color_text="#223366", color_end="#DFE1E8"):
    """LCARS number columns from real sensors (mostly power meters, see number_sensors()), each shown as
    a hex code read when the page loads, with a staggered colour waterfall running over them. The last row
    has priority 4: below its viewport height one row fewer is rendered instead of a cut-off one."""
    return tiered({4: _number_grid(HEX_ROWS, color_start, color_text, color_end),
                   1: _number_grid(HEX_ROWS - 1, color_start, color_text, color_end)})


def _number_grid(n_rows, color_start, color_text, color_end):
    picks = number_sensors(HEX_ROWS * HEX_COLS)
    rows = [[js_hex(e) for e in picks[r * HEX_COLS:(r + 1) * HEX_COLS]] for r in range(n_rows)]
    return {"type": "custom:lcards-data-grid", "data_mode": "data", "rows": rows,
            "grid": {"grid-template-columns": f"repeat({HEX_COLS}, auto)",
                     "grid-template-rows": f"repeat({n_rows}, 1fr)", "gap": "0 14px", "justify-content": "start"},
            "style": {"font_size": 15, "font_weight": "bold", "color": color_start, "align": "left"},
            "animations": [{"trigger": "on_load", "preset": "cascade-color",
                            "params": {"duration": CASCADE_MS, "colors": [color_start, color_text, color_end],
                                       "stagger_from": "first", "stagger_delay": 70}}]}


# ── Content primitives ──────────────────────────────────────────────────────────
DIM = "#B4B4CC"      # row label colour (dimmed lavender)


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    return "rgba(%d, %d, %d, %s)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def tint(color, alpha=0.16):
    return f"alpha({color}, {alpha})"


def header(text, color=ORANGE, cap="left"):
    """Section header: square cap + thin underline in the section colour (Titan-style, Voyager hue).

    cap="right" mirrors it (cap and text on the right), e.g. to face a header in the next column.
    """
    far = "right" if cap == "left" else "left"
    return {"type": "custom:lcards-button", "preset": "barrel", "interactive": False, "show_icon": False,
            "style": {"card": {"color": {"background": "transparent"}},
                      "border": {"width": {"top": 0, far: 0, cap: 14, "bottom": 2}, "color": color, "radius": 0}},
            "text": {"label": {"show": True, "content": text, "position": f"center-{cap}", "color": color,
                               "text_transform": "uppercase", "font_size_percent": 62, "padding": {cap: 24}}}}


def row(entity, label, colours, value_js, *, label_js=None, tap="more-info", interactive=True):
    """Flat readout row: tinted box, state-coloured stripe on the left, value in the state colour."""
    colours = dict(colours)
    colours.setdefault("default", OFF)
    colours.setdefault("unavailable", GRAY)
    card = {"type": "custom:lcards-button", "preset": "barrel", "show_icon": False, "interactive": interactive,
            "style": {"card": {"color": {"background": {k: tint(c) for k, c in colours.items()}}},
                      "border": {"width": {"top": 0, "right": 0, "bottom": 0, "left": 10}, "color": colours, "radius": 0}},
            "text": {"label": {"show": True, "content": label_js or label, "position": "center-left",
                               "color": DIM, "text_transform": "uppercase", "font_size_percent": 30,
                               "padding": {"left": 22}},
                     "value": {"content": value_js, "position": "center-right", "color": colours,
                               "text_transform": "uppercase", "font_size_percent": 42, "font_weight": "bold",
                               "padding": {"right": 16}}},
            "tap_action": {"action": tap if interactive else "none"}}
    if entity:
        card["entity"] = entity
        card["hold_action"] = {"action": "more-info"}
    return card


def column(items, filler=PERI):
    """Vertical stack of (kind, card): 'h' header / 'p' / 'r' rows sized to the viewport,
    remaining space left black."""
    names, rows, cards = [], [], []
    for i, (kind, card) in enumerate(items):
        n = f"r{i}"
        names.append(f'"{n}"')
        rows.append({"h": "clamp(30px, 4.2vh, 54px)", "r": "clamp(56px, 8vh, 96px)"}.get(kind, "clamp(40px, 5.6vh, 72px)"))
        cards.append(at(card, n))
    names.append('"fill"')
    rows.append("1fr")
    return grid(" ".join(names), "1fr", " ".join(rows), cards, gap="clamp(6px, 0.9vh, 12px)")


# ── Shared frame ────────────────────────────────────────────────────────────────
BASE = "/lcars-bridge/"

# Header sections, each with its sidebar sub-views.
#   section: (key, label, code, colour, classic_url, [(view_key, label, code, colour, path), ...])
SECTIONS = [
    ("aquarium", "Aquarium", lcars_code("section/aquarium"), ORANGE, "/lovelace/phishtank", [
        ("status", "Status", lcars_code("view/status"), PEACH, "aquarium-status"),
        ("visual", "Visual", lcars_code("view/visual"), LILAC, "aquarium-visual"),
        ("light", "Light", lcars_code("view/light"), SUNFLOWER, "aquarium-light"),
        ("dosing", "Dosing", lcars_code("view/dosing"), BLUEY, "aquarium-dosing"),
        ("power", "Power", lcars_code("view/power"), ALMOND, "aquarium-power"),
        ("osmosis", "Osmosis", lcars_code("view/osmosis"), ICE, "aquarium-osmosis"),
    ]),
    ("home", "OPS", lcars_code("section/home"), ROSE, "/lovelace/home", [
        ("home", "OPS", lcars_code("view/home"), ROSE, "ops"),
    ]),
    ("laundry", "Laundry", lcars_code("section/laundry"), LILAC, "/lovelace/waschen", [
        ("laundry", "Laundry", lcars_code("view/laundry"), LILAC, "laundry"),
    ]),
    ("waste", "Waste", lcars_code("section/waste"), PEACH, "/dashboard-muell/muell", [
        ("waste", "Overview", lcars_code("view/waste"), PEACH, "waste"),
        ("waste-calendar", "Calendar", lcars_code("view/waste-calendar"), BUTTERSCOTCH, "waste-calendar"),
    ]),
    ("calendar", "Calendar", lcars_code("section/calendar"), BLUEY, "/dashboard-termine/kalender", [
        ("calendar", "Calendar", lcars_code("view/calendar"), BLUEY, "calendar"),
        ("agenda", "Agenda", lcars_code("view/agenda"), PERI, "calendar-agenda"),
    ]),
]


SECTION_TITLES = {"home": "Operations"}   # page title where it differs from the menu label

NAV_ORDER = ["home", "aquarium", "laundry", "waste", "calendar"]
NAV_H = 38          # height of the header frame bar, which doubles as the section menu


def dashboard_nav(active_section):
    """Section menu rendered as the segments of the header frame bar (like the sidebar blocks)."""
    by_key = {sec[0]: sec for sec in SECTIONS}
    names, cards = [], []
    for key in NAV_ORDER:
        _, label, code, colour, _classic, subviews = by_key[key]
        active = key == active_section
        card = block(ORANGE if active else colour, label + (" ◂" if active else ""), code,
                     None if active else BASE + subviews[0][4], size=18)
        card["text"]["code"]["font_size"] = 10
        names.append(key)
        cards.append(at(card, key))
    names.append("tail")                       # plain segment running the bar out to the right edge
    cards.append(at(block(LILAC), "tail"))
    return grid('"' + " ".join(names) + '"', " ".join(["1fr"] * len(NAV_ORDER)) + " 1.6fr", "1fr", cards,
                gap="0 6px")


def sidebar(section_key, active_view):
    _, _, _, _, _, subviews = next(sec for sec in SECTIONS if sec[0] == section_key)
    items = [(k, label, code, colour, BASE + path) for k, label, code, colour, path in subviews]
    cards, areas, rows = [], [], []
    for key, label, code, colour, path in items:
        is_active = key == active_view
        cards.append(at(block(ORANGE if is_active else colour, label + (" ◂" if is_active else ""), code,
                              None if is_active else path), key))
        areas.append(f'"{key}"')
        rows.append("clamp(48px, 8vh, 110px)")   # 6 blocks + motion switch fit the 800 px tablet
    cards.append(at(block(GRAY, None, lcars_code(f"sidebar-filler/{section_key}")), "filler"))
    here = next(BASE + path for k, _, _, _, path in subviews if k == active_view)
    cards.append(at(motion_switch(section_key, here), "motion"))
    areas += ['"filler"', '"motion"']
    rows += ["1fr", "clamp(36px, 5vh, 60px)"]
    return grid(" ".join(areas), "1fr", " ".join(rows), cards, gap="6px")


def motion_switch(section_key, here):
    """Per-device animation switch, handled by ha/www/lcars-motion.js (state in localStorage): reloads
    the current view `here` with ?lcars_motion=toggle."""
    card = block(BLUEY, "[[[ let off = false; try { off = localStorage.getItem('lcars-motion') === 'off'; } "
                        "catch (e) {} return off ? 'Motion off' : 'Motion on'; ]]]",
                 lcars_code(f"motion/{section_key}"), size=16)
    card["interactive"] = True
    card["tap_action"] = {"action": "navigate", "navigation_path": here + "?lcars_motion=toggle"}
    return card


pump_title_js = (
    "[[[ const a = entity.attributes; const s = entity.state; "
    "if (s === 'Critical') return 'RED ALERT · PUMP OFFLINE > ' + a.critical_minutes + ' MIN'; "
    "if (s === 'Warning' || s === 'Off') { const m = a.minutes_left != null ? a.minutes_left : a.critical_minutes; "
    "return 'PUMP OFFLINE · ' + m + ' MIN TO CRITICAL'; } "
    "return '%s'; ]]]"
)


CLASSIC_H = "clamp(42px, 5.4vh, 58px)"   # Classic block on top of the header frame's pillar
WIDE_MIN = 1600      # header decoration that only fits on wide screens (not the 1280 px tablet)
WIDE_W = 290


def header_buttons(section, colours=(PERI, ALMOND, LILAC, ROSE)):
    """2x2 LCARS pill buttons with auto-generated numbers and no function (header decoration)."""
    names = ["a", "b", "c", "d"]
    cards = []
    for i, (n, c) in enumerate(zip(names, colours)):
        pill = block(c, lcars_code(f"header-button/{section}/{i}"), size=15)
        pill["style"]["border"] = {"width": 0, "radius": 40}
        pill["text"]["label"]["padding"] = {"right": 18, "bottom": 4}
        cards.append(at(pill, n))
    return grid('"a b" "c d"', "1fr 1fr", "1fr 1fr", cards, gap="10px 12px")


FOOT_FONT = 20                    # text in the foot bar; the bar's thickness and the foot row follow it
FOOT_T = FOOT_FONT + 6            # foot bar thickness = height of the clock and the stardate block
FOOT_H = FOOT_T + INNER_CURVE     # foot row: the bar plus the inner curve above it
CLOCK_W = int(22 * FOOT_T * 0.37) + 24   # "FRI 25/09/2026 · 14:32" at bar height (Antonio digits ~0.37 em)
STARDATE_W = int(16 * FOOT_FONT * 0.44) + 80   # label plus room for the code on the left
CLOCK_JS = ("[[[ const d = new Date(), p = (n) => String(n).padStart(2, '0'); "
            "return d.toLocaleDateString('en-GB', {weekday: 'short'}) + ' ' + p(d.getDate()) + '/' "
            "+ p(d.getMonth() + 1) + '/' + d.getFullYear() + ' · ' + p(d.getHours()) + ':' + p(d.getMinutes()); ]]]")
# Stardate in the TNG form (1000 units per year, one decimal ≈ 53 min), anchored so that 1987, the
# year TNG started with stardate 41xxx, is 41000-41999: 2026 runs from 80000 to 80999.9.
STARDATE_JS = ("[[[ const d = new Date(), y = d.getFullYear(), a = new Date(y, 0, 1), b = new Date(y + 1, 0, 1); "
               "const sd = 41000 + (y - 1987) * 1000 + 1000 * (d - a) / (b - a); "
               "return 'Stardate ' + (Math.floor(sd * 10) / 10).toFixed(1); ]]]")


def clock():
    """Local date and time, re-rendered by the minute through sensor.time."""
    return {"type": "custom:lcards-button", "entity": "sensor.time", "preset": "text-only", "show_icon": False,
            "interactive": False, "tap_action": {"action": "none"},
            "text": {"t": {"content": CLOCK_JS, "position": "center-left", "font_size": FOOT_T,
                           "color": ORANGE, "text_transform": "uppercase", "padding": {"left": 4}}}}


def stardate_block():
    card = block(PEACH, STARDATE_JS, lcars_code("stardate"), align="center-right", size=FOOT_FONT)
    card["entity"] = "sensor.time"
    card["text"]["code"]["font_size"] = 10
    card["text"]["code"]["padding"] = {"left": 6, "top": 2}
    return card


def frame(section, active, content, subtitle):
    section_label = SECTION_TITLES.get(section, next(sec[1] for sec in SECTIONS if sec[0] == section)).upper()
    title = {"type": "custom:lcards-button", "entity": PUMP, "preset": "text-only", "show_icon": False,
             "text": {"title": {"content": pump_title_js % section_label, "position": "top-right", "font_size": 60,
                                "color": {"Critical": RED, "Warning": SUNFLOWER, "Off": SUNFLOWER, "default": ORANGE},
                                "text_transform": "uppercase"},
                      "sub": {"content": subtitle, "position": "bottom-right", "font_size": 20, "color": PEACH,
                              "text_transform": "uppercase"}},
             "animations": [{"trigger": "on_entity_change", "entity": PUMP, "to_state": "Critical",
                             "check_on_load": True, "preset": "blink", "loop": True}],
             "tap_action": {"action": "more-info"}}
    # Four readout slots. An entry (card, n) spans n slots; (card, "wide") gets a column that is 0 px
    # below WIDE_MIN window width and WIDE_W above (pure CSS; LCARdS layout cards have no media queries),
    # the slot before it is widened a little.
    slots, cards, widths = [], [], []
    for i, item in enumerate(section_readouts(section)):
        card, span = item if isinstance(item, tuple) else (item, 1)
        name = f"s{i}"
        n = 1 if span == "wide" else span
        slots += [name if card else "."] * n
        if span == "wide":
            widths[-1] = "1.6fr"
            widths.append(f"clamp(0px, calc((100vw - {WIDE_MIN}px) * 100), {WIDE_W}px)")
        else:
            widths += ["1fr"] * n
        if card:
            extra = {"overflow": "hidden"} if span == "wide" else {}
            if card.get("type") == "custom:lcards-data-grid":
                extra["margin"] = "0 0 0 clamp(16px, 2vw, 40px)"
            cards.append(at(card, name, **extra))
    readouts = grid('"' + " ".join(slots) + ' t"', " ".join(widths + ["1.7fr"]), "1fr", [*cards, at(title, "t")],
                    gap="6px 16px")
    # the header frame's pillar starts with the link to the section's original dashboard
    _, _, _, _, classic_url, _ = next(sec for sec in SECTIONS if sec[0] == section)
    classic = block(VIOLET, "Classic", lcars_code(f"classic/{section}"), classic_url, size=18)
    top = grid('"cl data" "elbow data" "elbow nav"', f"{ELBOW_W}px 1fr", f"{CLASSIC_H} 1fr {NAV_H}px", [
        at(classic, "cl", margin=f"0 {ELBOW_W - PILLAR}px {PANEL_GAP + 2}px 0"),
        at(elbow("footer-left", LILAC, {"code": {"content": "LCARS 47174", "position": "top-left", "font_size": 14,
                                                 "color": INK, "padding": {"left": 8, "top": 6}}},
                 bar_height=NAV_H, outer_curve=PILLAR // 2), "elbow"),
        at(readouts, "data", margin="0 0 10px 0"),
        at(dashboard_nav(section), "nav"),
    ], gap="0 6px")
    mid = grid('"elbow bars"', f"{ELBOW_W}px 1fr", "1fr", [
        at(elbow("header-left", PEACH), "elbow"),
        at(segments([(PEACH, 1), (ROSE, 4), (BLUEY, 2), (ORANGE, 1)], "top"), "bars"),
    ], gap="0 6px")
    side = sidebar(section, active)
    # the foot bar is as thick as its text and ends in the local date/time (in a gap of the bar, like a
    # panel caption) and the stardate block; the elbow keeps the page frame's outer and inner radius
    foot = grid('"elbow . . . ." "elbow bars cap clock sd"', f"{ELBOW_W}px 1fr 14px {CLOCK_W}px {STARDATE_W}px",
                f"1fr {FOOT_T}px", [
        at(elbow("footer-left", BLUEY, bar_height=FOOT_T), "elbow"),
        at(grid('"a b c"', "3fr 1fr 5fr", "1fr", [at(block(c), n) for c, n in ((BLUEY, "a"), (LILAC, "b"),
                                                                                (ORANGE, "c"))], gap="0 6px"),
           "bars"),
        at(block(ORANGE), "cap"),
        at(clock(), "clock"),
        at(stardate_block(), "sd"),
    ], gap="0 6px")
    return [at(top, "top"), at(mid, "mid"), at(side, "side"), at(content, "main", margin="4px 0 4px 18px"),
            at(foot, "foot")]


def view(section, key, title, path, content, subtitle):
    return {"title": title, "path": path, "type": "custom:lcards-layout-view", "theme": THEME,
            "layout": {"grid-template-columns": f"{PILLAR}px 1fr",
                       "grid-template-rows": f"clamp(140px, 17vh, 176px) {FRAME_H}px 1fr {FOOT_H}px",
                       "grid-template-areas": '"top top" "mid mid" "side main" "foot foot"',
                       "grid-gap": "6px 0", "height": "calc(100dvh - 16px)", "padding": "8px"},
            "cards": frame(section, key, content, f"{subtitle} · {lcars_code(f'view/{key}')}")}


# ── Views ───────────────────────────────────────────────────────────────────────
# lcards-chart hands ApexCharts the container's pixel size at first render and never
# resizes; percentages let ApexCharts' own parent-resize observer redraw at full size.
# That observer ignores resizes while the draw-in animation runs (the layout settles
# exactly then), so animations stay off - which the no-animation rule wants anyway.
FLUID = {"width": "100%", "height": "100%", "animations": {"enabled": False}}


def mirrored_log_chart(series, ticks=(1, 10, 100), top=2.5):
    """series: [(entity, name, colour, sign)] -> 24 h area chart, mirrored around a zero axis.

    ApexCharts' log scale rejects negatives, so each series is mapped to
    sign * log10(1 + W) by an expression processor. Axis labels would show those
    log values, so they are hidden and the W ticks are drawn as labelled
    annotation lines instead. The tooltip is off for the same reason.
    """
    def lg(w):
        return math.log10(1 + w)

    lines = [{"y": 0, "borderColor": DIM, "borderWidth": 2, "strokeDashArray": 0, "opacity": 0.9}]
    for w in ticks:
        for s in (1, -1):
            lines.append({"y": s * lg(w), "borderColor": GRAY, "strokeDashArray": 4, "opacity": 0.6,
                          "label": {"text": f"{w} W", "position": "left", "textAnchor": "start",
                                    "borderWidth": 0, "offsetX": 4,
                                    "style": {"color": DIM, "background": "transparent", "fontSize": "12px"}}})
    return {"type": "custom:lcards-chart", "chart_type": "area", "xaxis_type": "datetime",
            # keyed by display name: live updates label the legend with the key, not series_names
            "data_sources": {n: {"entity": e, "history": {"hours": 24}, "processing": {"log": {
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
                      "chart_options": {"chart": FLUID, "yaxis": {"min": -top, "max": top},
                                        "annotations": {"yaxis": lines}}}}


# ── Shared helpers for the non-aquarium sections ─────────────────────────────────
WEATHER = "weather.forecast_home"
OSMO = {"switch": "switch.osmoseanlage", "mode": "sensor.osmoseanlage_mode", "fw": "update.osmoseanlage_firmware",
        "energy": "sensor.osmoseanlage_energie", "power": "sensor.osmoseanlage_leistung",
        "countdown": "sensor.osmoseanlage_auto_off_countdown"}
WASH = {"switch": "switch.waschmaschine", "power": "sensor.waschmaschine_leistung",
        "energy": "sensor.waschmaschine_energie"}
BINS = [("Residual", "sensor.mullabfuhr_restmull", "#AAAACC"), ("Organic", "sensor.mullabfuhr_biotonne", ALMOND),
        ("Recycling", "sensor.mullabfuhr_gelbe_tonne", SUNFLOWER),
        ("Paper", "sensor.mullabfuhr_papiertonne", ICE)]
# German bin names in the collection sensors' states and event titles -> short labels (rows are narrow)
BIN_NAMES = {"Restmüll": "Residual", "Biotonne": "Organic", "Gelbe Tonne": "Recycling",
             "Papiertonne": "Paper", "Schadstoffmobil": "Hazmat"}
# Calendar labels in the copied calendar cards
CAL_LABELS = {"Restmüll": "Residual waste", "Biotonne": "Organic waste", "Gelbe Tonne": "Recycling",
              "Papiertonne": "Paper", "Schadstoffmobil": "Hazmat collection", "Privat": "Private",
              "Geburtstage": "Birthdays", "Feiertage RLP": "Holidays RLP", "Feiertage Frankreich": "Holidays France"}
NEXT_PICKUP = "sensor.mullabfuhr_nachste_abholung"
HAZMAT = {"date": "sensor.schadstoffmobil", "window": "sensor.schadstoffmobil_zeitfenster",
          "place": "sensor.schadstoffmobil_standort"}
WASTE_CALS = ["calendar.mullabfuhr_restmull", "calendar.mullabfuhr_biotonne", "calendar.mullabfuhr_gelbe_tonne",
              "calendar.mullabfuhr_papiertonne", "calendar.schadstoffmobil"]
ALL_CALS = WASTE_CALS + ["calendar.telephone", "calendar.personal", "calendar.geburtstage",
                         "calendar.deutschland_rp", "calendar.feiertage_in_frankreich"]

# JS: relative-day wording for a Date `d` (uppercase via text_transform)
REL = ("const t0 = new Date(); t0.setHours(0,0,0,0); const d0 = new Date(d); d0.setHours(0,0,0,0); "
       "const n = Math.round((d0 - t0) / 86400000); "
       "const rel = n === 0 ? 'today' : n === 1 ? 'tomorrow' : n < 0 ? 'past' : 'in ' + n + ' days'; "
       "const wd = d.toLocaleDateString('en-GB', {weekday: 'short'}); "
       "const dm = d.toLocaleDateString('en-GB', {day: '2-digit', month: '2-digit'}); ")

WEATHER_NAMES = {"clear-night": "Clear night", "cloudy": "Cloudy", "exceptional": "Exceptional", "fog": "Fog",
                 "hail": "Hail", "lightning": "Lightning", "lightning-rainy": "Thunderstorm",
                 "partlycloudy": "Partly cloudy", "pouring": "Pouring", "rainy": "Rain", "snowy": "Snow",
                 "snowy-rainy": "Sleet", "sunny": "Sunny", "windy": "Windy", "windy-variant": "Windy"}


# JS: bin name from the next-pickup sensor ("Biotonne am 25.09.2026"), in English
JS_NEXT_BIN = ("[[[ const m = " + json.dumps(BIN_NAMES, ensure_ascii=False) + "; "
               "const n = String(entity.state).split(' am ')[0]; return m[n] || n; ]]]")


def js_de_date(expr, weekday=True):
    """JS for a 'dd.mm.yyyy' string -> 'Fri 25/09 · tomorrow' (weekday=False: '25/09 · tomorrow')."""
    return ("[[[ const m = String(" + expr + ").match(/(\\d\\d)\\.(\\d\\d)\\.(\\d{4})/); if (!m) return '–'; "
            "const d = new Date(+m[3], +m[2] - 1, +m[1]); " + REL + "return " + ("wd + ' ' + " if weekday else "") +
            "dm + ' · ' + rel; ]]]")


def js_iso_date(expr):
    return ("[[[ const s = String(" + expr + "); if (!/^\\d{4}-\\d{2}-\\d{2}/.test(s)) return '–'; "
            "const d = new Date(s.slice(0, 10) + 'T00:00:00'); " + REL + "return wd + ' ' + dm + ' · ' + rel; ]]]")


def js_events(cals):
    """JS prelude: `ev` = next event per calendar, soonest first."""
    return ("const ids = " + json.dumps(cals) + "; "
            "const ev = ids.map((id) => states[id]).filter((x) => x && x.attributes.start_time)"
            ".map((x) => ({d: new Date(x.attributes.start_time.replace(' ', 'T')), m: x.attributes.message || '?', "
            "all: x.attributes.all_day})).filter((e) => !isNaN(e.d)).sort((a, b) => a.d - b.d); ")


def agenda_row(cals, i, colour, names=None):
    """Row i of the next-event-per-calendar list. names: {event title: display title}."""
    title = "(" + json.dumps(names, ensure_ascii=False) + "[e.m] || e.m)" if names else "e.m"
    label = "[[[ " + js_events(cals) + "const e = ev[" + str(i) + "]; if (!e) return '—'; " \
            "const m = " + title + "; return m.length > 30 ? m.slice(0, 29) + '…' : m; ]]]"
    value = "[[[ " + js_events(cals) + "const e = ev[" + str(i) + "]; if (!e) return ''; const d = e.d; " + REL + \
            "return wd + ' ' + dm + (e.all ? '' : ' ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'})) " \
            "+ ' · ' + rel; ]]]"
    card = row(None, "", {"default": colour}, value, label_js=label, interactive=False)
    card["triggers_update"] = cals
    return card


# Foreign cards that have no LCARdS equivalent get an LCARS skin via UIX
LCARS_SKIN = (":host { --primary-color: #FF9900; --accent-color: #FF9900; --primary-text-color: #FFCC99; "
              "--secondary-text-color: #9999CC; --text-primary-color: #000; --divider-color: #2a2a3a; "
              "--secondary-background-color: #0d0d16; --card-background-color: #000; --ha-card-background: #000; "
              "--mdc-theme-primary: #FF9900; --state-icon-color: #99CCFF; } "
              "ha-card { background: #000 !important; border: none !important; border-radius: 0 !important; "
              "box-shadow: none !important; font-family: Antonio, sans-serif !important; }")


def skinned(card, extra=""):
    card = json.loads(json.dumps(card))
    card["uix"] = {"style": LCARS_SKIN + (" " + extra if extra else "")}
    return card


def framed(title, colour, card, head_rows="clamp(30px, 4.2vh, 54px)", overflow="auto", cap="left"):
    """LCARS section header above an embedded card that fills the rest.

    Charts need overflow="hidden": ApexCharts' canvas sticks out a little below the SVG,
    and the resulting scrollbars shrink the chart container.
    """
    return grid('"h" "c"', "1fr", f"{head_rows} 1fr", [at(header(title, colour, cap=cap), "h"),
                                                       at(card, "c", overflow=overflow)], gap="8px")


def cols(*items, widths=None, gap="0 22px"):
    names = [f"k{i}" for i in range(len(items))]
    widths = widths or ["1fr"] * len(items)
    return grid('"' + " ".join(names) + '"', " ".join(widths), "1fr",
                [at(c, n) for c, n in zip(items, names)], gap=gap)


# ── Header readouts per section ─────────────────────────────────────────────────
def section_readouts(section):
    if section == "aquarium":
        return [
            readout(POWER, "Total power", "{entity.state}"),
            readout(PUMP, "Circulation", js_map(PUMP_STATES),
                    {k: v[2] for k, v in PUMP_STATES.items()} | {"default": PEACH}),
            number_columns(),
            (header_buttons("aquarium"), "wide"),
        ]
    if section == "home":
        return [
            readout(WEATHER, "Outside", "[[[ return entity.attributes.temperature + ' °C'; ]]]", ICE),
            readout(WEATHER, "Condition", js_map({k: (v, "", "") for k, v in WEATHER_NAMES.items()}), SUNFLOWER),
            number_columns(),
            (header_buttons("home"), "wide"),
        ]
    if section == "osmosis":
        return [
            readout(OSMO["switch"], "RO unit", "[[[ return entity.state === 'on' ? 'Online' : 'Offline'; ]]]",
                    {"on": ICE, "default": GRAY}),
            readout(OSMO["mode"], "Mode", "{entity.state}", PEACH),
            readout(OSMO["power"], "Power", "{entity.state}", ORANGE),
            readout(OSMO["energy"], "Energy", "{entity.state}", LILAC),
        ]
    if section == "laundry":
        return [
            readout(WASH["power"], "Cycle", f"[[[ return parseFloat(entity.state) > {WASH_RUNNING} ? 'Running' : "
                                            "'Idle'; ]]]", ICE),
            readout(WASH["power"], "Power", "{entity.state}", ORANGE),
            number_columns(),
            (header_buttons("laundry"), "wide"),
        ]
    if section == "waste":
        return [
            readout(NEXT_PICKUP, "Next pickup", JS_NEXT_BIN, ORANGE),
            readout(NEXT_PICKUP, "Date", js_de_date("entity.state", weekday=False), PEACH),
            number_columns(),
            (header_buttons("waste"), "wide"),

        ]
    if section == "calendar":
        nxt = "[[[ " + js_events(ALL_CALS) + "const e = ev[0]; if (!e) return '—'; const n = " + \
              json.dumps(BIN_NAMES, ensure_ascii=False) + "; return n[e.m] || e.m; ]]]"
        when = "[[[ " + js_events(ALL_CALS) + "const e = ev[0]; if (!e) return '—'; const d = e.d; " + REL + \
               "return dm + ' · ' + rel; ]]]"   # no weekday: the slot is narrow
        today = "[[[ " + js_events(ALL_CALS) + "const t = new Date().toDateString(); " \
                "return ev.filter((e) => e.d.toDateString() === t).length; ]]]"
        cards = [readout("sensor.time", "Next event", nxt, ORANGE), readout("sensor.time", "When", when, PEACH),
                 readout("sensor.time", "Today", today, ICE), readout("sensor.time", "Local time", "{entity.state}")]
        for c in cards[:3]:
            c["triggers_update"] = ALL_CALS
        return cards
    raise KeyError(section)


# ── Native section content ──────────────────────────────────────────────────────
JS_COMPASS = ("const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']; "
              "const compass = (b) => dirs[Math.round(b / 22.5) % 16]; ")
JS_HHMM = "const hhmm = (t) => new Date(t).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); "


ATMOS_LABEL_W = 150      # "Temperature" needs more than DATA_LABEL_W next to its code


def home_content():
    """OPS in the waste page's language: framed groups, label blocks as pillars, a graphic next to
    every value, light custom cards for the bars. Below priority 2 the lower frames are open at the
    bottom and the forecast bars are shorter."""
    return tiered({2: _home(compact=False), 1: _home(compact=True)})


def _home(compact):
    w = WEATHER
    # like the waste page: the top frames stay open at the bottom, the lower ones close the page
    atmosphere = panel("Atmosphere", ICE, pillar=ATMOS_LABEL_W, bottom=False, content=pillar_rows([
        ("Temperature", PEACH, lcars_code("ops/temperature"),
         with_bar(value_text("[[[ return entity.attributes.temperature + ' °C'; ]]]", w),
                  level_bar(w, PEACH, "temperature", -10, 35), "left")),
        ("Humidity", ICE, lcars_code("ops/humidity"),
         with_bar(value_text("[[[ return Math.round(entity.attributes.humidity) + ' %'; ]]]", w),
                  level_bar(w, ICE, "humidity", 0, 100), "left")),
        ("Pressure", LILAC, lcars_code("ops/pressure"),
         with_bar(value_text("[[[ return Math.round(entity.attributes.pressure) + ' hPa'; ]]]", w),
                  level_bar(w, LILAC, "pressure", 970, 1050), "left")),
        ("Wind", PERI, lcars_code("ops/wind"),
         with_bar(value_text("[[[ " + JS_COMPASS + "const a = entity.attributes; "
                             "return Math.round(a.wind_speed) + ' km/h · ' + compass(a.wind_bearing); ]]]", w),
                  level_bar(w, PERI, "wind_speed", 0, 60), "left")),
        ("Daylight", SUNFLOWER, lcars_code("ops/daylight"),
         with_bar(value_text("[[[ " + JS_HHMM + "const a = entity.attributes; "
                             "return hhmm(a.next_rising) + ' – ' + hhmm(a.next_setting); ]]]", "sun.sun"),
                  span_bar("sun.sun", SUNFLOWER, "next_rising", "next_setting"), "left")),
    ], filler=ICE, label_w=ATMOS_LABEL_W))
    radar = panel("Precipitation radar", BLUEY, side="right", pillar=DECOR_PILLAR_W, bottom=False,
                  content=radar_card())
    forecast = panel("Forecast", LILAC, pillar=DECOR_PILLAR_W, bottom=not compact, content=with_decor_pillar(
        {"type": "custom:lcars-forecast", "entity": w, "hours": 12, "segments": 6 if compact else 8, "font": "Antonio, sans-serif",
         "colours": {"temp": PEACH, "rain": ICE, "off": rgba(PERI, 0.18), "text": PERI, "dim": GRAY, "flash": "#FFFFFF"},
         "blink": [8000, 24000], "off_fraction": 0.025},
        "ops/forecast", [BONE, PERI, ICE], side="left", filler=LILAC))
    # the lower frames face each other: their shoulders meet in the middle
    week = panel("Next 7 days", SUNFLOWER, side="right", pillar=ATMOS_LABEL_W, content=week_calendar(),
                 join_top=True, bottom=not compact)
    # sized like the waste page: fits the 1280x800 tablet, the rest of the page stays black
    top_h = f"calc({data_panel_height(5)} - {PANEL_CORNER}px)"
    bottom_h = f"calc({data_panel_height(5)} - {PANEL_CORNER}px)" if compact else data_panel_height(5)
    lower = grid('"week fc"', "1.15fr 1fr", "1fr", [at(week, "week"), at(forecast, "fc")], gap="0 8px")
    return grid('"atm atm radar" "low low low" ". . ."', "1fr 1fr 1.4fr", f"{top_h} {bottom_h} 1fr",
                [at(atmosphere, "atm"), at(radar, "radar"), at(lower, "low")],
                gap="clamp(12px, 2vh, 24px) 8px")


DECOR_PILLAR_W = 90      # pillar of decorative blocks next to embedded content (radar, forecast)


def with_decor_pillar(content, key, colours, side="right", filler=None):
    """Content next to a pillar of LCARS blocks with auto numbers and no function (use with
    panel(pillar=DECOR_PILLAR_W)). A filler piece in the frame colour runs into the bottom shoulder."""
    names = [f"p{i}" for i in range(len(colours))] + (["pf"] if filler else [])
    blocks = [at(block(c, None, lcars_code(f"{key}/{i}")), n) for i, (c, n) in enumerate(zip(colours, names))]
    if filler:
        blocks.append(at(block(filler), "pf"))
    rows = " ".join(["1fr"] * len(colours) + (["14px"] if filler else []))
    pillar = grid(" ".join(f'"{n}"' for n in names), "1fr", rows, blocks, gap=f"{PANEL_GAP}px")
    areas, widths = ('"c p"', f"1fr {DECOR_PILLAR_W}px") if side == "right" else ('"p c"', f"{DECOR_PILLAR_W}px 1fr")
    return grid(areas, widths, "1fr", [at(content, "c", overflow="hidden"), at(pillar, "p")], gap="0 16px")


# Precipitation radar: DWD composite + nowcast (ha/www/lcars-radar.js). Borders come from the DWD WFS at
# build time (its WMS forbids custom styles), rounded to ~100 m and passed to the card as SVG paths.
RADAR_CENTER, RADAR_HOME, RADAR_WIDTH_KM = (50.00, 8.00), (50.00, 8.00), 170
DWD_WFS = "https://maps.dwd.de/geoserver/dwd/ows"


def dwd_border_path(layer, digits=3, margin=(0.9, 1.4)):
    """SVG path (x = lon, y = -lat) of a DWD WFS polygon layer's outlines, clipped to the radar area plus a
    margin (paths break where they leave it) and rounded to `digits` decimals (3 ~ 100 m)."""
    lat, lon = RADAR_CENTER
    inside = lambda x, y: abs(y - lat) <= margin[0] and abs(x - lon) <= margin[1]
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
    return "".join(parts)


def radar_card():
    return {"type": "custom:lcars-radar", "center": list(RADAR_CENTER), "home": list(RADAR_HOME),
            "width_km": RADAR_WIDTH_KM, "layer": "dwd:Radar_wn-product_1x1km_ger",
            "past_min": 60, "future_min": 90, "step_min": 10, "lag_min": 10, "frame_ms": 500, "hold_ms": 1600,
            "borders": [{"d": dwd_border_path("dwd:Warngebiete_Kreise"), "colour": PERI, "width": 1, "opacity": 0.35},
                        {"d": dwd_border_path("dwd:Laender", digits=2), "colour": LILAC, "width": 1.5,
                         "opacity": 0.8}],
            "pillar": {"width": DECOR_PILLAR_W, "gap": PANEL_GAP, "filler": BLUEY, "ink": INK,
                       "blocks": [{"colour": c, "code": lcars_code(f"ops/radar/{i}")}
                                  for i, c in enumerate([PERI, ICE, LILAC, ORANGE])]},   # play, back, next, now
            "colours": {"past": PERI, "now": ORANGE, "future": LILAC, "text": PERI, "dim": GRAY, "home": ORANGE},
            "font": "Antonio, sans-serif"}


WEEK_PALETTE = [PEACH, ICE, LILAC, PERI, SUNFLOWER, ALMOND, ROSE, BUTTERSCOTCH, VIOLET, BLUEY]


def week_calendar():
    """Next 7 days of every calendar (ha/www/lcars-week.js): like the waste timeline, a label block per
    calendar with events (the pillar), a column per day, event titles in the calendar's colour."""
    waste = dict(zip(WASTE_CALS, [c for _, _, c in BINS] + [RED]))
    labels = {c["entity"]: CAL_LABELS.get(c.get("label"), c.get("label"))
              for c in foreign_card("dashboard-termine", "kalender").get("calendars", [])}
    others = iter(WEEK_PALETTE)
    cals = [{"entity": e, "label": labels.get(e, e.split(".")[1]), "colour": waste.get(e) or next(others),
             "code": lcars_code(f"week/{e}")} for e in ALL_CALS]
    return {"type": "custom:lcars-week", "days": 7, "calendars": cals, "titles": BIN_NAMES, "max_rows": 5,
            "label_w": ATMOS_LABEL_W, "side": "right",
            "pillar": SUNFLOWER, "head": TL_HEAD, "row": DATA_ROW, "gap": PANEL_GAP, "font": "Antonio, sans-serif",
            "colours": {"empty": rgba(PERI, 0.1), "weekend": rgba(PERI, 0.05), "today": rgba(PERI, 0.22),
                        "text": PERI, "text_weekend": GRAY, "text_today": ORANGE, "ink": INK}}


TIMELINE_DAYS = 28
TIMELINE_LABEL_W = 150   # label column = the timeline panel's left pillar
# Fixed row heights, so the frames hug their content instead of filling the viewport
# Budget at 1280x800 (tablet): the content area is ~550 px high, timeline + data panels must fit
TL_HEAD, TL_ROW, TL_AXIS, TL_GAP = "clamp(22px, 2.8vh, 30px)", "clamp(24px, 3.4vh, 40px)", "clamp(24px, 3vh, 32px)", 4
DATA_ROW, DATA_GAP = "clamp(28px, 3.8vh, 46px)", TL_GAP
DATA_LABEL_W = 130      # label blocks = pillar of the data panels

PANEL_T = 26        # bar thickness of a panel frame; the title sits in it, so it must fit the font
PANEL_PILLAR = 26   # width of its pillar
PANEL_CORNER = 46   # size of the shoulder (elbow card)
PANEL_GAP = TL_GAP  # gap between the pieces of a pillar


def panel_elbow(kind, colour, pillar=PANEL_PILLAR):
    return {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": pillar, "bar_height": PANEL_T, "outer_curve": PANEL_CORNER,
                                  "inner_curve": PANEL_CORNER - PANEL_T, "color": {"default": colour}}}}


def panel(title, colour, content, *, side="left", pillar=None, top=True, bottom=True, overflow="hidden",
          join_top=False, caption=True):
    """Content in its own LCARS bracket: a pillar on `side` with shoulders (elbows) at the ends that
    have a bar. The top bar is interrupted by the title; with top=False the frame is open at the top
    and the title moves into the bottom bar (a caption; caption=False: no title, e.g. when the title sits
    in a bar shared with the frame above, see s_frames()). bottom=False leaves the bottom open.

    pillar=<px>: the content brings its own pillar of that width as its column on `side` (e.g. the
    timeline's label blocks, see pillar_rows()); the shoulders widen to match. join_top: its first piece is
    in the frame colour and runs into the top shoulder without a gap (overlapping by 2 px, like fillers)."""
    right = side == "right"
    pw = pillar or PANEL_PILLAR
    corner = (pw + PANEL_CORNER - PANEL_T if pillar else PANEL_CORNER) + 8
    title_w = int(len(title) * PANEL_T * 0.42) + 18        # Antonio is narrow: ~0.4 em per character
    pad = "right" if right else "left"
    title_card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
                  "text": {"t": {"content": title, "position": f"center-{pad}", "font_size": PANEL_T,
                                 "color": colour, "text_transform": "uppercase", "padding": {pad: 10}}}}

    def line(edge, main):          # one row of the areas, edge column on the pillar side
        return f'"{main} {edge}"' if right else f'"{edge} {main}"'

    def bar(edge, titled):
        """Horizontal bar on the top/bottom edge of its row, optionally interrupted by the title."""
        seg = '"b t a"' if right else '"a t b"'
        widths = f"1fr {title_w}px 14px" if right else f"14px {title_w}px 1fr"
        parts = [at(block(colour), "a"), at(title_card, "t"), at(block(colour), "b")]
        if not titled:
            seg, widths, parts = '"b"', "1fr", [at(block(colour), "b")]
        blank = '"' + " ".join("." for _ in seg.strip('"').split()) + '"'
        areas_ = f"{seg} {blank}" if edge == "top" else f"{blank} {seg}"
        rows_ = f"{PANEL_T}px 1fr" if edge == "top" else f"1fr {PANEL_T}px"
        return grid(areas_, widths, rows_, parts, gap="0 6px")

    areas, rows, cards = [], [], []
    body_edge = "body" if pillar else "side"
    if top:
        areas.append(line("tl", "top"))
        rows.append(f"{PANEL_CORNER}px")
        cards += [at(panel_elbow("header-right" if right else "header-left", colour, pw), "tl"),
                  at(bar("top", True), "top")]
    areas.append(line(body_edge, "body"))
    rows.append("1fr")
    if bottom:
        areas.append(line("bl", "bot"))
        rows.append(f"{PANEL_CORNER}px")
        cards += [at(panel_elbow("footer-right" if right else "footer-left", colour, pw), "bl"),
                  at(bar("bottom", not top and caption), "bot")]
    if pillar:
        # the pillar's blocks keep the same small gap to the top shoulder as between each other; at the
        # bottom the pillar's filler piece (pillar_rows(filler=...)) runs into the shoulder: it overlaps
        # it by 2 px, otherwise fractional zoom levels (110 %) leave a hairline seam
        cards.append(at(content, "body", overflow=overflow,
                        margin=f"{-2 if join_top else PANEL_GAP}px 0 {-2 if bottom else 0}px 0"))
    else:
        pillar_card = (grid('". p"', f"1fr {PANEL_PILLAR}px", "1fr", [at(block(colour), "p")], gap="0") if right else
                       grid('"p ."', f"{PANEL_PILLAR}px 1fr", "1fr", [at(block(colour), "p")], gap="0"))
        cards += [at(pillar_card, "side"),
                  at(content, "body", overflow=overflow, margin="0 -18px 0 0" if right else "0 0 0 -18px")]
    return grid(" ".join(areas), f"1fr {corner}px" if right else f"{corner}px 1fr", " ".join(rows), cards,
                gap="0 6px")


def collection_timeline():
    """Exterior-overview style grid: a label block per bin (LCARdS, part of the frame's pillar) and,
    next to them, the day grid itself as one lightweight custom card (ha/www/lcars-day-grid.js) instead
    of ~200 LCARdS buttons: weekday header, a cell per day, day numbers underneath."""
    series = [(label, e, colour, "attribute") for label, e, colour in BINS]
    series.append(("Hazmat", HAZMAT["date"], RED, "state"))
    track_rows = [TL_HEAD] + [TL_ROW] * len(series) + [TL_AXIS]
    gap = f"{TL_GAP}px 4px"
    day_grid = {"type": "custom:lcars-day-grid", "days": TIMELINE_DAYS, "rows": track_rows, "gap": gap,
                "series": [{"entity": e, "colour": colour, "match": match} for _, e, colour, match in series],
                "colours": {"empty": rgba(PERI, 0.1), "weekend": rgba(PERI, 0.05), "today": rgba(PERI, 0.22),
                            "text": PERI, "text_weekend": GRAY, "text_today": ORANGE},
                "font": "Antonio, sans-serif", "font_size": 15}
    areas = ['"lw days"'] + [f'"l{i} days"' for i in range(len(series))] + ['"lx days"']
    cards = [at(block(ORANGE), "lw")]      # pillar piece above the bins, part of the shoulder: no number
    cards += [at(block(colour, label, lcars_code(f"timeline/{label}"), align="center-right", size=17), f"l{i}")
              for i, (label, _, colour, _) in enumerate(series)]
    cards.append(at(block(ORANGE, "Day", lcars_code("timeline/day"), align="center-right", size=17), "lx"))
    cards.append(at(day_grid, "days"))
    # the day grid repeats these row tracks internally, so its rows line up with the label blocks
    return grid(" ".join(areas), f"{TIMELINE_LABEL_W}px 1fr", " ".join(track_rows), cards, gap=gap)


def pillar_rows(items, side="left", filler=None, label_w=DATA_LABEL_W):
    """Rows of (label, colour, code, value card): the label blocks stack up as the frame's pillar on
    `side` (use with panel(pillar=DATA_LABEL_W)), each value sits next to its block. A filler colour
    continues the pillar below the last row down to the shoulder. label may be a ready block card
    (e.g. one with an action)."""
    areas, cards = [], []
    for i, (label, colour, code, value) in enumerate(items):
        areas.append(f'"v{i} l{i}"' if side == "right" else f'"l{i} v{i}"')
        lbl = label if isinstance(label, dict) else block(colour, label, code, align="center-right", size=17)
        cards += [at(lbl, f"l{i}"), at(value, f"v{i}")]
    rows = [DATA_ROW] * len(items)
    if filler:
        areas.append('". f"' if side == "right" else '"f ."')
        cards.append(at(block(filler), "f"))
        rows.append("1fr")
    widths = f"1fr {label_w}px" if side == "right" else f"{label_w}px 1fr"
    return grid(" ".join(areas), widths, " ".join(rows), cards, gap=f"{DATA_GAP}px 16px")


def value_text(value_js, entity, align="left", colour=PERI):
    """Just the value of a data row, aligned towards its label block. colour may be a state map."""
    return {"type": "custom:lcards-button", "entity": entity, "preset": "text-only", "show_icon": False,
            "tap_action": {"action": "more-info"},
            "text": {"value": {"content": value_js, "position": f"center-{align}", "color": colour,
                               "text_transform": "uppercase", "font_size": "var(--lcars-data-size)",
                               "font_weight": "bold", "padding": {align: 4}}}}


VALUE_W = "clamp(190px, 15vw, 290px)"   # value column next to a countdown bar
BAR_SEGMENTS = 14                        # countdown bars: one segment per 2 days, 0-28 days like the timeline

_BLINK = random.Random(1701)
BAR_OFF = rgba(PERI, 0.18)   # inactive bar segment
# Segment bars (ha/www/lcars-bar.js): input_boolean.lcars_bars switches them off for everyone
# (?lcars_bars=off|on|toggle, see ha/www/lcars-motion.js). HA's hui-card, which LCARdS layout cards
# wrap every child in, doesn't render a card whose visibility conditions fail.
BARS_HELPER = "input_boolean.lcars_bars"
BARS_VISIBLE = [{"condition": "state", "entity": BARS_HELPER, "state": "on"}]


def data_bar(entity, colour, mode, segments, side, **extra):
    """Segmented bar as one light custom card (ha/www/lcars-bar.js): segment 0 sits next to the value
    (towards the pillar on `side`); lit segments flash white briefly at random rates fixed here."""
    bar = {"type": "custom:lcars-bar", "entity": entity, "mode": mode, "segments": segments,
           "days_per_segment": 28 // BAR_SEGMENTS, "side": side, "colour": colour, "off": BAR_OFF,
           # cycle 8-24 s per segment, flashing white for 2.5 % of it (0.2-0.6 s)
           "blink": [_BLINK.randrange(8000, 24000, 500) for _ in range(segments)], "off_fraction": 0.025,
           "flash": "#FFFFFF", "gap": 3, **extra}
    bar["visibility"] = BARS_VISIBLE
    return bar


def countdown_bar(entity, colour, side):
    """Days until the date in entity.state, 2 days per segment, growing away from the pillar."""
    return data_bar(entity, colour, "countdown", BAR_SEGMENTS, side)


def window_bar(entity, colour, side):
    """24 h scale, one segment per hour, the hours of the time window in entity.state lit."""
    return data_bar(entity, colour, "window", 24, side)


def level_bar(entity, colour, attribute, lo, hi, side="left"):
    """A number (entity attribute) on a lo..hi scale, 14 segments."""
    return data_bar(entity, colour, "level", BAR_SEGMENTS, side, attribute=attribute, min=lo, max=hi)


def span_bar(entity, colour, start_attr, end_attr, side="left"):
    """24 h scale with the hours between two ISO timestamps (attributes) lit, e.g. daylight."""
    return data_bar(entity, colour, "span", 24, side, start_attr=start_attr, end_attr=end_attr)


def with_bar(value, bar, side, width=VALUE_W):
    """Value next to the pillar, its bar filling the rest of the row."""
    if side == "right":
        return grid('"b v"', f"1fr {width}", "1fr", [at(bar, "b", margin="clamp(6px, 1vh, 10px) 0"),
                                                       at(value, "v")], gap="0 14px")
    return grid('"v b"', f"{width} 1fr", "1fr", [at(value, "v"), at(bar, "b", margin="clamp(6px, 1vh, 10px) 0")],
                gap="0 14px")


def data_panel_height(n):
    """Height of a panel with top and bottom bars around n data rows: rows, the gaps between them and
    to both shoulders, and a short filler piece of pillar."""
    return f"calc({n} * {DATA_ROW} + {(n + 1) * DATA_GAP + 12}px + {2 * PANEL_CORNER}px)"


def waste_content():
    """Priority 2 shows the lower frames closed; below it they are open at the bottom (the shoulders are
    the first thing to go on a short screen)."""
    return tiered({2: _waste(compact=False), 1: _waste(compact=True)})


def _waste(compact):
    timeline = panel(f"Collection timeline · {TIMELINE_DAYS} days", ORANGE, collection_timeline(),
                     pillar=TIMELINE_LABEL_W, bottom=False, join_top=True)
    # The two lower frames face each other: pillars meet in the middle, labels next to them
    schedule = panel("Next per bin", PEACH, side="right", pillar=DATA_LABEL_W, bottom=not compact, content=pillar_rows(
        [(label, colour, lcars_code(f"next-per-bin/{label}"),
          with_bar(value_text(js_de_date("entity.state"), e, "right"), countdown_bar(e, colour, "right"), "right"))
         for label, e, colour in BINS], side="right", filler=PEACH))
    hazmat = panel("Hazmat collection", RED, pillar=DATA_LABEL_W, bottom=not compact, content=pillar_rows([
        ("Date", BONE, lcars_code("hazmat/date"),
         with_bar(value_text(js_iso_date("entity.state"), HAZMAT["date"]),
                  countdown_bar(HAZMAT["date"], RED, "left"), "left")),
        ("Window", BONE, lcars_code("hazmat/window"),
         with_bar(value_text("[[[ return String(entity.state).replace(/\\s*Uhr$/, ''); ]]]", HAZMAT["window"]),
                  window_bar(HAZMAT["window"], RED, "left"), "left")),
        ("Location", BONE, lcars_code("hazmat/location"),
         value_text("[[[ return String(entity.state).split(',')[0]; ]]]", HAZMAT["place"])),
    ], filler=RED))
    n_tl = len(BINS) + 1
    timeline_h = f"calc({PANEL_CORNER}px + {TL_HEAD} + {n_tl} * {TL_ROW} + {TL_AXIS} + {(n_tl + 2) * TL_GAP}px)"
    # Sized to content, not stretched to the viewport; what's left stays black
    lower_h = f"calc({data_panel_height(4)} - {PANEL_CORNER}px)" if compact else data_panel_height(4)
    return grid('"t t" "s h" ". ."', "1fr 1fr", f"{timeline_h} {lower_h} 1fr",
                [at(timeline, "t"), at(schedule, "s"), at(hazmat, "h")], gap="clamp(12px, 2vh, 24px) 8px")


WASH_RUNNING = 3                    # W: above this the machine is running
WASH_MAX = 2000                     # W: scale of the power bar (peaks ~1.9 kW when heating)


def power_card(entity, key="laundry"):
    """Power over 24 h / 7 d / 28 d (ha/www/lcars-power.js), drawn like the aquarium power chart (log scale,
    filled area, W lines), with its own pillar of range buttons on the left; the active one is orange."""
    ranges = [("24h", 24, "5minute"), ("7d", 168, "hour"), ("28d", 672, "hour")]
    return {"type": "custom:lcars-power", "entity": entity,
            "ranges": [{"label": label, "hours": hours, "period": period} for label, hours, period in ranges],
            "ticks": [1, 10, 100, 1000], "max": 2500,
            "pillar": {"width": DECOR_PILLAR_W, "gap": PANEL_GAP, "side": "left", "active": ORANGE, "filler": ORANGE,
                       "ink": INK, "blocks": [{"colour": c, "code": lcars_code(f"{key}/range/{label}")}
                                              for c, (label, _, _) in zip([ALMOND, PEACH, BONE], ranges)]},
            "colours": {"line": ALMOND, "fill_opacity": 0.35, "grid": GRAY, "axis": DIM, "text": DIM},
            "font": "Antonio, sans-serif"}


def state_bar(entity, states, side, threshold=None):
    """Status as a bar: every segment lit in the colour of the current state (none if it isn't listed)."""
    extra = {"states": states} | ({"threshold": threshold} if threshold is not None else {})
    return data_bar(entity, PERI, "state", BAR_SEGMENTS, side, **extra)


def laundry_content():
    """Laundry in the waste page's language: the unit's frame on top (pillar left, like OPS' atmosphere),
    the power chart with its range buttons below (priority 2, like the other charts)."""
    wsh = WASH
    trace = panel("Power trace", ORANGE, pillar=DECOR_PILLAR_W, content=power_card(wsh["power"]))
    supply = value_text("[[[ return entity.state === 'on' ? 'On' : 'Off'; ]]]", wsh["switch"], "left",
                        {"off": GRAY, "default": PERI})
    supply["hold_action"] = {"action": "toggle"}       # hold to switch (on purpose), tap shows more-info
    supply_block = block(PERI, "Supply", lcars_code("laundry/supply"), align="center-right", size=17)
    supply_block.update({"interactive": True, "hold_action": {"action": "toggle"}, "entity": wsh["switch"]})
    unit = panel("Laundry unit", LILAC, pillar=DATA_LABEL_W, content=pillar_rows([
        ("Cycle", ICE, lcars_code("laundry/cycle"),
         with_bar(value_text(f"[[[ return parseFloat(entity.state) > {WASH_RUNNING} ? 'Running' : 'Idle'; ]]]",
                             wsh["power"]),
                  state_bar(wsh["power"], {"on": ICE}, "left", threshold=WASH_RUNNING), "left")),
        ("Power", ALMOND, lcars_code("laundry/power"),
         with_bar(value_text("{entity.state}", wsh["power"]),
                  data_bar(wsh["power"], ALMOND, "level", BAR_SEGMENTS, "left", min=0, max=WASH_MAX), "left")),
        ("Energy", BONE, lcars_code("laundry/energy"), value_text("{entity.state}", wsh["energy"])),
        (supply_block, PERI, None, supply),
    ], filler=LILAC))
    # what's left below the chart stays black
    return grid('"u" "t" "."', "1fr", f"{data_panel_height(4)} {chart_height()} 1fr",
                [at(shown_from(trace, 2), "t"), at(unit, "u")], gap="clamp(12px, 2vh, 24px) 8px")


# ── Aquarium (reference style) ──────────────────────────────────────────────────
AQ_LABEL_W = ATMOS_LABEL_W   # "Maintenance", "CO² coupling" next to their code
LIGHT_POWER = "sensor.chihiros_wrgb2_slim_90_leistung"
DOSE_COLOURS = [PEACH, ICE, ALMOND, LILAC]
DOSE_LOW_ML = 50             # fill level below this: its bar turns red
JS_HHMM_OF = "const hhmm = (t) => new Date(t).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); "


def state_row(label, colour, key, entity, value_js, bar_states, value_colours=None, side="left", toggle=False,
              triggers=None):
    """Data row for a status: value (PERI unless value_colours says otherwise) and a status bar lit in the
    state's colour. toggle=True: a switch; tapping the block or the value switches it (hold: more-info), and
    it has no bar (a button, not a reading)."""
    value = value_text(value_js, entity, "right" if side == "right" else "left",
                       {"default": PERI, **(value_colours or {})})
    if triggers:
        value["triggers_update"] = triggers       # other entities the value reads
    blk = block(colour, label, lcars_code(key), align="center-right", size=17)
    if toggle:
        for card in (value, blk):
            card.update({"interactive": True, "entity": entity, "tap_action": {"action": "toggle"},
                         "hold_action": {"action": "more-info"}})
        return (blk, colour, None, value)
    return (blk, colour, None, with_bar(value, state_bar(entity, bar_states, side), side))


def plain_row(label, colour, key, entity, value_js, side="left"):
    return (label, colour, lcars_code(key), value_text(value_js, entity, "right" if side == "right" else "left"))


def on_off_js(on, off):
    return f"[[[ return entity.state === 'on' ? '{on}' : '{off}'; ]]]"


def aq_panel(title, colour, rows, side="left", label_w=AQ_LABEL_W, **kw):
    return panel(title, colour, side=side, pillar=label_w,
                 content=pillar_rows(rows, side=side, filler=colour, label_w=label_w), **kw)


def mode_button(label, entity, on, off, key):
    """Rounded LCARS button that switches `entity`: in `on` while on, `off` while off (hold: more-info)."""
    card = block(off, label, lcars_code(key), size=20)
    card.update({"entity": entity, "interactive": True, "tap_action": {"action": "toggle"},
                 "hold_action": {"action": "more-info"}})
    card["style"] = {"card": {"color": {"background": {"on": on, "off": off, "default": GRAY}}},
                     "border": {"width": 0, "radius": 40}}
    card["text"]["label"]["padding"] = {"right": 24, "bottom": 6}
    card["text"]["code"]["padding"] = {"left": 22, "top": 6}
    return card


def status_content():
    """Four groups in facing frames: modes | equipment, illumination | water change."""
    buttons = [
        mode_button("[[[ return entity.state === 'on' ? 'Auto mode' : 'Manual mode'; ]]]", "switch.aquarium_auto_mode",
                    ICE, SUNFLOWER, "aquarium/mode"),
        mode_button("Maintenance", "switch.aquarium_maintenance_mode", RED, GRAY, "aquarium/maintenance"),
        mode_button("[[[ " + JS_HHMM_OF + "const r = entity.attributes.resume_at; "
                    "return entity.state === 'on' && r ? 'Feeding · ' + hhmm(r) : 'Feeding'; ]]]",
                    "switch.aquarium_feeding_mode", ICE, GRAY, "aquarium/feeding"),
        mode_button("Water change", "switch.aquarium_water_change_mode", RED, GRAY, "aquarium/water-change-mode"),
    ]
    pad = f"{PANEL_GAP + 6}px 0"
    button_grid = grid('"a b" "c d"', "1fr 1fr", "1fr 1fr", [at(c, n, margin=pad) for c, n in zip(buttons, "abcd")],
                       gap="6px 14px")
    modes = panel("Modes", ORANGE, side="right", pillar=DECOR_PILLAR_W, content=with_decor_pillar(
        button_grid, "aquarium/modes", [PEACH, BONE], filler=ORANGE))
    pump_colours = {"Running": ICE, "Warning": SUNFLOWER, "Critical": RED}
    co2_colours = {"Running": ICE, "Manual": SUNFLOWER, "Safety Cutoff": RED}
    equipment = aq_panel("Equipment", LILAC, rows=[
        state_row("Pump", ICE, "aquarium/pump", PUMP,
                  "[[[ const a = entity.attributes; const m = " + json.dumps({k: v[0] for k, v in PUMP_STATES.items()}) +
                  "; const s = m[entity.state] || entity.state; if (a.off_minutes != null) return s + ' · ' + "
                  "a.off_minutes + ' min'; return a.power != null ? s + ' · ' + a.power + ' W' : s; ]]]",
                  pump_colours, {"Warning": SUNFLOWER, "Critical": RED, "Off": GRAY}),
        state_row("Heater", BUTTERSCOTCH, "aquarium/heater", HEATER, on_off_js("On", "Off"),
                  {"on": BUTTERSCOTCH}, {"off": GRAY}),
        state_row("CO²", LILAC, "aquarium/co2", CO2,
                  "[[[ const a = entity.attributes; const m = " + json.dumps({k: v[0] for k, v in CO2_STATES.items()}) +
                  "; const s = m[entity.state] || entity.state; "
                  "return a.reason === 'hysteresis_hold' ? s + ' · hold' : s; ]]]",
                  co2_colours, {"Manual": SUNFLOWER, "Safety Cutoff": RED, "Idle": GRAY}),
        state_row("CO² coupling", PERI, "aquarium/co2-coupling", CO2_COUPLING, on_off_js("Coupled", "Manual"),
                  {"on": ICE, "off": SUNFLOWER}, {"off": SUNFLOWER}, toggle=True),
    ])
    phase_colours = {k: v[2] for k, v in PHASE_STATES.items() if k != "Off"}
    light = aq_panel("Illumination", SUNFLOWER, side="right", rows=[
        state_row("Automation", PEACH, "aquarium/light-auto", LIGHT_AUTO, on_off_js("Schedule", "Manual"),
                  {"on": ICE, "off": SUNFLOWER}, {"off": SUNFLOWER}, "right", toggle=True),
        state_row("Light", SUNFLOWER, "aquarium/light-phase", PHASE, js_map(PHASE_STATES), phase_colours,
                  {"Off": GRAY}, "right"),
        plain_row("Next", BONE, "aquarium/light-next", PHASE,
                  "[[[ " + JS_HHMM_OF + "const a = entity.attributes; if (!a.next_change) return '–'; "
                  "return (a.next_phase || '?') + ' · ' + hhmm(a.next_change); ]]]", "right"),
    ])
    wc_colours = {"OK": ICE, "Due": SUNFLOWER, "Overdue": RED}
    days_since = value_text("[[[ const a = entity.attributes; const m = {Never: 'Never', OK: 'OK', Due: 'Due', "
                            "Overdue: 'Overdue'}; const s = m[entity.state] || entity.state; "
                            "return a.days_since == null ? s : s + ' · ' + a.days_since + ' d'; ]]]", WC, "left",
                            {"default": PERI, "Due": SUNFLOWER, "Overdue": RED, "Never": GRAY})
    water = aq_panel("Water change", ICE, rows=[
        ("Status", ICE, lcars_code("aquarium/wc-status"),
         with_bar(days_since, data_bar(WC, ICE, "level", BAR_SEGMENTS, "left", attribute="days_since", min=0,
                                       max=14, states=wc_colours), "left")),
        plain_row("Last change", BONE, "aquarium/wc-last", WC,
                  "[[[ const t = entity.attributes.last_water_change_at; if (!t) return '–'; const d = new Date(t); "
                  "return d.toLocaleDateString('en-GB', {weekday: 'short', day: '2-digit', month: '2-digit'})"
                  ".replace(',', '') + ' · ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); ]]]"),
        ("Next due", PERI, lcars_code("aquarium/wc-next"),
         with_bar(value_text(js_iso_date("entity.attributes.next_due_at"), WC),
                  data_bar(WC, ICE, "countdown", BAR_SEGMENTS, "left", attribute="next_due_at",
                           days_per_segment=1, states=wc_colours), "left")),
    ])
    upper = grid('"a b"', "1fr 1fr", "1fr", [at(modes, "a"), at(equipment, "b")], gap="0 8px")
    lower = grid('"a b"', "1fr 1fr", "1fr", [at(light, "a"), at(water, "b")], gap="0 8px")
    return grid('"u" "l" "."', "1fr", f"{data_panel_height(4)} {data_panel_height(3)} 1fr",
                [at(upper, "u"), at(lower, "l")], gap="clamp(12px, 2vh, 24px) 8px")


def visual_content():
    """The camera in its own frame (pillar of numbered blocks facing the readings), readings next to it."""
    cam = {"type": "custom:timed-camera-card", "entity": CAMERA, "still_interval": 30, "live_duration": 60,
           "show_name": False,
           "uix": {"style": "ha-card { background: #000 !important; border-radius: 0 !important; "
                            "border: none !important; box-shadow: none !important; }"}}
    camera = panel("Visual sensor 01", LILAC, side="right", pillar=DECOR_PILLAR_W,
                   content=with_decor_pillar(cam, "visual/camera", [BLUEY, PEACH, ICE], filler=LILAC))
    readings = aq_panel("Readings", ICE, rows=[
        plain_row("Feed", LILAC, "visual/feed", CAMERA, "[[[ return entity.state; ]]]"),
        plain_row("Circulation", ICE, "visual/circulation", PUMP, js_map(PUMP_STATES)),
        plain_row("Illumination", SUNFLOWER, "visual/illumination", PHASE, js_map(PHASE_STATES)),
        plain_row("Total power", ALMOND, "visual/power", POWER, "{entity.state}"),
    ])
    side = grid('"r" "."', "1fr", f"{data_panel_height(4)} 1fr", [at(readings, "r")], gap="0")
    return grid('"cam side"', "2.2fr 1fr", "1fr", [at(camera, "cam"), at(side, "side")], gap="0 8px")


LIGHT_PROFILES = [("Fire", {"red": 50, "green": 13, "blue": 0}, BUTTERSCOTCH),
                  ("Chill", {"red": 0, "green": 13, "blue": 50}, BLUEY)]
LIGHT_CHANNELS = [("red", "Red", RED), ("green", "Green", "#88CC88"), ("blue", "Blue", BLUEY)]


TRANSPORTER_SEGMENTS = 20    # 5 % each


def transporter_card():
    """The light channels as vertical transporter-console sliders (ha/www/lcars-transporter.js)."""
    return {"type": "custom:lcars-transporter", "min": 0, "max": 100, "step": 1, "segments": TRANSPORTER_SEGMENTS,
            "channels": [{"entity": CHANNEL.format(name), "label": label, "colour": colour,
                          "code": lcars_code(f"light/channel/{name}")} for name, label, colour in LIGHT_CHANNELS],
            "off": BAR_OFF, "slot": rgba(PERI, 0.08), "handle": BONE, "text": PERI, "dim": GRAY, "ink": INK,
            "label_h": f"calc({DATA_ROW} * 1.4)", "col_w": "clamp(70px, 7vw, 130px)",
            "blink": [_BLINK.randrange(8000, 24000, 500) for _ in range(TRANSPORTER_SEGMENTS)],
            "off_fraction": 0.025, "flash": "#FFFFFF", "gap": 3, "font": "Antonio, sans-serif"}


LIGHT_CONFIG = "/config/aquarium_light_control.yaml"   # the light schedule (aquarium_light_control)
HA_SSH = os.environ.get("HA_SSH", "hassio@homeassistant.local")


@functools.cache
def light_phases():
    """The light schedule's phases, read from the HA host at build time (no HA entity exposes them):
    start/end in minutes of the day, ramps, levels, a colour per phase. Rebuild after changing it."""
    out = subprocess.run(["ssh", "-o", "MACs=hmac-sha2-256-etm@openssh.com", HA_SSH, f"sudo cat {LIGHT_CONFIG}"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise SystemExit(f"can't read {LIGHT_CONFIG} from {HA_SSH}: {out.stderr.strip()}")

    def minutes(t):
        t = str(t).strip()
        if t in ("24:00", "24:00:00"):
            return 1439                  # like the integration: end of day = 23:59
        h, m = (t.split(":") + ["0"])[:2]
        return int(h) % 24 * 60 + int(m)

    return [{"name": p["name"], "start": minutes(p["start"]), "end": minutes(p["end"]),
             "up": int(p.get("ramp_up_minutes", 0)), "down": int(p.get("ramp_down_minutes", 0)),
             "levels": {str(k): int(v) for k, v in p.get("levels", {}).items()},
             "colour": PHASE_STATES.get(p["name"], (None, None, PERI))[2]}
            for p in yaml.safe_load(out.stdout).get("phases", [])]


def phases_card():
    """The light schedule over 24 h: a smooth shape per phase with its ramps, now line (ha/www/lcars-phases.js)."""
    return {"type": "custom:lcars-phases", "phases": light_phases(), "min_height": 0.3,
            "colours": {"grid": rgba(PERI, 0.15), "text": GRAY, "now": ORANGE}, "font": "Antonio, sans-serif"}


def s_joint(upper, lower, title):
    """The shared bar where one frame runs into the next, making an S: `upper` and `lower` are
    (side, colour, pillar width) of the frame above (open at the bottom) and below (open at the top), their
    pillars on opposite sides. The upper frame's bottom shoulder and the lower frame's top shoulder sit on
    the same bar, which carries `title` next to the lower frame's shoulder."""
    (su, cu, pu), (sl, cl, pl) = upper, lower
    corner = lambda pw: pw + PANEL_CORNER - PANEL_T + 8          # noqa: E731 (as panel() with a pillar)
    off = PANEL_CORNER - PANEL_T
    title_w = int(len(title) * PANEL_T * 0.42) + 18
    right = sl == "right"                                        # the title sits on the lower frame's side
    title_card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
                  "text": {"t": {"content": title, "position": "center-right" if right else "center-left",
                                 "font_size": PANEL_T, "color": cl, "text_transform": "uppercase",
                                 "padding": {"right" if right else "left": 10}}}}
    # the long part of the bar in the upper frame's colour, the short piece by the title in the lower one's
    left_c, right_c = (cu, cl) if right else (cl, cu)
    bar = grid('"a t b"', f"1fr {title_w}px 14px" if right else f"14px {title_w}px 1fr", "1fr",
               [at(block(left_c), "a"), at(title_card, "t"), at(block(right_c), "b")], gap="0 6px")
    # the upper shoulder's bar is at the bottom of its box, the lower one's at the top: offset to share it
    up = at(panel_elbow(f"footer-{su}", cu, pu), "u" if su == "left" else "l", margin=f"0 0 {off}px 0")
    low = at(panel_elbow(f"header-{sl}", cl, pl), "l" if sl == "right" else "u", margin=f"{off}px 0 0 0")
    lw, rw = (corner(pu), corner(pl)) if su == "left" else (corner(pl), corner(pu))
    return grid('"u m l"', f"{lw}px 1fr {rw}px", "1fr", [up, at(bar, "m", margin=f"{off}px 0"), low], gap="0 6px")


def s_chain(parts):
    """Frames stacked into an S (or a double S): parts = [(frame, height), joint, (frame, height), ...,
    optionally None last: the rest stays black]. A frame above a joint overlaps it by 2 px, so fractional
    zoom (110 %) leaves no hairline."""
    rows, cards = [], []
    for i, part in enumerate(parts):
        name = f"r{i}"
        if part is None:
            rows.append("1fr")
            cards.append(at(block(INK), name))       # nothing there; a card keeps the areas simple
        elif isinstance(part, tuple):
            frame, height = part
            last = i == len(parts) - 1
            cards.append(at(frame, name, **({} if last else {"margin": "0 0 -2px 0"})))
            rows.append(height)
        else:
            cards.append(at(part, name))
            rows.append(f"{2 * PANEL_CORNER - PANEL_T}px")
    return grid(" ".join(f'"r{i}"' for i in range(len(parts))), "1fr", " ".join(rows), cards, gap="0")


LIGHT_PLUG = "switch.chihiros_wrgb2_slim_90"      # smart plug powering the light (auto power-cycle)
LIGHT_ENTITY = "light.esszimmer_chihiros_wrgb2_slim_90_ble_xxxxxxxxxxxxxxxxxx_rgb"
LIGHT_BLE = "sensor.esszimmer_chihiros_wrgb2_slim_90_ble_xxxxxxxxxxxxxxxxxx_last_notification"
LOG_LEVELS = {"info": PERI, "ok": ICE, "warn": SUNFLOWER, "flap": BUTTERSCOTCH, "error": RED, "ble": GRAY}


def light_log_card():
    """Device log of the light and its plug (ha/www/lcars-log.js): phase changes, automation, light on/off,
    plug power, flapping/offline, protection flags, firmware, raw BLE notifications (collapsed bursts). Each
    line gets a descriptive detail; phase lines name the schedule's target levels."""
    levels = {p["name"]: p["levels"] for p in light_phases()}

    def rgb(name):
        lv = levels.get(name, {})
        return f"emitter array R {lv.get('red', 0)} · G {lv.get('green', 0)} · B {lv.get('blue', 0)}"

    ramp = {p["name"]: (p["up"], p["down"]) for p in light_phases()}.get("Daylight", (0, 0))
    phase = {
        "Daylight": ["Daylight", "info", f"Illumination cycle nominal · {rgb('Daylight')}"],
        "Daylight (ramping up)": ["Ramp up", "info", f"Emitter ramp initiated · plateau in {ramp[0]} min"],
        "Daylight (ramping down)": ["Ramp down", "info", f"Emitter ramp-down initiated · dark in {ramp[1]} min"],
        "Moonlight": ["Moonlight", "info", f"Nocturnal cycle engaged · {rgb('Moonlight')}"],
        "Off": ["Off", "info", "Emitter array standing down · all channels at zero"],
        "Manual Override": ["Manual override", "warn", "Sequencer suspended · channel levels under manual control"],
    }
    guards = [("uberhitzung", "Overtemperature", "Temperature ok", "Thermal cutoff tripped · plug protection active",
               "Thermal limits restored · protection reset"),
              ("uberlast", "Overload", "Load ok", "Load limit exceeded · relay protection active",
               "Load within tolerance · protection reset"),
              ("uberspannung", "Overvoltage", "Voltage ok", "Supply voltage above tolerance · relay protection active",
               "Supply voltage nominal · protection reset"),
              ("uberstrom", "Overcurrent", "Current ok", "Current draw above tolerance · relay protection active",
               "Current draw nominal · protection reset")]
    link = {"flap": "Link interruption · carrier reacquired, telemetry resumed",
            "offline": "Link lost · no telemetry from device",
            "online": "Link restored after {d} · telemetry resumed"}
    sources = [
        {"entity": PHASE, "tag": "Phase", "states": phase, "details": link},
        {"entity": LIGHT_AUTO, "tag": "Auto", "details": link, "states": {
            "on": ["Schedule", "ok", "Automatic sequencer engaged · following phase table"],
            "off": ["Manual", "warn", "Automatic sequencer disengaged · awaiting manual input"]}},
        {"entity": LIGHT_ENTITY, "tag": "Light", "details": link, "states": {
            "on": ["On", "info", "BLE command acknowledged · emitter array active"],
            "off": ["Off", "info", "BLE command acknowledged · emitter array dark"]}},
        {"entity": LIGHT_PLUG, "tag": "Plug", "details": link, "states": {
            "on": ["Power on", "ok", "Power relay closed · emitter bus energized"],
            "off": ["Power off", "error", "Power relay open · emitter bus de-energized"]}},
        *[{"entity": f"binary_sensor.chihiros_wrgb2_slim_90_{key}", "tag": "Plug", "details": link,
           "states": {"on": [bad, "error", bad_d], "off": [good, "ok", good_d]}}
          for key, bad, good, bad_d, good_d in guards],
        {"entity": "update.chihiros_wrgb2_slim_90_firmware", "tag": "Firmware", "details": link, "states": {
            "on": ["Update available", "warn", "New firmware package staged · install pending"],
            "off": ["Up to date", "ok", "Firmware verified · no update pending"]}},
        {"entity": LIGHT_BLE, "tag": "BLE", "burst": True,
         "default": [None, "ble", "Notification frames received · controller handshake"]},
    ]
    return {"type": "custom:lcars-log", "sources": sources, "hours": 24, "refresh_s": 60, "flap_s": 60,
            "burst_s": 60, "max_lines": 40, "levels": LOG_LEVELS,
            "colours": {"time": rgba(PERI, 0.55), "bright": "#DFE1E8"},
            "cascade_ms": 3 * CASCADE_MS, "stagger_ms": 90, "font": "Antonio, sans-serif", "font_size": 15}


def light_content():
    """Left, as a double S (s_chain): "Phase control" (phase rows next to the day's phases as a graph) runs
    into "Controls" (small LCARS buttons: automation on/off, the Fire and Chill profiles, numbered decorative
    pills), which runs into "Device log" in whatever height is left. Right: the channels as vertical
    transporter controls, as high as the page, pillar on the outer edge so its top bar meets Phase control's."""
    rows = pillar_rows([
        ("Current", SUNFLOWER, lcars_code("light/current"),
         value_text(js_map(PHASE_STATES), PHASE, "left", {"default": PERI, "Off": GRAY, "Manual Override": SUNFLOWER})),
        plain_row("Scheduled", BONE, "light/scheduled", PHASE, "[[[ return entity.attributes.scheduled_phase || '–'; ]]]"),
        plain_row("Next", BONE, "light/next", PHASE,
                  "[[[ " + JS_HHMM_OF + "const a = entity.attributes; if (!a.next_change) return '–'; "
                  "return (a.next_phase || '?') + ' · ' + hhmm(a.next_change); ]]]"),
        plain_row("Ramp", BUTTERSCOTCH, "light/ramp", PHASE,
                  "[[[ const a = entity.attributes; const f = a.ramp_fraction; "
                  "if (f == null || !a.ramp_direction) return '–'; "
                  "return a.ramp_direction + ' · ' + Math.round(f * 100) + ' %'; ]]]"),
    ], filler=SUNFLOWER, label_w=AQ_LABEL_W)
    # the graph takes the frame's width right of the values
    body = grid('"r g"', f"calc(clamp(140px, 11vw, 220px) + {AQ_LABEL_W}px + 16px) 1fr", "1fr",
                [at(rows, "r"), at(phases_card(), "g", margin="4px 0 8px 0")], gap="0 18px")
    control = panel("Phase control", SUNFLOWER, pillar=AQ_LABEL_W, content=body, bottom=False)

    def small(card):                  # smaller pill: text and number sized like the dosing buttons
        card["text"]["label"].update({"font_size": 17, "padding": {"right": 16, "bottom": 4}})
        card["text"]["code"]["padding"] = {"left": 16, "top": 4}
        return card

    def profile(label, levels, colour):
        card = mode_button(label, LIGHT_AUTO, colour, colour, f"light/profile/{label}")
        card["style"]["card"]["color"]["background"] = colour
        card.update({"tap_action": {"action": "call-service", "service": "aquarium_light_control.set_override",
                                    "service_data": {"levels": levels}}, "hold_action": {"action": "none"}})
        return small(card)

    def deco(i, colour):              # numbered pill without a function
        card = block(colour, None, lcars_code(f"light/controls/deco/{i}"))
        card["style"]["border"] = {"width": 0, "radius": 40}
        card["text"]["code"]["padding"] = {"left": 16, "top": 4}
        return card

    buttons = [small(mode_button(on_off_js("Automation", "Manual"), LIGHT_AUTO, ICE, SUNFLOWER, "light/auto")),
               *[profile(label, levels, colour) for label, levels, colour in LIGHT_PROFILES],
               *[deco(i, c) for i, c in enumerate([LILAC, PEACH, BONE, PERI, ALMOND])]]
    names = "abcdefgh"
    button_grid = grid('"a b c d" "e f g h"', "1fr 1fr 1fr 1fr", "1fr 1fr",
                       [at(c, n) for c, n in zip(buttons, names)], gap="8px 12px")
    def controls(bottom):
        return panel("Controls", ROSE, side="right", pillar=DECOR_PILLAR_W, top=False, bottom=bottom, caption=False,
                     content=with_decor_pillar(button_grid, "light/controls", [PEACH], filler=ROSE))

    # whatever height is left shows the device log; its bottom bar lines up with the Channels frame's.
    # Priority 3: on shorter screens (the tablet) it isn't rendered and Controls closes the S itself.
    log = panel("Device log", LILAC, pillar=DECOR_PILLAR_W, top=False, caption=False,
                content=with_decor_pillar(light_log_card(), "light/log", [PEACH, BONE], side="left", filler=LILAC))
    upper_h = f"calc({data_panel_height(5)} - {PANEL_CORNER}px)"
    to_controls = s_joint(("left", SUNFLOWER, AQ_LABEL_W), ("right", ROSE, DECOR_PILLAR_W), "Controls")
    double_s = s_chain([(control, upper_h), to_controls,
                        (controls(False), f"calc({data_panel_height(2)} - {2 * PANEL_CORNER}px)"),
                        s_joint(("right", ROSE, DECOR_PILLAR_W), ("left", LILAC, DECOR_PILLAR_W), "Device log"),
                        (log, "1fr")])
    single_s = s_chain([(control, upper_h), to_controls,
                        (controls(True), f"calc({data_panel_height(2)} - {PANEL_CORNER}px)"), None])
    left = tiered({3: double_s, 1: single_s})
    # pillar on the outer edge: its top bar continues Phase control's across the middle
    channels = panel("Channels", BUTTERSCOTCH, side="right", pillar=DECOR_PILLAR_W,
                     content=with_decor_pillar(transporter_card(), "light/channels", [PEACH, ALMOND, SUNFLOWER],
                                               side="right", filler=BUTTERSCOTCH))
    return grid('"l ch"', "1.2fr 1fr", "1fr", [at(left, "l"), at(channels, "ch")], gap="0 8px")


TANK_SEGMENTS = 20           # 25 ml each in a 500 ml bottle


def tank_card(fill, status, bottle, colour):
    """A bottle's fill level as a vertical segment stack with a scale and a pointer (ha/www/lcars-tank.js).
    Tap: more-info."""
    return {"type": "custom:lcars-tank", "entity": fill, "status": status, "capacity": bottle, "low": DOSE_LOW_ML,
            "segments": TANK_SEGMENTS, "colour": colour, "alarm": RED, "off": BAR_OFF, "text": PERI, "dim": GRAY,
            "blink": [_BLINK.randrange(8000, 24000, 500) for _ in range(TANK_SEGMENTS)], "off_fraction": 0.025,
            "flash": "#FFFFFF", "gap": 3, "font": "Antonio, sans-serif"}


def centre_text(value_js, entity, colour=PERI):
    """A value centred in its channel column."""
    card = value_text(value_js, entity, colour=colour)
    card["text"]["value"].update({"position": "center", "padding": {}})
    return card


def dosing_content():
    """Dosing station: a small frame per channel (thin pillar on alternating sides, open at the bottom, the
    channel's name in its top bar) with the schedule and refill buttons, the bottle as a tank, remaining
    supply, dose, next dose and weekdays; the row labels are the outer frame's pillar. Tap a Schedule pill
    to switch the schedule; hold Refill to mark the bottle refilled."""
    rows = [("sched", "Schedule", BONE, f"calc({DATA_ROW} * 1.3)"), ("tank", "Reservoir", PERI, "1fr"),
            ("left", "Remaining", BONE, DATA_ROW), ("dose", "Dose", BONE, DATA_ROW),
            ("next", "Next", BONE, DATA_ROW), ("days", "Weekdays", BONE, DATA_ROW)]
    n = len(DOSE_CHANNELS)
    # the label rows line up with the channel frames' bodies: the pieces above and below them are as high
    # as the frames' shoulders (less the grid gap, which the frames don't have)
    shoulder = f"{PANEL_CORNER - DATA_GAP}px"
    chans = " ".join(f"c{i}" for i in range(n))
    areas = ['"ph ' + chans + '"'] + [f'"p{key} {chans}"' for key, *_ in rows] + ['"pf ' + chans + '"']
    cards = [at(block(BLUEY), "ph")]    # runs into the top shoulder (join_top): no number
    cards += [at(block(colour, label, lcars_code(f"dosing/{key}"), align="center-right", size=17), f"p{key}")
              for key, label, colour, _ in rows]
    cards.append(at(block(BLUEY), "pf"))
    enabled = "(states['{sw}'] || {{}}).state === 'on' && a.configured_ml && (a.weekdays || []).length"
    for i, ((label, slug, bottle), colour) in enumerate(zip(DOSE_CHANNELS, DOSE_COLOURS)):
        status, fill, sw = f"sensor.dose_{slug}_status", f"number.dose_{slug}_fill_level", f"switch.dose_{slug}_schedule"
        on = enabled.format(sw=sw)
        # days until the bottle is empty at the scheduled rate, and the date
        remaining = centre_text(
            "[[[ const a = entity.attributes; const v = parseFloat(states['" + fill + "']?.state); "
            f"if (!({on}) || isNaN(v)) return '–'; "
            "const d = Math.floor(v / (a.configured_ml * a.weekdays.length / 7)); "
            "const e = new Date(Date.now() + d * 86400000); "
            "return d + ' d · ' + e.toLocaleDateString('en-GB', {day: '2-digit', month: '2-digit'}); ]]]",
            status, {"default": PERI, "Disabled": GRAY})
        dose = centre_text(f"[[[ const a = entity.attributes; if (!({on})) return 'Off'; "
                           "return a.configured_ml + ' ml · ' + a.time; ]]]", status,
                           {"default": PERI, "Disabled": GRAY, "Error": RED})
        nxt = centre_text("[[[ const a = entity.attributes; if (a.last_error) return 'Error'; "
                          f"if (!({on}) || !a.next_dose_at) return '–'; const d = new Date(a.next_dose_at); "
                          "const t0 = new Date(); t0.setHours(0, 0, 0, 0); const d0 = new Date(d); "
                          "d0.setHours(0, 0, 0, 0); const k = Math.round((d0 - t0) / 86400000); "
                          "const day = k === 0 ? 'today' : k === 1 ? 'tomorrow' : "
                          "d.toLocaleDateString('en-GB', {weekday: 'short'}); "
                          "return (entity.state === 'Idle' ? '' : entity.state + ' · ') + day; ]]]", status,
                          {"default": PERI, "Disabled": GRAY, "Error": RED})
        for card in (remaining, dose, nxt):
            card["triggers_update"] = [sw, fill]
        days = data_bar(status, colour, "days", 7, "left", attribute="weekdays",
                        labels=list("MTWTFSS"), ink=INK, label_colour=GRAY, font="Antonio, sans-serif")
        pill = mode_button(f"[[[ return entity.state === 'on' ? 'Active' : 'Off'; ]]]", sw, ICE, GRAY,
                           f"dosing/schedule/{slug}")
        # hold to mark the bottle refilled (fill level = bottle size), on purpose; tap: more-info
        refill = mode_button("Refill", fill, colour, colour, f"dosing/refill/{slug}")
        refill["style"]["card"]["color"]["background"] = colour
        refill.update({"tap_action": {"action": "more-info"},
                       "hold_action": {"action": "call-service", "service": "number.set_value",
                                       "target": {"entity_id": fill}, "service_data": {"value": bottle}}})
        for card in (pill, refill):      # half a column each: smaller text, the number above the label
            card["text"]["label"].update({"font_size": 17, "padding": {"right": 16, "bottom": 4}})
            card["text"]["code"]["padding"] = {"left": 16, "top": 4}
        buttons = grid('"s r"', "1fr 1fr", "1fr", [at(pill, "s"), at(refill, "r")], gap="0 8px")
        parts = {"sched": buttons, "tank": tank_card(fill, status, bottle, colour), "days": days,
                 "left": remaining, "dose": dose, "next": nxt}
        # open at the bottom: an empty row as high as the label pillar's bottom piece keeps the rows aligned
        # pillars alternate: Nitrate right, Phosphate left, ...; a spacer column on the open side keeps the
        # content off the neighbouring frame's
        right = i % 2 == 0
        body = grid(" ".join((f'"_ {key}"' if right else f'"{key} _"') for key, *_ in rows) + ' ". ."',
                    "14px 1fr" if right else "1fr 14px", " ".join([h for *_, h in rows] + [shoulder]),
                    [at(parts[key], key, **({"margin": "6px 0"} if key == "tank" else {})) for key, *_ in rows],
                    gap=f"{DATA_GAP}px 0")
        cards.append(at(panel(label, colour, content=body, side="right" if right else "left", bottom=False),
                        f"c{i}"))
    station = grid(" ".join(areas), f"{DATA_LABEL_W}px " + " ".join(["1fr"] * n),
                   " ".join([shoulder] + [h for *_, h in rows] + [shoulder]), cards, gap=f"{DATA_GAP}px 12px")
    frame_ = panel("Dosing station", BLUEY, pillar=DATA_LABEL_W, content=station, join_top=True)
    return grid('"s"', "1fr", "1fr", [at(frame_, "s")], gap="0")


POWER_GRID = [  # (label, entity, colour, W at the end of its bar, sign in the mirrored chart)
    ("Total", POWER, ORANGE, 350, 1), ("Pump", PUMP_POWER, ICE, 250, -1),
    ("Light", LIGHT_POWER, SUNFLOWER, 100, -1), ("CO² valve", CO2_POWER, LILAC, 2, -1),
]


def chart_height():
    """As high as the waste page's timeline plus the bottom shoulder, less where the page is too short."""
    n = len(BINS) + 1
    return f"minmax(0, calc({2 * PANEL_CORNER}px + {TL_HEAD} + {n} * {TL_ROW} + {TL_AXIS} + {(n + 2) * TL_GAP}px))"


def power_content():
    """Power grid (the block colours are the chart's legend) above the mirrored 24 h chart (priority 2:
    too flat to read below its viewport height, so not rendered there)."""
    grid_panel = aq_panel("Power grid", ALMOND, label_w=DATA_LABEL_W, rows=[
        (label, colour, lcars_code(f"power/{label}"),
         with_bar(value_text("{entity.state}", e), data_bar(e, colour, "level", BAR_SEGMENTS, "left", min=0, max=hi),
                  "left"))
        for label, e, colour, hi, _ in POWER_GRID])
    # no 1 W lines: on the tablet the chart is too short to keep them apart from the 10 W lines
    chart = mirrored_log_chart([(e, label, colour, sign) for label, e, colour, _, sign in POWER_GRID], ticks=(10, 100))
    trace = panel("Power visualization · 24 h", ORANGE, pillar=DECOR_PILLAR_W,
                  content=with_decor_pillar(chart, "power/chart", [ALMOND, PEACH, BONE], side="left", filler=ORANGE))
    return grid('"g" "t" "."', "1fr", f"{data_panel_height(4)} {chart_height()} 1fr",
                [at(grid_panel, "g"), at(shown_from(trace, 2), "t")], gap="clamp(12px, 2vh, 24px) 8px")


def osmosis_content():
    """Like the laundry page: the RO unit's frame on top, its power chart with range buttons below. Four
    rows, so the chart keeps the laundry chart's height on the tablet: auto-off and a pending firmware
    update go into the unit's value."""
    o = OSMO
    unit = aq_panel("RO unit", ICE, rows=[
        state_row("RO unit", ICE, "osmosis/unit", o["switch"],
                  "[[[ const fw = states['" + o["fw"] + "'] || {}; const up = fw.state === 'on' ? ' · FW ' + "
                  "fw.attributes.latest_version : ''; if (entity.state !== 'on') return 'Offline' + up; "
                  "const s = parseInt((states['" + o["countdown"] + "'] || {}).state); "
                  "return (s > 0 ? 'Online · off in ' + Math.ceil(s / 60) + ' min' : 'Online') + up; ]]]",
                  {"on": ICE}, {"off": GRAY}, toggle=True, triggers=[o["countdown"], o["fw"]]),
        plain_row("Mode", PEACH, "osmosis/mode", o["mode"], "[[[ return entity.state; ]]]"),
        ("Power", ALMOND, lcars_code("osmosis/power"),
         with_bar(value_text("{entity.state}", o["power"]),
                  data_bar(o["power"], ALMOND, "level", BAR_SEGMENTS, "left", min=0, max=40), "left")),
        plain_row("Energy", BONE, "osmosis/energy", o["energy"], "{entity.state}"),
    ])
    trace = panel("Power trace", ORANGE, pillar=DECOR_PILLAR_W, content=power_card(o["power"], "osmosis"))
    return grid('"u" "t" "."', "1fr", f"{data_panel_height(4)} {chart_height()} 1fr",
                [at(unit, "u"), at(shown_from(trace, 2), "t")], gap="clamp(12px, 2vh, 24px) 8px")


def english_labels(card):
    """Copy of a calendar card with its calendar labels in English."""
    card = json.loads(json.dumps(card))
    for c in card.get("calendars", []):
        c["label"] = CAL_LABELS.get(c.get("label"), c.get("label"))
    return card


def calendar_card(view, days=60, calendars=None):
    base = foreign_card("dashboard-termine", "kalender") if calendars is None else None
    card = english_labels(base) if base else {"type": "custom:global-calendar-card", "calendars": calendars}
    card.update({"default_view": view, "agenda_days": days})
    return skinned(card)


def waste_calendar_content():
    src = foreign_card("dashboard-muell", "kalender")
    card = skinned(english_labels(src))
    return framed("Collection calendar", PEACH, card)


def calendar_content():
    return framed("Stardate calendar", BLUEY, calendar_card("month_agenda"))


def agenda_content():
    def nxt_list(n):
        return column([("h", header("Next per calendar", ORANGE))] +
                      [("p", agenda_row(ALL_CALS, i, [ORANGE, PEACH, LILAC, PERI, ICE][i % 5], names=BIN_NAMES))
                       for i in range(n)])
    nxt = tiered({3: nxt_list(10), 2: nxt_list(9), 1: nxt_list(8)})      # as many rows as fit
    return cols(nxt, framed("Agenda · 60 days", BLUEY, calendar_card("agenda")), widths=["1fr", "1.4fr"])


VIEWS = [
    view("aquarium", "status", "LCARS Status", "aquarium-status", status_content(), "Systems status"),
    view("aquarium", "visual", "LCARS Visual", "aquarium-visual", visual_content(), "Visual sensor"),
    view("aquarium", "light", "LCARS Light", "aquarium-light", light_content(), "Illumination control"),
    view("aquarium", "dosing", "LCARS Dosing", "aquarium-dosing", dosing_content(), "Nutrient dosing"),
    view("aquarium", "power", "LCARS Power", "aquarium-power", power_content(), "Power distribution"),
    view("home", "home", "LCARS OPS", "ops", home_content(), "Habitat overview"),
    view("aquarium", "osmosis", "LCARS Osmosis", "aquarium-osmosis", osmosis_content(), "Water reclamation"),
    view("laundry", "laundry", "LCARS Laundry", "laundry", laundry_content(), "Laundry"),
    view("waste", "waste", "LCARS Waste", "waste", waste_content(), "Waste disposal"),
    view("waste", "waste-calendar", "LCARS Waste Calendar", "waste-calendar", waste_calendar_content(),
         "Waste schedule"),
    view("calendar", "calendar", "LCARS Calendar", "calendar", calendar_content(), "Stardate calendar"),
    view("calendar", "agenda", "LCARS Agenda", "calendar-agenda", agenda_content(), "Mission agenda"),
]

CONFIG = {"title": "LCARS",
          "kiosk_mode": {"hide_header": True, "hide_sidebar": True},
          "views": VIEWS}

# Click sounds. None = LCARdS' own scheme (lcards_default; its tap.mp3 is byte-identical to
# thelcars.com's beep1). Set to a dict to use the thelcars.com beeps stored in HA's media
# library (/media/lcars, deliberately not in this repo), e.g.:
#   CLICK_SOUNDS = {"card_tap": THELCARS.format(2), "card_hold": THELCARS.format(3)}
THELCARS = "media-source://media_source/local/lcars/thelcars_beep{}.mp3"
CLICK_SOUNDS = None

FR = re.compile(r"(?<![\w(,])(\d*\.?\d+)fr")


def finalize(node):
    """minmax(0,Nfr) for every fr track, and no theme min-height on LCARdS cards,
    so nothing inflates the grid beyond the viewport."""
    if isinstance(node, dict):
        lay = node.get("layout")
        if isinstance(lay, dict):
            for k in ("grid-template-columns", "grid-template-rows"):
                if k in lay:
                    lay[k] = FR.sub(r"minmax(0,\1fr)", lay[k])
        if node.get("type") in ("custom:lcards-button", "custom:lcards-elbow", "custom:lcards-slider",
                                "custom:lcards-data-grid", "custom:lcards-chart"):
            node.setdefault("min_height", 0)
        if CLICK_SOUNDS and node.get("type") in ("custom:lcards-button", "custom:lcards-slider") \
                and node.get("interactive", True) and node.get("tap_action", {}).get("action") != "none":
            node.setdefault("sounds", dict(CLICK_SOUNDS))
        for v in node.values():
            finalize(v)
    elif isinstance(node, list):
        for v in node:
            finalize(v)
    return node


if __name__ == "__main__":
    finalize(CONFIG)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(CONFIG, open(OUT, "w"), indent=1, ensure_ascii=False)
    print("views:", len(VIEWS), "bytes:", len(json.dumps(CONFIG)))
