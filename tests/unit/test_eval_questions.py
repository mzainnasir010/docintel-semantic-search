"""Schema and corpus-reference validation for the reviewed question set."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = ROOT / "eval" / "questions.json"
CORPUS_PATH = ROOT / "data" / "sample_docs"
ALLOWED_TYPES = {"direct", "paraphrased", "multi_chunk", "unanswerable"}


def test_question_set_schema_and_category_counts() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    assert 25 <= len(questions) <= 30
    assert len({question["id"] for question in questions}) == len(questions)

    for question in questions:
        assert {
            "id", "question", "expected_doc_name", "expected_pages",
            "expected_answer", "type", "evidence",
        } <= question.keys()
        assert question["type"] in ALLOWED_TYPES
        assert question["question"].strip()
        assert question["expected_answer"].strip()
        if question["type"] == "unanswerable":
            assert question["expected_doc_name"] is None
            assert question["expected_pages"] == []
            assert question["evidence"] == []
        else:
            assert (CORPUS_PATH / question["expected_doc_name"]).is_file()
            assert question["expected_pages"]
            assert all(isinstance(page, int) and page >= 1 for page in question["expected_pages"])
            assert question["evidence"]

    types = [question["type"] for question in questions]
    assert types.count("unanswerable") >= 4
    assert types.count("paraphrased") >= 5

