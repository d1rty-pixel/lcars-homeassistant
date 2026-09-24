"""Regenerate ha/www/lcards-registry-fix.js from the lcards.js currently served by HA.

Run after every LCARdS update: the workaround only re-registers tag names it
knows, so new LCARdS elements would otherwise hit the load race again.
"""
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "..", "ha", "www", "lcards-registry-fix.js")
HA = "http://" + os.environ.get("HA_HOST", "homeassistant.local") + ":8123"
CORE = ["lcards-button", "lcards-elbow", "lcards-chart", "lcards-slider", "lcards-data-grid", "lcards-msd-card",
        "lcards-alert-overlay", "lcards-select-menu", "lcards-layout-card", "lcards-layout-view"]

src = urllib.request.urlopen(HA + "/lcards/lcards.js").read().decode("utf-8", "replace")
versions = re.findall(r'"(20\d{2}\.\d{1,2}\.\d+)"', src)
version = max(set(versions), key=versions.count) if versions else "?"
tags = sorted(set(re.findall(r"customElements\.define\(['\"]([a-z0-9-]+)", src)))
missing = [t for t in CORE if t not in tags]
if missing:
    raise SystemExit(f"core tags not found in lcards.js: {missing}")

js = open(TARGET).read()
js = re.sub(r"TAGS is every name lcards\.js [^ ]+ passes", f"TAGS is every name lcards.js {version} passes", js)
js = re.sub(r"const TAGS = \[.*?\];", "const TAGS = " + json.dumps(tags) + ";", js, flags=re.S)
open(TARGET, "w").write(js)
print(f"lcards.js {version}: {len(tags)} tags written to {TARGET}")
