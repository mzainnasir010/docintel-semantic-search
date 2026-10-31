"""Mixed batch ingestion keeps processing after individual file failures."""

from quillseek.ingestion import ingest_files
import pymupdf


def test_batch_ingests_valid_files_and_reports_corrupt_and_unsupported(
    pdf_factory, tmp_path
) -> None:
    valid_pdf = pdf_factory("good.pdf", page_specs=("text", "text"))
    valid_txt = tmp_path / "good.txt"
    valid_txt.write_text("A valid text page", encoding="utf-8")
    corrupt_pdf = tmp_path / "broken.pdf"
    corrupt_pdf.write_bytes(b"not a PDF")
    unsupported = tmp_path / "table.csv"
    unsupported.write_text("a,b", encoding="utf-8")

    result = ingest_files([valid_pdf, corrupt_pdf, unsupported, valid_txt])

    assert result.succeeded == 2
    assert len(result.failed) == 2
    assert [record.status for record in result.documents] == [
        "indexed", "failed", "failed", "indexed"
    ]
    assert result.page_counts[result.documents[0].doc_id] == 2
    assert result.page_counts[result.documents[1].doc_id] == 0
    assert result.page_counts[result.documents[3].doc_id] == 1
    assert "No pages could be extracted" in result.documents[1].error_message
    assert "Unsupported document type" in result.documents[2].error_message
    assert len(result.pages) == 3
    assert result.pages[-1].doc_name == "good.txt"


def test_ingestion_service_cleans_repeated_pdf_boilerplate(tmp_path) -> None:
    pdf_path = tmp_path / "boilerplate.pdf"
    document = pymupdf.open()
    for page_number in range(1, 4):
        page = document.new_page()
        page.insert_text((72, 40), "Repeated Manual Header")
        page.insert_text((72, 100), f"Important content on page {page_number}")
        page.insert_text((72, 780), f"Page {page_number} of 3")
    document.save(pdf_path)
    document.close()

    result = ingest_files([pdf_path])

    assert result.succeeded == 1
    assert [page.page_number for page in result.pages] == [1, 2, 3]
    assert all("Repeated Manual Header" not in page.text for page in result.pages)
    assert all("Important content" in page.text for page in result.pages)
    assert all("Page " not in page.text for page in result.pages)
