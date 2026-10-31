"""Metadata-preserving chunk strategies for document pages."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter

from docintel.config import get_settings
from docintel.models import Chunk, PageContent


@dataclass(frozen=True)
class TextSpan:
    """A source slice and its optional detected section heading."""

    text: str
    start: int
    end: int
    section: str | None = None


class BaseChunker(ABC):
    """Common interface shared by all text chunk strategies."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def split(self, text: str, section: str | None = None) -> list[TextSpan]:
        """Split one page of text, returning offsets into its original content."""

    def _recursive_spans(self, text: str, section: str | None = None) -> list[TextSpan]:
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        spans: list[TextSpan] = []
        search_from = 0
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if not piece:
                continue
            start = text.find(piece, search_from)
            if start < 0:
                start = text.find(piece)
            if start < 0:
                continue
            end = start + len(piece)
            spans.append(TextSpan(piece, start, end, section))
            search_from = min(end, start + max(1, self.chunk_overlap))
        return spans


class RecursiveChunker(BaseChunker):
    """Recursively split on paragraphs, lines, sentences, words, then chars."""

    def split(self, text: str, section: str | None = None) -> list[TextSpan]:
        return self._recursive_spans(text, section)


class SentenceChunker(BaseChunker):
    """Group whole sentences to the size limit, with optional sentence overlap."""

    _BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")

    def split(self, text: str, section: str | None = None) -> list[TextSpan]:
        units: list[tuple[int, int]] = []
        cursor = 0
        for boundary in self._BOUNDARY.finditer(text):
            start, end = cursor, boundary.start()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start < end:
                units.append((start, end))
            cursor = boundary.end()
        start = cursor
        end = len(text)
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            units.append((start, end))

        spans: list[TextSpan] = []
        group: list[tuple[int, int]] = []
        for unit in units:
            unit_length = unit[1] - unit[0]
            if unit_length > self.chunk_size:
                if group:
                    spans.append(self._make_span(text, group, section))
                    group = self._overlap_units(group)
                for span in self._recursive_spans(text[unit[0]:unit[1]], section):
                    spans.append(
                        TextSpan(span.text, span.start + unit[0], span.end + unit[0], section)
                    )
                group = []
                continue
            if group and unit[1] - group[0][0] > self.chunk_size:
                spans.append(self._make_span(text, group, section))
                group = self._overlap_units(group)
                while group and unit[1] - group[0][0] > self.chunk_size:
                    group = group[1:]
            group.append(unit)
        if group:
            spans.append(self._make_span(text, group, section))
        return spans

    @staticmethod
    def _make_span(text: str, units: list[tuple[int, int]], section: str | None) -> TextSpan:
        start, end = units[0][0], units[-1][1]
        return TextSpan(text[start:end].strip(), start, end, section)

    def _overlap_units(self, units: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if self.chunk_overlap == 0:
            return []
        overlap: list[tuple[int, int]] = []
        for unit in reversed(units):
            if overlap and overlap[-1][1] - unit[0] > self.chunk_overlap:
                break
            overlap.insert(0, unit)
        return overlap


class SectionAwareChunker(RecursiveChunker):
    """Split at explicit section headings, then recurse within each section."""

    _HEADING = re.compile(r"(?m)^(?:#{1,6}\s+.+|[A-Z][^\n]{1,79}:)\s*$")

    def split(self, text: str, section: str | None = None) -> list[TextSpan]:
        headings = list(self._HEADING.finditer(text))
        if not headings:
            return self._recursive_spans(text, section)
        boundaries = [0] + [match.start() for match in headings] + [len(text)]
        spans: list[TextSpan] = []
        for index in range(len(boundaries) - 1):
            start, end = boundaries[index], boundaries[index + 1]
            block = text[start:end]
            own_heading = next(
                (match.group().strip().lstrip("# ") for match in headings if match.start() == start),
                section,
            )
            spans.extend(
                TextSpan(span.text, span.start + start, span.end + start, own_heading)
                for span in self._recursive_spans(block, own_heading)
            )
        return spans


_STRATEGIES = {
    "recursive": RecursiveChunker,
    "sentence": SentenceChunker,
    "section": SectionAwareChunker,
    "section_aware": SectionAwareChunker,
}


def create_chunker(
    strategy: str | None = None,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> BaseChunker:
    """Build a chunker from explicit options or application settings."""
    settings = get_settings()
    strategy_name = (strategy or settings.chunk_strategy).lower()
    try:
        chunker_type = _STRATEGIES[strategy_name]
    except KeyError as error:
        raise ValueError(f"Unknown chunk strategy: {strategy_name}") from error
    return chunker_type(
        chunk_size if chunk_size is not None else settings.chunk_size,
        chunk_overlap if chunk_overlap is not None else settings.chunk_overlap,
    )


def chunk_pages(
    pages: Iterable[PageContent],
    *,
    strategy: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    ingested_at: datetime | None = None,
) -> list[Chunk]:
    """Chunk pages while preserving source metadata and suppressing duplicates."""
    chunker = create_chunker(
        strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    timestamp = ingested_at or datetime.now(timezone.utc)
    chunks: list[Chunk] = []
    seen_by_document: dict[str, set[str]] = {}
    indices: dict[tuple[str, int], int] = {}
    for page in pages:
        seen = seen_by_document.setdefault(page.doc_id, set())
        for span in chunker.split(page.text, page.section):
            normalized = span.text.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            key = (page.doc_id, page.page_number)
            index = indices.get(key, 0)
            indices[key] = index + 1
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
            chunks.append(
                Chunk(
                    chunk_id=f"{page.doc_id}:p{page.page_number}:c{index}-{digest}",
                    doc_id=page.doc_id,
                    doc_name=page.doc_name,
                    text=normalized,
                    page_number=page.page_number,
                    section=span.section,
                    source_path=page.source_path,
                    ingested_at=timestamp,
                    char_start=span.start,
                    char_end=span.end,
                )
            )
    return chunks
