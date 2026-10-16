"""Meaning vectors for passages (OF-BLD-014 §4.2).

Each passage and each question becomes a vector, and close vectors rank
high. Two embedders share one protocol:

- `FastEmbedder`: `fastembed` with `BAAI/bge-small-en-v1.5` unless
  `OPENFERMENT_EMBED_MODEL` names another. The model file comes from Hugging
  Face once and is kept under `core/data/models/fastembed/`. `fastembed` is
  imported inside the class, so this module loads on a machine without it.
- `HashEmbedder`: a deterministic stand-in for tests. It hashes words into a
  fixed number of buckets; it knows nothing about meaning.

    pnpm index:build --dense    writes core/data/index/dense.npy and dense.json

`dense.json` names the model, the dimension, and the hash of the passage ids
the rows belong to, so a vector file that no longer matches the index is
never used.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from . import atomic, intake

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
# How many texts go to the model at once while the index is built: a software
# setting (E.1, convention).
BATCH = 64


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Unit-length rows, one per text."""
        ...


def _unit(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


class HashEmbedder:
    """Words hashed into `dim` buckets. A test stand-in: deterministic, free,
    and blind to meaning."""

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.name = f"hash-{dim}"

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
                out[row, h % self.dim] += 1.0
        return _unit(out)


class EmbedderUnavailable(RuntimeError):
    pass


def model_name() -> str:
    return os.environ.get("OPENFERMENT_EMBED_MODEL", "").strip() or DEFAULT_MODEL


def model_dir() -> Path:
    return intake.DATA_DIR / "models" / "fastembed"


class FastEmbedder:
    def __init__(self, model: str | None = None):
        self.name = model or model_name()
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise EmbedderUnavailable(
                "fastembed is not installed here; install the rag extra (uv sync --all-extras)"
            ) from e
        try:
            self._model = TextEmbedding(model_name=self.name, cache_dir=str(model_dir()))
        except Exception as e:  # a download that failed, a file that will not load
            raise EmbedderUnavailable(
                f"the model {self.name} could not be loaded ({type(e).__name__}); its file comes from "
                "huggingface.co once, and this machine needs to reach it for that"
            ) from e

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = list(self._model.embed(texts, batch_size=BATCH))
        return _unit(np.array(rows, dtype=np.float32)) if rows else np.zeros((0, 0), dtype=np.float32)


# ── the vectors on disk ────────────────────────────────────────────────


def _paths() -> tuple[Path, Path]:
    from .passages import index_dir

    return index_dir() / "dense.npy", index_dir() / "dense.json"


def ids_hash(ids: list[str], texts: list[str] | None = None) -> str:
    """The passages the rows belong to: their ids and their words, so a text
    that changed under the same ids is a different index (§4.R)."""
    h = hashlib.sha256("\n".join(ids).encode())
    for t in texts or []:
        h.update(b"\x00" + t.encode())
    return h.hexdigest()[:16]


def build_dense(embedder: Embedder) -> dict:
    """Vectors for every passage in the index, written beside it."""
    from .passages import read_index

    cuts = read_index()
    ids = [c.passage.id for c in cuts]
    texts = [f"{c.context}\n{c.passage.text}" for c in cuts]
    vectors = embedder.embed(texts) if texts else np.zeros((0, 0), dtype=np.float32)
    npy, meta = _paths()
    npy.parent.mkdir(parents=True, exist_ok=True)
    tmp = npy.with_suffix(".tmp.npy")
    np.save(tmp, vectors)
    os.replace(tmp, npy)
    info = {
        "model": embedder.name,
        "dim": int(vectors.shape[1]) if vectors.size else 0,
        "passageIds": ids_hash(ids, texts),
        "count": len(ids),
    }
    atomic.write_text(meta, json.dumps(info, indent=2) + "\n")
    return info


class DenseIndex:
    def __init__(self, ids: list[str], vectors: np.ndarray, model: str):
        self.ids = ids
        self.vectors = vectors
        self.model = model

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        if not self.ids:
            return []
        scores = self.vectors @ query_vector.reshape(-1)
        order = np.argsort(-scores, kind="stable")[: max(k, 0)]
        return [(self.ids[i], float(scores[i])) for i in order]


def load_dense(current_ids: list[str], current_texts: list[str]) -> tuple[DenseIndex | None, str | None]:
    """The vectors, or None and why they cannot be used. `current_texts` are
    what each passage is embedded from (context and text)."""
    npy, meta = _paths()
    if not npy.exists() or not meta.exists():
        return None, "no passage vectors yet: run pnpm index:build --dense on a machine that reaches huggingface.co"
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
        vectors = np.load(npy)
    except (ValueError, OSError) as e:
        return None, f"the passage vectors cannot be read ({type(e).__name__}); run pnpm index:build --dense again"
    if info.get("passageIds") != ids_hash(current_ids, current_texts) or len(vectors) != len(current_ids):
        return None, "the passage vectors belong to an older index; run pnpm index:build --dense again"
    return DenseIndex(current_ids, vectors, str(info.get("model"))), None


def dense_stale() -> str | None:
    """Why the vectors on disk cannot serve the current index, or None when
    they can. Vectors travel on the data branch, so a fresh clone may hold
    current ones; a session start builds them only when this says so."""
    from .passages import read_index

    cuts = read_index()
    _, why = load_dense([c.passage.id for c in cuts], [f"{c.context}\n{c.passage.text}" for c in cuts])
    return why


def main_dense() -> int:
    try:
        embedder = FastEmbedder()
    except EmbedderUnavailable as e:
        print(f"dense vectors: unavailable here: {e}")
        return 1
    info = build_dense(embedder)
    print(f"dense vectors: {info['count']} passages, {info['dim']} dimensions, {info['model']}")
    return 0
