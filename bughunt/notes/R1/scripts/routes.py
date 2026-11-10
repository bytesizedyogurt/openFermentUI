"""R1: every `METHOD /api/...` docs/PROGRESS.md names (Resume to Environment facts, and the alpha 2.2 log), held to
docs/api/openapi.json at a commit (and to the app's own routes outside the schema, read from api.py's decorators).
Usage: python3 routes.py [COMMIT]"""
import json, re, subprocess, sys
REPO = "/home/user/openFermentUI"; C = sys.argv[1] if len(sys.argv) > 1 else "2047f5a"
show = lambda p: subprocess.run(["git", "-C", REPO, "show", f"{C}:{p}"], capture_output=True, text=True).stdout
spec = json.loads(show("docs/api/openapi.json"))
api = show("core/openferment_core/api.py")
declared = {(m.upper(), p) for p, ops in spec["paths"].items() for m in ops}
declared |= {(m.upper(), p) for m, p in re.findall(r'@app\.(get|post|put|delete|patch)\(\s*"([^"]+)"', api)}
def norm(p):
    p = p.split("?")[0].split("[")[0].rstrip(".,;:)")
    return re.sub(r"\{[^}]*\}", "{}", p)
known = {(m, norm(p)) for m, p in declared}
lines = show("docs/PROGRESS.md").splitlines()
for n, line in enumerate(lines, 1):
    if not (9 <= n <= 251 or 383 <= n <= 560 or 644 <= n <= 698 or n >= 1372):
        continue
    for m, p in re.findall(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^\s`),;]*)", line):
        if (m, norm(p)) not in known and not any(k[1] == norm(p) for k in known if p.endswith("*")):
            # a route named with its method alone, or a prefix
            print(f"{n}\t{m} {p}\t{'path known under another method' if any(k[1] == norm(p) for k in known) else 'no such route'}")
