"""Primitive cards: LCARdS layout grids, blocks, pills, elbows, titles and values. Everything the frame
and the components are built from."""
import copy

from .palette import INK, PERI
from .sizes import (Len, PANEL_CORNER, PANEL_T, PILLAR, INNER_CURVE, FRAME_H, BAR, code_font, css, font,
                    title_width)


def at(card, area, **extra):
    """`card` placed in grid area `area` of its layout card (extra: margin, overflow, ... of view_layout)."""
    card = dict(card)
    card["view_layout"] = {"grid-area": area, **extra}
    return card


def grid(areas, columns, rows, cards, gap="6px", **layout):
    """An LCARdS layout card: a CSS grid with named areas."""
    return {"type": "custom:lcards-layout-card",
            "layout": {"grid-template-areas": areas, "grid-template-columns": columns,
                       "grid-template-rows": rows, "grid-gap": gap, **layout},
            "cards": cards}


def stack_areas(names):
    """grid-template-areas for one column of named areas."""
    return " ".join(f'"{n}"' for n in names)


def block(color, label=None, code=None, path=None, align="bottom-right", size=21):
    """A filled LCARS block: black label (bottom right by default), LCARS number top left, optionally a
    link (`path`)."""
    text = {}
    if label:
        pad = {"right": 8} if align.startswith("center") else {"right": 8, "bottom": 3}
        text["label"] = {"show": True, "content": label, "position": align,
                         "font_size": size if isinstance(size, str) else font(size),
                         "color": INK, "text_transform": "uppercase", "padding": pad}
    if code:
        text["code"] = {"content": code, "position": "top-left", "font_size": code_font(12), "color": INK,
                        "padding": {"left": 6, "top": 3}}
    card = {"type": "custom:lcards-button", "preset": "barrel", "show_icon": False,
            "interactive": bool(path), "style": {"card": {"color": {"background": color}}}, "text": text,
            "tap_action": {"action": "navigate", "navigation_path": path} if path else {"action": "none"}}
    return card


def label_block(colour, label, code, size=17):
    """A label block of a label column: label vertically centred and right-aligned, number top left."""
    return block(colour, label, code, align="center-right", size=size)


PILL_RADIUS = 40
PILL_INSET = (18, 5)   # px from the pill's side and from its top/bottom edge: clear of the rounded ends
PHONE_PILL_INSET = (10, 3)


def pill_shape(card):
    """Round a block's ends into an LCARS pill, with its label (bottom right) and number (top left) inset
    so the rounded ends never cover them. Every pill goes through this."""
    card["style"]["border"] = {"width": 0, "radius": PILL_RADIUS}
    x, y = PILL_INSET
    if "label" in card["text"]:
        card["text"]["label"]["padding"] = {"right": x, "bottom": y}
    if "code" in card["text"]:
        card["text"]["code"]["padding"] = {"left": x, "top": y}
    return card


def phone_pill(card):
    """The phone variant of a pill (use with by_screen()): no number and smaller insets, so its label fits a
    narrow pill. LCARdS takes text paddings in px only, so a pill can't shrink its insets by itself."""
    card = copy.deepcopy(card)
    card["text"].pop("code", None)
    if "label" in card["text"]:
        x, y = PHONE_PILL_INSET
        card["text"]["label"].update({"position": "center-right", "padding": {"right": x, "bottom": 0}})
    return card


def segments(colors_fr, position):
    """Segmented horizontal bar. position: 'top' or 'bottom' (bar sits on that edge)."""
    cols = " ".join(f"{fr}fr" for _, fr in colors_fr)
    names = [f"s{i}" for i in range(len(colors_fr))]
    row = '"' + " ".join(names) + '"'
    blank = '"' + " ".join("." for _ in names) + '"'
    areas = f"{row} {blank}" if position == "top" else f"{blank} {row}"
    rows = f"{Len.of(BAR)} 1fr" if position == "top" else f"1fr {Len.of(BAR)}"
    return grid(areas, cols, rows, [at(block(c), n) for (c, _), n in zip(colors_fr, names)], gap="0 6px")


def elbow(kind, color, text=None, bar_height=BAR, outer_curve=FRAME_H, width=PILLAR):
    """An elbow of the page frame. outer_curve defaults to the frame-row height: LCARdS would clamp 'auto'
    (PILLAR/2) to the card height anyway, and explicit values keep the mid and foot elbows identical."""
    card = {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": css(width), "bar_height": css(bar_height), "outer_curve": css(outer_curve),
                                  "inner_curve": css(INNER_CURVE), "color": {"default": color}}}}
    if text:
        card["text"] = text
    return card


def frame_elbow(kind, colour, width, bar_t, outer):
    """An elbow of the page frame in any colour and width (the right side's shoulders)."""
    return {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": css(width), "bar_height": css(bar_t), "outer_curve": css(outer),
                                  "inner_curve": css(INNER_CURVE), "color": {"default": colour}}}}


def panel_elbow(kind, colour, pillar):
    """A shoulder of an inner frame (bar PANEL_T thick, outer radius PANEL_CORNER)."""
    return {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
            "elbow": {"type": kind, "style": "simple",
                      "segment": {"bar_width": pillar, "bar_height": PANEL_T, "outer_curve": PANEL_CORNER,
                                  "inner_curve": PANEL_CORNER - PANEL_T, "color": {"default": colour}}}}


def text_card(content, position, size, colour, padding=None, **extra):
    """Plain text (an LCARdS text-only button without interaction)."""
    t = {"content": content, "position": position, "font_size": size, "color": colour, "text_transform": "uppercase"}
    if padding:
        t["padding"] = padding
    return {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
            "text": {"t": t}, **extra}


def readout(entity, label, value, colors=None, label_color=None, value_color=None):
    """A header readout: a small label over a large value (theme variable lcars-readout-size)."""
    from .palette import LILAC, PEACH
    return {"type": "custom:lcards-button", "entity": entity, "preset": "text-only", "show_icon": False,
            "text": {"lbl": {"content": label, "position": "top-left", "font_size": font(17),
                             "color": label_color or LILAC, "text_transform": "uppercase"},
                     "val": {"content": value, "position": "bottom-left", "font_size": "var(--lcars-readout-size)",
                             "font_weight": "bold",
                             "color": colors or value_color or PEACH, "text_transform": "uppercase"}},
            "tap_action": {"action": "more-info"}}


ANTONIO_CAP = 0.86     # cap height of Antonio in em (measured: 37 px at font size 43)


def title_text(title, colour, size, side="left"):
    """A title in a gap of a bar, font size = bar thickness. Placed by its baseline, half the space the cap
    height leaves above the bottom edge, so the capitals sit exactly centred in the bar (LCARdS' default
    "middle" centres the font's em box, which puts them against the top edge)."""
    return {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
            "text": {"t": {"content": title, "position": f"bottom-{side}", "baseline": "alphabetic",
                           "font_size": size, "color": colour, "text_transform": "uppercase",
                           "padding": {side: 10, "bottom": round(Len.of(size).full() * (1 - ANTONIO_CAP) / 2)}}}}


def titled_bar(title, colour, bar_t, side="left", middle=None):
    """A bar piece carrying `title` next to the shoulder on `side`; middle=(card, width): a card (e.g.
    buttons) between the title and the rest of the bar."""
    from .sizes import fl
    size = bar_t          # the title is always as tall as its bar
    names, widths = ["a", "t"], ["14px", f"{Len.of(title_width(title, size))}"]
    cards = [at(block(colour), "a"), at(title_text(title, colour, size, side), "t")]
    if middle:
        names.append("m")
        widths.append(middle[1])
        cards.append(at(middle[0], "m"))
    names.append("b")
    widths.append("1fr" if not middle else str(fl(40)))
    cards.append(at(block(colour), "b"))
    if side == "right":
        names, widths = names[::-1], widths[::-1]
    return grid('"' + " ".join(names) + '"', " ".join(widths), "1fr", cards, gap="0 6px")


def value_text(value_js, entity, align="left", colour=PERI):
    """Just the value of a data row, aligned towards its label block. colour may be a state map."""
    card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False,
            "tap_action": {"action": "more-info"},
            "text": {"value": {"content": value_js, "position": f"center-{align}", "color": colour,
                               "text_transform": "uppercase", "font_size": "var(--lcars-data-size)",
                               "font_weight": "bold", "padding": {align: 4}}}}
    if entity:
        card = {"type": card["type"], "entity": entity, **{k: v for k, v in card.items() if k != "type"}}
    return card

