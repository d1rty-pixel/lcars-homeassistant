"""Validate build/lcars_dashboard.json against the official LCARdS JSON schema.

Two passes per LCARdS card:
  1. jsonschema types/enums (the schema's known generator bug `enum: []` is ignored)
  2. strict unknown-key check (the schema has no additionalProperties:false,
     so invented keys would otherwise pass silently)

Exit code 1 on any finding.
"""
import json
import os
import sys
import urllib.request

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCHEMA_URL = "https://lcards.unimatrix01.ca/lcards-schema.json"
SCHEMA_CACHE = os.path.join(ROOT, "build", "lcards-schema.json")
CONTAINER_KEYS = {"view_layout", "uix", "visibility", "card_mod"}


def load_schemas():
    if not os.path.exists(SCHEMA_CACHE):
        os.makedirs(os.path.dirname(SCHEMA_CACHE), exist_ok=True)
        urllib.request.urlretrieve(SCHEMA_URL, SCHEMA_CACHE)
    raw = json.load(open(SCHEMA_CACHE))
    defs = raw["$defs"]

    def res(x, depth=0):
        # the generator hoists even list values (oneOf, properties) behind $ref, so resolve inline
        if depth > 60:
            return {}
        if isinstance(x, dict):
            if set(x) == {"$ref"} and x["$ref"].startswith("#/$defs/"):
                return res(defs[x["$ref"].split("/")[-1]], depth + 1)
            return {k: res(v, depth + 1) for k, v in x.items()}
        if isinstance(x, list):
            return [res(v, depth + 1) for v in x]
        return x

    schemas = {k: res(v) for k, v in raw["cards"].items()}
    # Schema gap: every card inherits `sounds` from LCARdSCard (runtime reads config.sounds
    # in src/base/LCARdSCard.js), but only the slider schema declares it.
    sounds = schemas["lcards-slider"]["properties"].get("sounds")
    for card in schemas.values():
        if sounds and "properties" in card and "sounds" not in card["properties"]:
            card["properties"]["sounds"] = sounds
    # Schema gap: processors declare only `type`/`from`, but the expression processor
    # reads `expression` and `sources` (src/core/data-sources/processors/ExpressionProcessor.js).
    for card in schemas.values():
        ds = card.get("properties", {}).get("data_sources", {}).get("additionalProperties", {})
        proc = ds.get("properties", {}).get("processing", {}).get("additionalProperties", {})
        if isinstance(proc.get("properties"), dict):
            proc["properties"].setdefault("expression", {"type": "string"})
            proc["properties"].setdefault("sources", {"type": "array", "items": {"type": "string"}})
    return schemas


def subschemas(sc):
    out = [sc]
    for k in ("oneOf", "anyOf", "allOf"):
        if isinstance(sc.get(k), list):
            for x in sc[k]:
                out += subschemas(x)
    return out


def unknown_keys(inst, sc, path, found):
    if isinstance(inst, list):
        for i, x in enumerate(inst):
            for s2 in subschemas(sc):
                if isinstance(s2.get("items"), dict):
                    unknown_keys(x, s2["items"], path + [i], found)
        return
    if not isinstance(inst, dict):
        return
    cands = [s2 for s2 in subschemas(sc) if isinstance(s2, dict)
             and (s2.get("properties") or s2.get("additionalProperties") or s2.get("patternProperties"))]
    if not cands:
        return
    props, loose = {}, False
    for s2 in cands:
        if isinstance(s2.get("properties"), dict):
            props.update(s2["properties"])
        if s2.get("additionalProperties") not in (None, False) or s2.get("patternProperties"):
            loose = True
    for k, v in inst.items():
        if k in props:
            unknown_keys(v, props[k], path + [k], found)
        elif not loose:
            found.append(".".join(map(str, path + [k])))
        else:
            for s2 in cands:
                if isinstance(s2.get("additionalProperties"), dict):
                    unknown_keys(v, s2["additionalProperties"], path + [k], found)


def walk(card):
    yield card
    if isinstance(card.get("card"), dict):
        yield from walk(card["card"])
    for c in card.get("cards", []):
        yield from walk(c)


def main(path):
    schemas = load_schemas()
    cfg = json.load(open(path))
    problems, checked = [], 0
    for view in cfg["views"]:
        for top in view["cards"]:
            for c in walk(top):
                t = c.get("type", "").replace("custom:", "")
                if t not in schemas:
                    continue
                checked += 1
                inst = {k: v for k, v in c.items() if k not in CONTAINER_KEYS and k != "cards"}
                where = f"{view['path']}:{t}:{c.get('entity', '')}"
                for e in jsonschema.Draft7Validator(schemas[t]).iter_errors(inst):
                    if "is not one of []" in e.message:  # known schema generator bug
                        continue
                    # Schema gap: colour patterns reject JS templates, but buttons pre-evaluate every
                    # template string under `style` (_preEvaluateStyleTemplates in LCARdSButton).
                    if (list(e.absolute_path)[:1] == ["style"] and isinstance(e.instance, str)
                            and e.instance.startswith("[[[")):
                        continue
                    problems.append(f"{where} {list(e.absolute_path)} {e.message[:160]}")
                found = []
                unknown_keys(inst, schemas[t], [], found)
                problems += [f"{where} UNKNOWN KEY {k}" for k in found]
    for p in sorted(set(problems)):
        print(p)
    print(f"checked {checked} LCARdS cards, {len(set(problems))} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "lcars_dashboard.json")))
