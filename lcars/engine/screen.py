"""Screen tiers: what is rendered where (docs/DESIGN.md "Display priorities").

Content that doesn't fit a shorter screen is not rendered there, instead of being cut off. HA's hui-card,
which wraps every child of a layout card, doesn't create a card whose visibility conditions fail, so a
variant that isn't shown costs nothing.

A *tier* is a display priority: 0 is always shown (the phone fallback), 1 everywhere but on phones, 2..4
from taller viewports up (PRIORITY_MIN_H). With scrolling (layout.scroll: auto), a screen lower than
SCROLL_MIN_H (a phone) shows what the highest tier shows: the sidebar and the content scroll there, so
nothing is left out.
"""
import json

from . import sizes
from .cards import at, grid
from .sizes import Len, only_under

SCROLL = "auto"      # "auto": phones scroll the sidebar and the content; "off": nothing ever scrolls
SCROLL_MIN_H = 520   # below this viewport height the page scrolls (scroll: auto)
PRIORITY_MIN_H = {0: 0, 1: sizes.PHONE_H, 2: 760, 3: 880, 4: 1000}
TIERS = (0, 1, 2, 3, 4)
SCROLL_PRIORITY = max(PRIORITY_MIN_H)


def configure(layout):
    """Apply the site's layout settings: scroll (auto or off), scroll_min_h."""
    global SCROLL, SCROLL_MIN_H
    unknown = set(layout) - {"scroll", "scroll_min_h"}
    if unknown:
        raise ValueError(f"layout: unknown setting(s) {', '.join(sorted(unknown))} (scroll, scroll_min_h)")
    SCROLL = layout.get("scroll", "auto")
    if SCROLL not in ("auto", "off"):
        raise ValueError(f"layout.scroll: 'auto' or 'off', not {SCROLL!r}")
    SCROLL_MIN_H = int(layout.get("scroll_min_h", sizes.PHONE_H))


def phone_query():
    return f"(max-height: {sizes.PHONE_H}px)"


def not_phone_query():
    return f"(min-height: {sizes.PHONE_H + 0.02}px)"


def portrait_query():
    """A phone held upright: as narrow as a phone (landscape) is low. The page frame needs landscape there."""
    return f"(orientation: portrait) and (max-width: {sizes.PHONE_H}px)"


def on_phone(card, phone=True):
    """`card` only on phones (phone=False: everywhere else)."""
    return dict(card, visibility=card.get("visibility", []) +
                [{"condition": "screen", "media_query": phone_query() if phone else not_phone_query()}])


def by_screen(other, phone):
    """`phone` on phones, `other` everywhere else: for what the phone's width needs (narrow pills), which
    scrolling doesn't change. What only its height needs belongs in tiered()."""
    return grid('"v"', "1fr", "1fr", [at(on_phone(other, False), "v"), at(on_phone(phone), "v")], gap="0")


def scroll_min_h(card, height):
    """`card` at least `height` high on screens that scroll (the scrolling row grows by it), with no minimum
    elsewhere. A grid row's minimum, since LCARdS passes no min-height from view_layout."""
    if SCROLL == "off":
        return card
    return grid('"v"', "1fr", f"minmax({only_under(SCROLL_MIN_H, height)},1fr)", [at(card, "v")], gap="0")


def shown_from(card, priority, below=None):
    """`card` only while the viewport is at least as high as `priority` needs (and lower than what
    priority `below` needs, if given)."""
    lo, hi = PRIORITY_MIN_H[priority], PRIORITY_MIN_H[below] if below else None
    if SCROLL == "auto":        # scrolling screens: by SCROLL_PRIORITY, not by their height
        lo = max(lo, SCROLL_MIN_H)
    q = [f"(min-height: {Len.of(lo)})"] if lo else []
    if hi is not None:
        q.append(f"(max-height: {Len.of(hi - 0.02)})")
    queries = [" and ".join(q) or "all"] if hi is None or hi > lo else []
    scroll_h = PRIORITY_MIN_H[SCROLL_PRIORITY]
    if SCROLL == "auto" and PRIORITY_MIN_H[priority] <= scroll_h and (hi is None or scroll_h < hi):
        queries.append(f"(max-height: {SCROLL_MIN_H - 0.02}px)")
    return dict(card, visibility=card.get("visibility", []) +
                [{"condition": "screen", "media_query": ", ".join(queries) or "not all"}])


def tiered(variants):
    """One of several variants of the same content by viewport height: {priority: card}; the variant with
    the highest priority that fits is rendered, the others aren't. The lowest variant is the fallback: it
    is shown on every screen too short for the others (phones included)."""
    prios = sorted(variants, reverse=True)
    cards = [at(shown_from(variants[p], p if i < len(prios) - 1 else 0, prios[i - 1] if i else None), "v")
             for i, p in enumerate(prios)]
    return grid('"v"', "1fr", "1fr", cards, gap="0")


def phone_tier():
    """The tier a phone renders: the highest when it scrolls, else the fallback."""
    return SCROLL_PRIORITY if SCROLL == "auto" else 0


def _same(a, b):
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def responsive(render, ctx):
    """The card `render(ctx)` gives at every screen tier, as few variants as it takes: renders it for the
    tiers 1..4 (not a phone) and for a phone, keeps the distinct ones (tiered() by height, by_screen() for a
    phone that differs from what the height variants would show it). ctx.fixed marks a render inside such
    a pass, where nested components render for the tier they are given."""
    renders = {t: render(ctx.at(tier=t, phone=False)) for t in (1, 2, 3, 4)}
    variants, prev = {}, None
    for t in (1, 2, 3, 4):
        if prev is None or not _same(renders[t], prev):
            variants[t] = renders[t]
            prev = renders[t]
    base = variants[1] if len(variants) == 1 else tiered(variants)
    phone = render(ctx.at(tier=phone_tier(), phone=True))
    shown = renders[4] if SCROLL == "auto" else renders[1]     # what `base` shows on a phone
    return base if _same(phone, shown) else by_screen(base, phone)
