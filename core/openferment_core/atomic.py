"""Whole-file writes that land whole or not at all (OF-BLD-012 §B.8).

Every file the service keeps (biorepo.json, a fetch in fulltext/, a run in
candidates/) used to be written with `Path.write_text`, which truncates first
and fills second. A crash, a power cut or a full disk between the two leaves a
half-written file. For biorepo.json, the committed record of who decided what,
that would be the decisions themselves. A reader in another process (the
nightly job writes while the server reads) could also catch a file mid-write.

`write_text` here writes beside the target, flushes to disk, then renames over
it. A rename within one directory is atomic, so the target holds either the
old contents or the new ones, never a mixture, and a failed write leaves the
old file exactly as it was and nothing beside it.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text(path: Path, text: str) -> None:
    """Replace `path` with `text` (UTF-8) atomically, creating its folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # mkstemp makes the file owner-only; give it the permissions the
            # file it replaces had, or ordinary ones for a new file.
            os.fchmod(f.fileno(), mode)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
