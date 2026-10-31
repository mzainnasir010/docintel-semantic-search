"""Verify corpus chunks and queries share the configured embedding space."""

from pathlib import Path

import numpy as np

from quillseek.chunking import chunk_pages
from quillseek.embeddings import Embedder
from quillseek.ingestion import ingest_files


def test_corpus_chunks_and_query_embed_to_normalized_vectors() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "data" / "sample_docs" / "python_asyncio.txt"
    ingestion = ingest_files([source])
    chunks = chunk_pages(ingestion.pages, chunk_size=300, chunk_overlap=40)
    embedder = Embedder()

    document_vectors = embedder.embed_documents([chunk.text for chunk in chunks[:3]])
    query_vector = embedder.embed_query("How do I run asynchronous Python coroutines?")

    assert document_vectors.shape == (min(3, len(chunks)), embedder.dimension)
    assert query_vector.shape == (embedder.dimension,)
    assert np.allclose(np.linalg.norm(document_vectors, axis=1), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(query_vector), 1.0, atol=1e-5)
    assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
