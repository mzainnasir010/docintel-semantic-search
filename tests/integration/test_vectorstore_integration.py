"""End-to-end corpus ingestion, embedding, and persistent similarity search."""

from pathlib import Path

from docintel.chunking import chunk_pages
from docintel.embeddings import Embedder
from docintel.ingestion import ingest_files
from docintel.vectorstore import ChromaVectorStore


def test_ingested_corpus_chunks_are_searchable_from_persistent_store(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "data" / "sample_docs" / "python_asyncio.txt"
    ingestion = ingest_files([source])
    document = ingestion.documents[0]
    chunks = chunk_pages(
        ingestion.pages, chunk_size=300, chunk_overlap=40,
        ingested_at=document.ingested_at,
    )
    embedder = Embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in chunks])
    store_path = tmp_path / "persistent-chroma"

    store = ChromaVectorStore(
        path=store_path,
        collection_name="corpus-test",
        embedding_model_name=embedder.model_name,
    )
    store.add_chunks(chunks, vectors)
    result = store.query(
        embedder.embed_query("How can Python run asynchronous coroutines?"),
        k=1,
        doc_id=document.doc_id,
    )

    assert store.count() == len(chunks)
    assert result
    assert result[0].chunk.doc_id == document.doc_id
    assert result[0].similarity >= 0.0
    assert store.list_documents()[0].doc_name == source.name
