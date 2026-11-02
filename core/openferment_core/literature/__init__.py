"""The literature layer: Sci RAG Kit, used as a library (ADR-002).

`kit.py` owns the kit: its settings, its engine, the one `RagService`, and
which project sees which document. `collectors.py` turns what openFerment
fetches or is given (Europe PMC, OSTI, SGD, an upload, pasted text) into the
kit's corpus entries. `fastembed.py` computes passage vectors on this machine.

Importing this package writes the kit's settings into the environment, where
its modules read them, before any of those modules is imported:
`sci_rag.db.models` sizes its vector column from `SCI_RAG_EMBEDDING_DIM` at
import, so the dimension has to be this one from the first import on. The
values are openFerment's and replace whatever the environment held.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).parent

#: The embedding model every chunk is embedded with, and its dimension. The
#: kit's vector column is made with this dimension by the first migration;
#: another model means a migration and a re-embedding pass.
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

#: Where FastEmbed keeps the model file it fetches from Hugging Face the
#: first time: FASTEMBED_CACHE_PATH, or the user's cache directory.
EMBEDDING_CACHE = Path(os.environ.get("FASTEMBED_CACHE_PATH", "").strip() or Path.home() / ".cache" / "fastembed")

#: The kit's domain profile and prompts (domain/domain.yaml).
DOMAIN_DIR = HERE / "domain"

_SETTINGS = {
    # What the kit would build if one of its own paths asked for an embedder;
    # every kit object openFerment builds is handed FastEmbed instead (kit.py),
    # and this keeps any other path offline rather than on Google's service.
    "SCI_RAG_EMBEDDING_PROVIDER": "local-hash",
    "SCI_RAG_EMBEDDING_MODEL": EMBEDDING_MODEL,
    "SCI_RAG_EMBEDDING_DIM": str(EMBEDDING_DIM),
    "SCI_RAG_DOMAIN_DIR": str(DOMAIN_DIR),
}
os.environ.update(_SETTINGS)
