"""`pnpm gen:api`: the OpenAPI document and the browser's types, written from the
service (execution prompt §4.7, §7.3 item 1, A5).

    docs/api/openapi.json   the FastAPI app's OpenAPI document, every route's project
                            scope written on it (api._scoped_openapi), keys sorted
    src/api/types.gen.ts    its schemas as TypeScript, by openapi-typescript

`--check` writes nothing and fails when either file differs from what the service
writes now: neither is edited by hand.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
os.environ.setdefault("OPENFERMENT_DATA_DIR", tempfile.mkdtemp(prefix="gen-api-"))

DOC = ROOT / "docs" / "api" / "openapi.json"
TYPES = ROOT / "src" / "api" / "types.gen.ts"
HEADER = ("// Written by `pnpm gen:api` from docs/api/openapi.json (openapi-typescript). Edit the\n"
          "// service's models (core/openferment_core/models.py), never this file.\n")


def document() -> str:
    from openferment_core.api import app

    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def types(doc_path: Path) -> str:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "types.gen.ts"
        done = subprocess.run(["pnpm", "exec", "openapi-typescript", str(doc_path), "-o", str(out)], cwd=ROOT,
                              capture_output=True, text=True, timeout=300)
        if done.returncode != 0:
            raise SystemExit(f"✗ openapi-typescript failed: {(done.stderr or done.stdout).strip()[-400:]}")
        return HEADER + out.read_text(encoding="utf-8")


def main(argv: list[str]) -> int:
    doc = document()
    with tempfile.TemporaryDirectory() as d:
        staged = Path(d) / "openapi.json"
        staged.write_text(doc, encoding="utf-8")
        ts = types(staged)
    if "--check" in argv:
        stale = [p.relative_to(ROOT).as_posix() for p, text in ((DOC, doc), (TYPES, ts))
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print(f"✗ {' and '.join(stale)} differ from what the service writes. Run `pnpm gen:api`.")
            return 1
        print("✓ docs/api/openapi.json and src/api/types.gen.ts are what the service writes.")
        return 0
    DOC.write_text(doc, encoding="utf-8")
    TYPES.parent.mkdir(parents=True, exist_ok=True)
    TYPES.write_text(ts, encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} and {TYPES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
