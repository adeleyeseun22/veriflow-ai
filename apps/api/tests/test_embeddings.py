from math import isclose, sqrt

import pytest

from veriflow_api.services.embeddings import EmbeddingProviderError, normalize_embedding


def test_embedding_normalization_returns_unit_vector() -> None:
    vector = normalize_embedding([3.0, 4.0], expected_dimension=2)

    assert vector == [0.6, 0.8]
    assert isclose(sqrt(sum(value * value for value in vector)), 1.0)


def test_embedding_normalization_rejects_wrong_dimension() -> None:
    with pytest.raises(EmbeddingProviderError, match="dimension mismatch"):
        normalize_embedding([1.0, 2.0], expected_dimension=3)


def test_embedding_normalization_rejects_zero_vector() -> None:
    with pytest.raises(EmbeddingProviderError, match="zero vector"):
        normalize_embedding([0.0, 0.0], expected_dimension=2)
