"""Exercise RAG orchestration against a temporary real semantic index."""

from pathlib import Path

from docintel.chunking import chunk_pages
from docintel.embeddings import Embedder
from docintel.ingestion import ingest_files
from docintel.rag import RAGService
from docintel.search import SearchService
from docintel.vectorstore import ChromaVectorStore


class StubLLM:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "The asyncio documentation covers asynchronous I/O [S1]."

    def stream(self, prompt: str):
        yield self.generate(prompt)


def test_rag_service_answers_from_real_index_with_stub_llm(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "data" / "sample_docs" / "python_asyncio.txt"
    ingestion = ingest_files([source])
    document = ingestion.documents[0]
    pages = [page for page in ingestion.pages if page.doc_id == document.doc_id]
    chunks = chunk_pages(
        pages,
        chunk_size=900,
        chunk_overlap=0,
        ingested_at=document.ingested_at,
    )
    embedder = Embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in chunks])
    store = ChromaVectorStore(
        path=tmp_path / "rag-index",
        collection_name="rag-integration",
        embedding_model_name=embedder.model_name,
    )
    store.add_chunks(chunks, vectors)
    search = SearchService(embedder=embedder, vector_store=store)
    llm = StubLLM()
    service = RAGService(search, llm, context_budget=5000)

    answer = service.ask("How does Python asyncio support asynchronous I/O?", k=3)

    assert answer.refused is False
    assert answer.answer.endswith("[S1].")
    assert answer.sources[0].doc_name == "python_asyncio.txt"
    assert answer.sources[0].label == "S1"
    assert answer.retrieved_chunks
    assert "python_asyncio.txt" in llm.prompts[0]
