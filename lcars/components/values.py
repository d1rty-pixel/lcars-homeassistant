"""How a value is shown: LCARdS text templates written for the common cases.

A value in the configuration is either a template string, passed on as is ("{entity.state}", or JavaScript
in "[[[ ... ]]]" with `entity`, `states` and `hass`), or one of these mappings:

    {attribute: temperature, unit: "°C", round: 0}   an attribute (rounded to `round` decimals if given)
    {state: true, unit: "W"}                          the state with a unit
    {map: {on: Online, off: Offline}}                 the state (or `attribute`) through a map; others as is
    {on_off: [Open, Closed]}                          'on' -> the first, anything else -> the second
    {above: 3, then: Running, else: Idle}             a number compared with a threshold
    {date: state}  / {date: next_due}                 a date ("yyyy-mm-dd..." or "dd.mm.yyyy") as
                                                      "Fri 25/09 · tomorrow"; weekday: false leaves it out
    {time: next_setting}                              a timestamp as "hh:mm"
    {span: [next_rising, next_setting]}               two timestamps as "hh:mm – hh:mm"
    {js: "return entity.state;"}                      JavaScript statements
"""
import json

from .base import ConfigError

# JS: relative-day wording for a Date `d` (uppercase via text_transform)
REL = ("const t0 = new Date(); t0.setHours(0,0,0,0); const d0 = new Date(d); d0.setHours(0,0,0,0); "
       "const n = Math.round((d0 - t0) / 86400000); "
       "const rel = n === 0 ? 'today' : n === 1 ? 'tomorrow' : n < 0 ? 'past' : 'in ' + n + ' days'; "
       "const wd = d.toLocaleDateString('en-GB', {weekday: 'short'}); "
       "const dm = d.toLocaleDateString('en-GB', {day: '2-digit', month: '2-digit'}); ")
JS_HHMM = "const hhmm = (t) => new Date(t).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); "
JS_COMPASS = ("const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']; "
              "const compass = (b) => dirs[Math.round(b / 22.5) % 16]; ")
# JS: a Date from "yyyy-mm-dd[...]" or "dd.mm.yyyy" (as waste collection and similar sensors report it)
JS_PARSE_DATE = ("const parse = (v) => { const s = String(v); let m = s.match(/(\\d{4})-(\\d\\d)-(\\d\\d)/); "
                 "if (m) return new Date(+m[1], +m[2] - 1, +m[3]); m = s.match(/(\\d\\d)\\.(\\d\\d)\\.(\\d{4})/); "
                 "return m ? new Date(+m[3], +m[2] - 1, +m[1]) : null; }; ")


def js_map(names, source="entity.state", fallback=None):
    """JS: `source` through a map of names; others as they are."""
    return (f"[[[ const m = {json.dumps(names, ensure_ascii=False)}; const v = {source}; "
            f"return (v in m) ? m[v] : {fallback or 'v'}; ]]]")


def attr(name):
    return f"entity.attributes[{json.dumps(name)}]" if not name.isidentifier() else f"entity.attributes.{name}"


def source(spec):
    """JS for a value's source: 'state' or an attribute name."""
    return "entity.state" if spec in (None, True, "state") else attr(spec)


def value_js(spec, where):
    """The LCARdS template for a value spec (see the module docstring)."""
    if spec is None:
        return "{entity.state}"
    if isinstance(spec, (int, float)):
        return str(spec)
    if isinstance(spec, str):
        return spec
    if not isinstance(spec, dict):
        raise ConfigError(f"{where}: expected a template string or a value mapping, got {spec!r}")
    unit = f" + ' {spec['unit']}'" if spec.get("unit") else ""
    if "js" in spec:
        return "[[[ " + spec["js"].strip() + " ]]]"
    if "map" in spec:
        names = {str(k): str(v) for k, v in spec["map"].items()}
        return js_map(names, source(spec.get("attribute")))
    if "on_off" in spec:
        on, off = spec["on_off"]
        return f"[[[ return {source(spec.get('attribute'))} === 'on' ? {json.dumps(on)} : {json.dumps(off)}; ]]]"
    if "above" in spec:
        return (f"[[[ return parseFloat({source(spec.get('attribute'))}) > {spec['above']} ? "
                f"{json.dumps(spec.get('then', 'On'))} : {json.dumps(spec.get('else', 'Off'))}; ]]]")
    if "date" in spec:
        wd = "wd + ' ' + " if spec.get("weekday", True) else ""
        return ("[[[ " + JS_PARSE_DATE + f"const d = parse({source(spec['date'])}); if (!d) return '–'; " + REL
                + f"return {wd}dm + ' · ' + rel; ]]]")
    if "time" in spec:
        return "[[[ " + JS_HHMM + f"const t = {source(spec['time'])}; return t ? hhmm(t) : '–'; ]]]"
    if "span" in spec:
        a, b = spec["span"]
        return "[[[ " + JS_HHMM + f"return hhmm({source(a)}) + ' – ' + hhmm({source(b)}); ]]]"
    if "attribute" in spec or "state" in spec:
        v = source(spec.get("attribute", "state"))
        if "round" in spec:
            n = int(spec["round"])
            v = f"Math.round({v})" if n == 0 else f"Number({v}).toFixed({n})"
        return f"[[[ return {v}{unit}; ]]]"
    raise ConfigError(f"{where}: unknown value mapping {spec!r} (see docs/COMPONENTS.md 'Values')")
