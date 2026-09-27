"""The Voyager-era LCARS palette (hex on purpose: the colours stay put when LCARdS alert modes shift the
theme variables) and the colour names a configuration may use."""

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
GREEN = "#88CC88"
EARTH = "#CC9966"    # muted orange (Voyager "flat dark earth") for large fillers in the orange family
BONE = "#EEE4CC"     # light LCARS block (the "LCARS" / "LCARS VERSION" blocks of the database screens)
INK = "#000000"
WHITE = "#FFFFFF"
DIM = "#B4B4CC"      # dimmed lavender: chart axes, secondary text
BRIGHT = "#DFE1E8"   # the brightest step of the number columns' colour waterfall

# Semantic state colours: ice = OK/running, sunflower = warning/manual, red = critical, grey = off
OK, WARN, CRIT, OFF, INFO = ICE, SUNFLOWER, RED, GRAY, VIOLET

# One colour family per frame (docs/DESIGN.md): the header frame in blues/lilacs, the page frame below it
# (sidebar, mid bar, foot bar, right side) in oranges. The header's nav bar and the mid bar are where the
# two frames meet, so colours may mix there. The active item (nav, sidebar, categories, devices) is light.
HEADER_FAMILY = (BLUEY, PERI, ICE, LILAC, VIOLET)
ORANGE_FAMILY = (PEACH, ALMOND, BUTTERSCOTCH)
ACTIVE = "#F3F3FC"   # near-white, so the active item stands out in every family
SIDEBAR_COLOURS = (PEACH, BUTTERSCOTCH, ALMOND)   # sub-view blocks, in turn

NAMES = {
    "orange": ORANGE, "butterscotch": BUTTERSCOTCH, "peach": PEACH, "almond": ALMOND, "violet": VIOLET,
    "lilac": LILAC, "bluey": BLUEY, "peri": PERI, "ice": ICE, "rose": ROSE, "red": RED, "sunflower": SUNFLOWER,
    "gray": GRAY, "grey": GRAY, "green": GREEN, "earth": EARTH, "bone": BONE, "ink": INK, "black": INK,
    "white": WHITE, "dim": DIM, "active": ACTIVE,
}

# Families a frame may be coloured in, for frames that don't name their colours: the frame colour and the
# colours of its label blocks, in turn (see components that pick colours automatically)
FAMILIES = {
    "orange": (ORANGE, (PEACH, ALMOND, BUTTERSCOTCH)),
    "lilac": (LILAC, (VIOLET, LILAC, PERI)),
    "blue": (BLUEY, (PERI, ICE, BLUEY)),
    "sunflower": (SUNFLOWER, (SUNFLOWER, BONE, BUTTERSCOTCH)),
    "rose": (ROSE, (PEACH, ROSE, ALMOND)),
}


def colour(value, where="colour"):
    """A colour from a configuration: a palette name or a CSS colour (#hex, rgb(), rgba(), var())."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        if v.lower() in NAMES:
            return NAMES[v.lower()]
        if v.startswith(("#", "rgb", "hsl", "var(")):
            return v
    raise ValueError(f"{where}: unknown colour {value!r} (palette names: {', '.join(sorted(NAMES))})")


def colours(value, where="colours"):
    """A state -> colour map (values through colour()), a list of colours, or one colour."""
    if isinstance(value, dict):
        return {str(k): colour(v, f"{where}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [colour(v, f"{where}[{i}]") for i, v in enumerate(value)]
    return colour(value, where)


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    return "rgba(%d, %d, %d, %s)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


BAR_OFF = rgba(PERI, 0.18)   # inactive segment of a segment bar
