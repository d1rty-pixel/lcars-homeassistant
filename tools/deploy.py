"""Build, validate and save the LCARS dashboard to Home Assistant.

Snapshots the currently live config to build/backups/ first, so a bad deploy
can be reverted with:  python3 tools/deploy.py --restore build/backups/<file>.json
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "generator"))
import ha_ws  # noqa: E402

URL_PATH = "lcars-bridge"
BUILT = os.path.join(ROOT, "build", "lcars_dashboard.json")


def save(config):
    c = ha_ws.Client()
    backup_dir = os.path.join(ROOT, "build", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    live = c.call({"type": "lovelace/config", "url_path": URL_PATH})
    if live["success"]:
        path = os.path.join(backup_dir, f"{URL_PATH}-{time.strftime('%Y%m%d-%H%M%S')}.json")
        json.dump(live["result"], open(path, "w"), indent=1, ensure_ascii=False)
        print("backup:", path)
    r = c.call({"type": "lovelace/config/save", "url_path": URL_PATH, "config": config})
    print("save:", r["success"], r.get("error", ""))
    return 0 if r["success"] else 1


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--restore":
        return save(json.load(open(sys.argv[2])))
    subprocess.run([sys.executable, os.path.join(ROOT, "generator", "build_dashboard.py")], check=True)
    if subprocess.run([sys.executable, os.path.join(HERE, "validate.py"), BUILT]).returncode != 0:
        print("validation failed, not deploying")
        return 1
    return save(json.load(open(BUILT)))


if __name__ == "__main__":
    sys.exit(main())
