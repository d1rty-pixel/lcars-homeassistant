"""Site-specific settings (HA host, location, device IDs, personal calendars) from site.yaml at the repo
root. site.yaml is not in git: copy site.example.yaml and fill it in. HA_HOST / HA_PORT / HA_SSH in the
environment override the file.

Also a tiny CLI for the shell tools:  python3 generator/site_config.py ha.ssh
"""
import os
import sys

import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site.yaml")
if not os.path.exists(PATH):
    raise SystemExit(f"missing {os.path.normpath(PATH)}: copy site.example.yaml to site.yaml and fill it in")
SITE = yaml.safe_load(open(PATH, encoding="utf-8"))

HA_HOST = os.environ.get("HA_HOST", SITE["ha"]["host"])
HA_PORT = int(os.environ.get("HA_PORT", SITE["ha"].get("port", 8123)))
HA_SSH = os.environ.get("HA_SSH", SITE["ha"]["ssh"])

if __name__ == "__main__":
    node = {"ha": {"host": HA_HOST, "port": HA_PORT, "ssh": HA_SSH}} | {k: v for k, v in SITE.items() if k != "ha"}
    for key in sys.argv[1].split("."):
        node = node[key]
    print(node)
