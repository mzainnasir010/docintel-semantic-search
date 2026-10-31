"""Hand-calculated checks for evaluation metrics and token cost."""

import pytest

from eval.metrics import key_fact_coverage, mean_relevant_similarity, priced_token_cost_usd
from quillseek.models import Chunk, SearchResult


def _result(doc: str, page: int, score: float) -> SearchResult:
    return SearchResult(
        chunk=Chunk(chunk_id=f"{doc}-{page}", doc_id=doc, doc_name=doc,
                    text="evidence", page_number=page),
        similarity=score,
        rank=1,
    )


def test_mean_correct_similarity_uses_only_gold_document_and_pages() -> None:
    results = [_result("guide.pdf", 1, 0.8), _result("guide.pdf", 2, 0.6), _result("other.pdf", 1, 1.0)]
    assert mean_relevant_similarity(results, expected_doc_name="guide.pdf", expected_pages=[1, 2]) == pytest.approx(0.7)
    assert mean_relevant_similarity(results, expected_doc_name="missing.pdf", expected_pages=[1]) is None


def test_key_fact_coverage_hand_computed_and_rejects_empty_facts() -> None:
    assert key_fact_coverage("Use pathlib.Path for paths.", "pathlib.Path handles paths") == pytest.approx(1.0)
    assert key_fact_coverage("Use pathlib.Path for paths.", "Use pathlib.Path") == pytest.approx(0.5)
    with pytest.raises(ValueError, match="key fact"):
        key_fact_coverage("the and of", "anything")


def test_paid_tier_cost_uses_usd_per_million_rates() -> None:
    assert priced_token_cost_usd(1000, 2000, input_per_million=0.75, output_per_million=3.75) == pytest.approx(0.00825)


def test_pricing_is_versioned_for_the_selected_gemini_model() -> None:
    from datetime import date
    from eval.run_eval import pricing_for

    assert pricing_for("gemini-3.8-flash", date(2026, 10, 31)) == (0.75, 3.75)
    assert pricing_for("gemini-3.8-flash", date(2027, 1, 1)) == (1.5, 7.5)
    with pytest.raises(ValueError, match="No dated pricing"):
        pricing_for("unknown-model", date(2026, 10, 31))
