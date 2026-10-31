"""Unit tests for strategy selection and metadata-complete chunks."""

from datetime import datetime, timezone

import pytest

from docintel.chunking import (
    RecursiveChunker,
    SectionAwareChunker,
    SentenceChunker,
    chunk_pages,
    create_chunker,
)
from docintel.models import PageContent


def _page(text: str, *, doc_id: str = "doc-1", page: int = 1, section=None):
    return PageContent(
        doc_id=doc_id,
        doc_name="manual.txt",
        page_number=page,
        section=section,
        text=text,
        source_path="data/manual.txt",
    )


def test_factory_selects_all_configured_strategies() -> None:
    assert isinstance(create_chunker("recursive", chunk_size=20, chunk_overlap=2), RecursiveChunker)
    assert isinstance(create_chunker("sentence", chunk_size=20, chunk_overlap=2), SentenceChunker)
    assert isinstance(create_chunker("section_aware", chunk_size=20, chunk_overlap=2), SectionAwareChunker)


def test_recursive_chunks_respect_size_overlap_and_metadata() -> None:
    text = "alpha beta gamma delta epsilon zeta eta theta"
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    chunks = chunk_pages(
        [_page(text)],
        strategy="recursive",
        chunk_size=18,
        chunk_overlap=7,
        ingested_at=timestamp,
    )

    assert len(chunks) > 1
    assert all(0 < len(chunk.text) <= 18 for chunk in chunks)
    assert any(set(chunks[index].text.split()) & set(chunks[index + 1].text.split()) for index in range(len(chunks) - 1))
    assert all(chunk.doc_id == "doc-1" for chunk in chunks)
    assert all(chunk.doc_name == "manual.txt" for chunk in chunks)
    assert all(chunk.source_path == "data/manual.txt" for chunk in chunks)
    assert all(chunk.ingested_at == timestamp for chunk in chunks)
    assert all(text[chunk.char_start:chunk.char_end].strip() == chunk.text for chunk in chunks)
    assert [chunk.chunk_id for chunk in chunks] == [
        chunk.chunk_id
        for chunk in chunk_pages(
            [_page(text)], strategy="recursive", chunk_size=18, chunk_overlap=7,
            ingested_at=timestamp,
        )
    ]


def test_sentence_strategy_keeps_sentence_boundaries() -> None:
    text = "First sentence. Second sentence! Third sentence?"
    chunks = chunk_pages(
        [_page(text)], strategy="sentence", chunk_size=32, chunk_overlap=0
    )

    assert [chunk.text for chunk in chunks] == [
        "First sentence. Second sentence!",
        "Third sentence?",
    ]


def test_section_strategy_attaches_heading_and_falls_back_for_long_sections() -> None:
    text = "# Setup\nInstall the package.\n\n# Usage\n" + "Run the command. " * 8
    chunks = chunk_pages(
        [_page(text)], strategy="section", chunk_size=28, chunk_overlap=4
    )

    assert all(len(chunk.text) <= 28 for chunk in chunks)
    assert any(chunk.section == "Setup" for chunk in chunks)
    assert any(chunk.section == "Usage" for chunk in chunks)


def test_empty_chunks_and_duplicates_within_document_are_skipped() -> None:
    pages = [_page("Same text.", page=1), _page("Same text.", page=2)]
    chunks = chunk_pages(pages, chunk_size=40, chunk_overlap=0)

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunk_pages([_page("   \n\t")], chunk_size=40, chunk_overlap=0) == []


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"), [(0, 0), (10, 10), (10, -1)]
)
def test_invalid_chunk_parameters_are_rejected(chunk_size, chunk_overlap) -> None:
    with pytest.raises(ValueError):
        create_chunker("recursive", chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown chunk strategy"):
        create_chunker("mystery", chunk_size=10, chunk_overlap=0)
