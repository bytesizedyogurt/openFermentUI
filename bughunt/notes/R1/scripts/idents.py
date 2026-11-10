"""R1: every backticked identifier docs/PROGRESS.md names in a line range, looked up in the tree at a commit
(core/, src/, scripts/, examples/, docs/api/, docs/decisions/, package.json, .github/). Prints the ones found nowhere.
Usage: python3 idents.py FIRST LAST [COMMIT]"""
import re, subprocess, sys
REPO = "/home/user/openFermentUI"
a, b = int(sys.argv[1]), int(sys.argv[2]); COMMIT = sys.argv[3] if len(sys.argv) > 3 else "2047f5a"
lines = subprocess.run(["git", "-C", REPO, "show", f"{COMMIT}:docs/PROGRESS.md"], capture_output=True, text=True).stdout.splitlines()
files = [p for p in subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", COMMIT], capture_output=True, text=True).stdout.split()
         if p.startswith(("core/openferment_core/", "core/tests/", "core/pyproject.toml", "src/", "scripts/", "examples/", "docs/api/", "docs/decisions/", "package.json", ".github/", "core/.env.example", "docs/TOOLS.md", "docs/BASE.md", "docs/runbooks/", "compose.yaml", ".mcp.json", "COMPONENTS.md", "core/licences.toml"))
         and not p.endswith((".png", ".jpg", ".xml", ".pdf"))]
blob = {}
for p in files:
    try:
        blob[p] = subprocess.run(["git", "-C", REPO, "show", f"{COMMIT}:{p}"], capture_output=True, text=True, errors="replace").stdout
    except Exception:
        pass
corpus = "\n".join(blob.values())
seen = {}
for n in range(a, min(b, len(lines)) + 1):
    for tok in re.findall(r"`([^`\n]{2,80})`", lines[n - 1]):
        t = tok.strip()
        if re.fullmatch(r"[0-9a-f]{7,40}", t) or t.startswith(("pnpm ", "git ", "cd ", "uv ", "python ", "/", "~", "$", "http")):
            continue
        # look the token up whole; for a dotted name also its last part
        cands = [t]
        if re.fullmatch(r"[\w.]+\(?\)?", t) and "." in t:
            cands.append(t.rstrip("()").split(".")[-1])
        if not any(c in corpus for c in cands):
            seen.setdefault(t, []).append(n)
for t, ns in seen.items():
    print(f"{ns[0]}\t{t}\t{ns[1:6]}")
