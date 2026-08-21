"""What a `corpusSnapshotId` is, computed once so every server agrees.

`ResponseMeta.corpusSnapshotId` (`src/adapters/types.ts`) asks each backend for
"an identifier of the corpus revision the answer was computed against", and
says a real server returns something immutable that IT holds, because only the
server knows what it actually served. Every server here holds the same kind of
thing — the bytes it read off disk — so every server can answer the same way.

WHY THIS IS SHARED AND NOT COPIED. The first two servers written each grew
their own digest, and they disagreed twice over: on the framing between name
and content (``name\\x00bytes`` against ``name:bytes``) and on the prefix
(``corpus-`` against ``sha256:``). Two servers reading the SAME file would have
reported different ids — while one of them carried a docstring promising that
reading the same files yields the same id. A snapshot id whose meaning depends
on which server minted it is barely better than a constant, which is the one
thing this field must never be. So the framing lives here, in the package every
Python server already depends on, and the TypeScript server mirrors it under a
parity gate (``scripts/check-servers.mjs``) exactly as the unit engine does.

WHAT THE ID COVERS, and the honest reading of it: the files THIS process read,
never the whole corpus. A digest over files a server never opened would attest
to data it cannot vouch for. So two servers reading different slices report
different ids, and that is correct — the id answers "what was this answer
computed against", not "what revision is the corpus at". When the exporter
mints a corpus-wide revision id, every server should report that instead and
this function becomes the fallback.

NOT A SECURITY BOUNDARY. It is a change detector. SHA-256 is used because it is
free in both standard libraries, not because anything here resists an
adversary who can already write to `data/corpus/`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

__all__ = ["SNAPSHOT_HEX_CHARS", "SNAPSHOT_PREFIX", "corpus_snapshot_id"]

#: Every id begins with this. A reader of a trace must be able to tell what
#: KIND of identifier they are holding before they try to recompute it.
SNAPSHOT_PREFIX = "sha256"

#: Hex characters of digest kept. 16 is 64 bits — ample for a change detector,
#: short enough to sit in a log line without wrapping.
SNAPSHOT_HEX_CHARS = 16


def corpus_snapshot_id(files: Mapping[str, bytes]) -> str:
    """Digest a set of corpus files into one identifier.

    ``files`` maps a repo-relative path (``data/corpus/papers.json``) to the
    RAW BYTES that were read. Raw bytes rather than a re-serialisation, because
    a server serves files it did not shape — the exporter's bytes are the thing
    being attested, and re-encoding them would digest this process's opinion of
    the corpus instead of the corpus.

    Names are sorted, so the id depends on WHICH files were read and not on the
    order a particular server happened to list them. Each entry is framed
    ``name \\0 length \\0 bytes`` with the length in decimal ASCII: without the
    length, a file named ``a`` holding ``b\\0c`` and a file named ``a\\0b``
    holding ``c`` would digest identically, and a snapshot id that two
    different corpora can share is not one.

    Returns ``sha256:<16 hex>``. An empty mapping is not an error and returns
    the digest of nothing — a server that read no corpus files should say so
    with an id it can defend, not with a blank.
    """
    digest = hashlib.sha256()
    for name in sorted(files):
        content = files[name]
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(str(len(content)).encode("ascii"))
        digest.update(b"\x00")
        digest.update(content)
    return f"{SNAPSHOT_PREFIX}:{digest.hexdigest()[:SNAPSHOT_HEX_CHARS]}"
