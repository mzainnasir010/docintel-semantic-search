"""Unit tests for repeated header/footer removal and page-wise iteration."""

from docintel.models import PageContent
from docintel.preprocessing import BoilerplateReport, iter_preprocessed_pages


def _page(number: int, text: str) -> PageContent:
    return PageContent(
        doc_id="doc-1", doc_name="manual.pdf", page_number=number, text=text
    )


def test_repeated_headers_footers_and_page_number_variants_are_removed() -> None:
    pages = [
        _page(i, f"Manual Title\nPage-specific paragraph {i}.\nIMPORTANT NOTICE\nPage {i} of 4")
        for i in range(1, 5)
    ]
    report = BoilerplateReport()
    cleaned = list(iter_preprocessed_pages(lambda: iter(pages), report=report))

    assert [page.page_number for page in cleaned] == [1, 2, 3, 4]
    assert all("Manual Title" not in page.text for page in cleaned)
    assert all("Page-specific paragraph" in page.text for page in cleaned)
    assert all("IMPORTANT NOTICE" in page.text for page in cleaned)
    assert all("Page " not in page.text for page in cleaned)
    assert report.pages_processed == 4
    assert report.removed_lines["manual title"] == 4
    assert report.removed_lines["page # of #"] == 4


def test_standalone_page_numbers_removed_but_repeated_midpage_content_kept() -> None:
    pages = [
        _page(i, f"Opening {i}\nShared technical phrase\nClosing {i}\n{i}")
        for i in range(1, 4)
    ]
    cleaned = list(iter_preprocessed_pages(lambda: iter(pages)))

    assert all("Shared technical phrase" in page.text for page in cleaned)
    assert all(f"Closing {index}" in page.text for index, page in enumerate(cleaned, 1))
    assert all(page.page_number == index for index, page in enumerate(cleaned, 1))


def test_empty_document_produces_no_pages_and_zero_report() -> None:
    report = BoilerplateReport()

    assert list(iter_preprocessed_pages(lambda: iter(()), report=report)) == []
    assert report.pages_processed == 0
    assert report.removed_lines == {}
