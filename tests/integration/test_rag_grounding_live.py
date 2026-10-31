"""Opt-in grounding and refusal evaluation using the real corpus and Gemini."""

import json
from pathlib import Path

import pytest

from docintel.config import get_settings
from docintel.rag import REFUSAL, RAGService

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
BY_ID = {item["id"]: item for item in QUESTIONS}


def _service() -> RAGService:
    if not get_settings().gemini_api_key.get_secret_value():
        pytest.skip("GEMINI_API_KEY is not configured")
    return RAGService()


@pytest.mark.gemini
@pytest.mark.parametrize(
    ("question_id", "expected_fact"),
    [
        ("q-001", "async/await"),
        ("q-004", "lightweight data interchange format"),
        ("q-014", "syntax errors"),
        ("q-019", "last-in, first-out"),
    ],
)
def test_live_answerable_question_is_grounded_and_cited(question_id, expected_fact) -> None:
    item = BY_ID[question_id]
    answer = _service().ask(item["question"], k=5)

    assert not answer.refused, f"{question_id} unexpectedly refused: {answer.answer}"
    assert expected_fact.casefold() in answer.answer.casefold()
    assert any(source.doc_name == item["expected_doc_name"] for source in answer.sources)
    assert all(f"[{source.label}]" in answer.answer for source in answer.sources)


@pytest.mark.gemini
@pytest.mark.parametrize(
    "question_id",
    ["q-029", "q-030", "q-032", "q-033"],
)
def test_live_unanswerable_question_is_honestly_refused(question_id) -> None:
    item = BY_ID[question_id]
    answer = _service().ask(item["question"], k=5)
    normalized = answer.answer.strip().casefold()

    assert answer.refused or normalized == REFUSAL or "not present" in normalized
    assert answer.sources == []
    assert not any(
        forbidden in normalized
        for forbidden in ("yes,", "no,", "it automatically", "the built-in module is")
    )
