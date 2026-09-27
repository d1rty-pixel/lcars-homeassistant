"""The page frame every view sits in (docs/DESIGN.md "Page frame"): header with readouts, title and the
section menu, sidebar with the section's views, mid bar with the titles and buttons of the content's top
row, foot bar with date/time and stardate, optionally a right side."""
from .engine import screen, sizes
from .engine.cards import at, block, elbow, frame_elbow, grid, segments, titled_bar
from .engine.codes import lcars_code
from .engine.palette import (ACTIVE, ALMOND, BLUEY, BUTTERSCOTCH, EARTH, HEADER_FAMILY, INK, LILAC, ORANGE, PEACH,
                             RED, ROSE, SIDEBAR_COLOURS, SUNFLOWER, VIOLET)
from .engine.screen import on_phone
from .engine.sizes import (CLOCK_W, CLOCK_W_PHONE, ELBOW_EXT, ELBOW_W, FOOT_FONT, FOOT_H, FOOT_T, FRAME_GAP,
                           FRAME_H, INNER_CURVE, MAIN_MARGIN, NAV_H, PANEL_GAP, PILLAR, STARDATE_W, BAR, Len,
                           code_font, fl, font, only_below, only_under)

CLASSIC_H = f"clamp({fl(42)}, 5.4dvh, 58px)"   # the link block on top of the header frame's pillar
WIDE_MIN = 1600      # header decoration that only fits on wide screens (not a 1280 px tablet)
WIDE_W = 290
SIDEBAR_LO = 0.6     # sidebar labels: 21 px -> 12.6 px on phones (the pillar is only 70 px wide there)
FOOT_NAV_FONT = 14   # the phone's section menu

CLOCK_JS = ("[[[ const d = new Date(), p = (n) => String(n).padStart(2, '0'); "
            "return d.toLocaleDateString('en-GB', {weekday: 'short'}) + ' ' + p(d.getDate()) + '/' "
            "+ p(d.getMonth() + 1) + '/' + d.getFullYear() + ' · ' + p(d.getHours()) + ':' + p(d.getMinutes()); ]]]")
CLOCK_JS_SHORT = ("const d = new Date(), p = (n) => String(n).padStart(2, '0'); "
                  "return d.toLocaleDateString('en-GB', {weekday: 'short'}) + ' ' + p(d.getHours()) + ':' "
                  "+ p(d.getMinutes()); ")
# Stardate in the TNG form (1000 units per year, one decimal ≈ 53 min), anchored so that 1987, the year TNG
# started with stardate 41xxx, is 41000-41999: 2026 runs from 80000 to 80999.9.
STARDATE_JS = ("[[[ const d = new Date(), y = d.getFullYear(), a = new Date(y, 0, 1), b = new Date(y + 1, 0, 1); "
               "const sd = 41000 + (y - 1987) * 1000 + 1000 * (d - a) / (b - a); "
               "return 'Stardate ' + (Math.floor(sd * 10) / 10).toFixed(1); ]]]")

# Segment bars (lcars-bar.js and the cards with segments) are hidden for everyone while this helper is off
# (?lcars_bars=off|on|toggle, see lcars-motion.js); `lcars setup` creates it.
BARS_HELPER = "input_boolean.lcars_bars"
BARS_VISIBLE = [{"condition": "state", "entity": BARS_HELPER, "state": "on"}]


def base_path(site):
    return f"/{site.url_path}/"


def dashboard_nav(site, active_section, foot=False, tail=None):
    """Section menu rendered as the segments of the header frame bar (like the sidebar blocks). foot=True:
    the phone variant (no numbers: the bar is only as thick as its text), in the foot bar or, with
    scrolling, in the phone's header (tail: the colour of the segment that runs the bar out)."""
    names, cards = [], []
    for sec in site.sections:
        active = sec.key == active_section.key
        path = None if active else base_path(site) + sec.views[0].path
        if foot:        # short labels, no arrow: the active one is marked by its colour
            card = block(ACTIVE if active else sec.colour, sec.short, None, path, align="center-right",
                         size=f"{FOOT_NAV_FONT}px")
        else:
            card = block(ACTIVE if active else sec.colour, sec.label + (" ◂" if active else ""),
                         lcars_code(f"section/{sec.key}"), path, size=18)
            card["text"]["code"]["font_size"] = code_font(10)
        names.append(sec.key)
        cards.append(at(card, sec.key))
    names.append("tail")                       # plain segment running the bar out (to the edge or the shoulder)
    cards.append(at(block(tail or (ORANGE if foot else LILAC)), "tail"))
    return grid('"' + " ".join(names) + '"', " ".join(["1fr"] * len(site.sections)) + (" 0.3fr" if foot else " 1.6fr"),
                "1fr", cards, gap="0 6px")


def sidebar(site, section, active_view):
    """The section's views as blocks (the active one near-white with "◂"), a filler, the motion switch."""
    cards, areas, rows = [], [], []
    for i, v in enumerate(section.views):
        colour = SIDEBAR_COLOURS[i % len(SIDEBAR_COLOURS)]
        is_active = v.key == active_view.key
        cards.append(at(block(ACTIVE if is_active else colour, v.label + (" ◂" if is_active else ""), v.code,
                              None if is_active else base_path(site) + v.path, size=font(21, SIDEBAR_LO)), v.key))
        areas.append(f'"{v.key}"')
        # 6 blocks and the motion switch fit an 800 px tablet; on the shortest phones they share what there is
        rows.append(f"minmax(0, clamp({fl(48)}, 8dvh, 110px))")
    cards.append(at(block(EARTH, None, lcars_code(f"sidebar-filler/{section.key}")), "filler"))
    cards.append(at(motion_switch(section, base_path(site) + active_view.path), "motion"))
    areas += ['"filler"', '"motion"']
    rows += ["1fr", f"clamp({Len(36, lo=0.7)}, 5dvh, 60px)"]
    return grid(" ".join(areas), "1fr", " ".join(rows), cards, gap="6px")


def motion_switch(section, here):
    """Per-device animation switch, handled by lcars-motion.js (state in localStorage): reloads the current
    view `here` with ?lcars_motion=toggle."""
    card = block(ALMOND, "[[[ let off = false; try { off = localStorage.getItem('lcars-motion') === 'off'; } "
                        "catch (e) {} return off ? 'Motion off' : 'Motion on'; ]]]",
                 lcars_code(f"motion/{section.key}"), size=font(16, SIDEBAR_LO))
    card["interactive"] = True
    card["tap_action"] = {"action": "navigate", "navigation_path": here + "?lcars_motion=toggle"}
    return card


def clock(site, phone=False):
    """Local date and time, re-rendered by the minute through sensor.time. phone=True: weekday and time
    only, and the alert's short text instead while there is one (the phone has no header title, where the
    alert sits otherwise)."""
    card = {"type": "custom:lcards-button", "entity": "sensor.time", "preset": "text-only", "show_icon": False,
            "interactive": False, "tap_action": {"action": "none"},
            "text": {"t": {"content": CLOCK_JS, "position": "center-left", "font_size": FOOT_T,
                           "color": ORANGE, "text_transform": "uppercase", "padding": {"left": 4}}}}
    if phone:
        alert = site.alert
        if alert:
            card.update({"entity": alert.entity, "triggers_update": ["sensor.time"], "interactive": True,
                         "tap_action": {"action": "more-info"}, "animations": alert.animations()})
            card["text"]["t"].update({"content": "[[[ " + alert.short_js() + CLOCK_JS_SHORT + "]]]",
                                      "color": alert.colours(ORANGE)})
        else:
            card["text"]["t"]["content"] = "[[[ " + CLOCK_JS_SHORT + "]]]"
    return card


def stardate_block():
    card = block(PEACH, STARDATE_JS, lcars_code("stardate"), align="center-right", size=FOOT_FONT)
    card["entity"] = "sensor.time"
    card["text"]["code"]["font_size"] = code_font(10)
    card["text"]["code"]["padding"] = {"left": 6, "top": 2}
    return card


def title_card(site, section, subtitle):
    """The page title (the section's title) with the view's subtitle; with an alert configured, the title
    turns into the alert's text and colour while it is active."""
    label = section.title.upper()
    card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False,
            "text": {"title": {"content": label, "position": "top-right", "font_size": font(60), "color": ORANGE,
                               "text_transform": "uppercase"},
                     "sub": {"content": subtitle, "position": "bottom-right", "font_size": font(20), "color": PEACH,
                             "text_transform": "uppercase"}},
            "tap_action": {"action": "none"}}
    alert = site.alert
    if alert:
        card = {"type": card["type"], "entity": alert.entity, **{k: v for k, v in card.items() if k != "type"}}
        card["text"]["title"].update({"content": alert.title_js(label), "color": alert.colours(ORANGE)})
        card["animations"] = alert.animations()
        card["tap_action"] = {"action": "more-info"}
    return card


def header_readouts(site, section, ctx):
    """Four readout slots next to the title. An entry (card, n) spans n slots; (card, "wide") gets a column
    that is 0 px below WIDE_MIN window width and WIDE_W above (pure CSS: layout cards have no media
    queries), the slot before it is widened a little."""
    slots, cards, widths = [], [], []
    for i, item in enumerate(r.header_item(ctx) for r in section.readouts):
        card, span = item if isinstance(item, tuple) else (item, 1)
        name = f"s{i}"
        n = 1 if span == "wide" else span
        slots += [name if card else "."] * n
        if span == "wide":
            widths[-1] = "1.6fr"
            widths.append(f"clamp(0px, calc((100vw - {Len.of(WIDE_MIN)}) * 100), {Len.of(WIDE_W)})")
        else:
            widths += ["1fr"] * n
        if card:
            extra = {"overflow": "hidden"} if span == "wide" else {}
            if card.get("type") == "custom:lcards-data-grid":
                extra["margin"] = "0 0 0 clamp(16px, 2vw, 40px)"
            cards.append(at(card, name, **extra))
    return slots, widths, cards


def top_bars(columns, pieces, right_w=None):
    """The mid bar's pieces over the top row's content columns. columns: the content grid's column widths
    ("1.1fr" or a Len; laid out with FRAME_GAP), pieces: [(number of columns it covers, card), ...] from
    left to right. Each piece ends where its last column ends, so bar and content split at the same x at
    any width. right_w: the frame's right side (view `right`), which shortens the bar.

    Coordinates: the content starts at PILLAR + MAIN_MARGIN and runs to the page's right edge; the bar
    starts after the left elbow (ELBOW_W + 6) and ends before the right shoulder. With the bar's width B as
    100 %, every column edge is a * B + b (b a Len), written as CSS calc()."""
    assert sum(n for n, _ in pieces) == len(columns)
    g, x0, b0 = FRAME_GAP, PILLAR + MAIN_MARGIN, ELBOW_W + 6
    shoulder = right_w + ELBOW_EXT + 6 if right_w else 0
    px = [Len.of(0) if isinstance(c, str) else c for c in columns]
    fr = [float(c[:-2]) if isinstance(c, str) else 0 for c in columns]
    free = b0 + shoulder - x0 - sum(px, Len()) - (len(columns) - 1) * g   # content width minus px and gaps = B + free

    def edge(k):          # right edge of column k in bar coordinates: (share of B, Len)
        f = sum(fr[:k + 1]) / sum(fr)
        return f, (x0 - b0) + sum(px[:k + 1], Len()) + k * g + free * f

    widths, start, k = [], (0.0, Len()), -1
    for i, (n, _) in enumerate(pieces):
        k += n
        if i == len(pieces) - 1:
            widths.append("1fr")
            break
        a, b = edge(k)
        widths.append(f"calc({a - start[0]:.5f} * 100% + {b - start[1]})")
        start = (a, b + g)
    names = [f"p{i}" for i in range(len(pieces))]
    return grid('"' + " ".join(names) + '"', " ".join(widths), "1fr",
                [at(card, n) for n, (_, card) in zip(names, pieces)], gap=f"0 {Len.of(g)}")


def mid_bar(view, ctx):
    """The mid bar's pieces from the view's `bar` entries: a titled bar per piece (with its buttons),
    aligned with the view's columns."""
    pieces = []
    for p in view.bar:
        middle = None
        if p.buttons is not None:
            buttons = p.buttons.card(ctx.at(key=f"{view.key}/bar"))
            if p.buttons_max:
                # the buttons keep their width, the bar runs on behind them to the shoulder
                buttons = grid('"c b"', f"minmax(0, {p.buttons_max}px) 1fr", "1fr",
                               [at(buttons, "c"), at(block(p.colour), "b")], gap="0 6px")
            middle = (buttons, "1fr")
        if not p.title and middle is None:       # a plain piece of bar (e.g. over a spine)
            pieces.append((p.span, block(p.colour)))
            continue
        pieces.append((p.span, titled_bar(p.title, p.colour, sizes.TOP_BAR_T, side=p.side, middle=middle)))
    return top_bars(view.columns, pieces, right_w=view.right.width if view.right else None)


def frame(site, section, view, content, ctx):
    """The page frame around `content` (a card): the list of the view's cards (top, mid, side/main or
    body, foot)."""
    nav_h = NAV_H
    right = view.right
    subtitle = f"{view.subtitle} · {view.code}"
    title = title_card(site, section, subtitle)
    slots, widths, cards = header_readouts(site, section, ctx)
    readouts = grid('"' + " ".join(slots) + ' t"', " ".join(widths + ["1.7fr"]), "1fr", [*cards, at(title, "t")],
                    gap="6px 16px")
    # the header frame's pillar starts with the section's link (e.g. to the original dashboard)
    link = section.link
    top_block = block(VIOLET, link.label if link else None, lcars_code(f"classic/{section.key}"),
                      link.url if link else None, size=18)
    top_cards = [
        at(top_block, "cl", margin=f"0 {ELBOW_W - PILLAR} {Len.of(PANEL_GAP + 2)} 0"),
        at(elbow("footer-left", LILAC, {"code": {"content": site.header_code, "position": "top-left",
                                                 "font_size": font(14), "color": INK,
                                                 "padding": {"left": 8, "top": 6}}},
                 bar_height=nav_h, outer_curve=PILLAR // 2), "elbow"),
        at(readouts, "data", margin="0 0 10px 0"),
        at(dashboard_nav(site, section), "nav"),
    ]
    if right:
        # a page closed on the right has a header closed on the right too, mirroring the link block and the
        # elbow on the left: a numbered block over a shoulder from the nav bar, as wide as the right side
        rw = right.width
        top_cards += [at(block(VIOLET, None, lcars_code(f"header-right/{section.key}")), "rc",
                         margin=f"0 0 {Len.of(PANEL_GAP + 2)} {ELBOW_EXT}"),
                      at(frame_elbow("footer-right", LILAC, rw, nav_h, rw // 2), "re")]
        top = grid('"cl data rc" "elbow data re" "elbow nav re"', f"{ELBOW_W} 1fr {rw + ELBOW_EXT}",
                   f"{CLASSIC_H} 1fr {nav_h}", top_cards, gap="0 6px")
    else:
        top = grid('"cl data" "elbow data" "elbow nav"', f"{ELBOW_W} 1fr", f"{CLASSIC_H} 1fr {nav_h}", top_cards,
                   gap="0 6px")
    mid_t = view.mid_t
    if not view.bar and right is None:
        mid = grid('"elbow bars"', f"{ELBOW_W} 1fr", "1fr", [
            at(elbow("header-left", PEACH), "elbow"),
            at(segments([(PEACH, 1), (ROSE, 4), (BLUEY, 2), (ORANGE, 1)], "top"), "bars"),
        ], gap="0 6px")
    else:
        bars = mid_bar(view, ctx) if view.bar else grid(
            '"a b c d"', "1fr 4fr 2fr 1fr", "1fr",
            [at(block(c), n) for c, n in ((PEACH, "a"), (ROSE, "b"), (BLUEY, "c"), (ORANGE, "d"))], gap="0 6px")
        h = mid_t + INNER_CURVE
        mcards = [at(elbow("header-left", PEACH, bar_height=mid_t, outer_curve=h), "e"), at(bars, "b")]
        areas, mwidths = '"e b" "e ."', f"{ELBOW_W} 1fr"
        if right:
            mcards.append(at(frame_elbow("header-right", right.colour, right.width, mid_t, h), "r"))
            areas, mwidths = '"e b r" "e . r"', f"{ELBOW_W} 1fr {right.width + ELBOW_EXT}"
        mid = grid(areas, mwidths, f"{Len.of(mid_t)} 1fr", mcards, gap="0 6px")
    side = sidebar(site, section, view)

    # the foot bar is as thick as its text and ends in the local date/time (in a gap of the bar, like a
    # panel caption) and the stardate block; the elbow keeps the page frame's outer and inner radius. On a
    # phone without scrolling (no header) the foot bar is the section menu and ends in the time (or the alert)
    def foot_bar(phone):
        fcards = []
        bars = grid('"a b c"', "3fr 1fr 5fr", "1fr", [at(block(c), n) for c, n in ((ALMOND, "a"), (BUTTERSCOTCH, "b"),
                                                                                  (ORANGE, "c"))], gap="0 6px")
        if phone:
            areas, fwidths = '"elbow . . ." "elbow bars cap clock"', f"{ELBOW_W} 1fr 14px {Len.of(CLOCK_W_PHONE)}"
            if screen.SCROLL == "off":     # the menu is in the foot bar (with scrolling: in the phone's header)
                bars = dashboard_nav(site, section, foot=True)
        else:
            areas, fwidths = '"elbow . . . ." "elbow bars cap clock sd"', f"{ELBOW_W} 1fr 14px {Len.of(CLOCK_W)} {Len.of(STARDATE_W)}"
            fcards.append(at(stardate_block(), "sd"))
        if right:       # the clock and stardate stay at the end of the bar, before the right shoulder
            fcards.append(at(frame_elbow("footer-right", right.foot, right.width, FOOT_T, FRAME_H), "r"))
            areas = areas.replace('."', '. r"').replace('clock"', 'clock r"').replace('sd"', 'sd r"')
            fwidths += f" {right.width + ELBOW_EXT}"
        return grid(areas, fwidths, f"1fr {Len.of(FOOT_T)}", fcards + [
            at(elbow("footer-left", ALMOND, bar_height=FOOT_T), "elbow"), at(bars, "bars"),
            at(block(ORANGE), "cap"), at(clock(site, phone), "clock")], gap="0 6px")

    foot = grid('"v"', "1fr", "1fr", [at(on_phone(foot_bar(False), False), "v"), at(on_phone(foot_bar(True)), "v")],
                gap="0")
    main_margin = f"4px 0 4px {MAIN_MARGIN}" if not right else f"0 0 0 {MAIN_MARGIN}"
    out = [at(on_phone(top, False), "top"), at(mid, "mid"), at(foot, "foot")]
    if screen.SCROLL == "off":
        return out + [at(side, "side"), at(content, "main", margin=main_margin)]
    # the phone keeps the header's menu bar (as thick as the foot bar), with its elbow and right shoulder
    phone_top = [at(elbow("footer-left", LILAC, bar_height=FOOT_T), "elbow"),
                 at(dashboard_nav(site, section, foot=True, tail=LILAC), "nav")]
    areas, pwidths = '"elbow ." "elbow nav"', f"{ELBOW_W} 1fr"
    if right:
        phone_top.append(at(frame_elbow("footer-right", LILAC, right.width, FOOT_T, FRAME_H), "re"))
        areas, pwidths = '"elbow . re" "elbow nav re"', f"{ELBOW_W} 1fr {right.width + ELBOW_EXT}"
    out.append(at(on_phone(grid(areas, pwidths, f"1fr {Len.of(FOOT_T)}", phone_top, gap="0 6px")), "top"))
    # sidebar and content scroll together (the frame around them stays): below SCROLL_MIN_H their row is as
    # much higher than the space they get as the viewport is lower than SCROLL_MIN_H, and higher still where
    # the content needs it (a min-height, e.g. lcars-flow.js' rows once they wrap)
    body = grid('"side main"', f"{PILLAR} 1fr",
                f"minmax(calc(100% + max(0px, {screen.SCROLL_MIN_H}px - 100dvh)), auto)",
                [at(side, "side"), at(content, "main", margin=main_margin)], gap="0", height="100%")
    return out + [at(body, "body")]


def view_config(site, section, view, content, ctx):
    """The Lovelace view: an LCARdS layout view of the frame's rows."""
    mid_h = view.mid_t + INNER_CURVE
    top_h = only_below(sizes.PHONE_H, "clamp(140px, 17dvh, 176px)")
    if screen.SCROLL == "auto":
        top_h = f"calc({top_h} + {only_under(sizes.PHONE_H + 0.02, FOOT_H)})"
    return {"title": view.title, "path": view.path, "type": "custom:lcards-layout-view", "theme": site.theme,
            # on a phone the header's row is 0 px high (its card isn't rendered there, see frame()), or as
            # high as the foot row with scrolling (only the menu bar)
            "layout": {"grid-template-columns": f"{PILLAR} 1fr",
                       "grid-template-rows": f"{top_h} {mid_h} 1fr {FOOT_H}",
                       "grid-template-areas": '"top top" "mid mid" '
                                              + ('"side main"' if screen.SCROLL == "off" else '"body body"')
                                              + ' "foot foot"',
                       # HA pads the view by the safe areas (notch, home indicator): the height leaves them out
                       "grid-gap": "6px 0", "padding": "8px",
                       "height": "calc(100dvh - 16px - var(--safe-area-inset-top, 0px) - var(--safe-area-inset-bottom, 0px))"},
            "cards": frame(site, section, view, content, ctx)}


def header_buttons(section, colours=HEADER_FAMILY[:4]):
    """2x2 LCARS pill buttons with auto-generated numbers and no function (header decoration)."""
    from .engine.cards import pill_shape
    names = ["a", "b", "c", "d"]
    cards = []
    for i, (n, c) in enumerate(zip(names, colours)):
        cards.append(at(pill_shape(block(c, lcars_code(f"header-button/{section.key}/{i}"), size=15)), n))
    return grid('"a b" "c d"', "1fr 1fr", "1fr 1fr", cards, gap="10px 12px")


__all__ = ["view_config", "frame", "top_bars", "header_buttons", "BARS_VISIBLE", "BARS_HELPER", "RED", "SUNFLOWER",
           "BAR", "FRAME_GAP"]
