"""Make every script in ha/www/ a Lovelace module resource (created if missing) with ?v=<unix timestamp>,
so browsers fetch the version just deployed. Run by tools/deploy_ha_files.sh after copying the files."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "generator"))
import ha_ws  # noqa: E402

WWW = os.path.join(HERE, "..", "ha", "www")


def main():
    stamp = int(time.time())
    names = {f for f in os.listdir(WWW) if f.endswith(".js")}
    c = ha_ws.Client()
    seen = set()
    for res in c.call({"type": "lovelace/resources"})["result"]:
        path = res["url"].split("?")[0]
        if path.startswith("/local/") and path[len("/local/"):] in names:
            seen.add(path[len("/local/"):])
            url = f"{path}?v={stamp}"
            ok = c.call({"type": "lovelace/resources/update", "resource_id": res["id"],
                         "res_type": res["type"], "url": url})["success"]
            print(url, "ok" if ok else "FAILED")
    for name in sorted(names - seen):
        url = f"/local/{name}?v={stamp}"
        ok = c.call({"type": "lovelace/resources/create", "res_type": "module", "url": url})["success"]
        print(url, "created" if ok else "FAILED")


if __name__ == "__main__":
    main()
