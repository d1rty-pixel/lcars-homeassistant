"""Fluid sizes (docs/DESIGN.md "Responsive sizes").

One layout for every screen: frame and content sizes follow the viewport height. A size is given at its
full value (reached at REF_H and above, i.e. on tablets and desktops) and shrinks linearly with the height
below that, down to its minimum share at MIN_H (phones in landscape): S_MIN by default, much less for the
frame's pieces, less for fonts (F_MIN), so text stays readable.
"""

REF_H = 720          # viewport height from which every size is at its full value
MIN_H = 400          # viewport height at which every size has reached its minimum
S_MIN = 0.6          # default minimum share for sizes
F_MIN = 0.8          # smallest scale for fonts
LABEL_LO = 0.75      # label columns shrink less than the frame, so their labels keep fitting
CODE_LO = 0.67       # LCARS numbers in blocks shrink to 67 % (and are hidden on phones, see code_font())
PHONE_H = 520        # below this viewport height: the phone placement (see engine/screen.py; the cards in
                     # lcars/www use the same 520 px in their media queries)


def _num(x):
    return f"{round(x, 3):g}"


class Len:
    """A CSS length: px that scale with the viewport height (see REF_H), each down to its own minimum share
    `lo`, plus fixed px. Supports + and - with Len and numbers (px) and * / by numbers; str() gives the
    CSS. The framework keeps doing its arithmetic with these, and the result stays exact at every height."""

    def __init__(self, s=0.0, f=0.0, lo=S_MIN):
        self.terms = {lo: s} if s else {}     # lo -> scaled px
        self.f = f

    @staticmethod
    def of(x):
        return x if isinstance(x, Len) else Len(0, x)

    def _new(self, terms, f):
        n = Len(0, f)
        n.terms = {lo: v for lo, v in terms.items() if abs(v) > 1e-9}
        return n

    def __add__(self, o):
        o = Len.of(o)
        terms = dict(self.terms)
        for lo, v in o.terms.items():
            terms[lo] = terms.get(lo, 0) + v
        return self._new(terms, self.f + o.f)

    __radd__ = __add__

    def __sub__(self, o):
        return self + (-Len.of(o))

    def __rsub__(self, o):
        return Len.of(o) - self

    def __neg__(self):
        return self * -1

    def __mul__(self, k):
        return self._new({lo: v * k for lo, v in self.terms.items()}, self.f * k)

    __rmul__ = __mul__

    def __truediv__(self, k):
        return self * (1 / k)

    __floordiv__ = __truediv__

    @staticmethod
    def _clamp(s, lo):
        """s at REF_H and above, s * lo at MIN_H and below, linear in between: k * 100dvh + c."""
        a, b = sorted((s * lo, s))
        k = s * (1 - lo) / (REF_H - MIN_H)
        c = s * lo - k * MIN_H
        return f"clamp({_num(a)}px, calc({_num(k * 100)}dvh {'+' if c >= 0 else '-'} {_num(abs(c))}px), {_num(b)}px)"

    def __str__(self):
        parts = [self._clamp(v, lo) for lo, v in sorted(self.terms.items())]
        if not parts:
            return f"{_num(self.f)}px"
        if self.f:
            parts.append(f"{_num(self.f)}px")
        if len(parts) == 1:
            return parts[0]
        return "calc(" + " + ".join(parts).replace("+ -", "- ") + ")"

    __format__ = lambda self, spec: str(self)   # noqa: E731  (f-strings give the CSS)

    def full(self):
        """The value in px at full size."""
        return sum(self.terms.values()) + self.f


def fl(px):
    """A size that follows the viewport height (full value `px`)."""
    return Len(px)


def font(px, lo=F_MIN):
    """A font size that follows the viewport height, down to `lo` of `px`."""
    return str(Len(px, lo=lo))


def only_below(px, value):
    """CSS: `value` while the viewport is at least `px` high, 0 below (no media query needed)."""
    return f"min({value}, max(0px, calc((100dvh - {px}px) * 1000)))"


def only_under(px, value):
    """CSS: `value` while the viewport is lower than `px`, 0 from there on (the counterpart of only_below())."""
    return f"min({value}, max(0px, calc(({px}px - 100dvh) * 1000)))"


def code_font(px):
    """Font size of an LCARS number in a block: shrinking like a font, 0 on phones (the numbers are
    decoration, and there they would collide with the labels)."""
    return only_below(PHONE_H, font(px, CODE_LO))


def css(x):
    """A size for a card config: CSS for a Len, the number itself otherwise."""
    return str(x) if isinstance(x, Len) else x


def label_width(px):
    """A label column `px` wide at full size (label columns shrink less than the frame)."""
    return Len(px, lo=LABEL_LO)


# ── The frame's pieces shrink much more than the content on short screens (minimum shares at MIN_H) ──
PILLAR = Len(140, lo=0.5)       # width of the vertical frame bars / sidebar (70 px on phones)
BAR = 10                        # thickness of the horizontal frame bars (LCARdS elbows need at least 10)
ELBOW_EXT = Len(44, lo=0.35)    # how far an elbow reaches beyond its pillar
ELBOW_W = PILLAR + ELBOW_EXT
MAIN_MARGIN = Len(18, lo=0.4)   # between the sidebar and the content
INNER_CURVE = Len(24, lo=0.35)  # one inner radius for every corner around the content
FRAME_H = BAR + INNER_CURVE     # height of the frame row above the sidebar/content (the foot row: FOOT_H)

NAV_H = fl(43)                  # the header's nav bar, which is the section menu (every page)
TOP_BAR_T = Len(43, lo=0.47)    # the mid bar when it carries titles and buttons
FRAME_GAP = 6                   # between the top row's content columns, as between the bar pieces above them

FOOT_FONT = 20                          # text in the foot bar; the bar's thickness and the foot row follow it
FOOT_T = Len(FOOT_FONT + 6, lo=0.8)     # foot bar thickness = height of the clock and the stardate block
FOOT_H = FOOT_T + INNER_CURVE           # foot row: the bar plus the inner curve above it
CLOCK_W = int(22 * (FOOT_FONT + 6) * 0.37) + 24   # "FRI 25/09/2026 · 14:32" at bar height (Antonio digits ~0.37 em)
STARDATE_W = int(16 * FOOT_FONT * 0.44) + 80      # label plus room for the code on the left
CLOCK_W_PHONE = 90                      # the phone's foot bar: weekday and time, or the alert

# ── Content rows and frames (the reference style) ──
# Fixed row heights, so the frames hug their content instead of filling the viewport. Rows keep their
# full size from the tablet up, grow with taller screens and shrink (to 72-80 %) on phones.
TL_HEAD, TL_ROW, TL_AXIS, TL_GAP = (f"clamp({Len(22, lo=0.8)}, 2.8dvh, 30px)", f"clamp({Len(24, lo=0.8)}, 3.4dvh, 40px)",
                                    f"clamp({Len(24, lo=0.8)}, 3dvh, 32px)", 4)
DATA_ROW, DATA_GAP = f"clamp({Len(28, lo=0.72)}, 3.8dvh, 46px)", TL_GAP
LABEL_W = label_width(150)      # the default label column (e.g. "Temperature" next to its code)
DATA_LABEL_W = label_width(130)  # a narrower label column
DECOR_W = Len(90, lo=0.45)      # pillar of decorative blocks next to embedded content (radar, camera)
SECTION_GAP = f"clamp({fl(10)}, 1.6dvh, 18px)"     # between the sections of a label column

PANEL_T = fl(26)                # bar thickness of an inner frame; the title sits in it, so it must fit the font
PANEL_PILLAR = Len(26, lo=0.45)  # width of its plain pillar
PANEL_CORNER = Len(46, lo=0.5)  # size of its shoulder (elbow card)
PANEL_GAP = TL_GAP              # gap between the pieces of a pillar

VALUE_W = f"clamp({fl(190)}, 15vw, 290px)"   # value column next to a segment bar


def rows_h(n):
    """Height of n data rows of a label column."""
    return f"calc({n} * {DATA_ROW} + {Len.of((n - 1) * DATA_GAP)})"


def data_panel_height(n):
    """Height of a frame with top and bottom bars around n data rows: rows, the gaps between them and to
    both shoulders, and a short filler piece of pillar."""
    return f"calc({n} * {DATA_ROW} + {Len.of((n + 1) * DATA_GAP + 12)} + {Len.of(2 * PANEL_CORNER)})"


def timeline_height(n):
    """Height of a day timeline (lcars-day-grid) with n series: head, rows, axis and their gaps."""
    return f"calc({TL_HEAD} + {n} * {TL_ROW} + {TL_AXIS} + {Len.of((n + 1) * TL_GAP)})"


def chart_height(n):
    """As high as a timeline of n series plus a bottom shoulder (charts next to timelines line up), less
    where the page is too short."""
    return f"minmax(0, calc({Len.of(2 * PANEL_CORNER)} + {TL_HEAD} + {n} * {TL_ROW} + {TL_AXIS} + {Len.of((n + 2) * TL_GAP)}))"


SHRINKS = "minmax(0, "


def total(parts, shrink=True):
    """The sum of heights as one CSS value. A part that may shrink (minmax(0, X), e.g. chart_height) can't
    go into calc(), which would make the whole value invalid: its X is added, and with `shrink` the sum
    may shrink too (a grid track); without it (for a minimum) it counts in full."""
    flex = False
    out = []
    for p in map(str, parts):
        if p.startswith(SHRINKS) and p.endswith(")"):
            p, flex = p[len(SHRINKS):-1], True
        out.append(p)
    s = f"calc({' + '.join(out)})"
    return f"{SHRINKS}{s})" if flex and shrink else s


# Advance widths of Antonio Regular (em) for what titles use, read from the font (Google Fonts, v22); titles
# are uppercase, so lowercase letters count as capitals. Anything else counts as 0.42 em.
ANTONIO_EM = {
    " ": 0.241, "A": 0.443, "B": 0.448, "C": 0.448, "D": 0.466, "E": 0.369, "F": 0.365, "G": 0.458, "H": 0.48,
    "I": 0.242, "J": 0.428, "K": 0.444, "L": 0.339, "M": 0.633, "N": 0.495, "O": 0.461, "P": 0.437, "Q": 0.461,
    "R": 0.458, "S": 0.404, "T": 0.307, "U": 0.466, "V": 0.431, "W": 0.654, "X": 0.389, "Y": 0.404, "Z": 0.337,
    "Ä": 0.443, "Ö": 0.461, "Ü": 0.466, **{d: 0.417 for d in "0123456789"}, "·": 0.234, ".": 0.26, ",": 0.226,
    ":": 0.239, ";": 0.274, "-": 0.34, "–": 0.369, "—": 0.563, "/": 0.356, "(": 0.273, ")": 0.273, "&": 0.468,
    "+": 0.332, "%": 1.063, "°": 0.447, "²": 0.413, "'": 0.202, '"': 0.363, "!": 0.258, "?": 0.417, "#": 0.417,
}
TITLE_PAD = 10       # a title's padding towards its shoulder (title_text()); the same room is left after it


def text_em(text):
    """Width of `text` in Antonio capitals, in em."""
    return sum(ANTONIO_EM.get(ch, 0.42) for ch in str(text).upper())


def title_width(title, size):
    """Width of a title's cell in a bar at font size `size`: the text plus TITLE_PAD on both sides, so the
    gap after it matches the one before it."""
    return size * text_em(title) + 2 * TITLE_PAD
