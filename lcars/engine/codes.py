"""LCARS numbers and random-looking animation timings, both derived from keys so they stay put between
builds."""
import random
import zlib

_CODES = {}


def lcars_code(key):
    """Stable, unique LCARS number (NN-NNNN) for a thing, derived from its key. The same key (the same
    thing, e.g. a sidebar block shown on several views) always gets the same number, and no two keys
    share one."""
    if key not in _CODES:
        h = zlib.crc32(key.encode())
        taken = set(_CODES.values())
        while f"{10 + h % 90:02d}-{h // 90 % 10000:04d}" in taken:
            h += 1
        _CODES[key] = f"{10 + h % 90:02d}-{h // 90 % 10000:04d}"
    return _CODES[key]


def blink(key, n, lo=8000, hi=24000):
    """n flash cycles in ms (lo..hi, steps of 500) for the segments of a bar: lit segments flash white
    briefly at these random but fixed rates, so bars don't blink in step."""
    rng = random.Random(zlib.crc32(("blink/" + key).encode()))
    return [rng.randrange(lo, hi, 500) for _ in range(n)]


def reset():
    """Forget every number handed out (one build = one registry)."""
    _CODES.clear()
