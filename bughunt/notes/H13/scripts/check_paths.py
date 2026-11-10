"""H13: every backticked path a document names, checked against the tree at a given root.

Usage: python check_paths.py ROOT DOC [DOC ...]
Prints one line a path that does not resolve, with the document and line it stands on.
A path is a backticked token holding a '/' or ending in a known file suffix. Paths are tried
from the root, from core/, from core/openferment_core/, from the document's own folder and
from the folder the document's own context names (examples/...).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SUFFIX = (".py", ".md", ".ts", ".tsx", ".mjs", ".json", ".toml", ".sh", ".yaml", ".yml", ".txt",
          ".lock", ".example", ".jsonl", ".sql", ".plist", ".cfg")
TICK = re.compile(r"`([^`\n]+)`")


def candidates(tok: str) -> list[str]:
    tok = tok.strip()
    tok = re.sub(r"[:#].*$", "", tok) if not tok.startswith("http") else ""
    tok = tok.split(" ")[0]
    return [tok] if tok else []


def looks_like_path(tok: str) -> bool:
    if tok.startswith(("http", "/api", "/rag", "/p/", "#/", "~", "$", "-", "<")):
        return False
    if any(c in tok for c in "()=<>*{}|,'\""):
        return False
    if "/" in tok and not tok.startswith("/"):
        return bool(re.match(r"^[A-Za-z0-9_.\-/]+$", tok))
    return tok.endswith(SUFFIX) and bool(re.match(r"^[A-Za-z0-9_.\-/]+$", tok))


def resolves(root: Path, doc: Path, tok: str) -> bool:
    bases = [root, root / "core", root / "core" / "openferment_core", doc.parent, root / "docs",
             root / "docs" / "api", root / "scripts", root / "src", root / "core" / "tests"]
    for b in bases:
        if (b / tok).exists():
            return True
        if tok.endswith("/") and (b / tok.rstrip("/")).exists():
            return True
    # a bare file name: anywhere in the tree
    if "/" not in tok:
        for p in root.rglob(tok):
            if ".venv" not in p.parts and "node_modules" not in p.parts:
                return True
    return False


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve()
    bad = 0
    for d in argv[2:]:
        doc = (root / d).resolve()
        for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for m in TICK.finditer(line):
                for tok in candidates(m.group(1)):
                    if looks_like_path(tok) and not resolves(root, doc, tok):
                        print(f"{d}:{n}: `{m.group(1)}` -> {tok}")
                        bad += 1
    print(f"{bad} unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
