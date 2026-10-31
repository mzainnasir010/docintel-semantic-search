"""Exercise API routes with a temporary Chroma store and deterministic LLM stub."""

import hashlib
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from quillseek.api import create_app
from quillseek.config import Settings
from quillseek.indexing import index_files
from quillseek.rag import RAGService
from quillseek.search import SearchService
from quillseek.vectorstore import ChromaVectorStore


class FakeEmbedder:
    def __init__(self, model_name):
        self.model_name = model_name

    def embed_documents(self, texts):
        return np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1))

    def embed_query(self, _query):
        return np.array([1.0, 0.0], dtype=np.float32)


class StubLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return "Python supports async/await syntax [S1]."

    def stream(self, prompt):
        yield self.generate(prompt)


@pytest.fixture
def api(tmp_path):
    settings = Settings(
        _env_file=None,
        chroma_path=str(tmp_path / "chroma"),
        collection_name="api-test",
        upload_dir=str(tmp_path / "uploads"),
        max_upload_bytes=10000,
        gemini_api_key="",
        gradio_origin="http://localhost:7860",
    )
    store = ChromaVectorStore(
        path=settings.chroma_path,
        collection_name=settings.collection_name,
        embedding_model_name=settings.embedding_model,
    )
    embedder = FakeEmbedder(settings.embedding_model)
    search = SearchService(embedder=embedder, vector_store=store)
    llm = StubLLM()
    rag = RAGService(search_service=search, llm_client=llm)

    def test_indexer(paths, callback, *, store, run_log_path=None):
        return index_files(
            paths,
            callback,
            store=store,
            embedder=embedder,
            run_log_path=run_log_path,
        )

    app = create_app(
        settings=settings,
        store=store,
        search_service=search,
        rag_service=rag,
        indexer=test_indexer,
        health_probe=lambda _settings: True,
    )
    return TestClient(app), store, llm


def test_every_api_route_happy_path_and_reset(api) -> None:
    client, store, llm = api
    assert client.get("/health").json() == {
        "status": "ok",
        "gemini_configured": False,
        "gemini_reachable": False,
        "gemini_model": "gemini-3.8-flash",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "chunk_count": 0,
    }

    text = b"Python supports async/await syntax for asynchronous programming."
    uploaded = client.post(
        "/documents/upload",
        files=[("files", ("../unsafe name.txt", text, "text/plain"))],
    )
    assert uploaded.status_code == 200
    assert uploaded.json() == {"uploaded": ["unsafe name.txt"], "count": 1}
    pending = client.get("/documents").json()
    assert pending["documents"] == []
    assert pending["pending_uploads"] == ["unsafe name.txt"]

    indexed = client.post("/index")
    assert indexed.status_code == 202
    job_id = indexed.json()["job_id"]
    assert indexed.json()["finished"] is False
    status = client.get(f"/index/status/{job_id}")
    for _ in range(500):
        if status.json()["finished"]:
            break
        time.sleep(0.01)
        status = client.get(f"/index/status/{job_id}")
    assert status.status_code == 200
    assert status.json()["finished"] is True
    assert status.json()["chunks_indexed"] == 1

    documents = client.get("/documents").json()
    assert len(documents["documents"]) == 1
    assert documents["pending_uploads"] == []

    found = client.post("/search", json={"query": "async python", "k": 3})
    assert found.status_code == 200
    assert found.json()["is_relevant"] is True
    assert found.json()["results"][0]["chunk"]["doc_name"] == "unsafe name.txt"

    answer = client.post("/ask", json={"query": "What syntax?"})
    assert answer.status_code == 200
    assert answer.json()["answer"] == "Python supports async/await syntax [S1]."
    assert answer.json()["sources"][0]["doc_name"] == "unsafe name.txt"
    assert len(llm.calls) == 1

    doc_id = hashlib.sha256(text).hexdigest()[:16]
    deleted = client.delete(f"/documents/{doc_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_chunks"] == 1
    assert client.delete("/documents/unknown").status_code == 404

    reset = client.delete("/collection")
    assert reset.status_code == 200
    assert reset.json() == {"status": "reset", "chunk_count": 0}
    assert store.count() == 0
    assert list(client.app.state.upload_dir.iterdir()) == []


def test_end_to_end_upload_corpus_index_search_and_ask(api) -> None:
    from pathlib import Path

    client, _store, _llm = api
    root = Path(__file__).resolve().parents[2]
    corpus_file = root / "data" / "sample_docs" / "python_asyncio.txt"
    uploaded = client.post(
        "/documents/upload",
        files=[("files", (corpus_file.name, corpus_file.read_bytes(), "text/plain"))],
    )
    assert uploaded.status_code == 200
    run = client.post("/index")
    assert run.status_code == 202

    for _ in range(500):
        status = client.get(f"/index/status/{run.json()['job_id']}")
        if status.json()["finished"]:
            break
        time.sleep(0.01)
    assert status.json()["finished"] is True
    assert status.json()["indexed"] == 1

    found = client.post(
        "/search",
        json={"query": "How does Python handle asynchronous network I/O?", "k": 5},
    )
    assert found.status_code == 200
    assert found.json()["is_relevant"]
    assert any(
        item["chunk"]["doc_name"] == "python_asyncio.txt"
        for item in found.json()["results"]
    )
    answer = client.post("/ask", json={"query": "What syntax does asyncio use?"})
    assert answer.status_code == 200
    assert answer.json()["sources"][0]["doc_name"] == "python_asyncio.txt"


def test_upload_rejects_bad_type_and_oversize_file(api) -> None:
    client, _store, _llm = api
    bad_type = client.post(
        "/documents/upload",
        files=[("files", ("payload.exe", b"bad", "application/octet-stream"))],
    )
    assert bad_type.status_code == 415
    assert bad_type.json()["error"] == "request_error"

    too_big = client.post(
        "/documents/upload",
        files=[
            (
                "files",
                (
                    "large.txt",
                    b"x" * (api[0].app.state.settings.max_upload_bytes + 1),
                    "text/plain",
                ),
            )
        ],
    )
    assert too_big.status_code == 413
    assert "size limit" in too_big.json()["detail"]


def test_unknown_index_job_and_invalid_requests_return_safe_errors(api) -> None:
    client, _store, _llm = api
    unknown = client.get("/index/status/does-not-exist")
    assert unknown.status_code == 404
    assert unknown.json() == {"error": "request_error", "detail": "Index job not found"}
    blank = client.post("/search", json={"query": "   "})
    assert blank.status_code == 422
    assert blank.json()["error"] == "validation_error"


def test_empty_index_ask_refuses_without_calling_llm(api) -> None:
    client, _store, llm = api
    answer = client.post("/ask", json={"query": "Something absent?"})
    assert answer.status_code == 200
    assert answer.json()["refused"] is True
    assert answer.json()["answer"] == "the answer is not present in the supplied documents"
    assert llm.calls == []


def test_running_index_job_is_exclusive_but_search_and_ask_stay_available(api) -> None:
    import threading

    client, _store, llm = api
    started = threading.Event()
    release = threading.Event()
    original_indexer = client.app.state.indexer

    def slow_indexer(paths, callback, *, store, run_log_path=None):
        started.set()
        assert release.wait(timeout=10)
        return original_indexer(paths, callback, store=store, run_log_path=run_log_path)

    client.app.state.indexer = slow_indexer
    try:
        first = client.post("/index")
        assert first.status_code == 202
        job_id = first.json()["job_id"]
        assert started.wait(timeout=5)

        second = client.post("/index")
        assert second.status_code == 409
        assert client.delete("/collection").status_code == 409
        assert client.post("/search", json={"query": "during indexing"}).status_code == 200
        assert client.post("/ask", json={"query": "during indexing"}).status_code == 200
        assert llm.calls == []
    finally:
        release.set()

    for _ in range(500):
        status = client.get(f"/index/status/{job_id}")
        if status.json()["finished"]:
            break
        time.sleep(0.01)
    assert status.json()["finished"] is True
