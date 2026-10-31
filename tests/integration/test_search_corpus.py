"""Paraphrased corpus question retrieves its source document semantically."""

from pathlib import Path

from quillseek.chunking import chunk_pages
from quillseek.embeddings import Embedder
from quillseek.ingestion import ingest_files
from quillseek.search import SearchService
from quillseek.vectorstore import ChromaVectorStore


def test_paraphrased_async_query_finds_asyncio_document_in_top_results(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    corpus = root / "data" / "sample_docs"
    paths = [
        corpus / "python_asyncio.txt",
        corpus / "python_modules.txt",
        corpus / "python_data_structures.txt",
    ]
    ingestion = ingest_files(paths)
    records = {record.doc_id: record for record in ingestion.documents}
    chunks = []
    for doc_id in records:
        doc_pages = [page for page in ingestion.pages if page.doc_id == doc_id]
        chunks.extend(
            chunk_pages(doc_pages, chunk_size=350, chunk_overlap=50,
                        ingested_at=records[doc_id].ingested_at)
        )

    embedder = Embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in chunks])
    store = ChromaVectorStore(
        path=tmp_path / "semantic-search",
        collection_name="corpus-search",
        embedding_model_name=embedder.model_name,
    )
    store.add_chunks(chunks, vectors)
    response = SearchService(embedder=embedder, vector_store=store).search(
        "How can a Python program handle network operations asynchronously without blocking?",
        k=5,
        min_similarity=0.15,
    )

    assert response.is_relevant
    assert response.results
    assert any(result.doc_name == "python_asyncio.txt" for result in response.results)
    assert [result.similarity for result in response.results] == sorted(
        (result.similarity for result in response.results), reverse=True
    )
