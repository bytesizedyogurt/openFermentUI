"""A local embedder for Sci RAG Kit: FastEmbed (ADR-002; execution prompt §8.2).

The kit ships Google's embedder and a lexical stand-in for tests. This is the
third, offered upstream as `sci_rag/embed/fastembed.py`: passage vectors
computed on this machine by FastEmbed's ONNX models, so no document leaves
it to be embedded. The model file comes from Hugging Face the first time and
is cached after that.

`version` is `fastembed:<model>@<dim>`, stamped onto every chunk, so a change
of model is findable. The task hint (document or query) is used where the
model is asymmetric (`query_embed` and `passage_embed`), and every vector is
scaled to unit length, as the kit's cosine ranking assumes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from sci_rag.embed.provider import EmbeddingProvider, EmbeddingTask, l2_normalize

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
# The dimension of each model this build has measured, so the kit's vector
# column can be sized before the model is ever loaded.
DIMENSIONS = {"BAAI/bge-small-en-v1.5": 384}


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self, model_name: str = DEFAULT_MODEL, *, batch_size: int = 64, dim: int | None = None,
                 cache_dir: str | Path | None = None) -> None:
        if dim is None and model_name not in DIMENSIONS:
            raise ValueError(f"the dimension of {model_name} is not known here; pass dim=")
        self.model_name = model_name
        self.dim = dim if dim is not None else DIMENSIONS[model_name]
        self.batch_size = batch_size
        # Where the model file is kept; FastEmbed's own default is the
        # system's temporary directory, which a restart may empty.
        self.cache_dir = str(cache_dir) if cache_dir is not None else None
        self.version = f"fastembed:{model_name}@{self.dim}"
        self._model: Any = None

    def _loaded(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)
        return self._model

    def _embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        model = self._loaded()
        if task == "query" and hasattr(model, "query_embed"):
            raw = model.query_embed(texts)
        elif task == "document" and hasattr(model, "passage_embed"):
            raw = model.passage_embed(texts, batch_size=self.batch_size)
        else:
            raw = model.embed(texts, batch_size=self.batch_size)
        return [self.assert_dimension(l2_normalize([float(x) for x in v])) for v in raw]

    async def embed(self, texts: list[str], *, task: EmbeddingTask) -> list[list[float]]:
        """Embed on a worker thread: the model is CPU-bound, and the event
        loop it is awaited on serves every database call."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embed, texts, task)
