"""H12-09 scan: every Host a test in core/tests sends that the guard on the head refuses.

Reads the test files by ast: a string under a "host"/"Host" key in a dict literal, a host= keyword,
and the host of a base_url= keyword. A strain's host field is a name with no dot, which the guard
answers to, so it never lands among the refused. Prints SCAN lines alone.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from urllib.parse import urlsplit

from openferment_core import guard

tests = Path(sys.argv[1])
refused, net = [], []
for path in sorted(tests.glob("test_*.py")):
    for node in ast.walk(ast.parse(path.read_text())):
        found = []
        if isinstance(node, ast.Dict):
            found = [(v, v.value) for k, v in zip(node.keys, node.values)
                     if isinstance(k, ast.Constant) and k.value in ("host", "Host")
                     and isinstance(v, ast.Constant) and isinstance(v.value, str)]
        elif isinstance(node, ast.keyword) and node.arg in ("host", "base_url") and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            v = node.value.value
            found = [(node.value, urlsplit(v).netloc if node.arg == "base_url" else v)]
        for at, value in found:
            name = guard.hostname(value)
            where = f"{path.name}:{at.lineno}"
            if name and name.endswith(".net"):
                net.append(f"{where} {value}")
            if name and not guard.answers_to(name):
                refused.append((where, value, name.rsplit(".", 1)[-1]))
refused.sort(key=lambda r: (r[0].split(':')[0], int(r[0].split(':')[1])))
for where, value, tld in refused:
    print(f"SCAN refused on the head: {where} Host {value!r} (ends .{tld})")
print(f"SCAN every Host value ending in .net: {sorted(net, key=lambda s: int(s.split(':')[1].split()[0]))}")
print(f"SCAN-REFUSED-NET {sum(1 for *_, tld in refused if tld == 'net')} of {len(refused)}")
