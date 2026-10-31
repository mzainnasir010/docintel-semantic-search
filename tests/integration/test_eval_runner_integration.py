"""Evaluation runner artifact test with deterministic retrieval and LLM doubles."""

from pathlib import Path
from types import SimpleNamespace

from eval.run_eval import run_evaluation
from quillseek.models import Chunk, SearchResult
from quillseek.rag.llm import RateLimitError
from quillseek.rag.service import RAGResponse, RAGSource


def _result() -> SearchResult:
    return SearchResult(
        chunk=Chunk(chunk_id="chunk-1", doc_id="doc-1", doc_name="guide.txt",
                    text="Use pathlib.Path for paths.", page_number=1),
        similarity=0.9,
        rank=1,
    )


class FakeSearch:
    def search(self, query: str, *, k: int):
        results = [_result()] if query == "Which path class?" else []
        return SimpleNamespace(results=results, is_relevant=bool(results))


class FakeRAG:
    def ask(self, query: str, *, k: int):
        if query == "Which path class?":
            result = _result()
            source = RAGSource(label="S1", doc_name="guide.txt", page_number=1,
                               section=None, similarity=0.9, snippet=result.text)
            return RAGResponse(
                answer="Use pathlib.Path for paths [S1].", sources=[source],
                retrieved_chunks=[result], retrieval_ms=2, generation_ms=3,
                input_tokens=100, output_tokens=12, total_tokens=112, refused=False,
            )
        return RAGResponse(
            answer="the answer is not present in the supplied documents", sources=[],
            retrieved_chunks=[], retrieval_ms=1, generation_ms=0, refused=True,
        )


def test_runner_writes_retrieval_answer_and_refusal_metrics(tmp_path: Path) -> None:
    questions = [
        {"id": "q1", "question": "Which path class?", "expected_doc_name": "guide.txt",
         "expected_pages": [1], "expected_answer": "Use pathlib.Path for paths.", "type": "direct"},
        {"id": "q2", "question": "How does this corpus explain quantum engines?",
         "expected_doc_name": None, "expected_pages": [],
         "expected_answer": "The corpus does not specify this.", "type": "unanswerable"},
    ]
    results_path = tmp_path / "results.csv"
    summary_path = tmp_path / "summary.json"
    rows, summary = run_evaluation(
        questions, FakeSearch(), FakeRAG(), model="gemini-3.8-flash",
        results_path=results_path, summary_path=summary_path,
        index_runs_path=tmp_path / "missing-index-log.jsonl",
    )
    assert len(rows) == 2
    assert rows[0]["hit_at_3"] == 1.0
    assert rows[0]["hit_at_10"] == 1.0
    assert summary["retrieval"]["20"]["precision"] == 0.05
    assert rows[0]["grounding_valid"] is True
    assert rows[0]["answer_correct_proxy"] is True
    assert rows[1]["refusal_correct"] is True
    assert rows[1]["estimated_paid_tier_cost_usd"] == 0
    assert summary["question_count"] == 2
    assert summary["retrieval"]["3"]["mrr"] == 1.0
    assert results_path.is_file() and summary_path.is_file()


def test_runner_stops_at_quota_and_resumes_without_repeating_successes(tmp_path: Path) -> None:
    questions = [
        {"id": f"q{index}", "question": "Which path class?", "expected_doc_name": "guide.txt",
         "expected_pages": [1], "expected_answer": "Use pathlib.Path for paths.", "type": "direct"}
        for index in range(1, 4)
    ]

    class QuotaThenSuccess:
        def __init__(self, quota_once: bool):
            self.quota_once = quota_once
            self.calls: list[str] = []

        def ask(self, query: str, *, k: int):
            self.calls.append(query)
            if self.quota_once and len(self.calls) == 2:
                raise RateLimitError("daily quota exhausted")
            return FakeRAG().ask("Which path class?", k=k)

    results_path = tmp_path / "resume.csv"
    summary_path = tmp_path / "resume.json"
    rag_first = QuotaThenSuccess(quota_once=True)
    partial, _ = run_evaluation(
        questions, FakeSearch(), rag_first, model="gemini-3.8-flash",
        results_path=results_path, summary_path=summary_path,
        index_runs_path=tmp_path / "missing.jsonl",
    )
    assert len(partial) == 2
    assert partial[-1]["evaluation_error"].startswith("RateLimitError:")

    rag_second = QuotaThenSuccess(quota_once=False)
    completed, summary = run_evaluation(
        questions, FakeSearch(), rag_second, model="gemini-3.8-flash",
        results_path=results_path, summary_path=summary_path,
        index_runs_path=tmp_path / "missing.jsonl", resume=True,
    )
    assert len(completed) == 3
    assert rag_second.calls == ["Which path class?", "Which path class?"]
    assert summary["question_count"] == 3


def test_runner_can_record_real_retrieval_while_deferring_gemini(tmp_path: Path) -> None:
    question = {"id": "q1", "question": "Which path class?", "expected_doc_name": "guide.txt",
                "expected_pages": [1], "expected_answer": "Use pathlib.Path for paths.", "type": "direct"}

    class NeverCallRAG:
        def ask(self, *_args, **_kwargs):
            raise AssertionError("RAG must be deferred in retrieval-only mode")

    rows, summary = run_evaluation(
        [question], FakeSearch(), NeverCallRAG(), model="gemini-3.8-flash",
        results_path=tmp_path / "retrieval.csv", summary_path=tmp_path / "retrieval.json",
        index_runs_path=tmp_path / "missing.jsonl", skip_rag=True,
    )
    assert rows[0]["hit_at_3"] == 1.0
    assert rows[0]["evaluation_error"].startswith("DeferredGeminiRun:")
    assert rows[0]["estimated_paid_tier_cost_usd"] is None
    assert summary["rag_deferred_question_count"] == 1
