"""The site configuration (lcars.yaml, docs/CONFIGURATION.md): loading, interpolation, and the model the
build works on (Site, Section, View).

Before the components are built, the YAML is expanded:
  - `${{ path }}` in any string is replaced by a value: `vars.NAME...` (the site's `vars`), `env.NAME` (an
    environment variable), `data.NAME...` (build-time data, see `data`), or a `repeat` variable. A string that is only a
    `${{ ... }}` becomes that value itself (a list, a mapping, a number). In paths, `.key` or `[key]`
    index mappings and lists, `[name=Daylight]` picks the list item whose `name` is Daylight.
  - a list item {repeat: {as: x, in: [...]}, item: {...}} becomes one item per value of `in`, with
    `${{ x... }}` in `item` replaced.
"""
import copy
import fnmatch
import json
import os
import re

import yaml

from .components.base import ConfigError, Ctx, build, colour, width
from .engine import palette, screen, sizes
from .engine.codes import lcars_code

EXPR = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")
DEFAULT_URL_PATH = "lcars-bridge"
DEFAULT_THEME = "LCARS Bridge"


def lookup(root, path, where):
    """The value at `path` (a.b[c][name=x].d) in `root`."""
    tokens = re.findall(r"[^.\[\]]+|\[[^\]]*\]", path)
    cur = root
    walked = []
    for t in tokens:
        key = t[1:-1] if t.startswith("[") else t
        walked.append(key)
        if isinstance(cur, dict):
            if key not in cur:
                raise ConfigError(f"{where}: {'.'.join(walked)} not found (have: {', '.join(map(str, cur))})")
            cur = cur[key]
        elif isinstance(cur, list):
            if "=" in key:
                k, v = key.split("=", 1)
                hits = [x for x in cur if isinstance(x, dict) and str(x.get(k)) == v]
                if not hits:
                    raise ConfigError(f"{where}: no item with {k}={v} in {'.'.join(walked[:-1])}")
                cur = hits[0]
            elif key.lstrip("-").isdigit():
                cur = cur[int(key)]
            else:
                raise ConfigError(f"{where}: {key!r} can't index a list ({'.'.join(walked[:-1])})")
        else:
            raise ConfigError(f"{where}: {'.'.join(walked)}: {type(cur).__name__} has no {key!r}")
    return cur


class Expander:
    """Interpolation and repeat (see the module docstring)."""

    def __init__(self, data_loader, vars_=None):
        self.data_loader = data_loader
        self.vars = vars_ or {}

    def root(self, scope):
        return _Root(self.data_loader, scope)

    def value(self, expr, scope, where):
        """The value of an expression: a path, optionally with a default after "|" (used where the path
        doesn't exist), e.g. ${{ data.light.phases[name=Moonlight].levels.red | 0 }}."""
        if "|" in expr:
            path, default = (x.strip() for x in expr.split("|", 1))
            try:
                return self.value(path, scope, where)
            except ConfigError:
                return yaml.safe_load(default)
        head = re.split(r"[.\[]", expr, 1)[0]
        if head == "vars":
            tail = expr[4:].lstrip(".")
            return lookup(self.vars, tail, where) if tail else self.vars
        if head == "env":
            name = expr[4:]
            if name not in os.environ:
                raise ConfigError(f"{where}: environment variable {name} is not set")
            return os.environ[name]
        if head == "data":
            rest = expr[5:]
            name = re.split(r"[.\[]", rest, 1)[0]
            val = self.data_loader(name, where)
            tail = rest[len(name):].lstrip(".")
            return lookup(val, tail, where) if tail else val
        if head in scope:
            tail = expr[len(head):].lstrip(".")
            return lookup(scope[head], tail, where) if tail else scope[head]
        raise ConfigError(f"{where}: unknown name {head!r} in ${{{{ {expr} }}}} (vars, env, data, or a repeat "
                          "variable)")

    def expand(self, node, scope=None, where="lcars.yaml"):
        scope = scope or {}
        if isinstance(node, str):
            m = EXPR.fullmatch(node.strip())
            if m:
                return copy.deepcopy(self.value(m.group(1), scope, where))
            return EXPR.sub(lambda mm: str(self.value(mm.group(1), scope, where)), node)
        if isinstance(node, list):
            out = []
            for i, item in enumerate(node):
                w = f"{where}[{i}]"
                if isinstance(item, dict) and set(item) == {"repeat", "item"}:
                    rep = item["repeat"]
                    if not isinstance(rep, dict) or "as" not in rep or "in" not in rep:
                        raise ConfigError(f"{w}.repeat: {{as: name, in: [values]}}")
                    values = self.expand(rep["in"], scope, f"{w}.repeat.in")
                    for j, v in enumerate(values):
                        out.append(self.expand(item["item"], {**scope, rep["as"]: v}, f"{w}.item[{j}]"))
                else:
                    out.append(self.expand(item, scope, w))
            return out
        if isinstance(node, dict):
            return {k: self.expand(v, scope, f"{where}.{k}") for k, v in node.items()}
        return node


class _Root:
    pass


# ── Model ───────────────────────────────────────────────────────────────────────
class Alert:
    """One of the site's alerts (site `alert`, docs/CONFIGURATION.md): while `entity` is in one of the listed
    states, lcars-alert.js colours the page frame in the state's colour (pulsing if `blink`, until someone
    acknowledges it), shows its heading and text in a dialog and plays its sound."""
    FIELDS = {"entity", "states"}
    STATE_FIELDS = {"heading", "text", "colour", "blink", "sound", "title", "short"}   # title, short: old names
    SOUNDS = ("red", "yellow", "blue", "gray", "black")

    def __init__(self, node, where="alert"):
        if not isinstance(node, dict) or "entity" not in node:
            raise ConfigError(f"{where}: a mapping with entity and states")
        unknown = set(node) - self.FIELDS
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(sorted(unknown))} (fields: entity, states)")
        self.entity = node["entity"]
        self.states = {}
        for state, s in (node.get("states") or {}).items():
            s = s or {}
            w = f"{where}.states.{state}"
            unknown = set(s) - self.STATE_FIELDS
            if unknown:
                raise ConfigError(f"{w}: unknown field(s) {', '.join(sorted(unknown))}")
            c = colour(s.get("colour", "red"), f"{w}.colour")
            sound = s.get("sound", self._sound(c))
            if sound not in (*self.SOUNDS, "none", False, None):
                raise ConfigError(f"{w}.sound: one of {', '.join(self.SOUNDS)}, none")
            heading = s.get("heading", s.get("short", self._heading(c)))
            self.states[str(state)] = {"heading": self._text(heading), "text": self._text(s.get("text", s.get("title", ""))),
                                       "colour": c, "blink": bool(s.get("blink", False)),
                                       "sound": f"alert_{sound}" if sound in self.SOUNDS else None}
        if not self.states:
            raise ConfigError(f"{where}: needs states")

    @staticmethod
    def _sound(c):
        return {palette.RED: "red", palette.SUNFLOWER: "yellow", palette.BLUEY: "blue", palette.PERI: "blue",
                palette.ICE: "blue", palette.GRAY: "gray"}.get(c, "yellow")

    @staticmethod
    def _heading(c):
        return {palette.RED: "Red alert", palette.SUNFLOWER: "Yellow alert", palette.BLUEY: "Blue alert",
                palette.PERI: "Blue alert", palette.ICE: "Blue alert"}.get(c, "Alert")

    @staticmethod
    def _text(t):
        """A text as a JS expression: plain text, or JS (a string starting with 'js:')."""
        t = str(t)
        return t[3:].strip() if t.startswith("js:") else json.dumps(t, ensure_ascii=False)

    def card(self):
        """This alert in lcars-alert.js' config."""
        return {"entity": self.entity, "states": self.states}


class Link:
    def __init__(self, node, where):
        if isinstance(node, str):
            node = {"url": node}
        self.label = node.get("label", "Classic")
        self.url = node["url"]


class BarPiece:
    """A piece of the mid bar over one or more of the view's columns: title, colour, side (where the title
    sits), span (columns it covers), buttons (a component in the bar, e.g. a radar's or a player's
    controls; buttons_max: their widest in px), drop (a plain piece that reaches down through the frame's
    inner curve to the content, e.g. for a spine that hangs from it)."""

    def __init__(self, node, where):
        if isinstance(node, str):
            node = {"title": node}
        unknown = set(node) - {"title", "colour", "side", "span", "buttons", "buttons_max", "drop"}
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")
        self.title = node.get("title", "")
        self.colour = colour(node.get("colour", "orange"), f"{where}.colour")
        self.side = node.get("side", "left")
        self.span = int(node.get("span", 1))
        self.buttons = build(node["buttons"], f"{where}.buttons") if node.get("buttons") else None
        self.buttons_max = node.get("buttons_max")
        self.drop = bool(node.get("drop", False))
        if self.drop and (self.title or self.buttons):
            raise ConfigError(f"{where}.drop: only a plain piece (no title, no buttons) can drop")


class Right:
    """The page frame closed on the right: a shoulder from the mid bar and one from the foot bar, the
    content's pillar between them (width: label, decor or px; foot: the foot shoulder's colour)."""

    def __init__(self, node, where):
        self.colour = colour(node.get("colour", "almond"), f"{where}.colour")
        self.width = width(node.get("width", "label"), None, f"{where}.width")
        self.foot = colour(node.get("foot"), f"{where}.foot", self.colour)


VIEW_FIELDS = {"key", "path", "label", "title", "subtitle", "label_width", "columns", "bar", "right", "content"}


class View:
    def __init__(self, node, section, where):
        unknown = set(node) - VIEW_FIELDS
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(sorted(unknown))} (view fields: "
                              f"{', '.join(sorted(VIEW_FIELDS))})")
        if "key" not in node or "content" not in node:
            raise ConfigError(f"{where}: a view needs key and content")
        self.section = section
        self.key = str(node["key"])
        self.label = node.get("label", self.key.replace("-", " ").title())
        self.path = node.get("path", self.key if len(section.views_raw) == 1 else f"{section.key}-{self.key}")
        self.title = node.get("title", f"LCARS {self.label}")
        self.subtitle = node.get("subtitle", self.label)
        lw = node.get("label_width")
        self.label_w = width(lw, None, f"{where}.label_width") if lw is not None else sizes.LABEL_W
        # the top row's columns (content and mid bar share them): CSS tracks, px numbers (fluid), label, decor
        self.columns = [width(c, None, f"{where}.columns", number=sizes.fl) for c in node.get("columns", ["1fr"])]
        bar = node.get("bar")
        if bar is None:
            bar = [{"title": self.subtitle}]
        self.bar = [BarPiece(p, f"{where}.bar[{i}]") for i, p in enumerate(bar)]
        if sum(p.span for p in self.bar) != len(self.columns) and self.bar:
            raise ConfigError(f"{where}.bar: the pieces span {sum(p.span for p in self.bar)} columns, the view has "
                              f"{len(self.columns)} (columns)")
        self.right = Right(node["right"], f"{where}.right") if node.get("right") else None
        self.content = build(node["content"], f"{where}.content")
        self.mid_t = sizes.TOP_BAR_T if self.bar else sizes.BAR
        self.code = lcars_code(f"view/{self.key}")


SECTION_FIELDS = {"key", "label", "short", "title", "colour", "link", "readouts", "views"}


class Section:
    def __init__(self, node, index, where):
        unknown = set(node) - SECTION_FIELDS
        if unknown:
            raise ConfigError(f"{where}: unknown field(s) {', '.join(sorted(unknown))} (section fields: "
                              f"{', '.join(sorted(SECTION_FIELDS))})")
        if "key" not in node or not node.get("views"):
            raise ConfigError(f"{where}: a section needs key and views")
        self.key = str(node["key"])
        self.label = node.get("label", self.key.title())
        self.short = node.get("short", self.label)
        self.title = node.get("title", self.label)
        self.colour = colour(node.get("colour"), f"{where}.colour",
                             palette.HEADER_FAMILY[index % len(palette.HEADER_FAMILY)])
        self.link = Link(node["link"], f"{where}.link") if node.get("link") else None
        self.readouts = [build(r if isinstance(r, dict) else {"type": r}, f"{where}.readouts[{i}]")
                         for i, r in enumerate(node.get("readouts") or [])]
        self.views_raw = node["views"]
        self.views = [View(v, self, f"{where}.views[{i}]") for i, v in enumerate(node["views"])]


SITE_FIELDS = {"homeassistant", "dashboard", "layout", "alert", "calendars", "titles", "weather", "radar", "numbers",
               "sounds", "data", "vars", "plugins", "sections", "header_code"}


class Site:
    def __init__(self, raw, path=None, ha=None, host=None):
        unknown = set(raw) - SITE_FIELDS
        if unknown:
            raise ConfigError(f"lcars.yaml: unknown top-level field(s) {', '.join(sorted(unknown))} (fields: "
                              f"{', '.join(sorted(SITE_FIELDS))})")
        self.path = path
        self.raw = raw
        self._ha = ha
        self._host = host
        self._states = None
        self._data = {}
        self.homeassistant = raw.get("homeassistant") or {}
        d = raw.get("dashboard") or {}
        self.url_path = os.environ.get("LCARS_DASHBOARD", d.get("url_path", DEFAULT_URL_PATH))
        if "-" not in self.url_path:
            raise ConfigError(f"dashboard.url_path: HA needs a hyphen in a dashboard's path ({self.url_path!r})")
        self.dashboard_title = d.get("title", "LCARS")
        self.theme = d.get("theme", DEFAULT_THEME)
        self.icon = d.get("icon", "mdi:star-four-points")
        self.show_in_sidebar = d.get("show_in_sidebar", True)
        self.require_admin = d.get("require_admin", False)
        self.kiosk = d.get("kiosk", True)
        self.header_code = raw.get("header_code", "LCARS 47174")
        self.layout = raw.get("layout") or {}
        screen.configure(self.layout)
        self.sounds = raw.get("sounds")
        self.weather = raw.get("weather", "weather.home")
        self.radar = raw.get("radar")
        self.numbers = raw.get("numbers") or {}
        self.titles = raw.get("titles") or {}
        self.calendars = []
        others = iter(WEEK_PALETTE * 4)
        for i, c in enumerate(raw.get("calendars") or []):
            if isinstance(c, str):
                c = {"entity": c}
            self.calendars.append({"entity": c["entity"], "label": c.get("label"),
                                   "colour": colour(c.get("colour"), f"calendars[{i}].colour") or next(others),
                                   "code": lcars_code(f"week/{c['entity']}")})
        alerts = raw.get("alert") or []
        if isinstance(alerts, dict):
            alerts = [alerts]
        self.alerts = [Alert(a, f"alert[{i}]" if len(alerts) > 1 else "alert") for i, a in enumerate(alerts)]
        if not raw.get("sections"):
            raise ConfigError("lcars.yaml: no sections (see docs/CONFIGURATION.md)")
        self.sections = [Section(s, i, f"sections[{i}]") for i, s in enumerate(raw["sections"])]
        keys = [v.key for s in self.sections for v in s.views]
        paths = [v.path for s in self.sections for v in s.views]
        for what, items in (("view key", keys), ("view path", paths)):
            dup = {x for x in items if items.count(x) > 1}
            if dup:
                raise ConfigError(f"sections: duplicate {what}(s) {', '.join(sorted(dup))}")

    # ── live data ──
    def ha(self):
        if self._ha is None:
            from .ha import Client
            self._ha = Client(ha_url(self.homeassistant), ha_token(self.homeassistant))
        return self._ha

    def host(self):
        if self._host is None:
            from .host import from_config
            self._host = from_config(self.homeassistant)
        return self._host

    def states(self):
        if self._states is None:
            self._states = self.ha().result({"type": "get_states"})
        return self._states

    def friendly_name(self, entity):
        """The entity's name in HA (or its object ID where HA doesn't know it)."""
        try:
            st = next((s for s in self.states() if s["entity_id"] == entity), None)
        except Exception:
            st = None
        return (st or {}).get("attributes", {}).get("friendly_name") or entity.split(".", 1)[1].replace("_", " ")

    def resolve(self, entity):
        """An entity ID, or the first live entity matching a pattern (media_player.spotify_*)."""
        if not any(ch in entity for ch in "*?["):
            return entity
        ids = sorted(st["entity_id"] for st in self.states() if fnmatch.fnmatch(st["entity_id"], entity))
        return ids[0] if ids else entity.replace("*", "").rstrip("_")

    def ctx(self, section=None, view=None):
        return Ctx(site=self, section=section, view=view, label_w=view.label_w if view else sizes.LABEL_W,
                   key=view.key if view else "")


WEEK_PALETTE = [palette.PEACH, palette.ICE, palette.LILAC, palette.PERI, palette.SUNFLOWER, palette.ALMOND, palette.ROSE,
                palette.BUTTERSCOTCH, palette.VIOLET, palette.BLUEY]


def ha_url(cfg):
    url = os.environ.get("HA_URL") or cfg.get("url")
    if not url and cfg.get("host"):
        url = f"http://{cfg['host']}:{cfg.get('port', 8123)}"
    return url or "http://homeassistant.local:8123"


def ha_token(cfg):
    if os.environ.get("HA_TOKEN"):
        return os.environ["HA_TOKEN"].strip()
    path = os.path.expanduser(cfg.get("token_file", "~/.config/homeassistant/token"))
    try:
        return open(path).read().strip()
    except OSError:
        raise ConfigError(f"no access token: set HA_TOKEN or put a long-lived token in {path} "
                          "(HA: your profile → Security → Long-lived access tokens)")


def read_yaml(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ConfigError(f"{path}: not found (lcars init writes a starting point)")
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: {e}")


def load(path, ha=None, host=None, build_components=True):
    """The Site from a configuration file. build_components=False loads only the connection settings (for
    setup and doctor, which must work before the views are right)."""
    raw = read_yaml(path)
    base = os.path.dirname(os.path.abspath(path))
    holder = {}

    def data(name, where):
        if name in holder:
            return holder[name]
        spec = (raw.get("data") or {}).get(name)
        if spec is None:
            raise ConfigError(f"{where}: no data source {name!r} (site `data`)")
        holder[name] = load_data(spec, base, raw.get("homeassistant") or {}, host, f"data.{name}")
        return holder[name]

    if not build_components:
        return raw
    load_plugins(raw.get("plugins") or [], base)
    ex = Expander(data)
    ex.vars = ex.expand(raw.get("vars") or {}, where="vars")
    expanded = ex.expand({k: v for k, v in raw.items() if k not in ("data", "vars")})
    return Site(expanded, path, ha=ha, host=host)


def load_plugins(paths, base):
    """Import the site's plugins: Python files (relative to lcars.yaml) that register their own component
    types with @component (docs/EXTENDING.md)."""
    import importlib.util
    for i, rel in enumerate(paths):
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            raise ConfigError(f"plugins[{i}]: {path} not found")
        name = "lcars_plugin_" + re.sub(r"\W", "_", os.path.splitext(os.path.basename(path))[0])
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)


def load_data(spec, base, ha_cfg, host, where):
    """Build-time data: {file: path} (YAML/JSON next to lcars.yaml), {ha_file: /config/...} (from the HA
    host, see homeassistant.files), {url: ...}; `key` picks a part of it."""
    if isinstance(spec, str):
        spec = {"file": spec}
    if "file" in spec:
        text = open(os.path.join(base, spec["file"]), encoding="utf-8").read()
    elif "ha_file" in spec:
        from .host import from_config
        h = host or from_config(ha_cfg)
        try:
            text = h.read(spec["ha_file"]).decode("utf-8")
        except Exception as e:
            raise ConfigError(f"{where}: {e}")
    elif "url" in spec:
        import urllib.request
        text = urllib.request.urlopen(spec["url"], timeout=60).read().decode("utf-8")
    elif "value" in spec:
        return spec["value"]
    else:
        raise ConfigError(f"{where}: file, ha_file, url or value")
    val = yaml.safe_load(text)
    return lookup(val, spec["key"], where) if spec.get("key") else val
