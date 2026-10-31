"""FastAPI routes for health, documents, indexing, search, and grounded answers."""

from __future__ import annotations

import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from docintel.config import Settings, get_settings
from docintel.indexing import index_files
from docintel.ingestion import stable_document_id
from docintel.models import IndexProgress
from docintel.rag import CitationValidationError, GeminiClient, RAGService
from docintel.search import SearchService
from docintel.vectorstore import ChromaVectorStore
from docintel.api.schemas import (
    AskAPIResponse,
    DocumentListResponse,
    ErrorResponse,
    HealthResponse,
    IndexResponse,
    IndexStatusResponse,
    QueryRequest,
    SearchAPIResponse,
    UploadResponse,
)

logger = logging.getLogger(__name__)
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def _safe_filename(name: str | None) -> str:
    """Keep only a normalized basename and remove path/control characters."""
    basename = (name or "upload").replace("\\", "/").split("/")[-1]
    sanitized = SAFE_NAME.sub("_", basename).strip(" .")
    if not sanitized or sanitized in {".", ".."}:
        sanitized = "upload"
    return sanitized[:180]


def _gemini_reachable(settings: Settings) -> bool:
    """Check model metadata endpoint without exposing credentials or prompting."""
    if not settings.gemini_api_key.get_secret_value():
        return False
    endpoint = (
        f"{settings.gemini_base_url.rstrip('/')}/models/{settings.gemini_model}"
    )
    try:
        response = httpx.get(
            endpoint,
            headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
            timeout=3.0,
        )
        return response.status_code == 200
    except httpx.RequestError:
        return False


def create_app(
    *,
    settings: Settings | None = None,
    store: Any | None = None,
    search_service: Any | None = None,
    rag_service: Any | None = None,
    indexer: Callable[..., Any] = index_files,
    health_probe: Callable[[Settings], bool] = _gemini_reachable,
) -> FastAPI:
    """Build an injectable FastAPI application suitable for production and tests."""
    active_settings = settings or get_settings()
    active_store = store or ChromaVectorStore(
        embedding_model_name=active_settings.embedding_model
    )
    active_search = search_service or SearchService(vector_store=active_store)
    active_rag = rag_service or RAGService(search_service=active_search)
    upload_dir = Path(active_settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="DocIntel API",
        version="0.1.0",
        description="Document ingestion, semantic retrieval, and grounded Q&A.",
    )
    app.state.settings = active_settings
    app.state.store = active_store
    app.state.search_service = active_search
    app.state.rag_service = active_rag
    app.state.indexer = indexer
    app.state.jobs: dict[str, dict[str, Any]] = {}
    app.state.upload_dir = upload_dir

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[active_settings.gradio_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        logger.info("API request %s %s", request.method, request.url.path)
        response = await call_next(request)
        logger.info(
            "API response %s %s %s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException):
        detail = error.detail if isinstance(error.detail, str) else "Request failed"
        return JSONResponse(
            status_code=error.status_code,
            content=ErrorResponse(error="request_error", detail=detail).model_dump(),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error", detail="Request validation failed"
            ).model_dump(),
        )

    @app.exception_handler(CitationValidationError)
    async def citation_error(_request: Request, _error: CitationValidationError):
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="invalid_model_response",
                detail="The language model returned an answer without valid source citations.",
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def internal_error(_request: Request, error: Exception):
        logger.exception("Unhandled API error: %s", error)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error", detail="The request could not be completed."
            ).model_dump(),
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        configured = bool(active_settings.gemini_api_key.get_secret_value())
        reachable = health_probe(active_settings) if configured else False
        return HealthResponse(
            status="ok",
            gemini_configured=configured,
            gemini_reachable=reachable,
            gemini_model=active_settings.gemini_model,
            embedding_model=active_settings.embedding_model,
            chunk_count=active_store.count(),
        )

    @app.post(
        "/documents/upload", response_model=UploadResponse, tags=["documents"]
    )
    async def upload_documents(
        files: list[UploadFile] = File(..., description="PDF, DOCX, or TXT files")
    ) -> UploadResponse:
        if not files:
            raise HTTPException(status_code=400, detail="At least one file is required")
        prepared: list[tuple[str, bytes]] = []
        total_bytes = 0
        for upload in files:
            name = _safe_filename(upload.filename)
            if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type for {name}; use PDF, DOCX, or TXT",
                )
            content = await upload.read(active_settings.max_upload_bytes + 1)
            if len(content) > active_settings.max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {name} exceeds the upload size limit",
                )
            if not content:
                raise HTTPException(status_code=400, detail=f"File {name} is empty")
            total_bytes += len(content)
            if total_bytes > active_settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="Upload batch exceeds the size limit")
            prepared.append((name, content))

        accepted: list[str] = []
        for name, content in prepared:
            document_id = __import__("hashlib").sha256(content).hexdigest()[:16]
            destination = upload_dir / document_id / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            accepted.append(name)
        return UploadResponse(uploaded=accepted, count=len(accepted))

    @app.get("/documents", response_model=DocumentListResponse, tags=["documents"])
    def list_documents() -> DocumentListResponse:
        indexed = active_store.list_documents()
        indexed_ids = {document.doc_id for document in indexed}
        pending = []
        for path in sorted(upload_dir.rglob("*"), key=lambda item: item.name.casefold()):
            if path.is_file() and stable_document_id(path) not in indexed_ids:
                pending.append(path.name)
        return DocumentListResponse(
            documents=[document.model_dump(mode="json") for document in indexed],
            pending_uploads=pending,
        )

    @app.delete("/documents/{doc_id}", tags=["documents"])
    def delete_document(doc_id: str) -> dict[str, Any]:
        deleted_chunks = active_store.delete_document(doc_id)
        deleted_uploads = 0
        for path in upload_dir.rglob("*"):
            if path.is_file() and stable_document_id(path) == doc_id:
                path.unlink()
                deleted_uploads += 1
        for directory in sorted(
            (path for path in upload_dir.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()
        if deleted_chunks == 0 and deleted_uploads == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "doc_id": doc_id,
            "deleted_chunks": deleted_chunks,
            "deleted_uploads": deleted_uploads,
        }

    @app.post("/index", response_model=IndexResponse, tags=["indexing"])
    def start_index() -> IndexResponse:
        pending_paths = [
            path
            for path in sorted(upload_dir.rglob("*"), key=lambda item: item.name.casefold())
            if path.is_file()
        ]
        progress: dict[str, Any] = {
            "stage": "queued",
            "current_file": "",
            "percent": 0.0,
            "indexed": 0,
            "skipped": 0,
            "failed": [],
            "chunks_indexed": 0,
            "finished": False,
        }

        def update(snapshot: IndexProgress) -> None:
            progress.update(
                stage=snapshot.stage,
                current_file=snapshot.current_file,
                percent=snapshot.percent,
                indexed=snapshot.indexed,
                skipped=snapshot.skipped,
                failed=snapshot.failed,
                chunks_indexed=snapshot.chunks_indexed,
            )

        summary = app.state.indexer(
            pending_paths,
            update,
            store=active_store,
            run_log_path=None,
        )
        job_id = summary.run_id
        progress.update(
            stage="complete",
            current_file=progress.get("current_file", ""),
            percent=100.0,
            indexed=summary.indexed,
            skipped=summary.skipped,
            failed=[failure.model_dump(mode="json") for failure in summary.failed],
            chunks_indexed=summary.chunks_indexed,
            finished=True,
        )
        app.state.jobs[job_id] = progress
        return IndexResponse(
            job_id=job_id,
            indexed=summary.indexed,
            skipped=summary.skipped,
            failed=[failure.model_dump(mode="json") for failure in summary.failed],
            chunks_indexed=summary.chunks_indexed,
            finished=True,
        )

    @app.get(
        "/index/status/{job_id}", response_model=IndexStatusResponse, tags=["indexing"]
    )
    def index_status(job_id: str) -> IndexStatusResponse:
        status = app.state.jobs.get(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Index job not found")
        return IndexStatusResponse(job_id=job_id, **status)

    @app.post("/search", response_model=SearchAPIResponse, tags=["search"])
    def search(request: QueryRequest) -> SearchAPIResponse:
        result = active_search.search(request.query, k=request.k)
        return SearchAPIResponse(
            query=request.query,
            is_relevant=result.is_relevant,
            results=result.results,
        )

    @app.post("/ask", response_model=AskAPIResponse, tags=["question answering"])
    def ask(request: QueryRequest) -> AskAPIResponse:
        return active_rag.ask(request.query, k=request.k)

    @app.delete("/collection", tags=["indexing"])
    def reset_collection() -> dict[str, Any]:
        active_store.reset()
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        app.state.jobs.clear()
        return {"status": "reset", "chunk_count": active_store.count()}

    return app


app = create_app()
