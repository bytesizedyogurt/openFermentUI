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

"Flushes to disk" has to mean the disk. On macOS, fsync hands the data to the
drive, whose own cache can still lose it in a power cut; F_FULLFSYNC asks the
drive to write it out, and is used wherever it exists. The folder is synced
after the rename too, so the new name itself survives the cut.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
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
            _flush(f.fileno())
        os.replace(tmp, path)
        _sync_folder(path.parent)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


@contextmanager
def held(path: Path) -> Iterator[None]:
    """Hold `path` for a read-modify-write against other processes too.

    A threading lock keeps two requests in the service apart; the nightly job
    is another process, and a change made in the service while it ran would
    be lost to whichever wrote second (OF-BLD-013 §5.5). This takes an
    exclusive advisory lock on a file beside `path` (`<name>.lock`, kept out
    of git with the file it guards) and waits for it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:  # pragma: no cover
        yield
        return
    with open(path.with_name(path.name + ".lock"), "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
