"""R1: every `pnpm <script>` named in docs/PROGRESS.md's checked sections, held to package.json's scripts at a commit."""
import json, re, subprocess, sys
REPO = "/home/user/openFermentUI"; COMMIT = sys.argv[1] if len(sys.argv) > 1 else "2047f5a"
SECTIONS = [(9, 251), (383, 560), (644, 698), (1372, 10**9)]
show = lambda p: subprocess.run(["git", "-C", REPO, "show", f"{COMMIT}:{p}"], capture_output=True, text=True).stdout
scripts = set(json.loads(show("package.json"))["scripts"])
BUILTIN = {"install", "exec", "dlx", "add", "run", "why", "list", "-w", "--filter", "store"}
lines = show("docs/PROGRESS.md").splitlines()
seen = {}
for n, line in enumerate(lines, 1):
    if not any(a <= n <= b for a, b in SECTIONS):
        continue
    for m in re.finditer(r"pnpm\s+([a-z][\w:.-]*)", line):
        s = m.group(1).rstrip(".,;:")
        if s in scripts or s in BUILTIN:
            continue
        seen.setdefault(s, []).append(n)
for s, ns in sorted(seen.items()):
    print(s, ns[:12])
