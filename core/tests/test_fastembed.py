"""FastEmbed as Sci RAG Kit's embedder (ADR-002; execution prompt §8.2): the
kit's embedding contract, met by the model the service embeds with.

Marked `lit`: the model file comes from Hugging Face the first time and is
cached after (literature.EMBEDDING_CACHE).
"""
from __future__ import annotations

import asyncio
import math

import pytest
from sci_rag.embed.provider import EmbeddingDimensionError, EmbeddingProvider

from openferment_core.literature import EMBEDDING_CACHE, EMBEDDING_DIM, EMBEDDING_MODEL
from openferment_core.literature.fastembed import FastEmbedProvider

pytestmark = pytest.mark.lit

PASSAGES = [
    "Saccharomyces cerevisiae was grown in fed-batch culture on glucose at 30 degrees.",
    "The column was eluted with a sodium chloride gradient and the protein recovered.",
]


@pytest.fixture(scope="module")
def provider() -> FastEmbedProvider:
    return FastEmbedProvider(EMBEDDING_MODEL, dim=EMBEDDING_DIM, cache_dir=EMBEDDING_CACHE)


def _embed(provider: EmbeddingProvider, texts: list[str], task: str) -> list[list[float]]:
    return asyncio.run(provider.embed(texts, task=task))  # type: ignore[arg-type]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_it_states_its_model_and_dimension(provider):
    assert isinstance(provider, EmbeddingProvider)
    assert provider.version == f"fastembed:{EMBEDDING_MODEL}@{EMBEDDING_DIM}" == "fastembed:BAAI/bge-small-en-v1.5@384"
    assert provider.dim == 384


def test_every_vector_has_the_dimension_and_unit_length(provider):
    vectors = _embed(provider, PASSAGES, "document")
    assert len(vectors) == len(PASSAGES)
    for v in vectors:
        assert len(v) == EMBEDDING_DIM and all(isinstance(x, float) for x in v)
        assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-5)


def test_the_same_text_gives_the_same_vector_and_nothing_gives_nothing(provider):
    assert _embed(provider, PASSAGES[:1], "document") == _embed(provider, PASSAGES[:1], "document")
    assert _embed(provider, [], "document") == []


def test_a_question_lands_nearest_the_passage_that_answers_it(provider):
    passages = _embed(provider, PASSAGES, "document")
    [question] = _embed(provider, ["How was the yeast cultivated?"], "query")
    assert _cosine(question, passages[0]) > _cosine(question, passages[1])


def test_a_dimension_the_model_does_not_give_is_refused():
    wrong = FastEmbedProvider(EMBEDDING_MODEL, dim=EMBEDDING_DIM + 1, cache_dir=EMBEDDING_CACHE)
    with pytest.raises(EmbeddingDimensionError):
        _embed(wrong, PASSAGES[:1], "document")
    with pytest.raises(ValueError):
        FastEmbedProvider("an/unmeasured-model")
