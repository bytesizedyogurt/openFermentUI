"""A runbook lock's digest, as the browser writes it (src/engine/lock.ts).

A lock freezes a runbook's predictions and measures under a digest of
them, so a later reader can tell whether what they read is what was frozen
(OF-BLD-006 §3.3). The browser computes it in `runbookLockHash`; the
service computes the same digest here, over the row as the project keeps
it, so a runbook the service locks reads as intact on the runbook's page
and a row sent after a lock can be checked against it (project_state.py).
test_runbook_lock.py holds this port to digests the browser's own code
wrote (`pnpm export:lock-fixtures`).

The digest is FNV-1a, 32 bits, twice: over the canonical text from offset
2166136261, and over the text with its length appended from 2166136243,
each pass over the text's UTF-16 code units as JavaScript reads a string.
The canonical text is `JSON.stringify({p, m})` of fixed-order arrays, so
a number is written as JavaScript writes it (`js_number`) and a string as
JSON.stringify escapes it. It is a content digest, not a signature
(lock.ts says what it is and is not).
"""
from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

# FNV-1a, 32 bits: lock.ts's two offsets and the prime.
OFFSET, OFFSET_2, PRIME = 2166136261, 2166136243, 16777619
# A prediction's fields the canonical form appends only when one of them is
# present (OF-BLD-014 §9.1): a point with none serialises as it did before.
OPTIONAL = ("kind", "interval", "artifactId", "recordIds")


def js_number(x: float | int) -> str:
    """A number as JavaScript writes it in JSON (ECMAScript
    Number::toString, the shortest digits that read back as the number):
    an integral value with no point, an exponent from 1e21 up and below
    1e-6, negative zero as 0, a number that is not finite as null."""
    if isinstance(x, bool):
        raise TypeError("a lock digest reads no true or false as a number")
    if isinstance(x, int) and abs(x) < 2 ** 53:
        return str(x)
    x = float(x)
    if not math.isfinite(x):
        return "null"
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    d = Decimal(repr(abs(x))).normalize().as_tuple()
    digits = "".join(map(str, d.digits))
    k, n = len(digits), len(digits) + d.exponent
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * -n + digits
    e = n - 1
    return f"{sign}{digits[0]}{'.' + digits[1:] if k > 1 else ''}e{'+' if e >= 0 else '-'}{abs(e)}"


def _js(value: Any) -> str:
    """A JSON value as JavaScript's JSON.stringify writes it."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return js_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_js(v) for v in value) + "]"
    raise TypeError(f"a lock digest reads no {type(value).__name__}")


def canonical(predictions: list[dict[str, Any]], schema: list[dict[str, Any]]) -> str:
    """lock.ts's canonical text over the predictions and measures as the
    row keeps them. A field the row leaves out and a field it keeps as null
    differ where lock.ts tells `undefined` from `null` (the optional four);
    elsewhere a field left out is written null, as JSON.stringify writes
    `undefined` inside an array."""
    p = []
    for x in predictions:
        base = [x.get(k) for k in ("id", "label", "value", "unit", "confidence", "basis")]
        if all(k not in x for k in OPTIONAL):
            p.append(base)
            continue
        interval = x.get("interval")
        p.append([*base, x.get("kind"), [interval.get("low"), interval.get("high")] if interval is not None else None,
                  x.get("artifactId"), x.get("recordIds")])
    m = [[x.get(k) for k in ("id", "label", "unit", "timepoint", "predictionId")] for x in schema]
    return '{"p":' + _js(p) + ',"m":' + _js(m) + "}"


def _units(text: str) -> list[int]:
    """The text's UTF-16 code units, which a JavaScript string is made of."""
    raw = text.encode("utf-16-le")
    return [raw[i] | raw[i + 1] << 8 for i in range(0, len(raw), 2)]


def _fnv1a(units: list[int], seed: int) -> int:
    h = seed
    for u in units:
        h = ((h ^ u) * PRIME) & 0xFFFFFFFF
    return h


def lock_hash(predictions: list[dict[str, Any]], schema: list[dict[str, Any]]) -> str:
    """lock.ts's `runbookLockHash`: sixteen hex digits."""
    units = _units(canonical(predictions, schema))
    a = _fnv1a(units, OFFSET)
    b = _fnv1a(units + _units(str(len(units))), OFFSET_2)
    return f"{a:08x}{b:08x}"


def frozen_as(row: dict[str, Any], digest: str) -> bool:
    """Whether a runbook row's predictions and measures are the ones a lock
    froze under `digest`; a row they cannot be read from is not."""
    try:
        return lock_hash(row.get("predictions") or [], row.get("measurementSchema") or []) == digest
    except (KeyError, TypeError, AttributeError):
        return False
