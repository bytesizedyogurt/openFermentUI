"""compare.py MAIN.json HEAD.json: set alpha 2.1's answers beside the head's, read for read.

For each read both services answered: a status that moved, a list whose ids moved (gained or lost), and
for a detail read the top-level keys that moved and the scalar values that changed. The head's
`GET /api/state` `refused` list is printed whole.
"""
from __future__ import annotations

import json
import sys
from typing import Any

a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))


def ident(x: Any) -> str | None:
    if isinstance(x, dict):
        for k in ("id", "artifactId", "documentId", "personId", "questionId"):
            if isinstance(x.get(k), str):
                return x[k]
    return None


def flat(x: Any, path: str = "", out: dict[str, Any] | None = None, depth: int = 0) -> dict[str, Any]:
    out = {} if out is None else out
    if depth > 3:
        return out
    if isinstance(x, dict):
        for k, v in x.items():
            flat(v, f"{path}.{k}" if path else k, out, depth + 1)
    elif isinstance(x, (str, int, float, bool)) or x is None:
        out[path] = x
    return out


for key in sorted(set(a) | set(b)):
    if key not in b:
        print(f"ONLY MAIN {key} {a[key]['status']}")
        continue
    if key not in a:
        if b[key]["status"] == 200:
            continue
        print(f"ONLY HEAD {key} {b[key]['status']}")
        continue
    sa, sb = a[key]["status"], b[key]["status"]
    if sa != sb:
        print(f"STATUS {key}: {sa} -> {sb} {str(b[key]['body'])[:240]}")
        continue
    ba, bb = a[key]["body"], b[key]["body"]
    if isinstance(ba, list) and isinstance(bb, list):
        ia = [ident(x) for x in ba]
        ib = [ident(x) for x in bb]
        lost, gained = [i for i in ia if i not in ib], [i for i in ib if i not in ia]
        if lost or gained or len(ba) != len(bb):
            print(f"LIST {key}: {len(ba)} -> {len(bb)}; lost {lost}; gained {gained}")
    elif isinstance(ba, dict) and isinstance(bb, dict):
        for k in sorted(set(ba) | set(bb)):
            va, vb = ba.get(k), bb.get(k)
            if isinstance(va, list) and isinstance(vb, list):
                ia = [ident(x) for x in va]
                ib = [ident(x) for x in vb]
                lost = [i for i in ia if i not in ib]
                if lost or len(va) != len(vb):
                    print(f"FIELD {key} .{k}: {len(va)} -> {len(vb)} items; lost {lost}")
            elif isinstance(va, dict) and isinstance(vb, dict) and k in ("records", "papers", "trains", "fits",
                                                                         "runbookLocks", "overrides"):
                lost = [x for x in va if x not in vb]
                if lost or len(va) != len(vb):
                    print(f"FIELD {key} .{k}: {len(va)} -> {len(vb)} keys; lost {lost}")
            elif k not in bb and va not in (None, [], {}):
                print(f"KEY GONE {key} .{k} (was {str(va)[:80]})")
        fa, fb = flat(ba), flat(bb)
        moved = [(p, fa[p], fb[p]) for p in fa if p in fb and fa[p] != fb[p] and not p.endswith(("At", "at"))]
        if moved:
            print(f"VALUES {key}: " + "; ".join(f"{p}: {x!r} -> {y!r}" for p, x, y in moved[:8])
                  + (f" (+{len(moved) - 8})" if len(moved) > 8 else ""))
st = b.get("/api/state", {}).get("body") or {}
print("HEAD state.refused:", json.dumps(st.get("refused"), indent=1))
