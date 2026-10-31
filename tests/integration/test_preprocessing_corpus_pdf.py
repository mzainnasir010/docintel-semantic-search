"""Exercise page-stream preprocessing against a checked-in corpus PDF."""

from pathlib import Path

from quillseek.ingestion import iter_pdf_pages
from quillseek.preprocessing import BoilerplateReport, iter_preprocessed_pages


def test_corpus_pdf_preprocessing_preserves_pages_and_document_text() -> None:
    root = Path(__file__).resolve().parents[2]
    pdf_path = root / "data" / "sample_docs" / "python_argparse.pdf"
    report = BoilerplateReport()

    cleaned_pages = list(
        iter_preprocessed_pages(lambda: iter_pdf_pages(pdf_path), report=report)
    )

    assert cleaned_pages
    assert [page.page_number for page in cleaned_pages] == list(
        range(1, len(cleaned_pages) + 1)
    )
    assert all(page.doc_name == pdf_path.name for page in cleaned_pages)
    assert "argparse" in cleaned_pages[0].text.lower()
    assert report.pages_processed == len(cleaned_pages)
