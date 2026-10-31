"""Hand-calculated tests for reusable retrieval metrics."""

import pytest

from quillseek.models import Chunk, SearchResult
from eval.metrics import mean_metrics, retrieval_metrics


def _result(doc: str, page: int, rank: int) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=f"{doc}-{page}-{rank}",
            doc_id=doc,
            doc_name=f"{doc}.txt",
            text="evidence",
            page_number=page,
        ),
        similarity=0.9 - rank * 0.1,
        rank=rank,
    )


def test_retrieval_metrics_hand_computed_single_page_match() -> None:
    scores = retrieval_metrics(
        [_result("other", 1, 1), _result("target", 1, 2), _result("target", 1, 3)],
        expected_doc_name="target.txt",
        expected_pages=[1],
        k=3,
    )

    assert scores.hit_at_k == 1.0
    assert scores.precision_at_k == pytest.approx(2 / 3)
    assert scores.recall_at_k == 1.0
    assert scores.mrr == 0.5


def test_recall_counts_expected_pages_independently() -> None:
    scores = retrieval_metrics(
        [_result("target", 2, 1), _result("other", 3, 2)],
        expected_doc_name="target.txt",
        expected_pages=[2, 3],
        k=5,
    )

    assert scores.hit_at_k == 1.0
    assert scores.precision_at_k == pytest.approx(1 / 5)
    assert scores.recall_at_k == 0.5
    assert scores.mrr == 1.0


def test_no_relevant_results_score_zero() -> None:
    scores = retrieval_metrics(
        [_result("other", 1, 1)],
        expected_doc_name="target.txt",
        expected_pages=[1],
        k=5,
    )

    assert scores.hit_at_k == 0.0
    assert scores.precision_at_k == 0.0
    assert scores.recall_at_k == 0.0
    assert scores.mrr == 0.0


def test_mean_metrics_hand_computed() -> None:
    first = retrieval_metrics(
        [_result("target", 1, 1)], expected_doc_name="target.txt", expected_pages=[1], k=1
    )
    second = retrieval_metrics(
        [], expected_doc_name="target.txt", expected_pages=[1], k=1
    )

    mean = mean_metrics([first, second])
    assert mean.hit_at_k == 0.5
    assert mean.precision_at_k == 0.5
    assert mean.recall_at_k == 0.5
    assert mean.mrr == 0.5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expected_doc_name": "target.txt", "expected_pages": [1], "k": 0},
        {"expected_doc_name": "target.txt", "expected_pages": [], "k": 5},
    ],
)
def test_invalid_metric_inputs_are_rejected(kwargs) -> None:
    with pytest.raises(ValueError):
        retrieval_metrics([], **kwargs)
