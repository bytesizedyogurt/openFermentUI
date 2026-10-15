"""geneOS on the service's side (OF-BLD-014 §6.2).

The geneOS worker does the flux balance analysis in a process of its own;
this module holds the one `SimWorker` that runs it, tells the worker where a
fetched model file lives, and fetches that file:

    pnpm geneos:fetch     the C. necator reconstruction at its pinned commit,
                          into core/data/models/, checked against its sha256

A hash that does not match is a stop condition (§6.2): the file is moved
aside, never used, and the command fails.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from . import geneos_models as shelf
from .workers import SimWorker

# Loading iJO1366 takes a few seconds and a frontier a little longer; the
# first call on a cold worker pays both. A setting, not a measurement.
WORKER_TIMEOUT_S = 180.0

_WORKER: SimWorker | None = None
_LOCK = threading.Lock()


def worker() -> SimWorker:
    global _WORKER
    with _LOCK:
        if _WORKER is None:
            _WORKER = SimWorker("openferment_core.workers.geneos_worker", timeout_s=WORKER_TIMEOUT_S)
        return _WORKER


class GeneosUnavailable(RuntimeError):
    """The model cannot be loaded here, in words."""


def model_args(model_id: str) -> dict[str, Any]:
    """The worker's arguments for a model: its id, and its file when fetched."""
    if model_id == "toy":
        return {"modelId": "toy"}
    entry = shelf.SHELF.get(model_id)
    if entry is None:
        raise GeneosUnavailable(f"there is no model {model_id} on the shelf; it holds {', '.join(shelf.SHELF)}")
    why = shelf.available(entry)
    if why:
        raise GeneosUnavailable(why)
    args: dict[str, Any] = {"modelId": model_id}
    if entry.fetched:
        args["path"] = str(entry.fetched.local)
    return args


def describe(model_id: str) -> dict[str, Any]:
    return worker().call("describe", model_args(model_id))


# ── fetching the published file ────────────────────────────────────────


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(model: shelf.ShelfModel = shelf.SHELF["RehMBEL1391"], *, run=subprocess.run) -> Path:
    """Clone the pinned commit without its blobs, check out the one file, and
    verify its hash. Returns the file's path; raises on a mismatch."""
    f = model.fetched
    assert f is not None, f"{model.id} is not a fetched model"
    clone = f.local.parents[len(Path(f.path).parts) - 1]
    if not (clone / ".git").is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", f.repository, str(clone)], check=True)
    run(["git", "-C", str(clone), "checkout", "--quiet", f.commit, "--", f.path], check=True)
    got = sha256_of(f.local)
    if got != f.sha256:
        aside = f.local.with_suffix(f.local.suffix + ".mismatch")
        shutil.move(str(f.local), aside)
        raise GeneosUnavailable(
            f"{model.id}: the file at {f.commit} hashes to {got}, not the pinned {f.sha256}. "
            f"It was moved to {aside.name} and is not used. This is a stop condition (OF-BLD-014 §6.2)."
        )
    return f.local


def main(argv: list[str]) -> int:
    if argv[:1] != ["fetch"]:
        print("usage: python -m openferment_core.geneos fetch", file=sys.stderr)
        return 2
    model = shelf.SHELF["RehMBEL1391"]
    try:
        path = fetch(model)
    except subprocess.CalledProcessError as e:
        print(f"✗ git failed ({e.returncode}) fetching {model.fetched.repository}", file=sys.stderr)
        return 1
    except GeneosUnavailable as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    print(f"✓ {model.id} at {model.fetched.commit}: {path.relative_to(shelf.model_dir().parent.parent)}, sha256 {model.fetched.sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
