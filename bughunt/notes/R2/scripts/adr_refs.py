"""R2: hold every backticked path and dotted name that alpha 2.2 added to docs/decisions/ to the tree at 2047f5a.

Prints each added ADR line's backticked token that names a file path the tree lacks, and each
`module.name` whose name appears nowhere under core/ or src/ (a deleted name an ADR line keeps
naming as standing is a Drift candidate; the reader then reads the line). Usage, from the repo root:
python bughunt/notes/R2/scripts/adr_refs.py
"""
import re
import subprocess

REV, BASE = "2047f5a", "112eb8b"
diff = subprocess.run(["git", "diff", "-U0", BASE, REV, "--", "docs/decisions/"], capture_output=True, text=True).stdout
files = set(subprocess.run(["git", "ls-tree", "-r", "--name-only", REV], capture_output=True, text=True).stdout.split())
dirs = {f.rsplit("/", i)[0] for f in files for i in range(1, f.count("/") + 1)}
cur = None
for line in diff.splitlines():
    if line.startswith("+++ "):
        cur = line[6:]
        continue
    if not line.startswith("+") or line.startswith("+++"):
        continue
    for tok in re.findall(r"`([^`]+)`", line):
        t = tok.strip()
        if re.fullmatch(r"[\w./-]+\.(py|ts|tsx|md|json|yaml|toml|sh|mjs|csv)", t) or (t.endswith("/") and "/" in t[:-1]):
            cands = [t.rstrip("/"), "core/" + t.rstrip("/"), "core/openferment_core/" + t.rstrip("/"), "src/" + t.rstrip("/"),
                     "docs/" + t.rstrip("/"), "scripts/" + t.rstrip("/")]
            if not any(c in files or c in dirs for c in cands):
                # a bare file name: look for it anywhere
                base = t.rstrip("/").split("/")[-1]
                if not any(f.endswith("/" + base) or f == base for f in files):
                    print(f"{cur}: path {t!r} not in the tree: {line[1:].strip()[:160]}")
        m = re.fullmatch(r"([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)(\(\))?", t)
        if m and m.group(1) not in {"e", "g", "i", "os", "sys", "json", "math", "self", "pnpm", "uv"}:
            name = m.group(2)
            hit = subprocess.run(["git", "grep", "-q", "-w", name, REV, "--", "core/openferment_core", "src", "scripts", "core/tests"]).returncode == 0
            if not hit:
                print(f"{cur}: name {t!r} not found in code: {line[1:].strip()[:160]}")
