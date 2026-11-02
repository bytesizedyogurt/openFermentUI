"""`pnpm gen:tools`: write docs/TOOLS.md from the tool registry
(core/openferment_core/tools/reference.py; execution prompt §7.3 item 7).
`--check` writes nothing and fails when the file differs from the registry."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
os.environ.setdefault("OPENFERMENT_DATA_DIR", tempfile.mkdtemp(prefix="gen-tools-"))

from openferment_core.tools import reference  # noqa: E402

DOC = ROOT / "docs" / "TOOLS.md"


def main(argv: list[str]) -> int:
    text = reference.render()
    if "--check" in argv:
        if DOC.read_text(encoding="utf-8") != text:
            print("✗ docs/TOOLS.md differs from the registry. Run `pnpm gen:tools`.")
            return 1
        print("✓ docs/TOOLS.md is what the registry writes.")
        return 0
    DOC.write_text(text, encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} ({text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
