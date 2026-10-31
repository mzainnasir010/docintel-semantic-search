"""Unit tests for ranked search results, thresholds, and input validation."""

import pytest

from quillseek.models import Chunk, SearchResult
from quillseek.search import SearchService


def _result(chunk_id: str, similarity: float, rank: int = 1) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=chunk_id,
            doc_id="doc-1",
            doc_name="guide.txt",
            text=chunk_id,
            page_number=1,
        ),
        similarity=similarity,
        rank=rank,
    )


class FakeEmbedder:
    model_name = "test-model"

    def __init__(self):
        self.queries = []

    def embed_query(self, query):
        self.queries.append(query)
        return [1.0, 0.0]


class FakeVectorStore:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def query(self, embedding, k, *, where=None, doc_id=None):
        self.calls.append((embedding, k, where, doc_id))
        return self.results[:k]


def test_search_sorts_descending_applies_threshold_and_assigns_ranks(monkeypatch) -> None:
    monkeypatch.setattr(
        "quillseek.search.service.get_settings",
        lambda: type("Settings", (), {"top_k": 5, "min_similarity": 0.25})(),
    )
    embedder = FakeEmbedder()
    store = FakeVectorStore([_result("low", 0.1), _result("high", 0.9), _result("mid", 0.5)])
    service = SearchService(embedder=embedder, vector_store=store)

    response = service.search("  find a guide  ", k=3)

    assert [item.chunk_id for item in response.results] == ["high", "mid"]
    assert [item.rank for item in response.results] == [1, 2]
    assert response.is_relevant is True
    assert response.results[0].text == "high"
    assert response.results[0].doc_name == "guide.txt"
    assert embedder.queries == ["find a guide"]


def test_search_passes_document_filter_to_vector_store() -> None:
    store = FakeVectorStore([_result("match", 0.8)])
    service = SearchService(embedder=FakeEmbedder(), vector_store=store)

    response = service.search("query", k=1, doc_filter="doc-1")

    assert response.is_relevant
    assert store.calls[0][3] == "doc-1"


def test_search_passes_metadata_filter_to_vector_store() -> None:
    where = {"doc_id": "doc-1", "page_number": 1}
    store = FakeVectorStore([_result("match", 0.8)])
    service = SearchService(embedder=FakeEmbedder(), vector_store=store)

    service.search("query", doc_filter=where)

    assert store.calls[0][2] == where


def test_search_returns_empty_response_when_index_empty_or_below_threshold() -> None:
    empty = SearchService(embedder=FakeEmbedder(), vector_store=FakeVectorStore([]))
    irrelevant = SearchService(
        embedder=FakeEmbedder(), vector_store=FakeVectorStore([_result("low", 0.2)])
    )

    assert empty.search("query").results == []
    response = irrelevant.search("query", min_similarity=0.3)
    assert response.results == []
    assert response.is_relevant is False


@pytest.mark.parametrize("query", ["", "  ", None])
def test_empty_query_is_rejected(query) -> None:
    service = SearchService(embedder=FakeEmbedder(), vector_store=FakeVectorStore([]))

    with pytest.raises(ValueError, match="query must not be empty"):
        service.search(query)


@pytest.mark.parametrize("k", [0, -1, 101, 1.5, True])
def test_k_bounds_and_type_are_validated(k) -> None:
    service = SearchService(embedder=FakeEmbedder(), vector_store=FakeVectorStore([]))

    with pytest.raises(ValueError):
        service.search("query", k=k)


@pytest.mark.parametrize("threshold", [-1.1, 1.1])
def test_similarity_threshold_is_validated(threshold) -> None:
    service = SearchService(embedder=FakeEmbedder(), vector_store=FakeVectorStore([]))

    with pytest.raises(ValueError, match="min_similarity"):
        service.search("query", min_similarity=threshold)
