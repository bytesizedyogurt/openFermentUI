"""A disk cache for the retrieval lanes' helper calls (OF-BLD-014 §4.2).

Every helper call is an `index`-role model call, kept under
`core/data/index/cache/<kind>/<hash>.json` by its inputs, so the same
question asked of the same passages is paid for once. The key names the
model chain and the prompt version, so a change to either asks again.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import atomic, llm


def _dir(kind: str) -> Path:
    from .passages import index_dir

    return index_dir() / "cache" / kind


def key(kind: str, prompt_version: str, payload: Any) -> str:
    body = json.dumps(
        {"kind": kind, "prompt": prompt_version, "chain": llm.chain("index"), "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode()).hexdigest()[:24]


def get(kind: str, k: str) -> dict[str, Any] | None:
    try:
        return json.loads((_dir(kind) / f"{k}.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def put(kind: str, k: str, value: dict[str, Any]) -> None:
    atomic.write_text(_dir(kind) / f"{k}.json", json.dumps(value, ensure_ascii=False, indent=1) + "\n")
