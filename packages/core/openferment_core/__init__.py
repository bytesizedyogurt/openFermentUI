"""openferment-core — the canonical openFerment schema and unit engine.

Python is the source of truth for both. `src/data/types.ts` in the UI is
generated from `openferment_core.schema`; the TypeScript unit engine is a mirror
of `openferment_core.units` with a parity gate in CI.

See `CLAUDE.md` at the repository root for the routing table that decides what
belongs here and what stays in TypeScript.
"""

from __future__ import annotations

__version__ = "0.1.0"
