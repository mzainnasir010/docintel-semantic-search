"""Integration checks for the assembled redistributable sample corpus."""

import pymupdf
from docx import Document as WordDocument

from scripts.build_corpus import DOCUMENTS, CORPUS_DIR, COPYRIGHT_NOTICE, LICENSE_NAME


def test_corpus_contains_licensed_pdf_docx_and_txt_documents() -> None:
    document_paths = [CORPUS_DIR / item.filename for item in DOCUMENTS]
    suffixes = {path.suffix.lower() for path in document_paths}

    assert 5 <= len(document_paths) <= 15
    assert suffixes == {".pdf", ".docx", ".txt"}
    assert all(path.is_file() and path.stat().st_size > 0 for path in document_paths)


def test_sources_manifest_covers_every_document_and_license() -> None:
    manifest = (CORPUS_DIR / "SOURCES.md").read_text(encoding="utf-8")

    assert LICENSE_NAME in manifest
    assert (CORPUS_DIR / "PSF_LICENSE.txt").is_file()
    for item in DOCUMENTS:
        assert item.filename in manifest
        assert item.url in manifest


def test_each_corpus_file_contains_its_subject_and_attribution() -> None:
    for item in DOCUMENTS:
        path = CORPUS_DIR / item.filename
        if path.suffix == ".pdf":
            with pymupdf.open(path) as document:
                text = "\n".join(page.get_text() for page in document)
        elif path.suffix == ".docx":
            word_document = WordDocument(path)
            text = "\n".join(paragraph.text for paragraph in word_document.paragraphs)
        else:
            text = path.read_text(encoding="utf-8")

        assert item.title in text
        assert LICENSE_NAME in text
        assert COPYRIGHT_NOTICE in text
