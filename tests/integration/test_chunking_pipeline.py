"""Integration coverage for ingest → preprocess → chunk on corpus content."""

from pathlib import Path

from quillseek.chunking import chunk_pages
from quillseek.ingestion import ingest_files


def test_corpus_document_runs_through_ingest_preprocess_and_chunk() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "data" / "sample_docs" / "python_asyncio.txt"
    ingestion = ingest_files([source])
    document = ingestion.documents[0]

    chunks = chunk_pages(
        ingestion.pages,
        strategy="recursive",
        chunk_size=180,
        chunk_overlap=30,
        ingested_at=document.ingested_at,
    )

    assert ingestion.succeeded == 1
    assert chunks
    assert all(chunk.doc_id == document.doc_id for chunk in chunks)
    assert all(chunk.doc_name == source.name for chunk in chunks)
    assert all(Path(chunk.source_path) == source for chunk in chunks)
    assert all(chunk.ingested_at == document.ingested_at for chunk in chunks)
    assert all(0 <= chunk.char_start <= chunk.char_end for chunk in chunks)
    assert all(chunk.text.strip() for chunk in chunks)
