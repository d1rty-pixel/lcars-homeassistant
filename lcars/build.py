"""Build the Lovelace configuration of the dashboard from a Site."""
import re

from . import components  # noqa: F401  (registers the component types)
from .engine import screen
from .engine.codes import reset
from .frame import view_config

FR = re.compile(r"(?<![\w(,])(\d*\.?\d+)fr")
LCARDS_CARDS = ("custom:lcards-button", "custom:lcards-elbow", "custom:lcards-slider", "custom:lcards-data-grid",
                "custom:lcards-chart")


def view_content(site, section, view):
    """The view's content card (its component for every screen tier, at least as high as it needs where
    the page scrolls) and that height (CSS, or None)."""
    ctx = site.ctx(section, view)
    card = view.content.card(ctx)
    need = view.content.min_height(ctx.at(tier=screen.phone_tier(), phone=True))
    if need:
        card = screen.scroll_min_h(card, need)
    return card, need


def build(site):
    """The dashboard's Lovelace configuration (a dict)."""
    reset()
    views = []
    for section in site.sections:
        for view in section.views:
            ctx = site.ctx(section, view)
            content, need = view_content(site, section, view)
            views.append(view_config(site, section, view, content, ctx, need))
    config = {"title": site.dashboard_title, "views": views}
    if site.kiosk:
        config["kiosk_mode"] = {"hide_header": True, "hide_sidebar": True}
    return finalize(config, site.sounds)


def finalize(node, sounds=None):
    """minmax(0,Nfr) for every fr track, and no theme min-height on LCARdS cards, so nothing inflates the
    grid beyond the viewport; click sounds (site `sounds`) on interactive LCARdS cards."""
    if isinstance(node, dict):
        lay = node.get("layout")
        if isinstance(lay, dict):
            for k in ("grid-template-columns", "grid-template-rows"):
                if k in lay:
                    lay[k] = FR.sub(r"minmax(0,\1fr)", lay[k])
        if node.get("type") in LCARDS_CARDS:
            node.setdefault("min_height", 0)
        if sounds and node.get("type") in ("custom:lcards-button", "custom:lcards-slider") \
                and node.get("interactive", True) and node.get("tap_action", {}).get("action") != "none":
            node.setdefault("sounds", dict(sounds))
        for v in node.values():
            finalize(v, sounds)
    elif isinstance(node, list):
        for v in node:
            finalize(v, sounds)
    return node


def entities(config):
    """Every entity ID a built dashboard refers to (entity fields, triggers_update, states['...'] in JS)."""
    found = set()

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if k in ("entity", "entity_id") and isinstance(v, str) and "." in v:
                    found.add(v)
                elif k == "triggers_update" and isinstance(v, list):
                    found.update(x for x in v if isinstance(x, str))
                else:
                    walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
        elif isinstance(n, str):
            found.update(re.findall(r"states\['([a-z_]+\.[a-z0-9_]+)'\]", n))
    walk(config)
    return found


def missing_entities(site, config):
    """The entities the dashboard refers to that HA doesn't have (sorted), and how many it refers to. LCARdS
    shows a value template as raw text where its entity is missing."""
    found = entities(config)
    have = {s["entity_id"] for s in site.states()}
    return sorted(e for e in found if e not in have and e != "all"), len(found)
