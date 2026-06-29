from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from datetime import datetime
from functools import lru_cache
from threading import Lock
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from veriflow_api.config import settings
from veriflow_api.models.chunk import DocumentChunk
from veriflow_api.models.document import Document


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider cannot produce valid vectors."""


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def normalize_embedding(values: Iterable[float], *, expected_dimension: int) -> list[float]:
    vector = [float(value) for value in values]
    if len(vector) != expected_dimension:
        raise EmbeddingProviderError(
            f"Embedding dimension mismatch: expected {expected_dimension}, received {len(vector)}."
        )
    if not all(math.isfinite(value) for value in vector):
        raise EmbeddingProviderError("Embedding contains non-finite values.")

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        raise EmbeddingProviderError("Embedding provider returned a zero vector.")
    return [value / magnitude for value in vector]


class FastEmbedProvider:
    provider_name = "fastembed"

    def __init__(self) -> None:
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._model: object | None = None
        self._model_lock = Lock()

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is None:
                try:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=settings.embedding_cache_dir,
                        threads=settings.embedding_threads,
                        providers=["CPUExecutionProvider"],
                        lazy_load=True,
                    )
                except Exception as error:
                    raise EmbeddingProviderError(
                        f"Unable to initialize embedding model {self.model_name}."
                    ) from error
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        try:
            raw_vectors = list(
                model.embed(
                    list(texts),
                    batch_size=settings.embedding_batch_size,
                )
            )
        except Exception as error:
            raise EmbeddingProviderError("Document embedding generation failed.") from error
        return [
            normalize_embedding(vector, expected_dimension=self.dimension) for vector in raw_vectors
        ]

    def embed_query(self, text: str) -> list[float]:
        query = text.strip()
        if not query:
            raise EmbeddingProviderError("Search query cannot be empty.")
        model = self._load_model()
        try:
            raw_vector = next(iter(model.query_embed(query)))
        except Exception as error:
            raise EmbeddingProviderError("Query embedding generation failed.") from error
        return normalize_embedding(raw_vector, expected_dimension=self.dimension)


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "fastembed":
        return FastEmbedProvider()
    raise EmbeddingProviderError(f"Unsupported embedding provider: {settings.embedding_provider}.")


async def embed_document_chunks(
    session: AsyncSession,
    *,
    document: Document,
    chunks: list[DocumentChunk],
    embedded_at: datetime,
    provider: EmbeddingProvider | None = None,
) -> list[DocumentChunk]:
    """Generate and persist one normalized vector per retrieval chunk."""

    active_provider = provider or get_embedding_provider()
    await session.flush()

    if chunks:
        vectors = await run_in_threadpool(
            active_provider.embed_documents,
            [chunk.content for chunk in chunks],
        )
        if len(vectors) != len(chunks):
            raise EmbeddingProviderError(
                "Embedding provider returned a different number of vectors than input chunks."
            )

        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk.embedding = normalize_embedding(
                vector,
                expected_dimension=active_provider.dimension,
            )
            chunk.embedding_provider = active_provider.provider_name
            chunk.embedding_model = active_provider.model_name
            chunk.embedded_at = embedded_at

    metadata = dict(document.document_metadata)
    metadata["embeddings"] = {
        "provider": active_provider.provider_name,
        "model": active_provider.model_name,
        "dimension": active_provider.dimension,
        "embedded_at": embedded_at.isoformat(),
        "embedding_count": len(chunks),
    }
    document.document_metadata = metadata
    document.embedding_provider = active_provider.provider_name
    document.embedding_model = active_provider.model_name
    document.embedding_dimension = active_provider.dimension
    document.embedding_count = len(chunks)
    document.embedded_at = embedded_at

    return chunks
