"""Unit tests for PDF, DOCX, and TXT loaders."""

import logging

from quillseek.ingestion import (
    decode_text,
    get_pdf_creation_date,
    load_docx,
    load_pdf,
    load_txt,
    parse_pdf_creation_date,
)
from quillseek.models import Chunk, DocumentRecord, PageContent, SearchResult


def test_pdf_loader_returns_one_record_per_page_and_creation_date(pdf_factory) -> None:
    pdf_path = pdf_factory(
        page_specs=("text", "text"), creation_date="D:20240203141516Z"
    )

    pages = load_pdf(pdf_path, doc_id="stable-id", doc_name="manual.pdf")

    assert [page.page_number for page in pages] == [1, 2]
    assert [page.text for page in pages] == ["Text on page 1", "Text on page 2"]
    assert all(page.doc_id == "stable-id" for page in pages)
    assert all(page.doc_name == "manual.pdf" for page in pages)
    assert get_pdf_creation_date(pdf_path).isoformat() == "2024-02-03T14:15:16+00:00"


def test_pdf_loader_keeps_blank_and_image_pages_and_warns(pdf_factory, caplog) -> None:
    pdf_path = pdf_factory(page_specs=("blank", "image"))

    with caplog.at_level(logging.WARNING):
        pages = load_pdf(pdf_path)

    assert len(pages) == 2
    assert [page.text for page in pages] == ["", ""]
    assert all("no extractable text" in record.message for record in caplog.records)


def test_pdf_loader_returns_empty_list_for_corrupt_pdf(tmp_path, caplog) -> None:
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"this is not a PDF")

    with caplog.at_level(logging.WARNING):
        pages = load_pdf(corrupt_pdf)

    assert pages == []
    assert any("Could not load PDF" in record.message for record in caplog.records)


def test_parse_pdf_creation_date_handles_offsets_and_invalid_values() -> None:
    parsed = parse_pdf_creation_date("D:20240203141516+05'30'")

    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 5.5 * 60 * 60
    assert parse_pdf_creation_date("not-a-pdf-date") is None
    assert parse_pdf_creation_date("D:20240203141516+99'99'") is None


def test_shared_models_validate_types_and_defaults() -> None:
    document = DocumentRecord(
        doc_id="id-1", doc_name="guide.pdf", source_path="guide.pdf",
        file_type="pdf", num_pages=2,
    )
    page = PageContent(doc_id="id-1", doc_name="guide.pdf", page_number=1, text="Hello")
    chunk = Chunk(chunk_id="chunk-1", doc_id="id-1", doc_name="guide.pdf", text="Hello", page_number=1)
    result = SearchResult(chunk=chunk, similarity=0.9, rank=1)

    assert document.status == "pending"
    assert document.num_pages == 2
    assert page.text == "Hello"
    assert result.chunk.chunk_id == "chunk-1"
    assert result.similarity == 0.9


def test_docx_loader_preserves_headings_paragraphs_and_table_rows(docx_factory) -> None:
    docx_path = docx_factory()

    pages = load_docx(docx_path, doc_id="word-id", doc_name="guide.docx")

    assert len(pages) == 2
    assert [page.section for page in pages] == ["Overview", "Details"]
    assert all(page.page_number == 1 for page in pages)
    assert pages[0].text.index("First section paragraph.") < pages[0].text.index(
        "Setting | Value"
    )
    assert "Retries | Three" in pages[0].text
    assert pages[1].text.endswith("Second section paragraph.")
    assert all(page.doc_id == "word-id" for page in pages)


def test_docx_loader_handles_empty_and_corrupt_documents(docx_factory, tmp_path) -> None:
    empty_path = docx_factory("empty.docx", empty=True)
    corrupt_path = tmp_path / "broken.docx"
    corrupt_path.write_bytes(b"not a DOCX")

    empty_pages = load_docx(empty_path)
    corrupt_pages = load_docx(corrupt_path)

    assert len(empty_pages) == 1
    assert empty_pages[0].page_number == 1
    assert empty_pages[0].text == ""
    assert corrupt_pages == []


def test_txt_loader_reads_utf8_and_removes_utf8_bom(tmp_path) -> None:
    text_path = tmp_path / "utf8.txt"
    text_path.write_bytes("\ufeffRésumé — notes".encode("utf-8"))

    pages = load_txt(text_path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].text == "Résumé — notes"


def test_txt_loader_decodes_latin1_and_cp1252(tmp_path) -> None:
    latin1_path = tmp_path / "latin1.txt"
    latin1_path.write_bytes(b"caf\xe9")
    cp1252_path = tmp_path / "cp1252.txt"
    cp1252_path.write_bytes(b"smart quote: \x93hello\x94")

    assert load_txt(latin1_path)[0].text == "café"
    assert load_txt(cp1252_path)[0].text == "smart quote: “hello”"
    assert decode_text(b"plain utf-8") == "plain utf-8"


def test_txt_loader_retains_one_empty_logical_page(tmp_path, caplog) -> None:
    empty_path = tmp_path / "empty.txt"
    empty_path.write_bytes(b"")

    with caplog.at_level(logging.WARNING):
        pages = load_txt(empty_path)

    assert len(pages) == 1
    assert pages[0].text == ""
    assert any("is empty" in record.message for record in caplog.records)
