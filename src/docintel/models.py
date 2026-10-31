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
    similarity: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)


class IngestionSummary(BaseModel):
    """Outcome of a batch ingestion run, including all extracted pages."""

    succeeded: int = Field(ge=0)
    failed: list[DocumentRecord] = Field(default_factory=list)
    documents: list[DocumentRecord] = Field(default_factory=list)
    pages: list[PageContent] = Field(default_factory=list)
    page_counts: dict[str, int] = Field(default_factory=dict)

