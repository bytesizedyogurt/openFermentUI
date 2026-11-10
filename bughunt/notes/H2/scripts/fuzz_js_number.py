"""Fuzz runbook_lock.js_number against node's JSON.stringify on many floats and ints.

    python3 fuzz_js_number.py N   (runs `node`; prints every number the two write differently)
"""
import json, random, struct, subprocess, sys
sys.path.insert(0, "/home/user/openFermentUI/core")
from openferment_core.runbook_lock import js_number

random.seed(7)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
xs = [0.0, -0.0, 1e21, 1e-7, 1e-6, 123456789012345680000.0, 5e-324, 1.7976931348623157e308, 0.1 + 0.2, 2 ** 53, 2 ** 53 + 1,
      -1e21, 9.999999999999999e20, 1e20, 100.0, 1.5e-6, 1e300, 12345678.9]
for _ in range(n):
    bits = random.getrandbits(64)
    x = struct.unpack("<d", struct.pack("<Q", bits))[0]
    if x == x and abs(x) != float("inf"):
        xs.append(x)
    xs.append(random.uniform(-1e6, 1e6))
    xs.append(round(random.uniform(0, 1e9), random.randint(0, 12)))
    xs.append(random.randint(-2 ** 60, 2 ** 60))
src = json.dumps([repr(x) if isinstance(x, float) else str(x) for x in xs])
js = "const xs = JSON.parse(require('fs').readFileSync(0,'utf8')).map(Number); process.stdout.write(JSON.stringify(xs.map(x => JSON.stringify(x))));"
out = json.loads(subprocess.run(["node", "-e", js], input=src, capture_output=True, text=True, check=True).stdout)
bad = [(x, js_number(x), o) for x, o in zip(xs, out) if js_number(x) != o]
print(len(xs), "numbers;", len(bad), "written differently")
for b in bad[:20]:
    print("  ", b)
