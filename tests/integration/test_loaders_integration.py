"""Exercise all file loaders with shared document metadata models."""

from quillseek.ingestion import load_docx, load_pdf, load_txt
from quillseek.models import PageContent


def test_all_loaders_return_compatible_page_content(pdf_factory, docx_factory, tmp_path) -> None:
    pdf_path = pdf_factory("report.pdf", page_specs=("text", "text"))
    docx_path = docx_factory("handbook.docx")
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("A short text document.", encoding="utf-8")

    loaded_pages = [
        *load_pdf(pdf_path),
        *load_docx(docx_path),
        *load_txt(txt_path),
    ]

    assert len(loaded_pages) == 5
    assert all(isinstance(page, PageContent) for page in loaded_pages)
    assert {page.doc_name for page in loaded_pages} == {
        "report.pdf",
        "handbook.docx",
        "notes.txt",
    }
    assert all(page.page_number >= 1 for page in loaded_pages)
