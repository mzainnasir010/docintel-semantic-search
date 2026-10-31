"""Opt-in grounding and refusal evaluation using the real corpus and Gemini."""

import json
import sys
from pathlib import Path

import pytest

from quillseek.config import get_settings
from quillseek.rag import REFUSAL, RAGService
from quillseek.rag.llm import (
    LLMTimeoutError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
BY_ID = {item["id"]: item for item in QUESTIONS}


def _service() -> RAGService:
    if not get_settings().gemini_api_key.get_secret_value():
        pytest.skip("GEMINI_API_KEY is not configured")
    return RAGService()


def _ask_live(question: str, *, k: int):
    try:
        return _service().ask(question, k=k)
    except (RateLimitError, ServiceUnavailableError, LLMTimeoutError, NetworkError) as error:
        pytest.skip(f"Gemini is temporarily unavailable: {type(error).__name__}")


@pytest.mark.gemini
@pytest.mark.parametrize(
    ("question_id", "expected_fact"),
    [
        ("q-001", "async/await"),
        ("q-004", "lightweight data interchange format"),
        ("q-014", "syntax errors"),
    ],
)
def test_live_answerable_question_is_grounded_and_cited(question_id, expected_fact) -> None:
    item = BY_ID[question_id]
    answer = _ask_live(item["question"], k=5)

    assert not answer.refused, f"{question_id} unexpectedly refused: {answer.answer}"
    assert expected_fact.casefold() in answer.answer.casefold()
    assert any(source.doc_name == item["expected_doc_name"] for source in answer.sources)
    assert all(f"[{source.label}]" in answer.answer for source in answer.sources)


@pytest.mark.gemini
def test_live_question_with_missing_retrieved_evidence_is_refused() -> None:
    # Q-019 is answerable in the corpus, but its top-five retrieval currently
    # misses the answer-bearing passage. The context-only system must abstain.
    item = BY_ID["q-019"]
    answer = _ask_live(item["question"], k=5)

    assert answer.refused is True
    assert answer.answer == REFUSAL
    assert answer.sources == []


@pytest.mark.gemini
@pytest.mark.parametrize(
    "question_id",
    ["q-029", "q-030", "q-032", "q-033"],
)
def test_live_unanswerable_question_is_honestly_refused(question_id) -> None:
    item = BY_ID[question_id]
    answer = _ask_live(item["question"], k=5)
    normalized = answer.answer.strip().casefold()

    assert answer.refused or normalized == REFUSAL or "not present" in normalized
    assert answer.sources == []
    assert not any(
        forbidden in normalized
        for forbidden in ("yes,", "no,", "it automatically", "the built-in module is")
    )


def test_rate_limited_live_request_skips_gracefully(monkeypatch) -> None:
    class LimitedService:
        def ask(self, _question: str, *, k: int):
            raise RateLimitError("rate limited")

    monkeypatch.setattr(sys.modules[__name__], "_service", lambda: LimitedService())
    with pytest.raises(pytest.skip.Exception, match="RateLimitError"):
        _ask_live("question", k=5)
