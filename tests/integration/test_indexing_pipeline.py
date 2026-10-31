"""Integration tests for resilient, idempotent end-to-end indexing."""

import json
from pathlib import Path

import numpy as np

from quillseek.indexing import index_directory, index_files
from quillseek.models import IndexProgress
from quillseek.vectorstore import ChromaVectorStore


class FakeEmbedder:
    model_name = "test-indexer-model"

    def embed_documents(self, texts):
        return np.asarray(
            [[len(text) + 1, text.lower().count("python") + 1, text.count(" ") + 1] for text in texts],
            dtype=np.float32,
        )


def test_mixed_index_run_continues_reports_progress_and_skips_on_rerun(tmp_path) -> None:
    first = tmp_path / "first.txt"
    first.write_text("Python coroutines can run asynchronously.", encoding="utf-8")
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"not a PDF")
    unsupported = tmp_path / "ignored.csv"
    unsupported.write_text("name,value", encoding="utf-8")
    final = tmp_path / "final.txt"
    final.write_text("Python tasks may also use queues.", encoding="utf-8")

    store = ChromaVectorStore(
        path=tmp_path / "index",
        collection_name="documents",
        embedding_model_name=FakeEmbedder.model_name,
    )
    events: list[IndexProgress] = []
    run_log = tmp_path / "runs.jsonl"
    files = [first, corrupt_pdf, unsupported, final]
    first_run = index_files(
        files,
        events.append,
        store=store,
        embedder=FakeEmbedder(),
        run_log_path=run_log,
    )

    assert first_run.indexed == 2
    assert first_run.skipped == 0
    assert len(first_run.failed) == 2
    assert first_run.chunks_indexed == 2
    assert store.count() == 2
    assert [event.percent for event in events] == sorted(event.percent for event in events)
    assert events[-1].percent == 100.0
    assert {event.current_file for event in events} == {
        "first.txt", "corrupt.pdf", "ignored.csv", "final.txt"
    }
    assert any("No pages could be extracted" in failure.reason for failure in first_run.failed)
    assert any("Unsupported document type" in failure.reason for failure in first_run.failed)

    second_run = index_files(
        files,
        store=store,
        embedder=FakeEmbedder(),
        run_log_path=run_log,
    )

    assert second_run.indexed == 0
    assert second_run.skipped == 2
    assert len(second_run.failed) == 2
    assert store.count() == 2
    records = [json.loads(line) for line in run_log.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[0]["elapsed_seconds"] >= 0


def test_index_directory_recursively_indexes_supported_files(tmp_path) -> None:
    input_root = tmp_path / "input"
    nested = input_root / "nested"
    nested.mkdir(parents=True)
    document = nested / "guide.txt"
    document.write_text("Python uses modules.", encoding="utf-8")
    store = ChromaVectorStore(
        path=tmp_path / "directory-index",
        collection_name="documents",
        embedding_model_name=FakeEmbedder.model_name,
    )

    summary = index_directory(
        input_root,
        store=store,
        embedder=FakeEmbedder(),
        run_log_path=None,
    )

    assert summary.indexed == 1
    assert summary.failed == []
    assert store.count() == 1
