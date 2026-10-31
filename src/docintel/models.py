"""Typed data models shared by ingestion and later pipeline stages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentRecord(BaseModel):
    """Metadata and processing state for one source document."""

    doc_id: str
    doc_name: str
    source_path: str
    file_type: Literal["pdf", "docx", "txt"]
    num_pages: int = Field(ge=0)
    created_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["pending", "indexed", "failed"] = "pending"


class PageContent(BaseModel):
    """Extracted content for a physical or logical document page."""

    doc_id: str
    doc_name: str
    page_number: int = Field(ge=1)
    section: str | None = None
    text: str


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


class SearchResult(BaseModel):
    """Placeholder for a ranked vector search result."""

    chunk: Chunk
    similarity: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)

