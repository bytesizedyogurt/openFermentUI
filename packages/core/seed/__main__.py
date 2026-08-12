"""`python3 -m seed …` — the same entry point as `seed/cli.py`."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
