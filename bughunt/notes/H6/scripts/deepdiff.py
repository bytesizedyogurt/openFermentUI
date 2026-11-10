"""deepdiff.py MAIN.json HEAD.json: every read both answered 200, compared value by value, listing each path
whose value alpha 2.1 answered and the head answers differently or leaves out (keys the head adds are not
listed). Volatile paths (times a read stamps, worker status) are named as they are found."""
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
def walk(x, y, path, out):
    if isinstance(x, dict):
        if not isinstance(y, dict):
            out.append((path, "type", str(x)[:80], str(y)[:80])); return
        for k, v in x.items():
            if k not in y:
                if v not in (None, [], {}, ""):
                    out.append((f"{path}.{k}", "gone", str(v)[:80], None))
            else:
                walk(v, y[k], f"{path}.{k}", out)
    elif isinstance(x, list):
        if not isinstance(y, list) or len(x) != len(y):
            out.append((path, "len", len(x), len(y) if isinstance(y, list) else type(y).__name__)); return
        for i, (p, q) in enumerate(zip(x, y)):
            walk(p, q, f"{path}[{i}]", out)
    else:
        if x != y and not (isinstance(x, (int, float)) and isinstance(y, (int, float)) and float(x) == float(y)):
            out.append((path, "value", str(x)[:80], str(y)[:80]))
for key in sorted(set(a) & set(b)):
    if a[key]["status"] != 200 or b[key]["status"] != 200:
        continue
    out = []
    walk(a[key]["body"], b[key]["body"], "", out)
    if out:
        print(f"{key}: {len(out)}")
        for o in out[:6]:
            print("   ", o)
