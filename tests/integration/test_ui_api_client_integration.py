"""Run the frontend API client against FastAPI's in-process TestClient."""

import time

import numpy as np
from fastapi.testclient import TestClient

from quillseek.api import create_app
from quillseek.config import Settings
from quillseek.indexing import index_files
from quillseek.rag import RAGService
from quillseek.search import SearchService
from quillseek.ui.api_client import APIClient
from quillseek.vectorstore import ChromaVectorStore


class TinyEmbedder:
    def __init__(self, model_name):
        self.model_name = model_name

    def embed_documents(self, texts):
        return np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1))

    def embed_query(self, _query):
        return np.array([1.0, 0.0], dtype=np.float32)


class StubLLM:
    def generate(self, _prompt):
        return "Asyncio uses async/await syntax [S1]."

    def stream(self, prompt):
        yield self.generate(prompt)


def test_api_client_uploads_indexes_and_retrieves_through_backend(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        chroma_path=str(tmp_path / "chroma"),
        collection_name="ui-client-integration",
        upload_dir=str(tmp_path / "uploads"),
        max_upload_bytes=10000,
        gemini_api_key="",
    )
    store = ChromaVectorStore(
        path=settings.chroma_path,
        collection_name=settings.collection_name,
        embedding_model_name=settings.embedding_model,
    )
    embedder = TinyEmbedder(settings.embedding_model)
    search = SearchService(embedder=embedder, vector_store=store)

    def test_indexer(paths, callback, *, store, run_log_path=None):
        return index_files(
            paths,
            callback,
            store=store,
            embedder=embedder,
            run_log_path=run_log_path,
        )

    backend_app = create_app(
        settings=settings,
        store=store,
        search_service=search,
        rag_service=RAGService(search_service=search, llm_client=StubLLM()),
        indexer=test_indexer,
        health_probe=lambda _settings: False,
    )
    with TestClient(backend_app) as backend:
        frontend_client = APIClient("http://testserver", client=backend)
        assert frontend_client.health()["status"] == "ok"

        source = tmp_path / "async.txt"
        source.write_text("Asyncio uses async/await syntax for concurrent code.", encoding="utf-8")
        assert frontend_client.upload_files([source])["count"] == 1
        assert frontend_client.documents()["pending_uploads"] == ["async.txt"]

        job = frontend_client.start_index()
        assert job["finished"] is False
        for _ in range(500):
            status = frontend_client.index_status(job["job_id"])
            if status["finished"]:
                break
            time.sleep(0.01)
        assert status["finished"] is True
        assert status["indexed"] == 1
        assert frontend_client.documents()["documents"][0]["doc_name"] == "async.txt"
        assert frontend_client.search("async syntax")["is_relevant"] is True
        answer = frontend_client.ask("What syntax does asyncio use?")
        assert answer["answer"] == "Asyncio uses async/await syntax [S1]."
