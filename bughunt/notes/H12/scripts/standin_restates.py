"""List each test function that leans on core/tests/standins.py, with every assert in it, marking each assert
that compares against a value standins.py itself makes (one of its exported names, or a literal its source
holds: a unit id, a stream count, a label, a number). A test whose every assert is so marked restates the
stand-in: it passes whatever the code under test does with the value, as long as it passes it through.

    python3 standin_restates.py /path/to/core/tests > restates.txt
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

tests = Path(sys.argv[1])
src = (tests / "standins.py").read_text()
tree = ast.parse(src)
EXPORTED = {n.targets[0].id for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
LITERALS = set()
DISTINCT_IDS = {"R1", "D1", "M1", "D302", "U301", "Q999", "s-cerevisiae-cenpk113-7d", "dep-standin-ethanol"}
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float)) and not isinstance(node.value, bool):
        v = node.value
        # Distinctive values alone: the stand-in's own labels, unit and stream ids, paper and strain ids, and
        # numbers no test would reach for by chance (three significant digits, or a hundred and more).
        if isinstance(v, str):
            if ("STAND-IN" in v or "standin" in v.lower() or v in DISTINCT_IDS) and len(v) <= 200:
                LITERALS.add(v)
        elif isinstance(v, float) and (abs(v) >= 100 or len(repr(v).strip("0.-").replace(".", "")) >= 3):
            LITERALS.add(v)


def uses_standins(fn: ast.AST, text: str) -> bool:
    seg = ast.get_source_segment(text, fn) or ""
    return "standins" in seg or "_standin" in seg or "standin" in seg


def restating(a: ast.Assert) -> bool:
    for node in ast.walk(a.test):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "standins" \
                and node.attr in EXPORTED:
            return True
        if isinstance(node, ast.Name) and node.id in EXPORTED:
            return True
        if isinstance(node, ast.Constant) and node.value in LITERALS and not isinstance(node.value, bool):
            return True
    return False


for path in sorted(tests.glob("test_*.py")):
    text = path.read_text()
    if "standin" not in text:
        continue
    mod = ast.parse(text)
    for fn in [n for n in ast.walk(mod) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
        if not uses_standins(fn, text):
            continue
        asserts = [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]
        if not asserts:
            continue
        marks = [restating(a) for a in asserts]
        tag = "ALL" if all(marks) else ("SOME" if any(marks) else "none")
        print(f"{tag:4} {path.name}::{fn.name} ({sum(marks)}/{len(asserts)})")
        for a, mk in zip(asserts, marks):
            if mk:
                print(f"       L{a.lineno}: {ast.get_source_segment(text, a)[:160]}")
