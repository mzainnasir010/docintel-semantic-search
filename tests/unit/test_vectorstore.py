"""Unit and temporary-database coverage for persistent Chroma operations."""

from datetime import datetime, timezone

import numpy as np
import pytest

from docintel.models import Chunk
from docintel.vectorstore import ChromaVectorStore, EmbeddingModelMismatchError


def _chunk(
    chunk_id: str,
    doc_id: str,
    text: str,
    *,
    page: int = 1,
    section: str | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        doc_name=f"{doc_id}.txt",
        text=text,
        page_number=page,
        section=section,
        source_path=f"data/{doc_id}.txt",
        ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        char_start=0,
        char_end=len(text),
    )


def _store(tmp_path, model="test-model"):
    return ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="test-documents",
        embedding_model_name=model,
    )


def test_add_query_similarity_order_filter_and_metadata_round_trip(tmp_path) -> None:
    store = _store(tmp_path)
    chunks = [
        _chunk("a-1", "a", "annual paid leave", page=1, section="Leave"),
        _chunk("b-1", "b", "car engine maintenance"),
        _chunk("a-2", "a", "vacation days", page=2),
    ]
    embeddings = [[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]]
    store.add_chunks(chunks, embeddings)

    results = store.query([1.0, 0.0], k=3)
    filtered = store.query([1.0, 0.0], k=5, doc_id="a")

    assert [result.chunk.chunk_id for result in results] == ["a-1", "a-2", "b-1"]
    assert results[0].similarity == pytest.approx(1.0)
    assert results[0].rank == 1
    assert results[0].chunk.section == "Leave"
    assert results[0].chunk.source_path == "data/a.txt"
    assert results[0].chunk.ingested_at == chunks[0].ingested_at
    assert results[0].chunk.char_end == len(chunks[0].text)
    assert [result.chunk.doc_id for result in filtered] == ["a", "a"]
    assert store.count() == 3


def test_upsert_by_chunk_id_is_idempotent_and_updates_content(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_chunks([_chunk("stable-id", "a", "old text")], [[1.0, 0.0]])
    store.add_chunks([_chunk("stable-id", "a", "new text")], [[0.0, 1.0]])

    results = store.query([0.0, 1.0], k=5)

    assert store.count() == 1
    assert results[0].chunk.text == "new text"


def test_list_documents_delete_and_reset(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_chunks(
        [
            _chunk("a-1", "a", "page one", page=1),
            _chunk("a-2", "a", "page two", page=2),
            _chunk("b-1", "b", "other doc"),
        ],
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    )

    documents = store.list_documents()
    assert [(doc.doc_id, doc.chunk_count, doc.pages) for doc in documents] == [
        ("a", 2, [1, 2]), ("b", 1, [1])
    ]
    assert store.delete_document("a") == 2
    assert store.count() == 1
    store.reset()
    assert store.count() == 0
    assert store.list_documents() == []


def test_data_persists_across_store_reinstantiation(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_chunks([_chunk("persist-1", "doc", "stored text")], [[1.0, 0.0]])
    del store

    reopened = _store(tmp_path)
    results = reopened.query([1.0, 0.0], k=1)

    assert reopened.count() == 1
    assert results[0].chunk.text == "stored text"


def test_open_rejects_a_different_embedding_model(tmp_path) -> None:
    _store(tmp_path, model="model-one")

    with pytest.raises(EmbeddingModelMismatchError, match="uses embedding model"):
        _store(tmp_path, model="model-two")


@pytest.mark.parametrize(
    "chunks,embeddings",
    [([_chunk("one", "a", "one")], []), ([_chunk("one", "a", "one")], [[np.nan, 0]])],
)
def test_invalid_chunk_embedding_batches_are_rejected(tmp_path, chunks, embeddings) -> None:
    store = _store(tmp_path)

    with pytest.raises(ValueError):
        store.add_chunks(chunks, embeddings)


def test_query_validates_k_and_query_vector(tmp_path) -> None:
    store = _store(tmp_path)

    with pytest.raises(ValueError, match="k must be positive"):
        store.query([1.0, 0.0], k=0)
    with pytest.raises(ValueError, match="one-dimensional"):
        store.query([[1.0, 0.0]])
