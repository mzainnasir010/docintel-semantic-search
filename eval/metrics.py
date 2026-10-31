"""Reusable ranked-retrieval metrics used by chunk experiments and evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from quillseek.models import SearchResult


@dataclass(frozen=True)
class RetrievalMetrics:
    """Per-question Hit@K, Precision@K, Recall@K, and reciprocal rank."""

    hit_at_k: float
    precision_at_k: float
    recall_at_k: float
    mrr: float


def retrieval_metrics(
    results: Iterable[SearchResult],
    *,
    expected_doc_name: str,
    expected_pages: Iterable[int],
    k: int = 5,
) -> RetrievalMetrics:
    """Score results against expected source document and relevant pages.

    Precision counts relevant retrieved chunks divided by K. Recall measures the
    fraction of expected pages represented in the top K. Reciprocal rank uses the
    first result matching both the expected document and one expected page.
    """
    if k < 1:
        raise ValueError("k must be positive")
    expected = set(expected_pages)
    if not expected:
        raise ValueError("expected_pages must not be empty")
    top_results = list(results)[:k]
    relevant = [
        result
        for result in top_results
        if result.chunk.doc_name == expected_doc_name
        and result.chunk.page_number in expected
    ]
    found_pages = {result.chunk.page_number for result in relevant}
    first_relevant_rank = next(
        (
            rank
            for rank, result in enumerate(top_results, start=1)
            if result.chunk.doc_name == expected_doc_name
            and result.chunk.page_number in expected
        ),
        None,
    )
    return RetrievalMetrics(
        hit_at_k=float(bool(relevant)),
        precision_at_k=len(relevant) / k,
        recall_at_k=len(found_pages) / len(expected),
        mrr=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
    )


def mean_metrics(values: Iterable[RetrievalMetrics]) -> RetrievalMetrics:
    """Return the arithmetic mean of per-question metric observations."""
    observations = list(values)
    if not observations:
        raise ValueError("at least one metric observation is required")
    count = len(observations)
    return RetrievalMetrics(
        hit_at_k=sum(value.hit_at_k for value in observations) / count,
        precision_at_k=sum(value.precision_at_k for value in observations) / count,
        recall_at_k=sum(value.recall_at_k for value in observations) / count,
        mrr=sum(value.mrr for value in observations) / count,
    )
