"""End-to-end file indexing orchestration with progress and failure isolation."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path

from quillseek.chunking import chunk_pages
from quillseek.embeddings import Embedder
from quillseek.ingestion import ingest_files, stable_document_id
from quillseek.models import IndexFailure, IndexProgress, IndexRunSummary
from quillseek.vectorstore import ChromaVectorStore

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[IndexProgress], None]
DEFAULT_RUN_LOG = Path("eval/results/index_runs.jsonl")


def _report(callback: ProgressCallback | None, progress: IndexProgress) -> None:
    if callback is not None:
        callback(progress)


def _record_run(path: Path | None, summary: IndexRunSummary) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(summary.model_dump(mode="json")) + "\n")
    except OSError as error:
        logger.warning("Could not record indexing run %s at %s: %s", summary.run_id, path, error)


def index_files(
    paths: Iterable[str | Path],
    progress_callback: ProgressCallback | None = None,
    *,
    store: ChromaVectorStore | None = None,
    embedder: Embedder | None = None,
    run_log_path: str | Path | None = DEFAULT_RUN_LOG,
) -> IndexRunSummary:
    """Index files independently, continuing after failures and duplicate IDs."""
    file_paths = [Path(path) for path in paths]
    started_at = datetime.now(timezone.utc)
    start_clock = time.perf_counter()
    run_id = uuid.uuid4().hex
    active_embedder = embedder or Embedder()
    active_store = store or ChromaVectorStore(
        embedding_model_name=active_embedder.model_name
    )
    known_doc_ids = {document.doc_id for document in active_store.list_documents()}
    indexed = 0
    skipped = 0
    failures: list[IndexFailure] = []
    chunks_indexed = 0
    last_percent = 0.0
    total_files = len(file_paths)

    def emit(file_name: str, stage: str, fraction: float, *, complete: bool = False) -> None:
        nonlocal last_percent
        percent = 100.0 if complete else ((file_index + fraction) / total_files) * 100.0
        last_percent = max(last_percent, min(100.0, percent))
        _report(
            progress_callback,
            IndexProgress(
                current_file=file_name,
                stage=stage,
                percent=last_percent,
                indexed=indexed,
                skipped=skipped,
                failed=len(failures),
                chunks_indexed=chunks_indexed,
            ),
        )

    for file_index, path in enumerate(file_paths):
        doc_id = stable_document_id(path)
        name = path.name or str(path)
        emit(name, "ingest_preprocess", 0.05)
        if doc_id in known_doc_ids:
            skipped += 1
            emit(name, "skipped", 1.0)
            continue

        try:
            ingestion = ingest_files([path])
            if ingestion.failed:
                failure = ingestion.failed[0]
                failures.append(
                    IndexFailure(
                        doc_id=failure.doc_id,
                        file_name=name,
                        reason=failure.error_message or "Document ingestion failed",
                    )
                )
                emit(name, "failed", 1.0)
                continue

            emit(name, "chunk", 0.35)
            record = ingestion.documents[0]
            chunks = chunk_pages(
                ingestion.pages,
                ingested_at=record.ingested_at,
            )
            emit(name, "embed", 0.6)
            embeddings = active_embedder.embed_documents([chunk.text for chunk in chunks])
            emit(name, "store", 0.9)
            active_store.add_chunks(chunks, embeddings)
            known_doc_ids.add(doc_id)
            indexed += 1
            chunks_indexed += len(chunks)
            emit(name, "complete", 1.0)
        except Exception as error:
            reason = str(error) or error.__class__.__name__
            logger.exception("Indexing failed for %s: %s", path, reason)
            failures.append(IndexFailure(doc_id=doc_id, file_name=name, reason=reason))
            emit(name, "failed", 1.0)

    if not file_paths:
        _report(
            progress_callback,
            IndexProgress(
                current_file="",
                stage="complete",
                percent=100.0,
                indexed=0,
                skipped=0,
                failed=0,
                chunks_indexed=0,
            ),
        )

    summary = IndexRunSummary(
        run_id=run_id,
        started_at=started_at,
        elapsed_seconds=time.perf_counter() - start_clock,
        indexed=indexed,
        skipped=skipped,
        failed=failures,
        chunks_indexed=chunks_indexed,
    )
    _record_run(Path(run_log_path) if run_log_path is not None else None, summary)
    logger.info(
        "Index run %s finished in %.3fs: indexed=%s skipped=%s failed=%s chunks=%s",
        summary.run_id,
        summary.elapsed_seconds,
        summary.indexed,
        summary.skipped,
        len(summary.failed),
        summary.chunks_indexed,
    )
    return summary


def index_directory(
    path: str | Path,
    progress_callback: ProgressCallback | None = None,
    **kwargs,
) -> IndexRunSummary:
    """Recursively index all regular files beneath a directory."""
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"Index directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Index path is not a directory: {root}")
    files = sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: str(item).casefold(),
    )
    return index_files(files, progress_callback, **kwargs)
