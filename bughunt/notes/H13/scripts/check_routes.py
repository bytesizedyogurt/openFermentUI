"""H13: every "METHOD /api/..." or bare `/api/...` a document names, checked against openapi.json.

Usage: python check_routes.py ROOT DOC [DOC ...]
A route matches when its method (if named) and its path template match an operation, where a
document's {placeholder} or <placeholder> matches any {param}, and a query string is dropped.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROUTE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)?\s*`?(/(?:api|rag)/[A-Za-z0-9_\-/{}<>.:]*)")


def norm(p: str) -> str:
    p = p.split("?")[0].rstrip(".,;:)`")
    p = re.sub(r"\{[^}]*\}|<[^>]*>|:[A-Za-z_]+", "{}", p)
    return p.rstrip("/") or "/"


def main(argv: list[str]) -> int:
    root = Path(argv[1])
    spec = json.loads((root / "docs/api/openapi.json").read_text())
    ops: dict[str, set[str]] = {}
    for path, item in spec["paths"].items():
        ops.setdefault(norm(path), set()).update(m.upper() for m in item)
    bad = 0
    for d in argv[2:]:
        for n, line in enumerate((root / d).read_text(encoding="utf-8").splitlines(), 1):
            for m in ROUTE.finditer(line):
                method, path = m.group(1), m.group(2)
                if path.startswith("/rag"):
                    continue  # the kit's REST, mounted; not in openFerment's document
                key = norm(path)
                hit = ops.get(key)
                if hit is None:
                    # a prefix the doc names as a family (e.g. /api/engines/...)
                    if any(k.startswith(key + "/") for k in ops) and not method:
                        continue
                    print(f"{d}:{n}: no operation for {method or ''} {path}")
                    bad += 1
                elif method and method not in hit:
                    print(f"{d}:{n}: {path} has {sorted(hit)}, the doc names {method}")
                    bad += 1
    print(f"{bad} unmatched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
