"""Verify answer evidence and page references against extracted corpus pages."""

import json
from pathlib import Path

from docintel.ingestion import load_docx, load_pdf, load_txt
from docintel.preprocessing import clean_text


def test_answerable_questions_have_evidence_on_their_cited_pages() -> None:
    root = Path(__file__).resolve().parents[2]
    corpus = root / "data" / "sample_docs"
    question_path = root / "eval" / "questions.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    cached_pages = {}

    for question in questions:
        if question["type"] == "unanswerable":
            continue
        filename = question["expected_doc_name"]
        if filename not in cached_pages:
            source = corpus / filename
            if source.suffix == ".pdf":
                pages = load_pdf(source)
            elif source.suffix == ".docx":
                pages = load_docx(source)
            else:
                pages = load_txt(source)
            cached_pages[filename] = {
                page.page_number: " ".join(clean_text(page.text).split()) for page in pages
            }

        page_map = cached_pages[filename]
        for page_number in question["expected_pages"]:
            assert page_number in page_map, f"{filename} has no page {page_number}"
        for evidence in question["evidence"]:
            normalized_evidence = " ".join(clean_text(evidence).split())
            assert any(
                normalized_evidence in page_map[page_number]
                for page_number in question["expected_pages"]
            ), f"Evidence for {question['id']} is not on its cited page"
