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
    foot  : footer elbow, segmented bar
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ha_ws  # noqa: E402  (raw websocket client, token from ~/.config/homeassistant/token)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "build", "lcars_dashboard.json")
_FOREIGN = {}


def foreign_card(url_path, view_path, index=0):
    """First card(s) of a view on another dashboard, fetched live (used for the calendar cards)."""
    if url_path not in _FOREIGN:
        _FOREIGN[url_path] = ha_ws.Client().call({"type": "lovelace/config", "url_path": url_path})["result"]
    view = next(v for v in _FOREIGN[url_path]["views"] if v.get("path") == view_path)
    return view.get("cards", [])[index]

# ── Voyager-era palette (hex on purpose: stays put when LCARdS alert modes shift vars) ──
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
        text["label"] = {"show": True, "content": label, "position": align, "font_size": size,
                         "color": INK, "text_transform": "uppercase", "padding": {"right": 8, "bottom": 3}}
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


FRAME_H = 34        # height of the frame rows above and below the sidebar/content
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


def legend_readout(entity, label, colour):
    """Readout that doubles as a chart legend entry: colour swatch, label, value in the series colour."""
    swatch = {"type": "custom:lcards-button", "preset": "barrel", "interactive": False, "show_icon": False,
              "style": {"card": {"color": {"background": colour}}, "border": {"radius": 0}}}
    return grid('"sw txt"', "clamp(10px, 0.8vw, 16px) 1fr", "1fr",
                [at(swatch, "sw"), at(readout(entity, label, "{entity.state}", colour, label_color=DIM), "txt")],
                gap="0 clamp(12px, 1vw, 20px)")


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


def pill(entity, label, states, *, label_js=None, tap="more-info", triggers=None):
    card = row(entity, label, {k: v[2] for k, v in states.items()}, js_map(states), label_js=label_js, tap=tap)
    if triggers:
        card["triggers_update"] = triggers
    return card


def info(label, value_js, entity=None, color=PERI):
    return row(entity, label, {"default": color}, value_js, interactive=bool(entity))


def action_btn(label, color, action, *, hold=False, icon=None):
    """Flat filled command block, label bottom-right in black (LCARS button)."""
    card = {"type": "custom:lcards-button", "preset": "barrel", "show_icon": False,
            "style": {"card": {"color": {"background": color}}, "border": {"radius": 0}},
            "text": {"label": {"show": True, "content": label, "position": "bottom-right", "color": INK,
                               "font_size_percent": 38, "text_transform": "uppercase",
                               "padding": {"right": 12, "bottom": 4}}}}
    if hold:
        card["tap_action"] = {"action": "none"}
        card["hold_action"] = action
    else:
        card["tap_action"] = action
    return card


def column(items, filler=PERI):
    """Vertical stack of (kind, card): 'h' header / 'p' pill / 'r' readout rows sized to the viewport,
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
    ("aquarium", "Aquarium", "10-0001", ORANGE, "/lovelace/phishtank", [
        ("status", "Status", "01-1138", PEACH, "aquarium-status"),
        ("visual", "Visual", "02-4712", LILAC, "aquarium-visual"),
        ("light", "Light", "03-2256", SUNFLOWER, "aquarium-light"),
        ("dosing", "Dosing", "04-9031", BLUEY, "aquarium-dosing"),
        ("power", "Power", "05-6620", ALMOND, "aquarium-power"),
        ("osmosis", "Osmosis", "06-2240", ICE, "aquarium-osmosis"),
    ]),
    ("home", "OPS", "11-1701", ROSE, "/lovelace/home", [
        ("home", "OPS", "21-0001", ROSE, "ops"),
    ]),
    ("laundry", "Laundry", "13-5519", LILAC, "/lovelace/waschen", [
        ("laundry", "Laundry", "41-0001", LILAC, "laundry"),
    ]),
    ("waste", "Waste", "14-0815", PEACH, "/dashboard-muell/muell", [
        ("waste", "Overview", "51-0001", PEACH, "waste"),
        ("waste-calendar", "Calendar", "51-0002", BUTTERSCOTCH, "waste-calendar"),
    ]),
    ("calendar", "Calendar", "15-3301", BLUEY, "/dashboard-termine/kalender", [
        ("calendar", "Calendar", "61-0001", BLUEY, "calendar"),
        ("agenda", "Agenda", "61-0002", PERI, "calendar-agenda"),
    ]),
]


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
    _, _, _, _, classic, subviews = next(sec for sec in SECTIONS if sec[0] == section_key)
    items = [(k, label, code, colour, BASE + path) for k, label, code, colour, path in subviews]
    items.append(("classic", "Classic", "09-0074", VIOLET, classic))
    cards, areas, rows = [], [], []
    for key, label, code, colour, path in items:
        is_active = key == active_view
        cards.append(at(block(ORANGE if is_active else colour, label + (" ◂" if is_active else ""), code,
                              None if is_active else path), key))
        areas.append(f'"{key}"')
        rows.append("clamp(56px, 9vh, 110px)")
    cards.append(at(block(GRAY, None, "08-3390"), "filler"))
    areas.append('"filler"')
    rows.append("1fr")
    return grid(" ".join(areas), "1fr", " ".join(rows), cards, gap="6px")


pump_title_js = (
    "[[[ const a = entity.attributes; const s = entity.state; "
    "if (s === 'Critical') return 'RED ALERT · PUMP OFFLINE > ' + a.critical_minutes + ' MIN'; "
    "if (s === 'Warning' || s === 'Off') { const m = a.minutes_left != null ? a.minutes_left : a.critical_minutes; "
    "return 'PUMP OFFLINE · ' + m + ' MIN TO CRITICAL'; } "
    "return '%s'; ]]]"
)


def frame(section, active, content, subtitle):
    section_label = next(sec[1] for sec in SECTIONS if sec[0] == section).upper()
    title = {"type": "custom:lcards-button", "entity": PUMP, "preset": "text-only", "show_icon": False,
             "text": {"title": {"content": pump_title_js % section_label, "position": "top-right", "font_size": 60,
                                "color": {"Critical": RED, "Warning": SUNFLOWER, "Off": SUNFLOWER, "default": ORANGE},
                                "text_transform": "uppercase"},
                      "sub": {"content": subtitle, "position": "bottom-right", "font_size": 20, "color": PEACH,
                              "text_transform": "uppercase"}},
             "animations": [{"trigger": "on_entity_change", "entity": PUMP, "to_state": "Critical",
                             "check_on_load": True, "preset": "blink", "loop": True}],
             "tap_action": {"action": "more-info"}}
    readouts = grid('"p c l d t"', "1fr 1fr 1fr 1fr 1.7fr", "1fr", [
        *[at(card, area) for card, area in zip(section_readouts(section), ["p", "c", "l", "d"]) if card],
        at(title, "t"),
    ], gap="6px 16px")
    top = grid('"elbow data" "elbow nav"', f"{ELBOW_W}px 1fr", f"1fr {NAV_H}px", [
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
    foot = grid('"elbow bars"', f"{ELBOW_W}px 1fr", "1fr", [
        at(elbow("footer-left", BLUEY), "elbow"),
        at(segments([(BLUEY, 3), (LILAC, 1), (ORANGE, 5), (PEACH, 1)], "bottom"), "bars"),
    ], gap="0 6px")
    return [at(top, "top"), at(mid, "mid"), at(side, "side"), at(content, "main", margin="4px 0 4px 18px"),
            at(foot, "foot")]


def view(section, key, title, path, content, subtitle):
    return {"title": title, "path": path, "type": "custom:lcards-layout-view", "theme": THEME,
            "layout": {"grid-template-columns": f"{PILLAR}px 1fr",
                       "grid-template-rows": f"clamp(140px, 17vh, 176px) {FRAME_H}px 1fr {FRAME_H}px",
                       "grid-template-areas": '"top top" "mid mid" "side main" "foot foot"',
                       "grid-gap": "6px 0", "height": "calc(100dvh - 16px)", "padding": "8px"},
            "cards": frame(section, key, content, subtitle)}


# ── Views ───────────────────────────────────────────────────────────────────────
def status_content():
    modes = column([
        ("h", header("Modes", ORANGE)),
        ("p", pill("switch.aquarium_auto_mode", "Mode",
                   {"on": ("Auto", "mdi:autorenew", OK), "off": ("Manual", "mdi:hand-back-right", WARN)}, tap="toggle")),
        ("p", pill("switch.aquarium_maintenance_mode", "Maintenance",
                   {"on": ("Active", "mdi:wrench", CRIT), "off": ("Off", "mdi:wrench-outline", OFF)}, tap="toggle")),
        ("p", pill("switch.aquarium_feeding_mode", "Feeding",
                   {"on": ("Active", "mdi:food-drumstick", OK), "off": ("Off", "mdi:food-drumstick-off", OFF)},
                   label_js="[[[ const r = entity.attributes.resume_at; if (!r) return 'Feeding'; "
                            "return 'Feeding · until ' + new Date(r).toLocaleTimeString('en-GB', "
                            "{hour: '2-digit', minute: '2-digit'}); ]]]", tap="toggle")),
        ("p", pill("switch.aquarium_water_change_mode", "Water change",
                   {"on": ("Active", "mdi:water-sync", CRIT), "off": ("Off", "mdi:water-off-outline", OFF)},
                   tap="toggle")),
    ])
    equipment = column([
        ("h", header("Equipment", LILAC)),
        ("p", pill(PUMP, "Pump", PUMP_STATES,
                   label_js="[[[ const a = entity.attributes; "
                            "if (a.off_minutes != null) return 'Pump · off ' + a.off_minutes + ' min'; "
                            "return a.power != null ? 'Pump · ' + a.power + ' W' : 'Pump'; ]]]")),
        ("p", pill(HEATER, "Heater", {"on": ("On", "mdi:radiator", BUTTERSCOTCH), "off": ("Off", "mdi:radiator-off", OFF)})),
        ("p", pill(CO2, "CO²", CO2_STATES,
                   label_js="[[[ const a = entity.attributes; "
                            "if (a.reason === 'hysteresis_hold') return 'CO² · hold (' + a.schedule_reason + ')'; "
                            "return 'CO²'; ]]]")),
        ("p", pill(CO2_COUPLING, "CO² coupling",
                   {"on": ("Coupled", "mdi:link-variant", OK), "off": ("Manual", "mdi:link-variant-off", WARN)},
                   tap="toggle")),
    ])
    life = column([
        ("h", header("Illumination", SUNFLOWER)),
        ("p", pill(LIGHT_AUTO, "Automation",
                   {"on": ("Schedule", "mdi:calendar-clock", OK), "off": ("Manual", "mdi:hand-back-right", WARN)},
                   tap="toggle")),
        ("p", pill(PHASE, "Light", PHASE_STATES,
                   label_js="[[[ const a = entity.attributes; if (!a.next_change) return 'Light'; "
                            "const t = new Date(a.next_change).toLocaleTimeString('en-GB', "
                            "{hour: '2-digit', minute: '2-digit'}); return '→ ' + (a.next_phase || '?') + ' ' + t; ]]]")),
        ("h", header("Water change", ICE)),
        ("p", pill(WC, "Status",
                   {"Never": ("Never", "mdi:water-alert-outline", OFF), "OK": ("OK", "mdi:water-check", OK),
                    "Due": ("Due", "mdi:water-alert", WARN), "Overdue": ("Overdue", "mdi:water-remove", CRIT)},
                   label_js="[[[ const d = entity.attributes.days_since; if (d == null) return 'Status'; "
                            "return d + (d === 1 ? ' day' : ' days') + ' since'; ]]]")),
        ("p", info("Last change",
                   "[[[ const t = entity.attributes.last_water_change_at; if (!t) return '–'; const d = new Date(t); "
                   "return d.toLocaleDateString('en-GB', {day: '2-digit', month: '2-digit'}) + ' ' + "
                   "d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); ]]]", WC)),
        ("p", info("Next due",
                   "[[[ const t = entity.attributes.next_due_at; if (!t) return '–'; "
                   "return new Date(t + 'T00:00:00').toLocaleDateString('en-GB', "
                   "{day: '2-digit', month: '2-digit', year: 'numeric'}); ]]]", WC)),
    ])
    return grid('"a b c"', "1fr 1fr 1fr", "1fr", [at(modes, "a"), at(equipment, "b"), at(life, "c")], gap="0 18px")


def visual_content():
    cam = {"type": "custom:timed-camera-card", "entity": CAMERA, "still_interval": 30, "live_duration": 60,
           "show_name": False,
           "uix": {"style": "ha-card { background: #000 !important; border-radius: 0 !important; "
                            "border: none !important; box-shadow: none !important; }"}}
    side = column([
        ("h", header("Visual sensor 01", LILAC)),
        ("p", info("Feed", "[[[ return entity.state; ]]]", CAMERA, ICE)),
        ("p", pill(PUMP, "Circulation", PUMP_STATES)),
        ("p", pill(PHASE, "Illumination", PHASE_STATES)),
        ("p", info("Total power", "{entity.state}", POWER, ALMOND)),
    ])
    return grid('"cam side"', "2.6fr 1fr", "1fr", [at(cam, "cam", overflow="hidden"), at(side, "side")],
                gap="0 18px")


def light_content():
    state = column([
        ("h", header("Phase control", SUNFLOWER)),
        ("p", pill(LIGHT_AUTO, "Automation",
                   {"on": ("Schedule", "mdi:calendar-clock", OK), "off": ("Manual", "mdi:hand-back-right", WARN)},
                   tap="toggle")),
        ("p", pill(PHASE, "Current", PHASE_STATES)),
        ("p", info("Scheduled", "[[[ return entity.attributes.scheduled_phase || '–'; ]]]", PHASE, PERI)),
        ("p", info("Next", "[[[ const a = entity.attributes; if (!a.next_change) return '–'; "
                           "return (a.next_phase || '?') + ' · ' + new Date(a.next_change).toLocaleTimeString("
                           "'en-GB', {hour: '2-digit', minute: '2-digit'}); ]]]", PHASE, PERI)),
        ("p", info("Ramp", "[[[ const a = entity.attributes; const f = a.ramp_fraction; "
                           "if (f == null || !a.ramp_direction) return '–'; "
                           "return a.ramp_direction + ' ' + Math.round(f * 100) + ' %'; ]]]", PHASE, PERI)),
    ])

    def channel(name, colour):
        return {"type": "custom:lcards-slider", "entity": CHANNEL.format(name), "preset": "pills-basic",
                "control": {"min": 0, "max": 100, "step": 1},
                "style": {"track": {"orientation": "vertical",
                                    "segments": {"count": 18, "gap": 5, "shape": {"radius": 6},
                                                 "gradient": {"start": colour, "end": colour},
                                                 "appearance": {"unfilled": {"opacity": 0.18}}}}}}

    def channel_label(name, colour):
        """Titan-style value box under a slider: name small top-left, value large bottom-right."""
        return {"type": "custom:lcards-button", "entity": CHANNEL.format(name), "preset": "barrel",
                "show_icon": False,
                "style": {"card": {"color": {"background": tint(colour, 0.18)}},
                          "border": {"width": {"top": 3, "right": 0, "bottom": 0, "left": 0}, "color": colour,
                                     "radius": 0}},
                "text": {"name": {"show": True, "content": name.upper(), "position": "top-left", "font_size": 14, "color": DIM,
                                  "padding": {"left": 8, "top": 6}},
                         "value": {"content": "{entity.state}", "position": "bottom-right", "font_size": 26,
                                   "font_weight": "bold", "color": colour, "padding": {"right": 8, "bottom": 4}}},
                "tap_action": {"action": "more-info"}}

    green = "#88CC88"
    col = "clamp(96px, 6vw, 140px)"
    channels = grid('"h h h h" "r g b ." "lr lg lb ." "note note note note"', f"{col} {col} {col} 1fr",
                    "clamp(30px, 4.2vh, 54px) 1fr clamp(56px, 7vh, 80px) clamp(30px, 4vh, 48px)", [
        at(header("Channels", BUTTERSCOTCH), "h"),
        at(channel("red", RED), "r"), at(channel("green", green), "g"), at(channel("blue", BLUEY), "b"),
        at(channel_label("red", RED), "lr"), at(channel_label("green", green), "lg"),
        at(channel_label("blue", BLUEY), "lb"),
        at({"type": "custom:lcards-button", "preset": "text-only", "interactive": False,
            "text": {"n": {"content": "Setting levels enters manual override · Automation → Schedule resumes",
                           "position": "center-left", "font_size": 17, "color": LILAC,
                           "text_transform": "uppercase"}}}, "note"),
    ], gap="10px 30px")

    def profile(label, levels, colour, icon):
        return action_btn(label, colour, {"action": "call-service", "service": "aquarium_light_control.set_override",
                                          "service_data": {"levels": levels}}, icon=icon)

    profiles = column([
        ("h", header("Profiles", ROSE)),
        ("p", profile("Fire", {"red": 50, "green": 13, "blue": 0}, BUTTERSCOTCH, "mdi:fire")),
        ("p", profile("Chill", {"red": 0, "green": 13, "blue": 50}, ICE, "mdi:snowflake")),
        ("p", action_btn("Resume schedule", OK, {"action": "call-service", "service": "switch.turn_on",
                                                  "target": {"entity_id": LIGHT_AUTO}}, icon="mdi:calendar-clock")),
    ])
    return grid('"a b c"', "1fr 1.3fr 0.9fr", "1fr", [at(state, "a"), at(channels, "b"), at(profiles, "c")],
                gap="0 18px")


def dosing_content():
    cols = []
    for label, slug, bottle in DOSE_CHANNELS:
        status = f"sensor.dose_{slug}_status"
        fill = f"number.dose_{slug}_fill_level"
        level_colour = {"below:50": RED, "default": ICE}
        gauge = {"type": "custom:lcards-slider", "entity": fill, "preset": "pills-basic",
                 "control": {"min": 0, "max": bottle, "locked": True},
                 "style": {"track": {"orientation": "vertical",
                                     "segments": {"count": 20, "gap": 4, "shape": {"radius": 3},
                                                  "gradient": {"start": level_colour, "end": level_colour},
                                                  "appearance": {"unfilled": {"opacity": 0.15}}}}},
                 "view_layout_hint": None}
        gauge.pop("view_layout_hint")
        level_js = ("[[[ const v = parseFloat(entity.state); if (isNaN(v)) return '–'; "
                    f"return Math.round(v / {bottle} * 100) + ' %'; ]]]")
        readouts = grid('"f" "b" "p" "." "r"', "1fr",
                        "clamp(36px, 5vh, 60px) clamp(36px, 5vh, 60px) clamp(36px, 5vh, 60px) 1fr clamp(36px, 5vh, 60px)", [
            at(info("Fill", "{entity.state}", fill, ICE), "f"),
            at(info("Bottle", f"{bottle} ml", None, LILAC), "b"),
            at(row(fill, "Level", level_colour, level_js), "p"),
            at(action_btn("Hold · refilled", ALMOND,
                          {"action": "call-service", "service": "number.set_value",
                           "target": {"entity_id": fill}, "service_data": {"value": bottle}}, hold=True), "r"),
        ], gap="clamp(6px, 0.9vh, 12px)")
        lower = grid('"g x"', "clamp(56px, 4.5vw, 84px) 1fr", "1fr",
                     [at(gauge, "g"), at(readouts, "x")], gap="0 18px")
        items = [
            ("h", header(label, BLUEY)),
            ("r", info("Status", "[[[ return entity.state; ]]]", status, PERI)),
            ("r", pill(f"switch.dose_{slug}_schedule", "Schedule",
                       {"on": ("On", "", OK), "off": ("Off", "", OFF)}, tap="toggle")),
            ("r", info("Dose", "[[[ const a = entity.attributes; if (!a.configured_ml) return '–'; "
                               "return a.configured_ml + ' ml · ' + a.time; ]]]", status, LILAC)),
            ("r", info("Next", "[[[ const t = entity.attributes.next_dose_at; if (!t) return '–'; "
                               "const d = new Date(t); return d.toLocaleDateString('en-GB', {weekday: 'short'}) "
                               "+ ' ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); ]]]",
                       status, LILAC)),
            ("g", lower),
        ]
        names, rows, cards = [], [], []
        for i, (kind, card) in enumerate(items):
            names.append(f'"i{i}"')
            rows.append({"h": "clamp(30px, 4.2vh, 54px)", "g": "1fr"}.get(kind, "clamp(36px, 5vh, 60px)"))
            cards.append(at(card, f"i{i}"))
        cols.append(grid(" ".join(names), "1fr", " ".join(rows), cards, gap="clamp(6px, 0.9vh, 12px)"))
    names = ["a", "b", "c", "d"]
    return grid('"a b c d"', "1fr 1fr 1fr 1fr", "1fr", [at(c, n) for c, n in zip(cols, names)], gap="0 36px")


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


def power_content():
    chart = mirrored_log_chart([(POWER, "Total", ORANGE, 1),
                                (PUMP_POWER, "Pump", ICE, -1),
                                (CO2_POWER, "CO²", LILAC, -1)])
    chart = framed("Power visualization · 24 h", ALMOND, chart, overflow="hidden", cap="right")
    side = column([
        ("h", header("Power grid", ALMOND)),
        ("r", legend_readout(POWER, "Total", ORANGE)),
        ("r", legend_readout(PUMP_POWER, "Pump", ICE)),
        ("r", legend_readout(CO2_POWER, "CO² valve", LILAC)),
    ])
    return grid('"chart side"', "2.6fr 1fr", "1fr", [at(chart, "chart"), at(side, "side")], gap="0 18px")


# ── Shared helpers for the non-aquarium sections ─────────────────────────────────
WEATHER = "weather.forecast_home"
TODO = "todo.zuhause_2"
NINA = [f"binary_sensor.warning_home_{i}" for i in range(1, 6)]
OSMO = {"switch": "switch.osmoseanlage", "mode": "sensor.osmoseanlage_mode", "fw": "update.osmoseanlage_firmware",
        "energy": "sensor.osmoseanlage_energie", "power": "sensor.osmoseanlage_leistung",
        "countdown": "sensor.osmoseanlage_auto_off_countdown"}
WASH = {"switch": "switch.waschmaschine", "power": "sensor.waschmaschine_leistung",
        "energy": "sensor.waschmaschine_energie"}
WASH_PROTECT = [("Overheat", "binary_sensor.waschmaschine_uberhitzung"), ("Overload", "binary_sensor.waschmaschine_uberlast"),
                ("Overvoltage", "binary_sensor.waschmaschine_uberspannung"),
                ("Overcurrent", "binary_sensor.waschmaschine_uberstrom")]
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


def skinned(card):
    card = json.loads(json.dumps(card))
    card["uix"] = {"style": LCARS_SKIN}
    return card


def power_chart(series):
    """series: [(entity, name, colour)] -> 24 h stepline chart."""
    return {"type": "custom:lcards-chart", "chart_type": "line", "xaxis_type": "datetime",
            "data_sources": {f"s{i}": {"entity": e, "history": {"hours": 24}} for i, (e, _, _) in enumerate(series)},
            "sources": [{"datasource": f"s{i}", "buffer": "main", "name": n} for i, (_, n, _) in enumerate(series)],
            "series_names": [n for _, n, _ in series],
            "style": {"colors": {"series": [c for _, _, c in series]}, "stroke": {"curve": "stepline", "width": 3},
                      "legend": {"show": len(series) > 1}, "yaxis": {"decimals": 0},
                      "formatters": {"yaxis_label": "{value} W", "xaxis_label": "HH:mm"},
                      "chart_options": {"chart": FLUID}}}


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


def on_off(entity, label, on=("On", OK), off=("Off", OFF), tap="more-info", hold=None):
    card = pill(entity, label, {"on": (on[0], "", on[1]), "off": (off[0], "", off[1])}, tap=tap)
    if hold:
        card["hold_action"] = hold
    return card


# ── Header readouts per section ─────────────────────────────────────────────────
def section_readouts(section):
    if section == "aquarium":
        return [
            readout(POWER, "Total power", "{entity.state}"),
            readout(PUMP, "Circulation", js_map(PUMP_STATES),
                    {k: v[2] for k, v in PUMP_STATES.items()} | {"default": PEACH}),
            readout(PHASE, "Illumination", js_map(PHASE_STATES),
                    {k: v[2] for k, v in PHASE_STATES.items()} | {"default": PEACH}),
            readout(CO2, "CO² injection", js_map(CO2_STATES),
                    {k: v[2] for k, v in CO2_STATES.items()} | {"default": PEACH}),
        ]
    if section == "home":
        return [
            readout("sensor.time", "Local time", "{entity.state}"),
            readout(WEATHER, "Outside", "[[[ return entity.attributes.temperature + ' °C'; ]]]", ICE),
            readout(WEATHER, "Condition", js_map({k: (v, "", "") for k, v in WEATHER_NAMES.items()}), SUNFLOWER),
            readout(TODO, "Open tasks", "{entity.state}", LILAC),
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
            readout(WASH["power"], "Cycle", "[[[ return parseFloat(entity.state) > 3 ? 'Running' : 'Idle'; ]]]", ICE),
            readout(WASH["power"], "Power", "{entity.state}", ORANGE),
            readout(WASH["energy"], "Energy", "{entity.state}", LILAC),
            readout(WASH["switch"], "Supply", "[[[ return entity.state === 'on' ? 'On' : 'Off'; ]]]",
                    {"on": ICE, "default": GRAY}),
        ]
    if section == "waste":
        return [
            readout(NEXT_PICKUP, "Next pickup", JS_NEXT_BIN, ORANGE),
            readout(NEXT_PICKUP, "Date", js_de_date("entity.state", weekday=False), PEACH),
            None,                               # keep the slot free: the date is wide
            readout("sensor.time", "Local time", "{entity.state}"),
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
def home_content():
    w = WEATHER
    atmos = column([
        ("h", header("Atmosphere", ICE)),
        ("p", info("Sky", js_map({k: (v, "", "") for k, v in WEATHER_NAMES.items()}), w, SUNFLOWER)),
        ("p", info("Temperature", "[[[ return entity.attributes.temperature + ' °C'; ]]]", w, ICE)),
        ("p", info("Humidity", "[[[ return entity.attributes.humidity + ' %'; ]]]", w, PERI)),
        ("p", info("Pressure", "[[[ return Math.round(entity.attributes.pressure) + ' hPa'; ]]]", w, LILAC)),
        ("p", info("Wind", "[[[ const a = entity.attributes; return Math.round(a.wind_speed) + ' km/h · ' + "
                           "Math.round(a.wind_bearing) + '°'; ]]]", w, PERI)),
        ("p", info("Clouds", "[[[ return Math.round(entity.attributes.cloud_coverage) + ' %'; ]]]", w, LILAC)),
        ("h", header("Sol", SUNFLOWER)),
        ("p", info("Sunrise", "[[[ return new Date(entity.attributes.next_rising).toLocaleTimeString('en-GB', "
                              "{hour: '2-digit', minute: '2-digit'}); ]]]", "sun.sun", SUNFLOWER)),
        ("p", info("Sunset", "[[[ return new Date(entity.attributes.next_setting).toLocaleTimeString('en-GB', "
                             "{hour: '2-digit', minute: '2-digit'}); ]]]", "sun.sun", BUTTERSCOTCH)),
    ])
    alerts = [("h", header("Alerts · NINA", RED))]
    for i, e in enumerate(NINA, 1):
        alerts.append(("p", pill(e, f"Channel {i}", {"on": ("Warning", "", RED), "off": ("Clear", "", OFF)},
                                 label_js=f"[[[ return entity.state === 'on' ? (entity.attributes.headline || "
                                          f"'Warning {i}') : 'Channel {i}'; ]]]")))
    left = cols(atmos, column(alerts))
    todo = framed("Tasks · Home", LILAC, skinned({"type": "todo-list", "entity": TODO, "hide_completed": True,
                                                    "display_order": "none"}))
    radar = framed("Precipitation radar", BLUEY, skinned({
        "type": "iframe", "url": "https://radar.wo-cloud.com/mobile/rr/interactive?wrx=50.00,8.00&wrm=8&wry=50.00,8.00",
        "aspect_ratio": "56%", "hide_background": True}))
    forecast = framed("Forecast", ICE, skinned({"type": "weather-forecast", "entity": w, "show_current": False,
                                                "show_forecast": True, "forecast_type": "hourly",
                                                "forecast_slots": 12}))
    right = grid('"r" "f"', "1fr", "1fr clamp(150px, 20vh, 220px)", [at(radar, "r"), at(forecast, "f")], gap="14px")
    return cols(left, grid('"t" "."', "1fr", "1fr 0fr", [at(todo, "t")]), right, widths=["2fr", "1fr", "2fr"])


def osmosis_content():
    o = OSMO
    control = column([
        ("h", header("RO control", ICE)),
        ("p", on_off(o["switch"], "RO unit", on=("Online", OK), off=("Offline", OFF), tap="toggle")),
        ("p", info("Mode", "{entity.state}", o["mode"], PEACH)),
        ("p", info("Power", "{entity.state}", o["power"], ORANGE)),
        ("p", info("Energy", "{entity.state}", o["energy"], LILAC)),
        ("p", info("Auto-off", "[[[ const s = parseInt(entity.state); return s > 0 ? Math.ceil(s / 60) + ' min' : '–'; ]]]",
                   o["countdown"], PERI)),
        ("p", info("Firmware", "[[[ const a = entity.attributes; return a.installed_version + "
                               "(entity.state === 'on' ? ' → ' + a.latest_version : ' · current'); ]]]", o["fw"], PERI)),
    ])
    trace = framed("Power trace · 24 h", ORANGE, power_chart([(o["power"], "RO unit", ICE)]), overflow="hidden")
    return cols(control, trace, widths=["1fr", "2fr"])


def laundry_content():
    wsh = WASH
    unit = column([
        ("h", header("Laundry unit", LILAC)),
        ("p", info("Cycle", "[[[ return parseFloat(entity.state) > 3 ? 'Running' : 'Idle'; ]]]", wsh["power"], ICE)),
        ("p", info("Power", "{entity.state}", wsh["power"], ORANGE)),
        ("p", info("Energy", "{entity.state}", wsh["energy"], LILAC)),
        ("p", on_off(wsh["switch"], "Supply · hold to switch", tap="more-info",
                     hold={"action": "toggle"})),
        ("h", header("Protection", RED)),
        *[("p", on_off(e, label, on=("Alert", CRIT), off=("Nominal", OK))) for label, e in WASH_PROTECT],
    ])
    trace = framed("Power trace · 24 h", ORANGE, power_chart([(wsh["power"], "Washing machine", ORANGE)]),
                   overflow="hidden")
    return cols(unit, trace, widths=["1fr", "2fr"])


TIMELINE_DAYS = 28
TIMELINE_LABEL_W = 150   # label column = the timeline panel's left pillar
# Fixed row heights, so the frames hug their content instead of filling the viewport
TL_HEAD, TL_ROW, TL_AXIS, TL_GAP = "clamp(22px, 2.8vh, 30px)", "clamp(26px, 4vh, 40px)", "clamp(24px, 3vh, 32px)", 6
DATA_ROW, DATA_GAP = "clamp(30px, 4.4vh, 48px)", 6
# JS: `ds` = 'yyyy-mm-dd' for today + k days
JS_DAY = ("const t = new Date(); t.setHours(0,0,0,0); t.setDate(t.getDate() + %d); "
          "const ds = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' "
          "+ String(t.getDate()).padStart(2, '0'); const we = t.getDay() %% 6 === 0; ")


PANEL_T = 26        # bar thickness of a panel frame; the title sits in it, so it must fit the font
PANEL_PILLAR = 26   # width of its pillar
PANEL_CORNER = 54   # size of the shoulder (elbow card)


def panel_elbow(kind, colour, pillar=PANEL_PILLAR):
    return {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": pillar, "bar_height": PANEL_T, "outer_curve": PANEL_CORNER,
                                  "inner_curve": PANEL_CORNER - PANEL_T, "color": {"default": colour}}}}


def panel(title, colour, content, *, side="left", pillar=None, top=True, bottom=True, overflow="hidden"):
    """Content in its own LCARS bracket: a pillar on `side` with shoulders (elbows) at the ends that
    have a bar. The top bar is interrupted by the title; with top=False the frame is open at the top
    and the title moves into the bottom bar (a caption). bottom=False leaves the bottom open.

    pillar=<px> (left side only): the content brings its own pillar of that width as its first
    column (e.g. the timeline's label blocks); the shoulders widen to match."""
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
                  at(bar("bottom", not top), "bot")]
    if pillar:
        cards.append(at(content, "body", overflow=overflow))
    else:
        pillar_card = (grid('". p"', f"1fr {PANEL_PILLAR}px", "1fr", [at(block(colour), "p")], gap="0") if right else
                       grid('"p ."', f"{PANEL_PILLAR}px 1fr", "1fr", [at(block(colour), "p")], gap="0"))
        cards += [at(pillar_card, "side"),
                  at(content, "body", overflow=overflow, margin="0 -18px 0 0" if right else "0 0 0 -18px")]
    return grid(" ".join(areas), f"1fr {corner}px" if right else f"{corner}px 1fr", " ".join(rows), cards,
                gap="0 6px")


def text_row(label, value_js, entity=None, label_color=ORANGE, value_color=PERI):
    """Plain data line (label left, value right), no box: the quiet counterpart to row()."""
    card = row(entity, label, {"default": value_color}, value_js, interactive=bool(entity))
    card["style"] = {"card": {"color": {"background": "transparent"}}, "border": {"width": 0, "radius": 0}}
    # Sizes relative to the row height, larger than row()'s: these rows are short and have no box
    card["text"]["label"].update({"color": label_color, "padding": {"left": 0}, "font_size_percent": 40})
    card["text"]["value"].update({"color": value_color, "padding": {"right": 0}, "font_size_percent": 50})
    return card


def timeline_cell(entity, k, colour, hit):
    """One day of the collection timeline: filled in the bin colour on a pickup day, else a dim grid cell.
    hit: JS condition on `entity` and `ds`. JS templates in `style` are evaluated (see docs/NOTES.md)."""
    empty = "'" + rgba(PERI, 0.22) + "'" if k == 0 else "(we ? '" + rgba(PERI, 0.05) + "' : '" + rgba(PERI, 0.1) + "')"
    return {"type": "custom:lcards-button", "entity": entity, "preset": "barrel", "show_icon": False,
            "interactive": False, "tap_action": {"action": "none"}, "hold_action": {"action": "none"},
            "triggers_update": ["sensor.time"],
            "style": {"card": {"color": {"background": "[[[ " + JS_DAY % k + "return (" + hit + ") ? '" + colour +
                                                       "' : " + empty + "; ]]]"}},
                      "border": {"width": 0, "radius": 0}}}


def timeline_axis_cell(k, value_js, position):
    """Axis label for day k. Text colours can't be templated, so a weekday field and a weekend field
    share the spot and only one of them has content."""
    colour = ORANGE if k == 0 else PERI
    text = {name: {"content": "[[[ " + JS_DAY % k + "return (" + ("" if name == "wd" else "!") + "we) ? '' : "
                              + value_js + "; ]]]",
                   "position": position, "font_size": 15, "color": c, "text_transform": "uppercase"}
            for name, c in (("wd", colour), ("wkend", GRAY if k else colour))}
    return {"type": "custom:lcards-button", "entity": "sensor.time", "preset": "text-only", "show_icon": False,
            "interactive": False, "tap_action": {"action": "none"}, "text": text}


def collection_timeline():
    """Exterior-overview style grid: a label block per bin, one cell per day, day numbers underneath."""
    rows = [(label, e, colour, "entity.attributes[ds]") for label, e, colour in BINS]
    rows.append(("Hazmat", HAZMAT["date"], RED, "entity.state === ds"))
    days = [f"d{k}" for k in range(TIMELINE_DAYS)]
    areas = ['"lw ' + " ".join(f"w{k}" for k in range(TIMELINE_DAYS)) + '"']
    cards = [at(block(ORANGE, None, "51-0999"), "lw")]      # pillar piece between shoulder and first bin
    cards += [at(timeline_axis_cell(k, "t.toLocaleDateString('en-GB', {weekday: 'short'})", "bottom-center"), f"w{k}")
              for k in range(TIMELINE_DAYS)]
    for i, (label, entity, colour, hit) in enumerate(rows):
        areas.append('"' + " ".join([f"l{i}"] + [f"c{i}_{k}" for k in range(TIMELINE_DAYS)]) + '"')
        cards.append(at(block(colour, label, f"51-{1001 + i}", size=17), f"l{i}"))
        cards += [at(timeline_cell(entity, k, colour, hit), f"c{i}_{k}") for k in range(TIMELINE_DAYS)]
    areas.append('"lx ' + " ".join(days) + '"')
    cards.append(at(block(ORANGE, "Day", "51-1000", size=17), "lx"))
    cards += [at(timeline_axis_cell(k, "t.getDate()", "top-center"), d) for k, d in enumerate(days)]
    # Tracks spelled out: LCARdS counts tracks itself, treats repeat() as one and trims the areas to match
    return grid(" ".join(areas), f"{TIMELINE_LABEL_W}px " + " ".join(["1fr"] * TIMELINE_DAYS),
" ".join([TL_HEAD] + [TL_ROW] * len(rows) + [TL_AXIS]), cards, gap=f"{TL_GAP}px 4px")


def data_stack(cards):
    """Fixed-height rows of text_row()s (column() would stretch to fill)."""
    names = [f"r{i}" for i in range(len(cards))]
    return grid(" ".join(f'"{n}"' for n in names), "1fr", " ".join([DATA_ROW] * len(cards)),
                [at(c, n) for c, n in zip(cards, names)], gap=f"{DATA_GAP}px")


def data_panel_height(n):
    return f"calc({n} * {DATA_ROW} + {(n - 1) * DATA_GAP + 8}px + {PANEL_CORNER}px)"


def waste_content():
    timeline = panel(f"Collection timeline · {TIMELINE_DAYS} days", ORANGE, collection_timeline(),
                     pillar=TIMELINE_LABEL_W, bottom=False)
    # The two lower frames face each other: pillars meet in the middle, open at the top
    schedule = panel("Next per bin", PEACH, data_stack(
                     [text_row(label, js_de_date("entity.state"), e) for label, e, _ in BINS]),
                     side="right", top=False)
    hazmat = panel("Hazmat collection", RED, top=False, content=data_stack([
        text_row("Date", js_iso_date("entity.state"), HAZMAT["date"]),
        text_row("Window", "[[[ return String(entity.state).replace(/\\s*Uhr$/, ''); ]]]", HAZMAT["window"]),
        text_row("Location", "[[[ return String(entity.state).split(',')[0]; ]]]", HAZMAT["place"]),
        {"type": "custom:lcards-button", "preset": "text-only", "interactive": False,
         "text": {"n": {"content": "Four times a year · dates appear automatically", "position": "center-left",
                        "font_size": 16, "color": DIM, "text_transform": "uppercase"}}},
    ]))
    n_tl = len(BINS) + 1
    timeline_h = f"calc({PANEL_CORNER}px + {TL_HEAD} + {n_tl} * {TL_ROW} + {TL_AXIS} + {(n_tl + 1) * TL_GAP}px)"
    # Sized to content, not stretched to the viewport; what's left stays black
    return grid('"t t" "s h" ". ."', "1fr 1fr", f"{timeline_h} {data_panel_height(4)} 1fr",
                [at(timeline, "t"), at(schedule, "s"), at(hazmat, "h")], gap="clamp(12px, 2vh, 24px) 8px")


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
    nxt = column([("h", header("Next per calendar", ORANGE))] +
                 [("p", agenda_row(ALL_CALS, i, [ORANGE, PEACH, LILAC, PERI, ICE][i % 5], names=BIN_NAMES))
                  for i in range(10)])
    return cols(nxt, framed("Agenda · 60 days", BLUEY, calendar_card("agenda")), widths=["1fr", "1.4fr"])


VIEWS = [
    view("aquarium", "status", "LCARS Status", "aquarium-status", status_content(), "Systems status · 01-1138"),
    view("aquarium", "visual", "LCARS Visual", "aquarium-visual", visual_content(), "Visual sensor · 02-4712"),
    view("aquarium", "light", "LCARS Light", "aquarium-light", light_content(), "Illumination control · 03-2256"),
    view("aquarium", "dosing", "LCARS Dosing", "aquarium-dosing", dosing_content(), "Nutrient dosing · 04-9031"),
    view("aquarium", "power", "LCARS Power", "aquarium-power", power_content(), "Power distribution · 05-6620"),
    view("home", "home", "LCARS OPS", "ops", home_content(), "Operations · habitat overview · 21-0001"),
    view("aquarium", "osmosis", "LCARS Osmosis", "aquarium-osmosis", osmosis_content(), "Water reclamation · 06-2240"),
    view("laundry", "laundry", "LCARS Laundry", "laundry", laundry_content(), "Laundry · 41-0001"),
    view("waste", "waste", "LCARS Waste", "waste", waste_content(), "Waste disposal · 51-0001"),
    view("waste", "waste-calendar", "LCARS Waste Calendar", "waste-calendar", waste_calendar_content(),
         "Waste schedule · 51-0002"),
    view("calendar", "calendar", "LCARS Calendar", "calendar", calendar_content(), "Stardate calendar · 61-0001"),
    view("calendar", "agenda", "LCARS Agenda", "calendar-agenda", agenda_content(), "Mission agenda · 61-0002"),
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
