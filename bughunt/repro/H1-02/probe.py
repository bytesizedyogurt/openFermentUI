"""H1-02's probe: the service's startup in one process. The entry-point group is read from the installed
distributions and the stand-in dist-info on PYTHONPATH (no patching); importing openferment_core.api runs
discovery as the service does at startup (api.py:196). Prints each stand-in's verdict and whether cobra
stands in sys.modules after discovery."""
import sys

print("cobra in sys.modules before discovery:", "cobra" in sys.modules)
from openferment_core import api  # noqa: E402,F401  discovery runs as the app is imported
from openferment_core.engine import registry  # noqa: E402

group = [e.name for e in registry.entry_points()]
print("entry points read:", ", ".join(group))
for name, f in sorted(registry.found().items()):
    if name.startswith("h1"):
        print(f"VERDICT {name}: {'LOADED' if f.engine is not None else 'set aside'}: {f.error}")
print("COBRA_AFTER", "cobra" in sys.modules, len([m for m in sys.modules if m == "cobra" or m.startswith("cobra.")]))
