"""Unit tests for grounded prompt construction and RAG orchestration."""

import pytest

from docintel.models import Chunk, SearchResponse, SearchResult
from docintel.rag import (
    REFUSAL,
    CitationValidationError,
    PromptBuilder,
    RAGService,
)


def result(
    chunk_id: str,
    *,
    doc_name: str = "guide.txt",
    text: str | None = None,
    page: int = 1,
    section: str | None = "Overview",
    similarity: float = 0.8,
) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=chunk_id,
            doc_id=f"doc-{chunk_id}",
            doc_name=doc_name,
            text=text or f"Evidence for {chunk_id}.",
            page_number=page,
            section=section,
        ),
        similarity=similarity,
        rank=1,
    )


class FakeSearch:
    def __init__(self, results=None, *, relevant=None):
        self.results = results or []
        self.relevant = bool(self.results) if relevant is None else relevant
        self.calls = []

    def search(self, question, k=None):
        self.calls.append((question, k))
        return SearchResponse(results=self.results, is_relevant=self.relevant)


class FakeLLM:
    def __init__(self, answer="Evidence supports this [S1]."):
        self.answer = answer
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.answer

    def stream(self, prompt):
        yield self.generate(prompt)


def test_prompt_has_grounding_instruction_labeled_context_and_question() -> None:
    first = result("one", doc_name="api.pdf", text="First source text", page=4)
    second = result("two", doc_name="guide.docx", text="Second source text", page=2)

    built = PromptBuilder().build("What is documented?", [first, second], max_chars=5000)

    assert "Answer using ONLY the supplied CONTEXT" in built.text
    assert "Do not use outside knowledge" in built.text
    assert "MUST include at least one exact source label" in built.text
    assert "The documented value is 42 [S1]." in built.text
    assert "reply exactly" in built.text
    assert "[S1] document=api.pdf; page=4; section=Overview" in built.text
    assert "[S2] document=guide.docx; page=2; section=Overview" in built.text
    assert "First source text" in built.text and "Second source text" in built.text
    assert "QUESTION:\nWhat is documented?" in built.text
    assert [source.label for source in built.sources] == ["S1", "S2"]


def test_prompt_truncates_to_total_character_budget() -> None:
    long = result("long", text="evidence " * 500)
    next_result = result("next", doc_name="next.txt", text="other evidence")
    builder = PromptBuilder()
    minimum_prompt = builder.build("Q?", [], max_chars=5000).text
    budget = len(minimum_prompt) + 110

    built = builder.build("Q?", [long, next_result], max_chars=budget)

    assert len(built.text) <= budget
    assert len(built.sources) == 1
    assert len(built.sources[0].context_text) < len(long.chunk.text)
    assert "[S1]" in built.text
    assert "[S2]" not in built.text


def test_prompt_rejects_too_small_budget() -> None:
    with pytest.raises(ValueError, match="budget is too small"):
        PromptBuilder().build("A long enough question", [], max_chars=10)


def test_refusal_skips_llm_when_retrieval_finds_no_relevant_results() -> None:
    search = FakeSearch([result("below", similarity=0.1)], relevant=False)
    llm = FakeLLM()
    service = RAGService(search, llm)

    answer = service.ask("What does the corpus say?", k=4)

    assert answer.answer == REFUSAL
    assert answer.refused is True
    assert answer.sources == []
    assert answer.retrieved_chunks == []
    assert answer.generation_ms == 0
    assert llm.prompts == []
    assert search.calls == [("What does the corpus say?", 4)]


def test_answer_maps_only_cited_sources_and_returns_timings() -> None:
    first = result("one", doc_name="first.pdf", page=3, text="First source evidence.")
    second = result("two", doc_name="second.txt", page=8, text="Second source evidence.")
    search = FakeSearch([first, second])
    llm = FakeLLM("Supported fact [S2].")
    service = RAGService(search, llm)

    answer = service.ask("Tell me a supported fact")

    assert answer.answer == "Supported fact [S2]."
    assert answer.refused is False
    assert len(answer.retrieved_chunks) == 2
    assert len(answer.sources) == 1
    assert answer.sources[0].label == "S2"
    assert answer.sources[0].doc_name == "second.txt"
    assert answer.sources[0].page_number == 8
    assert answer.sources[0].snippet == "Second source evidence."
    assert answer.retrieval_ms >= 0
    assert answer.generation_ms >= 0
    assert "[S2] document=second.txt; page=8" in llm.prompts[0]


@pytest.mark.parametrize("answer", ["Uncited statement.", "Bad citation [S9]."])
def test_invalid_or_missing_citations_are_rejected(answer) -> None:
    service = RAGService(FakeSearch([result("one")]), FakeLLM(answer))

    with pytest.raises(CitationValidationError):
        service.ask("Question")


def test_model_refusal_is_returned_as_refusal() -> None:
    service = RAGService(FakeSearch([result("one")]), FakeLLM(REFUSAL.upper()))

    answer = service.ask("Question")

    assert answer.answer == REFUSAL
    assert answer.refused
    assert answer.sources == []


def test_retrieval_only_mode_does_not_call_llm() -> None:
    search = FakeSearch([result("one")])
    llm = FakeLLM()
    service = RAGService(search, llm)

    response = service.retrieve("Search only", k=2)

    assert response.is_relevant
    assert len(response.results) == 1
    assert search.calls == [("Search only", 2)]
    assert llm.prompts == []
