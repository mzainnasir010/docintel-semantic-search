"""Semantic top-k retrieval with threshold and input validation."""

from __future__ import annotations

from typing import Any

from quillseek.config import get_settings
from quillseek.embeddings import Embedder
from quillseek.models import SearchResponse
from quillseek.vectorstore import ChromaVectorStore


class SearchService:
    """Embed queries and return ranked, thresholded document chunks."""

    MAX_K = 100

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: ChromaVectorStore | None = None,
    ) -> None:
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or ChromaVectorStore(
            embedding_model_name=self.embedder.model_name
        )

    def search(
        self,
        query: str,
        k: int | None = None,
        min_similarity: float | None = None,
        doc_filter: str | dict[str, Any] | None = None,
    ) -> SearchResponse:
        """Return matching chunks sorted by similarity and their relevance flag."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty")
        settings = get_settings()
        result_count = settings.top_k if k is None else k
        threshold = settings.min_similarity if min_similarity is None else min_similarity
        if isinstance(result_count, bool) or not isinstance(result_count, int):
            raise ValueError("k must be an integer")
        if not 1 <= result_count <= self.MAX_K:
            raise ValueError(f"k must be between 1 and {self.MAX_K}")
        if not -1.0 <= threshold <= 1.0:
            raise ValueError("min_similarity must be between -1.0 and 1.0")

        query_vector = self.embedder.embed_query(query.strip())
        if isinstance(doc_filter, str):
            retrieved = self.vector_store.query(
                query_vector, k=result_count, doc_id=doc_filter
            )
        else:
            retrieved = self.vector_store.query(
                query_vector, k=result_count, where=doc_filter
            )
        relevant = sorted(
            (item for item in retrieved if item.similarity >= threshold),
            key=lambda item: item.similarity,
            reverse=True,
        )
        ranked = [item.model_copy(update={"rank": index}) for index, item in enumerate(relevant, 1)]
        return SearchResponse(results=ranked, is_relevant=bool(ranked))
