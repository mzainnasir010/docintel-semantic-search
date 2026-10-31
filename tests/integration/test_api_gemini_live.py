"""Opt-in full API flow through the real corpus, embedding model, and Gemini."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from quillseek.api import create_app
from quillseek.config import Settings, get_settings
from quillseek.vectorstore import ChromaVectorStore


@pytest.mark.gemini
def test_live_api_upload_index_search_and_grounded_ask(tmp_path) -> None:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        pytest.skip("GEMINI_API_KEY is not configured")

    root = Path(__file__).resolve().parents[2]
    source = root / "data" / "sample_docs" / "python_asyncio.txt"
    app_settings = Settings(
        _env_file=None,
        gemini_api_key=settings.gemini_api_key,
        gemini_base_url=settings.gemini_base_url,
        gemini_model=settings.gemini_model,
        llm_temperature=settings.llm_temperature,
        chroma_path=str(tmp_path / "chroma"),
        collection_name="api-live",
        upload_dir=str(tmp_path / "uploads"),
        max_upload_bytes=100_000,
        rag_prompt_char_budget=5000,
    )
    store = ChromaVectorStore(
        path=app_settings.chroma_path,
        collection_name=app_settings.collection_name,
        embedding_model_name=app_settings.embedding_model,
    )
    app = create_app(settings=app_settings, store=store)
    with TestClient(app) as client:
        upload = client.post(
            "/documents/upload",
            files=[("files", (source.name, source.read_bytes(), "text/plain"))],
        )
        assert upload.status_code == 200
        run = client.post("/index")
        assert run.status_code == 202
        job_id = run.json()["job_id"]

        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            status = client.get(f"/index/status/{job_id}").json()
            if status["finished"]:
                break
            time.sleep(0.1)
        assert status["finished"] is True
        assert status["indexed"] == 1

        results = client.post(
            "/search",
            json={"query": "How does asyncio enable asynchronous I/O?", "k": 5},
        )
        assert results.status_code == 200
        assert any(
            item["chunk"]["doc_name"] == source.name
            for item in results.json()["results"]
        )
        answer = client.post(
            "/ask", json={"query": "What syntax does asyncio use for concurrency?", "k": 5}
        )
        assert answer.status_code == 200
        body = answer.json()
        assert body["refused"] is False
        assert "async/await" in body["answer"].casefold()
        assert any(item["doc_name"] == source.name for item in body["sources"])
