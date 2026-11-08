"""Whole-file writes that land whole or not at all.

The one file the service keeps on disk is a genome-scale model it fetched
into models/ (geneos.py); the records themselves are kept in the database
(ADR-001). `Path.write_bytes` truncates first and fills second, so a crash,
a power cut or a full disk between the two would leave half a model file,
whose hash is its pin.

`write_bytes` here writes beside the target, flushes to disk, then renames
over it, and `write_text` is the same for text. A rename within one
directory is atomic, so the target holds either the old contents or the new
ones, never a mixture, and a failed write leaves the old file exactly as it
was and nothing beside it.

"Flushes to disk" has to mean the disk. On macOS, fsync hands the data to the
drive, whose own cache can still lose it in a power cut; F_FULLFSYNC asks the
drive to write it out, and is used wherever it exists. The folder is synced
after the rename too, so the new name itself survives the cut.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - not on Windows, where this never runs
    fcntl = None  # type: ignore[assignment]


def _flush(fd: int) -> None:
    """Make what was written to `fd` survive a power cut."""
    if fcntl is not None and hasattr(fcntl, "F_FULLFSYNC"):
        try:
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
            return
        except OSError:
            pass  # a filesystem that does not support it; fsync is the next best
    os.fsync(fd)


def _sync_folder(folder: Path) -> None:
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        _flush(fd)
    except OSError:
        pass  # some filesystems refuse to sync a directory; the rename stands
    finally:
        os.close(fd)


def write_text(path: Path, text: str) -> None:
    """Replace `path` with `text` (UTF-8) atomically, creating its folder."""
    write_bytes(path, text.encode("utf-8"))


def write_bytes(path: Path, data: bytes) -> None:
    """Replace `path` with `data` atomically, creating its folder: a file
    kept as it was fetched (a model file, whose hash is its pin)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            # mkstemp makes the file owner-only; give it the permissions the
            # file it replaces had, or ordinary ones for a new file.
            os.fchmod(f.fileno(), mode)
            f.write(data)
            f.flush()
            _flush(f.fileno())
        os.replace(tmp, path)
        _sync_folder(path.parent)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

