"""Validated API request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from docintel.models import SearchResult
from docintel.rag.service import RAGResponse, RAGSource


class QueryRequest(BaseModel):
    """Question or search query with an optional bounded result count."""

    query: str = Field(min_length=1, max_length=10000)
    k: int | None = Field(default=None, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def query_must_have_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must contain non-whitespace text")
        return value.strip()


class HealthResponse(BaseModel):
    """Service and configured dependency health information."""

    status: str
    gemini_configured: bool
    gemini_reachable: bool | None
    gemini_model: str
    embedding_model: str
    chunk_count: int


class SearchAPIResponse(BaseModel):
    """Search results returned by the API."""

    query: str
    is_relevant: bool
    results: list[SearchResult]


class DocumentListResponse(BaseModel):
    """Indexed document summaries and pending upload names."""

    documents: list[dict]
    pending_uploads: list[str]


class UploadResponse(BaseModel):
    """Names accepted into the pending upload directory."""

    uploaded: list[str]
    count: int


class IndexResponse(BaseModel):
    """Index job identifier and its initial state."""

    job_id: str
    indexed: int = 0
    skipped: int = 0
    failed: list[dict] = Field(default_factory=list)
    chunks_indexed: int = 0
    finished: bool = False


class IndexStatusResponse(BaseModel):
    """Current/finished state of an indexing run."""

    job_id: str
    stage: str
    current_file: str
    percent: float = Field(ge=0.0, le=100.0)
    indexed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failed: list[dict] = Field(default_factory=list)
    failed_count: int = Field(default=0, ge=0)
    chunks_indexed: int = Field(ge=0)
    finished: bool


class AskAPIResponse(RAGResponse):
    """Grounded answer and evidence returned by `/ask`."""

    sources: list[RAGSource]


class ErrorResponse(BaseModel):
    """Consistent non-sensitive error response."""

    error: str
    detail: str
