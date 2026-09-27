"""Layout components: how frames, sections and columns are put together (docs/DESIGN.md "Reference
style")."""
from ..engine import sizes
from ..engine.cards import at, block, grid, label_block, panel_elbow, stack_areas, title_text
from ..engine.palette import INK, ORANGE_FAMILY
from ..engine.sizes import (DATA_GAP, DATA_ROW, DECOR_W, FRAME_GAP, Len, PANEL_CORNER, PANEL_GAP, PANEL_PILLAR, PANEL_T,
                            SECTION_GAP, css, data_panel_height, fl, title_width)
from .base import REQUIRED, Component, ConfigError, colour, component, height_spec, row_height, width


# ── Building blocks (functions) ─────────────────────────────────────────────────
def with_pillar(content, ctx, colours, side="right", filler=None, width=DECOR_W, row=None):
    """Content next to a pillar of LCARS blocks with numbers and no function. A filler piece in the frame
    colour runs into the bottom shoulder. row=<height>: blocks one data row high (part of a label column),
    the filler takes the rest."""
    names = [f"p{i}" for i in range(len(colours))] + (["pf"] if filler else [])
    blocks = [at(block(c, None, ctx.code("pillar", str(i))), n) for i, (c, n) in enumerate(zip(colours, names))]
    if filler:
        blocks.append(at(block(filler), "pf"))
    if row:
        rows = " ".join([row] * len(colours) + (["1fr"] if filler else []))
    else:
        rows = " ".join(["1fr"] * len(colours) + (["14px"] if filler else []))
    pillar = grid(" ".join(f'"{n}"' for n in names), "1fr", rows, blocks, gap=f"{Len.of(DATA_GAP if row else PANEL_GAP)}")
    areas, widths = ('"c p"', f"1fr {Len.of(width)}") if side == "right" else ('"p c"', f"{Len.of(width)} 1fr")
    return grid(areas, widths, "1fr", [at(content, "c", overflow="hidden"), at(pillar, "p")], gap="0 16px")


def panel(title, colour, content, *, side="left", pillar=None, top=True, bottom=True, overflow="hidden",
          join_top=False, caption=True):
    """Content in its own LCARS bracket: a pillar on `side` with shoulders (elbows) at the ends that have a
    bar. The top bar is interrupted by the title; with top=False the frame is open at the top and the title
    moves into the bottom bar (a caption; caption=False: no title, e.g. when it sits in a shared bar).
    bottom=False leaves the bottom open.

    pillar=<width>: the content brings its own pillar of that width as its column on `side` (e.g. label
    blocks); the shoulders widen to match. join_top: its first piece is in the frame colour and runs into
    the top shoulder without a gap (overlapping by 2 px, like fillers)."""
    right = side == "right"
    pw = pillar or PANEL_PILLAR
    corner = (pw + PANEL_CORNER - PANEL_T if pillar else PANEL_CORNER) + 8
    pad = "right" if right else "left"
    title_card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
                  "text": {"t": {"content": title, "position": f"center-{pad}", "font_size": PANEL_T,
                                 "color": colour, "text_transform": "uppercase", "padding": {pad: 10}}}}

    def line(edge, main):          # one row of the areas, edge column on the pillar side
        return f'"{main} {edge}"' if right else f'"{edge} {main}"'

    def bar(edge, titled):
        """Horizontal bar on the top/bottom edge of its row, optionally interrupted by the title."""
        seg = '"b t a"' if right else '"a t b"'
        # the title's track may shrink (clipping it) where the frame is narrower than its title (phones)
        tw = title_width(title, PANEL_T)
        widths = f"1fr minmax(0, {tw}) 14px" if right else f"14px minmax(0, {tw}) 1fr"
        parts = [at(block(colour), "a"), at(title_card, "t"), at(block(colour), "b")]
        if not titled:
            seg, widths, parts = '"b"', "1fr", [at(block(colour), "b")]
        blank = '"' + " ".join("." for _ in seg.strip('"').split()) + '"'
        areas_ = f"{seg} {blank}" if edge == "top" else f"{blank} {seg}"
        rows_ = f"{Len.of(PANEL_T)} 1fr" if edge == "top" else f"1fr {Len.of(PANEL_T)}"
        return grid(areas_, widths, rows_, parts, gap="0 6px")

    areas, rows, cards = [], [], []
    body_edge = "body" if pillar else "side"
    if top:
        areas.append(line("tl", "top"))
        rows.append(f"{Len.of(PANEL_CORNER)}")
        cards += [at(panel_elbow("header-right" if right else "header-left", colour, pw), "tl"),
                  at(bar("top", True), "top")]
    areas.append(line(body_edge, "body"))
    rows.append("1fr")
    if bottom:
        areas.append(line("bl", "bot"))
        rows.append(f"{Len.of(PANEL_CORNER)}")
        cards += [at(panel_elbow("footer-right" if right else "footer-left", colour, pw), "bl"),
                  at(bar("bottom", not top and caption), "bot")]
    if pillar:
        # the pillar's blocks keep the same small gap to the top shoulder as between each other; at the
        # bottom the pillar's filler piece runs into the shoulder: it overlaps it by 2 px, otherwise
        # fractional zoom levels (110 %) leave a hairline seam
        cards.append(at(content, "body", overflow=overflow,
                        margin=f"{Len.of(-2 if join_top else PANEL_GAP)} 0 {Len.of(-2 if bottom else 0)} 0"))
    else:
        pillar_card = (grid('". p"', f"1fr {Len.of(PANEL_PILLAR)}", "1fr", [at(block(colour), "p")], gap="0") if right else
                       grid('"p ."', f"{Len.of(PANEL_PILLAR)} 1fr", "1fr", [at(block(colour), "p")], gap="0"))
        cards += [at(pillar_card, "side"),
                  at(content, "body", overflow=overflow, margin="0 -18px 0 0" if right else "0 0 0 -18px")]
    return grid(" ".join(areas), f"1fr {Len.of(corner)}" if right else f"{Len.of(corner)} 1fr", " ".join(rows), cards,
                gap="0 6px")


def panel_min_w(title):
    """The narrowest a panel() without its own pillar can get with its whole title and a piece of bar after
    it (shoulder corner, the bar's first piece, the title, 14 px of bar, the gaps)."""
    return PANEL_CORNER + 8 + 6 + 14 + 6 + title_width(title, PANEL_T) + 6 + 14


def section_bar(title, colour, label_w, side="left"):
    """A section's top bar, growing out of the label column on `side`: a block as wide as the column, the
    title (as tall as the bar), the rest of the bar."""
    names, widths = ["p", "t", "b"], [f"{Len.of(label_w)}", f"{Len.of(title_width(title, PANEL_T))}", "1fr"]
    if side == "right":
        names, widths = names[::-1], widths[::-1]
    return grid('"' + " ".join(names) + '"', " ".join(widths), "1fr",
                [at(block(colour), "p"), at(title_text(title, colour, PANEL_T, side), "t"), at(block(colour), "b")],
                gap="0 6px")


def section(title, colour, body, label_w, side="left"):
    """A section of a label column: its bar, then its content."""
    return grid('"bar" "body"', "1fr", f"{Len.of(PANEL_T)} 1fr",
                [at(section_bar(title, colour, label_w, side), "bar"), at(body, "body")],
                gap=f"{Len.of(DATA_GAP)} 0")


FC_BOTTOM_T = sizes.BAR     # a closing bar's thickness; its shoulder has the facing shoulder's outer radius


def bottom_shoulder(colour, label_w, bar_t=FC_BOTTOM_T, side="left"):
    """A thin bottom bar with a shoulder into the label column on `side` (outer radius PANEL_CORNER, like
    the frame shoulder it faces), PANEL_CORNER high; the bar runs to the other edge of its cell."""
    shoulder = {"type": "custom:lcards-elbow", "interactive": False, "tap_action": {"action": "none"},
                "elbow": {"type": f"footer-{side}", "style": "simple",
                          "segment": {"bar_width": label_w, "bar_height": bar_t, "outer_curve": PANEL_CORNER,
                                      "inner_curve": PANEL_CORNER - PANEL_T, "color": {"default": colour}}}}
    bar = grid('". " "b"', "1fr", f"1fr {Len.of(bar_t)}", [at(block(colour), "b")], gap="0")
    corner = label_w + PANEL_CORNER - PANEL_T + 8
    if side == "right":
        return grid('"b e"', f"1fr {Len.of(corner)}", "1fr", [at(bar, "b"), at(shoulder, "e")], gap="0 6px")
    return grid('"e b"', f"{Len.of(corner)} 1fr", "1fr", [at(shoulder, "e"), at(bar, "b")], gap="0 6px")


def pad(card, side):
    """`card` kept 16 px (the label/value gap) off a spine on `side` ("left" or "right")."""
    return grid('"r"', "1fr", "1fr", [at(card, "r", margin="0 16px 0 0" if side == "right" else "0 0 0 16px")], gap="0")


def corner_w(pillar_w):
    """Width of an inner frame's shoulder cell with a pillar `pillar_w` wide (as panel() computes it)."""
    return pillar_w + PANEL_CORNER - PANEL_T + 8


def s_joint(upper, lower, title):
    """The shared bar where one frame runs into the next, making an S: `upper` and `lower` are (side,
    colour, pillar width) of the frame above (open at the bottom) and below (open at the top), their pillars
    on opposite sides. The upper frame's bottom shoulder and the lower frame's top shoulder sit on the same
    bar, which carries `title` next to the lower frame's shoulder."""
    (su, cu, pu), (sl, cl, pl) = upper, lower
    off = PANEL_CORNER - PANEL_T
    tw = title_width(title, PANEL_T)
    right = sl == "right"                                        # the title sits on the lower frame's side
    title_card = {"type": "custom:lcards-button", "preset": "text-only", "show_icon": False, "interactive": False,
                  "text": {"t": {"content": title, "position": "center-right" if right else "center-left",
                                 "font_size": PANEL_T, "color": cl, "text_transform": "uppercase",
                                 "padding": {"right" if right else "left": 10}}}}
    # the long part of the bar in the upper frame's colour, the short piece by the title in the lower one's
    left_c, right_c = (cu, cl) if right else (cl, cu)
    bar = grid('"a t b"', f"1fr {Len.of(tw)} 14px" if right else f"14px {Len.of(tw)} 1fr", "1fr",
               [at(block(left_c), "a"), at(title_card, "t"), at(block(right_c), "b")], gap="0 6px")
    # the upper shoulder's bar is at the bottom of its box, the lower one's at the top: offset to share it
    up = at(panel_elbow(f"footer-{su}", cu, pu), "u" if su == "left" else "l", margin=f"0 0 {Len.of(off)} 0")
    low = at(panel_elbow(f"header-{sl}", cl, pl), "l" if sl == "right" else "u", margin=f"{Len.of(off)} 0 0 0")
    lw, rw = (corner_w(pu), corner_w(pl)) if su == "left" else (corner_w(pl), corner_w(pu))
    return grid('"u m l"', f"{Len.of(lw)} 1fr {Len.of(rw)}", "1fr", [up, at(bar, "m", margin=f"{Len.of(off)} 0"), low],
                gap="0 6px")


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
            rows.append(f"{Len.of(2 * PANEL_CORNER - PANEL_T)}")
    return grid(" ".join(f'"r{i}"' for i in range(len(parts))), "1fr", " ".join(rows), cards, gap="0")


def item_height(comp, ctx):
    """The height a component takes in a stack: its `height` field, else what it needs, else None (fill)."""
    h = getattr(comp, "height_field", None)
    if h is not None:
        return h
    return comp.height(ctx)


def edge(comp, side, ctx):
    """The width of the pillar `comp` brings on `side` (label blocks, a decorative pillar), or None."""
    if comp.pillar is not None and comp.pillar.side == side:
        return width(comp.pillar.width_spec, ctx)
    f = getattr(comp, "edge", None)
    return f(side, ctx) if f else None


# ── Components ──────────────────────────────────────────────────────────────────
class _Sized(Component):
    """A layout component (parse_more(): its own field checks)."""

    def parse(self):
        self.parse_more()

    def parse_more(self):
        pass


@component("stack")
class Stack(_Sized):
    """Children one under the other, each as high as it needs (or its `height`), the last ones without a
    height sharing the rest; below children that all have a height the rest stays black.

    gap: section (the gap between sections of a label column), frame, none, or CSS."""
    fields = {"items": REQUIRED, "gap": "section"}

    def parse_more(self):
        self.kids = self.children(self.items, "items")
        self.sensitive = any(k.show_from or k.phone is False for k in self.kids)

    def _gap(self):
        return {"section": SECTION_GAP, "frame": f"{Len.of(FRAME_GAP)}", "none": "0px"}.get(self.gap, self.gap)

    def render(self, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        heights = [item_height(k, ctx) for k in kids]
        names = [f"i{i}" for i in range(len(kids))]
        cards = [at(k.card(ctx.at(key=ctx.key)), n) for k, n in zip(kids, names)]
        rows = [h or "1fr" for h in heights]
        if all(heights):
            names.append(".")
            rows.append("1fr")
        return grid(stack_areas(names), "1fr", " ".join(rows), cards, gap=f"{self._gap()} 0")

    def height(self, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        hs = [item_height(k, ctx) for k in kids]
        if not hs or not all(hs):
            return None
        return "calc(" + " + ".join(hs + [self._gap()] * (len(hs) - 1)) + ")"

    def min_height(self, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        parts = [item_height(k, ctx) or k.min_height(ctx) for k in kids]
        if not any(k.min_height(ctx) for k in kids) or not all(parts):
            return None
        return "calc(" + " + ".join(parts + [self._gap()] * (len(parts) - 1)) + ")"

    def edge(self, side, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        return edge(kids[0], side, ctx) if kids else None


@component("columns")
class Columns(_Sized):
    """Children side by side (widths: CSS grid tracks, default: the view's columns when the counts match,
    else equal). A child that needs less height than the row stands at the top, the rest stays black."""
    fields = {"items": REQUIRED, "widths": None, "gap": "frame"}

    def parse_more(self):
        self.kids = self.children(self.items, "items")
        self.sensitive = any(k.show_from or k.phone is False for k in self.kids)
        if self.widths is not None and len(self.widths) != len(self.kids):
            raise ConfigError(f"{self.where}.widths: {len(self.widths)} widths for {len(self.kids)} items")

    def track_widths(self, ctx):
        if self.widths:
            return [str(width(w, ctx, f"{self.where}.widths", number=fl)) for w in self.widths]
        if ctx.view is not None and len(ctx.view.columns) == len(self.kids):
            return [str(c) for c in ctx.view.columns]
        return ["1fr"] * len(self.kids)

    def render(self, ctx):
        names = [f"c{i}" for i in range(len(self.kids))]
        cards = []
        for k, n in zip(self.kids, names):
            if not k.visible(ctx):
                continue
            card = k.card(ctx)
            h = item_height(k, ctx)
            if h and h != "1fr":
                card = grid('"r" "."', "1fr", f"{h} 1fr", [at(card, "r")], gap="0")
            cards.append(at(card, n))
        gap = {"frame": f"{Len.of(FRAME_GAP)}", "none": "0px"}.get(self.gap, self.gap)
        return grid('"' + " ".join(names) + '"', " ".join(self.track_widths(ctx)), "1fr", cards, gap=f"0 {gap}")

    def height(self, ctx):
        return None

    def min_height(self, ctx):
        mins = [k.min_height(ctx) for k in self.kids if k.visible(ctx)]
        mins = [m for m in mins if m]
        return f"max({', '.join(mins)})" if len(mins) > 1 else (mins[0] if mins else None)

    def edge(self, side, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        if not kids:
            return None
        return edge(kids[0] if side == "left" else kids[-1], side, ctx)


@component("section")
class Section(_Sized):
    """A section of a label column: a bar growing out of the column with the title, then the content."""
    fields = {"title": REQUIRED, "colour": None, "side": "left", "content": REQUIRED}

    def parse_more(self):
        self.colour = colour(self.colour, f"{self.where}.colour", ORANGE_FAMILY[0])
        self.body = self.child(self.content, "content")

    def render(self, ctx):
        c = ctx.at(key=self.key or f"{ctx.key}/{self.title}")
        return section(self.title, self.colour, self.body.card(c), ctx.label_w, self.side)

    def height(self, ctx):
        h = item_height(self.body, ctx)
        return f"calc({Len.of(PANEL_T + DATA_GAP)} + {h})" if h and h != "1fr" else None

    def min_height(self, ctx):
        m = self.body.min_height(ctx)
        return f"calc({Len.of(PANEL_T)} + {m})" if m else None

    def edge(self, side, ctx):
        return ctx.label_w if side == self.side else None


@component("frame")
class Frame(_Sized):
    """Content in its own LCARS bracket (an inner frame): a pillar on `side` with shoulders, the title in
    the top bar. The pillar is the content's own where it brings one on that side (label blocks, a
    decorative pillar), else a plain one. top / bottom: false leaves that end open (the title then moves
    into the bottom bar; caption: false drops it). rows: its height in data rows (for chains and stacks).

    Where the screen is short (frames inside a split or pair, below its shoulders_from tier), a frame
    gives way to a flat section bar."""
    fields = {"title": REQUIRED, "colour": None, "side": "left", "content": REQUIRED, "top": True, "bottom": True,
              "caption": True, "join_top": False, "rows": None}

    def parse_more(self):
        self.colour = colour(self.colour, f"{self.where}.colour", ORANGE_FAMILY[0])
        self.body = self.child(self.content, "content")
        self.pad_side = None     # set by a pair: keep the content off the spine
        if self.rows is not None and not isinstance(self.rows, (int, float, dict)):
            raise ConfigError(f"{self.where}.rows: a number of data rows")
        from .base import is_tiered
        if is_tiered(self.rows):
            self.sensitive = True

    def pillar_width(self, ctx):
        return edge(self.body, self.side, ctx)

    def body_card(self, ctx):
        c = ctx.at(key=self.key or f"{ctx.key}/{self.title}")
        card = self.body.card(c)
        if self.pad_side:
            card = pad(card, self.pad_side)
        return card

    def render(self, ctx, top=None, bottom=None, caption=None):
        if ctx.flat:
            return section(self.title, self.colour, self.body_card(ctx), self.pillar_width(ctx) or ctx.label_w,
                           self.side)
        return panel(self.title, self.colour, self.body_card(ctx), side=self.side, pillar=self.pillar_width(ctx),
                     top=self.top if top is None else top, bottom=self.bottom if bottom is None else bottom,
                     caption=self.caption if caption is None else caption, join_top=self.join_top)

    def n_rows(self, ctx):
        from .base import tiered_value
        return tiered_value(self.rows, ctx.tier)

    def height(self, ctx):
        n = self.n_rows(ctx)
        if n is not None:
            return data_panel_height(n)
        h = item_height(self.body, ctx)
        if not h or h == "1fr":
            return None
        if ctx.flat:                    # a flat section bar and the gap under it
            return f"calc({Len.of(PANEL_T + DATA_GAP)} + {h})"
        # the top shoulder and the gap down to the first piece of pillar; the bottom shoulder
        ends = (PANEL_CORNER + PANEL_GAP if self.top else 0) + (PANEL_CORNER if self.bottom else 0)
        return f"calc({Len.of(ends)} + {h})"

    def edge(self, side, ctx):
        return self.pillar_width(ctx) or PANEL_PILLAR if side == self.side else None


@component("split")
class Split(_Sized):
    """A top part closed below by a thin bar with a shoulder, the bottom part (usually frames whose top
    shoulders face that bar) under it. Below the tier shoulders_from the shoulders give way: a section gap
    instead of the closing bar, flat section bars in the frames below. colour: the closing bar's (default:
    the top part's frame colour). A bottom part not shown leaves the top alone (closed below if it has a
    height of its own)."""
    fields = {"top": REQUIRED, "bottom": REQUIRED, "colour": None, "shoulders_from": 2, "side": "left"}

    def parse_more(self):
        self.top_c = self.child(self.top, "top")
        self.bottom_c = self.child(self.bottom, "bottom")
        self.colour = colour(self.colour, f"{self.where}.colour", None)
        self.sensitive = True

    def _colour(self):
        return self.colour or getattr(self.top_c, "colour", None) or ORANGE_FAMILY[0]

    def render(self, ctx):
        shoulders = ctx.tier >= self.shoulders_from
        inner = ctx.at(flat=not shoulders)
        top = self.top_c.card(inner)
        top_h = item_height(self.top_c, inner) or "1fr"
        cards = [at(top, "t")]
        close = bottom_shoulder(self._colour(), ctx.label_w, side=self.side)
        if not self.bottom_c.visible(ctx):
            if top_h == "1fr":
                return top
            return grid('"t" "." "fb" "."', "1fr", f"{top_h} {Len.of(PANEL_GAP)} {PANEL_CORNER} 1fr",
                        cards + [at(close, "fb")], gap="0")
        low_h = item_height(self.bottom_c, inner) or "1fr"
        cards.append(at(self.bottom_c.card(inner), "low"))
        tail = top_h != "1fr" and low_h != "1fr"
        if not shoulders:
            areas = '"t" "." "low"' + (' "."' if tail else "")
            return grid(areas, "1fr", f"{top_h} {SECTION_GAP} {low_h}" + (" 1fr" if tail else ""), cards, gap="0")
        cards.append(at(close, "fb"))
        return grid('"t" "." "fb" "." "low"' + (' "."' if tail else ""), "1fr",
                    f"{top_h} {Len.of(PANEL_GAP)} {Len.of(PANEL_CORNER)} {Len.of(FRAME_GAP)} {low_h}"
                    + (" 1fr" if tail else ""), cards, gap="0")

    def min_height(self, ctx):
        inner = ctx.at(flat=False)
        t = item_height(self.top_c, inner) or self.top_c.min_height(inner)
        b = item_height(self.bottom_c, inner) or self.bottom_c.min_height(inner)
        if not (self.top_c.min_height(inner) or self.bottom_c.min_height(inner)) or not (t and b):
            return None
        return f"calc({t} + {Len.of(PANEL_GAP + PANEL_CORNER + FRAME_GAP)} + {b})"

    def edge(self, side, ctx):
        return edge(self.top_c, side, ctx)


@component("pair")
class Pair(_Sized):
    """Two frames side by side that face outwards (docs/DESIGN.md): pillars on the outer edges, their top
    bars meeting in the middle as one line. Between them a spine: a column of numbered blocks without a
    function, one per data row (`spine`: their colours, in turn; `rows`: how many, default the larger
    frame's row count). The spine hangs from a piece of the shared line (`link` colour).

    top: {left, right, colour, spine} puts a row of two parts above the frames (e.g. two label columns),
    closed below by thin bars with shoulders on both sides; the spine then runs through both.
    close_left: the left frame is closed below, its bottom bar runs into the spine."""
    fields = {"left": REQUIRED, "right": REQUIRED, "spine": ["peach", "bone", "almond", "bone"], "rows": None,
              "link": "almond", "top": None, "close_left": False, "shoulders_from": 2}

    def parse_more(self):
        self.l = self.child(self.left, "left")
        self.r = self.child(self.right, "right")
        for f, side in ((self.l, "right"), (self.r, "left")):
            if isinstance(f, Frame):
                f.pad_side = side
                if "bottom" not in f.node:      # open below unless said otherwise
                    f.bottom = False
        self.spine_c = [colour(c, f"{self.where}.spine") for c in self.spine]
        self.link_c = colour(self.link, f"{self.where}.link")
        self.sensitive = True
        self.top_parts = None
        if self.top is not None:
            t = self.top
            if not isinstance(t, dict) or set(t) - {"left", "right", "colour", "spine"}:
                raise ConfigError(f"{self.where}.top: a mapping with left, right, colour, spine")
            self.top_parts = (self.child(t["left"], "top.left"), self.child(t["right"], "top.right"))
            self.top_colour = colour(t.get("colour", "orange"), f"{self.where}.top.colour")
            self.top_spine = [colour(c, f"{self.where}.top.spine") for c in t.get("spine", self.spine)]

    def n_rows(self, ctx):
        if self.rows:
            return int(self.rows)
        counts = [getattr(getattr(f, "body", None), "count", lambda c: 0)(ctx) for f in (self.l, self.r)]
        return max(counts) or 4

    def render(self, ctx):
        shoulders = ctx.tier >= self.shoulders_from
        inner = ctx.at(flat=not shoulders)
        if self.top_parts:
            return self._spine_page(ctx, inner, shoulders)
        return self._pair(ctx, inner, shoulders)[0]

    def _pair(self, ctx, inner, shoulders):
        n = self.n_rows(ctx)
        top = PANEL_CORNER + PANEL_GAP if shoulders else PANEL_T + DATA_GAP
        height = f"calc({Len.of(top)} + {n} * {DATA_ROW} + {Len.of(n * DATA_GAP + 8)})"
        blocks = [self.spine_c[i % len(self.spine_c)] for i in range(n)]
        column = grid('"b" "." ' + " ".join(f'"d{i}"' for i in range(n)) + ' "."', "1fr",
                      f"{Len.of(PANEL_T)} {Len.of(top - PANEL_T - DATA_GAP)} " + " ".join([DATA_ROW] * n) + " 1fr",
                      [at(block(self.link_c), "b")] + [at(block(c, None, ctx.code("spine", str(i))), f"d{i}")
                                                      for i, c in enumerate(blocks)], gap=f"{Len.of(DATA_GAP)} 0")
        card = grid('"l d r"', f"1fr {Len.of(DECOR_W)} 1fr", "1fr",
                    [at(self.l.card(inner), "l"), at(column, "d"), at(self.r.card(inner), "r")],
                    gap=f"0 {Len.of(FRAME_GAP)}")
        return card, height

    def height(self, ctx):
        if self.top_parts:
            return None
        shoulders = ctx.tier >= self.shoulders_from
        return self._pair(ctx, ctx.at(flat=not shoulders), shoulders)[1]

    def _spine_page(self, ctx, inner, shoulders):
        """One block column runs through the page between the left and right halves: blocks beside the top
        row's rows, a piece through the closing bars and the frames' top line (both end at it), blocks
        beside the frames' rows. With shoulders and close_left, the left frame is closed below: a bottom
        shoulder, a bar and a shoulder up into the column, which is its right side there; the right frame's
        pillar runs down to the foot bar."""
        g = DATA_GAP
        tl, tr = self.top_parts
        n_top = max(getattr(tl, "count", lambda c: 0)(ctx), getattr(tr, "count", lambda c: 0)(ctx)) or 4
        n_low = self.n_rows(ctx)
        lw = edge(self.l, "left", ctx) or ctx.label_w
        il_card = self.l.card(inner) if not self.close_left or not shoulders else \
            self.l.render(inner, bottom=False)
        wc_card = self.r.card(inner)
        if shoulders:
            head = PANEL_CORNER + PANEL_GAP            # lower frames: shoulder down to their first row
            between = f"{Len.of(PANEL_GAP)} {Len.of(PANEL_CORNER)} {Len.of(FRAME_GAP)}"
            link = f"calc({Len.of(PANEL_GAP + PANEL_CORNER + FRAME_GAP + head - 2 * g)})"
        else:
            head = PANEL_T + DATA_GAP
            between = SECTION_GAP
            link = f"calc({SECTION_GAP} + {Len.of(head - 2 * g)})"
        lower_h = f"calc({Len.of(head)} + {n_low} * {DATA_ROW} + {Len.of(n_low * DATA_GAP + 8)})"
        top_blocks = [at(block(c, None, ctx.code("spine", str(i))), f"t{i}")
                      for i, c in enumerate(self.top_spine[i % len(self.top_spine)] for i in range(n_top))]
        low_blocks = [at(block(c, None, ctx.code("spine", "low", str(i))), f"b{i}")
                      for i, c in enumerate(self.spine_c[i % len(self.spine_c)] for i in range(n_low))]
        closed = self.close_left and shoulders
        # below the lower rows: with a closed left frame a piece in its colour runs into its bottom-right
        # shoulder (no number), else the column just ends
        tail = [at(block(self.l.colour), "tail")] if closed else []
        column = grid(" ".join(f'"t{i}"' for i in range(n_top)) + ' "link" ' + " ".join(f'"b{i}"' for i in range(n_low))
                      + (' "tail"' if closed else ' "."'), "1fr",
                      " ".join([DATA_ROW] * n_top + [link] + [DATA_ROW] * n_low + ["1fr"]),
                      top_blocks + [at(block(self.link_c), "link")] + low_blocks + tail,
                      gap=f"{Len.of(g)} 0")   # the link merges into bars: no number
        cards = [at(pad(tl.card(ctx), "right"), "e"), at(pad(tr.card(ctx), "left"), "m"), at(wc_card, "wc")]
        if shoulders:
            rw = edge(tr, "right", ctx) or ctx.label_w
            cards += [at(bottom_shoulder(self.top_colour, lw), "fb"),
                      at(bottom_shoulder(self.top_colour, rw, side="right"), "fbr"),
                      # the left frame's filler and the column's tail overlap the bottom shoulders by 2 px
                      at(il_card, "il", margin="0 0 -2px 0"), at(column, "col", margin="0 0 -2px 0")]
            if closed:
                c = self.l.colour
                bar = grid('"." "b"', "1fr", f"1fr {Len.of(PANEL_T)}", [at(block(c), "b")], gap="0")
                closing = grid('"l b r"', f"{Len.of(corner_w(lw))} 1fr {Len.of(corner_w(DECOR_W))}", "1fr", [
                    at(panel_elbow("footer-left", c, lw), "l"), at(bar, "b"),
                    at(panel_elbow("footer-right", c, DECOR_W), "r")], gap="0 6px")
                cards.append(at(closing, "ilb"))
                areas = '"e col m" ". col ." "fb col fbr" ". col ." "il col wc" "ilb ilb wc" ". . wc"'
                rows = f"{sizes.rows_h(n_top)} {between} {lower_h} {Len.of(PANEL_CORNER)} 1fr"
            else:
                areas = '"e col m" ". col ." "fb col fbr" ". col ." "il col wc"'
                rows = f"{sizes.rows_h(n_top)} {between} 1fr"
        else:
            cards += [at(il_card, "il"), at(column, "col")]
            areas = '"e col m" ". col ." "il col wc"'
            rows = f"{sizes.rows_h(n_top)} {between} 1fr"      # the lower frames' pillars run down to the bottom
        return grid(areas, f"1fr {DECOR_W} 1fr", rows, cards, gap=f"0 {Len.of(FRAME_GAP)}")

    def edge(self, side, ctx):
        if self.top_parts:
            return edge(self.top_parts[0 if side == "left" else 1], side, ctx)
        return edge(self.l if side == "left" else self.r, side, ctx)


@component("chain")
class Chain(_Sized):
    """Frames joined into an S (or a double S): each frame's bottom shoulder and the next one's top shoulder
    sit on one shared bar that carries the next frame's title. Their pillars alternate sides (each frame's
    `side`). The first frame's title is in the mid bar. Every frame but the last is `rows` data rows high;
    the last takes the rest (open at the bottom, above the foot bar), or, with `rows`, is closed below and
    the rest stays black. A frame not shown (show_from) ends the chain at the one before it."""
    fields = {"items": REQUIRED}

    def parse_more(self):
        self.kids = self.children(self.items, "items")
        for k in self.kids:
            if not isinstance(k, Frame):
                raise ConfigError(f"{k.where}: a chain holds frames")
        for k in self.kids[:-1]:
            if k.rows is None:
                raise ConfigError(f"{k.where}: a frame in a chain (but the last) needs 'rows'")
        self.sensitive = True

    def render(self, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        parts = []
        for i, k in enumerate(kids):
            last = i == len(kids) - 1
            fixed = k.rows is not None
            bottom = last and fixed
            card = k.render(ctx, top=False, bottom=bottom, caption=False)
            if fixed:
                h = f"calc({data_panel_height(k.n_rows(ctx))} - {Len.of((1 if bottom else 2) * PANEL_CORNER)})"
            else:
                h = "1fr"
            if i:
                prev = kids[i - 1]
                parts.append(s_joint((prev.side, prev.colour, prev.pillar_width(ctx) or PANEL_PILLAR),
                                     (k.side, k.colour, k.pillar_width(ctx) or PANEL_PILLAR), k.title))
            parts.append((card, h))
        if kids and kids[-1].rows is not None:
            parts.append(None)
        return s_chain(parts)

    def edge(self, side, ctx):
        kids = [k for k in self.kids if k.visible(ctx)]
        return kids[0].pillar_width(ctx) if kids and kids[0].side == side else None


@component("matrix")
class Matrix(_Sized):
    """One inner frame per column (e.g. a channel of a device) whose cells line up with one label column of
    row names beside them, so the rows aren't labelled in every frame. The frames sit side by side while
    each gets its whole title, else they wrap into even rows (2 × 2 …), each row of frames with its own
    label column (lcars-flow.js, by the card's own width).

    rows: [{key, label, colour, height}] (height in data rows or fill; show_from per row)
    columns: [{title, colour, side, cells: {key: component}}] (side alternates right/left by default)
    head / foot: the label column's top piece (level with the frames' shoulders) and filler colours."""
    fields = {"rows": REQUIRED, "columns": REQUIRED, "head": "orange", "foot": "earth", "min_rows": 3}

    def parse_more(self):
        self.row_specs = []
        for i, r in enumerate(self.rows):
            w = f"{self.where}.rows[{i}]"
            if not isinstance(r, dict) or "key" not in r:
                raise ConfigError(f"{w}: a mapping with key, label, colour, height")
            self.row_specs.append({"key": r["key"], "label": r.get("label", r["key"]),
                                   "colour": colour(r.get("colour"), f"{w}.colour", ORANGE_FAMILY[i % 3]),
                                   "height": r.get("height", 1), "show_from": int(r.get("show_from", 0))})
        self.cols = []
        for i, c in enumerate(self.columns):
            w = f"{self.where}.columns[{i}]"
            cells = {k: build_cell(v, f"{w}.cells.{k}") for k, v in (c.get("cells") or {}).items()}
            self.cols.append({"title": c["title"], "colour": colour(c.get("colour"), f"{w}.colour", ORANGE_FAMILY[i % 3]),
                              "side": c.get("side", "right" if i % 2 == 0 else "left"), "cells": cells})
        self.head_c = colour(self.head, f"{self.where}.head")
        self.foot_c = colour(self.foot, f"{self.where}.foot")
        self.sensitive = any(r["show_from"] for r in self.row_specs)

    def render(self, ctx):
        rows = [r for r in self.row_specs if ctx.tier >= r["show_from"]]
        heights = {r["key"]: row_height(r["height"], f"{self.where}.rows.{r['key']}.height") for r in rows}
        # the label rows line up with the frames' bodies: the pieces above and below them are as high as the
        # frames' shoulders (less the grid gap, which the frames don't have)
        shoulder = f"{Len.of(PANEL_CORNER - DATA_GAP)}"
        hs = [shoulder] + [heights[r["key"]] for r in rows] + [shoulder]
        labels = grid(" ".join(['"ph"'] + [f'"p{r["key"]}"' for r in rows] + ['"pf"']), "1fr", " ".join(hs),
                      [at(block(self.head_c), "ph")]   # the column's top piece, level with the frames' shoulders
                      + [at(label_block(r["colour"], r["label"], ctx.code(r["key"])), f"p{r['key']}") for r in rows]
                      + [at(block(self.foot_c), "pf")], gap=f"{Len.of(DATA_GAP)} 0")
        cards = []
        for col in self.cols:
            right = col["side"] == "right"
            parts = {}
            for r in rows:
                cell = col["cells"].get(r["key"])
                if cell is None:
                    parts[r["key"]] = block(INK)
                else:
                    parts[r["key"]] = cell.card(ctx.at(key=f"{ctx.key}/{col['title']}/{r['key']}"))
            # open at the bottom: an empty row as high as the label column's bottom piece keeps the rows
            # aligned; a spacer column on the open side keeps the content off the neighbouring frame's
            body = grid(" ".join((f'"_ {r["key"]}"' if right else f'"{r["key"]} _"') for r in rows) + ' ". ."',
                        "14px 1fr" if right else "1fr 14px", " ".join([heights[r["key"]] for r in rows] + [shoulder]),
                        [at(parts[r["key"]], r["key"], **({"margin": "6px 0"} if heights[r["key"]] == "1fr" else {}))
                         for r in rows], gap=f"{Len.of(DATA_GAP)} 0")
            cards.append(panel(col["title"], col["colour"], body, side=col["side"], bottom=False))
        # a row of frames is at least as high as its fixed rows and min_rows data rows for the fill rows
        fixed = " + ".join(h for h in heights.values() if h != "1fr") or "0px"
        n_fill = sum(1 for h in heights.values() if h == "1fr")
        row_min = (f"calc({Len.of(2 * (PANEL_CORNER - DATA_GAP))} + {fixed} + {self.min_rows * n_fill} * {DATA_ROW} + "
                   f"{Len.of((len(rows) + 1) * DATA_GAP)})")
        return {"type": "custom:lcars-flow", "label": labels, "cards": cards, "label_w": css(ctx.label_w),
                "min_w": css(max((panel_min_w(c["title"]) for c in self.cols), key=lambda x: x.full())),
                "row_min": row_min, "gap": css(fl(12)), "row_gap": SECTION_GAP}


def build_cell(node, where):
    from .base import build
    return build(node, where)


@component("grid")
class Grid(_Sized):
    """A CSS grid for layouts the other components don't cover: areas (grid-template-areas), columns, rows,
    gap, and items, each a component with an `area`."""
    fields = {"areas": REQUIRED, "columns": "1fr", "rows": "1fr", "gap": "6px", "items": REQUIRED}

    def parse_more(self):
        self.kids = []
        for i, it in enumerate(self.items):
            if not isinstance(it, dict) or "area" not in it:
                raise ConfigError(f"{self.where}.items[{i}]: needs 'area'")
            node = {k: v for k, v in it.items() if k != "area"}
            self.kids.append((it["area"], self.child(node, f"items[{i}]")))
        self.sensitive = any(k.show_from or k.phone is False for _, k in self.kids)

    def render(self, ctx):
        areas = self.areas if isinstance(self.areas, str) else " ".join(f'"{a}"' for a in self.areas)
        cols = self.columns if isinstance(self.columns, str) else " ".join(str(width(c, ctx)) if not isinstance(c, str) else c for c in self.columns)
        rows = self.rows if isinstance(self.rows, str) else " ".join(height_spec(r, self.where) for r in self.rows)
        return grid(areas, cols, rows, [at(k.card(ctx), a) for a, k in self.kids if k.visible(ctx)], gap=self.gap)


@component("blank")
class Blank(_Sized):
    """Nothing: black space (e.g. to keep a grid area or a stack row empty)."""

    def render(self, ctx):
        return block(INK)


@component("card")
class Card(_Sized):
    """Any other Lovelace card, e.g. a picture or camera card, passed on as it is (with a black, borderless
    card style through UIX where it is installed)."""
    fields = {"card": REQUIRED, "plain": False}

    def render(self, ctx):
        card = dict(self.card_cfg)
        if not self.plain:
            card.setdefault("uix", {"style": "ha-card { background: #000 !important; border-radius: 0 !important; "
                                             "border: none !important; box-shadow: none !important; }"})
        return card

