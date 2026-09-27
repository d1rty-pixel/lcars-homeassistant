"""lcars: build and install an LCARS dashboard for Home Assistant.

    lcars init [dir]          write a starting configuration (lcars.yaml)
    lcars doctor              check Home Assistant and the configuration, change nothing
    lcars setup               install and set up what the dashboard needs in Home Assistant
    lcars files               copy the cards and the theme to Home Assistant (after an update)
    lcars build               build the dashboard (build/lcars_dashboard.json)
    lcars deploy              build, validate, back up the live dashboard, save
    lcars restore FILE        save a backup (or any built config) as the dashboard
    lcars diag                add a view that shows what a device's browser reports about its screen

Options: -c/--config FILE (default ./lcars.yaml, or $LCARS_CONFIG), --dashboard URL_PATH (a test copy).
"""
import argparse
import json
import os
import sys
import time

from .components.base import ConfigError


def config_path(args):
    return args.config or os.environ.get("LCARS_CONFIG") or "lcars.yaml"


def build_dir(args):
    return os.path.join(os.path.dirname(os.path.abspath(config_path(args))), "build")


def load_site(args):
    from .config import load
    if args.dashboard:
        os.environ["LCARS_DASHBOARD"] = args.dashboard
    return load(config_path(args))


def cmd_build(args):
    from .build import build
    site = load_site(args)
    config = build(site)
    out = args.output or os.path.join(build_dir(args), "lcars_dashboard.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=1, ensure_ascii=False, default=str)
    n = sum(1 for _ in config["views"])
    print(f"{out}: {n} views, {os.path.getsize(out)} bytes")
    try:
        from .build import missing_entities
        missing, total = missing_entities(site, config)
        if missing:
            print(f"warning: {len(missing)} of {total} entities don't exist in Home Assistant (their values show "
                  f"as raw templates): {', '.join(missing)}")
    except Exception as e:      # no connection: the build itself doesn't need one for every configuration
        print(f"(entities not checked: {e})")
    return site, config, out


def save(site, config, url_path, backups):
    ha = site.ha()
    live = ha.call({"type": "lovelace/config", "url_path": url_path})
    if live["success"]:
        os.makedirs(backups, exist_ok=True)
        path = os.path.join(backups, f"{url_path}-{time.strftime('%Y%m%d-%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(live["result"], f, indent=1, ensure_ascii=False)
        print("backup:", path)
    ha.result({"type": "lovelace/config/save", "url_path": url_path, "config": config})
    print(f"saved to /{url_path}")


def cmd_deploy(args):
    from .validate import validate
    site, config, out = cmd_build(args)
    problems = validate(json.loads(json.dumps(config, default=str)))
    if problems:
        for p in problems[:40]:
            print(p)
        print(f"{len(problems)} problem(s): not deployed")
        return 1
    save(site, json.loads(json.dumps(config, default=str)), site.url_path, os.path.join(build_dir(args), "backups"))
    return 0


def cmd_restore(args):
    site = load_site(args)
    with open(args.file, encoding="utf-8") as f:
        config = json.load(f)
    save(site, config, site.url_path, os.path.join(build_dir(args), "backups"))
    return 0


def cmd_doctor(args):
    from .setup import run
    return run(config_path(args), fix=False, args=args)


def cmd_setup(args):
    from .setup import run
    return run(config_path(args), fix=True, args=args)


def cmd_files(args):
    from .setup import run
    return run(config_path(args), fix=True, args=args, only=("files", "resources", "themes"))


def cmd_diag(args):
    from .diag import add_view
    add_view(load_site(args))
    return 0


def cmd_init(args):
    from .setup import init
    return init(args.dir or ".", args)


def main(argv=None):
    p = argparse.ArgumentParser(prog="lcars", description=__doc__.split("\n", 1)[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n", 2)[2])
    p.add_argument("-c", "--config", help="the site configuration (default ./lcars.yaml)")
    p.add_argument("--dashboard", help="build for / save to this dashboard instead (e.g. a test copy)")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build the dashboard")
    b.add_argument("-o", "--output")
    d = sub.add_parser("deploy", help="build, validate, back up and save")
    d.add_argument("-o", "--output")
    r = sub.add_parser("restore", help="save a backup as the dashboard")
    r.add_argument("file")
    sub.add_parser("doctor", help="check everything, change nothing")
    s = sub.add_parser("setup", help="install and set up what the dashboard needs")
    s.add_argument("-y", "--yes", action="store_true", help="don't ask before restarting Home Assistant")
    sub.add_parser("files", help="copy the cards and the theme to Home Assistant")
    sub.add_parser("diag", help="add a diagnostic view (viewport, safe areas) to the dashboard")
    i = sub.add_parser("init", help="write a starting configuration")
    i.add_argument("dir", nargs="?")
    i.add_argument("--url", help="Home Assistant's URL")
    args = p.parse_args(argv)
    args.yes = getattr(args, "yes", False)
    try:
        r = {"build": lambda a: (cmd_build(a), 0)[1], "deploy": cmd_deploy, "restore": cmd_restore,
             "doctor": cmd_doctor, "setup": cmd_setup, "files": cmd_files, "init": cmd_init,
             "diag": cmd_diag}[args.cmd](args)
        return r or 0
    except ConfigError as e:
        print(f"configuration: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as e:     # errors from HA or the host: one line, not a traceback
        if os.environ.get("LCARS_DEBUG"):
            raise
        print(f"error: {e}", file=sys.stderr)
        return 1
