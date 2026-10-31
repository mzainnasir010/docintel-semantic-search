"""Test configuration for imports from the src layout."""

import sys
from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document as WordDocument
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontend" / "src"))
sys.path.insert(0, str(ROOT / "backend" / "src"))


@pytest.fixture
def pdf_factory(tmp_path):
    """Create tiny PDFs with text, blank, or image-only pages."""
    def create_pdf(name="fixture.pdf", page_specs=("text",), creation_date=None):
        pdf = pymupdf.open()
        for index, kind in enumerate(page_specs, start=1):
            page = pdf.new_page()
            if kind == "text":
                page.insert_text((72, 72), f"Text on page {index}")
            elif kind == "image":
                image_bytes = BytesIO()
                Image.new("RGB", (8, 8), color="red").save(image_bytes, format="PNG")
                page.insert_image(
                    pymupdf.Rect(40, 40, 48, 48), stream=image_bytes.getvalue()
                )
        if creation_date:
            pdf.set_metadata({"creationDate": creation_date})
        path = tmp_path / name
        pdf.save(path)
        pdf.close()
        return path

    return create_pdf


@pytest.fixture
def docx_factory(tmp_path):
    """Create a DOCX containing headings, paragraphs, and a table."""
    def create_docx(name="fixture.docx", *, empty=False):
        document = WordDocument()
        if not empty:
            document.add_heading("Overview", level=1)
            document.add_paragraph("First section paragraph.")
            table = document.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Setting"
            table.cell(0, 1).text = "Value"
            table.cell(1, 0).text = "Retries"
            table.cell(1, 1).text = "Three"
            document.add_heading("Details", level=2)
            document.add_paragraph("Second section paragraph.")
        path = tmp_path / name
        document.save(path)
        return path

    return create_docx

