"""`lcars setup` and `lcars doctor`: bring Home Assistant into the state the dashboard needs, or only check it
(docs/INSTALL.md). Every step checks first and changes something only when it isn't right yet, so setup can
run again at any time (e.g. after an update of this package: it copies the changed cards).

Steps, in order:
  connection   HA reachable, the token accepted
  hacs         HACS installed (the dependencies below come through it)
  lcards       LCARdS downloaded (HACS) and set up (a config entry)
  kiosk-mode   kiosk-mode downloaded (HACS; hides HA's header and sidebar on the dashboard)
  card-mod     not a Lovelace resource while UIX is installed (UIX refuses to set up then)
  time         the Time & Date integration's sensor.time (re-renders the clock every minute)
  helpers      input_boolean.lcars_bars (the global switch for the segment bars), input_text.lcars_alert_ack
               (alerts acknowledged on any screen)
  files        the cards and the view theme copied to /config/www/lcars and /config/themes
  themes       the theme loaded (configuration.yaml includes the themes directory)
  resources    the cards and the Antonio font as Lovelace resources
  dashboard    the dashboard exists
A restart of HA, where an integration was downloaded or configuration.yaml changed, is asked for first
(or done right away with --yes).
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import yaml

from .config import DEFAULT_THEME, DEFAULT_URL_PATH, ha_token, ha_url, read_yaml
from .host import HostError, from_config

PKG = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(PKG, "www")
THEMES = os.path.join(PKG, "themes")
REMOTE_WWW = "/config/www/lcars"
REMOTE_THEME = "/config/themes/lcars_bridge.yaml"
LOCAL_URL = "/local/lcars"
FONT_URL = "https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&display=swap"
REQUIRED_HACS = [   # (full name, category, what for)
    ("snootched/lcards", "integration", "LCARdS: the cards the frame is drawn with"),
    ("NemesisRE/kiosk-mode", "plugin", "kiosk-mode: hides HA's header and sidebar on the dashboard"),
]
# old installs (before the framework) registered the cards one by one in /config/www
LEGACY = re.compile(r"^/local/(lcars-[a-z-]+|lcards-registry-fix)\.js(\?.*)?$")

OK, FIXED, FAIL, WARN, INFO = "ok", "fixed", "FAIL", "warn", "info"
MARK = {OK: "✓", FIXED: "→", FAIL: "✗", WARN: "!", INFO: "·"}


class Report:
    def __init__(self):
        self.rows = []
        self.restart = []      # reasons HA needs a restart

    def add(self, step, status, text):
        self.rows.append((step, status, text))
        print(f" {MARK[status]} {step:<11} {text}", flush=True)

    @property
    def failed(self):
        return [r for r in self.rows if r[1] == FAIL]


class Setup:
    def __init__(self, raw, fix, yes=False):
        self.raw = raw
        self.fix = fix
        self.yes = yes
        self.cfg = raw.get("homeassistant") or {}
        self.url = ha_url(self.cfg).rstrip("/")
        self.token = None
        self.ha = None
        self.host = None
        self.report = Report()
        d = raw.get("dashboard") or {}
        self.url_path = os.environ.get("LCARS_DASHBOARD", d.get("url_path", DEFAULT_URL_PATH))
        self.theme = d.get("theme", DEFAULT_THEME)
        self.dashboard = d

    # ── HA access ──
    def connect(self):
        from .ha import Client
        self.token = ha_token(self.cfg)
        self.ha = Client(self.url, self.token)
        return self.ha

    def rest(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")

    def get_text(self, path):
        req = urllib.request.Request(self.url + path, headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")

    # ── steps ──
    def step_connection(self):
        try:
            self.connect()
        except Exception as e:
            self.report.add("connection", FAIL, f"{e}")
            return False
        self.report.add("connection", OK, f"{self.url} (Home Assistant {self.ha.version})")
        return True

    def hacs_repos(self):
        try:
            return {r["full_name"].lower(): r for r in self.ha.result({"type": "hacs/repositories/list"})}
        except Exception:
            return None

    def step_hacs(self):
        repos = self.hacs_repos()
        if repos is None:
            self.report.add("hacs", FAIL, "HACS isn't installed. Install it once (https://hacs.xyz/docs/use/), "
                                          "link it to GitHub, then run lcars setup again.")
            return None
        self.report.add("hacs", OK, "installed")
        return repos

    def hacs_install(self, repos, full_name, category, what):
        step = full_name.split("/")[1].lower()[:11]
        r = repos.get(full_name.lower())
        if r and r.get("installed"):
            self.report.add(step, OK, f"{what} ({r.get('installed_version')})")
            return r
        if not self.fix:
            self.report.add(step, FAIL, f"not downloaded: {what}")
            return None
        if r is None:        # not in HACS' lists: add it as a custom repository
            self.ha.result({"type": "hacs/repositories/add", "repository": full_name, "category": category})
            for _ in range(30):
                repos.update(self.hacs_repos() or {})
                r = repos.get(full_name.lower())
                if r:
                    break
                time.sleep(2)
            if r is None:
                self.report.add(step, FAIL, f"HACS didn't add {full_name}")
                return None
        self.ha.result({"type": "hacs/repository/download", "repository": str(r["id"])})
        for _ in range(60):          # HACS downloads in the background
            r = (self.hacs_repos() or {}).get(full_name.lower()) or r
            if r.get("installed"):
                break
            time.sleep(2)
        if not r.get("installed"):
            self.report.add(step, FAIL, f"the download of {full_name} didn't finish; see HACS")
            return None
        if category == "integration":
            self.report.restart.append(f"{full_name} was downloaded")
        self.report.add(step, FIXED, f"downloaded {full_name} {r.get('installed_version', '')}")
        return r

    def config_entry(self, domain, answers=None):
        """The domain's config entries; with fix, create one through its config flow (answers: the input for
        its form steps; a form without answers is submitted with its defaults)."""
        entries = self.ha.result({"type": "config_entries/get", "domain": domain})
        if entries or not self.fix:
            return entries, False
        flow = self.rest("POST", "/api/config/config_entries/flow", {"handler": domain, "show_advanced_options": False})
        for _ in range(8):
            if flow.get("type") == "create_entry":
                return [flow.get("result")], True
            if flow.get("type") == "abort":
                raise RuntimeError(f"{domain}: setup aborted ({flow.get('reason')})")
            if flow.get("type") != "form":
                raise RuntimeError(f"{domain}: unexpected setup step {flow.get('type')}")
            flow = self.rest("POST", f"/api/config/config_entries/flow/{flow['flow_id']}",
                             (answers or {}).get(flow.get("step_id"), {}))
        raise RuntimeError(f"{domain}: the setup flow didn't finish")

    def step_lcards(self, repos):
        r = self.hacs_install(repos, *REQUIRED_HACS[0]) if repos is not None else None
        if r is None and repos is not None:
            return
        if self.report.restart:
            self.report.add("lcards", INFO, "its config entry follows after the restart")
            return
        try:
            entries, created = self.config_entry("lcards")
        except Exception as e:
            self.report.add("lcards", FAIL, f"setting it up: {e}")
            return
        if not entries:
            self.report.add("lcards", FAIL, "downloaded but not set up (Settings → Devices & services → Add → LCARdS)")
        else:
            self.report.add("lcards", FIXED if created else OK, "config entry " + ("created" if created else "set up"))

    def resources(self):
        return self.ha.result({"type": "lovelace/resources"})

    def step_card_mod(self, repos):
        uix = repos and (repos.get("lint-free-technology/uix") or {}).get("installed")
        cm = [r for r in self.resources() if "card-mod" in r["url"]]
        if cm and uix:
            self.report.add("card-mod", WARN, "card-mod is a resource while UIX is installed: UIX refuses to set up. "
                                              "Remove card-mod in HACS (UIX keeps card_mod: keys working).")
        else:
            self.report.add("card-mod", OK, "no conflict with UIX")

    def step_time(self):
        states = {s["entity_id"] for s in self.ha.result({"type": "get_states"})}
        if "sensor.time" in states:
            self.report.add("time", OK, "sensor.time")
            return
        if not self.fix:
            self.report.add("time", FAIL, "no sensor.time (the Time & Date integration with the Time sensor)")
            return
        try:
            self.rest_flow_time_date()
            self.report.add("time", FIXED, "set up Time & Date (sensor.time)")
        except Exception as e:
            self.report.add("time", FAIL, f"Time & Date: {e}")

    def rest_flow_time_date(self):
        flow = self.rest("POST", "/api/config/config_entries/flow", {"handler": "time_date"})
        for _ in range(4):
            if flow.get("type") == "create_entry":
                return
            if flow.get("type") != "form":
                raise RuntimeError(flow.get("reason") or flow.get("type"))
            flow = self.rest("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {"display_option": "time"})
        raise RuntimeError("the setup flow didn't finish")

    def step_helpers(self):
        self.helper_bars()
        self.helper_alert_ack()

    def helper_bars(self):
        helpers = {h["id"] for h in self.ha.result({"type": "input_boolean/list"})}
        if "lcars_bars" in helpers:
            self.report.add("helpers", OK, "input_boolean.lcars_bars")
            return
        if not self.fix:
            self.report.add("helpers", FAIL, "no input_boolean.lcars_bars (the segment bars' switch)")
            return
        self.ha.result({"type": "input_boolean/create", "name": "LCARS bars", "icon": "mdi:dots-horizontal",
                        "initial": True})
        time.sleep(1)
        self.ha.service("input_boolean", "turn_on", target={"entity_id": "input_boolean.lcars_bars"})
        self.report.add("helpers", FIXED, "created input_boolean.lcars_bars (on)")

    def helper_alert_ack(self):
        helpers = {h["id"] for h in self.ha.result({"type": "input_text/list"})}
        if "lcars_alert_ack" in helpers:
            self.report.add("helpers", OK, "input_text.lcars_alert_ack")
            return
        if not self.fix:
            self.report.add("helpers", FAIL, "no input_text.lcars_alert_ack (the acknowledged alerts)")
            return
        self.ha.result({"type": "input_text/create", "name": "LCARS alert ack", "icon": "mdi:alert-check",
                        "min": 0, "max": 255, "mode": "text"})
        self.report.add("helpers", FIXED, "created input_text.lcars_alert_ack")

    def file_list(self):
        """(local path, remote path, content) of every file to copy; the registry workaround is written for
        the LCARdS version HA serves."""
        out = []
        for name in sorted(os.listdir(WWW)):
            if name.endswith(".js"):
                data = open(os.path.join(WWW, name), "rb").read()
                if name == "lcards-registry-fix.js":
                    data = self.registry_fix(data)
                out.append((name, f"{REMOTE_WWW}/{name}", data))
        theme = open(os.path.join(THEMES, "lcars_bridge.yaml"), "rb").read()
        if self.theme != DEFAULT_THEME:      # the site names its theme differently
            theme = theme.replace(DEFAULT_THEME.encode(), self.theme.encode())
        out.append(("lcars_bridge.yaml", REMOTE_THEME, theme))
        return out

    def registry_fix(self, template):
        """lcards-registry-fix.js with the tag names the installed lcards.js defines."""
        try:
            src = self.get_text("/lcards/lcards.js")
        except Exception:
            return template
        tags = sorted(set(re.findall(r"customElements\.define\(['\"]([a-z0-9-]+)", src)))
        versions = re.findall(r'"(20\d{2}\.\d{1,2}\.\d+)"', src)
        version = max(set(versions), key=versions.count) if versions else "?"
        if not tags:
            return template
        js = template.decode()
        js = re.sub(r"TAGS is every name lcards\.js [^ ]+ passes", f"TAGS is every name lcards.js {version} passes", js)
        js = re.sub(r"const TAGS = \[.*?\];", "const TAGS = " + json.dumps(tags) + ";", js, flags=re.S)
        return js.encode()

    def step_files(self):
        try:
            self.host = from_config(self.cfg)
        except HostError as e:
            self.report.add("files", FAIL, str(e))
            return None
        files = self.file_list()
        if self.host.method == "none":
            self.report.add("files", WARN if not self.fix else FAIL,
                            "no file access to HA (homeassistant.files): copy lcars/www/*.js to /config/www/lcars/ "
                            "and lcars/themes/lcars_bridge.yaml to /config/themes/ by hand")
            return files
        changed = []
        try:
            for name, remote, data in files:
                try:
                    same = self.host.read(remote) == data
                except HostError:
                    same = False
                if not same:
                    changed.append(name)
                    if self.fix:
                        self.host.write(remote, data)
        except HostError as e:
            self.report.add("files", FAIL, str(e))
            return None
        if not changed:
            self.report.add("files", OK, f"{len(files)} files up to date ({self.host.describe()})")
        elif self.fix:
            self.report.add("files", FIXED, f"copied {', '.join(changed)}")
            self.files_changed = changed
        else:
            self.report.add("files", FAIL, f"out of date: {', '.join(changed)}")
        return files

    def step_themes(self):
        if self.fix:
            try:
                self.ha.service("frontend", "reload_themes")
            except Exception:
                pass
        themes = self.ha.result({"type": "frontend/get_themes"})["themes"]
        if self.theme in themes:
            self.report.add("themes", OK, f"{self.theme!r} loaded")
            return
        conf = None
        if self.host and self.host.method != "none":
            try:
                conf = self.host.read("/config/configuration.yaml").decode()
            except HostError as e:
                self.report.add("themes", FAIL, f"{e}")
                return
            if "!include_dir_merge_named themes" in conf or "!include_dir_named themes" in conf:
                if not self.fix and not self.host.exists(REMOTE_THEME):
                    self.report.add("themes", FAIL, f"{self.theme!r} not copied yet (see files)")
                else:
                    self.report.add("themes", FAIL, f"{self.theme!r} isn't loaded although configuration.yaml "
                                                    "includes themes/ (see HA's log)")
                return
        # the theme file is there but HA doesn't read the themes directory
        if self.fix and conf is not None:
            if re.search(r"^frontend:\s*$", conf, re.M):
                new = re.sub(r"^frontend:\s*$", "frontend:\n  themes: !include_dir_merge_named themes", conf, count=1,
                             flags=re.M)
            elif re.search(r"^frontend:", conf, re.M):
                self.report.add("themes", FAIL, "configuration.yaml has a frontend: section; add "
                                                "'themes: !include_dir_merge_named themes' to it by hand")
                return
            else:
                new = conf.rstrip("\n") + "\n\nfrontend:\n  themes: !include_dir_merge_named themes\n"
            self.host.write("/config/configuration.yaml.lcars-backup", conf)
            self.host.write("/config/configuration.yaml", new)
            self.report.restart.append("configuration.yaml now includes the themes directory")
            self.report.add("themes", FIXED, "configuration.yaml includes themes/ now (backup: "
                                             "configuration.yaml.lcars-backup); loaded after the restart")
            return
        self.report.add("themes", FAIL, f"{self.theme!r} isn't loaded: configuration.yaml needs\n"
                                        "               frontend:\n                 themes: !include_dir_merge_named themes")

    def step_resources(self, files):
        res = self.resources()
        want = {}
        for name, remote, data in files or []:
            if name.endswith(".js"):
                want[f"{LOCAL_URL}/{name}"] = hashlib.sha1(data).hexdigest()[:10]
        want_font = FONT_URL
        todo, done = [], []
        by_path = {r["url"].split("?")[0]: r for r in res}
        for path, v in want.items():
            url = f"{path}?v={v}"
            r = by_path.get(path)
            if r and r["url"] == url:
                continue
            todo.append(("update" if r else "create", r, url))
        if want_font not in {r["url"] for r in res}:
            todo.append(("create-css", None, want_font))
        legacy = [r for r in res if LEGACY.match(r["url"])]
        if not todo and not legacy:
            self.report.add("resources", OK, f"{len(want)} cards and the font")
            return
        if not self.fix:
            what = [u for _, _, u in todo] + [f"remove {r['url']}" for r in legacy]
            self.report.add("resources", FAIL, "to do: " + ", ".join(what))
            return
        for kind, r, url in todo:
            if kind == "update":
                self.ha.result({"type": "lovelace/resources/update", "resource_id": r["id"], "res_type": "module",
                                "url": url})
            else:
                self.ha.result({"type": "lovelace/resources/create", "res_type": "css" if kind == "create-css" else "module",
                                "url": url})
            done.append(url.split("?")[0].rsplit("/", 1)[-1])
        for r in legacy:     # the same cards from an install before the framework
            self.ha.result({"type": "lovelace/resources/delete", "resource_id": r["id"]})
            done.append(f"removed {r['url'].split('?')[0]}")
        self.report.add("resources", FIXED, ", ".join(done))

    def step_dashboard(self):
        dashes = {d["url_path"]: d for d in self.ha.result({"type": "lovelace/dashboards/list"})}
        if self.url_path in dashes:
            self.report.add("dashboard", OK, f"/{self.url_path}")
            return
        if not self.fix:
            self.report.add("dashboard", FAIL, f"no dashboard /{self.url_path}")
            return
        d = self.dashboard
        self.ha.result({"type": "lovelace/dashboards/create", "url_path": self.url_path, "mode": "storage",
                        "title": d.get("title", "LCARS"), "icon": d.get("icon", "mdi:star-four-points"),
                        "show_in_sidebar": d.get("show_in_sidebar", True),
                        "require_admin": d.get("require_admin", False)})
        self.report.add("dashboard", FIXED, f"created /{self.url_path} (fill it with: lcars deploy)")

    def restart(self):
        reasons = "; ".join(self.report.restart)
        if not self.fix:
            return False
        if not self.yes:
            if not sys.stdin.isatty():
                print(f"\nHome Assistant needs a restart ({reasons}). Run lcars setup --yes, or restart it and run "
                      "lcars setup again.")
                return False
            a = input(f"\nHome Assistant needs a restart ({reasons}). Restart now? [y/N] ").strip().lower()
            if a not in ("y", "yes", "j", "ja"):
                print("Restart it later and run lcars setup again.")
                return False
        print("restarting Home Assistant ...", flush=True)
        try:
            self.ha.service("homeassistant", "restart")
        except Exception:
            pass
        time.sleep(15)
        for _ in range(60):
            try:
                self.connect()
                self.ha.result({"type": "get_config"})
                if self.ha.result({"type": "get_config"}).get("state") == "RUNNING":
                    return True
            except Exception:
                pass
            time.sleep(5)
        print("Home Assistant didn't come back within 5 minutes: run lcars setup again once it runs.")
        return False

    def run(self, only=None):
        print(("Setting up" if self.fix else "Checking") + f" Home Assistant for the LCARS dashboard (/{self.url_path})")
        if not self.step_connection():
            return 1
        steps = only or ("hacs", "files", "themes", "resources", "time", "helpers", "dashboard")
        repos = None
        if "hacs" in steps:
            repos = self.step_hacs()
            if repos is not None:
                self.step_lcards(repos)
                self.hacs_install(repos, *REQUIRED_HACS[1])
                self.step_card_mod(repos)
        files = self.step_files() if "files" in steps else None
        if "themes" in steps:
            self.step_themes()
        if "resources" in steps:
            self.step_resources(files if files is not None else self.file_list())
        if "time" in steps:
            self.step_time()
        if "helpers" in steps:
            self.step_helpers()
        if "dashboard" in steps:
            self.step_dashboard()
        if self.report.restart:
            if self.restart():
                print("\nrunning the steps again after the restart:")
                self.report = Report()
                return self.run(only)
        failed = self.report.failed
        if failed:
            print(f"\n{len(failed)} step(s) need attention (see above).")
            return 1
        print("\nAll set." + ("" if not self.fix else " Next: lcars deploy"))
        return 0


def run(path, fix, args, only=None):
    raw = read_yaml(path)
    s = Setup(raw, fix, yes=getattr(args, "yes", False))
    code = s.run(only)
    if code == 0 and not fix and not only:
        code = check_config(path, s)
    return code


def check_config(path, setup):
    """doctor: the configuration builds, and every entity it names exists."""
    from .build import build
    from .config import load
    print("\nChecking the configuration")
    try:
        site = load(path, ha=setup.ha)
        config = build(site)
    except Exception as e:
        print(f" ✗ config      {e}")
        return 1
    from .build import missing_entities
    missing, total = missing_entities(site, config)
    n = sum(len(s.views) for s in site.sections)
    print(f" ✓ config      {n} views build")
    if missing:
        print(f" ! entities    {len(missing)} of {total} don't exist in HA: {', '.join(missing)}")
        return 1
    print(f" ✓ entities    all {total} exist")
    return 0


# ── lcars init ─────────────────────────────────────────────────────────────────
def init(directory, args):
    """Write a starting lcars.yaml for the HA it finds: OPS (weather, radar where DWD covers it, the next
    days of the calendars), a month calendar, a media player; entities taken from HA."""
    from .ha import Client
    path = os.path.join(directory, "lcars.yaml")
    if os.path.exists(path):
        print(f"{path} exists already: not overwritten")
        return 1
    url = args.url or os.environ.get("HA_URL") or "http://homeassistant.local:8123"
    cfg = {"url": url}
    try:
        ha = Client(url, ha_token(cfg))
    except Exception as e:
        print(f"error: {e}\n(lcars init --url http://<your HA>:8123, token in HA_TOKEN or "
              "~/.config/homeassistant/token)")
        return 1
    states = ha.result({"type": "get_states"})
    conf = ha.result({"type": "get_config"})
    by_domain = {}
    for s in states:
        if s["state"] in ("unavailable", "unknown") and s["entity_id"].split(".")[0] != "sensor":
            continue
        by_domain.setdefault(s["entity_id"].split(".")[0], []).append(s)
    text = starter_config(url, conf, by_domain)
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {path}. Next: lcars setup, then lcars deploy")
    return 0


def starter_config(url, conf, by_domain):
    weather = (by_domain.get("weather") or [{}])[0].get("entity_id")
    cals = [s["entity_id"] for s in by_domain.get("calendar", [])][:8]
    players = [s for s in by_domain.get("media_player", []) if s["attributes"].get("supported_features", 0) & 131072]
    player = (players or by_domain.get("media_player") or [{}])[0].get("entity_id")
    lat, lon = conf.get("latitude"), conf.get("longitude")
    in_germany = lat is not None and 47.2 <= lat <= 55.1 and 5.8 <= lon <= 15.1
    names = {s["entity_id"]: s["attributes"].get("friendly_name") or s["entity_id"].split(".", 1)[1]
             for ss in by_domain.values() for s in ss}
    power = [s["entity_id"] for s in by_domain.get("sensor", []) if s["attributes"].get("device_class") == "power"
             and s["state"] not in ("unavailable", "unknown")][:4]
    doc = {
        "homeassistant": {"url": url, "token_file": "~/.config/homeassistant/token",
                          "files": {"method": "ssh", "login": "root@" + (re.sub(r"^https?://|:\d+$", "", url) or "homeassistant.local")}},
        "dashboard": {"url_path": "lcars-bridge", "title": "LCARS"},
        "layout": {"scroll": "auto"},
    }
    if weather:
        doc["weather"] = weather
    if in_germany:
        doc["radar"] = {"home": [round(lat, 2), round(lon, 2)], "width_km": 170}
    if cals:
        doc["calendars"] = [{"entity": c, "label": names.get(c, c)} for c in cals]
    sections = []
    if weather:
        rows = [
            {"label": "Temperature", "entity": weather, "value": {"attribute": "temperature", "unit": "°C"},
             "bar": {"mode": "level", "attribute": "temperature", "min": -10, "max": 35}},
            {"label": "Humidity", "entity": weather, "value": {"attribute": "humidity", "unit": "%", "round": 0},
             "bar": {"mode": "level", "attribute": "humidity", "min": 0, "max": 100}},
            {"label": "Pressure", "entity": weather, "value": {"attribute": "pressure", "unit": "hPa", "round": 0},
             "bar": {"mode": "level", "attribute": "pressure", "min": 970, "max": 1050}},
        ]
        if "sun.sun" in {s["entity_id"] for s in by_domain.get("sun", [])}:
            rows.append({"label": "Daylight", "entity": "sun.sun", "value": {"span": ["next_rising", "next_setting"]},
                         "bar": {"mode": "span", "start": "next_rising", "end": "next_setting"}})
        left = {"type": "stack", "items": [
            {"type": "rows", "rows": rows},
            {"type": "section", "title": "Forecast", "colour": "lilac",
             "content": {"type": "forecast", "labels": ["violet", "lilac"], "min_rows": 6}}]}
        top = {"type": "columns", "items": [left, {"type": "radar", "controls": "none"}]} if in_germany else left
        content = top
        if cals:
            content = {"type": "split", "colour": "lilac", "top": top,
                       "bottom": {"type": "frame", "title": "Next 7 days", "colour": "bluey", "bottom": False,
                                  "show_from": 1, "content": {"type": "week", "rows": {1: 1, 3: 2, 4: 3}}}}
        view = {"key": "ops", "label": "OPS", "subtitle": "Habitat overview", "content": content}
        if in_germany:
            view["columns"] = ["1.5fr", "1fr"]
            view["bar"] = [{"title": "Atmosphere", "colour": "orange"},
                           {"title": "Radar", "colour": "almond", "side": "right",
                            "buttons": {"type": "radar", "controls": "row"}}]
        else:
            view["bar"] = [{"title": "Atmosphere", "colour": "orange"}]
        sections.append({"key": "ops", "label": "OPS", "title": "Operations", "readouts": [
            {"type": "readout", "entity": weather, "label": "Outside",
             "value": {"attribute": "temperature", "unit": "°C"}, "colour": "ice"},
            "numbers", "decor"], "views": [view]})
    if power:
        sections.append({"key": "power", "label": "Power", "readouts": ["numbers", "decor"], "views": [{
            "key": "power", "label": "Power", "subtitle": "Power distribution",
            "bar": [{"title": "Power grid", "colour": "orange"}],
            "content": {"type": "stack", "items": [
                {"type": "rows", "rows": [{"label": names[e][:18], "entity": e,
                                           "bar": {"mode": "level", "min": 0, "max": 2000}} for e in power]},
                {"type": "section", "title": "Power trace", "colour": "lilac", "height": {"timeline": 5},
                 "content": {"type": "history", "entity": power[0], "buttons": ["violet", "lilac", "peri"],
                             "filler": "lilac"}}]}}]})
    if cals:
        sections.append({"key": "calendar", "label": "Calendar", "short": "Cal", "readouts": [
            {"type": "next_event", "label": "Next event", "show": "title"},
            {"type": "next_event", "label": "When", "show": "when", "colour": "peach"},
            {"type": "next_event", "label": "Today", "show": "today", "colour": "ice"},
            {"type": "readout", "entity": "sensor.time", "label": "Local time"}],
            "views": [{"key": "calendar", "label": "Calendar", "subtitle": "Stardate calendar",
                       "bar": [{"title": "Calendar", "colour": "orange", "buttons": {"type": "month", "mode": "controls"},
                                "buttons_max": 330}],
                       "right": {"colour": "almond", "width": "label"},
                       "content": {"type": "month"}}]})
    if player:
        sections.append({"key": "media", "label": "Media", "readouts": [
            {"type": "readout", "entity": player, "label": "Audio",
             "value": {"map": {"playing": "Playing", "paused": "Paused", "idle": "Standby", "off": "Off"}},
             "colour": {"playing": "ice", "paused": "sunflower", "default": "gray"}},
            {"type": "readout", "entity": player, "label": "Output",
             "value": "[[[ return entity.attributes.source || '—'; ]]]"}, "numbers", "decor"],
            "views": [{"key": "media", "label": "Player", "subtitle": "Audio playback",
                       "columns": ["1.1fr", 160, "1fr"],
                       "bar": [{"title": "Now playing", "colour": "orange", "span": 2,
                                "buttons": {"type": "player", "entity": player, "part": "transport"}},
                               {"title": "Library", "colour": "almond", "side": "right"}],
                       "right": {"colour": "almond", "width": "label"},
                       "content": {"type": "columns", "items": [
                           {"type": "player", "entity": player, "part": "now", "margin": "0 0 8px 0"},
                           {"type": "player", "entity": player, "part": "devices"},
                           {"type": "library", "entity": player, "categories": [
                               {"match": "", "label": "Library", "colour": "peach"}]}]}}]})
    if not sections:
        sections.append({"key": "home", "label": "Home", "views": [{
            "key": "home", "label": "Home", "subtitle": "Status",
            "content": {"type": "rows", "rows": [{"label": "Time", "entity": "sensor.time"}]}}]})
    doc["sections"] = sections
    head = ("# LCARS dashboard configuration, written by `lcars init` from what Home Assistant has.\n"
            "# Reference: docs/CONFIGURATION.md and docs/COMPONENTS.md of the lcars package.\n"
            "# homeassistant.files: how lcars setup copies the cards and the theme to HA (ssh, local or none).\n\n")
    return head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110)
