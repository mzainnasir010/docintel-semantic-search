"""Typed data models shared by ingestion and later pipeline stages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    """Metadata and processing state for one source document."""

    doc_id: str
    doc_name: str
    source_path: str
    file_type: Literal["pdf", "docx", "txt", "unsupported"]
    num_pages: int = Field(ge=0)
    created_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["pending", "indexed", "failed"] = "pending"
    error_message: str | None = None


class PageContent(BaseModel):
    """Extracted content for a physical or logical document page."""

    doc_id: str
    doc_name: str
    page_number: int = Field(ge=1)
    section: str | None = None
    text: str
    source_path: str | Path = ""


class Chunk(BaseModel):
    """Placeholder for a text chunk used by later pipeline stages."""

    chunk_id: str
    doc_id: str
    doc_name: str
    text: str
    page_number: int = Field(ge=1)
    section: str | None = None
    source_path: str | Path = ""
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)


class SearchResult(BaseModel):
    """Placeholder for a ranked vector search result."""

    chunk: Chunk
    similarity: float = Field(ge=-1.0, le=1.0)
    rank: int = Field(ge=1)

    @property
    def text(self) -> str:
        """Expose matched chunk text directly for search consumers."""
        return self.chunk.text

    @property
    def doc_name(self) -> str:
        """Expose the source document name directly."""
        return self.chunk.doc_name

    @property
    def doc_id(self) -> str:
        """Expose the stable source document ID directly."""
        return self.chunk.doc_id

    @property
    def page_number(self) -> int:
        """Expose the source page number directly."""
        return self.chunk.page_number

    @property
    def section(self) -> str | None:
        """Expose the source section directly."""
        return self.chunk.section

    @property
    def chunk_id(self) -> str:
        """Expose the stable chunk ID directly."""
        return self.chunk.chunk_id


class SearchResponse(BaseModel):
    """Ranked search matches and an explicit relevance flag."""

    results: list[SearchResult] = Field(default_factory=list)
    is_relevant: bool


class IndexedDocument(BaseModel):
    """Document summary stored in the persistent vector index."""

    doc_id: str
    doc_name: str
    chunk_count: int = Field(ge=0)
    pages: list[int] = Field(default_factory=list)


class IndexFailure(BaseModel):
    """Per-file indexing failure with a stable document identity when possible."""

    doc_id: str
    file_name: str
    reason: str


class IndexProgress(BaseModel):
    """Snapshot emitted by the indexing pipeline progress callback."""

    current_file: str
    stage: str
    percent: float = Field(ge=0.0, le=100.0)
    indexed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failed: int = Field(ge=0)
    chunks_indexed: int = Field(ge=0)


class IndexRunSummary(BaseModel):
    """Counts and timing for one complete indexing run."""

    run_id: str
    started_at: datetime
    elapsed_seconds: float = Field(ge=0.0)
    indexed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failed: list[IndexFailure] = Field(default_factory=list)
    chunks_indexed: int = Field(ge=0)


class IngestionSummary(BaseModel):
    """Outcome of a batch ingestion run, including all extracted pages."""

    succeeded: int = Field(ge=0)
    failed: list[DocumentRecord] = Field(default_factory=list)
    documents: list[DocumentRecord] = Field(default_factory=list)
    pages: list[PageContent] = Field(default_factory=list)
    page_counts: dict[str, int] = Field(default_factory=dict)

