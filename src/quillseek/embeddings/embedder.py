"""Shared sentence-transformer embeddings with lazy model loading."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from quillseek.config import get_settings


def select_device() -> str:
    """Use CUDA when available and otherwise run on CPU."""
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=4)
def _load_model(model_name: str, device: str) -> SentenceTransformer:
    """Load and share one SentenceTransformer per model/device pair."""
    return SentenceTransformer(model_name, device=device)


class Embedder:
    """Embed documents and queries with one configured, normalized model."""

    def __init__(
        self,
        model_name: str | None = None,
        *,
        batch_size: int | None = None,
        device: str | None = None,
    ) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self.batch_size = (
            settings.embedding_batch_size if batch_size is None else batch_size
        )
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.device = device or select_device()
        self._model_instance: SentenceTransformer | None = None

    @property
    def model_name(self) -> str:
        """Configured model identifier for persistence and compatibility checks."""
        return self._model_name

    @property
    def model(self) -> SentenceTransformer:
        """Load the shared model only when an embedding or dimension is requested."""
        if self._model_instance is None:
            self._model_instance = _load_model(self._model_name, self.device)
        return self._model_instance

    @property
    def dimension(self) -> int:
        """Return the output vector dimension reported by the model."""
        get_dimension = getattr(self.model, "get_embedding_dimension", None)
        if get_dimension is None:
            get_dimension = self.model.get_sentence_embedding_dimension
        dimension = get_dimension()
        if dimension is None:
            raise RuntimeError(f"Embedding dimension unavailable for {self.model_name}")
        return int(dimension)

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.shape != (len(texts), self.dimension):
            raise RuntimeError(
                f"Model {self.model_name} returned shape {matrix.shape}; "
                f"expected ({len(texts)}, {self.dimension})"
            )
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Encode a batch of document strings into an L2-normalized matrix."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        return self._encode(texts)

    def embed_query(self, text: str) -> np.ndarray:
        """Encode one query with exactly the same model and normalization path."""
        return self._encode([text])[0]
