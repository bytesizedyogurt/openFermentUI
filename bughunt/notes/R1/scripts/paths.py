"""R1: every backticked path-like token in docs/PROGRESS.md's checked sections, held to the tree at a commit.
Usage: python3 paths.py [COMMIT]   (default 2047f5a). Prints line, token, verdict for tokens missing at COMMIT."""
import re, subprocess, sys
REPO = "/home/user/openFermentUI"
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "2047f5a"
SECTIONS = [(9, 251), (383, 560), (644, 698), (1372, 10**9)]
lines = subprocess.run(["git", "-C", REPO, "show", f"{COMMIT}:docs/PROGRESS.md"], capture_output=True, text=True).stdout.splitlines()
tree = set(subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", COMMIT], capture_output=True, text=True).stdout.split())
dirs = set()
for p in tree:
    parts = p.split("/")
    for i in range(1, len(parts)):
        dirs.add("/".join(parts[:i]))
ROOTS = ["", "core/", "core/openferment_core/", "core/tests/", "src/", "scripts/", "docs/", "core/openferment_core/engine/", "src/screens/", "src/lib/", "src/components/"]
def exists(tok):
    t = tok.rstrip("/").split("::")[0].split(":")[0] if not tok.startswith("http") else None
    if t is None:
        return True
    for r in ROOTS:
        c = r + t
        if c in tree or c in dirs:
            return True
    # basename anywhere
    base = t.split("/")[-1]
    if "/" not in t and any(p.endswith("/" + base) or p == base for p in tree):
        return "basename-only"
    return False
out = []
for n, line in enumerate(lines, 1):
    if not any(a <= n <= b for a, b in SECTIONS):
        continue
    for tok in re.findall(r"`([^`]+)`", line):
        tok = tok.strip()
        if " " in tok or tok.startswith("~") or tok.startswith("$"):
            continue
        if not re.search(r"\.(py|ts|tsx|md|json|toml|sh|yaml|yml|mjs|js|txt|csv|lock|sql|ini|plist)$|/$", tok.split("::")[0]):
            continue
        v = exists(tok)
        if v is not True:
            out.append((n, tok, v))
for n, tok, v in out:
    print(f"{n}\t{tok}\t{v}")
