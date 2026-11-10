"""Discovery's heavy-module count, with the group narrowed to the entry points named on the command
line (every one when none), in a process that then imports the service's app as the service does:
which h1 engines load, and whether cobra stands in this process afterwards.
Run with the worktree's venv (the probe package installed)."""
import sys
from openferment_core.engine import registry

want = set(sys.argv[1:])
real = registry.entry_points
registry.entry_points = lambda: [e for e in real() if not want or e.name in want]
print("cobra in sys.modules before discovery:", "cobra" in sys.modules)
from openferment_core import api  # noqa: E402,F401  discovery runs as the app is imported
for name, f in sorted(registry.found().items()):
    if name.startswith("h1"):
        print(f"{name}: {'LOADED' if f.engine is not None else 'set aside'}: {f.error}")
print("cobra in sys.modules after discovery:", "cobra" in sys.modules)
